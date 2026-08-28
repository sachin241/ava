"""Small HTTP surface for AVA's perception layer."""
from __future__ import annotations

import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from services.yolo import InvalidImageError, ModelUnavailableError, yolo_service
from services.state import world_state
from services.safety import SafetyEngine
from services.response import response_manager
from services.ocr import OcrImageError, OcrUnavailableError, ocr_service
from services.stt import SttAudioError, SttUnavailableError, stt_service
from services.interaction import respond, route

logger = logging.getLogger(__name__)
safety_engine = SafetyEngine()


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "yolo": yolo_service.status(), "tracking": world_state.telemetry(), "rich": {"langgraph": True, "ollama_enabled": settings.OLLAMA_ENABLED, "ollama_model": settings.OLLAMA_MODEL}})


@api_view(["POST"])
def detect(request):
    image = request.FILES.get("image")
    if image is None:
        return Response({"error": "Upload a camera frame using the 'image' field."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        detections, inference_ms, frame_size = yolo_service.detect(image)
    except InvalidImageError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except ModelUnavailableError as error:
        logger.warning("YOLO detection unavailable: %s", error)
        return Response({"error": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    world = world_state.update(detections, frame_size)
    events, summary = safety_engine.evaluate(world["objects"], world["timestamp"])
    responses = [response_manager.submit(event) for event in sorted(events, key=lambda item: item.priority, reverse=True)]
    accepted = next((decision for decision in responses if decision["action"] != "DROP"), None)
    world = world_state.apply_safety(summary, accepted["request"] if accepted else None)
    return Response({"detections": detections, "inference_ms": inference_ms, "world_state": world, "tracking": world_state.telemetry(), "safety": {"events": [event.public() for event in events], **summary}, "responses": responses})


@api_view(["POST"])
def complete_response(request):
    timestamp = request.data.get("timestamp")
    try:
        timestamp = int(timestamp) if timestamp is not None else None
    except (TypeError, ValueError):
        return Response({"error": "timestamp must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
    return Response(response_manager.complete(timestamp))


@api_view(["POST"])
def stop_response(request):
    return Response(response_manager.stop())


@api_view(["POST"])
def repeat_response(request):
    return Response(response_manager.repeat())


@api_view(["POST"])
def emergency(request):
    return Response({"response": response_manager.submit_emergency()})


@api_view(["POST"])
def read(request):
    image = request.FILES.get("image")
    if image is None:
        return Response({"error": "Upload the current camera frame using the 'image' field."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = ocr_service.read(image)
    except OcrImageError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except OcrUnavailableError as error:
        return Response({"error": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"ocr": {"text": result.text, "confidence": result.confidence, "attempts": result.attempts, "elapsed_ms": result.elapsed_ms}, "intent": "READ", "response": respond(result.text, "OCR", 65)})


@api_view(["POST"])
def transcribe(request):
    audio = request.FILES.get("audio")
    if audio is None:
        return Response({"error": "Upload a mono 16-bit WAV recording using the 'audio' field."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        transcript = stt_service.transcribe(audio)
    except SttAudioError as error:
        return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except SttUnavailableError as error:
        return Response({"error": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if not transcript:
        return Response({"transcript": "", **route("help")})
    return Response({"transcript": transcript, **route(transcript)})
