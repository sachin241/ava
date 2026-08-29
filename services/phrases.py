"""Local deterministic text cache for critical responses; no LLM is involved."""
from __future__ import annotations

from .safety import SafetyEvent

CRITICAL_PHRASES = {
    "stop": "Stop.",
    "left": "Obstacle on your left.",
    "right": "Obstacle on your right.",
    "ahead": "Obstacle ahead.",
    "clear": "The path looks open again.",
    "emergency": "Emergency detected. Stay still and pay attention.",
    "emergency_exit": "Emergency exit ahead.",
    "wait": "Please wait.",
}

DANGER_PHRASES = {
    "ELECTRICAL_HAZARD": "Danger sign: high voltage.",
    "FIRE_HAZARD": "Danger sign: fire hazard.",
    "WET_FLOOR": "Careful. Wet floor sign.",
    "SLIPPERY_FLOOR": "Careful. Slippery floor sign.",
    "ROAD_WORK": "Careful. Road work sign.",
    "ROAD_CLOSURE": "Careful. Road closure sign.",
    "NO_ENTRY": "No entry sign ahead.",
    "RESTRICTED_AREA": "Restricted area sign ahead.",
    "CONSTRUCTION": "Construction warning ahead.",
    "DANGER": "Danger warning sign ahead.",
    "GENERAL_WARNING": "Warning sign ahead.",
    "UNKNOWN_HAZARD": "Warning sign ahead. I cannot read the exact hazard.",
    "OPENING_HOLE": "Careful. Opening or hole warning.",
    "EMERGENCY_EXIT": "Emergency exit sign ahead.",
    "EVACUATION": "Emergency exit sign ahead.",
    "FIRE": "Fire warning detected.",
    "SOS": "Emergency alert detected.",
    "EMERGENCY": "Emergency alert detected.",
}


def phrase_for(event: SafetyEvent) -> str:
    if event.type == "EMERGENCY_DETECTED":
        return CRITICAL_PHRASES["emergency"]
    if event.type == "DANGER_DETECTED":
        return DANGER_PHRASES.get(str(event.name or ""), "Warning sign ahead.")
    if event.type == "PATH_CLEARED":
        return CRITICAL_PHRASES["clear"]
    if event.type == "PATH_BLOCKED":
        if event.name:
            if event.direction == "center":
                return f"Careful. {event.name.capitalize()} in your path."
            if event.direction in {"left", "right"}:
                return f"Careful. {event.name.capitalize()} close on your {event.direction}."
            return f"Careful. {event.name.capitalize()} nearby."
        return "Careful. The path ahead looks blocked."
    if event.type in {"OBSTACLE_APPROACHING", "OBSTACLE_ENTERED_PATH"}:
        if event.name and event.direction == "center":
            return f"Careful. {event.name.capitalize()} ahead."
        if event.name and event.direction in {"left", "right"}:
            return f"Careful. {event.name.capitalize()} on your {event.direction}."
        if event.direction in {"left", "right"}:
            return CRITICAL_PHRASES[event.direction]
        return CRITICAL_PHRASES["ahead"]
    if event.direction in {"left", "right"}:
        return CRITICAL_PHRASES[event.direction]
    return CRITICAL_PHRASES["ahead"]
