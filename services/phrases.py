"""Local deterministic text cache for critical responses; no LLM is involved."""
from __future__ import annotations

from .safety import SafetyEvent

CRITICAL_PHRASES = {
    "stop": "Stop.",
    "left": "Obstacle on your left.",
    "right": "Obstacle on your right.",
    "ahead": "Obstacle ahead.",
    "clear": "Path clear.",
    "emergency": "Emergency detected. Please pay attention.",
    "emergency_exit": "Emergency exit ahead.",
    "wait": "Please wait.",
}


def phrase_for(event: SafetyEvent) -> str:
    if event.type == "EMERGENCY_DETECTED":
        return CRITICAL_PHRASES["emergency"]
    if event.type == "PATH_CLEARED":
        return CRITICAL_PHRASES["clear"]
    if event.type == "PATH_BLOCKED":
        if event.name:
            return f"{event.name.capitalize()} is in your path."
        return "Path ahead is blocked."
    if event.type in {"OBSTACLE_APPROACHING", "OBSTACLE_ENTERED_PATH"}:
        if event.name and event.direction == "center":
            return f"{event.name.capitalize()} ahead."
        if event.name and event.direction in {"left", "right"}:
            return f"{event.name.capitalize()} on your {event.direction}."
        if event.direction in {"left", "right"}:
            return CRITICAL_PHRASES[event.direction]
        return CRITICAL_PHRASES["ahead"]
    if event.direction in {"left", "right"}:
        return CRITICAL_PHRASES[event.direction]
    return CRITICAL_PHRASES["ahead"]
