# Implemented and tested

- Django project foundation with Django templates and static assets.
- Accessible AVA page renders with live-camera area, readiness statuses, detection area, and controls.
- Health endpoint and multipart image detection API contract.
- Automated template, health, and mocked detection-contract tests.
- Real YOLO model loading and per-frame inference through the Django detection endpoint. Final-pass verification used the included corridor demo: chair detected on three consecutive requests; cold inference was 2139.5 ms and the next two warm inferences were 77.7 ms and 79.2 ms (end-to-end request times 5344.3 ms, 144.5 ms, and 145.7 ms).
- Stable object IDs are assigned by the bounded tracker from live detections and remained consistent (`[1, 2, 3, 4, 5]`) for two consecutive sample-image observations.
- Shared bounded World State with track history, configurable expiration, duplicate suppression, relative direction/proximity, and motion classification.
- Twenty-eight automated tests passed: FAR to MEDIUM to NEAR, LEFT to CENTER, stationary/moving/approaching transitions, stable track ID, expiry, latest-frame replacement/drop semantics, safety transitions, priority, response interruption, queue release, STOP, REPEAT, intent classification, interaction routing, OCR cleanup, LangGraph fallback, fact-contract filtering, and LLM-response validation.
- `GET /api/health/` exposes processed-frame count, server FPS, and active-track count.
- Deterministic Safety Engine and configurable center-path overlap. Its tests verified stationary hazard suppression, approaching-object escalation to priority 95, and emergency priority 100.
- Central Response Manager tested for SPEAK, INTERRUPT, DROP cooldown behavior, STOP, and REPEAT. The HTTP emergency flow returned priority-100 SPEAK; STOP cleared it; REPEAT returned INTERRUPT.
- Local critical phrase text cache and API response endpoints for completion, STOP, REPEAT, and local SOS/emergency requests. No external emergency service is contacted.
- On-demand OCR and local-STT service adapters with bounded OCR retries, confidence/text cleanup, mono-WAV input validation, and safe 503 responses when local engines/models are unavailable. Python adapters were installed and their missing Tesseract/Vosk-model responses were verified.
- Deterministic Intent Engine and interaction router. Automated coverage verifies LOCATE, PATH, READ, SCENE, REPEAT, STOP intent recognition, World State-backed LOCATE routing, OCR-to-Response-Manager routing, and mocked STT-to-PATH routing.
- Accessible interaction controls: READ, ASK AVA, REPEAT, STOP, and SOS; current listening, speaking, message, and system-state outputs. ASK AVA records a short mono WAV command for the local backend.
- Optional LangGraph rich workflow for SCENE requests only; deterministic World State context summaries; Ollama fact-only adapter; and conservative LLM output validation with automatic fallback. LangGraph installation and deterministic SCENE fallback were tested.
- Browser English/Hindi speech-language selection and a local Hindi critical-phrase cache. This is separate from safety decision-making and Ollama.
- Camera-failure and repeatable-demo fallback: **USE DEMO** loads `demo/corridor-chair-door.png` into the same transient browser capture and normal detection/OCR endpoints; it does not introduce a mock perception path.
- Mobile media support: AVA requests the back camera with a compatible `facingMode` preference, falls back to the default camera, provides a front/back switch control, releases old camera tracks on switch, supports WebKit audio contexts, and explains the HTTPS requirement for phone camera/microphone access.
- Response completion is correlated to the spoken request timestamp, so an `onend` from a cancelled utterance cannot release or clear a newer emergency response. Queued responses are bounded and stale responses expire.

## Not yet verified in this environment

- Browser camera/microphone permissions and real camera capture (requires an interactive browser and physical device).
- Sustained real-camera FPS and browser-side dropped-frame telemetry (requires an interactive browser and physical device).
- Continuous browser scan controls and their live display of browser FPS, server FPS, inference time, and dropped-frame count.
- Browser SpeechSynthesis playback, cancellation, queued playback, and repeat through a real browser/audio device.
- Real OCR recognition/performance (Tesseract executable is not installed in this environment).
- Real STT recognition/performance (no local Vosk model is present in this environment).
- Ollama synthesis against a running local server and its real response latency.
- Hindi critical-phrase playback on this machine's browser and a compatible local Hindi voice.
- Browser camera FPS, browser-side dropped frames, state/event/alert timing under a real camera, and TTS startup latency (all require an interactive browser and physical devices).
