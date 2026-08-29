"""On-demand local OCR. It never runs inside the camera perception loop."""
from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import BinaryIO

from django.conf import settings


class OcrUnavailableError(RuntimeError):
    pass


class OcrImageError(ValueError):
    pass


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float
    attempts: int
    elapsed_ms: float


def _clean(text: str) -> str:
    return " ".join(text.replace("\x0c", " ").split())


class OcrService:
    def read(self, upload: BinaryIO) -> OcrResult:
        try:
            import pytesseract
            from PIL import Image, ImageOps, ImageFilter
        except ImportError as error:
            raise OcrUnavailableError("OCR dependencies are unavailable. Install requirements and local Tesseract OCR.") from error
        try:
            image = Image.open(io.BytesIO(upload.read())).convert("L")
        except Exception as error:
            raise OcrImageError("The uploaded read frame is not a valid image.") from error
        started = time.perf_counter()
        best_text, best_confidence = "", 0.0
        # Signs on a phone camera often occupy only a small region. Include a
        # focused center crop and a thresholded upscale while retaining the
        # full frame as the first candidate.
        enlarged = ImageOps.autocontrast(image).resize((image.width * 2, image.height * 2))
        left, top = int(image.width * .1), int(image.height * .1)
        right, bottom = int(image.width * .9), int(image.height * .9)
        focused = ImageOps.autocontrast(image.crop((left, top, right, bottom))).resize((image.width * 3, image.height * 3))
        thresholded = focused.filter(ImageFilter.SHARPEN).point(lambda pixel: 255 if pixel > 160 else 0)
        variants = [image, focused, enlarged, thresholded]
        max_attempts = max(2, min(len(variants), settings.OCR_MAX_ATTEMPTS))
        for attempt, candidate in enumerate(variants[:max_attempts], start=1):
            try:
                data = pytesseract.image_to_data(candidate, config="--psm 11", output_type=pytesseract.Output.DICT)
            except Exception as error:
                raise OcrUnavailableError(f"Local Tesseract OCR is unavailable: {error}") from error
            words = [(word, float(confidence)) for word, confidence in zip(data["text"], data["conf"]) if word.strip() and float(confidence) >= 0]
            text = _clean(" ".join(word for word, _ in words))
            confidence = sum(confidence for _, confidence in words) / len(words) if words else 0.0
            if confidence > best_confidence:
                best_text, best_confidence = text, confidence
            if best_text and best_confidence >= settings.OCR_MIN_CONFIDENCE:
                return OcrResult(best_text, round(best_confidence, 1), attempt, round((time.perf_counter() - started) * 1000, 1))
        if not best_text:
            best_text = "I could not read text clearly. Please hold the sign steady and try again."
        return OcrResult(best_text, round(best_confidence, 1), max_attempts, round((time.perf_counter() - started) * 1000, 1))


ocr_service = OcrService()
