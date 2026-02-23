# Build Plan: Ava WhatsApp Companion (From Scratch)


## Context

This plan provides a sequential code-writing order for building Ava — a production-grade multimodal AI companion that operates over WhatsApp. The system enables text, voice, and image conversations where an AI persona (Ava) can remember past interactions, generate images, and respond in natural language with voice synthesis.

**Core Architecture**: User Input (Text/Audio/Image) → Interface (WhatsApp / Chainlit) → LangGraph Workflow → Multimodal Modules → Long-term Memory → Response

**Why this sequence**: Each step builds on proven foundations. You validate components in isolation before integration, reducing debugging complexity.

---

## Build Sequence: First Code to Last


### Phase 1: Foundation (Steps 1–2)


#### 1. Configuration System

**File**: `src/ai_companion/settings.py`

Create a Pydantic `BaseSettings` class loading all service configuration from environment:

- API keys: `GROQ_API_KEY`, `ELEVENLABS_API_KEY`, `TOGETHER_API_KEY`, `QDRANT_API_KEY`
- Voice: `ELEVENLABS_VOICE_ID`
- WhatsApp: `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TOKEN`, `WHATSAPP_VERIFY_TOKEN`
- Model names: `TEXT_MODEL_NAME`, `STT_MODEL_NAME`, `TTS_MODEL_NAME`, `TTI_MODEL_NAME`, `ITT_MODEL_NAME`
- Memory params: `MEMORY_TOP_K`, `ROUTER_MESSAGES_TO_ANALYZE`, `TOTAL_MESSAGES_SUMMARY_TRIGGER`
- Database: `SHORT_TERM_MEMORY_DB_PATH`

**Why first**: Every subsequent module imports `settings`. Centralises all configuration before any implementation.

**Verify**:

```python
from ai_companion.settings import settings
print(settings.TEXT_MODEL_NAME)    # llama-3.3-70b-versatile
assert settings.MEMORY_TOP_K == 3
```

---

#### 2. Custom Exceptions

**File**: `src/ai_companion/core/exceptions.py`

Define typed exceptions for each module boundary:

- `SpeechToTextError`
- `TextToSpeechError`
- `TextToImageError`
- `ImageToTextError`

**Why now**: Establish error vocabulary before writing modules. Enables callers to catch specific failures without exposing third-party exceptions.

**Verify**:

```python
from ai_companion.core.exceptions import SpeechToTextError
try:
    raise SpeechToTextError("audio decode failed")
except SpeechToTextError as e:
    assert str(e) == "audio decode failed"
```

---

### Phase 2: Multimodal Modules (Steps 3–6)


#### 3. Speech-to-Text

**File**: `src/ai_companion/modules/speech/speech_to_text.py`

Implement `SpeechToText` class:

- `async transcribe(audio_data: bytes) -> str`
- Uses Groq Whisper (`whisper-large-v3-turbo`)
- Writes audio bytes to a temp file, calls the Groq transcription API, cleans up
- Raises `SpeechToTextError` on failure

**Why now**: Required by both the WhatsApp and Chainlit interfaces. Has no dependencies beyond `settings` and `exceptions`.

**Verify**:

```python
import asyncio
from ai_companion.modules.speech.speech_to_text import SpeechToText

stt = SpeechToText()
result = asyncio.run(stt.transcribe(open("test.wav", "rb").read()))
assert len(result) > 0
```

---

#### 4. Text-to-Speech

**File**: `src/ai_companion/modules/speech/text_to_speech.py`

Implement `TextToSpeech` class:

- `async synthesize(text: str) -> bytes`
- Uses ElevenLabs (`eleven_flash_v2_5` model)
- Validates max 5000 characters
- Configurable `stability` and `similarity_boost` via `VoiceSettings`
- Raises `TextToSpeechError` on failure

**Why now**: Required by the `audio_node` in the LangGraph workflow. Independent of all other modules.

**Verify**:

```python
from ai_companion.modules.speech.text_to_speech import TextToSpeech
tts = TextToSpeech()
audio = asyncio.run(tts.synthesize("Hello, I am Ava."))
assert isinstance(audio, bytes) and len(audio) > 0
```

---

#### 5. Image Generation

**File**: `src/ai_companion/modules/image/text_to_image.py`

Implement `TextToImage` class:

- `async generate_image(prompt: str, output_path: str = "") -> bytes`
  - Calls Together AI FLUX.1-schnell, returns base64-decoded image bytes
  - Optionally saves to file
- `async create_scenario(chat_history: list) -> ScenarioPrompt`
  - Uses LLM to produce a first-person narrative + image prompt from chat history
  - Returns `ScenarioPrompt(scenario_text, image_prompt)` Pydantic model
- `async enhance_prompt(prompt: str) -> str`
  - Passes prompt through LLM for quality improvement
- Raises `TextToImageError` on failure

**Why now**: Required by `image_node`. Can be verified in isolation without the full workflow.

**Verify**:

```python
from ai_companion.modules.image.text_to_image import TextToImage
tti = TextToImage()
image_bytes = asyncio.run(tti.generate_image("a sunset over the San Francisco bay"))
assert len(image_bytes) > 1000
```

---

#### 6. Image Analysis (Vision)

**File**: `src/ai_companion/modules/image/image_to_text.py`

Implement `ImageToText` class:

- `async analyze_image(image_data: Union[str, bytes], prompt: str = "") -> str`
  - Accepts a file path (str) or raw bytes
  - Converts to base64, calls Groq Vision (`llama-3.2-90b-vision-preview`)
  - Returns natural language description
- Raises `ImageToTextError` on failure

**Why now**: Required by WhatsApp and Chainlit interfaces when users send images.

**Verify**:

```python
from ai_companion.modules.image.image_to_text import ImageToText
itt = ImageToText()
result = asyncio.run(itt.analyze_image("test_image.jpg"))
assert len(result) > 0
```

---

### Phase 3: Memory System (Steps 7–8)


#### 7. Vector Store

**File**: `src/ai_companion/modules/memory/long_term/vector_store.py`

Implement `VectorStore` as a singleton class backed by Qdrant:

- `EMBEDDING_MODEL = "all-MiniLM-L6-v2"` (via `sentence-transformers`)
- `COLLECTION_NAME = "long_term_memory"`
- `SIMILARITY_THRESHOLD = 0.9`
- `store_memory(text: str, metadata: dict) -> None`
- `search_memories(query: str, k: int = 5) -> List[Memory]`
- `find_similar_memory(text: str) -> Optional[Memory]` — dedup guard
- `Memory` dataclass with `text`, `metadata`, `score` fields
- `get_vector_store()` factory function

Connects to Qdrant Cloud if `QDRANT_API_KEY` is set, otherwise local Qdrant.

**Why now**: Foundation of long-term memory. Must exist before the MemoryManager.

**Verify**:

```python
from ai_companion.modules.memory.long_term.vector_store import get_vector_store
vs = get_vector_store()
vs.store_memory("User lives in Barcelona", {"id": "test-1", "timestamp": "2024-01-01"})
results = vs.search_memories("Where does the user live?", k=1)
assert "Barcelona" in results[0].text
```

---

#### 8. Memory Manager

**File**: `src/ai_companion/modules/memory/long_term/memory_manager.py`

Implement `MemoryManager` class orchestrating the full memory lifecycle:

- `MemoryAnalysis` Pydantic model: `is_important: bool`, `formatted_memory: Optional[str]`
- `async _analyze_memory(message: str) -> MemoryAnalysis` — LLM call (Gemma2 9B) with `MEMORY_ANALYSIS_PROMPT`
- `async extract_and_store_memories(message: BaseMessage) -> None`
  - Only processes `human` messages
  - Skips if LLM deems not important
  - Dedup via `find_similar_memory()`
- `get_relevant_memories(context: str) -> List[str]` — searches top K
- `format_memories_for_prompt(memories: List[str]) -> str` — bullet-point formatter
- `get_memory_manager()` factory function

**Why now**: Wraps the vector store with business logic. Required by graph nodes.

**Verify**:

```python
from ai_companion.modules.memory.long_term.memory_manager import get_memory_manager
mgr = get_memory_manager()
formatted = mgr.format_memories_for_prompt(["User likes jazz", "User has a dog"])
assert formatted == "- User likes jazz\n- User has a dog"
```

---

### Phase 4: Character & Context (Steps 9–11)


#### 9. Prompts

**File**: `src/ai_companion/core/prompts.py`

Define all system prompts as module-level string constants:

- `ROUTER_PROMPT` — Routes to `conversation`, `image`, or `audio` based on message history
- `CHARACTER_CARD_PROMPT` — Full persona definition for Ava (name, background, personality, communication style, rules)
- `IMAGE_SCENARIO_PROMPT` — Instructs the LLM to produce a first-person scenario + image generation prompt
- `IMAGE_ENHANCEMENT_PROMPT` — Improves a raw image prompt for diffusion model quality
- `MEMORY_ANALYSIS_PROMPT` — Extracts and formats factual information from a user message (structured output)

**Why now**: Prompts are pure strings with no dependencies. All graph chains depend on them.

**Verify**:

```python
from ai_companion.core.prompts import CHARACTER_CARD_PROMPT, ROUTER_PROMPT
assert "Ava" in CHARACTER_CARD_PROMPT
assert "conversation" in ROUTER_PROMPT
```

---

#### 10. Activity Schedules

**File**: `src/ai_companion/core/schedules.py`

Define one dict per weekday (`MONDAY_SCHEDULE` through `SUNDAY_SCHEDULE`):

- Keys: time ranges as `"HH:MM-HH:MM"` strings
- Values: activity description strings (e.g., `"Ava starts her day with a morning run along the Embarcadero"`)
- Must cover the full 24-hour period including overnight slots

**Why now**: Pure data — no dependencies. Required by the context generator.

**Verify**:

```python
from ai_companion.core.schedules import MONDAY_SCHEDULE
assert isinstance(MONDAY_SCHEDULE, dict)
assert len(MONDAY_SCHEDULE) > 0
```

---

#### 11. Schedule Context Generator

**File**: `src/ai_companion/modules/schedules/context_generation.py`

Implement `ScheduleContextGenerator` class:

- `SCHEDULES` dict mapping weekday int (0=Monday) to schedule dict
- `@staticmethod _parse_time_range(time_range: str) -> tuple[time, time]`
- `@classmethod get_current_activity(cls) -> Optional[str]`
  - Gets real system time
  - Handles overnight slots (start > end)
  - Returns activity string or `None`
- `@classmethod get_schedule_for_day(cls, day: int) -> Dict[str, str]`

**Why now**: Provides real-time character context. Required by `context_injection_node`.

**Verify**:

```python
from ai_companion.modules.schedules.context_generation import ScheduleContextGenerator
activity = ScheduleContextGenerator.get_current_activity()
assert activity is None or isinstance(activity, str)
```

---

### Phase 5: LangGraph Workflow (Steps 12–16)


#### 12. Workflow State

**File**: `src/ai_companion/graph/state.py`

Define `AICompanionState` extending LangGraph's `MessagesState`:

```python
class AICompanionState(MessagesState):
    summary: str          # Rolling conversation summary
    workflow: str         # Selected branch: "conversation" | "image" | "audio"
    audio_buffer: bytes   # Synthesised audio bytes for audio responses
    image_path: str       # Path to generated image file
    current_activity: str # Ava's current real-time activity
    apply_activity: bool  # Whether to inject activity context
    memory_context: str   # Formatted long-term memories
```

**Why now**: State is the contract all nodes communicate through. Must exist before any node.

---

#### 13. Chains & Helpers

**Files**:
- `src/ai_companion/graph/utils/chains.py`
- `src/ai_companion/graph/utils/helpers.py`

**chains.py**:

- `RouterResponse(BaseModel)` — `response_type: str`
- `get_router_chain()` — ChatGroq (temp 0.3) with structured output → `RouterResponse`
- `get_character_response_chain(summary: str = "")` — ChatGroq with `CHARACTER_CARD_PROMPT`, supports optional conversation summary injection
- `AsteriskRemovalParser` — `StrOutputParser` subclass that strips `*asterisk content*` from responses

**helpers.py**:

- `get_chat_model(temperature: float = 0.7) -> ChatGroq`
- `get_text_to_speech_module() -> TextToSpeech`
- `get_text_to_image_module() -> TextToImage`

**Why now**: Chains are stateless factories. Nodes import them directly.

---

#### 14. Conditional Edges

**File**: `src/ai_companion/graph/edges.py`

Implement two routing functions:

- `select_workflow(state) -> Literal["conversation_node", "image_node", "audio_node"]`
  - Reads `state["workflow"]`, dispatches accordingly
- `should_summarize_conversation(state) -> Literal["summarize_conversation_node", "__end__"]`
  - Returns `"summarize_conversation_node"` if `len(messages) > TOTAL_MESSAGES_SUMMARY_TRIGGER`

**Why now**: Required to wire the graph. Depends on State and settings.

---

#### 15. Workflow Nodes

**File**: `src/ai_companion/graph/nodes.py`

Implement 8 async node functions (all receive/return `AICompanionState`):

1. **`memory_extraction_node`** — Calls `MemoryManager.extract_and_store_memories()` on the last human message
2. **`router_node`** — Runs router chain on last N messages, sets `state["workflow"]`
3. **`context_injection_node`** — Calls `ScheduleContextGenerator.get_current_activity()`, injects as system message if found
4. **`memory_injection_node`** — Calls `MemoryManager.get_relevant_memories()`, injects formatted memories as system message
5. **`conversation_node`** — Streams response from character response chain, returns AI message
6. **`image_node`** — Calls `TextToImage.create_scenario()` then `generate_image()`, returns scenario text + sets `image_path`
7. **`audio_node`** — Calls conversation chain then `TextToSpeech.synthesize()`, sets `audio_buffer`
8. **`summarize_conversation_node`** — Compresses old messages into `state["summary"]`, trims to `TOTAL_MESSAGES_AFTER_SUMMARY`

**Why now**: All dependencies (state, chains, modules, memory) are ready.

**Verify**:

```python
from ai_companion.graph.nodes import (
    memory_extraction_node, router_node, conversation_node,
    image_node, audio_node, summarize_conversation_node,
)
```

---

#### 16. Graph Assembly

**File**: `src/ai_companion/graph/graph.py`

Assemble the full workflow with `StateGraph`:

```
START
  → memory_extraction_node
  → router_node
  → context_injection_node
  → memory_injection_node
  → [select_workflow] → conversation_node | image_node | audio_node
  → [should_summarize] → summarize_conversation_node | END
```

- Wrap with `@lru_cache(maxsize=1)` — graph is expensive to build
- Export `graph = create_workflow_graph().compile()`

**Why now**: All nodes and edges exist. This is the integration point.

**Verify**:

```python
from ai_companion.graph import graph
assert graph is not None
print(graph.get_graph().print_ascii())
```

---

### Phase 6: Interfaces (Steps 17–18)


#### 17. Chainlit Web UI

**File**: `src/ai_companion/interfaces/chainlit/app.py`

Wire LangGraph to Chainlit's event model:

- `@cl.on_chat_start` — initialise `AsyncSqliteSaver` checkpointer, store `thread_id` in user session
- `@cl.on_message` — handle text + image inputs:
  - If image attached: call `ImageToText.analyze_image()`, prepend description to message
  - Invoke graph, stream response tokens
  - If `audio_buffer` in state: send audio element
  - If `image_path` in state: send image element
- `@cl.on_audio_chunk` / `@cl.on_audio_end` — accumulate audio bytes, transcribe with STT, invoke graph

**Why now**: All backend components are ready. This provides a full local test harness before WhatsApp.

**Verify**:

```bash
chainlit run src/ai_companion/interfaces/chainlit/app.py
# Open http://localhost:8000 and send a text message
```

---

#### 18. WhatsApp Webhook

**Files**:
- `src/ai_companion/interfaces/whatsapp/webhook_endpoint.py` — FastAPI app, includes router
- `src/ai_companion/interfaces/whatsapp/whatsapp_response.py` — all webhook logic

Implement the full WhatsApp Cloud API integration:

- `GET /webhook` — verification endpoint (echo back hub challenge)
- `POST /webhook` — main message handler (`whatsapp_handler`):
  - Parse incoming JSON for message type
  - Dispatch to `process_audio_message()` (STT → graph) or direct text/image processing
  - Call `send_response()` with appropriate message type
- `async download_media(media_id: str) -> bytes` — download audio/image from WhatsApp servers
- `async send_response(from_number, response_text, message_type)` — routes to text, audio, or image send
- `async upload_media(media_content: BytesIO, mime_type: str) -> str` — upload to WhatsApp media API

**Why now**: Final integration layer. The agent runs; add the phone channel.

**Verify**:

```bash
uvicorn ai_companion.interfaces.whatsapp.webhook_endpoint:app --reload --port 8080
curl http://localhost:8080/docs
```

---

### Phase 7: Deployment (Steps 19–20)


#### 19. Docker

**Files**:
- `Dockerfile` — FastAPI/WhatsApp container (Python 3.12, uv, all dependencies)
- `Dockerfile.chainlit` — Chainlit UI container
- `docker-compose.yml` — Qdrant + Chainlit + FastAPI local stack

Compose services:

| Service | Port | Purpose |
|---------|------|---------|
| `qdrant` | 6333 | Vector database |
| `chainlit` | 8000 | Web chat UI |
| `fastapi` | 8080 | WhatsApp webhook |

**Why now**: Application works locally. Package it for repeatable deployment.

**Verify**:

```bash
docker compose up --build
curl http://localhost:8080/docs
# Open http://localhost:8000
```

---

#### 20. Cloud Deployment

**Files**:
- `cloudbuild.yaml` — Google Cloud Build pipeline (build + push + deploy to Cloud Run)
- `Makefile` — `ava-run`, `ava-delete` targets for local compose management

Deploy to Cloud Run:

```bash
gcloud builds submit --config cloudbuild.yaml
# Get the deployed URL, configure as WhatsApp webhook
```

Configure WhatsApp webhook URL in Meta Developer Portal:

```
https://<your-cloud-run-url>/webhook
```

**Verify**:

```bash
curl https://<your-cloud-run-url>/docs
# Send a WhatsApp message to your registered number
# Verify: message → webhook → STT/text → LangGraph → TTS/image → WhatsApp reply
```

---

## Critical Files Overview

**Core 5 Files** (backbone of the system):

1. `src/ai_companion/settings.py` — Central configuration hub
2. `src/ai_companion/graph/graph.py` — Main orchestrator (LangGraph workflow)
3. `src/ai_companion/modules/memory/long_term/vector_store.py` — Memory persistence
4. `src/ai_companion/interfaces/whatsapp/whatsapp_response.py` — WhatsApp integration point
5. `src/ai_companion/graph/nodes.py` — All business logic (8 nodes)

---

## Dependencies Summary

```
Settings (Step 1)
  ↓
Exceptions (Step 2)
  ↓
STT Module (Step 3)
TTS Module (Step 4)
Image Gen  (Step 5)
Vision     (Step 6)
  ↓
Vector Store (Step 7)
  ↓
Memory Manager (Step 8)

Prompts (Step 9) ──────────────────────┐
Schedules (Step 10)                    │
  ↓                                    │
Context Generator (Step 11)            │
                                       ↓
                             LangGraph State (Step 12)
                                       ↓
                          Chains & Helpers (Step 13)
                                       ↓
                           Conditional Edges (Step 14)
                                       ↓
                            Workflow Nodes (Step 15)
                                       ↓
                           Graph Assembly (Step 16)
                                       ↓
                     Chainlit UI (Step 17) ─────────┐
                     WhatsApp Webhook (Step 18) ─────┤
                                                     ↓
                                          Docker (Step 19)
                                                     ↓
                                     Cloud Deployment (Step 20)
```

---

## Verification Strategy

Each phase produces a testable unit:

- **Phase 1–2**: Import tests, exception raises
- **Phase 2**: Direct API calls to Groq / ElevenLabs / Together AI (real keys required)
- **Phase 3**: Store and retrieve memories from local Qdrant
- **Phase 4**: Python import checks, schedule coverage assertions
- **Phase 5**: LangGraph graph compilation, node import checks
- **Phase 6**: Chainlit UI smoke test, `curl` against FastAPI webhook
- **Phase 7**: `docker compose up`, Cloud Run health check, live WhatsApp message

**Testing philosophy**: Validate each component in isolation before integration. Each step should be demonstrable and working before proceeding to the next.
