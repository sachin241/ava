"""Deterministic scene summaries derived only from verified World State."""
from __future__ import annotations

from typing import Any


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


def deterministic_summary(state: dict[str, Any]) -> str:
    facts = verified_facts(state)
    path = facts["path_status"]
    if path == "clear":
        sentence = "The path ahead appears clear."
    elif path == "blocked":
        sentence = "The path ahead is blocked."
    else:
        sentence = "I do not have enough information about the path yet."
    objects = facts["objects"][:3]
    if not objects:
        return sentence
    def description(obj: dict[str, Any]) -> str:
        name = obj["name"].capitalize()
        position = "ahead" if obj["direction"] == "center" else f"on your {obj['direction']}"
        return f"{name} {position}, {obj.get('proximity', 'unknown')}"

    descriptions = [description(obj) for obj in objects]
    if len(descriptions) == 1:
        return f"{sentence} {descriptions[0]}."
    if len(descriptions) == 2:
        listing = " and ".join(descriptions)
    else:
        listing = ", ".join(descriptions[:-1]) + ", and " + descriptions[-1]
    return f"{sentence} {listing}."
