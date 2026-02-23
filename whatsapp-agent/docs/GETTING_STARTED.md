# Getting Started

This guide walks you through setting up and running the Ava WhatsApp agent locally.

---

## 1. Clone the repository

```bash
git clone <your-repo-url>
cd whatsapp-agent
```

---

## 2. Install uv

This project uses [uv](https://docs.astral.sh/uv/) as the Python package manager.

Install it by following the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

---

## 3. Install project dependencies

Create a virtual environment and install all dependencies:

```bash
uv venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.\.venv\Scripts\activate

uv pip install -e .
```

Verify the Python version:

```bash
uv run python --version
# Expected: Python 3.12.x
```

---

## 4. Configure environment variables

Copy the example env file and fill in your API keys:

```bash
cp .env.example .env
```

Open `.env` and set the following values:

```
GROQ_API_KEY=""
ELEVENLABS_API_KEY=""
ELEVENLABS_VOICE_ID=""
TOGETHER_API_KEY=""
QDRANT_URL=""
QDRANT_API_KEY=""
WHATSAPP_PHONE_NUMBER_ID=""
WHATSAPP_TOKEN=""
WHATSAPP_VERIFY_TOKEN=""
```

### Groq

Create a free API key at [console.groq.com](https://console.groq.com/docs/quickstart). This powers LLM inference, vision, and speech-to-text.

![Groq API Key](img/groq_api_key.png)

### ElevenLabs

Create an account at [elevenlabs.io](https://elevenlabs.io/), then generate an API key from your account settings. For the voice ID, browse the available voices and copy the ID of your preferred voice.

![ElevenLabs API Key](img/elevenlabs_api_key.png)

### Together AI

Log in to [together.ai](https://www.together.ai/) and create an API key from your account settings. This is used for image generation.

![Together AI API Key](img/together_api_key.png)

### Qdrant

This project uses Qdrant for long-term memory storage. You can run it locally via Docker (included in the Docker Compose file) or use [Qdrant Cloud](https://cloud.qdrant.io/).

For Qdrant Cloud:
1. Create a free cluster
2. Copy the **API key** and **cluster URL** into your `.env`

![Qdrant API Key](img/qdrant_api_key.png)

![Qdrant URL](img/qdrant_url.png)

For local-only development, you can leave `QDRANT_URL=http://localhost:6333` and `QDRANT_API_KEY` empty — the Docker Compose stack handles the local Qdrant instance automatically.

### WhatsApp (optional for local testing)

The `WHATSAPP_*` variables are only needed for the production WhatsApp webhook. For local development and testing, use the Chainlit UI at `http://localhost:8000` — no WhatsApp configuration required.

See [WhatsApp Cloud API setup](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started) for production configuration.

---

## 5. Run locally

Start the full stack with Docker Compose:

```bash
# Linux / macOS
make ava-run

# Windows (Command Prompt)
run.bat ava-run

# Windows (PowerShell)
.\run.ps1 ava-run
```

This starts three services:

| Service | URL | Purpose |
|---------|-----|---------|
| Chainlit UI | http://localhost:8000 | Interactive chat interface for testing |
| FastAPI | http://localhost:8080/docs | WhatsApp webhook + API |
| Qdrant | http://localhost:6333/dashboard | Vector DB dashboard |

Open the Chainlit URL to start chatting with Ava. All multimodal features (voice, images, memory) are available in this interface.

![Ava Chainlit](img/ava_chainlit.png)

---

## 6. Clean up

To stop the stack and remove all local data volumes:

```bash
make ava-delete
```

---

## Deployment to Google Cloud Run

For production deployment, see [gcp_setup.md](gcp_setup.md).
