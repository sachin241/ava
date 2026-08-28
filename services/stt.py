"""Local Vosk speech-to-text adapter, deliberately independent from camera work."""
from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import BinaryIO

from django.conf import settings


class SttUnavailableError(RuntimeError):
    pass


class SttAudioError(ValueError):
    pass


class SttService:
    def transcribe(self, upload: BinaryIO) -> str:
        try:
            from vosk import KaldiRecognizer, Model
        except ImportError as error:
            raise SttUnavailableError("Vosk is unavailable. Install requirements and a local Vosk model.") from error
        model_path = Path(settings.VOSK_MODEL_PATH)
        if not model_path.is_dir():
            raise SttUnavailableError(f"Local Vosk model not found at {model_path}.")
        try:
            audio = wave.open(upload, "rb")
            if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
                raise SttAudioError("Audio must be mono 16-bit WAV.")
            recognizer = KaldiRecognizer(Model(str(model_path)), audio.getframerate())
            while chunk := audio.readframes(4000):
                recognizer.AcceptWaveform(chunk)
            return str(json.loads(recognizer.FinalResult()).get("text", "")).strip()
        except SttAudioError:
            raise
        except Exception as error:
            raise SttAudioError("The recorded audio could not be transcribed.") from error


stt_service = SttService()
