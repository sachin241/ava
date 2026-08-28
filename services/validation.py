"""Conservative validation for optional LLM wording before it reaches speech."""
from __future__ import annotations

import re
from typing import Any

from django.conf import settings

OBJECT_VOCABULARY = {
    "person", "chair", "door", "table", "bottle", "car", "bus", "dog", "cat", "phone", "book", "backpack",
    "fire", "smoke", "stairs", "exit", "sign", "bed", "sofa", "cup", "laptop", "bicycle", "motorcycle",
}


def validate_scene_response(text: str, facts: dict[str, Any]) -> str | None:
    candidate = " ".join(text.split()).strip()
    if not candidate or len(candidate) > settings.RICH_RESPONSE_MAX_CHARS:
        return None
    words = set(re.findall(r"[a-z]+", candidate.lower()))
    known_objects = {obj["name"].lower() for obj in facts.get("objects", [])}
    if any(word in OBJECT_VOCABULARY and word not in known_objects for word in words):
        return None
    directions = {obj["direction"] for obj in facts.get("objects", [])}
    if any(word in {"left", "right", "center"} and word not in directions for word in words):
        return None
    for obj in facts.get("objects", []):
        match = re.search(rf"\b{re.escape(obj['name'].lower())}\b[^.!]*\b(left|right|center)\b", candidate.lower())
        if match and match.group(1) != obj["direction"]:
            return None
    path = facts.get("path_status")
    if ("clear" in words and path != "clear") or ("blocked" in words and path != "blocked"):
        return None
    return candidate
