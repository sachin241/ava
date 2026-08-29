from django.test import SimpleTestCase, override_settings
from unittest.mock import patch

from .frame_buffer import LatestFrameBuffer
from .state import WorldStateEngine
from .response import ResponseManager, ResponseRequest
from .safety import SafetyEngine, SafetyEvent, path_overlap_for_bbox
from .intent import classify
from .interaction import route
from .controller import AssistantController
from .ocr import _clean
from .context import deterministic_summary, verified_facts
from .validation import validate_scene_response
from .workflow import RichWorkflow
from .danger import classify_detections, classify_text, classify_sign, normalize_sign_text, UNKNOWN_HAZARD


class DangerClassifierTests(SimpleTestCase):
    def obj(self, name="chair", confidence=0.9, direction="center", proximity="near", motion="stationary"):
        return {"id": 1, "name": name, "confidence": confidence, "direction": direction, "proximity": proximity, "motion": motion}

    def test_chair_approaching_becomes_collision_hazard(self):
        result = classify_detections([self.obj(motion="approaching")], 10)
        self.assertEqual(result[0]["type"], "COLLISION_HAZARD")

    def test_stairs_becomes_stair_hazard(self):
        self.assertEqual(classify_detections([self.obj("stairs")])[0]["type"], "STAIR_HAZARD")

    def test_ocr_semantic_signs(self):
        self.assertEqual(classify_text("ROAD WORK AHEAD")[0]["type"], "ROAD_WORK")
        self.assertEqual(classify_text("WET FLOOR")[0]["type"], "WET_FLOOR")
        self.assertEqual(classify_text("HIGH VOLTAGE")[0]["type"], "ELECTRICAL_HAZARD")

    def test_unknown_warning_and_low_confidence(self):
        self.assertEqual(classify_text("CAUTION")[0]["type"], UNKNOWN_HAZARD)
        self.assertEqual(classify_text("HIGH VOLTAGE", 0.3)[0]["confidence"], 0.3)

    def test_sign_normalization_and_symbol_fusion(self):
        self.assertEqual(normalize_sign_text("  wet---  floor! "), "WET FLOOR")
        result = classify_sign("HIGH VOLTAGE", ["⚡"], 0.8)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "ELECTRICAL_HAZARD")
        self.assertGreater(result[0]["confidence"], 0.8)

    def test_ordinary_text_is_not_a_danger(self):
        self.assertEqual(classify_sign("Library opening hours"), [])


@override_settings(TRACK_MAX_AGE_MS=100, TRACK_HISTORY_SIZE=12)
class WorldStateTests(SimpleTestCase):
    def setUp(self):
        self.state = WorldStateEngine()

    def update(self, bbox, timestamp, track_id=None):
        return self.state.update([{"track_id": track_id, "label": "chair", "confidence": 0.9, "bbox": bbox}], (100, 100), timestamp)

    def test_proximity_changes_far_medium_near_for_same_object(self):
        first = self.update([0, 0, 5, 5], 1)
        middle = self.update([0, 0, 30, 30], 2)
        last = self.update([0, 0, 50, 50], 3)
        self.assertEqual([first["objects"][0]["proximity"], middle["objects"][0]["proximity"], last["objects"][0]["proximity"]], ["far", "medium", "near"])
        self.assertEqual(first["objects"][0]["id"], last["objects"][0]["id"])

    def test_direction_and_motion_change(self):
        first = self.update([0, 40, 10, 50], 1, track_id=17)
        second = self.update([40, 40, 50, 50], 2, track_id=17)
        third = self.update([40, 40, 60, 60], 3, track_id=17)
        self.assertEqual(first["objects"][0]["direction"], "left")
        self.assertEqual(second["objects"][0]["direction"], "center")
        self.assertEqual(second["objects"][0]["motion"], "moving")
        self.assertEqual(third["objects"][0]["motion"], "approaching")

    def test_expired_object_is_removed_from_active_state(self):
        self.update([0, 0, 10, 10], 1)
        retained = self.state.update([], (100, 100), 50)
        self.assertEqual(len(retained["objects"]), 1)
        state = self.state.update([], (100, 100), 102)
        self.assertEqual(state["objects"], [])

    def test_bytetrack_id_is_preserved_when_present(self):
        first = self.update([0, 0, 10, 10], 1, track_id=17)
        second = self.update([1, 0, 11, 10], 2, track_id=17)
        self.assertEqual(first["objects"][0]["id"], 17)
        self.assertEqual(second["objects"][0]["id"], 17)

    @override_settings(MAX_ACTIVE_TRACKS=2)
    def test_active_world_state_is_capped(self):
        detections = [
            {"track_id": index, "label": f"object-{index}", "confidence": 0.9 - index / 100, "bbox": [index, 0, index + 1, 1]}
            for index in range(5)
        ]
        state = self.state.update(detections, (100, 100), 1)
        self.assertEqual(len(state["objects"]), 2)


class LatestFrameBufferTests(SimpleTestCase):
    def test_newer_pending_frame_replaces_older_frame(self):
        buffer = LatestFrameBuffer[str]()
        buffer.offer("old")
        buffer.offer("latest")
        self.assertEqual(buffer.take_latest(), "latest")
        self.assertEqual(buffer.metrics.dropped, 1)


class SafetyEngineTests(SimpleTestCase):
    def setUp(self):
        self.engine = SafetyEngine()

    @staticmethod
    def obj(object_id=1, proximity="near", motion="stationary", path_overlap=True, name="chair", confidence=0.9):
        return {"id": object_id, "name": name, "confidence": confidence, "direction": "center", "proximity": proximity, "motion": motion, "path_overlap": path_overlap}

    def test_stationary_hazard_requires_persistence_before_alerting(self):
        first, summary = self.engine.evaluate([self.obj()], 1000)
        second, summary = self.engine.evaluate([self.obj()], 1100)
        third, summary = self.engine.evaluate([self.obj()], 1200)
        fourth, summary = self.engine.evaluate([self.obj()], 1300)
        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertTrue(any(event.type == "PATH_BLOCKED" for event in third))
        self.assertEqual(fourth, [])
        self.assertEqual(summary["path_status"], "blocked")

    def test_approaching_object_escalates_to_immediate_alert(self):
        self.engine.evaluate([self.obj(proximity="medium")], 1000)
        events, summary = self.engine.evaluate([self.obj(proximity="near", motion="approaching")], 1100)
        self.assertTrue(any(event.type == "OBSTACLE_APPROACHING" and event.priority == 95 for event in events))
        self.assertEqual(summary["system_state"], "critical")

    def test_low_confidence_detections_are_ignored(self):
        events, summary = self.engine.evaluate([self.obj(confidence=0.4)], 1000)
        self.assertEqual(events, [])
        self.assertEqual(summary["system_state"], "clear")
        self.assertEqual(summary["path_status"], "clear")

    def test_path_overlap_is_conservative(self):
        self.assertTrue(path_overlap_for_bbox([40, 0, 60, 20], 100))
        self.assertFalse(path_overlap_for_bbox([0, 0, 20, 20], 100))

    def test_emergency_is_priority_one_hundred(self):
        events, _ = self.engine.evaluate([self.obj(name="fire")], 1000)
        self.assertEqual(events[0].type, "EMERGENCY_DETECTED")
        self.assertEqual(events[0].priority, 100)

    def test_path_cleared_follows_a_blocked_path(self):
        self.engine.evaluate([self.obj()], 1000)
        self.engine.evaluate([self.obj()], 1100)
        self.engine.evaluate([self.obj()], 1200)
        self.engine.evaluate([], 1300)
        self.engine.evaluate([], 1400)
        events, summary = self.engine.evaluate([], 1500)
        self.assertTrue(any(event.type == "PATH_CLEARED" for event in events))
        self.assertEqual(summary["path_status"], "clear")

    @patch("services.workflow.ollama_service.describe")
    @override_settings(OLLAMA_ENABLED=True)
    def test_critical_safety_path_never_invokes_ollama(self, describe):
        events, summary = self.engine.evaluate([self.obj(proximity="near", motion="approaching")], 1000)
        self.assertTrue(any(event.priority == 95 for event in events))
        self.assertEqual(summary["system_state"], "critical")
        describe.assert_not_called()


class ResponseManagerTests(SimpleTestCase):
    @staticmethod
    def event(event_type="OBSTACLE_ENTERED_PATH", priority=90, timestamp=1000, object_id=1):
        return SafetyEvent(event_type, priority, object_id, "chair", "center", "high", timestamp)

    def test_same_alert_is_suppressed_during_cooldown(self):
        manager = ResponseManager()
        self.assertEqual(manager.submit(self.event())["action"], "SPEAK")
        self.assertEqual(manager.submit(self.event(timestamp=1100))["action"], "DROP")

    def test_critical_event_interrupts_current_scene_response(self):
        manager = ResponseManager()
        scene = ResponseRequest("You are in a corridor.", 50, "SCENE", None, 1000)
        self.assertEqual(manager.submit_request(scene)["action"], "SPEAK")
        result = manager.submit(self.event("OBSTACLE_APPROACHING", 95, 1100))
        self.assertEqual(result["action"], "INTERRUPT")

    def test_emergency_stop_and_repeat(self):
        manager = ResponseManager()
        emergency = manager.submit(self.event("EMERGENCY_DETECTED", 100, 1000, None))
        self.assertEqual(emergency["action"], "SPEAK")
        self.assertEqual(emergency["request"]["priority"], 100)
        self.assertEqual(manager.stop()["action"], "DROP")
        repeat = manager.repeat()
        self.assertEqual(repeat["action"], "INTERRUPT")
        self.assertEqual(repeat["request"]["priority"], 100)

    def test_lower_priority_response_queues_and_releases_after_completion(self):
        manager = ResponseManager()
        manager.submit_request(ResponseRequest("Current scene", 50, "SCENE", None, 1000))
        queued = manager.submit_request(ResponseRequest("General information", 30, "INFO", None, 1100))
        self.assertEqual(queued["action"], "QUEUE")
        released = manager.complete()
        self.assertEqual(released["action"], "SPEAK")
        self.assertEqual(released["request"]["text"], "General information")

    def test_cancelled_response_cannot_complete_a_newer_interrupt(self):
        manager = ResponseManager()
        first = ResponseRequest("Scene", 50, "SCENE", None, 1000)
        manager.submit_request(first)
        emergency = manager.submit(self.event("EMERGENCY_DETECTED", 100, 1100, None))
        self.assertEqual(manager.complete(first.timestamp)["action"], "DROP")
        self.assertEqual(manager.complete(emergency["request"]["timestamp"])["action"], "DROP")


class InteractionTests(SimpleTestCase):
    def test_assistant_controller_transitions_are_deterministic(self):
        controller = AssistantController()
        self.assertEqual(controller.snapshot()["state"], "IDLE")
        self.assertEqual(controller.handle("START_MONITORING")["state"], "MONITORING")
        self.assertEqual(controller.handle("PAUSE_MONITORING")["state"], "PAUSED")
        self.assertEqual(controller.handle("RESUME_MONITORING")["state"], "MONITORING")
        self.assertEqual(controller.handle("STOP_MONITORING")["state"], "IDLE")
        self.assertTrue(controller.handle("MUTE")["muted"])
        self.assertFalse(controller.handle("UNMUTE")["muted"])

    def test_extended_voice_commands_classify(self):
        self.assertEqual(classify("Start monitoring"), "START_MONITORING")
        self.assertEqual(classify("Stop monitoring"), "STOP_MONITORING")
        self.assertEqual(classify("Pause"), "PAUSE_MONITORING")
        self.assertEqual(classify("Resume"), "RESUME_MONITORING")
        self.assertEqual(classify("Mute"), "MUTE")
        self.assertEqual(classify("Emergency"), "SOS")

    def test_deterministic_intent_routing(self):
        self.assertEqual(classify("Where is the door?"), "LOCATE")
        self.assertEqual(classify("Is the path clear?"), "PATH")
        self.assertEqual(classify("Read this sign."), "READ")
        self.assertEqual(classify("Describe my surroundings."), "SCENE")
        self.assertEqual(classify("Repeat."), "REPEAT")
        self.assertEqual(classify("Stop."), "STOP")

    @patch("services.interaction.response_manager")
    @patch("services.interaction.world_state")
    def test_locate_uses_world_state_then_response_manager(self, state, manager):
        state.snapshot.return_value = {"objects": [{"name": "door", "direction": "right"}]}
        manager.submit_request.return_value = {"action": "SPEAK", "request": {"text": "The door is on your right."}}
        result = route("Where is the door?")
        self.assertEqual(result["intent"], "LOCATE")
        manager.submit_request.assert_called_once()

    def test_ocr_cleanup_collapses_noise(self):
        self.assertEqual(_clean(" Exit\n\n  Ahead\x0c"), "Exit Ahead")


class RichWorkflowTests(SimpleTestCase):
    def setUp(self):
        self.state = {
            "objects": [
                {"name": "person", "direction": "center", "proximity": "medium", "motion": "stationary"},
                {"name": "door", "direction": "right", "proximity": "medium", "motion": "stationary"},
                {"name": "chair", "direction": "left", "proximity": "near", "motion": "stationary"},
            ],
            "path_status": "clear",
            "system_state": "clear",
        }

    @override_settings(OLLAMA_ENABLED=False)
    def test_scene_uses_langgraph_and_deterministic_fallback_when_ollama_disabled(self):
        result = RichWorkflow().run("SCENE", self.state)
        self.assertEqual(result["source"], "deterministic")
        self.assertIn("path ahead appears clear", result["text"].lower())
        self.assertIn("door on your right", result["text"].lower())

    def test_fact_contract_excludes_safety_internal_fields(self):
        facts = verified_facts({**self.state, "active_hazard": 7, "last_alert": {"priority": 95}})
        self.assertEqual(set(facts), {"objects", "path_status", "system_state"})
        self.assertNotIn("active_hazard", str(facts))

    def test_invalid_llm_object_or_direction_is_rejected(self):
        facts = verified_facts(self.state)
        self.assertIsNone(validate_scene_response("There is a cat on your left.", facts))
        self.assertIsNone(validate_scene_response("The door is on your left.", facts))

    @patch("services.workflow.ollama_service.describe", return_value="The path is clear. There is a door on your right.")
    @override_settings(OLLAMA_ENABLED=True)
    def test_valid_ollama_text_is_used_only_after_validation(self, describe):
        result = RichWorkflow().run("SCENE", self.state)
        self.assertEqual(result["source"], "ollama")
        self.assertIn("door", result["text"].lower())

    @patch("services.workflow.ollama_service.describe", return_value="There is a cat on your left.")
    @override_settings(OLLAMA_ENABLED=True)
    def test_invalid_ollama_text_falls_back(self, describe):
        result = RichWorkflow().run("SCENE", self.state)
        self.assertEqual(result["source"], "deterministic")
