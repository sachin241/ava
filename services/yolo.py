"""YOLO perception service, intentionally independent of Django views."""
from __future__ import annotations

import io
import logging
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any, BinaryIO

from django.conf import settings

logger = logging.getLogger(__name__)


class ModelUnavailableError(RuntimeError):
    """Raised when the local YOLO engine cannot be loaded."""


class InvalidImageError(ValueError):
    """Raised when an upload is not a usable image."""


class YoloService:
    def __init__(self) -> None:
        self._model: Any | None = None
        self._load_error: str | None = None
        self._lock = Lock()
        self._inference_lock = Lock()

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from ultralytics import YOLO

                self._model = YOLO(settings.YOLO_MODEL)
                self._load_error = None
                logger.info("Loaded YOLO model %s", settings.YOLO_MODEL)
                return self._model
            except Exception as error:  # dependency, weights, and device errors become an API response
                self._load_error = str(error)
                raise ModelUnavailableError(f"YOLO model is unavailable: {error}") from error

    def status(self) -> dict[str, Any]:
        return {"model": settings.YOLO_MODEL, "loaded": self._model is not None, "error": self._load_error}

    @staticmethod
    def _read_image(upload: BinaryIO) -> Any:
        try:
            from PIL import Image

            data = upload.read()
            image = Image.open(io.BytesIO(data)).convert("RGB")
            if image.width == 0 or image.height == 0:
                raise ValueError("Image has no pixels")
            return image
        except Exception as error:
            raise InvalidImageError("The uploaded frame is not a valid image.") from error

    def detect(self, upload: BinaryIO) -> tuple[list[dict[str, Any]], float, tuple[int, int]]:
        image = self._read_image(upload)
        model = self._load_model()
        started = time.perf_counter()
        with self._inference_lock:
            results = model.predict(image, conf=settings.YOLO_CONFIDENCE, imgsz=settings.YOLO_IMAGE_SIZE, verbose=False)
        inference_ms = round((time.perf_counter() - started) * 1000, 1)
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        detections: list[dict[str, Any]] = []
        for result in results:
            names = result.names
            for box in result.boxes:
                confidence = float(box.conf[0])
                if confidence < settings.YOLO_CONFIDENCE:
                    continue
                class_id = int(box.cls[0])
                detections.append({
                    "track_id": None,
                    "label": str(names[class_id]),
                    "confidence": round(confidence, 4),
                    "bbox": [round(float(value), 1) for value in box.xyxy[0].tolist()],
                    "timestamp": timestamp,
                })
        logger.info("YOLO inference completed in %.1f ms (%d detections)", inference_ms, len(detections))
        return detections, inference_ms, image.size


yolo_service = YoloService()
