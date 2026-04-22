# ABC Dental Clinic AI Receptionist

A voice AI receptionist for a dental clinic. Patients call in (or open the web app), speak naturally, and the bot handles appointment booking, clinic FAQs, and escalation to human staff — all through a real-time voice conversation.

---

## What It Does

- Greets the patient with a pre-recorded audio clip
- Books appointments by collecting: name, date of birth, reason for visit, preferred date/time, and insurance (optional)
- Answers common questions about clinic hours, address, services, and insurance
- Escalates to a human staff member when needed
- Saves everything to a PostgreSQL database
- Runs a post-call AI analysis (intent, satisfaction, Q&A quality) after every session

---

## Tech Stack

| Layer | Technology |
|---|---|
| Voice pipeline | LiveKit Agents 1.4.5 |
| Speech-to-text | Deepgram (nova-2) |
| Language model | OpenAI GPT-4o-mini |
| Text-to-speech | Cartesia (sonic-english) |
| Voice activity detection | Silero VAD |
| Turn detection | LiveKit MultilingualModel |
| Backend API | FastAPI + Uvicorn |
| Database | PostgreSQL via SQLAlchemy (async) |
| Frontend | React + Tailwind CSS |

---

## Project Structure

```
Dental_Bot/
├── agent.py                  # LiveKit worker entrypoint
├── config.py                 # All settings loaded from .env
├── start.sh                  # Single script to start everything
│
├── agents/
│   ├── dental_agent.py       # Agent class with all tool methods
│   ├── entrypoint.py         # Per-call session handler
│   ├── patient_memory.py     # In-memory patient data per call
│   ├── prompts.py            # System prompt and greeting text
│   ├── prewarm.py            # Pre-loads VAD, STT, LLM models at startup
│   ├── session.py            # Builds AgentSession, plays greeting
│   └── metrics.py            # Per-turn latency and cost tracking
│
├── backend/
│   └── main.py               # FastAPI app (serves API + frontend)
│
├── routes/
│   ├── token.py              # POST /token — issues LiveKit room token
│   ├── health.py             # GET /health
│   └── spa.py                # Serves React frontend
│
├── database/
│   ├── models.py             # ORM table definitions
│   ├── connection.py         # Async DB engine (NullPool)
│   ├── call_metadata_repo.py
│   ├── patient_repo.py
│   ├── appointment_repo.py
│   ├── conversation_repo.py
│   ├── evaluation_stats_repo.py
│   ├── call_analysis_repo.py
│   └── call_analysis_service.py  # Post-call GPT-4o-mini analysis
│
├── utils/
│   ├── date_utils.py         # Normalizes DOB → DD-MM-YYYY, time → DD-MM-YYYY HH:MM:SS
│   ├── logging_setup.py      # Silences noisy third-party loggers
│   └── env_setup.py          # Env var helpers
│
└── frontend/                 # React app (built output in frontend/dist/)
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+ (only needed to rebuild the frontend)
- PostgreSQL running locally
- A LiveKit Cloud account
- API keys for Deepgram, OpenAI, and Cartesia

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
CLOUD_URL=wss://your-project.livekit.cloud
CLOUD_API_KEY=...
CLOUD_API_SECRET=...

DEEPGRAM_API_KEY=...
OPENAI_API_KEY=...
CARTESIA_API_KEY=...

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dental_bot
```

### 3. Start everything

```bash
bash start.sh
```

This script will:
1. Copy `.env.example` to `.env` if `.env` is missing
2. Install Python dependencies
3. Download VAD and turn-detector models (first run only)
4. Start the FastAPI backend on port 8000
5. Start the LiveKit agent worker

Open `http://localhost:8000` in your browser, click **Start Conversation**, and speak.

---

## Database Tables

| Table | What it stores |
|---|---|
| `call_metadata` | One row per call — room name, phone number, duration |
| `patient_data` | Patient profile collected during the call |
| `appointments` | Confirmed appointment bookings |
| `conversations` | Every turn of the conversation (user + assistant) |
| `evaluation_statistics` | Latency, token usage, and cost per session |
| `call_analysis` | Post-call AI analysis — intent, satisfaction, Q&A quality |

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `CLOUD_URL` | LiveKit Cloud WebSocket URL |
| `CLOUD_API_KEY` | LiveKit API key |
| `CLOUD_API_SECRET` | LiveKit API secret |
| `DEEPGRAM_API_KEY` | Deepgram STT key |
| `OPENAI_API_KEY` | OpenAI key (LLM + post-call analysis) |
| `CARTESIA_API_KEY` | Cartesia TTS key |
| `DATABASE_URL` | PostgreSQL connection string (asyncpg format) |
| `CLINIC_NAME` | Clinic name shown in responses |
| `CLINIC_PHONE` | Clinic phone number |
| `CLINIC_ADDRESS` | Clinic address |
| `CLINIC_HOURS` | Opening hours |
| `CLINIC_INSURANCE` | Accepted insurance providers |

---

## How the Bot Collects Information

The bot uses GPT-4o-mini to drive the conversation. It never follows a fixed script — it listens to what the patient says and captures information as it comes up naturally. It asks up to 2 missing fields at a time to keep the conversation efficient.

Fields collected:
- **Name** — patient's full name
- **DOB** — date of birth, stored as `DD-MM-YYYY`
- **Reason for visit** — tooth pain, cleaning, filling, etc.
- **Preferred time** — stored as `DD-MM-YYYY HH:MM:SS`
- **Insurance** — optional

If the patient mentions their reason before saying they want to book, the bot remembers it and will not ask again.
