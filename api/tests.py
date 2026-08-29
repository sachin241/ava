from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image


class ApiTests(TestCase):
    def image_upload(self):
        buffer = BytesIO()
        Image.new("RGB", (20, 20), "white").save(buffer, format="JPEG")
        return SimpleUploadedFile("frame.jpg", buffer.getvalue(), content_type="image/jpeg")

    def test_health_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("api.views.yolo_service.detect")
    def test_detection_contract(self, detect):
        detect.return_value = ([{"track_id": None, "label": "chair", "confidence": 0.9, "bbox": [1, 2, 3, 4], "timestamp": 1}], 12.3, (20, 20))
        response = self.client.post("/api/vision/detect/", {"image": self.image_upload()})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["detections"][0]["label"], "chair")
        self.assertEqual(result["inference_ms"], 12.3)
        self.assertIn("world_state", result)

    @patch("api.views.ocr_service.read")
    def test_read_uses_response_manager_route(self, read):
        from services.ocr import OcrResult
        read.return_value = OcrResult("Emergency Exit", 91.0, 1, 12.0)
        response = self.client.post("/api/interaction/read/", {"image": self.image_upload()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "READ")
        self.assertEqual(response.json()["ocr"]["text"], "Emergency Exit")

    @patch("api.views.recognise_indian_currency_image")
    def test_currency_endpoint_recognises_indian_note_text(self, recognise):
        from services.currency import CurrencyResult
        recognise.return_value = CurrencyResult(500, "high", "This looks like an Indian 500 rupee note.", ["test"], note_detected=True)
        response = self.client.post("/api/interaction/currency/", {"image": self.image_upload()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "CURRENCY")
        self.assertEqual(response.json()["currency"]["denomination"], 500)

    @patch("api.views.stt_service.transcribe", return_value="Is the path clear?")
    def test_transcribe_routes_path_request(self, transcribe):
        audio = SimpleUploadedFile("command.wav", b"audio", content_type="audio/wav")
        response = self.client.post("/api/interaction/transcribe/", {"audio": audio})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transcript"], "Is the path clear?")
        self.assertEqual(response.json()["intent"], "PATH")
