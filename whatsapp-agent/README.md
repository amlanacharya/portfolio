<p align="center">
    <img alt="Ava" src="img/ava_final_design.gif" width=800 />
    <h1 align="center">Ava — AI WhatsApp Companion</h1>
    <h3 align="center">A production-grade multimodal AI agent that converses over WhatsApp</h3>
</p>

<p align="center">
    <img alt="WhatsApp" src="img/whatsapp_logo.png" width=80 />
</p>

---

## Overview

**Ava** is a fully autonomous AI companion that runs on WhatsApp. She can hold natural conversations, understand your voice, see your images, reply with voice notes, generate images of her activities, and remember details about you across sessions.

Ava is built on a LangGraph-orchestrated workflow backed by Groq, ElevenLabs, Together AI, and Qdrant — designed for both local development and cloud deployment on Google Cloud Run.

---

## Features

- **Text conversations** — Contextual, personality-driven responses powered by Llama 3.3 70B
- **Voice I/O** — Transcribes incoming voice notes (Whisper) and replies with synthesized speech (ElevenLabs)
- **Image understanding** — Analyses images you send using a vision model (Llama 3.2 Vision)
- **Image generation** — Sends back images of her current activities using FLUX diffusion models
- **Long-term memory** — Remembers facts about you across conversations via a Qdrant vector store
- **Activity awareness** — Knows what she is doing based on a realistic weekly schedule
- **Multi-interface** — Runs on WhatsApp (production) and Chainlit (local development/testing)

---

## Architecture

```
User (WhatsApp / Chainlit)
        │
        ▼
   FastAPI / Chainlit
        │
        ▼
   LangGraph Workflow
   ┌────────────────────────────────────────┐
   │ memory_extraction → router             │
   │        → context_injection             │
   │        → memory_injection              │
   │        → conversation / image / audio  │
   │        → summarize (if needed)         │
   └────────────────────────────────────────┘
        │
        ▼
   STT (Groq Whisper) · TTS (ElevenLabs) · Image Gen (FLUX) · Vision (Llama)
        │
        ▼
   Qdrant (long-term memory) · SQLite (short-term / conversation state)
```

---

## Tech Stack

| Technology | Role |
|------------|------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Workflow orchestration (state machine) |
| [Groq](https://groq.com) | LLM inference (Llama 3.3 70B, Llama 3.2 Vision, Whisper) |
| [ElevenLabs](https://elevenlabs.io) | Text-to-speech synthesis |
| [Together AI](https://www.together.ai) | Image generation (FLUX.1-schnell) |
| [Qdrant](https://qdrant.tech) | Vector database for long-term memory |
| [FastAPI](https://fastapi.tiangolo.com) | WhatsApp webhook server |
| [Chainlit](https://chainlit.io) | Web UI for local testing |
| [Docker](https://www.docker.com) | Containerised deployment |
| [Google Cloud Run](https://cloud.google.com/run) | Serverless cloud deployment |
| [uv](https://github.com/astral-sh/uv) | Python package management |

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- API keys for Groq, ElevenLabs, Together AI, and Qdrant Cloud

### Setup

```bash
# 1. Clone and enter the repo
git clone <your-repo-url>
cd whatsapp-agent

# 2. Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
uv pip install -e .

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see docs/GETTING_STARTED.md for details)
```

### Run locally

```bash
# Linux / macOS
make ava-run

# Windows (Command Prompt)
run.bat ava-run

# Windows (PowerShell)
.\run.ps1 ava-run
```

This starts three services via Docker Compose:

| Service | URL |
|---------|-----|
| Chainlit UI (local testing) | http://localhost:8000 |
| FastAPI WhatsApp webhook | http://localhost:8080/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |

Open the Chainlit URL to start chatting with Ava immediately — no WhatsApp setup required.

To stop and clean up:

```bash
make ava-delete
```

### Connect WhatsApp (production)

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for full setup instructions including WhatsApp Cloud API configuration and deployment to Google Cloud Run.

---

## Project Structure

```
src/ai_companion/
├── settings.py                    # Central configuration (Pydantic Settings)
├── core/
│   ├── exceptions.py              # Custom exception types
│   ├── prompts.py                 # LLM system prompts
│   └── schedules.py               # Ava's weekly activity schedule
├── graph/
│   ├── graph.py                   # LangGraph workflow assembly
│   ├── nodes.py                   # 8 async workflow nodes
│   ├── edges.py                   # Conditional routing logic
│   ├── state.py                   # AICompanionState definition
│   └── utils/
│       ├── chains.py              # LLM chain factories
│       └── helpers.py             # Model helper utilities
├── modules/
│   ├── image/
│   │   ├── text_to_image.py       # FLUX image generation
│   │   └── image_to_text.py       # Vision model analysis
│   ├── memory/long_term/
│   │   ├── memory_manager.py      # Memory orchestration
│   │   └── vector_store.py        # Qdrant vector store (singleton)
│   ├── schedules/
│   │   └── context_generation.py  # Real-time activity lookup
│   └── speech/
│       ├── speech_to_text.py      # Groq Whisper STT
│       └── text_to_speech.py      # ElevenLabs TTS
└── interfaces/
    ├── chainlit/app.py            # Chainlit web UI
    └── whatsapp/
        ├── webhook_endpoint.py    # FastAPI app entry point
        └── whatsapp_response.py   # WhatsApp Cloud API integration
```

---

## Configuration

All configuration is environment-driven via `.env`. Key variables:

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Groq API access |
| `ELEVENLABS_API_KEY` | ElevenLabs TTS |
| `ELEVENLABS_VOICE_ID` | Voice selection |
| `TOGETHER_API_KEY` | Image generation |
| `QDRANT_URL` | Qdrant Cloud endpoint |
| `QDRANT_API_KEY` | Qdrant Cloud auth |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Cloud API |
| `WHATSAPP_TOKEN` | WhatsApp Cloud API bearer token |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token |

Model selections and behaviour parameters can be overridden in `.env` — see `src/ai_companion/settings.py` for all available options.

---

## Deployment

The project includes a full Google Cloud Run deployment pipeline:

```bash
# Build and deploy via Cloud Build
gcloud builds submit --config cloudbuild.yaml
```

See [docs/gcp_setup.md](docs/gcp_setup.md) for GCP project configuration and IAM setup.

---

## License

MIT — see [LICENSE](LICENSE).
