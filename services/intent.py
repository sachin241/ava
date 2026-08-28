"""Deterministic command matching for AVA's bounded command set."""
from __future__ import annotations

from typing import Literal

Intent = Literal["LOCATE", "PATH", "READ", "SCENE", "REPEAT", "STOP", "HELP", "UNKNOWN"]


def classify(text: str) -> Intent:
    value = text.lower().strip()
    if any(word in value for word in ("repeat", "say that again")):
        return "REPEAT"
    if any(word in value for word in ("stop", "be quiet", "silence")):
        return "STOP"
    if any(word in value for word in ("read", "sign", "text")):
        return "READ"
    if any(word in value for word in ("where is", "locate", "find")):
        return "LOCATE"
    if any(word in value for word in ("path", "way clear", "clear ahead")):
        return "PATH"
    if any(word in value for word in ("describe", "surroundings", "scene")):
        return "SCENE"
    if any(word in value for word in ("help", "what can", "commands")):
        return "HELP"
    return "UNKNOWN"
