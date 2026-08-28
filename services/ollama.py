"""Optional local Ollama adapter. Input is restricted to verified structured facts."""
from __future__ import annotations

import json
from typing import Any

import requests
from django.conf import settings


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaService:
    def describe(self, facts: dict[str, Any]) -> str:
        if not settings.OLLAMA_ENABLED:
            raise OllamaUnavailableError("Ollama is disabled.")
        prompt = (
            "Summarise only these verified AVA facts in one concise sentence. "
            "Do not invent objects, locations, distances, hazards, or directions. "
            "Do not issue safety advice. Facts JSON: " + json.dumps(facts, separators=(",", ":"))
        )
        try:
            response = requests.post(
                f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            value = str(response.json().get("response", "")).strip()
            if not value:
                raise ValueError("Ollama returned no response")
            return value
        except Exception as error:
            raise OllamaUnavailableError(str(error)) from error


ollama_service = OllamaService()
