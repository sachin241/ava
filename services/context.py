"""Deterministic scene summaries derived only from verified World State."""
from __future__ import annotations

from typing import Any

NAVIGATION_OBJECTS = {"door", "exit", "stairs", "stair", "sign"}
OBSTACLE_OBJECTS = {"chair", "table", "bench", "barrier", "debris", "bicycle"}


def verified_facts(state: dict[str, Any]) -> dict[str, Any]:
    """The only fact contract passed to optional rich reasoning services."""
    return {
        "objects": [
            {key: obj[key] for key in ("name", "direction", "proximity", "motion") if key in obj}
            for obj in state.get("objects", [])
        ],
        "path_status": state.get("path_status", "unknown"),
        "system_state": state.get("system_state", "monitoring"),
    }


def _position(obj: dict[str, Any]) -> str:
    direction = obj.get("direction", "center")
    if direction == "center":
        return "ahead"
    return f"to your {direction}"


def _distance(obj: dict[str, Any]) -> str:
    proximity = obj.get("proximity", "unknown")
    return {
        "near": "close",
        "medium": "a short distance away",
        "far": "farther away",
    }.get(proximity, "at an unclear distance")


def _is_salient(obj: dict[str, Any]) -> bool:
    name = str(obj.get("name", "")).lower()
    if name in NAVIGATION_OBJECTS:
        return True
    if obj.get("proximity") == "near":
        return True
    if obj.get("direction") == "center" and obj.get("proximity") == "medium":
        return True
    if name in OBSTACLE_OBJECTS and obj.get("proximity") in {"near", "medium"}:
        return True
    if obj.get("motion") == "approaching":
        return True
    return False


def _object_phrase(obj: dict[str, Any]) -> str:
    name = str(obj.get("name", "object")).replace("_", " ")
    return f"a {name} {_position(obj)}, {_distance(obj)}"


def deterministic_summary(state: dict[str, Any]) -> str:
    facts = verified_facts(state)
    path = facts["path_status"]
    if path == "clear":
        sentence = "The path ahead looks open."
    elif path == "blocked":
        sentence = "Hold on, the path ahead looks blocked."
    else:
        sentence = "I am still getting a clear read on the path."
    objects = facts["objects"]
    if not objects:
        return sentence

    people = [obj for obj in objects if obj.get("name") == "person"]
    salient = [obj for obj in objects if obj.get("name") != "person" and _is_salient(obj)]

    details: list[str] = []
    if people:
        if len(people) == 1:
            details.append(f"I can see a person {_position(people[0])}, {_distance(people[0])}.")
        else:
            near_people = [obj for obj in people if obj.get("proximity") in {"near", "medium"}]
            if near_people:
                details.append("There are people nearby, so move gently.")
            else:
                details.append("There are people in view, but they look farther away.")
    if salient:
        phrases = [_object_phrase(obj) for obj in salient[:2]]
        if len(phrases) == 1:
            details.append(f"I also notice {phrases[0]}.")
        else:
            details.append(f"I also notice {phrases[0]} and {phrases[1]}.")

    if not details:
        return f"{sentence} Nothing nearby needs attention right now."
    return f"{sentence} {' '.join(details)}"
