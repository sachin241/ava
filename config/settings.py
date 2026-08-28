"""Settings for the local-first AVA prototype."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "ava-development-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
# ``demo`` is intentionally served as static, read-only input.  It is never an
# upload destination and its frames follow the normal detection/OCR requests.
STATICFILES_DIRS = [BASE_DIR / "static", BASE_DIR / "demo"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

YOLO_MODEL = os.getenv("YOLO_MODEL", "yolo11n.pt")
YOLO_CONFIDENCE = float(os.getenv("YOLO_CONFIDENCE", "0.25"))
YOLO_IMAGE_SIZE = int(os.getenv("YOLO_IMAGE_SIZE", "832"))
TRACK_MAX_AGE_MS = int(os.getenv("TRACK_MAX_AGE_MS", "2000"))
TRACK_HISTORY_SIZE = int(os.getenv("TRACK_HISTORY_SIZE", "12"))
TRACK_IOU_THRESHOLD = float(os.getenv("TRACK_IOU_THRESHOLD", "0.30"))
TRACK_DUPLICATE_IOU_THRESHOLD = float(os.getenv("TRACK_DUPLICATE_IOU_THRESHOLD", "0.75"))
MAX_ACTIVE_TRACKS = int(os.getenv("MAX_ACTIVE_TRACKS", "64"))
PATH_LEFT_RATIO = float(os.getenv("PATH_LEFT_RATIO", "0.26"))
PATH_RIGHT_RATIO = float(os.getenv("PATH_RIGHT_RATIO", "0.74"))
PATH_MIN_OVERLAP_RATIO = float(os.getenv("PATH_MIN_OVERLAP_RATIO", "0.30"))
SAFETY_MIN_CONFIDENCE = float(os.getenv("SAFETY_MIN_CONFIDENCE", "0.55"))
SAFETY_BLOCK_CONFIRM_FRAMES = int(os.getenv("SAFETY_BLOCK_CONFIRM_FRAMES", "3"))
SAFETY_CLEAR_CONFIRM_FRAMES = int(os.getenv("SAFETY_CLEAR_CONFIRM_FRAMES", "3"))
ALERT_COOLDOWN_MS = int(os.getenv("ALERT_COOLDOWN_MS", "5000"))
RESPONSE_QUEUE_LIMIT = int(os.getenv("RESPONSE_QUEUE_LIMIT", "3"))
RESPONSE_MAX_AGE_MS = int(os.getenv("RESPONSE_MAX_AGE_MS", "15000"))
EMERGENCY_LABELS = {label.strip().lower() for label in os.getenv("EMERGENCY_LABELS", "fire,smoke").split(",") if label.strip()}
OCR_MIN_CONFIDENCE = float(os.getenv("OCR_MIN_CONFIDENCE", "55"))
OCR_MAX_ATTEMPTS = int(os.getenv("OCR_MAX_ATTEMPTS", "2"))
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", str(BASE_DIR / "models" / "vosk-model"))
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "false").lower() in {"1", "true", "yes"}
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "4"))
RICH_RESPONSE_MAX_CHARS = int(os.getenv("RICH_RESPONSE_MAX_CHARS", "280"))
