# Quick Start Guide

Get your Realtime Phone Agent system up and running in minutes.

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- API Keys for:
  - Groq (required for LLM)
  - OpenAI (required for natural query parsing)
  - Qdrant (optional, for cloud deployment)
  - Twilio (required for phone integration)
  - RunPod (optional, for GPU acceleration)
  - Opik (optional, for observability)

---

## Installation

### 1. Clone and Setup

```bash
cd realtime-phone-agents-course

# Install uv package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Required - LLM Service
GROQ__API_KEY=your_groq_key_here
GROQ__MODEL=openai/gpt-oss-20b

# Required - Natural Language Query Processing
OPENAI__API_KEY=your_openai_key_here
OPENAI__MODEL=gpt-4o-mini

# Required - Phone Integration
TWILIO__ACCOUNT_SID=your_twilio_sid_here
TWILIO__AUTH_TOKEN=your_twilio_token_here

# Optional - Cloud Vector Database (or use local Qdrant via Docker)
QDRANT__USE_QDRANT_CLOUD=false  # Set to true for cloud
QDRANT__HOST=qdrant
QDRANT__PORT=6333

# Optional - STT/TTS Model Selection
STT_MODEL=whisper-groq  # Options: whisper-groq, moonshine, faster-whisper
TTS_MODEL=kokoro        # Options: kokoro, orpheus-runpod, together

# Optional - Observability
OPIK__API_KEY=your_opik_key_here
OPIK__PROJECT_NAME=phone-calling-agents
```

---

## Running Locally

### Option 1: Docker Compose (Recommended)

```bash
# Start all services (API + Qdrant)
docker-compose up --build

# In another terminal, ingest property data
python scripts/ingest_properties.py
```

The API will be available at `http://localhost:8000`

### Option 2: Direct Python Execution

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the API
uvicorn realtime_phone_agents.api.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, ingest data
python scripts/ingest_properties.py
```

---

## Testing the System

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "message": "Service is ready"
}
```

### 2. Test Property Search

```bash
curl -X POST http://localhost:8000/superlinked/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "3 bedroom apartment in Barcelona under 500k",
    "limit": 3
  }'
```

### 3. View API Documentation

Open your browser to: `http://localhost:8000/docs`

---

## Making Phone Calls

### Configure Twilio Webhook

1. Log into your Twilio account
2. Go to your phone number settings
3. Under "Voice Configuration" → "A Call Comes In"
4. Set the webhook URL to: `https://your-domain.com/voice/telephone/incoming`
5. Set HTTP method to: `POST`

**Note**: For local testing, use ngrok or similar to expose your local server:
```bash
ngrok http 8000
# Use the ngrok URL: https://abc123.ngrok.io/voice/telephone/incoming
```

### Test Inbound Calls

1. Call your Twilio number
2. The AI agent will answer and greet you
3. Try asking: "Do you have any apartments in Barcelona?"

### Test Outbound Calls

```bash
python scripts/make_outbound_call.py
```

Follow the interactive prompts to:
- Enter your Twilio phone number
- Enter your voice agent URL (e.g., https://abc123.ngrok.io)
- Enter the recipient's phone number

---

## Avatar Selection

The system includes 8 pre-configured avatars with different personalities:

- **Tara** (default) - Energetic and enthusiastic
- **Leo** - Professional and experienced
- **Mia** - Warm and friendly
- **Zoe** - Tech-savvy and modern
- **Dan** - Analytical and detail-oriented
- **Jess** - Creative and personable
- **Leah** - Calm and reassuring
- **Zac** - Dynamic and energetic

Change the avatar by setting in `.env`:
```bash
AVATAR_NAME=leo
```

---

## Model Selection

### Speech-to-Text (STT) Options

```bash
# In .env
STT_MODEL=whisper-groq    # Fast, API-based (recommended for quick start)
STT_MODEL=moonshine       # Local, no API needed (requires more resources)
STT_MODEL=faster-whisper  # RunPod deployment (best quality)
```

### Text-to-Speech (TTS) Options

```bash
# In .env
TTS_MODEL=kokoro          # Local, fast (recommended for quick start)
TTS_MODEL=orpheus-runpod  # RunPod deployment (best quality)
TTS_MODEL=together        # Together AI API (easy setup)
```

---

## Common Commands

### Data Management

```bash
# Ingest properties from CSV
python scripts/ingest_properties.py

# Using API endpoint
curl -X POST http://localhost:8000/superlinked/ingest \
  -H "Content-Type: application/json" \
  -d '{"data_path": "data/properties.csv"}'
```

### Docker Operations

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build
```

### Development

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy src/
```

---

## Troubleshooting

### Issue: "Connection refused" on API calls

**Solution**: Ensure the API is running:
```bash
docker-compose ps
# or
curl http://localhost:8000/health
```

### Issue: "No properties found" in searches

**Solution**: Ingest the property data:
```bash
python scripts/ingest_properties.py
```

### Issue: Twilio calls not connecting

**Solutions**:
1. Verify webhook URL is publicly accessible
2. Check Twilio credentials in `.env`
3. Ensure phone numbers are in E.164 format (+1234567890)
4. Check Twilio console logs for errors

### Issue: STT/TTS not working

**Solutions**:
1. Verify API keys are set correctly
2. Check model selection in `.env`
3. For local models, ensure sufficient system resources
4. For RunPod models, verify endpoint URLs

### Issue: Qdrant connection errors

**Solutions**:
1. For local: Ensure Qdrant container is running
2. For cloud: Verify credentials and cluster URL
3. Check `QDRANT__USE_QDRANT_CLOUD` setting

---

## Environment Variables Reference

### Required Variables

```bash
GROQ__API_KEY              # Groq API key for LLM
OPENAI__API_KEY            # OpenAI key for query parsing
TWILIO__ACCOUNT_SID        # Twilio account identifier
TWILIO__AUTH_TOKEN         # Twilio authentication token
```

### Optional Variables

```bash
STT_MODEL                  # whisper-groq | moonshine | faster-whisper
TTS_MODEL                  # kokoro | orpheus-runpod | together
AVATAR_NAME                # tara | leo | mia | zoe | dan | jess | leah | zac
QDRANT__USE_QDRANT_CLOUD   # true | false
OPIK__API_KEY              # For observability (optional)
```

---

## Next Steps

1. ✅ System running locally
2. ✅ Property data ingested
3. ✅ API tests passing
4. 📞 Configure Twilio webhook
5. 📱 Test phone calls
6. 🚀 Deploy to production
7. 📊 Set up Opik monitoring
8. ⚡ Deploy RunPod services for GPU acceleration

---

## Getting Help

- Check `IMPLEMENTATION_STATUS.md` for detailed system information
- Review `README.md` for project overview
- View API docs at `http://localhost:8000/docs`
- Check logs: `docker-compose logs -f phone-calling-agent-api`

---

## Production Deployment

For production deployment instructions, see:
- RunPod deployment: `scripts/runpod/`
- Docker deployment: `Dockerfile`, `docker-compose.yml`
- Environment configuration: `.env.example`

Happy building! 🎉
