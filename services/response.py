"""The sole authority that turns safety events into speech requests."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any, Literal

from django.conf import settings

from .phrases import phrase_for
from .safety import SafetyEvent

Action = Literal["SPEAK", "INTERRUPT", "QUEUE", "DROP"]


@dataclass(frozen=True)
class ResponseRequest:
    text: str
    priority: int
    event_type: str
    object_id: int | None
    timestamp: int


class ResponseManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._current: ResponseRequest | None = None
        self._queue: list[ResponseRequest] = []
        self._last_important: ResponseRequest | None = None
        self._alert_history: dict[tuple[int | None, str], int] = {}

    @staticmethod
    def _public(action: Action, request: ResponseRequest | None) -> dict[str, Any]:
        return {"action": action, "request": asdict(request) if request else None}

    def _discard_stale(self, now: int) -> None:
        """Never let an old browser utterance block a current safety alert."""
        if self._current is not None and now - self._current.timestamp > settings.RESPONSE_MAX_AGE_MS:
            self._current = None
        self._queue = [
            request for request in self._queue
            if now - request.timestamp <= settings.RESPONSE_MAX_AGE_MS
        ]

    def submit(self, event: SafetyEvent) -> dict[str, Any]:
        request = ResponseRequest(phrase_for(event), event.priority, event.type, event.object_id, event.timestamp)
        return self.submit_request(request)

    def submit_request(self, request: ResponseRequest, suppress: bool = True) -> dict[str, Any]:
        with self._lock:
            self._discard_stale(request.timestamp)
            self._alert_history = {
                key: seen for key, seen in self._alert_history.items()
                if request.timestamp - seen <= settings.ALERT_COOLDOWN_MS
            }
            key = (request.object_id, request.event_type)
            previous = self._alert_history.get(key)
            if suppress and request.priority < 100 and previous is not None and request.timestamp - previous < settings.ALERT_COOLDOWN_MS:
                return self._public("DROP", request)
            self._alert_history[key] = request.timestamp
            self._last_important = request
            if self._current is None:
                self._current = request
                return self._public("SPEAK", request)
            if request.priority > self._current.priority:
                self._current = request
                # An interrupted safety response must not later release stale,
                # lower-priority narration.
                self._queue = [queued for queued in self._queue if queued.priority >= request.priority]
                return self._public("INTERRUPT", request)
            if len(self._queue) >= settings.RESPONSE_QUEUE_LIMIT:
                return self._public("DROP", request)
            self._queue.append(request)
            return self._public("QUEUE", request)

    def complete(self, timestamp: int | None = None) -> dict[str, Any]:
        with self._lock:
            if timestamp is not None:
                self._discard_stale(timestamp)
            # A cancelled browser utterance can emit ``onend`` after a newer
            # interrupt.  It must not complete that newer response.
            if timestamp is not None and (self._current is None or self._current.timestamp != timestamp):
                return self._public("DROP", None)
            self._current = None
            if not self._queue:
                return self._public("DROP", None)
            next_request = self._queue.pop(0)
            self._current = next_request
            return self._public("SPEAK", next_request)

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._current = None
            self._queue.clear()
            return self._public("DROP", None)

    def repeat(self) -> dict[str, Any]:
        with self._lock:
            if self._last_important is None:
                return self._public("DROP", None)
            self._current = self._last_important
            return self._public("INTERRUPT", self._last_important)

    def submit_emergency(self) -> dict[str, Any]:
        timestamp = int(time.time() * 1000)
        return self.submit(SafetyEvent("EMERGENCY_DETECTED", 100, None, None, None, "critical", timestamp))


response_manager = ResponseManager()
