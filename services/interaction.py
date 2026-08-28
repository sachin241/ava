"""Routes interaction results through ResponseManager; it never speaks directly."""
from __future__ import annotations

import time
from typing import Any

from .intent import classify
from .response import ResponseRequest, response_manager
from .state import world_state
from .workflow import rich_workflow


def respond(text: str, event_type: str, priority: int = 50) -> dict[str, Any]:
    request = ResponseRequest(text, priority, event_type, None, int(time.time() * 1000))
    return response_manager.submit_request(request, suppress=False)


def route(text: str) -> dict[str, Any]:
    intent = classify(text)
    if intent == "REPEAT":
        return {"intent": intent, "response": response_manager.repeat()}
    if intent == "STOP":
        return {"intent": intent, "response": response_manager.stop()}
    if intent == "LOCATE":
        objects = world_state.snapshot()["objects"]
        target = next((obj for obj in objects if obj["name"] in text.lower()), None)
        if target:
            direction = "ahead" if target["direction"] == "center" else f"on your {target['direction']}"
            proximity = target.get("proximity", "unknown")
            message = f"{target['name'].capitalize()} is {direction}, {proximity}."
        else:
            message = "I cannot currently locate that object."
        return {"intent": intent, "response": respond(message, "LOCATE", 75)}
    if intent == "PATH":
        state = world_state.snapshot()
        if state["path_status"] == "blocked":
            hazard = state.get("active_hazard")
            message = "The path is blocked." if hazard is None else f"The path is blocked by object {hazard}."
        else:
            message = "The path appears clear."
        return {"intent": intent, "response": respond(message, "PATH", 75)}
    if intent == "READ":
        return {"intent": intent, "requires_frame": True, "response": respond("Please hold the text steady. Reading the current frame.", "READ_PROMPT", 65)}
    if intent == "SCENE":
        result = rich_workflow.run(intent, world_state.snapshot())
        return {"intent": intent, "rich_source": result["source"], "response": respond(result["text"], "SCENE", 50)}
    if intent == "HELP":
        return {"intent": intent, "response": respond("You can say: where is the door, is the path clear, read this, repeat, or stop.", "HELP", 30)}
    return {"intent": intent, "response": respond("I did not understand. Say help to hear available commands.", "UNKNOWN", 30)}
