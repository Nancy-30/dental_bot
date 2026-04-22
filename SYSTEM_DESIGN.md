# System Design — ABC Dental Clinic AI Receptionist

This document explains how the system works end-to-end, in plain language.

---

## The Big Picture

A patient opens a web page and clicks "Start Conversation". Their voice goes through several processing steps — speech recognition, a language model, text-to-speech — and they hear a human-sounding voice reply within about a second. Everything the patient says is saved to a database, and after the call ends, an AI reviews the full transcript and generates a quality report.

```
Patient (browser)
      |
      | WebRTC audio (via LiveKit)
      v
 LiveKit Cloud  ──────────────────────────────────────────────
      |                                                       |
      | dispatch to agent                                     |
      v                                                       |
  Agent Worker (Python)                                       |
  ┌────────────────────────┐                                  |
  │  VAD → STT → LLM → TTS │                                 |
  └────────────────────────┘                                  |
      |                                                       |
      | saves data                                            |
      v                                                       |
  PostgreSQL DB ←── FastAPI Backend ←─────────────────────────
```

---

## Components

### 1. Frontend (React)

The frontend is a single web page. When the patient clicks "Start Conversation":

1. It calls `POST /token` on the backend.
2. The backend creates a LiveKit room, assigns the patient a token, and tells the LiveKit agent system to send a bot into that room.
3. The frontend connects to LiveKit Cloud using that token.
4. Audio from the patient's microphone streams directly to LiveKit Cloud over WebRTC. The patient hears the bot's voice back through the same connection.

The frontend does not process any audio itself — it is just a WebRTC client.

---

### 2. Backend (FastAPI)

A lightweight Python API server with three responsibilities:

- **`POST /token`** — issues a LiveKit room token for the browser and dispatches the `dental-bot` agent to that room.
- **`GET /health`** — simple health check.
- **Static file serving** — serves the compiled React app so everything runs on one port (8000).

The backend starts the database tables on startup (via SQLAlchemy `create_all`).

---

### 3. LiveKit Cloud

LiveKit is the real-time communication layer. It handles:

- Receiving audio from the browser (WebRTC)
- Routing audio to the agent worker
- Sending agent audio back to the browser
- Room lifecycle management

The agent worker connects to LiveKit Cloud over a persistent WebSocket. When a new room is created with `RoomAgentDispatch`, LiveKit sends a job to the worker, which then joins that room.

---

### 4. Agent Worker (the core)

This is where the intelligence lives. It is a Python process that runs continuously and handles one call at a time per worker instance.

#### Startup — Prewarm

When the worker process first starts (before any calls arrive), it pre-loads the heavy models into memory:

```
Worker starts
  → load Silero VAD model (voice activity detection)
  → load Deepgram STT client
  → load OpenAI LLM client (GPT-4o-mini)
  → establish Cartesia TTS WebSocket connection
```

This means the first call gets fast responses — nothing is cold-started when the patient speaks.

#### Per-Call Lifecycle

When a new call comes in:

```
1. Job arrives from LiveKit Cloud
2. Create call_metadata row in DB (room name, timestamp)
3. Connect to the LiveKit room
4. Build AgentSession (wires together VAD, STT, LLM, TTS)
5. Play pre-recorded greeting audio (MP3)
6. Listen and respond in a loop until patient disconnects
7. On disconnect:
   - Save call duration to DB
   - Save latency/cost statistics to DB
   - Run post-call AI analysis (async)
   - Close session
```

#### The Voice Pipeline

Each time the patient speaks, this pipeline runs:

```
Patient speaks
    ↓
VAD (Silero) — detects start and end of speech
    ↓
STT (Deepgram nova-2) — converts audio to text
    ↓
LLM (GPT-4o-mini) — generates a text response
    ↓
TTS (Cartesia sonic-english) — converts text to audio
    ↓
Patient hears the response
```

**Latency optimizations applied:**
- Models are prewarmed before calls arrive (no cold start)
- `preemptive_generation=True` — the LLM starts generating before speech fully ends
- `min_endpointing_delay=0.05s` — the pipeline starts processing 50ms after the patient stops speaking
- TTS streams sentence-by-sentence (not waiting for the full response)
- Cartesia WebSocket is pre-established at startup
- Filler words ("Sure, one moment...") play immediately while tools run in the background

---

### 5. DentalAgent — Tools and Memory

The agent is not a rigid decision tree. GPT-4o-mini drives the conversation and decides when to call tools.

#### Per-Call Memory

Each call has a `PatientMemory` dataclass that holds:
- `name`, `dob`, `reason_for_visit`, `preferred_time`, `insurance_name`
- `appointment_booked` flag

This is held in Python memory for the duration of the call. It is the single source of truth — the LLM is updated with what has been collected so it never asks the same question twice.

#### Tools Available to the LLM

| Tool | When it is called |
|---|---|
| `capture_patient_info()` | As soon as the patient shares any detail (name, DOB, reason, etc.) |
| `book_appointment()` | When all required fields are collected |
| `get_clinic_info()` | For any FAQ (hours, address, insurance, services) |
| `escalate_call()` | Severe emergency or explicit request for human |
| `end_call()` | After the patient says goodbye |

#### Information Flow for a Booking

```
Patient: "I have a cavity, my name is Suraj"
  → LLM calls capture_patient_info(name="Suraj", reason_for_visit="cavity")
  → PatientMemory updated: name=Suraj, reason=cavity
  → DB row updated (fire-and-forget async task)
  → LLM instructions updated: "name and reason already captured, don't ask again"

Bot: "Got it. What's your date of birth, and what date and time works for you?"

Patient: "20th July 2003, how about Thursday at 3pm?"
  → LLM calls capture_patient_info(dob="20th July 2003", preferred_time="Thursday at 3pm")
  → date_utils normalizes: dob → "20-07-2003", preferred_time → "24-04-2026 15:00:00"
  → PatientMemory updated

Bot: "Perfect. And do you have dental insurance?"

Patient: "Delta Dental"
  → LLM calls book_appointment(insurance_name="Delta Dental")
  → Merges with memory (all 5 fields now complete)
  → Saves to appointments table
  → Bot confirms booking
```

---

### 6. Database

PostgreSQL with six tables. All timestamps are stored in IST (Indian Standard Time).

```
call_metadata (1 row per call)
  └── patient_data       (patient profile, updated incrementally)
  └── appointments       (confirmed booking, 1 row per booking)
  └── conversations      (every turn: user + assistant messages)
  └── evaluation_statistics (latency/cost summary at call end)
  └── call_analysis      (post-call AI report)
```

**Why NullPool?**
LiveKit runs each agent session in a subprocess with its own event loop. SQLAlchemy's default connection pool does not work safely across subprocess boundaries. `NullPool` creates a fresh connection per query and closes it immediately — no shared state across process boundaries.

**Why fire-and-forget?**
DB writes happen inside `asyncio.create_task()` so they do not block the voice pipeline. A 20ms DB write would add 20ms of perceived latency if awaited. Instead the agent responds immediately and the DB updates in the background.

---

### 7. Post-Call Analysis

After every call ends, a background task sends the full transcript to GPT-4o-mini with a structured prompt. The model returns a JSON object with fields like:

- `call_intent` — booking / faq / reschedule / emergency / other
- `appointment_confirmed` — true / false
- `customer_satisfaction_signal` — Satisfied / Neutral / Dissatisfied
- `bot_response_accuracy` — Accurate / Partially Accurate / Incorrect
- `did_bot_fail_to_answer` — Yes / No
- `questions_asked` — list of questions the patient asked
- `conversational_issue_detected` — description of any problem

This is saved to the `call_analysis` table and can be used for quality monitoring and agent improvement.

---

## Key Design Decisions

### Why LiveKit?
LiveKit handles the hardest parts of real-time voice: WebRTC negotiation, audio routing, NAT traversal, and room lifecycle. The agent only needs to process audio — not manage connections.

### Why GPT-4o-mini and not a rule engine?
A rule engine would need explicit branching for every conversation path. GPT-4o-mini can handle natural variation — patients who answer multiple questions at once, change their mind, or go off-topic — without any extra code. The tools give it structured actions; the system prompt gives it boundaries.

### Why Cartesia for TTS?
Cartesia uses a persistent WebSocket (unlike REST-based TTS services). This means the first audio chunk arrives much faster because the connection is already open. Combined with sentence-level streaming, the patient hears the beginning of the response before the full sentence is even generated.

### Why a pre-recorded greeting?
The first thing a patient hears should be instant and high quality. Generating the greeting through the TTS pipeline every time adds ~300-500ms of cold-start latency at the worst possible moment (first impression). An MP3 file plays immediately.

### Why store dates as strings (not DATE columns)?
The patient says things like "20th July 2003" or "next Thursday at 3pm". These get parsed and normalized by `dateparser` before storage. Using a `VARCHAR` column makes it easy to store the normalized string without timezone or format conversion issues at the ORM layer. The format is always `DD-MM-YYYY` (DOB) or `DD-MM-YYYY HH:MM:SS` (preferred time).

---

## Sequence Diagram — Full Call

```
Browser          Backend         LiveKit Cloud      Agent Worker        DB
   |                |                  |                  |              |
   |-- POST /token ->|                  |                  |              |
   |                |-- create room --->|                  |              |
   |                |-- dispatch bot -->|                  |              |
   |<-- token ------|                  |                  |              |
   |                                   |                  |              |
   |-- WebRTC connect ---------------->|                  |              |
   |                                   |-- job dispatch ->|              |
   |                                   |                  |-- upsert --> |
   |                                   |<-- agent joins --|  call_meta   |
   |<-- greeting audio (MP3) ----------|                  |              |
   |                                   |                  |              |
   |-- patient speaks ---------------->|                  |              |
   |                                   |-- audio stream ->|              |
   |                                   |     VAD detects speech end      |
   |                                   |     STT transcribes             |
   |                                   |     LLM generates reply         |
   |                                   |     (filler plays immediately)  |
   |                                   |     TTS streams audio           |
   |<-- bot speaks --------------------|                  |              |
   |                                   |                  |-- save turn->|
   |                                   |                  |  (async)     |
   |                  ...conversation continues...                        |
   |                                   |                  |              |
   |-- patient disconnects ----------->|                  |              |
   |                                   |-- session end -->|              |
   |                                   |                  |-- save stats>|
   |                                   |                  |-- analyze -->|
   |                                   |                  |  (async GPT) |
   |                                   |                  |-- save anal->|
```
