````markdown
# AVA — AI Visual Assist

> **From seeing objects to understanding situations.**

AVA is a **local-first, proactive, context-aware AI assistive system** designed primarily for visually impaired users.

Instead of simply detecting objects in a camera frame and reading them aloud, AVA continuously maintains a compact understanding of the user's immediate environment, detects meaningful changes, evaluates their relevance and safety, and communicates only what the user needs to know.

> **AVA forgets the frames. It remembers what changed.**

---

## Project Vision

Traditional computer-vision assistance can be represented as:

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

The central question AVA tries to answer is:

> **“What does this user need to know right now?”**

---

## Problem Statement Alignment

AVA addresses **Problem Statement #4 — AI Assistive Technology for Persons with Visual or Hearing Impairments**.

The problem statement focuses on improving accessibility in digital and physical environments and explicitly allows teams to focus on one specific accessibility challenge rather than attempting to solve everything.

AVA focuses specifically on:

> **Visual environmental assistance for visually impaired users.**

Relevant capabilities from the problem statement incorporated into AVA include:

* Real-time object detection
* Text/signboard recognition
* Text-to-speech
* Speech-to-text
* Navigation/spatial assistance
* Obstacle detection
* Emergency assistance

The broader problem statement also mentions currency/document recognition, environmental sound alerts and accessible educational content. These are treated as future/stretch modules rather than core functionality.

---

# Why AVA Is Different

AVA does **not** try to compete with general-purpose computer vision systems on the basis of having a better detector, OCR engine or language model.

Products such as Google Lens and Google Lookout already provide powerful visual understanding and accessibility features.

AVA's differentiation is the **system-level interaction model**.

### Conventional visual assistance

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

### AVA

```text
Environment continuously changes
              ↓
      Maintain World State
              ↓
      Detect meaningful change
              ↓
       Evaluate relevance
              ↓
        Evaluate safety
              ↓
       Prioritize information
              ↓
        Proactively assist
```

AVA therefore focuses on:

* Continuous environmental state
* Temporal change detection
* User-relative spatial understanding
* Attention and priority
* Proactive safety alerts
* Central speech arbitration
* Voice-first interaction
* LLM-independent safety
* Local-first operation

> **AVA adds the decision layer between machine perception and human attention.**

---

# Core User Features

AVA is intentionally focused around a small set of useful capabilities rather than attempting to reproduce every possible accessibility feature.

## SEE

Real-time perception of relevant objects and surroundings.

Powered by:

* YOLO
* Object confidence
* Bounding-box information
* Object tracking

---

## LOCATE

Answers where an object is relative to the user.

Example:

> “Where is the door?”

AVA:

> “The door is on your right.”

---

## PROTECT

Detects obstacles, changing proximity and path hazards.

Example:

> “Stop. Obstacle ahead.”

---

## READ

Reads visible text and signs.

Example:

> “Read this sign.”

AVA:

> “Emergency Exit.”

---

## COMMUNICATE

Allows the user to interact through speech and receive spoken responses.

Examples:

> “Where is the door?”

> “Repeat.”

> “Stop.”

> “Describe my surroundings.”

---

## ASSIST

Provides high-priority emergency and exit assistance.

Emergency events always receive higher priority than normal information.

---

# Master Architecture

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
             CHANGE / EVENT     USER INTENT
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

# Engine Architecture

AVA should be understood as a set of specialized engines.

---

## Perception Engine

### Purpose

> **What is around me?**

The perception layer is responsible for detecting what appears in the current camera frame.

Primary component:

**YOLO**

Input:

```text
Camera frame
```

Output:

```text
Object class
Confidence
Bounding box
```

Example:

```json
{
  "class": "chair",
  "confidence": 0.91,
  "bbox": [420, 250, 650, 620]
}
```

YOLO is only the perception layer.

It does not decide:

> “This chair is dangerous.”

That decision belongs to later engines.

---

# Tracking Engine

Detection tells us what exists in one frame.

Tracking connects observations across time.

Without tracking:

```text
Frame 1 → Chair
Frame 2 → Chair
Frame 3 → Chair
Frame 4 → Chair
```

With tracking:

```text
Frame 1 → Chair #17
Frame 2 → Chair #17
Frame 3 → Chair #17
Frame 4 → Chair #17
```

This allows AVA to determine:

* Whether the object is the same object
* Whether it is moving
* Whether it is approaching
* Whether it has already been announced
* Whether its state has changed

Tracking is therefore fundamental to continuous environmental awareness.

---

# Spatial Engine

### Purpose

> **Where is it relative to me?**

AVA derives direction from the bounding-box position.

```python
center_x = (x1 + x2) / 2
```

For the MVP:

```text
0–33%   → LEFT
33–66%  → CENTER
66–100% → RIGHT
```

Example:

```text
x = 20% → LEFT
x = 50% → CENTER
x = 82% → RIGHT
```

This gives AVA user-relative answers such as:

> “The door is on your right.”

---

# Relative Proximity

AVA should not claim exact physical distance without appropriate calibration.

Instead, the MVP uses relative proximity:

```text
Small bounding box  → FAR
Medium              → MEDIUM
Large               → NEAR
Very large + path overlap → CRITICAL
```

Temporal change can then show:

```text
FAR
 ↓
MEDIUM
 ↓
NEAR
 ↓
CRITICAL
```

This can trigger an approaching-obstacle event.

Future versions can add calibrated depth or a suitable depth model.

---

# World State Engine

The World State is AVA's **short-term environmental memory**.

Instead of storing thousands of raw video frames, AVA stores structured facts extracted from the environment.

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

The key idea is:

> **Raw pixels are temporary. Context persists briefly.**

---

# Frame Management

The camera may produce 24–30 frames per second.

AVA does not need to process every frame through every model.

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

We intentionally avoid:

```text
Frame 1 waiting
Frame 2 waiting
Frame 3 waiting
...
Frame 500 waiting
```

because stale frames increase latency.

The system retains:

* current object identities
* position
* relative proximity
* movement
* confidence
* last alert
* short temporal history

It does not need an ever-growing video history.

> **AVA forgets the frames. It remembers what changed.**

---

# Change / Event Engine

The Change Engine compares the current World State with the previous state.

```text
Previous State
      ↓
Current State
      ↓
Difference
      ↓
Meaningful Change?
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
Frame 1:
Chair = FAR

Frame 2:
Chair = MEDIUM

Frame 3:
Chair = NEAR

Frame 4:
Chair = CENTER + CRITICAL
```

Result:

```text
OBSTACLE_APPROACHING
```

---

# Safety Engine

The Safety Engine determines whether the current environment requires action.

It considers:

```text
Object
+
Direction
+
Proximity
+
Movement
+
Path relationship
```

Example:

```text
Person
far
left
stationary
→ LOW

Chair
center
near
approaching
→ HIGH

Obstacle
center
critical
→ CRITICAL
```

Safety logic should remain deterministic.

---

# Priority Engine

Not every observation should become speech.

Suppose AVA sees:

```text
Person
Chair
Door
Bottle
Table
Exit
Plant
```

A naïve assistant might announce everything.

AVA should remain silent unless information is useful or important.

Example:

```text
Chair enters path
       ↓
Priority increases
       ↓
“Caution. Obstacle ahead.”
```

A practical priority structure:

```text
100 → Emergency
 95 → Immediate collision
 90 → Safety warning
 75 → Navigation / direction
 65 → Important text
 50 → Scene description
 30 → General information
```

The principle is:

> **Silence is also a decision.**

---

# Response Manager

Only one component should control the outgoing speech channel.

All engines submit response requests to the Response Manager.

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

AVA is speaking:

> “You are in a corridor…”

A new critical event occurs:

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

# STT / Intent Engine

The user can communicate with AVA through voice.

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

Example:

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

---

# OCR Engine

OCR is activated when useful rather than continuously.

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

This keeps the continuous perception pipeline lightweight.

---

# Context Engine

The Context Engine converts verified structured facts into useful descriptions.

Example input:

```text
person = center
door = right
chair = left
path = clear
```

Possible output:

> “You are in a corridor. The path ahead is clear. There is a door on your right.”

This can be implemented using deterministic templates.

That gives AVA a reliable fallback without requiring an LLM.

---

# LangGraph

LangGraph is used for **workflow orchestration**, not high-frequency perception.

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

Important rule:

> **Do not invoke LangGraph for every camera frame.**

It should activate around meaningful events and higher-level user queries.

---

# Ollama

Ollama is an **optional natural-language layer**.

### Good uses

* Scene descriptions
* Conversational responses
* Natural-language synthesis
* Contextual explanations

### Bad uses

* Collision decisions
* Emergency decisions
* Safety severity
* Object detection
* Exact direction decisions

Correct architecture:

```text
Verified World State
       ↓
Structured Facts
       ↓
Ollama
       ↓
Response Validator
       ↓
TTS
```

Hard rule:

> **The LLM never becomes the safety authority.**

---

# Fast Path vs Rich Path

AVA effectively contains two different computational paths.

## Fast Path

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

Used for:

* Obstacles
* Collision warnings
* Emergency events
* Immediate path changes

Characteristics:

**Local**
**Deterministic**
**Fast**

---

## Rich Path

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

Used for:

* Scene descriptions
* Conversational questions
* Contextual explanations

Characteristics:

**Contextual**
**Conversational**
**Optional**

---

# Critical Safety Principle

The most important architectural rule is:

```text
The LLM never sits between perception
and a critical safety alert.
```

Correct:

```text
YOLO
 ↓
Spatial
 ↓
Safety Rules
 ↓
Priority
 ↓
Cached TTS
```

Incorrect:

```text
YOLO
 ↓
Ollama
 ↓
“Is this dangerous?”
 ↓
TTS
```

The deterministic safety path must remain operational independently.

---

# TTS Architecture

Speech is not merely:

```text
Text → Audio
```

AVA must first decide:

```text
What?
When?
Priority?
Interrupt?
Queue?
Drop?
Language?
```

Then:

```text
Approved Response
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

# Local-Language TTS

AVA should use a local multilingual TTS path where practical.

For Indian-language output, the primary experimental choice is:

**AI4Bharat Indic Parler-TTS**

Critical messages can be pre-generated and cached.

Example:

```text
“Stop. Obstacle ahead.”

“Obstacle on your left.”

“Path clear.”

“Emergency exit ahead.”
```

Then:

```text
Critical Event
      ↓
Cached Audio
      ↓
Immediate Playback
```

Dynamic responses can use local TTS generation.

The live demonstration should use a **preselected and tested language** rather than depending on automatic language switching for safety-critical speech.

---

# End-to-End Example: Obstacle

Imagine the user is walking.

### Camera

```text
Continuous frames
```

### YOLO

```text
chair
door
person
```

### Tracker

```text
Chair #17
```

### Spatial Engine

```text
chair = center
```

### World State

```text
chair
center
medium
```

### Later

```text
medium
 ↓
near
 ↓
approaching
```

### Change Engine

```text
OBSTACLE_APPROACHING
```

### Safety Engine

```text
path overlap = YES
proximity = NEAR
approaching = YES
```

### Priority

```text
95
```

### Response Manager

```text
INTERRUPT
```

### TTS

> **“Stop. Obstacle ahead.”**

That entire chain is AVA.

---

# End-to-End Example: Door

User:

> “Where is the door?”

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

# End-to-End Example: Read Sign

User:

> “Read this sign.”

```text
VOICE
 ↓
STT
 ↓
READ
 ↓
CURRENT FRAME
 ↓
OCR
 ↓
TEXT
 ↓
TTS
```

Output:

> **“Emergency Exit.”**

---

# End-to-End Example: Scene Description

User:

> “Describe my surroundings.”

```text
VOICE
 ↓
STT
 ↓
SCENE
 ↓
WORLD STATE
 ↓
CONTEXT ENGINE
 ↓
OPTIONAL LANGGRAPH
 ↓
OPTIONAL OLLAMA
 ↓
VALIDATOR
 ↓
TTS
```

Output:

> “You are in a corridor. A door is on your right and the path ahead is clear.”

---

# Accessibility Architecture

AVA's screen is not the primary source of information.

The intended interaction is:

```text
Voice-first
      +
Audio-first
      +
Screen-reader compatible
      +
Large controls
      +
Minimal visual dependency
```

Core commands should work without requiring the user to continuously inspect the interface.

Suggested controls:

```text
[SCAN]
[READ]
[REPEAT]
[STOP]
[SOS]
```

The corresponding voice commands provide the same operations.

---

# Frontend

Recommended:

```text
React + Vite
```

Interface:

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
│       🎙 ASK AVA        │
│                         │
│ [SCAN]    [READ]        │
│                         │
│          [SOS]          │
└─────────────────────────┘
```

---

# Backend

Recommended:

```text
Python + FastAPI
```

Responsibilities:

* API handling
* model orchestration
* World State
* events
* safety
* response management
* TTS
* optional LLM workflow

---

# Repository Structure

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

---

# Internal Data Flow

## Detection

```python
{
    "track_id": 17,
    "label": "chair",
    "confidence": 0.91,
    "bbox": [x1, y1, x2, y2],
    "timestamp": 0
}
```

## Spatial Object

```python
{
    "track_id": 17,
    "label": "chair",
    "direction": "center",
    "proximity": "near",
    "motion": "approaching"
}
```

## Event

```python
{
    "type": "OBSTACLE_APPROACHING",
    "priority": 95,
    "object_id": 17,
    "direction": "center",
    "proximity": "near"
}
```

## Speech Job

```python
{
    "text": "Stop. Obstacle ahead.",
    "priority": 95,
    "interrupt": True,
    "language": "en",
    "cacheable": True
}
```

---

# API

Initial endpoints:

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

Optional real-time events once the core system is stable.

Start simple:

```text
REST first
 ↓
WebSocket later
```

---

# Technology Stack

| Layer            | Technology                        |
| ---------------- | --------------------------------- |
| Frontend         | React + Vite                      |
| Backend          | Python + FastAPI                  |
| Camera           | OpenCV / browser camera           |
| Object Detection | YOLO                              |
| Tracking         | ByteTrack initially               |
| Spatial          | Python + OpenCV / NumPy           |
| World State      | Python + Pydantic                 |
| Event Engine     | Python                            |
| Safety           | Deterministic rules               |
| OCR              | PaddleOCR                         |
| STT              | faster-whisper                    |
| Workflow         | LangGraph                         |
| LLM              | Ollama, optional                  |
| TTS              | Indic Parler-TTS + cached phrases |
| Transport        | REST → WebSocket if stable        |
| Version Control  | Git + GitHub                      |

---

# Development Sequence

The implementation should follow dependencies rather than trying to develop all engines simultaneously.

```text
Foundation
    ↓
Camera
    ↓
YOLO
    ↓
Tracking
    ↓
Spatial
    ↓
World State
    ↓
Change / Events
    ↓
Safety
    ↓
Priority
    ↓
Response Manager
    ↓
TTS
    ↓
OCR
    ↓
STT
    ↓
Intent
    ↓
Context
    ↓
LangGraph
    ↓
Ollama
    ↓
Accessibility
    ↓
Fallbacks
    ↓
Testing
```

The core rule is:

> **Build the deterministic pipeline first. Add intelligence only after the core loop works.**

---

# Core MVP

The system is complete enough for demonstration when it can:

```text
1. Start the camera.
2. Detect objects.
3. Track objects.
4. Determine direction.
5. Estimate relative proximity.
6. Maintain World State.
7. Detect meaningful changes.
8. Identify obstacles.
9. Prioritize alerts.
10. Prevent repeated speech.
11. Interrupt speech for critical hazards.
12. Answer “Where is the door?”
13. Read a sign.
14. Accept core voice commands.
15. Describe the environment.
16. Speak through local TTS.
17. Operate through an accessibility-first interface.
18. Continue basic operation without Ollama or internet.
```

---

# Failure Strategy

AVA should degrade gracefully.

| Failure               | Fallback                               |
| --------------------- | -------------------------------------- |
| Ollama unavailable    | Deterministic templates                |
| Internet unavailable  | Local pipeline                         |
| YOLO too slow         | Smaller model / lower resolution / FPS |
| Tracker unstable      | Simpler tracking + cooldown            |
| OCR unreliable        | Focused scan                           |
| TTS slow              | Cached safety phrases                  |
| TTS overlap           | Response Manager                       |
| False detection       | Confidence + tracking + cooldown       |
| Camera failure        | Prepared input through same pipeline   |
| WebSocket instability | REST/snapshot mode                     |

The rule is:

> **Optional components may fail. The core safety loop must remain.**

---

# Safety Boundaries

AVA is an assistive prototype.

It is **not** a replacement for:

* a mobility cane
* a guide dog
* trained assistance
* emergency services

Do not claim:

* perfect object detection
* exact distance without calibration
* guaranteed collision avoidance
* perfect language recognition
* production-grade safety certification

Use conservative language when confidence is low.

---

# Privacy

The local-first architecture also reduces unnecessary handling of camera data.

Principles:

* Process locally where practical.
* Do not unnecessarily store raw video.
* Retain compact environmental state instead of video history.
* Avoid unnecessary personal data collection.
* Do not add facial recognition to the MVP.

---

# Best Demo

Use one continuous physical environment.

### Phase 1 — Observe

AVA detects:

```text
Person
Chair
Door
Table
```

but does not narrate everything.

### Phase 2 — Threat emerges

Chair enters path.

> **“Caution. Obstacle ahead.”**

### Phase 3 — Threat escalates

Chair becomes closer.

> **“Stop. Obstacle directly ahead.”**

### Phase 4 — User asks

> “Where is the door?”

> **“The door is on your right.”**

### Phase 5 — Read

> “Read this sign.”

> **“Emergency Exit.”**

### Phase 6 — Understand

> “Describe my surroundings.”

AVA generates a concise contextual description.

### Phase 7 — Local language

Switch the selected language and demonstrate a cached critical alert.

This single demonstration exercises almost the entire architecture.

---

# The Core Mental Model

Remember every engine like this:

```text
YOLO
→ sees

TRACKER
→ connects time

SPATIAL ENGINE
→ gives perspective

WORLD STATE
→ remembers context

CHANGE ENGINE
→ notices what changed

SAFETY ENGINE
→ evaluates risk

PRIORITY ENGINE
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
→ controls the speech channel

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

# Final Principle

> ## **Perception is not the product.**
>
> ## **The decision loop is the product.**

AVA continuously observes the environment, retains only the context it needs, understands change over time, evaluates safety and relevance, interprets user intent, and communicates the right information through an accessible voice-first interface.

> **Others tell you what the camera sees.**
>
> **AVA decides what you need to know.**

```
```
