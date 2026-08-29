"""Deterministic assistant session state; the only writer of assistant state."""
from __future__ import annotations

from threading import RLock
from typing import Literal

AssistantState = Literal["IDLE", "LISTENING", "PROCESSING", "MONITORING", "SPEAKING", "PAUSED", "EMERGENCY", "ERROR"]


class AssistantController:
    def __init__(self) -> None:
        self._lock = RLock()
        self._state: AssistantState = "IDLE"
        self._muted = False

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {"state": self._state, "muted": self._muted}

    def handle(self, intent: str) -> dict[str, object]:
        with self._lock:
            if intent == "START_MONITORING": self._state = "MONITORING"
            elif intent == "STOP_MONITORING": self._state = "IDLE"
            elif intent == "PAUSE_MONITORING": self._state = "PAUSED"
            elif intent == "RESUME_MONITORING": self._state = "MONITORING"
            elif intent == "SOS": self._state = "EMERGENCY"
            elif intent == "MUTE": self._muted = True
            elif intent == "UNMUTE": self._muted = False
            return self.snapshot()

    def set_state(self, state: AssistantState) -> dict[str, object]:
        with self._lock:
            self._state = state
            return {"state": self._state, "muted": self._muted}

    def listening(self) -> dict[str, object]:
        return self.set_state("LISTENING")

    def processing(self) -> dict[str, object]:
        return self.set_state("PROCESSING")

    def speaking(self) -> dict[str, object]:
        return self.set_state("SPEAKING")

    def error(self) -> dict[str, object]:
        return self.set_state("ERROR")


assistant_controller = AssistantController()
