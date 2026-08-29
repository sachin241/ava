"""Routes interaction results through ResponseManager; it never speaks directly."""
from __future__ import annotations

import time
from typing import Any

from .intent import classify
from .response import ResponseRequest, response_manager
from .state import world_state
from .workflow import rich_workflow
from .controller import assistant_controller


def respond(text: str, event_type: str, priority: int = 50, suppress: bool = False) -> dict[str, Any]:
    request = ResponseRequest(text, priority, event_type, None, int(time.time() * 1000))
    return response_manager.submit_request(request, suppress=suppress)


def _position(obj: dict[str, Any]) -> str:
    direction = obj.get("direction")
    if direction == "center":
        return "ahead"
    if direction in {"left", "right"}:
        return f"to your {direction}"
    return "in view"


def _distance(obj: dict[str, Any]) -> str:
    return {
        "near": "close",
        "medium": "a short distance away",
        "far": "farther away",
    }.get(obj.get("proximity"), "at an unclear distance")


def route(text: str) -> dict[str, Any]:
    intent = classify(text)
    state = assistant_controller.handle(intent)
    if intent == "MUTE":
        response_manager.set_muted(True)
        return {"intent": intent, "assistant": state, "response": {"action": "DROP", "request": None}}
    if intent == "UNMUTE":
        response_manager.set_muted(False)
        return {"intent": intent, "assistant": state, "response": respond("Voice responses are back on.", "UNMUTE", 30)}
    if intent == "SOS":
        return {"intent": intent, "assistant": state, "response": response_manager.submit_emergency()}
    if intent == "CHANGE_LANGUAGE":
        language = "hi-IN" if "hindi" in text.lower() else "en-US"
        return {"intent": intent, "assistant": state, "language": language, "response": respond(f"I will speak in {'Hindi' if language == 'hi-IN' else 'English'}.", "CHANGE_LANGUAGE", 30)}
    if intent in {"START_MONITORING", "STOP_MONITORING", "PAUSE_MONITORING", "RESUME_MONITORING"}:
        labels = {
            "START_MONITORING": "I am watching the path.",
            "STOP_MONITORING": "Monitoring stopped.",
            "PAUSE_MONITORING": "Paused. I will stay quiet until you resume.",
            "RESUME_MONITORING": "I am watching again.",
        }
        return {"intent": intent, "assistant": state, "response": respond(labels[intent], intent, 40)}
    if intent == "SCAN":
        return {"intent": intent, "assistant": state, "response": respond("Taking a quick look.", "SCAN", 40), "scan": True}
    if intent in {"REPEAT"}:
        return {"intent": intent, "assistant": state, "response": response_manager.repeat()}
    if intent in {"STOP_SPEAKING", "STOP"}:
        return {"intent": intent, "assistant": state, "response": response_manager.stop()}
    if intent == "LOCATE":
        objects = world_state.snapshot()["objects"]
        target = next((obj for obj in objects if obj["name"] in text.lower()), None)
        if target:
            message = f"I see the {target['name']} {_position(target)}, {_distance(target)}."
        else:
            message = "I do not see that clearly right now."
        return {"intent": intent, "assistant": state, "response": respond(message, "LOCATE", 75)}
    if intent in {"PATH", "PATH_STATUS"}:
        world = world_state.snapshot()
        if world["path_status"] == "blocked":
            hazard = world.get("active_hazard")
            objects = world.get("objects", [])
            blocker = next((obj for obj in objects if obj.get("id") == hazard), None)
            if blocker:
                message = f"The path looks blocked by a {blocker['name']} {_position(blocker)}."
            else:
                message = "The path looks blocked."
        else:
            message = "The path ahead looks open right now."
        return {"intent": intent, "assistant": state, "response": respond(message, "PATH", 75)}
    if intent == "READ":
        return {"intent": intent, "assistant": state, "requires_frame": True, "response": respond("Hold the text steady. I will read it now.", "READ_PROMPT", 65)}
    if intent == "CURRENCY":
        return {"intent": intent, "assistant": state, "requires_frame": True, "currency": True, "response": respond("Hold the note steady. I will check the currency now.", "CURRENCY_PROMPT", 65)}
    if intent in {"SCENE", "DESCRIBE"}:
        result = rich_workflow.run("SCENE", world_state.snapshot())
        return {"intent": intent, "assistant": state, "rich_source": result["source"], "response": respond(result["text"], "SCENE", 50)}
    if intent == "HELP":
        return {"intent": intent, "assistant": state, "response": respond("You can say start monitoring, stop monitoring, read this, describe my surroundings, where is the door, is the path clear, mute, repeat, or stop speaking.", "HELP", 30)}
    return {"intent": intent, "assistant": state, "response": respond("I missed that. Try a short command, or say help.", "UNKNOWN", 30)}
