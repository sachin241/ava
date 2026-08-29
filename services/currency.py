"""Fast Indian currency recognition from image, note crop, and OCR evidence."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from threading import Lock
from typing import Any, BinaryIO

from django.conf import settings
from PIL import Image, ImageOps


INDIAN_NOTE_DENOMINATIONS = (10, 20, 50, 100, 200, 500, 2000)
_DENOMINATION_LABELS = {str(value): value for value in INDIAN_NOTE_DENOMINATIONS}

_WORD_DENOMINATIONS = {
    "ten": 10,
    "twenty": 20,
    "fifty": 50,
    "hundred": 100,
    "one hundred": 100,
    "two hundred": 200,
    "five hundred": 500,
    "two thousand": 2000,
}

_INDIAN_CURRENCY_MARKERS = (
    "reserve bank",
    "bank of india",
    "bharatiya reserve bank",
    "mahatma gandhi",
    "rupee",
    "rupees",
    "inr",
)


@dataclass(frozen=True)
class CurrencyResult:
    denomination: int | None
    confidence: str
    message: str
    evidence: list[str]
    note_detected: bool = False
    ocr_text: str = ""
    ocr_confidence: float = 0.0


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _rank(confidence: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(confidence, 0)


def recognise_indian_currency(text: str, ocr_confidence: float = 0.0) -> CurrencyResult:
    value = _normalise(text)
    if not value:
        return CurrencyResult(None, "low", "I could not read enough detail to identify Indian currency.", [], ocr_confidence=ocr_confidence)

    evidence: list[str] = []
    markers = [marker for marker in _INDIAN_CURRENCY_MARKERS if marker in value]
    if markers:
        evidence.append("Indian currency text")

    scores = {denomination: 0 for denomination in INDIAN_NOTE_DENOMINATIONS}
    tokens = re.findall(r"\d{1,4}", value)
    for token in tokens:
        try:
            number = int(token)
        except ValueError:
            continue
        if number in scores:
            scores[number] += 2
            evidence.append(str(number))

    for phrase, denomination in _WORD_DENOMINATIONS.items():
        if phrase in value:
            scores[denomination] += 2
            evidence.append(phrase)

    best_denomination, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score == 0:
        return CurrencyResult(None, "low", "I could not identify an Indian currency denomination.", evidence, ocr_confidence=ocr_confidence)

    competing = [amount for amount, amount_score in scores.items() if amount != best_denomination and amount_score == best_score and amount_score > 0]
    if competing:
        return CurrencyResult(None, "low", "I saw possible currency text, but the denomination is unclear.", evidence[:6], ocr_confidence=ocr_confidence)

    confidence_score = best_score + (1 if markers else 0) + (1 if ocr_confidence >= 55 else 0)
    confidence = "high" if confidence_score >= 4 else "medium" if confidence_score >= 3 else "low"
    if confidence == "low":
        message = f"This may be an Indian {best_denomination} rupee note, but I am not confident."
    else:
        message = f"This looks like an Indian {best_denomination} rupee note."
    return CurrencyResult(best_denomination, confidence, message, evidence[:6], ocr_confidence=ocr_confidence)


def _confidence(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.52:
        return "medium"
    return "low"


def _message(denomination: int | None, confidence: str, note_detected: bool) -> str:
    if denomination and confidence != "low":
        return f"This looks like an Indian {denomination} rupee note."
    if note_detected:
        return "I can see a note or bill, but I cannot identify the Indian rupee amount clearly."
    return "I do not see Indian currency clearly."


def _dominant_note_colour(hue: float, saturation: float, value: float) -> tuple[int | None, str, float]:
    if saturation < 42 and 70 <= value <= 210:
        return 500, "grey note colour", 0.58
    if 88 <= hue <= 112 and saturation >= 45:
        return 50, "blue note colour", 0.65
    if 124 <= hue <= 158 and saturation >= 35:
        return 100, "lavender note colour", 0.62
    if (158 <= hue <= 179 or hue <= 5) and saturation >= 45:
        return 2000, "magenta note colour", 0.62
    if 18 <= hue <= 34 and saturation >= 70 and value >= 115:
        return 200, "yellow-orange note colour", 0.64
    if 35 <= hue <= 58 and saturation >= 45:
        return 20, "green-yellow note colour", 0.56
    if 5 <= hue <= 24 and 40 <= saturation < 95 and value < 165:
        return 10, "brown-orange note colour", 0.52
    return None, "unclear note colour", 0.0


def _expand_bbox(bbox: list[float], width: int, height: int, padding: float = 0.14) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    box_width = right - left
    box_height = bottom - top
    pad_x = box_width * padding
    pad_y = box_height * padding
    x1 = max(0, int(left - pad_x))
    y1 = max(0, int(top - pad_y))
    x2 = min(width, int(right + pad_x))
    y2 = min(height, int(bottom + pad_y))
    if x2 <= x1:
        x2 = min(width, x1 + 1)
    if y2 <= y1:
        y2 = min(height, y1 + 1)
    return x1, y1, x2, y2


def _prepare_ocr_image(image: Image.Image) -> Image.Image:
    width, height = image.size
    scale = 2 if max(width, height) < 1100 else 1
    if scale > 1:
        image = image.resize((width * scale, height * scale), Image.Resampling.LANCZOS)
    return ImageOps.autocontrast(image.convert("L"))


def _crop_to_bbox(image: Image.Image, bbox: list[float] | None) -> Image.Image:
    if not bbox:
        return image
    return image.crop(_expand_bbox(bbox, image.width, image.height))


def _visual_recognition(image: Image.Image) -> CurrencyResult:
    try:
        import cv2
        import numpy as np
    except ImportError:
        return CurrencyResult(None, "low", "Currency image recognition dependencies are unavailable.", [])

    rgb = np.array(image.convert("RGB"))
    height, width = rgb.shape[:2]
    scale = min(1.0, 900 / max(width, height))
    if scale < 1.0:
        rgb = cv2.resize(rgb, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
        height, width = rgb.shape[:2]

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    colour_mask = cv2.bitwise_and(cv2.inRange(saturation, 28, 255), cv2.inRange(value, 35, 245))
    grey_mask = cv2.bitwise_and(cv2.inRange(saturation, 0, 55), cv2.inRange(value, 65, 220))
    mask = cv2.bitwise_or(colour_mask, grey_mask)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    frame_area = width * height
    best: tuple[float, object, tuple[float, float], float] | None = None
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < frame_area * 0.035:
            continue
        rect = cv2.minAreaRect(contour)
        rect_width, rect_height = rect[1]
        short, long = sorted((rect_width, rect_height))
        if short <= 0:
            continue
        aspect = long / short
        if not 1.7 <= aspect <= 3.2:
            continue
        rectangularity = min(1.0, area / max(rect_width * rect_height, 1))
        aspect_score = max(0.0, 1.0 - abs(aspect - 2.25) / 1.0)
        area_score = min(1.0, area / (frame_area * 0.22))
        score = 0.45 * rectangularity + 0.35 * aspect_score + 0.20 * area_score
        if best is None or score > best[0]:
            best = (score, contour, rect[1], aspect)

    if best is None:
        return CurrencyResult(None, "low", _message(None, "low", False), [])

    score, contour, _, aspect = best
    note_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(note_mask, [contour], -1, 255, thickness=-1)
    pixels = hsv[note_mask == 255]
    if len(pixels) == 0:
        return CurrencyResult(None, "low", _message(None, "low", True), ["note-shaped object"])

    hue, saturation_median, value_median = [float(number) for number in np.median(pixels, axis=0)]
    denomination, colour_evidence, colour_score = _dominant_note_colour(hue, saturation_median, value_median)
    combined_score = (score * 0.55) + (colour_score * 0.45)
    confidence = _confidence(combined_score)
    evidence = ["note-shaped object", f"aspect {aspect:.2f}", colour_evidence]
    return CurrencyResult(denomination, confidence, _message(denomination, confidence, True), evidence, note_detected=True)


class CurrencyService:
    def __init__(self) -> None:
        self._model: Any | None = None
        self._load_error: str | None = None
        self._load_lock = Lock()
        self._inference_lock = Lock()

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            try:
                from ultralytics import YOLO

                self._model = YOLO(settings.CURRENCY_MODEL)
                self._load_error = None
                return self._model
            except Exception as error:
                self._load_error = str(error)
                raise RuntimeError(f"Currency model is unavailable: {error}") from error

    def status(self) -> dict[str, Any]:
        return {"model": settings.CURRENCY_MODEL, "loaded": self._model is not None, "error": self._load_error}

    @staticmethod
    def _prepare_image(upload: BinaryIO) -> Image.Image:
        image = Image.open(io.BytesIO(upload.read()))
        return ImageOps.exif_transpose(image).convert("RGB")

    def _model_recognition(self, image: Image.Image) -> tuple[list[float] | None, list[str]]:
        try:
            model = self._load_model()
        except RuntimeError:
            return None, []

        with self._inference_lock:
            results = model.predict(
                image,
                conf=settings.CURRENCY_MODEL_CONFIDENCE,
                imgsz=settings.CURRENCY_IMAGE_SIZE,
                verbose=False,
                max_det=1,
            )

        best: tuple[float, list[float], list[str]] | None = None
        for result in results:
            for box in getattr(result, "boxes", []) or []:
                confidence = float(box.conf[0])
                if confidence < settings.CURRENCY_MODEL_CONFIDENCE:
                    continue
                coords = box.xyxy[0]
                if hasattr(coords, "tolist"):
                    coords = coords.tolist()
                bbox = [round(float(value), 1) for value in coords]
                evidence = [f"currency model confidence {round(confidence * 100):.0f}%"]
                if best is None or confidence > best[0]:
                    best = (confidence, bbox, evidence)
        if best is None:
            return None, []
        return best[1], best[2]

    @staticmethod
    def _ocr_candidates(image: Image.Image) -> list[tuple[CurrencyResult, str]]:
        try:
            import pytesseract
        except Exception:
            return []

        candidates: list[tuple[CurrencyResult, str]] = []
        for config in ("--psm 6", "--psm 11"):
            text = pytesseract.image_to_string(_prepare_ocr_image(image), config=config)
            result = recognise_indian_currency(text)
            if result.denomination:
                candidates.append((result, text))
        return candidates

    def recognise_image(self, upload: BinaryIO) -> CurrencyResult:
        image = self._prepare_image(upload)
        bbox, model_evidence = self._model_recognition(image)
        note_crop = _crop_to_bbox(image, bbox)

        ocr_text = ""
        ocr_candidates = self._ocr_candidates(note_crop)
        if not ocr_candidates and note_crop is not image:
            ocr_candidates = self._ocr_candidates(image)

        if ocr_candidates:
            ocr_result, ocr_text = max(ocr_candidates, key=lambda item: (_rank(item[0].confidence), len(item[0].evidence), len(item[1])))
            evidence = [*model_evidence, *ocr_result.evidence][:8]
            confidence = ocr_result.confidence
            return CurrencyResult(
                ocr_result.denomination,
                confidence,
                ocr_result.message,
                evidence,
                note_detected=True,
                ocr_text=ocr_text,
                ocr_confidence=ocr_result.ocr_confidence,
            )

        visual_result = _visual_recognition(note_crop)
        if bbox and visual_result.note_detected:
            return CurrencyResult(
                None,
                "low",
                "I can see an Indian note, but I cannot read the denomination clearly.",
                [*model_evidence, *visual_result.evidence][:8],
                note_detected=True,
                ocr_text=ocr_text,
                ocr_confidence=0.0,
            )

        return CurrencyResult(
            None,
            "low",
            "I do not see Indian currency clearly.",
            model_evidence,
            note_detected=False,
            ocr_text=ocr_text,
            ocr_confidence=0.0,
        )


currency_service = CurrencyService()


def recognise_indian_currency_image(upload: BinaryIO) -> CurrencyResult:
    return currency_service.recognise_image(upload)
