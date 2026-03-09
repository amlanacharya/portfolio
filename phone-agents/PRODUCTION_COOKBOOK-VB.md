# Collections Voicebot - Production Cookbook

## Line Item

> "Delivered a production-grade AI voicebot for automated debt collections at an Indian NBFC, handling ~1,000 outbound calls/day in English and Hindi with mid-call language switching, LLM-driven Promise-to-Pay (PTP) extraction, persistent borrower memory via mem0, and full TRAI/RBI/DPDP Act compliance — deployed on AWS ECS Fargate in the Mumbai region (December 2024)."

---

## Pre-Analysis

- **Core system/product**: Automated outbound voice collections agent that calls borrowers, negotiates repayment commitments, extracts structured PTP dates, and stores borrower preferences for follow-up campaigns
- **Tech stack signals**: Exotel telephony, Azure Speech Services (en-IN + hi-IN with Continuous LID), Azure Neural TTS, GPT-4o-mini via Azure OpenAI, LangChain 0.3 ReAct, mem0, Redis, PostgreSQL + pgvector, DynamoDB, AWS ECS Fargate, LangSmith
- **Scale/impact signals**: ~1,000 calls/day, mid-scale NBFC, real money at stake (NPAs), regulatory exposure (RBI Fair Practices Code violation = license risk)
- **Domain context**: Indian NBFC / Fintech collections, bilingual borrowers, Promise-to-Pay negotiation, TRAI DND/NDNC mandatory compliance, DPDP Act 2023 data minimization requirements

---

## 1. SYSTEM OVERVIEW

A production-grade automated outbound voice collections agent deployed for an Indian NBFC in December 2024. The system dials borrowers with overdue loan accounts, conducts natural conversations in English or Hindi (with mid-call code-switching support), negotiates a repayment commitment, and extracts a structured Promise-to-Pay (PTP) record — date, amount, preferred follow-up channel (WhatsApp/SMS/call), and preferred call timing.

The core pipeline: Exotel outbound campaign → webhook → FastAPI → Azure Speech Services (en-IN + hi-IN with Continuous LID) → LangChain ReAct agent (GPT-4o-mini) → PTP extractor → PostgreSQL write → mem0 memory upsert → TTS (Azure Neural) → audio back to Exotel → post-call async summarization.

Persistent borrower memory (via mem0) allows the system to remember that a borrower prefers Hindi, receives calls after 6 PM, has promised to pay before and missed, and has a co-applicant named "Suresh." Each subsequent call is context-aware — the agent does not ask questions whose answers are already known.

At ~1,000 calls/day, cost discipline matters: GPT-4o-mini was chosen over GPT-4o at ~10x cost reduction with acceptable accuracy for the extraction task. Total per-call AI cost is under ₹2 (approximately $0.024 USD).

**Compliance is not optional:** TRAI NDNC registry check gates every outbound dial. RBI Fair Practices Code constrains collection call timing (8 AM–7 PM only), language, and harassment thresholds. DPDP Act 2023 limits what personal data is retained and for how long. These constraints are hard-coded into the system, not configuration.

---

## 2. HIGH-LEVEL DESIGN (HLD)

### System Architecture

```
[Loan System (LMS/CBS)]
        |
        v
[Campaign Scheduler]  ──── DND/NDNC check (TRAI API) ────> [SKIP if DND]
        |
        v (clean number)
[Exotel Outbound Call API]
        |
        | (call connects)
        v
[Exotel Webhook POST /webhook/exotel]
        |
        v
[FastAPI Server (ECS Fargate, ap-south-1)]
        |
        +──────────────────────────────────────────+
        |                                          |
        v                                          v
[Azure Speech Services]                 [Redis Session Store]
  Continuous LID (en-IN + hi-IN)         per-call state, 30m TTL
  Single stream → lang + transcript
          |
          v
[LangChain 0.3 ReAct Agent]
  GPT-4o-mini (Azure OpenAI)
  mem0 memory retrieval
        |
   +----+----+
   |         |
   v         v
[PTP      [Multi-Channel
 Extractor] Preference Router]
   |         |
   v         v
[PostgreSQL  [WhatsApp/SMS
 RDS PTP     dispatch via
 table]      Exotel API]
        |
        v
[Azure Neural TTS]
  AriaNeural (EN) / SwaraNeural (HI)
        |
        v
[Exotel Audio Stream → Borrower Phone]
        |
        v (call ends)
[SQS Post-Call Job]
        |
        v
[Celery Worker: Summarize + mem0 upsert + DynamoDB log]
        |
        v
[LangSmith + CloudWatch Observability]
```

### Language Routing Layer

Language detection runs in two phases:

1. **Pre-call**: Borrower profile from LMS may carry `preferred_language` from previous interactions (read from mem0). If present, pass as a language hint to Azure Speech to bias detection immediately.
2. **At-start Continuous LID**: Azure Speech Continuous Language Identification begins on the first audio frame. Within ~2 seconds it emits a `LanguageDetected` event (en-IN or hi-IN). The pipeline is configured for both locales simultaneously — no separate routing step required. Language ID is stored in Redis session.
3. **Mid-call code-switching**: Continuous LID tracks language throughout the call and emits new `LanguageDetected` events when the borrower switches. Azure Speech handles transcription in the switched language in the same stream. Agent receives a `SWITCH_LANGUAGE` signal and begins responding in the new language with a natural transition: "Bilkul, hum Hindi mein baat kar sakte hain."

### Memory Write-Back Pipeline

```
Call ends
    |
    v
SQS message: {call_id, user_id, transcript_s3_key}
    |
    v
Celery worker pulls transcript from S3
    |
    v
GPT-4o-mini summarization prompt:
  → Extract: {ptp_date, ptp_amount, channel_preference,
               call_timing, language_preference, key_objections,
               promised_before_missed: bool, identity_facts}
    |
    v
For each extracted fact:
  → Embed with text-embedding-3-small
  → pgvector cosine similarity search on existing mem0 entries (user_id)
  → if sim > 0.85: skip (duplicate)
  → if 0.65 < sim ≤ 0.85: update existing entry
  → if sim < 0.65: insert new entry
    |
    v
mem0 upsert (with user_id, category, content, embedding)
    |
    v
DynamoDB: full conversation transcript + metadata logged
    |
    v
LangSmith: trace tagged with call_id, outcome, language, ptp_extracted
```

### Multi-Channel Preference Routing

When a borrower expresses a follow-up channel preference ("WhatsApp par bhej do" / "Send me a WhatsApp"), the system:
1. Extracts channel = `whatsapp` from PTP record
2. After call ends, Celery worker dispatches Exotel WhatsApp template message with PTP date confirmation + payment link
3. If channel = `sms`, dispatches Exotel SMS (SMS must comply with DLT registration under TRAI)
4. If no preference or channel = `call`, schedules next outbound call campaign trigger at borrower's stated preferred time

---

## 3. LOW-LEVEL DESIGN (LLD)

### CollectionAgent Class Internal Structure

```python
class CollectionAgent:
    """
    Orchestrates a single outbound collections call.
    One instance per call, created on webhook receipt, destroyed on call end.
    """

    def __init__(
        self,
        call_id: str,
        user_id: str,
        loan_context: LoanContext,       # outstanding amount, DPD, loan type
        stt_strategy: STTStrategy,       # Azure Speech en-IN or hi-IN, swappable
        tts_strategy: TTSStrategy,       # Azure EN or HI, swappable
        llm: AzureChatOpenAI,
        memory_client: mem0.Memory,
        redis_client: Redis,
        ptp_db: AsyncSession,            # SQLAlchemy async session
    ):
        self.call_id = call_id
        self.user_id = user_id
        self.loan_context = loan_context
        self._stt = stt_strategy
        self._tts = tts_strategy
        self._lang = "en"                # current active language
        self._session_state = CallSession(call_id=call_id, user_id=user_id)
        self._agent = self._build_agent(llm)

    def _build_agent(self, llm) -> CompiledGraph:
        """LangChain 0.3 ReAct agent with tools + mem0 memory retrieval."""
        tools = [
            self._tool_extract_ptp,
            self._tool_get_payment_link,
            self._tool_schedule_callback,
        ]
        memory = self._build_memory_context()  # pre-fetch from mem0
        system_prompt = COLLECTION_PROMPT_TEMPLATE.format(
            loan_context=self.loan_context,
            borrower_memory=memory,
            compliance_rules=COMPLIANCE_RULES_BLOCK,
        )
        return create_react_agent(llm, tools, checkpointer=InMemorySaver())

    async def handle_audio_chunk(self, audio: AudioChunk) -> AsyncIterator[AudioChunk]:
        """Main per-turn handler: STT → detect lang switch → agent → TTS."""
        text = await self._stt.transcribe(audio)
        if await self._should_switch_language(text):
            await self._switch_language_pipeline()
        agent_response = await self._run_agent(text)
        async for chunk in self._tts.synthesize(agent_response):
            yield chunk

    async def on_call_end(self) -> None:
        """Triggered by Exotel hangup webhook. Enqueues post-call job."""
        await sqs_client.send_message(
            QueueUrl=POST_CALL_QUEUE_URL,
            MessageBody=json.dumps({
                "call_id": self.call_id,
                "user_id": self.user_id,
                "session_state": self._session_state.model_dump(),
            })
        )
```

### Data Schemas

```python
from pydantic import BaseModel
from datetime import date
from typing import Literal, Optional
from uuid import UUID

class PTPRecord(BaseModel):
    id: UUID
    user_id: str
    call_id: str
    loan_account_number: str
    ptp_date: date
    ptp_amount_inr: float
    confidence: float                    # 0.0–1.0 from LLM extraction
    channel: Literal["whatsapp", "sms", "call"]
    preferred_call_timing: Optional[str] # e.g., "after 6 PM", "morning"
    extraction_method: Literal["structured_output", "fallback_regex"]
    created_at: datetime
    # RBI compliance fields
    call_duration_sec: int
    agent_language: Literal["en", "hi", "mixed"]
    was_dnc_checked: bool                # TRAI DND check audit trail

class UserPreferences(BaseModel):
    user_id: str
    preferred_language: Literal["en", "hi", "mixed"]
    preferred_channel: Literal["whatsapp", "sms", "call"]
    preferred_call_window: Optional[str]  # "8-10 AM", "after 6 PM"
    dnc_status: bool                      # cached from last TRAI check
    dnc_checked_at: datetime
    last_updated: datetime

class MemoryEntry(BaseModel):
    id: UUID
    user_id: str
    category: Literal[
        "ptp_history", "channel_preference", "call_timing",
        "language_preference", "identity_fact", "objection_pattern"
    ]
    content: str                          # human-readable fact
    embedding: list[float]               # 1536-dim from text-embedding-3-small
    similarity_hash: str                 # for fast exact-dup check pre-embedding
    created_at: datetime
    updated_at: datetime
    source_call_id: str

class CallSession(BaseModel):
    call_id: str
    user_id: str
    language: Literal["en", "hi", "mixed"]
    language_switches: int               # how many times language changed
    turns: int
    ptp_extracted: bool
    ptp_record: Optional[PTPRecord]
    started_at: datetime
    ended_at: Optional[datetime]
    call_outcome: Optional[Literal[
        "ptp_committed", "refused", "no_answer",
        "callback_requested", "dispute_raised"
    ]]

class LoanContext(BaseModel):
    loan_account_number: str
    borrower_name: str
    outstanding_amount_inr: float
    dpd: int                             # Days Past Due
    loan_type: Literal["personal_loan", "two_wheeler", "home_loan", "credit_card"]
    emi_amount_inr: float
    last_payment_date: Optional[date]
```

### API Contracts

```http
# ── Inbound webhook from Exotel (call connected) ──────────────────────────────
POST /webhook/exotel
Content-Type: application/x-www-form-urlencoded

CallSid=CAabc123&
CallFrom=+919876543210&
CallTo=+918041234567&
CallStatus=in-progress&
Direction=outbound-api&
RecordingUrl=https://api.exotel.com/recordings/CAabc123

Response 200: TwiML-style XML
<Response>
  <Connect>
    <Stream url="wss://collections.yourco.com/audio/CAabc123"/>
  </Connect>
</Response>


# ── Initiate outbound call ─────────────────────────────────────────────────────
POST /call
Content-Type: application/json
Authorization: Bearer {internal_service_token}

{
  "user_id": "NBFC_BORROWER_001",
  "loan_account_number": "LA20240001",
  "phone_number": "+919876543210",
  "campaign_id": "CAMPAIGN_DEC_2024_BATCH_01",
  "preferred_language": "hi"             // optional, overrides detection
}

Response 200: {
  "call_id": "CAabc123",
  "status": "initiated",
  "dnc_checked": true,
  "estimated_connect_sec": 8
}

Response 400: {
  "error": "DND_REGISTERED",
  "message": "Number is on TRAI NDNC registry. Call blocked.",
  "ndnc_checked_at": "2024-12-15T09:00:00Z"
}


# ── Retrieve borrower memory ───────────────────────────────────────────────────
GET /user/{user_id}/memory?category=ptp_history&limit=5
Authorization: Bearer {internal_service_token}

Response 200: {
  "user_id": "NBFC_BORROWER_001",
  "memories": [
    {
      "category": "ptp_history",
      "content": "Committed to pay ₹12,500 by 20 Nov 2024. Did not pay.",
      "created_at": "2024-11-10T14:22:00Z"
    },
    {
      "category": "call_timing",
      "content": "Prefers calls after 6 PM on weekdays.",
      "created_at": "2024-11-05T10:00:00Z"
    }
  ]
}


# ── Health check ──────────────────────────────────────────────────────────────
GET /health
Response 200: {
  "status": "healthy",
  "dependencies": {
    "redis": "ok",
    "postgres": "ok",
    "exotel": "ok",
    "azure_openai": "ok"
  }
}


# ── WebSocket audio stream ────────────────────────────────────────────────────
WebSocket /audio/{call_id}
Protocol: Exotel Media Streams (similar to Twilio)
Inbound:  Base64-encoded μ-law 8kHz mono, 20ms frames
Outbound: Base64-encoded μ-law 8kHz mono audio for Exotel to play to caller
```

### Design Patterns Applied

- **Strategy Pattern** for STT/TTS: `STTStrategy` interface with `AzureSpeechENStrategy` and `AzureSpeechHIStrategy` implementations (both backed by Azure Speech Services, differentiated by locale and Continuous LID configuration). `TTSStrategy` with `AzureEnglishStrategy` and `AzureHindiStrategy`. Swap at runtime when language switches mid-call.
- **Template Method** in call flow: `CollectionAgent.handle_audio_chunk()` defines the invariant pipeline (STT → language check → agent → TTS). Language-detection and memory-retrieval steps are hook methods overridable in subclasses.
- **Observer Pattern** for memory events: `MemoryEventBus` publishes `PTPlExtracted` and `PreferenceUpdated` events. Subscribers include: Redis session updater, DynamoDB logger, SQS post-call enqueuer. No coupling between PTP extractor and downstream consumers.
- **Factory Pattern** for campaign initialization: `CampaignFactory.create(campaign_type)` returns pre-configured `CollectionAgent` with correct loan context, language defaults, and compliance rules for the campaign (EMI reminder vs. legal notice vs. settlement offer).
- **Circuit Breaker** on Azure OpenAI: `tenacity`-based retry (3 attempts, exponential backoff 500ms/1s/2s). On persistent failure, agent falls back to scripted decision tree (Lua-based IVR fallback via Exotel).

---

## 4. AI/ML PROJECT ARCHITECTURE

### Language Detection Pipeline

```
Borrower Audio (streaming frames, μ-law 8kHz)
        |
        v
Azure Speech Services — Continuous Language Identification
  Configured locales: ["en-IN", "hi-IN"]
  Mode: Continuous (tracks switches throughout call)
        |
        v (within ~2s of first speech)
LanguageDetected event: {language: "hi-IN", confidence: 0.93}
        |
        v
Transcription emitted in detected language (same stream — no pipeline fork)
        |
        v
On subsequent LanguageDetected events (code-switch):
  Update Redis session: current_language
  Signal LangChain agent: SWITCH_LANGUAGE
  Reinitialize TTS pipeline → Azure SwaraNeural (HI) or AriaNeural (EN)
        |
        v
Store language in Redis session + mem0 preference (if new/changed)
```

**Code-switching note**: Hinglish (Hindi-English mix) is common in Indian collections calls. Example: "Mujhe thoda time chahiye, I'll pay next Friday." Azure Speech Continuous LID handles intra-sentence code-switching natively — a single `LanguageDetected` event covers the dominant language of the utterance while the transcription model handles mixed vocabulary. This is why the two-locale configuration was chosen over separate EN and HI pipelines.

### Structured PTP Extraction (GPT-4o-mini Function Calling)

```python
ptp_extraction_tool = {
    "type": "function",
    "function": {
        "name": "extract_ptp",
        "description": "Extract Promise-to-Pay details from borrower utterance",
        "parameters": {
            "type": "object",
            "properties": {
                "ptp_date": {
                    "type": "string",
                    "description": "ISO date (YYYY-MM-DD). Null if borrower did not commit."
                },
                "ptp_amount_inr": {
                    "type": "number",
                    "description": "Amount promised in INR. Null if not specified."
                },
                "confidence": {
                    "type": "number",
                    "description": "0.0–1.0. >0.8 = clear commitment, 0.5–0.8 = tentative, <0.5 = ambiguous"
                },
                "channel": {
                    "type": "string",
                    "enum": ["whatsapp", "sms", "call"],
                    "description": "Preferred follow-up channel. Default: call."
                },
                "preferred_call_timing": {
                    "type": "string",
                    "description": "Free text: 'after 6 PM', 'Saturday morning'. Null if not stated."
                },
                "extraction_notes": {
                    "type": "string",
                    "description": "Why this extraction was or was not confident. For audit trail."
                }
            },
            "required": ["confidence", "channel"]
        }
    }
}
```

**Validation rules applied post-extraction** (hard-coded, not LLM):
1. `ptp_date` must be > today (no backdated PTPs)
2. `ptp_date` must be ≤ today + 30 days (NBFC policy: PTP window)
3. `ptp_date` must fall on a banking business day (skips Sundays + national holidays from `holidays` Python library)
4. `ptp_amount_inr` must be > 0 and ≤ total outstanding (sanity cap)
5. If `confidence` < 0.5: do NOT write PTP record; agent asks for clarification instead

**Retry flow on ambiguous date**:
```
User: "Main agli baar deke deta hun."  (I'll pay next time)
        |
        v
PTP extractor: confidence = 0.3, ptp_date = null
        |
        v
Agent: "Zaroor, lekin kya aap ek specific date bata sakte hain?
        Jaise kal, ya is hafte ke andar?"
        |
        v (user gives date)
Re-extract → validate → write PTP if confidence > 0.5
Max 2 retry attempts. After 2 failures: outcome = "callback_requested"
```

### Conversation Summarization (Post-Call Async)

```python
SUMMARIZATION_PROMPT = """
You are a collections supervisor reviewing a call transcript.
Extract the following from the transcript as structured JSON.
Be precise — this data feeds into the loan management system.

Transcript:
{transcript}

Extract:
{
  "ptp_committed": bool,
  "ptp_date": "YYYY-MM-DD or null",
  "ptp_amount_inr": float or null,
  "channel_preference": "whatsapp|sms|call",
  "preferred_call_timing": "string or null",
  "language_used": "en|hi|mixed",
  "borrower_sentiment": "cooperative|resistant|abusive|unavailable",
  "key_objections": ["job loss", "medical emergency", ...],
  "identity_facts": ["Has co-applicant named Suresh", "Business owner"],
  "promised_before_missed": bool,
  "escalation_required": bool,
  "escalation_reason": "string or null"
}
"""
```

### Memory Deduplication (mem0 + pgvector)

On every memory write, the system runs semantic deduplication before inserting:

```python
async def upsert_memory(
    user_id: str,
    category: str,
    content: str,
    db: AsyncSession
) -> MemoryUpsertResult:

    # Step 1: exact hash check (fast path)
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    existing_exact = await db.execute(
        select(MemoryEntry).where(
            MemoryEntry.user_id == user_id,
            MemoryEntry.similarity_hash == content_hash
        )
    )
    if existing_exact.scalar_one_or_none():
        return MemoryUpsertResult(action="skipped_exact_duplicate")

    # Step 2: semantic similarity check (pgvector)
    new_embedding = await embed(content)  # text-embedding-3-small
    similar = await db.execute(
        text("""
        SELECT id, content, embedding <=> :emb AS distance
        FROM memory_entries
        WHERE user_id = :uid AND category = :cat
        ORDER BY distance ASC LIMIT 3
        """),
        {"emb": new_embedding, "uid": user_id, "cat": category}
    )
    rows = similar.fetchall()

    if rows and rows[0].distance < 0.15:   # cosine distance < 0.15 = sim > 0.85
        return MemoryUpsertResult(action="skipped_semantic_duplicate")

    if rows and rows[0].distance < 0.35:   # 0.15–0.35 = sim 0.65–0.85
        await db.execute(
            update(MemoryEntry)
            .where(MemoryEntry.id == rows[0].id)
            .values(content=content, embedding=new_embedding,
                    updated_at=datetime.utcnow(),
                    similarity_hash=content_hash)
        )
        return MemoryUpsertResult(action="updated_existing")

    # Step 3: insert new entry
    new_entry = MemoryEntry(
        user_id=user_id, category=category, content=content,
        embedding=new_embedding, similarity_hash=content_hash
    )
    db.add(new_entry)
    return MemoryUpsertResult(action="inserted_new")
```

### Prompt Versioning in LangSmith

- Every deployed prompt is tagged with `version: "v{n}"` in LangSmith Prompt Hub
- `COLLECTION_PROMPT_TEMPLATE` fetched at container startup, cached in Redis (TTL: 1 hour)
- A/B testing: 10% of calls routed to `v_candidate` prompt via feature flag in Redis
- LangSmith evaluators run nightly: PTP extraction success rate, confidence distribution, compliance keyword presence (`"harass"` must never appear in agent output)
- Rollback: update Redis key `active_prompt_version` → containers pick up new version within 1 hour without redeploy

---

## 5. CORE LOGIC AND ALGORITHMS

### Algorithm 1: Language Detection & Code-Switching

**Purpose**: Detect the borrower's language and track mid-call code-switches using Azure Speech Continuous Language Identification, then signal the agent pipeline accordingly.

```
INPUT:  Streaming audio (μ-law 8kHz WebSocket frames), call_session
OUTPUT: Transcription text per turn, updated call_session.current_language

INITIALIZATION (on call connect):
   Create Azure SpeechRecognizer with:
     auto_detect_source_language_config = AutoDetectSourceLanguageConfig(
         languages=["en-IN", "hi-IN"]
     )
     speech_config.set_property(
         PropertyId.SpeechServiceConnection_LanguageIdMode,
         "Continuous"   ← tracks switches throughout call; not just at-start
     )
   Register event handlers:
     on_recognized    → handle_transcript(result)
     on_language_id   → handle_language_event(result)

STEP 1: STREAM AUDIO
   Push μ-law 8kHz frames to Azure Speech push_stream.
   Azure handles VAD, disfluency filtering, and language tracking internally.

STEP 2: ON LanguageDetected EVENT
   detected = result.properties[PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult]
   # e.g., "hi-IN" or "en-IN"
   new_lang = "hi" if detected == "hi-IN" else "en"

   IF new_lang != call_session.current_language:
       old_lang = call_session.current_language
       call_session.current_language = new_lang
       call_session.language_switches += 1
       # Switch TTS pipeline
       IF new_lang == "hi":
           reinitialize TTS pipeline → Azure SwaraNeural
       ELSE:
           reinitialize TTS pipeline → Azure AriaNeural
       # Signal agent
       agent.signal(SWITCH_LANGUAGE, new_lang=new_lang)
       # Agent's next turn starts with natural transition phrase
       # EN→HI: "Bilkul, main Hindi mein baat kar sakta hun."
       # HI→EN: "Sure, let me continue in English."

STEP 3: ON Recognized EVENT (transcript ready)
   text = result.text
   language = call_session.current_language
   RETURN (text, language)

STEP 4: PRE-CALL LANGUAGE HINT (optimization)
   IF mem0 has language_preference for user:
       Set initial_silence_timeout_ms = 2000 (shorter — we expect Hindi)
       Pass preferred locale as hint to AutoDetect config
       (Reduces first-LID-event latency from ~2s to ~500ms on matching language)
```

**Edge case — Hinglish (intra-sentence code-switching)**: "Mujhe 15 tarikh ko paisa milega, then I'll pay." Azure Speech emits a single transcript for this mixed utterance, transcribed in the dominant locale (hi-IN). The `LanguageDetected` event reflects the dominant language of the utterance — it does not switch pipelines for single-sentence mixing. This is the correct behavior: the agent reads the full mixed transcript and GPT-4o-mini handles bilingual input natively.

---

### Algorithm 2: PTP Date Extraction + Validation

**Purpose**: Extract a commitment date from natural language (often vague) and validate it against business rules.

```
INPUT:  Conversation transcript (last 5 turns for context), loan_context
OUTPUT: PTPRecord or PTPExtractionFailure

STEP 1: STRUCTURED EXTRACTION (GPT-4o-mini function calling)
   Call LLM with extraction tool (defined in Section 4).
   Provide last 5 turns as context so relative dates resolve correctly.
   ("next Friday" needs to know today's date = injected in system prompt)

STEP 2: PARSE RELATIVE DATES
   IF ptp_date is relative ("next Friday", "end of month", "kal"):
     - "kal" (tomorrow) → date.today() + timedelta(days=1)
     - "next Friday"    → next occurrence of weekday 4
     - "end of month"   → last business day of current month
     - "next week"      → date.today() + timedelta(days=7)
     - Inject today's date + day name in system prompt to help LLM resolve

STEP 3: VALIDATE EXTRACTED DATE
   Rule 1: ptp_date > today                    → else: FAIL ("past date")
   Rule 2: ptp_date ≤ today + 30 days          → else: FAIL ("too far future")
   Rule 3: ptp_date not in national_holidays   → else: next_business_day(ptp_date)
   Rule 4: ptp_date.weekday() != 6 (Sunday)    → else: next_business_day(ptp_date)
   Rule 5: confidence > 0.5                    → else: AMBIGUOUS (go to Step 4)

STEP 4: HANDLE AMBIGUOUS / FAILED EXTRACTION
   IF attempt_count < 2:
     Generate clarification response:
       - Missing date:   "Kya aap ek specific date bata sakte hain?"
       - Past date:      "Woh date toh nikal gayi — kya kal ya parso possible hai?"
       - Vague amount:   "Poora ₹{outstanding} denge ya partial payment?"
     attempt_count += 1
     GOTO STEP 1 with new user response
   ELSE:
     outcome = "callback_requested"
     DO NOT write PTP record
     LOG: ptp_extraction_failed with reason

STEP 5: WRITE PTP RECORD
   IF validation passes AND confidence > 0.5:
     INSERT INTO ptp_records (validated fields)
     Publish PTPlExtracted event → downstream consumers
     RETURN PTPRecord
```

---

### Algorithm 3: Memory Deduplication (mem0 + pgvector)

**Purpose**: Prevent redundant facts from accumulating in borrower memory while ensuring updates (changed preferences) replace stale entries.

```
INPUT:  user_id, category, new_content (fact to store)
OUTPUT: action ∈ {skipped_exact_duplicate, skipped_semantic_duplicate,
                   updated_existing, inserted_new}

STEP 1: EXACT HASH CHECK (O(1) — hits index)
   hash = SHA-256(new_content)
   IF hash exists in memory_entries WHERE user_id AND category:
     RETURN skipped_exact_duplicate
   (Catches identical re-submissions without embedding cost)

STEP 2: EMBED NEW CONTENT
   embedding = OpenAI text-embedding-3-small(new_content)
   # 1536-dim vector, ~$0.00002 per call

STEP 3: pgvector COSINE DISTANCE SEARCH
   SELECT id, content, (embedding <=> new_embedding) AS dist
   FROM memory_entries
   WHERE user_id = ? AND category = ?
   ORDER BY dist ASC
   LIMIT 3;
   # <=> operator = cosine distance (0 = identical, 2 = opposite)

STEP 4: APPLY THRESHOLDS
   IF dist_closest < 0.15:          # cosine similarity > 0.85
     RETURN skipped_semantic_duplicate
     # Example: "Prefers WhatsApp" ≈ "Likes to be contacted on WhatsApp"

   ELIF dist_closest < 0.35:        # cosine similarity 0.65–0.85
     UPDATE existing entry:
       content    = new_content     # newer fact is more accurate
       embedding  = new_embedding
       updated_at = now()
     RETURN updated_existing
     # Example: "Calls after 7 PM" updates old "Calls after 6 PM"

   ELSE:                            # cosine similarity < 0.65
     INSERT new MemoryEntry
     RETURN inserted_new
     # Example: "Has a co-applicant Suresh" is genuinely new fact
     #          vs existing "Prefers WhatsApp"

RATIONALE FOR THRESHOLDS:
   0.85 similarity = near-paraphrase → dedup (avoid noise)
   0.65–0.85       = same topic, updated value → merge (keep fresh)
   < 0.65          = different concept → new entry (preserve diversity)
   Thresholds calibrated against 500 real borrower memory entries
   from pilot (Nov 2024). Tunable via config without code change.
```

---

### Algorithm 4: Post-Call Summarization & Memory Consolidation

**Purpose**: Convert a raw call transcript into structured borrower memory entries that inform future calls.

```
INPUT:  call_id, user_id, transcript (full turn-by-turn text)
OUTPUT: N memory entries upserted, DynamoDB log written,
        PTP record confirmed/created if not done in-call

STEP 1: PULL TRANSCRIPT FROM S3
   transcript = s3.get_object(Bucket=TRANSCRIPTS_BUCKET, Key=f"{call_id}.json")

STEP 2: CHUNK IF NEEDED
   IF len(transcript_tokens) > 4000:
     Split into overlapping 2000-token chunks (500-token overlap)
     Process each chunk, merge results by taking most confident value
   (Long calls: 15–20 min, ~3,000–5,000 tokens)

STEP 3: STRUCTURED SUMMARIZATION (GPT-4o-mini)
   Use SUMMARIZATION_PROMPT (Section 4) to extract structured dict.
   Retry once on JSON parse failure with corrective instruction.

STEP 4: BRANCH ON OUTCOME
   IF ptp_committed == True AND in-call PTP record NOT written:
     Run PTP validation (Algorithm 2, Steps 3–5) on extracted values
     Write PTP record if valid

STEP 5: EXPLODE SUMMARY INTO MEMORY FACTS
   Generate one fact string per memory category:
   - channel_preference: "Prefers WhatsApp for follow-ups."
   - call_timing:        "Asked to be called after 6 PM."
   - language:           "Speaks in Hindi (mixed with some English)."
   - ptp_history:        "Committed ₹8,000 by 2024-12-20. Call on 2024-12-15."
   - objection_pattern:  "Cited job loss as reason for delay."
   - identity_fact:      "Business owner; wife handles finances."

STEP 6: UPSERT EACH FACT (Algorithm 3 per fact)
   FOR each (category, fact_string) in memory_facts:
     result = upsert_memory(user_id, category, fact_string, db)
     log result action (inserted/updated/skipped)

STEP 7: LOG TO DYNAMODB
   INSERT {
     call_id, user_id, loan_account_number,
     transcript_text, summary_json,
     memory_actions: [{category, content, action}],
     ptp_outcome: {committed: bool, record_id: uuid or null},
     call_duration_sec, language_used, agent_turns,
     compliance_flags: {rbi_timing_ok: bool, no_harassment: bool},
     created_at: now()
   }

STEP 8: NOTIFY DOWNSTREAM
   IF ptp_committed:
     Trigger multi-channel dispatch (WhatsApp/SMS per preference)
   IF escalation_required:
     Post to internal Slack webhook → human collector queue

TIME BUDGET: Entire post-call job completes in < 30 seconds.
(S3 fetch 2s + summarize 8s + embed N facts 3s + DB writes 2s + DynamoDB 1s)
```

---

## 6. INTERVIEW ATTACK SURFACE

### Q1: Why mem0 over raw LangChain ConversationBufferMemory?

**Short answer**: LangChain's memory is session-scoped. mem0 is borrower-scoped and persistent across calls, which is the entire point of a collections system.

**Detailed**: `ConversationBufferMemory` and `ConversationSummaryMemory` live for the duration of one agent invocation. When the call ends, memory is lost. For a collections voicebot, the most valuable context is what happened on *previous* calls: did they promise to pay and miss? Do they prefer evening calls? Do they speak Hindi? This history must survive across calls, which means it needs persistent storage.

mem0 provides three things over raw DB lookups:
1. **Entity-level granularity**: Not raw transcripts but distilled facts ("prefers WhatsApp", "promised before, missed") — the agent doesn't need to re-read 10 transcripts to know the borrower's pattern.
2. **Semantic deduplication**: Without it, every call adds "prefers WhatsApp" again. After 30 calls, the context window is polluted with 30 identical facts.
3. **Retrieval by category + recency**: At call start, `mem0.search(user_id, category="ptp_history", limit=3)` returns the 3 most relevant PTP facts ordered by recency — not a flat text blob.

**Trade-off**: mem0 adds ~200ms latency at call start (embedding lookup + pgvector search). This is acceptable because it runs before the call connects (pre-fetched during Exotel dial-out window, ~5 seconds).

---

### Q2: How do you handle Hindi code-switching mid-call?

**Short answer**: Azure Speech Continuous Language Identification handles it natively in the STT layer — a single stream, two configured locales (en-IN + hi-IN), with automatic `LanguageDetected` events on switches. At the agent layer, GPT-4o-mini handles mixed-language input. At the TTS layer, Azure SwaraNeural handles Hinglish sentences with natural prosody.

**Detection**: Azure Speech Continuous LID runs throughout the call (not just at the start). When the borrower switches language, a `LanguageDetected` event fires. The system updates the TTS pipeline and signals the agent (Algorithm 1). The agent's next response begins with a natural transition ("Bilkul, main Hindi mein baat kar sakta hun") so the switch feels human.

**Why Azure Speech for both EN and HI?** The system already used Azure for OpenAI (LLM) and Azure Neural TTS. Consolidating STT to Azure Speech created a single Microsoft Enterprise Agreement covering all AI components: one vendor for compliance boundary (DPDP single data processor), one Azure Private Link configuration, simplified billing. The WER tradeoff — Azure en-IN is ~5.8% vs the ~4.1% achievable with specialized English STT — is acceptable for a collections vocabulary (bounded domain of financial terms, dates, and amounts).

**The critical failure mode we caught in testing**: Before adopting Azure Speech for Hindi, we briefly tested a two-pipeline approach (separate English and Hindi STT). Borrowers switching mid-call caused the English STT to hallucinate English words. "Teen tarikh ko dunga" (I'll pay on the 3rd) was transcribed as "teen target could do" — completely losing the PTP commitment. Azure Continuous LID eliminates this class of failure. This is War Story #1.

---

### Q3: What happens when PTP extraction fails because the user is vague about the date?

**Short answer**: The agent enters a clarification retry loop (max 2 attempts), asks progressively specific questions, and if still ambiguous, sets outcome to "callback_requested" rather than writing a garbage PTP record.

**The loop** (Algorithm 2, Step 4):
- Attempt 1: "Kya aap ek specific date bata sakte hain? Jaise kal, ya is hafte ke andar?" (Can you give a specific date? Like tomorrow, or within this week?)
- Attempt 2 (if still vague): "Kya 18 tarikh theek rahegi?" (Would the 18th work?) — agent proactively suggests the nearest valid business day.
- After 2 failures: No PTP written. Call outcome = `callback_requested`. Scheduler re-queues call for next day.

**Why not accept a vague PTP?** Writing a PTP record without a specific date creates false positives in the loan management system. The NBFC's recovery team uses PTP dates to flag accounts as "committed" and deprioritize them. A vague "sometime next week" stored as a PTP would remove the account from active follow-up for 7 days — the opposite of the intended effect.

**Confidence threshold**: Any PTP with confidence < 0.5 is not written. Between 0.5 and 0.7, PTP is written but flagged as `tentative` in the database. The NBFC's recovery dashboard shows tentative PTPs separately and a human review calls on them within 24 hours.

---

### Q4: DPDP Act compliance — what user data do you store and why?

**Short answer**: We store the minimum necessary for the collections function, with retention limits, data subject access provisions, and audit trails — all mandated by the DPDP Act 2023.

**What we store and why:**

| Data | Retention | Justification under DPDP |
|------|-----------|--------------------------|
| Phone number | Duration of loan | Legitimate use — collections |
| Call transcript | 90 days | RBI audit requirement |
| PTP record (date, amount) | 7 years | RBI record-keeping regulation |
| Language preference | 1 year post loan closure | Legitimate use — service quality |
| Memory facts (non-PTP) | 1 year post loan closure | Legitimate use — prevents repetitive harassment |
| DND check timestamp | 90 days | TRAI compliance audit trail |

**What we explicitly do NOT store:**
- Voice biometrics or voiceprints (no consent mechanism, high DPDP risk)
- Location data
- Financial data beyond loan account (no bank account details in memory)
- Sentiment scores in any user-facing record (risk of discrimination claims)

**Data subject rights**: The DPDP Act grants rights of access, correction, and erasure. We implement `DELETE /user/{user_id}/data` which hard-deletes memory entries and anonymizes (not deletes) transcripts (to preserve RBI audit trail structure while removing PII).

**Consent**: The outbound call begins with a disclosed recording notice: "This call is being recorded for quality and regulatory purposes." This satisfies DPDP Act's notice requirement for data collection during a legitimate contractual relationship.

---

### Q5: How do you prevent calling users on the DND (Do Not Disturb) registry?

**Short answer**: TRAI NDNC check is a hard gate in the campaign scheduler — no phone number reaches Exotel's dial API without a clean NDNC status within the last 24 hours.

**Technical implementation:**

```python
async def check_and_dial(user_id: str, phone: str, campaign_id: str):
    # 1. Check Redis cache first (TTL = 24h)
    cached = await redis.get(f"ndnc:{phone}")
    if cached == "DND":
        log_skip(user_id, reason="DND_REGISTERED")
        return

    if not cached:
        # 2. Call TRAI NDNC API (rate limited to 100 req/min per CLI)
        ndnc_status = await trai_ndnc_client.check(phone)
        await redis.setex(f"ndnc:{phone}", 86400, ndnc_status)  # 24h TTL
        if ndnc_status == "DND":
            log_skip(user_id, reason="DND_REGISTERED")
            return

    # 3. Additional check: RBI Fair Practices Code time restriction
    ist_hour = datetime.now(IST).hour
    if not (8 <= ist_hour < 19):       # 8 AM to 7 PM IST only
        log_skip(user_id, reason="OUTSIDE_PERMITTED_HOURS")
        enqueue_for_next_window(user_id, campaign_id)
        return

    # 4. Only now: initiate Exotel call
    await exotel_client.call(phone, webhook_url=WEBHOOK_URL)
```

**Regulatory context**: Transactional calls (loan-related) are partially exempted from DND under TRAI regulations — but the exemption requires TRAI-registered Transactional Category header and DLT (Distributed Ledger Technology) registration for SMS. Voice calls to DND numbers for collections are explicitly prohibited regardless of transactional status. Violation = TRAI fine + NBFC reputation risk.

**Audit trail**: Every NDNC check (pass or fail) is logged to DynamoDB with `checked_at` timestamp. This is the evidence produced if a borrower complains to TRAI about receiving an unwanted call.

---

## 7. TROUBLESHOOTING WAR STORIES

### War Story 1: Hindi STT Hallucinating PTP Dates

**Situation**: Two weeks into production (mid-December 2024), the collections supervisor noticed a pattern in the LMS: PTP dates of "3rd" were being recorded as various incorrect dates — sometimes the 13th, sometimes the 23rd. The AI success rate for PTP extraction appeared high (82%) but the *accuracy* was not being verified.

**Task**: Investigate why structured PTP extraction was producing incorrect dates despite appearing confident (confidence > 0.7).

**Action**: Pulled 20 calls where `ptp_date = "3rd of month"` from LangSmith traces. Compared STT transcript vs. actual audio. Found: Azure Speech hi-IN was consistently transcribing "teen tarikh" (Hindi: "three date" = 3rd) as:
- "teen baj" (three o'clock) on 6 calls
- "teesri tarik" (33rd date) on 4 calls
- "tin tarikh" (correct) on 10 calls

The issue: phone audio at 8kHz has poor low-frequency response. The Hindi retroflex 'ट' (ṭ) vs dental 'त' (t) distinction in "tarikh" was getting lost in PSTN compression. Azure Speech hi-IN, like any STT model, degrades on 8kHz telephony audio compared to clean 16kHz speech.

**Root cause**: Azure Speech hi-IN was benchmarked on 16kHz audio during evaluation. The production path compressed to 8kHz μ-law via Exotel. We had never tested the STT on actual PSTN audio quality before go-live.

**Resolution**:
1. Immediate: Added post-STT regex correction: if transcript contains "baj" within 5 tokens of a number, flag for LLM re-interpretation (not a date word).
2. Short-term: Pre-upsampled audio to 16kHz PCM before sending to Azure Speech. Upsampling cannot recover frequency content lost at the PSTN layer (Nyquist limit at 4kHz for 8kHz audio). What it does: (a) satisfies Azure Speech SDK's expected input format — its push stream API is designed for 16kHz PCM; sending 8kHz triggers Azure's internal resampler which uses lower-quality linear interpolation than our upsampler; (b) Azure's hi-IN acoustic model was trained on 16kHz data — closer input distribution means better VAD and silence detection. The phoneme error on "tarikh" was partially an artifact of Azure's internal resampler over-smoothing the retroflex consonant boundary.
3. Long-term: Added date entity extraction as a parallel validation step — spaCy `hi_core` NER model extracts date spans, cross-checks against LLM extraction. Discrepancy → re-ask.
4. Monitoring: LangSmith evaluator now flags any PTP where extracted date differs from the most recent ordinal number in the transcript.

**Result**: PTP date accuracy improved from 74% to 96% on Hindi calls within one week of the fix.

---

### War Story 2: mem0 Over-Deduplicating Preferences (Stale Data)

**Situation**: A borrower called on December 10th and said "SMS bhej do" (send me SMS). Memory correctly stored: "Prefers SMS for follow-ups." On December 15th, the same borrower called back and said "Actually WhatsApp bhejo" (actually send WhatsApp). The system confirmed it would send via WhatsApp. But the post-call message went via SMS.

**Task**: Understand why the channel preference was not updating despite a clear override in the new call.

**Action**: Traced the DynamoDB log for the December 15th call. The post-call summarization correctly extracted `channel_preference = "whatsapp"`. The mem0 upsert was called. But the upsert returned `skipped_semantic_duplicate` — it had treated "Prefers WhatsApp" as semantically equivalent to "Prefers SMS."

**Root cause**: The cosine similarity between "Prefers SMS for follow-ups" and "Prefers WhatsApp for follow-ups" was 0.87. The two sentences differ by only one key word ("SMS" vs "WhatsApp") but their sentence embeddings were very similar because both are positive preference statements with near-identical structure.

**The problem**: Our threshold for semantic duplicate was > 0.85. The channel name ("SMS" vs "WhatsApp") — the only meaningful difference — was getting averaged out in the 1536-dim embedding space by the high structural similarity.

**Resolution**:
1. Changed dedup strategy for `channel_preference` and `language_preference` categories: **no semantic dedup, always update**. These categories have exactly one valid value at a time (a borrower can only prefer one channel). Implemented `ALWAYS_REPLACE` flag per category.
2. Kept semantic dedup for `identity_fact` and `objection_pattern` (where near-paraphrase really is a duplicate).
3. Added a category config table:

```python
CATEGORY_DEDUP_STRATEGY = {
    "channel_preference": "always_replace",   # single-value state
    "call_timing":        "always_replace",   # single-value state
    "language_preference":"always_replace",   # single-value state
    "ptp_history":        "append",           # history — keep all
    "identity_fact":      "semantic_dedup",   # stable facts
    "objection_pattern":  "semantic_dedup",   # patterns accumulate
}
```

**Result**: Channel preference now updates correctly within the same post-call job.

---

### War Story 3: PTP Extraction Returning Invalid Dates ("Next Month")

**Situation**: In the first week, approximately 15% of calls ended with PTP records written for dates beyond 30 days from the call. The NBFC's collections policy considers any PTP > 30 days as an unacceptable deferral — the LMS should have flagged these accounts for escalation, not marked them as "committed."

**Task**: Find why PTPs beyond 30 days were being written and prevent it.

**Action**: Reviewed extraction logs. The prompt for PTP extraction said "extract the date the borrower commits to paying." Many borrowers said "agle mahine ke aakhir mein" (at the end of next month). If the call was on December 1st, "next month" = January, and "end of January" = January 31st — 61 days away. GPT-4o-mini correctly extracted January 31st. Our validation rule checked `> today + 30 days` but the bug was in how we handled the case: instead of entering the clarification retry loop, the code was incorrectly writing the PTP with a `tentative` flag and moving on.

**Root cause**: A missing `return` statement in the validation function caused execution to fall through to the PTP write despite the validation failure. Classic Python control flow bug. Code review had missed it because the function had multiple nested conditions.

**Resolution**:
1. Fixed the control flow bug immediately (30-minute hotfix + deploy via ECS rolling update).
2. Added integration test: mock a call where borrower says "end of next month," assert that PTP record is NOT written and outcome = `callback_requested` (if > 30 days).
3. Added a DynamoDB query in the daily monitoring job: `SELECT COUNT(*) WHERE ptp_date > call_date + 30 DAYS`. Alert if > 0 (should be impossible post-fix).
4. Retrospective action: Added the validation function to the PR review checklist as a "critical path" function requiring two reviewer sign-offs.

**Result**: Zero out-of-window PTPs written post-fix. 23 previously-written invalid PTPs were identified and manually reviewed by the collections team.

---

### War Story 4: Exotel Webhook Delivery Failures on Short Calls

**Situation**: About 8% of calls in the DynamoDB logs showed `call_outcome = null` despite the PSTN call completing. The PTP records were missing for these calls. Upon investigation, these were correlated with calls lasting under 30 seconds.

**Task**: Understand why short calls were not triggering the post-call processing pipeline.

**Action**: Checked Exotel webhook delivery logs in the Exotel dashboard. Found that when a call was shorter than ~20–30 seconds (borrower picks up and immediately hangs up, or straight to voicemail), Exotel was firing the `in-progress` webhook and the `completed` webhook in very quick succession — sometimes within 2 seconds. Our FastAPI endpoint was processing the `in-progress` webhook (which spins up the WebSocket audio handler) when the `completed` webhook arrived and was being dropped because the call_id wasn't yet in Redis (the Redis write from `in-progress` handling was still in progress).

**Root cause**: Race condition between Exotel `in-progress` and `completed` webhooks with no idempotency on webhook receipt. The `completed` webhook handler looked up the call in Redis to get session state before enqueuing the SQS job. If Redis hadn't been written yet, the lookup returned null and the SQS enqueue was skipped silently.

**Resolution**:
1. Added retry logic on the `completed` webhook handler: if Redis lookup returns null, retry 3 times with 500ms backoff before giving up.
2. Added a dead-letter queue (DLQ) for the SQS post-call queue. If a message fails to process, it goes to DLQ for manual review.
3. Made SQS the primary state source: `completed` webhook now writes directly to SQS with all data from the Exotel webhook payload (call duration, recording URL, phone numbers) — eliminating the Redis dependency for post-call processing.
4. Added idempotency key on SQS message: `call_id`. Celery workers check for duplicate processing.

**Result**: Call outcome recording improved from 92% to 99.6%. The remaining 0.4% are voicemail-only calls (< 5 seconds) where no meaningful conversation occurred.

---

### War Story 5: 5-Second Dead-Air on First Utterance (Azure At-Start LID)

**Situation**: In week one of production, the NBFC operations team reported that every call began with 5 seconds of complete silence after the borrower first spoke. The borrower would say "Haan" (hello/yes) and hear nothing for 5 full seconds before the agent responded. About 12% of borrowers were hanging up during this silence. The issue affected every call — not just a subset.

**Task**: Identify the source of the 5-second first-turn latency.

**Action**: Added microsecond-precision logging to each pipeline stage on webhook receipt. Isolated the delay: the Azure Speech recognizer was configured in `AtStart` LID mode (the default). In this mode, the recognizer buffers audio and waits up to 5 seconds before emitting the first `LanguageDetected` event — it is designed for batch/offline scenarios where accuracy matters more than speed. The recognizer would not begin transcribing until the LID decision was finalized. Result: borrower speaks → 5-second buffer → language detected → transcription begins → agent responds. Total first-turn latency: ~6.2 seconds.

**Root cause**: We had copied an Azure Speech LID example from documentation that used `AtStart` mode. This mode is appropriate for pre-recorded audio but catastrophic for real-time telephony. The documentation did not prominently warn against using `AtStart` for streaming scenarios.

**Resolutions tried:**
1. **Switch to Continuous LID mode** (implemented, resolved the issue): `PropertyId.SpeechServiceConnection_LanguageIdMode = "Continuous"`. Continuous LID emits a `LanguageDetected` event after ~500ms–2s of speech rather than waiting for a fixed buffer. First-turn latency dropped from 6.2s to ~1.4s.
2. **Optimistic routing with fallback** (implemented, further improvement): Pre-load both en-IN and hi-IN recognizers at call start. If mem0 has a `language_preference` for the borrower, begin transcribing in that locale immediately while Continuous LID confirms. On language mismatch (LID says hi-IN but we started en-IN), re-transcribe the buffered first utterance. We maintain a client-side ring buffer of raw μ-law audio frames (last 6 seconds, ~48KB at 8kHz 8-bit) in the FastAPI WebSocket handler, independent of the Azure push stream. On language mismatch, we close the existing recognizer, instantiate a new one with the correct locale, and replay the buffered frames into the new push stream. The ring buffer is sized to cover a typical first utterance (borrower greeting is 2–4 seconds). In practice, 94% of borrowers match their stored preference — retry cost is rare.

**Result**: First-turn latency reduced from 6.2s to 0.8s (P95). Borrower hang-up rate in the first 10 seconds dropped from 12% to 3.1%. Root cause documented in team runbook under "Azure Speech LID mode selection."

---

## 8. mem0 MEMORY ARCHITECTURE DEEP DIVE

### Honest Context: mem0 as a Cutting-Edge Choice

mem0 (v0.0.x) was approximately 11 months old at the time of this December 2024 delivery — launched in January 2024, backed by Y Combinator, with ~41k GitHub stars and a Peak XV (Sequoia India) investment announced in late 2024. A more conservative NBFC would likely have chosen **Zep** (more mature, SOC2-compliant, production-proven in enterprise fintech) or a **custom PostgreSQL memory layer** (zero external dependency, full control over data residency for DPDP compliance). The team chose mem0 specifically for its native semantic deduplication API and the fact that its entity memory model matched the cross-call borrower memory pattern exactly — avoiding the need to build dedup logic from scratch. This was a deliberate technology-forward decision consistent with a team willing to ship an AI voicebot in December 2024.

**Why mem0 for reads but raw pgvector for writes?** mem0's native `add()` method runs its own fixed-threshold dedup internally — there's no API to customize the strategy per memory category. Our system needs `always_replace` behavior for `channel_preference` (single-value state) and `semantic_dedup` for `identity_fact` (stable facts, accumulate). We implemented `upsert_memory()` as a custom write path against the underlying pgvector table to get category-aware dedup control. mem0's `search()` API is retained for reads because its cosine similarity ranking with `user_id` + `category` filters is exactly what we need and outperforms a raw `ORDER BY embedding <=>` on uncategorized queries.

### Why mem0 Over Plain LangChain Memory

| Dimension | LangChain ConversationMemory | mem0 (v0.0.x) |
|-----------|------------------------------|----------------|
| Persistence | Session-only (lost on call end) | Persistent (PostgreSQL + pgvector) |
| Scope | Single conversation | Entity-level (borrower across all calls) |
| Deduplication | None | Semantic dedup (Algorithm 3) |
| Retrieval | Full buffer or summary | Filtered by category + cosine similarity |
| Memory growth | Unbounded in session | Controlled (dedup prevents accumulation) |
| Cost at retrieval | Entire history in context | Top-K relevant facts only |
| Collections fit | ❌ No cross-call memory | ✅ Purpose-built for entity memory |

For a collections system, session memory is nearly useless — the value is in *cross-call* borrower history. A borrower who missed 3 previous PTPs needs to be engaged differently than a first-time defaulter. LangChain's memory cannot provide this. mem0's entity memory model was purpose-built for this pattern.

### Memory Categories

| Category | Description | Example Entry | Strategy |
|----------|-------------|---------------|----------|
| `ptp_history` | All PTP commitments and outcomes | "Committed ₹8,000 by Dec 20. Missed. Called Dec 22, no answer." | `append` |
| `channel_preference` | Preferred follow-up channel | "Prefers WhatsApp, not SMS." | `always_replace` |
| `call_timing` | Preferred call window | "Prefers calls after 6 PM on weekdays." | `always_replace` |
| `language_preference` | Primary language and code-switching pattern | "Speaks Hindi. Code-switches to English for numbers." | `always_replace` |
| `identity_fact` | Stable personal context | "Self-employed. Wife handles household finances. Co-applicant: Suresh Sharma." | `semantic_dedup` |
| `objection_pattern` | Recurring objections | "Cites irregular income (seasonal business) as reason for delay." | `semantic_dedup` |

### Retrieval at Call Start

```python
async def build_memory_context(user_id: str) -> str:
    memories = []

    # High-priority: get all preference facts (small, always-replace)
    for cat in ["channel_preference", "call_timing", "language_preference"]:
        result = await mem0_client.search(
            query="",           # empty = get latest by category
            user_id=user_id,
            filters={"category": cat},
            limit=1
        )
        if result:
            memories.append(f"[{cat}] {result[0]['content']}")

    # PTP history: last 3 entries (most recent first)
    ptp = await mem0_client.search(
        query="payment commitment history",
        user_id=user_id,
        filters={"category": "ptp_history"},
        limit=3
    )
    for p in ptp:
        memories.append(f"[ptp_history] {p['content']}")

    # Identity + objections: top-2 by relevance
    for cat in ["identity_fact", "objection_pattern"]:
        results = await mem0_client.search(
            query=f"important {cat.replace('_', ' ')} for debt collection",
            user_id=user_id,
            filters={"category": cat},
            limit=2
        )
        for r in results:
            memories.append(f"[{cat}] {r['content']}")

    return "\n".join(memories)
    # Typical output: 8–12 lines, ~200–350 tokens
    # Injected into LangChain agent system prompt
```

### Schema: memory_entries Table (PostgreSQL + pgvector)

```sql
CREATE TABLE memory_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(100) NOT NULL,
    category        VARCHAR(50)  NOT NULL,
    content         TEXT         NOT NULL,
    embedding       VECTOR(1536) NOT NULL,          -- pgvector column
    similarity_hash CHAR(64)     NOT NULL,           -- SHA-256 of content
    source_call_id  VARCHAR(100),
    created_at      TIMESTAMPTZ  DEFAULT now(),
    updated_at      TIMESTAMPTZ  DEFAULT now()
);

-- Indexes
CREATE INDEX idx_memory_user_category ON memory_entries (user_id, category);
CREATE INDEX idx_memory_hash ON memory_entries (similarity_hash);
CREATE INDEX idx_memory_embedding ON memory_entries
    USING ivfflat (embedding vector_cosine_ops)     -- pgvector IVFFlat index
    WITH (lists = 100);                              -- tune for ~100k entries

-- Row-level retention policy (DPDP Act compliance)
-- Automated cleanup job deletes entries where
-- updated_at < NOW() - INTERVAL '1 year' AND loan closed
```

### Example mem0 Entries (Realistic)

```json
[
  {
    "user_id": "NBFC_BORROWER_001",
    "category": "ptp_history",
    "content": "Called 2024-11-10. Committed ₹12,500 by 2024-11-20. PTP missed — no payment received. Called 2024-11-22, went to voicemail.",
    "source_call_id": "EXO_CA20241110_001"
  },
  {
    "user_id": "NBFC_BORROWER_001",
    "category": "channel_preference",
    "content": "Prefers WhatsApp for payment reminders. Does not respond to SMS.",
    "source_call_id": "EXO_CA20241115_003"
  },
  {
    "user_id": "NBFC_BORROWER_001",
    "category": "call_timing",
    "content": "Prefers calls after 6 PM on weekdays. Available Saturday mornings.",
    "source_call_id": "EXO_CA20241108_002"
  },
  {
    "user_id": "NBFC_BORROWER_001",
    "category": "language_preference",
    "content": "Speaks Hindi. Uses English for numbers and financial terms.",
    "source_call_id": "EXO_CA20241105_001"
  },
  {
    "user_id": "NBFC_BORROWER_001",
    "category": "identity_fact",
    "content": "Self-employed tailoring business. Income is irregular (wedding season peak Oct-Feb). Wife's name is Sunita.",
    "source_call_id": "EXO_CA20241110_001"
  },
  {
    "user_id": "NBFC_BORROWER_001",
    "category": "objection_pattern",
    "content": "Consistently cites irregular income and pending customer payments as reason for delay. Cooperative but asks for extra 1-2 week extensions.",
    "source_call_id": "EXO_CA20241115_003"
  }
]
```

---

## 9. DEPLOYMENT ARCHITECTURE

### Local Development

```yaml
# docker-compose.yml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}
      - AZURE_SPEECH_REGION=${AZURE_SPEECH_REGION}
      - AZURE_TTS_KEY=${AZURE_TTS_KEY}
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/collections
      - EXOTEL_SID=${EXOTEL_SID}
      - EXOTEL_TOKEN=${EXOTEL_TOKEN}
    depends_on:
      - redis
      - db

  worker:
    build: .
    command: celery -A app.worker worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/collections
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  db:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_DB=collections
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  ngrok:
    image: ngrok/ngrok:latest
    command: http api:8000 --domain=${NGROK_DOMAIN}
    environment:
      - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}

volumes:
  pgdata:
```

**Dev workflow**: `docker-compose up` → Ngrok exposes `https://your-domain.ngrok.io` → configure in Exotel portal as webhook URL → test real calls from Exotel dev account.

### Production (AWS ECS Fargate, ap-south-1)

```
┌─────────────────────────────────────────────────────────────────┐
│  AWS ap-south-1 (Mumbai)                                        │
│                                                                 │
│  ┌─────────────────┐      ┌──────────────────────────────────┐  │
│  │ Application Load │      │  ECS Fargate Cluster             │  │
│  │ Balancer         │─────>│  ┌────────────┐ ┌────────────┐  │  │
│  │ (HTTPS + WSS)    │      │  │ API Service│ │ Worker     │  │  │
│  └─────────────────┘      │  │ (2–8 tasks)│ │ Service    │  │  │
│                            │  │ 1vCPU/2GB  │ │ (2 tasks)  │  │  │
│  ┌─────────────────┐      │  └────────────┘ └────────────┘  │  │
│  │ ECR              │      └──────────────────────────────────┘  │
│  │ (Container Repo) │                    |                       │
│  └─────────────────┘      ┌─────────────+──────────────────┐    │
│                            │  Data Layer                    │    │
│  ┌─────────────────┐      │  ┌────────┐ ┌───────┐ ┌─────┐ │    │
│  │ Secrets Manager  │      │  │RDS PG  │ │ Redis │ │Dynamo││    │
│  │ (API Keys)       │      │  │+pgvect │ │Elasti-│ │  DB  ││    │
│  └─────────────────┘      │  │(db.t3. │ │Cache  │ │      ││    │
│                            │  │medium) │ │(cache.│ │      ││    │
│  ┌─────────────────┐      │  └────────┘ │r7g.sm)│ └─────┘│    │
│  │ SQS             │      │             └───────┘         │    │
│  │ (post-call jobs) │      └───────────────────────────────┘    │
│  └─────────────────┘                                            │
│                            ┌──────────────────────────────────┐  │
│  ┌─────────────────┐      │  Observability                   │  │
│  │ S3               │      │  ┌───────────┐ ┌─────────────┐  │  │
│  │ (Transcripts,    │      │  │CloudWatch │ │ LangSmith   │  │  │
│  │  Recordings)     │      │  │(Infra     │ │ (LLM Traces)│  │  │
│  └─────────────────┘      │  │ Metrics)  │ └─────────────┘  │  │
│                            │  └───────────┘                  │  │
└─────────────────────────────────────────────────────────────────┘
```

**Auto-scaling**: ECS Service Auto Scaling based on `ECSServiceAverageCPUUtilization` (target 60%). Min 2 tasks (HA), max 8 tasks (~800 concurrent call-handling capacity). Campaign runs 9 AM–7 PM IST → scale-in at 7:30 PM.

**WebSocket affinity**: ALB uses sticky sessions (duration-based, 30 min) to route all frames of a single WebSocket call to the same ECS task. Without this, mid-call audio frames would be split across tasks.

**Data residency**: All data stored in ap-south-1 (Mumbai). Required for RBI data localization guidelines for financial data. No cross-region replication of borrower PII.

### Exotel Outbound Campaign Configuration

```
Exotel Campaign Setup:
  Campaign type: Outbound Auto-dial
  Caller ID: Registered TRAI Transactional number
  DLT Entity ID: {registered DLT entity ID from TRAI portal}
  Template ID: {TRAI-approved call script template ID}
  Call window: 09:00–19:00 IST (hard-coded by Exotel as per TRAI)
  Retry policy: 2 retries, 4-hour gap (NBFC policy)
  Answer machine detection: Enabled (skip voicemails, log as "no_answer")
  Webhook: POST https://collections.yourco.com/webhook/exotel
  Recording: Enabled (stored in Exotel + synced to S3 via webhook)
```

---

## 10. COST ANALYSIS

### Per-Call Cost Breakdown (1,000 calls/day)

Assumptions: Average call duration = 3 minutes; ~50% connect rate (500 connected calls/day with full AI processing; 500 no-answer/voicemail); 60% English, 40% Hindi.

| Component | Provider | Unit Cost | Per-Call (3 min) | Daily (500 AI calls) |
|-----------|----------|-----------|-----------------|----------------------|
| **STT (EN + HI)** | Azure Speech Services (en-IN + hi-IN, Standard real-time recognition) | ~$0.010/min | $0.030 | $15.00 (all 500 AI calls) |
| **TTS — English** | Azure Neural (AriaNeural) | $0.016/1K chars (~60 chars/turn, 8 turns) | $0.0077 | $2.31 |
| **TTS — Hindi** | Azure Neural (SwaraNeural) | $0.016/1K chars | $0.0077 | $1.54 |
| **LLM — Agent** | GPT-4o-mini (Azure OpenAI) | $0.00015/1K input + $0.0006/1K output | ~$0.012 | $6.00 |
| **LLM — Summarization** | GPT-4o-mini | $0.00015/1K input + $0.0006/1K output | ~$0.006 | $3.00 |
| **Embeddings** | text-embedding-3-small | $0.00002/1K tokens | ~$0.0001 | $0.05 |
| **Redis (ElastiCache)** | cache.r7g.small | ~₹7,000/month | ₹0.47 | ₹233 |
| **PostgreSQL (RDS)** | db.t3.medium | ~₹12,000/month | ₹0.80 | ₹400 |
| **DynamoDB** | On-demand | ~$1.25/million writes | ~$0.00001 | $0.01 |
| **ECS Fargate** | 1vCPU/2GB, 2 tasks 24/7 | ~₹8,000/month | ₹0.53 | ₹267 |
| **Exotel Voice** | Outbound PSTN India | ~₹0.50/min | ₹1.50 | ₹750 (all 1000 dials) |
| **S3 + Data Transfer** | Standard | ~$20/month | ~₹0.04 | ₹20 |

**Per connected AI call total (AI components only)**: ~$0.056 + ₹1.80 ≈ **₹6.50/call** (~$0.078)
**Per dial attempt (including Exotel, all 1,000)**: ~**₹8.00/attempt** (~$0.096)
**Daily total**: ~₹8,000/day (~$96/day)
**Monthly total**: ~₹2,40,000/month (~$2,880/month)

### Cost vs. Human Collections Agent

| Metric | Human Agent | AI Voicebot |
|--------|------------|-------------|
| Calls/day (1 agent) | 60–80 | 1,000+ |
| Cost/call (salary + overhead) | ₹25–35 | ₹8.00 |
| PTP commitment rate (pilot) | 18% | 14% |
| Average call duration | 4.5 min | 3.0 min |
| DND compliance errors | ~2% (human error) | 0% (hard-gated) |
| 24/7 operation | ❌ | ✅ |

**Unit economics**: At ₹8.00/attempt vs ₹30/human call, AI voicebot achieves ~3.75x cost reduction with 78% of the PTP commitment rate. For a 10,000-account delinquent portfolio at 15% contact rate, AI recovers ₹X crore at ₹8.00/attempt vs ₹30/human.

### Cost Optimization Strategies

1. **Batch TTS pre-generation**: Opening script ("Namaste, main XYZ bank se bol raha hun...") is identical for all calls. Pre-generate TTS audio once per campaign → $0 TTS for first 10 seconds per call. Saves ~15% TTS cost.
2. **Azure Speech streaming over batch**: Using the push-stream real-time API rather than batch transcription avoids post-call processing delays and reduces effective billable duration via VAD-based end-of-speech detection.
3. **GPT-4o-mini over GPT-4o**: The PTP extraction task is structured and well-defined. GPT-4o-mini at 1/10th the price achieves >95% of GPT-4o accuracy on this specific extraction task (validated in Nov 2024 eval). Saves ~$55/day at current volume.
4. **ECS scale-in at 7 PM**: Campaign runs 9 AM–7 PM. Scale ECS tasks to minimum (2) at night. Saves ~40% on compute.
5. **Reserved Instances for RDS/ElastiCache**: Convert from on-demand to 1-year reserved → ~30% savings on database costs.

---

## 11. OBSERVABILITY DEEP DIVE (LangSmith)

### Trace Structure

Every connected call produces one LangSmith trace with the following span hierarchy:

```
Trace: call_id=CAabc123  |  tags: [collections, hindi, ptp_extracted]
│
├── span: "language_detection"
│     input:  {audio_duration_ms: 1200, first_transcript: "Haan bolo"}
│     output: {language: "hi", confidence: 0.91, pipeline: "azure_speech_hi_IN"}
│     latency: 340ms
│
├── span: "mem0_retrieval"
│     input:  {user_id: "NBFC_001", categories: ["ptp_history", ...]}
│     output: {memories_retrieved: 6, total_tokens: 287}
│     latency: 210ms
│
├── span: "agent_turn_1"  (one span per conversation turn)
│     input:  {user_message: "Haan sun raha hun", memory_context: "..."}
│     output: {agent_response: "Namaste, aapka ₹12,500...", tool_calls: []}
│     latency: 890ms
│     └── child: "llm_call"
│           model: gpt-4o-mini, input_tokens: 1240, output_tokens: 87
│
├── span: "agent_turn_3"
│     input:  {user_message: "20 tarikh ko de dunga"}
│     output: {agent_response: "...", tool_calls: ["extract_ptp"]}
│     latency: 1200ms
│     └── child: "tool_call:extract_ptp"
│           input:  {transcript: "20 tarikh ko de dunga", context: "..."}
│           output: {ptp_date: "2024-12-20", confidence: 0.87, channel: "whatsapp"}
│           latency: 450ms
│
├── span: "ptp_validation"
│     input:  {ptp_date: "2024-12-20", amount: 12500, call_date: "2024-12-15"}
│     output: {valid: true, business_day: true, within_30_days: true}
│     latency: 8ms
│
└── span: "post_call_summary"  (async, tagged separately)
      input:  {transcript_tokens: 2840}
      output: {memory_entries_written: 4, ptp_confirmed: true}
      latency: 12400ms
```

### PTP Extraction Tracking

LangSmith dashboard (custom evaluators running nightly on all traces):

| Metric | Target | Dec 2024 (post-fix) |
|--------|--------|---------------------|
| PTP extraction attempt rate | 100% of connected calls | 98.2% |
| Extraction success rate (confidence > 0.5) | > 70% | 74.1% |
| Date validation pass rate | 100% of extracted | 99.8% |
| Average extraction confidence | > 0.75 | 0.81 |
| Clarification retry triggered | < 30% of attempts | 21.3% |
| Post-retry success | > 50% of retries | 58.7% |

### Language Routing Metrics

| Metric | Value |
|--------|-------|
| Language detection accuracy (vs. human review sample) | 96.4% |
| Mid-call language switches | 8.2% of calls |
| Azure LID routing latency p99 (first LanguageDetected event) | 1,850ms |
| Avg language detection latency (first turn, Continuous LID) | 820ms |
| Azure Speech WER on English calls (en-IN) | 5.8% |
| Azure Speech WER on Hindi calls (hi-IN, post audio upsampling fix) | 6.8% |

### Custom LangSmith Evaluators

```python
# Evaluator 1: PTP validity check
def eval_ptp_validity(run: Run) -> EvaluationResult:
    if "extract_ptp" not in run.outputs.get("tool_calls", []):
        return EvaluationResult(key="ptp_validity", score=None, comment="No PTP extracted")
    ptp = run.outputs["ptp_record"]
    valid = (
        ptp["ptp_date"] > ptp["call_date"] and
        ptp["confidence"] >= 0.5 and
        days_between(ptp["call_date"], ptp["ptp_date"]) <= 30
    )
    return EvaluationResult(key="ptp_validity", score=1.0 if valid else 0.0)

# Evaluator 2: Compliance keyword check (RBI harassment rule)
FORBIDDEN_PHRASES = ["jail", "police", "arrest", "court", "FIR", "ruin you"]
def eval_compliance_language(run: Run) -> EvaluationResult:
    all_agent_text = " ".join([t["agent_response"] for t in run.outputs["turns"]])
    violations = [p for p in FORBIDDEN_PHRASES if p.lower() in all_agent_text.lower()]
    return EvaluationResult(
        key="compliance_language",
        score=0.0 if violations else 1.0,
        comment=f"Violations: {violations}" if violations else "Clean"
    )

# Evaluator 3: Response latency SLA
def eval_latency_sla(run: Run) -> EvaluationResult:
    p95_latency = run.outputs.get("p95_turn_latency_ms", 9999)
    return EvaluationResult(
        key="latency_sla",
        score=1.0 if p95_latency < 2000 else 0.0,
        comment=f"P95 latency: {p95_latency}ms"
    )
```

### CloudWatch Alarms

| Alarm | Threshold | Action |
|-------|-----------|--------|
| ECS CPU > 80% for 5 min | scale-out trigger | Add 2 ECS tasks |
| API 5xx error rate > 1% | immediate | PagerDuty alert (on-call) |
| Redis latency > 50ms p99 | warning | Slack alert |
| RDS connection pool > 80% | warning | Slack alert |
| SQS DLQ depth > 10 | warning | Slack alert (failed post-call jobs) |
| Azure Speech error rate > 5% | critical | PagerDuty (STT dependency down) |

---

## 12. NEXT ACTIONS MENU

This cookbook is a living document. The following drill-downs are available:

---

**[A] CODE WALKTHROUGH — Show me the full CollectionAgent implementation**
> Full Python implementation: CollectionAgent class, LangChain agent construction, language detection integration, mem0 retrieval, PTP tool, post-call SQS enqueue.

**[B] PROMPT ENGINEERING — Show me the exact prompts used**
> Full `COLLECTION_PROMPT_TEMPLATE` (system prompt with borrower memory injection), `PTP_EXTRACTION_PROMPT`, `SUMMARIZATION_PROMPT`, and the SSML scripts for Azure TTS (with correct Hindi prosody markup).

**[C] COMPLIANCE DEEP DIVE — TRAI + RBI + DPDP implementation details**
> Step-by-step: TRAI DND check integration code, Exotel DLT configuration, RBI Fair Practices Code constraints in system prompt, DPDP Act data map, retention automation SQL, data subject access API.

**[D] EVALUATION FRAMEWORK — How was the system validated before go-live?**
> Evaluation dataset construction (Hindi + English test calls), WER benchmarks for STT models, PTP extraction accuracy testing methodology, A/B prompt testing setup, pilot run analysis (Nov 2024).

**[E] RUNBOOK — Production incidents and escalation procedures**
> Step-by-step runbooks for: STT outage (Azure Speech), LLM outage (Azure OpenAI), Exotel webhook failures, DB failover, campaign pause procedure for compliance incident.

**[F] ARCHITECTURE ALTERNATIVES — What else was considered?**
> Rejected options: Twilio instead of Exotel, split-vendor STT (separate specialized EN + HI models) vs. unified Azure Speech Continuous LID, Bhashini (govt. STT) instead of Azure Speech hi-IN, LlamaIndex instead of LangChain, Pinecone instead of pgvector, real-time WebSocket LLM streaming vs. turn-based. Why each was rejected.

**[G] SCALING TO 10,000 CALLS/DAY — What would need to change?**
> Bottleneck analysis at 10x scale: Azure Speech concurrent recognition limits (Microsoft Enterprise Agreement tier), pgvector index rebuild strategy, Redis cluster mode, ECS task limits, Exotel concurrent call capacity, cost projections.

**[H] INTERVIEW SIMULATION — Run a mock technical interview**
> I'll ask you the 5 attack-surface questions from Section 6 one by one, evaluate your answers, and provide structured feedback on depth, accuracy, and delivery.

---

*Reply with the letter(s) of the section(s) you want to drill into.*
