"""Deterministic path-risk evaluation. This module never performs speech."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from django.conf import settings

SafetyLevel = Literal["low", "high", "critical"]


@dataclass(frozen=True)
class SafetyEvent:
    type: str
    priority: int
    object_id: int | None
    name: str | None
    direction: str | None
    level: SafetyLevel | None
    timestamp: int

    def public(self) -> dict[str, Any]:
        return asdict(self)


def path_overlap_for_bbox(bbox: list[float], frame_width: int) -> bool:
    """Whether a substantial portion of an object crosses the conservative center path."""
    path_left = frame_width * settings.PATH_LEFT_RATIO
    path_right = frame_width * settings.PATH_RIGHT_RATIO
    overlap = max(0.0, min(bbox[2], path_right) - max(bbox[0], path_left))
    object_width = max(1.0, bbox[2] - bbox[0])
    return overlap / object_width >= settings.PATH_MIN_OVERLAP_RATIO


class SafetyEngine:
    def __init__(self) -> None:
        self._previous_levels: dict[int, SafetyLevel] = {}
        self._path_blocked = False
        self._blocked_streak = 0
        self._clear_streak = 0

    @staticmethod
    def _is_relevant(obj: dict[str, Any]) -> bool:
        if obj["confidence"] >= settings.SAFETY_MIN_CONFIDENCE:
            return True
        return obj.get("seen_frames", 0) >= settings.SAFETY_BLOCK_CONFIRM_FRAMES and obj["path_overlap"]

    @staticmethod
    def _level(obj: dict[str, Any]) -> SafetyLevel:
        if not obj["path_overlap"]:
            return "low"
        if obj["proximity"] == "near" and obj["motion"] == "approaching":
            return "critical"
        if obj["proximity"] == "near":
            return "high"
        if obj["proximity"] == "medium" and obj["motion"] == "approaching":
            return "high"
        if obj["proximity"] == "medium" and obj["motion"] == "stationary" and obj.get("seen_frames", 0) >= settings.SAFETY_BLOCK_CONFIRM_FRAMES:
            return "high"
        return "low"

    def evaluate(self, objects: list[dict[str, Any]], timestamp: int, dangers: list[dict[str, Any]] | None = None) -> tuple[list[SafetyEvent], dict[str, Any]]:
        events: list[SafetyEvent] = []
        levels: dict[int, SafetyLevel] = {}
        hazards: list[tuple[dict[str, Any], SafetyLevel]] = []
        for obj in objects:
            object_id = obj["id"]
            if not self._is_relevant(obj):
                levels[object_id] = "low"
                continue
            if obj["name"].lower() in settings.EMERGENCY_LABELS:
                events.append(SafetyEvent("EMERGENCY_DETECTED", 100, object_id, obj["name"], obj["direction"], "critical", timestamp))
                levels[object_id] = "critical"
                hazards.append((obj, "critical"))
                continue
            level = self._level(obj)
            levels[object_id] = level
            if level == "low":
                continue
            hazards.append((obj, level))
            previous = self._previous_levels.get(object_id, "low")
            if level == "critical" and previous != "critical":
                events.append(SafetyEvent("OBSTACLE_APPROACHING", 95, object_id, obj["name"], obj["direction"], level, timestamp))

        # Semantic danger facts (for example OCR signs) enter the same safety
        # event stream; the classifier itself never speaks or sets priority.
        for danger in dangers or []:
            if not danger.get("active", True) or float(danger.get("confidence", 0)) < 0.55:
                continue
            severity = danger.get("severity", "medium")
            if severity == "critical":
                priority = 100 if danger.get("type") in {"EMERGENCY", "SOS", "FIRE", "EVACUATION"} else 95
                level: SafetyLevel = "critical"
            elif severity == "high":
                priority, level = 90, "high"
            else:
                priority, level = 75, "low"
            if priority >= 90:
                events.append(SafetyEvent("DANGER_DETECTED", priority, None, danger.get("type"), danger.get("direction"), level, timestamp))
        blocked_candidate = bool(hazards)
        if blocked_candidate:
            self._blocked_streak += 1
            self._clear_streak = 0
        else:
            self._clear_streak += 1
            self._blocked_streak = 0

        blocked = self._path_blocked
        confirmed_block = blocked_candidate and self._blocked_streak >= settings.SAFETY_BLOCK_CONFIRM_FRAMES
        confirmed_clear = not blocked_candidate and self._path_blocked and self._clear_streak >= settings.SAFETY_CLEAR_CONFIRM_FRAMES

        if confirmed_block and not self._path_blocked:
            lead, level = max(hazards, key=lambda item: 95 if item[1] == "critical" else 90)
            if level != "critical" and self._previous_levels.get(lead["id"], "low") == "low":
                events.append(SafetyEvent("OBSTACLE_ENTERED_PATH", 90, lead["id"], lead["name"], lead["direction"], level, timestamp))
            events.append(SafetyEvent("PATH_BLOCKED", 95 if level == "critical" else 90, lead["id"], lead["name"], lead["direction"], level, timestamp))
            blocked = True
        elif blocked and hazards:
            lead, level = max(hazards, key=lambda item: 95 if item[1] == "critical" else 90)
            previous = self._previous_levels.get(lead["id"], "low")
            if level == "critical" and previous != "critical":
                events.append(SafetyEvent("OBSTACLE_APPROACHING", 95, lead["id"], lead["name"], lead["direction"], level, timestamp))

        if confirmed_clear:
            events.append(SafetyEvent("PATH_CLEARED", 75, None, None, None, None, timestamp))
            blocked = False

        self._previous_levels = levels
        self._path_blocked = blocked
        lead = max(hazards, key=lambda item: 2 if item[1] == "critical" else 1, default=(None, "low"))[0]
        semantic_levels = [danger.get("severity") for danger in (dangers or []) if danger.get("active", True) and float(danger.get("confidence", 0)) >= 0.55]
        semantic_critical = "critical" in semantic_levels
        semantic_high = "high" in semantic_levels
        summary = {
            "system_state": "critical" if any(level == "critical" for _, level in hazards) or semantic_critical else "caution" if blocked or semantic_high else "clear",
            "path_status": "blocked" if blocked else "clear",
            "active_hazard": lead["id"] if lead else None,
            "dangers": [danger for danger in (dangers or []) if danger.get("active", True)],
        }
        return events, summary
