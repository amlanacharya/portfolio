# Realtime Phone Agent System

A production-grade AI phone agent system that enables voice conversations over phone calls with semantic property search capabilities.

## Overview

This system combines voice communication with intelligent real estate property search, allowing users to have natural conversations with an AI agent that can search and recommend properties based on their requirements.

**Architecture**: Phone Call (Twilio) → WebRTC Audio Stream → Speech-to-Text → LangChain Agent → Property Search Tool → Text-to-Speech → Audio Response

## Features

- ☎️ Inbound and outbound phone calls via Twilio
- 🎙️ Real-time speech-to-text with multiple model options (Groq Whisper, Moonshine, Faster Whisper)
- 🗣️ Text-to-speech with multiple voices (Kokoro, Orpheus, Together AI)
- 🏠 Semantic property search powered by Superlinked and Qdrant
- 🤖 Multi-avatar personality system
- 📊 Full observability with Opik tracing
- 🚀 GPU-accelerated deployment on RunPod

## Quick Start

### Prerequisites

- Python 3.11+
- uv package manager
- Docker and Docker Compose (for local development)
- Twilio account for phone integration
- API keys for: Groq, OpenAI, Qdrant, RunPod (optional), Opik (optional)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd realtime-phone-agents-course
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. Start local services with Docker Compose:
```bash
docker-compose up -d
```

5. Ingest property data:
```bash
python scripts/ingest_properties.py --data-path data/properties.csv
```

6. Run the application:
```bash
uvicorn realtime_phone_agents.api.main:app --reload
```

## Configuration

All configuration is managed through environment variables. Key settings include:

- **STT Model**: Choose from `whisper-groq`, `moonshine`, or `faster-whisper`
- **TTS Model**: Choose from `kokoro`, `orpheus-runpod`, or `together`
- **Qdrant**: Configure for local or cloud deployment
- **Twilio**: Set account SID and auth token for phone integration

See `.env.example` for complete configuration options.

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /search` - Property search API
- `WebSocket /voice` - Voice stream endpoint for Twilio integration
- `POST /call` - Initiate outbound calls

API documentation available at `http://localhost:8000/docs`

## Avatar System

The system supports multiple AI personalities (avatars) with customizable communication styles. Avatars are defined in YAML files in `src/realtime_phone_agents/avatars/definitions/`.

## Deployment

### Local Development
```bash
docker-compose up --build
```

### RunPod Deployment
Use the provided scripts to deploy GPU-accelerated services:
```bash
python scripts/runpod/create_faster_whisper_pod.py
python scripts/runpod/create_orpheus_pod.py
python scripts/runpod/create_call_center_pod.py
```

## Project Structure

```
.
├── src/realtime_phone_agents/
│   ├── agent/              # Core agent and tools
│   ├── api/                # FastAPI application
│   ├── avatars/            # Avatar personality system
│   ├── background_effects/ # Audio effects
│   ├── infrastructure/     # Superlinked & Qdrant integration
│   ├── observability/      # Opik tracing
│   ├── stt/                # Speech-to-text models
│   ├── tts/                # Text-to-speech models
│   └── config.py           # Configuration system
├── scripts/                # Deployment and utility scripts
├── data/                   # Property data files
└── docker-compose.yml      # Local development stack
```

## Usage Examples

### Making an Outbound Call
```bash
python scripts/make_outbound_call.py --to "+1234567890"
```

### Searching Properties via API
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "3 bedroom apartment in Barcelona under 500k", "limit": 5}'
```

## License

See LICENSE file for details.

## Support

For issues and questions, please refer to the project's issue tracker.
