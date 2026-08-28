"""Relative, image-space interpretation of tracked detections."""
from __future__ import annotations

from typing import Literal

Direction = Literal["left", "center", "right"]
Proximity = Literal["far", "medium", "near"]


def direction_for_bbox(bbox: list[float], frame_width: int) -> Direction:
    center_x = (bbox[0] + bbox[2]) / 2
    ratio = center_x / max(frame_width, 1)
    if ratio < 0.33:
        return "left"
    if ratio <= 0.66:
        return "center"
    return "right"


def proximity_for_bbox(bbox: list[float], frame_width: int, frame_height: int) -> Proximity:
    """Return apparent proximity from image coverage, never a physical distance."""
    width = max(0.0, bbox[2] - bbox[0])
    height = max(0.0, bbox[3] - bbox[1])
    coverage = (width * height) / max(frame_width * frame_height, 1)
    if coverage < 0.05:
        return "far"
    if coverage < 0.20:
        return "medium"
    return "near"


def bbox_center(bbox: list[float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


def bbox_area(bbox: list[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])
