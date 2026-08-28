"""Shared, bounded environmental state for AVA perception services."""
from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Any

from .spatial import direction_for_bbox, proximity_for_bbox
from .safety import path_overlap_for_bbox
from .tracking import ObjectTracker


class WorldStateEngine:
    def __init__(self) -> None:
        self._tracker = ObjectTracker()
        self._lock = Lock()
        self._completed_at: deque[int] = deque(maxlen=60)
        self._last_state: dict[str, Any] = self._empty_state()

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {"timestamp": 0, "objects": [], "text": [], "path_status": "unknown", "active_hazard": None, "user_intent": None, "last_alert": None}

    def update(self, detections: list[dict[str, Any]], frame_size: tuple[int, int], timestamp: int | None = None) -> dict[str, Any]:
        timestamp = timestamp or int(time.time() * 1000)
        with self._lock:
            self._tracker.update(detections, timestamp, frame_size)
            objects = []
            for track in self._tracker.active_tracks:
                objects.append({
                    "id": track.id,
                    "name": track.label,
                    "confidence": round(track.confidence, 4),
                    "seen_frames": track.observations_seen,
                    "direction": direction_for_bbox(track.bbox, frame_size[0]),
                    "proximity": proximity_for_bbox(track.bbox, *frame_size),
                    "motion": track.motion,
                    "path_overlap": path_overlap_for_bbox(track.bbox, frame_size[0]),
                })
            self._completed_at.append(timestamp)
            self._last_state = {"timestamp": timestamp, "objects": objects, "text": [], "path_status": "unknown", "active_hazard": None, "user_intent": None, "last_alert": None}
            return self._last_state.copy()

    def apply_safety(self, summary: dict[str, Any], last_alert: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            self._last_state.update(summary)
            self._last_state["last_alert"] = last_alert
            return self._last_state.copy()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._last_state.copy()

    def telemetry(self) -> dict[str, float | int]:
        with self._lock:
            if len(self._completed_at) < 2:
                fps = 0.0
            else:
                elapsed = self._completed_at[-1] - self._completed_at[0]
                fps = round((len(self._completed_at) - 1) * 1000 / elapsed, 2) if elapsed else 0.0
            return {"processed_frames": len(self._completed_at), "fps": fps, "active_tracks": self._tracker.active_count}


world_state = WorldStateEngine()
