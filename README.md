# AVA — AI Visual Assist

AVA is a local-first Django prototype for visual assistance. It implements a deterministic fast safety path plus an optional, on-demand rich context path.

## Architecture

```text
Django template + vanilla JavaScript
  → browser camera: latest frame only
  → POST /api/vision/detect/
  → YOLO detector + bounded tracker
  → World State
  → deterministic safety, priority, and response request
```

`services/yolo.py` owns model loading and per-frame YOLO inference. `services/tracking.py` keeps short object histories, duplicate suppression, and fallback association. `services/state.py` maintains one shared, structured World State. No raw frames are retained by backend services.

`services/safety.py` evaluates configurable center-path overlap and relative risk without an LLM. `services/response.py` is the only backend authority that turns events into `SPEAK`, `INTERRUPT`, `QUEUE`, or `DROP` requests. The browser's `speech.js` is the only frontend module that calls SpeechSynthesis.

On-demand interaction services are independent from the camera loop: `services/ocr.py` reads an explicit current-frame request and `services/stt.py` transcribes a short mono WAV command with a local Vosk model. `services/intent.py` routes deterministic commands through `services/interaction.py`, which always submits a response request rather than speaking directly.

`services/workflow.py` invokes LangGraph only for rich interaction requests such as SCENE. It passes Ollama only the fact contract produced by `services/context.py`; `services/validation.py` rejects unsupported objects, incorrect directions, incompatible path claims, empty output, and overlong output. A rejected, disabled, or unavailable Ollama response falls back to the deterministic context template before Response Manager submission.

The browser scan loop sends only the newest current frame. When inference is still running, scan ticks are counted as dropped rather than added to a queue.

If camera access fails, or for a repeatable walkthrough, choose **USE DEMO**. The prepared corridor image is drawn into the same transient canvas and sent through the normal image detection and OCR HTTP endpoints; it is not a separate mock pipeline.

## Features included

- Accessible Django-rendered AVA UI with camera preview, scan controls, and status output.
- YOLO detector, confidence filtering, labels, boxes, timestamps, stable IDs from the bounded tracker, and inference-time logging.
- Track direction (`left`, `center`, `right`), apparent proximity (`far`, `medium`, `near`), and motion trend.
- Shared bounded World State, configurable expiry, and frame/FPS/latency/drop telemetry.
- Deterministic path safety events, priority 75–100, per-object cooldown suppression, escalation, and local emergency response requests.
- STOP and REPEAT response controls. Speech uses browser SpeechSynthesis when supported.
- READ captures the current frame on demand and performs bounded local Tesseract OCR retries with confidence-based text cleanup.
- ASK AVA records a short browser WAV clip for local Vosk STT. Deterministic intents: LOCATE, PATH, READ, SCENE, REPEAT, STOP, and HELP.
- SCENE uses an optional LangGraph workflow and Ollama synthesis of verified facts only, with deterministic fallback.
- Browser TTS offers English and Hindi selection; Hindi critical phrases are cached locally in the speech module and never wait for Ollama.
- `GET /api/health/` and `POST /api/vision/detect/` using Django REST Framework.

Detection contract:

```json
{
  "track_id": 17,
  "label": "chair",
  "confidence": 0.91,
  "bbox": [420.0, 250.0, 650.0, 620.0],
  "timestamp": 0
}
```

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`, grant permissions, and choose **START SCAN**. On a phone, camera and microphone permissions require HTTPS (or the phone's own localhost); do not open the development server through a plain `http://` LAN address. After opening AVA on mobile, tap **CONNECT CAMERA** so the permission prompt starts from a user gesture, then tap **ENABLE AVA VOICE** for hands-free commands or **ASK AVA** for a short recorded command. Use **SWITCH TO FRONT/BACK** to change camera and **USE DEMO** if hardware access is unavailable. Ultralytics downloads `yolo11n.pt` on first use if it is absent. See `.env.example` for `YOLO_*` and `TRACK_*` environment settings.

### Local OCR and STT setup

The Python adapters are installed by `requirements.txt`, but their local runtimes are intentionally separate:

- Install Tesseract OCR and make the `tesseract` executable available on `PATH` for READ.
- Download and unpack a compatible Vosk model into `models/vosk-model`, or set `VOSK_MODEL_PATH` to its directory, for ASK AVA.

On Windows, the extracted directory must contain Vosk files such as `am`, `conf`, and `graph` directly under `D:\ava\models\vosk-model` (avoid an extra nested folder). For example:

```powershell
New-Item -ItemType Directory -Force models\vosk-model
# Download a model from https://alphacephei.com/vosk/models and extract it here.
Test-Path models\vosk-model\am
```

Alternatively set an absolute path in `.env`:

```env
VOSK_MODEL_PATH=D:\\ava\\models\\vosk-model
```

If you do not want to install a Vosk model, use **ENABLE AVA VOICE** in a browser that supports SpeechRecognition; ASK AVA's recorded-WAV path specifically requires the local model.

Until configured, AVA responds with a clear HTTP 503 and does not send images or audio to an external service.

### Optional Ollama rich context

Ollama is disabled by default. To enable it, run a local Ollama server with the configured model and set `OLLAMA_ENABLED=true`. It is used only after a SCENE request; safety, detection, tracking, and emergency handling remain LLM-free. If Ollama is unavailable or its response fails validation, AVA speaks the deterministic World State summary instead.

## Verify

```powershell
python manage.py check
python manage.py test
```

## Demo walkthrough

1. Open AVA and choose **USE DEMO** (or allow the camera and choose **START SCAN**).
2. Start scanning. The included corridor scene is real YOLO input; it was verified to detect its chair on this machine.
3. Use **READ** after installing Tesseract to scan the visible library and exit signs. Ask **WHERE IS THE DOOR?** only after a door is present in World State; this particular prepared image is not guaranteed to produce a YOLO door detection.
4. Use **SOS** to exercise the priority-100, cached emergency phrase. Change Speech language to Hindi to exercise the local Hindi critical phrase selection.
5. Set `OLLAMA_ENABLED=false` (the default), then ask **Describe my surroundings**. AVA uses the deterministic summary and safety scanning remains active.

## Limitations

- Browser camera operation requires a real device, user permission, and a secure deployment context (localhost is supported for development).
- Tracking is image-space and can lose identities after occlusion, major scene changes, or longer missed detections than `TRACK_MAX_AGE_MS`.
- Proximity is image coverage, not physical distance; direction is frame-relative, not user-relative.
- Browser speech output depends on the browser/platform voice and has not been validated with a physical audio device in this environment.
- Ollama is optional and has not been tested against a running local server in this environment.
- Tesseract OCR and a local Vosk model are required before READ and ASK AVA can complete real recognition. OCR accuracy depends on text size, focus, glare, and camera motion.
- Hindi playback requires a compatible local browser/platform Hindi voice; that actual-device path has not been tested here.
- AVA is a prototype and not a mobility or safety device.
