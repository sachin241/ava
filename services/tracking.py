"""Bounded object association and temporal motion classification."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal

from django.conf import settings

from .spatial import bbox_area, bbox_center

Motion = Literal["stationary", "moving", "approaching", "moving_away"]


def iou(first: list[float], second: list[float]) -> float:
    left, top = max(first[0], second[0]), max(first[1], second[1])
    right, bottom = min(first[2], second[2]), min(first[3], second[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = bbox_area(first) + bbox_area(second) - intersection
    return intersection / union if union else 0.0


def contains(first: list[float], second: list[float]) -> bool:
    """Whether one box fully contains the other (common for an approaching object)."""
    return (
        (first[0] <= second[0] <= second[2] <= first[2] and first[1] <= second[1] <= second[3] <= first[3])
        or (second[0] <= first[0] <= first[2] <= second[2] and second[1] <= first[1] <= first[3] <= second[3])
    )


@dataclass
class Observation:
    bbox: list[float]
    timestamp: int


@dataclass
class ActiveTrack:
    id: int
    label: str
    confidence: float
    bbox: list[float]
    last_seen: int
    observations_seen: int = 0
    history: deque[Observation] = field(default_factory=lambda: deque(maxlen=settings.TRACK_HISTORY_SIZE))
    motion: Motion = "stationary"

    def observe(self, detection: dict[str, Any], timestamp: int, frame_size: tuple[int, int]) -> None:
        previous = self.history[-1] if self.history else None
        self.bbox = detection["bbox"]
        self.confidence = detection["confidence"]
        self.last_seen = timestamp
        self.observations_seen += 1
        self.history.append(Observation(self.bbox, timestamp))
        if previous is not None:
            self.motion = classify_motion(previous.bbox, self.bbox, frame_size)


def classify_motion(previous: list[float], current: list[float], frame_size: tuple[int, int]) -> Motion:
    old_area, new_area = bbox_area(previous), bbox_area(current)
    old_center, new_center = bbox_center(previous), bbox_center(current)
    diagonal = max((frame_size[0] ** 2 + frame_size[1] ** 2) ** 0.5, 1)
    moved = ((new_center[0] - old_center[0]) ** 2 + (new_center[1] - old_center[1]) ** 2) ** 0.5 / diagonal
    scale_change = (new_area - old_area) / max(old_area, 1)
    if scale_change >= 0.15:
        return "approaching"
    if scale_change <= -0.15:
        return "moving_away"
    if moved >= 0.02:
        return "moving"
    return "stationary"


class ObjectTracker:
    """Keeps only active structured observations, never image frames."""

    def __init__(self) -> None:
        self._tracks: dict[int, ActiveTrack] = {}
        self._next_id = 1

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def _new_id(self) -> int:
        while self._next_id in self._tracks:
            self._next_id += 1
        value = self._next_id
        self._next_id += 1
        return value

    def _suppress_duplicates(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept: list[dict[str, Any]] = []
        for detection in sorted(detections, key=lambda item: item["confidence"], reverse=True):
            if any(detection["label"] == existing["label"] and iou(detection["bbox"], existing["bbox"]) >= settings.TRACK_DUPLICATE_IOU_THRESHOLD for existing in kept):
                continue
            kept.append(detection)
        return kept

    def _associate(self, detection: dict[str, Any]) -> int:
        requested_id = detection.get("track_id")
        if requested_id is not None and int(requested_id) in self._tracks:
            return int(requested_id)
        candidates = [track for track in self._tracks.values() if track.label == detection["label"]]
        best = max(candidates, key=lambda track: iou(track.bbox, detection["bbox"]), default=None)
        if best is not None and (iou(best.bbox, detection["bbox"]) >= settings.TRACK_IOU_THRESHOLD or contains(best.bbox, detection["bbox"])):
            return best.id
        # Preserve a new ByteTrack id if supplied, unless it collides with an active different object.
        if requested_id is not None and int(requested_id) not in self._tracks:
            return int(requested_id)
        return self._new_id()

    def update(self, detections: list[dict[str, Any]], timestamp: int, frame_size: tuple[int, int]) -> list[ActiveTrack]:
        self.expire(timestamp)
        updated: list[ActiveTrack] = []
        # A malformed or unusually busy frame must not make structured World
        # State unbounded.  The highest-confidence unique detections win.
        for detection in self._suppress_duplicates(detections)[:settings.MAX_ACTIVE_TRACKS]:
            track_id = self._associate(detection)
            track = self._tracks.get(track_id)
            if track is None:
                track = ActiveTrack(id=track_id, label=detection["label"], confidence=detection["confidence"], bbox=detection["bbox"], last_seen=timestamp)
                self._tracks[track_id] = track
            track.observe(detection, timestamp, frame_size)
            detection["track_id"] = track_id
            updated.append(track)
        return updated

    def expire(self, timestamp: int) -> list[int]:
        expired = [track_id for track_id, track in self._tracks.items() if timestamp - track.last_seen > settings.TRACK_MAX_AGE_MS]
        for track_id in expired:
            del self._tracks[track_id]
        return expired

    @property
    def active_count(self) -> int:
        return len(self._tracks)

    @property
    def active_tracks(self) -> list[ActiveTrack]:
        return list(self._tracks.values())
