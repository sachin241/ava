"""Single-slot latest-frame buffer used to document and test drop semantics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

Frame = TypeVar("Frame")


@dataclass
class FrameMetrics:
    accepted: int = 0
    dropped: int = 0


class LatestFrameBuffer(Generic[Frame]):
    """A one-item buffer: offering a newer frame discards the older pending one."""

    def __init__(self) -> None:
        self._latest: Frame | None = None
        self.metrics = FrameMetrics()

    def offer(self, frame: Frame) -> None:
        if self._latest is not None:
            self.metrics.dropped += 1
        self._latest = frame
        self.metrics.accepted += 1

    def take_latest(self) -> Frame | None:
        frame, self._latest = self._latest, None
        return frame
