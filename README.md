# AVA — AI Visual Assist

> **From seeing objects to understanding situations.**

AVA is a **local-first, proactive, context-aware AI assistive system** designed primarily for visually impaired users.

Instead of simply detecting objects in a camera frame and reading them aloud, AVA continuously maintains a compact understanding of the user's immediate environment, detects meaningful changes, evaluates their relevance and safety, and communicates only what the user needs to know.

The core idea is:

> **AVA forgets the frames. It remembers what changed.**

---

# 1. Project Vision

Traditional computer-vision pipelines typically look like:

```text
Camera → Detection → Result
````

AVA is designed as:

```text
Camera / Voice
      ↓
Perception
      ↓
Spatial Understanding
      ↓
World State
      ↓
Change / Event Detection
      ↓
Safety + Context
      ↓
Priority
      ↓
Response Management
      ↓
TTS
      ↓
User
```

AVA therefore focuses on the layer between:

**machine perception** and **human attention**.

The system should answer:

> **“What does this user need to know right now?”**

---

# 2. Problem Statement Alignment

The selected Problem Statement is:

**PS #4 — AI Assistive Technology for Persons with Visual or Hearing Impairments**

The problem statement describes accessibility challenges in digital and physical environments and explicitly allows teams to focus on one specific accessibility challenge.

AVA focuses on:

> **Visual environmental assistance for visually impaired users.**

Relevant PS capabilities incorporated into AVA include:

* Real-time object detection
* Text/signboard recognition
* Text-to-speech
* Speech-to-text
* Navigation/spatial assistance
* Obstacle detection
* Emergency assistance

The broader PS also mentions currency/document recognition, environmental sound alerts and accessible educational content. These remain future/stretch modules rather than the core 20-hour build.

---

# 3. Core Differentiation

AVA is **not** trying to compete with Google on general visual search, OCR or generic image understanding.

Products such as Google Lens and Google Lookout already provide strong visual understanding and accessibility functionality.

AVA's differentiation is the **interaction model and decision architecture**.

## Conventional Visual Assistance

```text
User
  ↓
Point camera
  ↓
Analyze image
  ↓
Ask question
  ↓
Receive answer
```

## AVA

```text
Environment continuously changes
              ↓
      Maintain world state
              ↓
      Detect meaningful change
              ↓
     Evaluate user relevance
              ↓
       Evaluate safety
              ↓
      Prioritize information
              ↓
        Speak only when needed
```

### Core differentiators

| Differentiator                      | AVA  |
| ----------------------------------- | ---- |
| Continuous environmental state      | Core |
| Temporal change detection           | Core |
| User-relative spatial understanding | Core |
| Attention / priority engine         | Core |
| Proactive safety alerts             | Core |
| Central speech arbitration          | Core |
| Voice-first interaction             | Core |
| LLM-independent safety path         | Core |
| Local-first operation               | Core |

The innovation is therefore primarily **system-level orchestration**, not the creation of a new object detector.

---

# 4. User Experience

AVA is designed around the visually impaired user's interaction model.

The screen is secondary.

The primary interaction is:

```text
Voice → Understanding → Spoken assistance
```

Example:

### User

> “Where is the door?”

### AVA

> “The door is on your right.”

---

### User

> “Is the path clear?”

### AVA

> “No. There is an obstacle ahead.”

---

### User

> “Read this sign.”

### AVA

> “Computer Science Laboratory.”

---

### User

> “Describe my surroundings.”

### AVA

> “You are in a corridor. The path ahead is clear and a door is on your right.”

---

# 5. Feature Set

AVA's user-facing functionality is intentionally curated rather than being a checklist of every PS feature.

## SEE

Real-time environment perception using object detection.

## LOCATE

User-relative directional assistance.

Example:

> “The door is on your right.”

## PROTECT

Obstacle detection, proximity reasoning and safety alerts.

Example:

> “Stop. Obstacle ahead.”

## READ

Text and signboard recognition through OCR.

## COMMUNICATE

Speech-to-text input and text-to-speech output.

## ASSIST

Emergency and high-priority assistance.

---

# 6. Master Architecture

```text
                         USER
                    ┌──────┴──────┐
                    │             │
                 CAMERA         VOICE
                    │             │
                    ▼             ▼
               PERCEPTION         STT
                    │             │
             ┌──────┴──────┐      │
             │             │      │
            YOLO          OCR     │
             │             │      │
             └──────┬──────┘      │
                    │             │
                    └──────┬──────┘
                           ▼
                    SPATIAL ENGINE
                           │
                           ▼
                      WORLD STATE
                           │
                    ┌──────┴──────┐
                    ▼             ▼
               CHANGE /       USER INTENT
               EVENT ENGINE        │
                    │             │
                    └──────┬──────┘
                           ▼
                    SAFETY ENGINE
                           │
                           ▼
                    PRIORITY ENGINE
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                 SPEAK           WAIT
                    │             │
                    ▼             ▼
                  TTS        QUEUE / DROP
                    │
                    ▼
                   USER
```

Optional rich reasoning path:

```text
WORLD STATE + USER INTENT
          ↓
       LANGGRAPH
          ↓
        OLLAMA
          ↓
   Natural-language response
          ↓
         TTS
```

---

# 7. Engine Architecture

AVA is best understood as a set of specialized engines.

## 7.1 Perception Engine

### Responsibility

Determine:

> **What is present?**

Primary tool:

**YOLO**

Input:

```text
camera frame
```

Output:

```text
object class
confidence
bounding box
```

Example:

```json
{
  "class": "chair",
  "confidence": 0.91,
  "bbox": [420, 250, 650, 620]
}
```

### Important boundary

YOLO does **not** decide whether something is dangerous.

---

# 8. Tracking Engine

Tracking connects detections across time.

Without tracking:

```text
Frame 1 → Chair
Frame 2 → Chair
Frame 3 → Chair
```

With tracking:

```text
Frame 1 → Chair #17
Frame 2 → Chair #17
Frame 3 → Chair #17
```

This enables:

* object identity
* motion estimation
* approach detection
* repetition suppression
* state transitions

Tracking is therefore essential for continuous assistance.

---

# 9. Spatial Engine

The Spatial Engine answers:

> **Where is the object relative to the user?**

For MVP:

```text
0–33%  → LEFT
33–66% → CENTER
66–100% → RIGHT
```

The bounding-box center is:

```python
center_x = (x1 + x2) / 2
```

Example:

```text
x = 20% → LEFT
x = 50% → CENTER
x = 82% → RIGHT
```

---

# 10. Relative Proximity

For the 20-hour MVP, AVA uses **relative proximity**, not exact physical distance.

A simple approximation:

```text
small bounding box  → FAR
medium               → MEDIUM
large                → NEAR
very large + path overlap → CRITICAL
```

This can be strengthened using temporal trends:

```text
FAR
 ↓
MEDIUM
 ↓
NEAR
 ↓
CRITICAL
```

### Important limitation

Do not claim:

> “The obstacle is exactly 1.7 metres away.”

unless a calibrated depth mechanism supports that claim.

The MVP should use:

> **relative proximity estimation**

A future version can add:

```text
YOLO
 +
Monocular depth / calibrated depth
 ↓
Improved distance estimation
```

---

# 11. World State Engine

The World State is AVA's short-term environmental memory.

Instead of storing raw video, it stores structured facts.

Example:

```json
{
  "objects": [
    {
      "id": 17,
      "name": "chair",
      "confidence": 0.91,
      "direction": "center",
      "proximity": "near",
      "motion": "approaching"
    },
    {
      "id": 21,
      "name": "door",
      "confidence": 0.94,
      "direction": "right",
      "proximity": "medium",
      "motion": "stationary"
    }
  ],
  "path_status": "blocked",
  "active_hazard": "obstacle"
}
```

### Key idea

> **Raw pixels are temporary. Context persists briefly.**

---

# 12. Frame Management

The camera may produce:

```text
24–30 FPS
```

AVA does **not** need to process every frame with every model.

Instead:

```text
CAMERA
   ↓
LATEST FRAME BUFFER
   ↓
YOLO
   ↓
TRACKER
   ↓
WORLD STATE
```

If inference falls behind:

```text
OLD FRAME → DROP
LATEST FRAME → PROCESS
```

### Never do:

```text
Camera
 ↓
Frame 1 waiting
Frame 2 waiting
Frame 3 waiting
...
Frame 500 waiting
 ↓
AI
```

That creates stale results and growing latency.

### Design principle

> **AVA forgets the frames. It remembers what changed.**

---

# 13. Change / Event Engine

The event engine compares the current state with the previous state.

```text
Previous World State
        ↓
Current World State
        ↓
Difference
        ↓
Meaningful change?
```

Possible events:

```text
OBSTACLE_ENTERED_PATH
OBSTACLE_APPROACHING
PATH_BLOCKED
PATH_CLEARED
TARGET_FOUND
NEW_IMPORTANT_TEXT
EMERGENCY_DETECTED
```

Example:

```text
F1:
chair = far

F2:
chair = medium

F3:
chair = near

F4:
chair = center + critical
```

Result:

```text
OBSTACLE_APPROACHING
```

---

# 14. Safety Engine

The Safety Engine determines:

> **Does this situation require action?**

It receives:

```text
object
+
direction
+
proximity
+
motion
+
path relationship
```

Example:

```text
Person + far + left + stationary
→ LOW

Chair + center + near + approaching
→ HIGH

Obstacle + center + critical
→ CRITICAL
```

Safety decisions are deterministic.

---

# 15. Priority Engine

Not every observation should be spoken.

Example environment:

```text
Person
Chair
Door
Bottle
Table
Exit
Plant
```

A naïve assistant:

> “Person. Chair. Door. Bottle. Table. Exit. Plant.”

AVA:

> **silence**

until something meaningful happens.

Example:

```text
Chair enters path
        ↓
PRIORITY ↑
        ↓
“Caution. Obstacle ahead.”
```

Suggested priority structure:

```text
100 → Emergency
 95 → Immediate collision
 90 → Safety warning
 75 → Navigation / direction
 65 → Important text
 50 → Scene description
 30 → General information
```

### Principle

> **Silence is also a decision.**

---

# 16. Response Manager

Only one system component should control speech.

Every other module submits a response request.

```text
EVENT / QUERY
      ↓
RESPONSE MANAGER
      ↓
PRIORITY QUEUE
```

Possible actions:

```text
INTERRUPT
QUEUE
DROP
```

Example:

Current:

> “You are in a corridor…”

New event:

```text
Obstacle detected
Priority = 95
```

Response Manager:

```text
INTERRUPT
```

AVA:

> **“Stop. Obstacle ahead.”**

This prevents speech overlap and information overload.

---

# 17. Voice Input / STT Engine

The user can provide commands verbally.

```text
Speech
 ↓
STT
 ↓
Intent
```

Core intents:

```text
SCENE
LOCATE
READ
PATH
REPEAT
HELP
STOP
```

Examples:

```text
“Where is the door?”
→ LOCATE

“Read this.”
→ READ

“Describe my surroundings.”
→ SCENE

“Is the path clear?”
→ PATH

“Repeat.”
→ REPEAT

“Stop.”
→ STOP
```

For the local STT layer, faster-whisper is the current implementation candidate.

---

# 18. OCR Engine

OCR is **on demand**, not continuously active.

```text
User:
“Read this.”
      ↓
Capture current/best frame
      ↓
OCR
      ↓
Confidence / cleanup
      ↓
TTS
```

This avoids wasting computation performing OCR on every camera frame.

PaddleOCR is the current candidate for local OCR.

---

# 19. Context Engine

The Context Engine turns structured facts into useful descriptions.

Input:

```text
person = center
door = right
chair = left
path = clear
```

Output:

> “You are in a corridor. The path ahead is clear. There is a door on your right.”

This can work through deterministic templates.

That gives us a fallback even if the LLM is unavailable.

---

# 20. LangGraph

LangGraph is **not** the perception engine.

It is used for higher-level workflow orchestration.

Example:

```text
USER QUERY
    ↓
INTENT
    ↓
LANGGRAPH
    ├── LOCATE → Spatial Engine
    ├── READ   → OCR
    ├── PATH   → Safety
    ├── SCENE  → Context / Ollama
    └── HELP   → Help
```

### Important

Do not invoke LangGraph:

```text
10–15 times per second
```

for camera perception.

Instead:

```text
continuous perception
        ↓
meaningful event/query
        ↓
LangGraph
```

This keeps the real-time path lightweight.

---

# 21. Ollama

Ollama is an **optional natural-language layer**.

### Good uses

* scene descriptions
* conversational answers
* natural-language synthesis
* contextual explanation

### Bad uses

* collision decisions
* emergency decisions
* safety severity
* object detection
* exact spatial decisions

Correct:

```text
Verified World State
        ↓
Ollama
        ↓
Natural-language response
        ↓
Validator
        ↓
TTS
```

Incorrect:

```text
Camera
 ↓
YOLO
 ↓
Ollama
 ↓
“Is this dangerous?”
```

### Hard rule

> **The LLM never becomes the safety authority.**

---

# 22. Fast Path vs Rich Path

AVA has two conceptual paths.

## FAST PATH

```text
Camera
 ↓
YOLO
 ↓
Tracker
 ↓
Spatial
 ↓
Safety
 ↓
Priority
 ↓
Cached TTS
```

Characteristics:

* local
* deterministic
* low-latency
* safety-critical

Used for:

* obstacle alerts
* collision warnings
* emergency events
* path changes

---

## RICH PATH

```text
World State
 ↓
User Intent
 ↓
LangGraph
 ↓
Ollama
 ↓
Natural Language
 ↓
TTS
```

Characteristics:

* contextual
* conversational
* optional
* slower

Used for:

* scene description
* natural-language answers
* contextual queries

---

# 23. TTS Engine

TTS is more than:

```text
text → audio
```

AVA has to decide:

```text
what
when
priority
interrupt?
queue?
drop?
language?
```

Then:

```text
Approved response
      ↓
Language Router
      ↓
TTS
      ↓
Audio Queue
      ↓
Speaker / Headphones
```

---

# 24. Local-Language TTS Strategy

The system should support a **locally executed multilingual TTS path**.

Primary experimental candidate:

**AI4Bharat Indic Parler-TTS**

For hackathon safety and latency:

```text
Critical message
      ↓
Pre-generated / cached audio
      ↓
Immediate playback
```

Dynamic message:

```text
Text
 ↓
Local TTS
 ↓
Audio
```

Critical phrases to pre-cache:

```text
“Stop. Obstacle ahead.”

“Obstacle on your left.”

“Path clear.”

“Emergency exit ahead.”

“Please wait.”
```

### Hackathon recommendation

Select the exact language for the live demo in advance and benchmark it on the actual machine.

Do not rely on automatic language switching for the critical demonstration path.

---

# 25. Continuous Runtime

A practical runtime configuration is:

```text
CAMERA
24–30 FPS

YOLO + TRACKER
~8–15 FPS target

SAFETY / EVENTS
~2–5 Hz target

OCR
ON DEMAND

STT
WHILE LISTENING

OLLAMA
ON DEMAND

TTS
EVENT / QUERY DRIVEN
```

This means:

> **The system continuously observes, but doesn't continuously execute every expensive operation.**

---

# 26. Complete Example — Obstacle

Let's walk through a complete real execution.

### Frame 1

YOLO:

```text
chair
```

Spatial:

```text
left
far
```

World State:

```text
chair #17
left
far
stationary
```

No speech.

---

### Frame 20

```text
chair #17
center
medium
```

Change:

```text
LEFT → CENTER
FAR → MEDIUM
```

Potential event:

```text
OBSTACLE_APPROACHING
```

Safety:

```text
HIGH
```

Priority:

```text
95
```

Response:

> **“Caution. Obstacle ahead.”**

---

### Frame 30

```text
chair #17
center
near
approaching
```

Priority increases.

Response Manager:

```text
INTERRUPT
```

TTS:

> **“Stop. Obstacle directly ahead.”**

---

### Frame 40

User moves away.

```text
chair
medium
left
```

World State:

```text
path = clear
```

Optional:

> **“Path clear.”**

Then silence.

---

# 27. Complete Example — Door Query

User:

> “Where is the door?”

Pipeline:

```text
VOICE
 ↓
STT
 ↓
LOCATE
 ↓
TARGET = DOOR
 ↓
WORLD STATE
 ↓
SPATIAL LOOKUP
 ↓
RIGHT
 ↓
TTS
```

Output:

> **“The door is on your right.”**

No LLM required.

---

# 28. Complete Example — Read Sign

User:

> “Read this sign.”

Pipeline:

```text
VOICE
 ↓
STT
 ↓
READ
 ↓
capture frame
 ↓
OCR
 ↓
text
 ↓
TTS
```

Output:

> **“Emergency Exit.”**

---

# 29. Complete Example — Scene Description

User:

> “Describe my surroundings.”

Pipeline:

```text
VOICE
 ↓
STT
 ↓
SCENE
 ↓
WORLD STATE
 ↓
Context Engine
 ↓
optional LangGraph
 ↓
optional Ollama
 ↓
Validator
 ↓
TTS
```

Output:

> “You are in a corridor. A door is on your right and the path ahead is clear.”

---

# 30. Emergency Path

Emergency events get the highest priority.

```text
Emergency event
      ↓
Priority = 100
      ↓
Interrupt current audio
      ↓
Cached / validated phrase
      ↓
TTS
```

The emergency path should **not** wait for:

* Ollama
* internet
* cloud APIs
* complex reasoning

---

# 31. Frontend Architecture

Recommended stack:

```text
React + Vite
       ↓
Camera / Microphone
       ↓
FastAPI backend
       ↓
WebSocket / REST
```

Suggested interface:

```text
┌─────────────────────────┐
│           AVA           │
│     AI VISUAL ASSIST    │
│                         │
│      LIVE CAMERA        │
│                         │
├─────────────────────────┤
│ 🔊 “Obstacle ahead.”    │
├─────────────────────────┤
│      🎙 ASK AVA         │
│                         │
│ [SCAN]    [READ]        │
│                         │
│         [SOS]           │
└─────────────────────────┘
```

The interface should have:

* large touch targets
* high contrast
* semantic screen-reader labels
* minimal visual clutter
* keyboard accessibility
* voice-first operation

The user should not have to constantly inspect the screen.

---

# 32. Backend Structure

Recommended repository:

```text
ava/
│
├── frontend/
│   ├── src/
│   │   ├── camera/
│   │   ├── audio/
│   │   ├── components/
│   │   └── services/
│   └── package.json
│
├── backend/
│   ├── main.py
│   │
│   ├── routes/
│   │   ├── vision.py
│   │   ├── ocr.py
│   │   ├── assistant.py
│   │   └── emergency.py
│   │
│   └── services/
│       ├── yolo.py
│       ├── tracking.py
│       ├── spatial.py
│       ├── state.py
│       ├── events.py
│       ├── safety.py
│       ├── intent.py
│       ├── response.py
│       ├── tts.py
│       └── ollama.py
│
├── demo/
│   ├── classroom.jpg
│   ├── corridor.jpg
│   ├── library-sign.jpg
│   └── emergency-exit.jpg
│
├── requirements.txt
├── .env.example
└── README.md
```

The current development plan follows essentially this modular separation. 

---

# 33. Internal Data Contracts

## Detection

```python
DetectionResult = {
    "track_id": 17,
    "label": "chair",
    "confidence": 0.91,
    "bbox": [x1, y1, x2, y2],
    "timestamp": 0
}
```

## Spatial Object

```python
SpatialObject = {
    "track_id": 17,
    "label": "chair",
    "direction": "center",
    "proximity": "near",
    "motion": "approaching"
}
```

## Event

```python
Event = {
    "type": "OBSTACLE_APPROACHING",
    "priority": 95,
    "object_id": 17,
    "direction": "center",
    "proximity": "near"
}
```

## Speech Job

```python
SpeechJob = {
    "text": "Stop. Obstacle ahead.",
    "priority": 95,
    "interrupt": True,
    "language": "en",
    "cacheable": True
}
```

---

# 34. API

Minimal initial API:

```text
POST /vision/detect
```

Object detection.

```text
POST /vision/ocr
```

OCR.

```text
POST /assistant/query
```

User query / intent.

```text
POST /emergency
```

Emergency flow.

```text
WS /events
```

Live state/events if WebSocket mode is stable.

Start simple:

```text
REST first
↓
WebSocket after core works
```

This minimizes integration risk.

---

# 35. Technology Stack

| Layer             | Technology                        |
| ----------------- | --------------------------------- |
| Frontend          | React + Vite                      |
| Backend           | Python + FastAPI                  |
| Camera            | OpenCV / browser camera           |
| Object detection  | Ultralytics YOLO                  |
| Tracking          | ByteTrack initially               |
| Spatial reasoning | Python + OpenCV / NumPy           |
| World State       | Python + Pydantic                 |
| Event engine      | Python                            |
| Safety            | Deterministic rules               |
| OCR               | PaddleOCR                         |
| STT               | faster-whisper                    |
| Workflow          | LangGraph                         |
| LLM               | Ollama, optional                  |
| TTS               | Indic Parler-TTS + cached phrases |
| Communication     | REST → WebSocket if stable        |
| Version control   | Git + GitHub                      |

---

# 36. 20-Hour Build Plan

## Hour 0–1 — Foundation

Build:

```text
Repo
FastAPI
React
Camera
Basic API
```

### Exit condition

Everyone can run the project.

---

## Hour 1–3 — Vision

Build:

```text
Camera
 ↓
YOLO
 ↓
detections
```

### Exit condition

Live detections work.

---

## Hour 3–5 — Tracking + Spatial

Build:

```text
YOLO
 ↓
Tracking
 ↓
Direction
 ↓
Relative proximity
```

### Exit condition

Stable object state.

---

## Hour 5–7 — World State + Safety

Build:

```text
Spatial data
 ↓
World State
 ↓
Change detection
 ↓
Safety events
```

### Exit condition

Obstacle can enter the path and produce a state transition.

---

## Hour 7–9 — Response + TTS

Build:

```text
Event
 ↓
Priority
 ↓
Response Manager
 ↓
TTS
```

### Exit condition

No speech spam.

Critical alerts can interrupt.

---

## Hour 9–11 — OCR

Build:

```text
READ
 ↓
OCR
 ↓
TTS
```

### Exit condition

Demo sign works.

---

## Hour 11–13 — STT + Intent

Build:

```text
VOICE
 ↓
STT
 ↓
Intent
```

### Exit condition

Core voice commands work.

---

## Hour 13–15 — Context

Build:

```text
World State
 ↓
Context
 ↓
Scene response
```

### Exit condition

Scene query produces a useful answer.

---

## Hour 15–16 — Ollama

Only if the system is already stable.

Build:

```text
World State
 ↓
Ollama
 ↓
Natural-language description
```

### Exit condition

Optional rich mode works.

If unstable:

> **Disable it.**

---

## Hour 16–17.5 — Emergency + Accessibility

Implement:

* SOS
* emergency priority
* screen-reader labels
* large controls
* voice-first interaction

---

## Hour 17.5–18.5 — Fallback Mode

Prepare:

```text
Ollama fallback
TTS cache
Prepared images
Prepared signs
REST fallback
```

---

## Hour 18.5–20 — Demo + Pitch

No new functionality.

Test.

Rehearse.

Freeze.

---

# 37. Team Responsibilities

## Vision Engineer

Own:

* YOLO
* Tracking
* Spatial
* World State ingestion

## Backend / AI Engineer

Own:

* FastAPI
* Event engine
* Safety
* LangGraph
* Ollama

## Frontend Engineer

Own:

* React
* Camera interface
* accessibility
* controls

## Voice / Integration Engineer

Own:

* STT
* TTS
* Response Manager
* audio queue
* end-to-end integration

The existing plan uses essentially the same role split. 

---

# 38. Testing Strategy

## Core safety

```text
Chair enters center
→ obstacle warning

Chair stays
→ no repeated warning

Chair approaches
→ warning escalates

Chair leaves
→ path clear
```

## Voice

```text
Where is the door?
→ right

Is the path clear?
→ safety response

Read this
→ OCR

Describe surroundings
→ scene response

Repeat
→ repeat last response

Stop
→ stop audio
```

## Failure

```text
Ollama OFF
→ core works

Internet OFF
→ local system works

TTS delay
→ cached alert

OCR failure
→ focused scan

YOLO slowdown
→ reduce resolution/FPS
```

The current source plan defines these same core test and fallback expectations. 

---

# 39. Failure / Fallback Architecture

AVA should degrade gracefully.

| Failure              | Fallback                  |
| -------------------- | ------------------------- |
| Ollama unavailable   | Deterministic templates   |
| Internet unavailable | Local pipeline            |
| YOLO slow            | Lower resolution/FPS      |
| Tracker unstable     | Simpler tracking/cooldown |
| OCR unreliable       | Focused scan              |
| TTS slow             | Cached phrases            |
| TTS overlap          | Response Manager          |
| Camera failure       | Prepared demo input       |
| WebSocket failure    | REST/snapshot mode        |

The key rule:

> **Optional components may fail. The safety loop must remain.**

---

# 40. Performance Strategy

The system is designed around different computational frequencies.

```text
CAMERA
24–30 FPS
      ↓
YOLO
~8–15 FPS
      ↓
WORLD STATE
      ↓
SAFETY
~2–5 Hz
```

Meanwhile:

```text
OCR       → on demand
STT       → listening
Ollama    → on demand
TTS       → event/query driven
```

This avoids wasting resources and reduces latency.

---

# 41. Latency Philosophy

The safety path should target a response that feels immediate.

Conceptually:

```text
Frame
 ↓
YOLO
 ↓
Spatial
 ↓
Safety
 ↓
Priority
 ↓
Cached TTS
```

No:

```text
LLM
translation
cloud API
database
```

between detection and a critical safety alert.

Exact latency must be benchmarked on the actual hackathon machine.

Track:

```text
inference_time
fps
dropped_frames
event_time
tts_start_time
end_to_end_latency
```

---

# 42. Privacy

Local-first design also reduces unnecessary exposure of camera data.

Principles:

* process locally where practical
* don't store raw video unnecessarily
* retain compact state instead of video history
* don't add facial recognition
* don't collect personal data unnecessarily

---

# 43. Safety Boundaries

AVA is an **assistive prototype**, not a certified mobility device.

Do not claim:

* perfect detection
* exact distance without calibration
* guaranteed collision avoidance
* replacement for a cane
* replacement for a guide dog
* replacement for emergency services

Safety language should be conservative when confidence is low.

---

# 44. Demo Scenario

The best demonstration is one continuous environment.

### Stage 1

AVA sees:

```text
Person
Chair
Door
Table
```

AVA remains mostly silent.

### Stage 2

Chair enters path.

> **“Caution. Obstacle ahead.”**

### Stage 3

Chair becomes closer.

> **“Stop. Obstacle directly ahead.”**

### Stage 4

User asks:

> “Where is the door?”

> **“The door is on your right.”**

### Stage 5

User asks:

> “Read this sign.”

> **“Emergency Exit.”**

### Stage 6

User asks:

> “Describe my surroundings.”

Rich contextual response.

### Stage 7

Switch language.

Demonstrate a cached local-language safety phrase.

This shows the entire architecture in one story.

---

# 45. Why This Is Different

The strongest competitor answer is not:

> “We use better YOLO.”

It is:

> **“We don't compete on general visual perception. We use proven perception tools and build the missing decision layer around them.”**

The fundamental contrast:

```text
GENERAL VISION
“What do you see?”

AVA
“What changed?
Where is it relative to me?
Does it matter?
Should I hear it now?
What should I do?”
```

---

# 46. Final Mental Model

Remember AVA as:

```text
YOLO
→ sees

TRACKER
→ connects time

SPATIAL
→ gives perspective

WORLD STATE
→ remembers context

CHANGE ENGINE
→ notices what changed

SAFETY
→ evaluates risk

PRIORITY
→ decides importance

STT
→ understands the user

OCR
→ reads text

LANGGRAPH
→ orchestrates complex workflows

OLLAMA
→ provides optional natural language

RESPONSE MANAGER
→ controls the conversation

TTS
→ gives AVA a voice
```

Together:

```text
SEE
 ↓
REMEMBER
 ↓
UNDERSTAND
 ↓
DECIDE
 ↓
SPEAK
```

# 47. Final Principle

> ## **Perception is not the product.**
>
> ## **The decision loop is the product.**

AVA continuously observes the environment, maintains only the context it needs, reacts to meaningful change, prioritizes safety and relevance, understands user intent, and communicates through an accessible voice-first interface.

> **Others tell you what the camera sees.**
>
> **AVA decides what you need to know.**

```
```
