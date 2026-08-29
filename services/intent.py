"""Deterministic command matching for AVA's bounded command set."""
from __future__ import annotations

from typing import Literal
import re

Intent = Literal["START_MONITORING", "STOP_MONITORING", "PAUSE_MONITORING", "RESUME_MONITORING", "SCAN", "LOCATE", "PATH", "PATH_STATUS", "READ", "DESCRIBE", "SCENE", "REPEAT", "STOP_SPEAKING", "STOP", "MUTE", "UNMUTE", "CHANGE_LANGUAGE", "SOS", "HELP", "UNKNOWN"]


def classify(text: str) -> Intent:
    value = re.sub(r"[^\w\s?]", "", text.lower()).strip()
    if any(word in value for word in ("emergency", "sos", "help me")):
        return "SOS"
    if any(word in value for word in ("change language", "switch language", "speak hindi", "speak english")):
        return "CHANGE_LANGUAGE"
    if any(word in value for word in ("unmute", "sound on", "enable speech")):
        return "UNMUTE"
    if any(word in value for word in ("mute", "sound off")):
        return "MUTE"
    if any(word in value for word in ("stop monitoring", "end monitoring", "disable monitoring")):
        return "STOP_MONITORING"
    if any(word in value for word in ("start monitoring", "start scan", "begin monitoring", "monitor")):
        return "START_MONITORING"
    if any(word in value for word in ("pause", "pause monitoring")):
        return "PAUSE_MONITORING"
    if any(word in value for word in ("resume", "resume monitoring", "continue monitoring")):
        return "RESUME_MONITORING"
    if value in {"scan", "scan now", "look"}:
        return "SCAN"
    if any(word in value for word in ("repeat", "say that again")):
        return "REPEAT"
    if value == "stop":
        return "STOP"
    if value in {"be quiet", "silence", "stop speaking", "stop talking"}:
        return "STOP_SPEAKING"
    if any(word in value for word in ("read", "sign", "text")):
        return "READ"
    if any(word in value for word in ("where is", "locate", "find")):
        return "LOCATE"
    if value in {"path status", "path state"}:
        return "PATH_STATUS"
    if any(word in value for word in ("path", "way clear", "clear ahead")):
        return "PATH"
    if any(word in value for word in ("describe", "surroundings", "scene")):
        return "SCENE"
    if any(word in value for word in ("help", "what can", "commands")):
        return "HELP"
    return "UNKNOWN"
