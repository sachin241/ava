"""Routes interaction results through ResponseManager; it never speaks directly."""
from __future__ import annotations

import time
from typing import Any

from .intent import classify
from .response import ResponseRequest, response_manager
from .state import world_state
from .workflow import rich_workflow
from .controller import assistant_controller


def respond(text: str, event_type: str, priority: int = 50) -> dict[str, Any]:
    request = ResponseRequest(text, priority, event_type, None, int(time.time() * 1000))
    return response_manager.submit_request(request, suppress=False)


def route(text: str) -> dict[str, Any]:
    intent = classify(text)
    state = assistant_controller.handle(intent)
    if intent == "MUTE":
        response_manager.set_muted(True)
        return {"intent": intent, "assistant": state, "response": {"action": "DROP", "request": None}}
    if intent == "UNMUTE":
        response_manager.set_muted(False)
        return {"intent": intent, "assistant": state, "response": respond("Normal speech restored.", "UNMUTE", 30)}
    if intent == "SOS":
        return {"intent": intent, "assistant": state, "response": response_manager.submit_emergency()}
    if intent == "CHANGE_LANGUAGE":
        language = "hi-IN" if "hindi" in text.lower() else "en-US"
        return {"intent": intent, "assistant": state, "language": language, "response": respond(f"Speech language changed to {'Hindi' if language == 'hi-IN' else 'English'}.", "CHANGE_LANGUAGE", 30)}
    if intent in {"START_MONITORING", "STOP_MONITORING", "PAUSE_MONITORING", "RESUME_MONITORING"}:
        labels = {"START_MONITORING": "Monitoring started.", "STOP_MONITORING": "Monitoring stopped.", "PAUSE_MONITORING": "Monitoring paused.", "RESUME_MONITORING": "Monitoring resumed."}
        return {"intent": intent, "assistant": state, "response": respond(labels[intent], intent, 40)}
    if intent == "SCAN":
        return {"intent": intent, "assistant": state, "response": respond("Scanning now.", "SCAN", 40), "scan": True}
    if intent in {"REPEAT"}:
        return {"intent": intent, "assistant": state, "response": response_manager.repeat()}
    if intent in {"STOP_SPEAKING", "STOP"}:
        return {"intent": intent, "assistant": state, "response": response_manager.stop()}
    if intent == "LOCATE":
        objects = world_state.snapshot()["objects"]
        target = next((obj for obj in objects if obj["name"] in text.lower()), None)
        if target:
            direction = "ahead" if target["direction"] == "center" else f"on your {target['direction']}"
            proximity = target.get("proximity", "unknown")
            message = f"{target['name'].capitalize()} is {direction}, {proximity}."
        else:
            message = "I cannot currently locate that object."
        return {"intent": intent, "assistant": state, "response": respond(message, "LOCATE", 75)}
    if intent in {"PATH", "PATH_STATUS"}:
        world = world_state.snapshot()
        if world["path_status"] == "blocked":
            hazard = world.get("active_hazard")
            message = "The path is blocked." if hazard is None else f"The path is blocked by object {hazard}."
        else:
            message = "The path appears clear."
        return {"intent": intent, "assistant": state, "response": respond(message, "PATH", 75)}
    if intent == "READ":
        return {"intent": intent, "assistant": state, "requires_frame": True, "response": respond("Please hold the text steady. Reading the current frame.", "READ_PROMPT", 65)}
    if intent in {"SCENE", "DESCRIBE"}:
        result = rich_workflow.run("SCENE", world_state.snapshot())
        return {"intent": intent, "assistant": state, "rich_source": result["source"], "response": respond(result["text"], "SCENE", 50)}
    if intent == "HELP":
        return {"intent": intent, "assistant": state, "response": respond("You can say: start monitoring, pause, resume, where is the door, is the path clear, read this, describe my surroundings, mute, repeat, or stop.", "HELP", 30)}
    return {"intent": intent, "assistant": state, "response": respond("I did not understand. Say help to hear available commands.", "UNKNOWN", 30)}
