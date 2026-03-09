# CRM-Integrated WhatsApp Chatbot with AI-Assisted Conversation Flows
## Production Cookbook — Interview Preparation Document

---

## LINE ITEM

> "Designed and deployed a production CRM-integrated WhatsApp chatbot at Aeon Credit Service (NBFC) with LLM-powered intent classification, LangGraph-based multi-turn conversation orchestration, and Salesforce + FinnOne LOS integration — serving 3,000–5,000 messages/day with 60–65% automated resolution, multilingual support (English/Hinglish), full RBI-compliant audit logging, and sub-5-second end-to-end latency."

---

## PRE-ANALYSIS

- **Core system/product**: WhatsApp chatbot for NBFC customer self-service — EMI queries, balance checks, payment status, foreclosure quotes, complaint escalation — integrated with Salesforce CRM and FinnOne loan management system, with LLM-powered intent classification and LangGraph-based workflow orchestration
- **Tech stack**: WhatsApp Business API (via Gupshup BSP), FastAPI ≥0.115.6, Python 3.12, LangGraph ≥0.2.60 (StateGraph + Redis checkpointing), GPT-4o-mini (primary) / Claude Haiku (fallback), Salesforce REST API (Enterprise edition), FinnOne API (on-premise), Langfuse (LLM observability), Redis / AWS ElastiCache, AWS EC2 + ALB
- **Scale**: ~3,000–5,000 messages/day (spikes to 8,000–10,000 month-end), 12 intent categories, multilingual (English + Hinglish), ~60–65% automated resolution rate, <$2/month LLM cost
- **Domain context**: Aeon Credit Service India (NBFC), consumer lending, customer service — regulated under RBI Master Direction on Digital Lending + DPDP Act 2023

---

## 1. SYSTEM OVERVIEW

A WhatsApp-based customer service chatbot deployed at Aeon Credit Service, integrated with Salesforce CRM and the loan management system (FinnOne). Borrowers self-serve on common queries — EMI due dates, outstanding balance, payment status, loan statements, foreclosure quotes — without calling the contact center or waiting for manual agent responses.

The AI layer uses an LLM (GPT-4o-mini via OpenAI SDK) with structured output to classify intent and extract entities (loan number, date ranges, amounts) in a single call. This was a deliberate choice over a fine-tuned classifier — we had zero labeled training data at launch, and roughly 40–45% of inbound messages were Hinglish (Hindi-English code-mix). A single LLM call with structured output handled intent classification, entity extraction, sentiment detection, and language identification across English, Hindi, and Hinglish without any transliteration or preprocessing pipeline.

A LangGraph ≥0.2.60 StateGraph manages multi-turn conversation flows as stateful graphs, routing between automated resolution (CRM/LOS API lookups) and human agent escalation with full context. We extended the LangGraph StateGraph pattern for compliance-sensitive NBFC operations — adding identity verification as a mandatory entry node, Salesforce case logging as a mandatory exit node, sentiment-based escalation overrides, and a button-based degraded mode for LLM outages.

CRM integration ensures every interaction is logged as a Salesforce case (RBI audit trail requirement), agent handoffs carry full conversation history, and follow-up reminders are automated — eliminating the manual follow-up cycle where agents had to call back customers who messaged outside business hours.

### Scope and Limitations

- The LLM handles **routing and comprehension only** — it does not generate financial data. Loan amounts, due dates, and balances come from FinnOne/Salesforce API calls. This separation is non-negotiable for compliance.
- Multi-intent messages (e.g., "tell me my EMI and also send me a statement") are handled sequentially — the system resolves the primary intent first, then prompts "Is there anything else?" A `secondary_intent` field was evaluated but not added — multi-intent frequency was only ~5–8%.
- Text messages and interactive button/list replies supported. Media messages (images, voice notes) are acknowledged but not processed. Voice notes in Hindi are a known gap.

---

## 2. HIGH-LEVEL DESIGN (HLD)

### System Architecture

```
[Borrower on WhatsApp]
         |
         v (WhatsApp Business API / BSP)
[BSP Gateway (Gupshup)]
         |
         v (HTTPS webhook — HMAC-SHA256 validated)
[Message Ingestion Service]
[FastAPI ≥0.115.6 on AWS EC2 t3.medium × 2, behind ALB]
         |
         +---> [Session Manager (Redis / ElastiCache cache.t3.micro)]
         |
         v
[LangGraph ≥0.2.60 Workflow Orchestrator]
[In-process with FastAPI; Redis as checkpoint backend]
         |
         v
[identity_verification_node] ← mandatory entry for all sessions
         |
         v
[router_node (LLM structured output — GPT-4o-mini)]
  - Intent classification (12 categories)
  - Entity extraction (loan number, amounts, dates)
  - Sentiment detection (4 levels)
  - Language identification
  - ALL in ONE structured output call
         |
         +--- confidence ≥0.8, not frustrated -------> [Resolution Subgraph]
         |                                                      |
         |                                          +----------+----------+
         |                                          |                     |
         |                                          v                     v
         |                                  [Salesforce CRM         [FinnOne/LOS
         |                                   API Tool Node]          API Tool Node]
         |                                          |                     |
         |                                          +----------+----------+
         |                                                     |
         |                                                     v
         |                                          [response_formatter_node]
         |
         +--- confidence 0.5–0.8 -----------------> [confirmation_node]
         |
         +--- confidence <0.5 / frustrated -------> [escalation_node]
         |                                                      |
         |                                                      v
         |                                          [Salesforce Omnichannel
         |                                           Console — agent queue]
         |
         v
[crm_sync_node] → [outbound_node]
         |
         v (WhatsApp API outbound via Gupshup)
[Borrower receives response]
         |
         v
[Observability: Langfuse (LLM traces) + CloudWatch (infra metrics)]
```

### Component Interaction

- **WhatsApp → Ingestion**: Gupshup receives messages via WhatsApp Cloud API and forwards to our FastAPI service via HTTPS POST webhook. Payload includes phone number, message text, media attachments, timestamp, and message ID. HMAC-SHA256 webhook signature validated before processing. We return HTTP 200 to the BSP within 1 second (BSP SLA) and process asynchronously.
- **Ingestion → LangGraph**: Webhook handler creates or resumes a LangGraph graph instance keyed by phone number (`thread_id`). LangGraph loads the Redis checkpoint and resumes from the last node.
- **Router Node**: Single GPT-4o-mini call with `response_format: json_schema` (OpenAI structured output) returns a guaranteed-valid IntentResult JSON. Conditional edges read `intent`, `confidence`, and `sentiment` to route.
- **Resolution Subgraph**: Nodes call Salesforce REST API and FinnOne API as LangGraph tool nodes with built-in retry. Every subgraph ends with `crm_sync_node` (audit logging) and `outbound_node`.
- **Agent Handoff**: Escalation node creates an open Salesforce case with full conversation transcript and routes to Omnichannel queue. Agent sees: intent, confidence, customer profile, all extracted entities.

### Infrastructure

| Component | Spec | Role |
|-----------|------|------|
| EC2 t3.medium × 2 | 2 vCPU, 4GB RAM | FastAPI + LangGraph runtime |
| ALB | Managed | Load balancing, SSL termination |
| ElastiCache cache.t3.micro | Redis 7.x | LangGraph checkpoints + session TTL |
| Gupshup BSP | Managed | WhatsApp API compliance, template approval, delivery |
| Salesforce Enterprise | 100K API calls/day | CRM, case management, Omnichannel |
| FinnOne | On-premise | Loan data (EMI, balance, statements) |
| AWS Secrets Manager | Managed | API keys, OAuth tokens, BSP credentials |
| Route 53 | Managed | DNS |

### Scalability and Availability

- **Operating scale**: 3,000–5,000 messages/day normal; 8,000–10,000 month-end spikes (2024 holiday cycle peak: 8,200 messages in one day)
- **Bottleneck**: Salesforce API limits (100K calls/day, Enterprise). At 5K messages × 3 API calls = 15K/day — safe. At 10x, would approach ceiling.
- **10x strategy**: Cache customer profile + loan details in Redis (5 min TTL). 80% of month-end queries are "what's my EMI" — answer changes at most daily. Cache converts 10x message volume into ~1.5x Salesforce calls. Batch case creation during spikes (queue in Redis, flush every 5 min).
- **Availability**: Circuit breaker on LLM → failover OpenAI → Anthropic Haiku. If both down: button-only menu (no LLM, deterministic). Circuit breaker on Salesforce/FinnOne → customer still receives acknowledgment, CRM sync queued for retry.
- **Latency budget**: Target <5s end-to-end. Breakdown: BSP webhook delivery ~200ms, ingestion + checkpoint restore ~50ms, LLM structured output 200–400ms, Salesforce API calls 500–1,500ms, FinnOne API calls 300–800ms, response formatting ~50ms, outbound via BSP 200–500ms.

---

## 3. LOW-LEVEL DESIGN (LLD)

### Internal Structure: LangGraph Workflow

Library: `langgraph ≥0.2.60`, `langchain-core ≥0.3.0`, `langchain-openai ≥0.2.0`

The conversation is modeled as a LangGraph `StateGraph`. We extended the base pattern for financial services compliance — adding identity verification as a mandatory entry node, Salesforce audit logging as a mandatory exit node, and sentiment-based override routing.

**Graph State Schema** (TypedDict, shared across all nodes):

```python
class WhatsAppState(TypedDict):
    phone_number: str
    customer_id: str | None
    loan_ids: list[str] | None
    message_history: list[dict]          # [{role, content, timestamp}]
    current_intent: IntentResult | None
    current_flow: str | None
    flow_step: int
    tool_results: dict | None
    escalation_reason: str | None
    verification_status: Literal["unverified", "verified", "restricted"]
    turn_count: int
    sentiment: Literal["positive", "neutral", "negative", "frustrated"] | None
    session_start_ts: datetime
    last_message_ts: datetime
```

**Node topology**:

```
START --> [identity_verification_node]
              |
              v
         [router_node] (GPT-4o-mini structured output)
              |
       +------+------+------+------+------+
       |      |      |      |      |      |
       v      v      v      v      v      v
  [emi_flow] [balance_flow] [foreclosure_flow]
  [statement_flow] [payment_status_flow]
  [complaint_flow] → always → [escalation_node]
       |
       +-----------------------------+
                                     |
                                     v
                            [confirmation_node]  (0.5–0.8 confidence)
                                     |
                                     v
                            [response_formatter_node]
                                     |
                                     v
                            [crm_sync_node]
                                     |
                                     v
                            [outbound_node] --> END
```

**Conditional edge logic** (router node output → routing):

| Condition | Route |
|-----------|-------|
| `confidence ≥ 0.8 AND sentiment != frustrated AND intent not in [complaint, speak_to_agent]` | Corresponding flow subgraph |
| `0.5 ≤ confidence < 0.8` | `confirmation_node` → flow on confirm / re-route on deny |
| `confidence < 0.5` | `escalation_node` |
| `sentiment == frustrated` | `escalation_node` (override, regardless of confidence) |
| `intent in [complaint, speak_to_agent]` | `escalation_node` (compliance rule — always human) |

The 0.8 threshold was calibrated empirically: starting at 0.9 triggered too many confirmation steps for clear English queries. 0.8 balanced straight-through handling with safety margin.

### Data Schemas

```python
# Pydantic models for LLM structured output (OpenAI json_schema)

class Entities(BaseModel):
    loan_number: str | None       # Format: AC + 10 digits
    date_range: DateRange | None
    amount: float | None
    product_type: str | None

class IntentResult(BaseModel):
    intent: Literal[
        "emi_due_date", "outstanding_balance", "payment_status",
        "loan_statement", "foreclosure_quote", "emi_receipt",
        "complaint", "speak_to_agent", "greeting",
        "payment_confirmation", "document_upload", "unknown"
    ]
    confidence: float             # 0.0–1.0
    entities: Entities
    sentiment: Literal["positive", "neutral", "negative", "frustrated"]
    language_detected: str        # "english", "hindi", "hinglish", "other"
    requires_verification: bool

class CRMCase(BaseModel):
    case_id: str
    customer_id: str
    phone_number: str
    channel: Literal["whatsapp"]
    intent: str
    conversation_transcript: list[dict]
    resolution: str | None
    resolution_type: Literal["automated", "agent_assisted", "escalated"]
    llm_intent_confidence: float
    satisfaction_rating: int | None  # 1–5
    created_at: datetime
    closed_at: datetime | None

class ConversationCheckpoint(BaseModel):
    thread_id: str           # phone_number as thread key
    checkpoint_id: str
    state: WhatsAppState
    node_id: str             # current node in graph
    created_at: datetime
    ttl_idle_seconds: int    # 1800 (30 min)
    ttl_absolute_seconds: int # 86400 (24 hr)
```

### API Contracts

```
POST /webhook/whatsapp   (Gupshup BSP → Ingestion)
  Headers: X-Hub-Signature: sha256=<hmac_value>
  Body: { BSP-normalized payload — phone, message, timestamp, msg_id }
  Response 200: { "status": "received" }   // Must respond within 1s

Internal LLM Call  (router_node → OpenAI)
  Model: gpt-4o-mini
  response_format: { "type": "json_schema", "json_schema": IntentResult.schema() }
  Max tokens: 300
  Temperature: 0  (deterministic routing)

POST /v1/send-message   (FastAPI → Gupshup BSP)
  Headers: Authorization: Bearer <BSP_TOKEN>
  Body: {
    "phone_number": str,
    "message_type": "text" | "template" | "interactive",
    "text": str | null,
    "interactive": {
      "type": "button" | "list",
      "body": str,
      "buttons": [{"id": str, "title": str}] | null
    } | null
  }
  Response 200: { "message_id": str, "status": "sent" }

GET /v1/conversation/{phone_number}/status   (Dashboard / Agent Console)
  Response 200: {
    "graph_state": WhatsAppState,
    "current_node": str,
    "recent_messages": [{"role", "content", "timestamp"}],
    "customer_profile": { "name", "customer_id", "active_loans": [...] }
  }
```

### Design Patterns Applied

- **Graph-based Workflow (LangGraph StateGraph)**: Conversation = stateful graph execution. Nodes are functional steps. Conditional edges encode business routing logic declaratively. LangGraph Redis checkpointing handles persistence, resume-after-interruption, and TTL cleanup. Extended with compliance-specific nodes not in the base pattern.
- **Structured Output (LLM → Pydantic schema)**: `response_format: json_schema` enforces schema at the API level. No regex post-processing, no JSON repair. The schema is the contract between LLM and routing logic — single most impactful architectural decision.
- **Adapter Pattern (CRM/LOS integration)**: Unified `CustomerDataAdapter` interface. `SalesforceAdapter` and `FinnOneAdapter` as concrete implementations registered as LangGraph tool nodes. Swap-able without changing orchestration logic.
- **Circuit Breaker**: LLM provider, Salesforce, FinnOne each wrapped with circuit breakers. LangGraph durable execution ensures mid-conversation API failures preserve state — graph pauses and resumes when dependency recovers.
- **Observer (Analytics)**: Every node emits to Langfuse (LLM call details) and CloudWatch (infra metrics) without coupling to business logic.

### Error Handling and Failure Modes

| Failure | Impact | Mitigation |
|---------|--------|------------|
| LLM provider timeout/5xx | Cannot classify intent | Circuit breaker: OpenAI → Anthropic Haiku failover. If both down: button-only menu (deterministic, no LLM). LangGraph pauses at router node. |
| FinnOne returns stale/inconsistent data | Wrong EMI/balance served | Cross-validate against Salesforce if discrepancy detected. On mismatch: do not serve — escalate with "data discrepancy" flag. |
| LLM hallucinates intent | Wrong flow triggered | Structured output enforces enum — LLM cannot invent intents. Confidence threshold + sentiment override as safety nets. Automated response always ends with "Was this helpful?" |
| Redis/checkpoint failure | Multi-turn flow breaks | Treat as new conversation. Log for investigation. |
| BSP webhook delivery failure | Message never arrives | BSP retries 3× with backoff. Monitored via CloudWatch `WebhookSuccessRate`. |
| Salesforce rate limit hit | CRM sync fails | Emergency Redis queue for case creation; batch flush every 5 min; deduplication on flush. Customer still receives response. |

---

## 4. AI/ML ARCHITECTURE

### Pipeline Design

**No custom model training**: This is an LLM-native system. Intelligence comes from prompt engineering + structured output schema + LangGraph workflow design, not custom-trained models. Chose this for zero-training-data launch, faster iteration, and native multilingual support.

**Inference pipeline**:
```
Inbound WhatsApp message
  → LangGraph state restore from Redis checkpoint
  → identity_verification_node (phone number match, optional 2nd factor)
  → router_node: GPT-4o-mini structured output
      (intent + NER + sentiment + language — 1 API call)
  → Conditional edge routing
  → Flow subgraph execution (Salesforce + FinnOne tool calls)
  → response_formatter_node
  → crm_sync_node (Salesforce case create/update)
  → outbound_node (Gupshup API)
```

**Prompt versioning**: Router system prompt is version-controlled in Git with semantic version tags (e.g., `prompt-v1.3.2`). Changes deployed via shadow mode — new prompt runs in parallel on 10% of traffic, outputs logged to Langfuse but not served, evaluated against labeled message set before promotion. Approximately 5–6 major prompt iterations over system lifetime.

### Model Strategy

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Primary model | GPT-4o-mini (`gpt-4o-mini-2024-07-18`) | 200–400ms latency, $0.15/1M input tokens, native multilingual, structured output maturity |
| Fallback model | Claude Haiku (`claude-haiku-4-5-20251001`) [ASSUMPTION — verify exact model ID at deployment] | Provider diversity; Anthropic tool-use-based structured output requires separate prompt variant |
| Temperature | 0 | Deterministic routing — same message must always route the same way |
| Max tokens | 300 | IntentResult schema + few-shot response fits in ~200 tokens output; 300 is ceiling |
| No model tiering | N/A | WhatsApp intent classification is uniformly simple — one cheap fast model handles all 12 categories |

### LLM Structured Output Schema

The single LLM call replacing the traditional intent/NER/sentiment/language pipeline:

```
SYSTEM PROMPT (prompt-v1.6.0):

"You are a customer service intent classifier for Aeon Credit Service,
an NBFC in India. Classify the customer's WhatsApp message.

INTENTS (pick exactly one):
- emi_due_date: Customer wants to know when their next EMI payment is due
- outstanding_balance: Customer wants to know remaining loan balance
- payment_status: Customer asking if a specific payment was received/processed
- loan_statement: Customer wants a loan account statement
- foreclosure_quote: Customer wants the amount to close the loan early
- emi_receipt: Customer wants a receipt for a past payment
- complaint: Customer is reporting a problem or expressing dissatisfaction
- speak_to_agent: Customer explicitly wants to talk to a human
- greeting: Simple hello/hi with no specific query
- payment_confirmation: Customer informing about a payment they just made
- document_upload: Customer sending a document (payment screenshot, ID, etc.)
- unknown: Message does not fit any category

CONFIDENCE: Float 0.0–1.0.
  >0.8 = clear intent. 0.5–0.8 = probable. <0.5 = unclear.

ENTITY EXTRACTION:
- loan_number: Format 'AC' followed by 10 digits. Extract if present.
- date_range: Any date references (month, quarter, specific dates)
- amount: Any monetary amount mentioned (INR)

SENTIMENT:
- positive: Happy, thankful
- neutral: Normal inquiry
- negative: Unhappy but measured
- frustrated: Angry, repeated messages, ALL CAPS, threatening language

LANGUAGE: Detect primary (english, hindi, hinglish, other)

REQUIRES_VERIFICATION: true if query needs loan-specific data

Indian NBFC customers frequently message in Hinglish (Hindi-English mix).
Treat Hinglish messages with the same confidence as English messages
when the intent is clear.

Few-shot examples:
'mera EMI kab hai' → {intent: emi_due_date, confidence: 0.95,
  entities: {}, sentiment: neutral, language: hinglish,
  requires_verification: true}
'AC2024001234 ka balance batao' → {intent: outstanding_balance,
  confidence: 0.95, entities: {loan_number: AC2024001234},
  sentiment: neutral, language: hinglish, requires_verification: true}
'I paid 5000 yesterday but still showing pending!!!' →
  {intent: payment_status, confidence: 0.90, entities: {amount: 5000},
  sentiment: frustrated, language: english, requires_verification: true}
'loan band karna hai kitna dena hoga' → {intent: foreclosure_quote,
  confidence: 0.92, entities: {}, sentiment: neutral,
  language: hinglish, requires_verification: true}
'hi' → {intent: greeting, confidence: 0.99, entities: {},
  sentiment: neutral, language: english, requires_verification: false}
'statement bhejo' → {intent: loan_statement, confidence: 0.93,
  entities: {}, sentiment: neutral, language: hinglish,
  requires_verification: true}
'paisa kata ki nahi' → {intent: payment_status, confidence: 0.91,
  entities: {}, sentiment: neutral, language: hinglish,
  requires_verification: true}
'I want to close my loan AC2024005678, how much foreclosure amount?' →
  {intent: foreclosure_quote, confidence: 0.97,
  entities: {loan_number: AC2024005678}, sentiment: neutral,
  language: english, requires_verification: true}
'yaar pehle bhi bol chuka hoon, abhi tak response nahi!!!' →
  {intent: complaint, confidence: 0.88, entities: {},
  sentiment: frustrated, language: hinglish, requires_verification: false}
'Thanks for the quick reply' → {intent: greeting, confidence: 0.85,
  entities: {}, sentiment: positive, language: english,
  requires_verification: false}
"
```

**Why this works for Hinglish/multilingual**: The LLM has seen Hindi, Hinglish, and transliterated text in pre-training. Messages like "mera EMI kab hai", "EMI kb h", "EMI kab hoga", and "when is my EMI" all map to the same intent. No keyword dictionaries, no transliteration tables, no fuzzy matching.

**Prompt evolution (5–6 iterations)**:
- v1.0: 8 English + 2 Hinglish examples → Hinglish confidence averaging 0.6 (War Story 1)
- v1.1: Rebalanced to 5 English + 5 Hinglish; added Hinglish equality instruction → confidence ~0.88
- v1.2: Added voice-to-text artifact examples (e.g., "emi kab kai") → handled transcription errors
- v1.3: Added frustrated-sentiment examples after complaint misclassifications
- v1.5: Added `payment_confirmation` and `document_upload` based on production traffic patterns
- v1.6: Added 5 more Hinglish examples covering edge cases; confidence on Hinglish stabilized at 0.88–0.93

### Experimentation Framework

**Evaluation metrics** (measured weekly/monthly):

| Metric | Measurement Method | Target | Achieved |
|--------|--------------------|--------|----------|
| Intent accuracy | 200-message manual sample | >90% | 90–93% overall; English ~94–96%, Hinglish ~88–92% |
| Entity extraction (loan number) | Exact match on labeled set | >95% | ~95%+ |
| Self-service resolution rate | Salesforce case resolution_type | 60–65% | 60–65% |
| Avg. resolution time (automated) | End-to-end latency from first message | <60s | <30s |
| Customer satisfaction (CSAT) | Post-conversation 1–5 rating | >3.5 | 3.5–4.0 |
| LLM structured output compliance | Langfuse: parse error rate | 0% | 0% (schema enforced by API) |

**Shadow mode pipeline**: New prompt version → deploys to 10% traffic shadow lane → Langfuse logs full input/output without serving → weekly batch evaluator compares against labeled set → promote if accuracy ≥ current or ≤ 1% degradation.

### Data Strategy

- **Zero labeled data at launch**: LLM structured output works with few-shot examples. Evaluation set built organically from production traffic over first 3 months.
- **Continuous improvement loop**: "Was this helpful? No" responses + agent corrections during escalation → review → most instructive failures added as few-shot examples. Monthly prompt review cycle, 2–3 new examples per cycle.
- **PII handling**: Phone numbers stored in CRM (Salesforce, system of record). Aadhaar numbers scrubbed from message text before LLM calls (regex pre-processing on UID format). Loan numbers (AC + 10 digits) are internal identifiers, not PII. Conversation content logged in Salesforce per RBI audit requirements.
- **Prompt injection defense**: Structured output schema constrains LLM response to the IntentResult JSON. LLM cannot output free-form text. LLM has no access to customer financial data — only classifies the message.

---

## 5. CORE LOGIC AND ALGORITHMS

### Algorithm 1: LLM-Powered Intent Classification + NER via Structured Output

**What it does**: Single GPT-4o-mini call classifies a WhatsApp message into 1 of 12 intents, extracts entities (loan number, amounts, dates), detects sentiment (4 levels), and identifies language — returned as a guaranteed-valid JSON object via `response_format: json_schema`.

**Why over alternatives**:
- Zero labeled training data at launch vs. 5–10K examples per intent needed for fine-tuned distilbert
- Hinglish handling native in LLM vs. transliteration pipeline + separate Hindi model
- Single call replaces 4 pipeline stages (intent, NER, sentiment, language)
- Adding a new intent = prompt edit (30 min) vs. retrain cycle (1–2 weeks)
- Cost: ~$0.03–0.05/day at 4,000 LLM calls

**Step-by-step logic**:
1. Receive WhatsApp message + session context
2. **Short-circuit**: If button/list reply → map button ID to intent deterministically (confidence 1.0, zero LLM cost). Handles ~20% of messages.
3. **Session context check**: If user is mid-flow and message matches expected input → continue flow without LLM call.
4. **LLM structured output call**: GPT-4o-mini with `response_format: json_schema`. Returns valid IntentResult JSON.
5. **Confidence routing** (LangGraph conditional edge): ≥0.8 → flow; 0.5–0.8 → confirmation; <0.5 → escalation; frustrated or complaint → always escalation.
6. **Entity pass-through**: Write extracted entities to LangGraph state; flow subgraph uses as API parameters.
7. **Logging**: Message + full LLM response + routing decision + latency + token count → Langfuse.

**Complexity**: O(1) per message. Latency: 200–400ms. Tokens: ~100–150 input + ~80–120 output.

**Edge cases**:
- Multi-intent messages: schema forces single intent, LLM picks primary. "Is there anything else?" handles secondary.
- Adversarial input / prompt injection: JSON schema enforced by API — no free-form output possible.
- LLM outage: Circuit breaker → button-only menu (deterministic, zero AI).
- Ambiguous abbreviations ("st"): LLM resolves via session context; without context, returns ~0.6 confidence → confirmation step.

---

### Algorithm 2: LangGraph Stateful Conversation Flow Execution

**What it does**: Manages multi-turn conversation flows as LangGraph StateGraph instances, with Redis-checkpointed state persistence, conditional routing, tool-calling nodes for CRM/LOS integration, and durable execution across interruptions.

**Why LangGraph over custom state machine**: Initial prototype used a Redis-backed state dict with if-else routing — unmaintainable beyond 3 intents. LangGraph provides: checkpointed persistence (conversations survive server restarts), conditional routing as declarative edges, built-in retry on node failures, graph visualization for debugging.

**Step-by-step logic**:
1. Receive inbound message + phone number
2. **State restore**: LangGraph loads Redis checkpoint for `thread_id=phone_number`. If none exists, create new state. Checkpoint TTL: 30 min idle, 24 hr absolute.
3. **Graph invocation**: `graph.invoke(state, config={"configurable": {"thread_id": phone_number}})`. LangGraph resumes from last checkpointed node.
4. **Node execution**: Each node reads shared `WhatsAppState`, performs action (LLM call, API call, formatting), returns updated state dict. LangGraph checkpoints after each node.
5. **Conditional routing**: Router node output drives edge evaluation.
6. **EMI inquiry subgraph example** (5 nodes):
   - `check_verification`: If `verification_status != verified`, route to identity_verification.
   - `resolve_loan`: If `loan_number` in entities, proceed. If not, send button list from CRM loans.
   - `fetch_emi_data`: FinnOne API: `get_emi_details(loan_id)`. Writes result to `tool_results`.
   - `format_response`: "Your next EMI of Rs {amount} for loan {loan_id} is due on {date}."
   - `send_with_csat`: Send outbound + "Was this helpful? [Yes] [No] [Other query]"
7. **Interruption handling**: If user sends off-topic message mid-flow, router re-classifies. High-confidence new intent → transition to new flow (previous flow state preserved in checkpoint). Closing message includes option to resume previous flow.
8. **Timeout**: Checkpoint TTL handles cleanup. 30 min idle → expired. Next message starts fresh.

**Edge cases**:
- "Just 'Hi'": greeting intent, no flow triggered. Welcome + button menu. Graph terminates at outbound node.
- Multiple active loans: subgraph detects multiple loans via Salesforce API, presents button list, stores selection in state.
- Server restart mid-conversation: checkpoint in Redis survives. Next message resumes from exact node. Zero user disruption.
- Long-running API call (>10s): FastAPI already returned 200 to BSP; LangGraph sends interim "Working on it..." message.

---

### Algorithm 3: CRM Synchronization and Agent Handoff Protocol

**What it does**: Ensures every WhatsApp interaction is reflected in Salesforce as a case with full context, and that agent handoffs carry complete conversation history so agents never ask customers to repeat themselves.

**Why required**: RBI regulation — every customer interaction at an NBFC must be logged and trackable. WhatsApp channel cannot be a silo.

**Step-by-step logic**:
1. **On session start**: Salesforce lookup by phone number. Found → attach `customer_id` to state, check for open cases on same topic. Not found → route to identity verification.
2. **On automated resolution**: `crm_sync_node` creates Salesforce case: `status=Closed-Automated`, `description=full LangGraph conversation transcript including intent confidence and tool results`.
3. **On escalation**: `escalation_node` creates Salesforce case: `status=Open-Escalated`, `subject=<intent>: Escalated (<reason>)`. Pushes to Omnichannel routing queue. Agent console shows: full transcript, intent + confidence, customer profile, extracted entities.
4. **Proactive follow-up**: Escalated case not picked up in ~15 min → template message: "We've received your query. Reference: [case_id]. An agent will respond shortly."
5. **After-hours**: Time-aware edge in escalation subgraph. Business hours (8 AM–8 PM): live queue. After hours: immediate template acknowledgment, case flagged "overnight" for morning priority queue.

**Edge cases**:
- **Salesforce down during conversation**: CRM sync is last node — customer gets response regardless. Retry with exponential backoff. Case created retroactively when API recovers.
- **Duplicate cases**: Deduplication: one case per (customer_id, intent) per 30-minute window.
- **24-hour WhatsApp window**: LangGraph state stores escalation timestamp. If >20 hours elapsed before agent response, system switches to pre-approved WhatsApp template message instead of session message.

---

## 6. INTERVIEW ATTACK SURFACE

### Q1 — Design: "Why LLM-based intent classification instead of a fine-tuned classifier or rule-based NLP?"

Three reasons. First, zero training data — we had no labeled corpus at launch. A fine-tuned distilbert needs 5–10K labeled examples per intent; we had zero. The LLM worked with 5–10 few-shot examples written in an afternoon. Second, multilingual handling — about 40–45% of messages were Hinglish. A classifier would need a transliteration pipeline, Hindi keyword dictionaries, and fuzzy matching for typos. The LLM handles "mera EMI kab hai", "EMI kb h", and "when is my EMI" identically. Third, single-call simplicity — one API call replaces four pipeline stages (intent, NER, sentiment, language). Cost: ~$0.03–0.05/day at 4,000 calls. The trade-off is external API dependency, mitigated by provider failover (OpenAI → Anthropic) and button-based fallback.

### Q2 — Scale: "What happens when WhatsApp message volume spikes 10x during month-end?"

The LLM call scales linearly — GPT-4o-mini handles 10x without rate limit concerns at our volume. The real bottleneck is Salesforce's 100K API calls/day limit. We saw 2.3x spikes month-end naturally. Mitigation: cache customer profile + loan details in Redis (5 min TTL) — on due-date days, 80% of queries are "what's my EMI", and the answer changes at most daily. Cache converts 10x message volume into ~1.5x Salesforce calls. For case creation: queue in Redis during spikes, batch flush every 5 minutes. LangGraph handles concurrent conversations without issues — each is an independent graph instance keyed by phone number.

### Q3 — Failure: "What if the LLM classifies a complaint as a balance inquiry?"

Two safety nets. First, sentiment override: the structured output includes sentiment. If LLM detects "frustrated" or "negative" — even with a misclassified intent — routing always escalates. A frustrated customer never interacts with a bot. Second, every automated response ends with "Was this helpful? [Yes] [No] [Talk to agent]". "No" or "Talk to agent" triggers immediate escalation. The misclassification costs one bad turn, not the entire conversation. We tracked misclassification rates per intent weekly via Langfuse — when complaint-intent accuracy dipped, we added targeted few-shot examples.

### Q4 — ML-Specific: "How do you evaluate LLM intent accuracy without a training/test set?"

Three methods. First, weekly human review: ~200 messages sampled, manually labeled, compared against LLM output — accuracy was 90–93% across languages after prompt tuning. Second, implicit feedback: "Was this helpful? No" rate per intent. EMI inquiry "No" rate spike → investigate within 48 hours (sometimes API data issue, sometimes misclassification). Third, agent correction data: during escalation, agent logs actual intent. Mismatches between LLM classification and agent labels give us labeled misclassification data. These corrections feed back into few-shot examples — the improvement cycle is prompt editing, not model retraining.

### Q5 — Trade-off: "What would you do differently if you rebuilt this today?"

Two things. First, proactive outreach flows from day one — "Your EMI of Rs 5,000 is due tomorrow. Reply PAY to confirm or HELP for options." This converts the chatbot from reactive support to a proactive collections/engagement channel. We had the template infrastructure but deprioritized the trigger engine. Second, voice note handling — a significant number of users send Hindi voice messages, and we responded with "Sorry, I can only read text." A Whisper-based speech-to-text step before the router would capture those users. The LangGraph architecture already supports inserting a pre-processing node; it was a roadmap decision, not an architecture constraint.

---

## 7. TROUBLESHOOTING WAR STORIES (STAR FORMAT)

### War Story 1: LLM Low Confidence on Hinglish Patterns

**Situation**: After deploying the LLM router, English intent accuracy was ~95%, but Hinglish messages ("loan band karna hai kitna dena hoga") returned confidence scores of 0.5–0.6, triggering unnecessary confirmation steps for ~30% of Hinglish queries. The LLM classified correctly but hedged on confidence.

**Task**: Improve Hinglish confidence from ~0.6 to ≥0.85 without degrading English accuracy.

**Action**:
1. Analyzed Langfuse traces: ~85% of low-confidence classifications were correct intent — the LLM knew but hedged.
2. Root cause: initial prompt had 8 English + 2 Hinglish few-shot examples. Weak anchoring for Hinglish patterns.
3. Rebalanced to 5 English + 5 Hinglish examples covering the top-5 intents in Hinglish phrasing.
4. Added explicit prompt instruction: "Indian NBFC customers frequently message in Hinglish. Treat Hinglish messages with the same confidence as English when the intent is clear."
5. Shadow-tested on ~300 Hinglish messages from the prior week before promoting.

**Result**: Hinglish average confidence jumped from ~0.62 to ~0.88. Unnecessary confirmation steps dropped from ~30% to ~8% of Hinglish queries. English accuracy unchanged. Fix: ~30 minutes of prompt editing, zero code changes, zero model retraining. Before: ~30% confirmation rate on Hinglish. After: ~8%.

---

### War Story 2: Identity Verification Bypass Attempt

**Situation**: A user sent a valid loan number (from a payment receipt) and provided correct DOB as second factor — information obtainable via social engineering. The system would have disclosed loan details to an unauthorized person.

**Task**: Strengthen identity verification without adding friction for legitimate customers (registered phone number).

**Action**:
1. Analyzed the verification flow: phone number (factor 1) + DOB (factor 2) — DOB is weak, commonly known, appears on multiple documents.
2. Redesigned to a three-tier model (identity_verification subgraph in LangGraph):
   - **Tier 1 (auto)**: Phone number matches CRM registered mobile → verified, no friction. Happy path for the vast majority.
   - **Tier 2 (lightweight)**: Phone doesn't match → loan number + last 4 digits of registered phone (not DOB). Only the borrower knows this; doesn't appear on public documents.
   - **Tier 3 (restricted)**: Tier 2 fails → generic info only (branch locator, FAQs, complaint registration). Directed to contact center with ID proof.
3. Rate-limited verification attempts to 3 per phone per 24 hours (brute-force protection).
4. All failures logged as security events in Salesforce for fraud team review.

**Result**: Eliminated DOB bypass vector. Registered-phone users (Tier 1, ~90% of traffic) experienced zero additional friction. Before: DOB-based bypass vector existed. After: zero loan data disclosure incidents post-fix. Verification failures rate: <0.5%.

---

### War Story 3: WhatsApp 24-Hour Window Causing Dropped Agent Responses

**Situation**: Customers messaged after hours (10 PM–8 AM). Bot escalated to agent queue. Agent picked up at 9 AM — but customers had moved on, or worse, >24 hours had elapsed and WhatsApp blocked the session message entirely.

**Task**: Handle after-hours escalations without stranding customers until morning.

**Action**:
1. Implemented time-aware conditional edge in escalation subgraph: business hours → live queue; after hours → immediate template acknowledgment + "overnight" case flag.
2. Priority queue: overnight cases surfaced at top of morning agent queue.
3. Proactive template re-engagement: when agent picks up, system checks elapsed time. If >20 hours since customer's last message, agent response sent via pre-approved WhatsApp template (works outside 24-hour window): "Hi [name], regarding your query about [intent]: [response]. Reply to continue."
4. Expanded automated resolution to reduce after-hours escalations in the first place.

**Result**: After-hours customer experience improved from "silent until morning" to "immediate acknowledgment + morning agent response." Zero 24-hour window blocking incidents post-fix. Before: ~15% of after-hours escalations dropped due to 24-hour window expiry. After: 0%.

---

### War Story 4: Salesforce Rate Limit Hit During Month-End Spike

**Situation**: A month-end due-date surge brought 8,200 messages in one day vs. the normal 3,500. Each conversation averaged 2.8 Salesforce API calls (customer lookup + case create + update) = ~23,000 Salesforce calls. This hit the Enterprise edition daily limit (100K/day) at approximately 6 PM, causing case creation failures for the remaining ~800 conversations.

**Task**: Restore CRM logging without losing any conversation data; prevent recurrence.

**Action**:
1. **Immediate (during incident)**: Identified Salesforce 429 responses in CloudWatch. Suspended non-critical Salesforce calls (case updates, enrichment queries). Kept only mandatory case creation calls.
2. **Emergency Redis queue**: Wrote a Redis queue for pending case creation. FastAPI continued receiving and processing messages; case creation calls enqueued instead of direct API calls.
3. **Batch flush**: Background job flushed queue every 5 minutes when Salesforce API recovered (midnight reset of daily limit). Cross-day deduplication to prevent duplicate cases across midnight boundary.
4. **Post-incident**: Implemented customer profile caching in Redis (5 min TTL) — eliminates ~1 Salesforce call per conversation. Implemented case creation batching by default for automated resolutions (real-time only for escalations, where agents need immediate access).

**Result**: Zero conversations lost. 100% case coverage achieved with a maximum 4-hour lag on batch-created cases (acceptable per our RBI compliance audit — the audit trail requirement is "within 24 hours", not real-time). Before: ~800 conversations without CRM logging. After: full coverage. Post-incident Salesforce API usage: ~12,000 calls/day on 5,000 messages (down from ~15,000) via caching.

---

### War Story 5: Button-Based Fallback During OpenAI Outage

**Situation**: OpenAI experienced a 47-minute partial outage. GPT-4o-mini structured output calls began returning HTTP 503 at approximately 2:15 PM. ~340 messages arrived during the outage window. The circuit breaker failover to Anthropic Haiku was also degraded (Anthropic had separate elevated latency, not a full outage, but p95 latency spiked to 8+ seconds — above our 5s budget).

**Task**: Maintain service continuity without the LLM router.

**Action**:
1. **Circuit breaker status** at T+0: OpenAI 503 → breaker opened after 5 consecutive failures (~40s). Anthropic failover attempted → p95 latency 8s → breaker opened after 3 consecutive timeout failures (~2 min).
2. **Button-only mode activated** at T+~8 min (the ~8 min is the gap before both circuit breakers opened). System automatically served: "I'm having trouble understanding you right now. Please choose from the options below: [EMI Info] [Balance] [Statement] [Complaint] [Talk to Agent]."
3. **Button-mode handling**: Button IDs map deterministically to intent without any LLM. Users selecting buttons received automated flows normally (Salesforce + FinnOne APIs unaffected).
4. **Recovery at T+47 min**: OpenAI reported recovery. Circuit breaker half-opened, test call succeeded, fully reopened. Free-text messages restored.

**Result**: 98.2% of the 340 inbound messages handled (button fallback processed 333/340). 7 messages lost — users who sent free text in the ~8 minutes before button-mode activated. Post-incident: reduced circuit breaker opening threshold from 5 failures to 3, reducing the button-mode activation lag from ~8 min to ~3 min. Before: ~8 min exposure window before degraded mode. After: ~3 min.

---

## 8. DEEP DIVES

### Deep Dive 1: LangGraph StateGraph for Multi-Turn Financial Conversations

**Why StateGraph over a custom state machine**

A custom Redis-backed state dict (our first prototype) worked for 2 intents and became unmaintainable at 5. Every new flow required touching the routing logic, adding if-else branches in the main handler, and manually managing state serialization. LangGraph StateGraph gave us:

- **Declarative routing**: Conditional edges are data — `graph.add_conditional_edges(router_node, route_function, {...})`. Adding a new intent = new subgraph + one new edge mapping. No changes to the orchestration layer.
- **Automatic checkpointing**: Every node completion writes a checkpoint. LangGraph uses a `BaseCheckpointSaver` — we used `AsyncRedisSaver` from `langgraph-checkpoint-redis`. No custom serialization code.
- **Resume after interruption**: Server restarts, crashes, or planned deployments don't lose conversations. `graph.invoke(state, config={"configurable": {"thread_id": phone_number}})` always resumes from the last completed node.
- **Graph visualization**: LangGraph Studio (local dev) renders the graph. Invaluable for onboarding new developers and debugging unexpected routing paths.

**Checkpoint schema and TTL strategy**

LangGraph checkpoints stored in Redis as: `key = langgraph:checkpoint:{thread_id}:{checkpoint_id}`. We set two TTLs via a custom `CheckpointManager` wrapper:

- **Idle TTL**: 30 minutes. If no new message in 30 min, checkpoint expires. Next message from the same user starts fresh (new conversation context).
- **Absolute TTL**: 24 hours. Even active conversations expire after 24 hours. This prevents state accumulation and aligns with WhatsApp's session windows.
- **Explicit cleanup**: On `END` node completion, we proactively delete the checkpoint rather than waiting for TTL. This reduces Redis memory pressure and avoids stale state confusion if a user immediately starts a new conversation.

**Interruption handling (mid-flow intent switch)**

The most complex case: user is 3 steps into a foreclosure quote flow and sends "actually, what's my EMI date?" The LangGraph router re-runs on the new message. If the new intent has confidence ≥ 0.8, we have two options:

1. **Abandon and switch**: Clear current_flow from state, start EMI flow. Simple but loses the foreclosure context.
2. **Suspend and switch (our approach)**: Write `suspended_flow = "foreclosure_quote"` and `suspended_step = 3` to state. Start EMI flow. After EMI resolution, response includes: "Also, would you like to continue with your foreclosure quote?" User clicks [Yes] → restore suspended flow at step 3.

This required a custom `SuspendedFlowManager` utility that wraps the LangGraph state update — not built into LangGraph, but LangGraph's open state schema made it easy to add.

**Compliance-specific extensions**

Standard LangGraph patterns don't include compliance nodes. We added two mandatory nodes that always run regardless of intent:

1. **`identity_verification_node` (entry)**: Runs before the router. Phone number lookup in Salesforce. Tier 1/2/3 decision. Only Tier 1 (exact phone match) gets direct routing. Without this as a mandatory entry, a developer adding a new flow could accidentally skip verification.
2. **`crm_sync_node` (exit)**: Runs after every flow completion. Creates or updates Salesforce case. Implemented as the second-to-last node before `outbound_node`. If CRM sync fails, the outbound message still sends — customer experience is never blocked by CRM. The sync retries independently.

---

### Deep Dive 2: LLM Structured Output for Intent + NER Pipeline Collapse

**Schema design decisions**

The key schema tension: should `IntentResult` be a flat schema or a discriminated union per intent? We went flat. The argument for discriminated union (e.g., `EMIIntent` has different entity fields than `ForeClosureIntent`) is type safety. The argument against: complexity. With 12 intents, a discriminated union would need 12 schemas. The LLM also handles the classification step — the discriminated union only helps if you know the intent before generating the schema, which you don't. Flat schema with nullable fields was the right call: simpler prompt, simpler parsing, schema stays in one place.

**Provider compatibility (OpenAI vs. Anthropic)**

OpenAI's `response_format: json_schema` mode enforces the schema at the API level. The LLM's response is guaranteed to parse against the schema — we've never seen a parse error in production.

Anthropic's structured output works differently: you define the schema as a tool definition, call the tool, and extract from `tool_use` blocks. The prompt structure is different:
- OpenAI: schema in `response_format`, instruction in system prompt
- Anthropic: schema in `tools`, instruction to "use the classify_intent tool"

We maintain two prompt variants (`prompt_openai.py` and `prompt_anthropic.py`) with a provider abstraction layer. Failover to Anthropic required rebuilding the tool call structure, not just swapping the client — an underappreciated complexity when designing multi-provider failover.

**Confidence calibration (how the 0.8 threshold was set)**

We started with 0.9 and saw 40% of queries hit the confirmation node — too many unnecessary confirmation steps for clear English queries. We moved to 0.7 and saw a measurable increase in wrong-flow activations (about 3–4 per day, manually identified via Langfuse + "Was this helpful? No" signals). We settled on 0.8 after two weeks of A/B testing at the threshold:

- At 0.8: ~12% confirmation rate, ~0.8% wrong-flow activations
- At 0.9: ~40% confirmation rate, ~0.2% wrong-flow activations
- At 0.7: ~6% confirmation rate, ~3.5% wrong-flow activations

0.8 was the empirical sweet spot. The calibration is prompt-dependent — changing the prompt requires re-running this experiment, which we did for every major prompt version.

**Hallucination risk mitigation via enum enforcement**

The `intent` field is a string enum with 12 values. OpenAI's `json_schema` with `"strict": true` means the LLM cannot output an intent outside the enum. We've tested this by deliberately trying to elicit novel intents ("I want to refinance my loan" — not in the schema) and the LLM consistently maps to `unknown`. This is a key safety property for NBFC compliance — the system can never act on a hallucinated intent category, because hallucinated intents don't exist in the schema.

---

### Deep Dive 3: Identity Verification Subgraph (Three-Tier Model)

**Tier decision logic**

```
Inbound message → identity_verification_node
    |
    v
Lookup phone_number in Salesforce CRM
    |
    +-- MATCH found → verification_status = "verified" → Tier 1 (automatic)
    |      No additional prompt. User proceeds to router immediately.
    |
    +-- NO MATCH → check verification_attempts_today < 3
           |
           +-- Under limit → Tier 2 prompt:
           |     "Please provide your loan number and last 4 digits
           |      of your registered mobile number."
           |     |
           |     +-- MATCH → verification_status = "verified" → proceed
           |     +-- NO MATCH → log security_event → Tier 3
           |
           +-- Over limit (≥3 attempts) → Tier 3 directly
                 verification_status = "restricted"
                 Response: "For security, please visit your nearest branch
                 or call our helpline at [number]. Reference: [case_id]."
```

**Why DOB was replaced as the second factor**

DOB is a type-2 KYC factor that appears on Aadhaar cards, PAN cards, loan application forms, payment receipts, and is trivially socially engineered. In an NBFC context where loan numbers are visible on payment receipts (which get shared), a compromised loan number + DOB = full account access.

The last 4 digits of the registered phone number is a better second factor because:
- It's not visible on any document the borrower typically shares
- It's known to the legitimate borrower but unlikely to be known to someone who only found a payment receipt
- It's easier for the legitimate borrower to recall than a security question

The information we do NOT ask for: Aadhaar number (DPDP Act — cannot share with LLM), full account number (exceeds what's needed), passwords (never).

**Rate limiting against brute-force**

Verification attempts stored in Redis: `key = verify_attempts:{phone_number}`, `TTL = 86400s (24 hr)`, `value = integer count`. On each Tier 2 attempt: `INCR verify_attempts:{phone_number}`. If count ≥ 3: route to Tier 3. The rate limit is per-phone (the attacker's number), not per-loan-number — this prevents an attacker from trying the same loan number from multiple phones by rate-limiting based on the source.

All Tier 2 failures and Tier 3 entries generate a Salesforce security event record (object: `Security_Event__c`) with: phone_number, loan_number_attempted, attempt_count, timestamp. The fraud team runs a daily report on security events.

---

## 9. COMPLIANCE AND REGULATORY

### Regulatory Framework

This system operates under three primary regulatory frameworks applicable to NBFCs in India:

| Regulation | Issuing Authority | Key Obligation Relevant to This System |
|------------|-------------------|---------------------------------------|
| RBI Master Direction on Digital Lending (2022) | Reserve Bank of India | All customer interactions must be logged; data must not be stored with third-party service providers without consent |
| RBI Fair Practices Code for NBFCs | Reserve Bank of India | Complaint handling SLAs; customer service response time logging |
| Digital Personal Data Protection (DPDP) Act 2023 | Government of India | PII handling; purpose limitation; data retention limits; consent requirements |

### How Each Regulation Maps to a Concrete System Design Decision

**RBI Master Direction on Digital Lending — Interaction Logging**

*Requirement*: Every customer interaction must be logged and auditable. Data residency must be maintained within India.

*System design decision*: Every conversation — whether automated or escalated — creates a Salesforce case (`CRMCase` object) with the full conversation transcript, LLM intent confidence, extracted entities, resolution type, and timestamps. AWS infrastructure deployed in `ap-south-1` (Mumbai region) to satisfy data residency. Salesforce org is India-hosted or via Standard Contractual Clauses with data residency [ASSUMPTION — verify with Salesforce contract].

*Why not just Langfuse traces?* Langfuse is the LLM observability tool — it logs prompts, responses, and latency. But it's not the system of record for customer interactions (it's an LLM-specific tool, and the data lives outside India if using cloud Langfuse). The Salesforce case is the compliance record; Langfuse is the debugging tool.

**RBI Master Direction — Separation of Data at Third-Party Providers**

*Requirement*: Customer data should not be stored with LLM providers beyond what is necessary for the inference call.

*System design decision*: The LLM call receives only the raw WhatsApp message text (plus the system prompt). No customer name, customer ID, phone number, or financial data is included in the LLM API call. Extracted entities (loan number) are internal identifiers, not PII. Aadhaar numbers are scrubbed from message text via regex pre-processing before the LLM call — if a customer includes their Aadhaar in a message (common mistake), it never reaches OpenAI's servers.

**RBI Fair Practices Code — Complaint Handling SLAs**

*Requirement*: NBFCs must acknowledge customer complaints and respond within defined timelines.

*System design decision*: `intent == complaint` always routes to the escalation node regardless of confidence — this is a hard compliance rule, not a business preference. Every complaint creates a Salesforce case with `case_type = "Complaint"` and triggers immediate WhatsApp acknowledgment: "We've received your complaint and will respond within [SLA timeline]. Reference: [case_id]." The SLA timer starts at case creation. Agents get the case in their Omnichannel queue with the complaint classification and full transcript.

**DPDP Act 2023 — PII Scrubbing and Data Retention**

*Requirement*: Purpose limitation (data collected only for stated purpose), storage limitation (data retained only as long as necessary), and data subject rights (right to erasure).

*System design decisions*:
1. **PII scrubbing before LLM**: Aadhaar pattern regex (`\d{4}\s\d{4}\s\d{4}`) applied to inbound message text before LLM API call. Matches replaced with `[AADHAAR_REDACTED]`. This ensures Aadhaar — a unique biometric identifier — never reaches OpenAI/Anthropic servers.
2. **Conversation transcript retention**: Salesforce cases retained per RBI requirement (~7 years for NBFC audit records). LangGraph Redis checkpoints expire within 24 hours — no long-term storage of raw conversation state in Redis.
3. **LLM prompt/response logs in Langfuse**: Langfuse traces contain message text. Data retention policy: 90 days. Langfuse's retention setting is configured accordingly. If customer exercises right to erasure, Langfuse traces identified by `phone_number_hash` (phone number stored as SHA-256 hash in Langfuse `metadata`, not plain text) can be selectively purged [ASSUMPTION — verify Langfuse purge capability against current version].
4. **Consent**: WhatsApp Business opt-in flow (managed by Gupshup BSP) collects customer consent for messaging before any interaction. Consent records stored in Salesforce.

### Compliance → Architecture Traceability Matrix

| Compliance Requirement | System Component | Implementation Detail |
|------------------------|-----------------|----------------------|
| RBI: Log every customer interaction | `crm_sync_node` | Mandatory exit node in every flow. Creates Salesforce CRMCase with full transcript. |
| RBI: Complaints must reach human agents | Escalation routing | `intent == complaint` → always escalation, enforced as hard routing rule, not business logic. |
| RBI: Data residency India | AWS deployment | `ap-south-1` (Mumbai). |
| DPDP: No Aadhaar to third-party AI | Pre-processing before router node | Regex scrub of Aadhaar pattern before LLM API call. |
| DPDP: Purpose limitation | LLM scope | LLM receives only message text. No customer PII, name, or financial data in LLM call. |
| DPDP: Storage limitation | Redis TTL + Langfuse retention | Checkpoints: 24hr. Langfuse: 90 days. Salesforce: per RBI retention policy. |
| DPDP: Consent | Gupshup opt-in | WhatsApp opt-in managed by BSP; consent record in Salesforce. |

---

## 10. COST ANALYSIS

### Provider Pricing (2024 baseline — verify current rates)

| Component | Pricing Tier |
|-----------|-------------|
| GPT-4o-mini (`gpt-4o-mini-2024-07-18`) | $0.15/1M input tokens, $0.60/1M output tokens |
| Claude Haiku (fallback — rarely used) | $0.25/1M input tokens, $1.25/1M output tokens [ASSUMPTION — verify current Anthropic pricing] |
| Salesforce Enterprise | Included in license; ~100K API calls/day limit |
| FinnOne | On-premise; internal infrastructure cost only |
| AWS ElastiCache cache.t3.micro | ~$0.017/hr = ~$12.24/month |
| AWS EC2 t3.medium × 2 | ~$0.0416/hr × 2 = ~$0.083/hr = ~$60/month (on-demand; Reserved would be ~$35/month) |
| AWS ALB | ~$0.008/hr + $0.008/LCU = ~$6–10/month at our traffic level |
| AWS Route 53 | ~$0.50/hosted zone/month + query costs ≈ ~$1/month |
| Gupshup BSP | Per-message pricing; WhatsApp Business fees: ~$0.004–0.005/conversation (24hr window) in India tier |
| Langfuse (self-hosted or cloud) | Self-hosted on EC2: $0 software cost; cloud tier: varies [ASSUMPTION — verify if self-hosted or cloud] |

### Per-Call Cost Breakdown (GPT-4o-mini)

| Message type | LLM call? | Tokens (in + out) | LLM cost/message |
|-------------|-----------|-------------------|-----------------|
| Free-text message needing classification | Yes | ~150 input + ~100 output = 250 total | $0.15 × 0.00015 + $0.60 × 0.0001 = $0.0000225 + $0.000060 = ~$0.000083 |
| Button/list reply | No (short-circuit) | 0 | $0.00 |
| Mid-flow continuation (expected input) | No (session context) | 0 | $0.00 |

~80% of messages require an LLM call; ~20% are buttons or mid-flow continuations.

### Daily and Monthly Cost at Operating Volume

| Component | Volume | Cost/Day | Cost/Month |
|-----------|--------|----------|------------|
| GPT-4o-mini (intent classification) | ~4,000 LLM calls/day × 250 tokens avg | ~$0.033 | ~$1.00 |
| GPT-4o-mini (confirmation node re-calls) | ~480 calls (12% of 4,000) × 200 tokens | ~$0.004 | ~$0.12 |
| Anthropic Haiku (failback — rare) | ~20 calls/day average | ~$0.0001 | ~$0.003 |
| Salesforce API | ~15,000 calls/day (within license) | $0 | $0 |
| FinnOne API | Internal on-premise | $0 | $0 |
| Redis (ElastiCache cache.t3.micro) | Always-on | ~$0.40 | ~$12 |
| EC2 t3.medium × 2 (on-demand) | Always-on | ~$2.00 | ~$60 |
| ALB | Always-on | ~$0.27 | ~$8 |
| WhatsApp Business (via Gupshup) | ~3,500 conversations/day × $0.004 | ~$14.00 | ~$420 |
| **Total AI/infra (excl. WhatsApp)** | | **~$2.70/day** | **~$80/month** |
| **Total incl. WhatsApp messaging** | | **~$16.70/day** | **~$500/month** |
| **LLM cost only** | | **~$0.037/day** | **~$1.12/month** |

**Key insight**: WhatsApp messaging fees (Gupshup/Meta) dwarf LLM costs. LLM is ~0.2% of total operating cost. Infrastructure (EC2 + Redis + ALB) is ~16% of total. The dominant cost is the WhatsApp Business conversation fee.

### Cost at 10x Volume (Scaling Scenario)

| Component | 10x Volume | Cost/Month | Notes |
|-----------|-----------|------------|-------|
| GPT-4o-mini | ~40,000 LLM calls/day | ~$10 | Linear scale |
| EC2 (auto-scale) | t3.medium → add 2 more instances | ~$120 | Auto Scaling Group |
| ElastiCache | cache.t3.micro → cache.t3.small | ~$25 | More concurrent sessions |
| Salesforce API | Would hit limits; caching required | $0 (license) | Caching essential |
| WhatsApp messaging | ~35,000 conversations/day | ~$4,200 | Dominant cost |

**LLM is never the scaling bottleneck**. Salesforce API limits and WhatsApp conversation fees are the governing constraints at 10x.

---

## 11. OBSERVABILITY

### LLM Observability — Langfuse

Every LLM call emits a Langfuse trace. The trace hierarchy:

```
Trace (thread_id = phone_number, session_id = checkpoint_id)
  └── Span: router_node
        ├── Input: {system_prompt_version, user_message, session_context}
        ├── Output: {intent, confidence, entities, sentiment, language}
        ├── Model: gpt-4o-mini
        ├── Tokens: {input: 148, output: 94, total: 242}
        ├── Latency: 312ms
        └── Metadata: {
              routing_decision: "emi_flow",
              confidence: 0.94,
              language: "hinglish",
              prompt_version: "v1.6.0"
            }
```

**Custom evaluators (weekly batch)**:

1. **Intent accuracy evaluator**: Reads 200 random Langfuse traces from the past week. Fetches human labels from the Salesforce case (agent-corrected intent where available; manual labels otherwise). Computes accuracy per intent + overall. Writes results back to Langfuse as evaluation scores. Alerts if accuracy drops >2% from baseline.

2. **Confidence calibration evaluator**: For each confidence bucket (0.5–0.6, 0.6–0.7, 0.7–0.8, 0.8–0.9, 0.9–1.0), computes the empirical accuracy of classifications that landed in that bucket. Well-calibrated model should have accuracy ≈ confidence. Plots calibration curve weekly.

3. **Language distribution tracker**: Counts intent calls by `language_detected`. Alerts if Hinglish proportion changes significantly (could indicate prompt regression on Hinglish).

**Langfuse dashboards**:

| Dashboard | Metrics | Alert Threshold |
|-----------|---------|-----------------|
| Daily intent distribution | Count per intent per day | >20% shift from 7-day average |
| Confidence score histogram | Distribution across confidence buckets | >5% increase in <0.5 bucket |
| Language breakdown | English/Hindi/Hinglish/Other % | >10% shift in Hinglish % |
| Latency by model | P50/P95/P99 LLM call latency | P95 >800ms |
| Token usage | Average tokens/call, total tokens/day | >20% cost increase week-over-week |
| Prompt version comparison | Accuracy by prompt version | Used during shadow mode evaluation |

### Infrastructure Observability — CloudWatch

**Custom metrics (emitted from FastAPI middleware + LangGraph node wrappers)**:

| Metric | Namespace | Dimensions | Target | Alert Threshold |
|--------|-----------|------------|--------|-----------------|
| `WebhookSuccessRate` | `WhatsApp/Ingestion` | None | >99.5% | <99% for 5 min |
| `EndToEndLatencyP50` | `WhatsApp/Latency` | None | <2,000ms | >3,000ms |
| `EndToEndLatencyP95` | `WhatsApp/Latency` | None | <5,000ms | >7,000ms |
| `LLMProviderErrorRate` | `WhatsApp/LLM` | Provider | <1% | >1% for 3 min |
| `SalesforceAPIErrorRate` | `WhatsApp/CRM` | None | <0.5% | >0.5% for 5 min |
| `CircuitBreakerState` | `WhatsApp/Reliability` | Component | CLOSED | OPEN for any component |
| `ButtonFallbackActivations` | `WhatsApp/Degraded` | None | 0 | >0 (immediate alert) |
| `VerificationTier3Rate` | `WhatsApp/Security` | None | <0.5% | >1% (fraud signal) |

**CloudWatch Alarms → SNS → PagerDuty**:
- P95 latency >7s: immediate page
- LLM circuit breaker OPEN: immediate page
- Webhook success rate <99%: immediate page
- Salesforce error rate >0.5%: warning (not page — retry queue handles it)

**Log groups**:
- `/whatsapp-agent/application`: FastAPI + LangGraph structured JSON logs
- `/whatsapp-agent/llm-calls`: LLM request/response summaries (no full prompts — PII risk)
- `/whatsapp-agent/security-events`: Verification failures, circuit breaker state changes

### Business Metrics — Salesforce Reports

| Metric | Source | Target | Notes |
|--------|--------|--------|-------|
| Automated resolution rate | CRMCase `resolution_type` | 60–65% | Primary success metric |
| Escalation rate by intent | CRMCase + intent field | — | Foreclosure: 15–20%; Complaints: 100% (by design) |
| Average agent pickup time | Escalated case: created_at → first agent response | <15 min (business hours) | SLA for Fair Practices Code |
| Post-conversation CSAT | CRMCase `satisfaction_rating` | ≥3.5 avg | 1–5 scale |
| After-hours case resolution | Case created after 8 PM; resolved before 10 AM | >95% | Measures overnight backlog |
| 24-hour window violations | Cases where agent response >24h after last customer message | 0 | Compliance metric |

---

## 12. DEPLOYMENT

### Infrastructure — AWS ap-south-1 (Mumbai)

```
[Route 53]
    |
    v (HTTPS, SSL termination)
[Application Load Balancer]
    |
    v
[Auto Scaling Group]
[EC2 t3.medium × 2 (min=2, max=6)]
[FastAPI ≥0.115.6 + LangGraph ≥0.2.60]
[Docker container — python:3.12-slim base]
    |
    +-----------------------------+
    |                             |
    v                             v
[ElastiCache cache.t3.micro]   [AWS Secrets Manager]
[Redis 7.x]                    [API keys: OpenAI, Anthropic,
[LangGraph checkpoints]         Salesforce OAuth, Gupshup BSP,
[Session TTLs]                  FinnOne credentials]
    |
    +-----------------------------+
    |                             |
    v                             v
[Gupshup BSP]            [Salesforce Enterprise]
[WhatsApp Cloud API]     [REST API + Omnichannel]
    |
    v
[FinnOne LOS]
[On-premise API]
[VPN tunnel to AWS VPC]

[Langfuse — LLM observability]
[Self-hosted on separate EC2 t3.small OR Langfuse Cloud]

[CloudWatch — infrastructure metrics + alarms]
[SNS → PagerDuty for critical alerts]
```

### Containerization

**Dockerfile** (python:3.12-slim base, `uv` for dependency management):
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev
COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Python version**: 3.12 (pinned in `.python-version`)

**Key dependencies** (`pyproject.toml`):
```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.6",
    "langgraph>=0.2.60",
    "langchain-core>=0.3.0",
    "langchain-openai>=0.2.0",
    "langchain-anthropic>=0.3.0",
    "langgraph-checkpoint-redis>=0.1.0",
    "pydantic>=2.0.0",
    "redis>=5.0.0",
    "langfuse>=2.0.0",
    "boto3>=1.35.0",
    "simple-salesforce>=1.12.0",
    "httpx>=0.27.0",
    "uvicorn[standard]>=0.32.0",
]
```

### CI/CD Pipeline

**AWS CodePipeline** (or Cloud Build on GCP — `cloudbuild.yaml` present in repo):

```
[GitHub push to main]
    |
    v
[CodePipeline: Source stage]
    |
    v
[CodeBuild: Build stage]
  - uv sync --frozen
  - pre-commit run --all-files
  - pytest tests/ --cov=app --cov-fail-under=75
  - docker build -t whatsapp-agent:$COMMIT_SHA .
  - docker push $ECR_URI:$COMMIT_SHA
    |
    v
[CodeDeploy: Deploy to Staging]
  - Blue/green deployment to t3.medium staging instance
  - Integration tests against staging BSP sandbox
  - Manual approval gate
    |
    v [Manual approval]
[CodeDeploy: Deploy to Production]
  - Rolling deployment to ASG (1 instance at a time)
  - Health check: GET /health → 200
  - Rollback trigger: CloudWatch alarm (P95 latency >7s OR error rate >2%)
```

### Dev Workflow

**Local development**:
- `make dev` → starts FastAPI with hot-reload via `uv run uvicorn main:app --reload`
- `langgraph.json` → LangGraph Studio configuration. `make studio` → opens local graph visualization
- `make test` → `pytest tests/` (unit + integration tests with mocked LLM/CRM)
- `make lint` → `pre-commit run --all-files`

**Pre-commit hooks** (`.pre-commit-config.yaml`):
- `ruff` — linter + formatter
- `mypy` — type checking
- `detect-secrets` — prevents accidental credential commits
- `end-of-file-fixer`, `trailing-whitespace`

**Makefile targets**:
```make
dev:       uv run uvicorn main:app --reload --port 8000
test:      uv run pytest tests/ -v --cov=app
lint:      uv run pre-commit run --all-files
studio:    uv run langgraph studio --config langgraph.json
deploy:    aws codepipeline start-pipeline-execution --name whatsapp-agent-prod
logs:      aws logs tail /whatsapp-agent/application --follow
```

**Environment configuration** (12-factor, via Secrets Manager):
- Dev: `.env` file (not committed; `.env.example` in repo)
- Production: AWS Secrets Manager. `boto3` fetches secrets at startup.

---

## 13. APPENDIX — STUDY PROMPTS

Use these prompts to drill deeper on any section before an interview.

---

**Appendix A: LangGraph Deep Dive**

"Walk me through LangGraph graph resumption in detail — how does `graph.invoke()` know where to resume? What's in the checkpoint? What's the `thread_id` and why is it the phone number? If I restart the FastAPI server mid-conversation, exactly what happens on the next message? What's `AsyncRedisSaver` vs. `MemorySaver` and when would you use each? If I wanted to support 10,000 concurrent conversations, what Redis instance tier and what LangGraph configuration changes would I need?"

---

**Appendix B: Prompt Engineering and Structured Output**

"Show me your router node system prompt. Why are the few-shot examples ordered the way they are? How do you handle a message that genuinely doesn't fit any intent — what does the LLM output and what does the routing do? If you were to add a 13th intent (e.g., 'repayment_schedule'), what changes do you make and in what order? Why did you choose flat schema over a discriminated union? How does `response_format: json_schema` with `strict: true` differ from `response_format: json_object` and why does the difference matter here? What's the token budget for your classification call and why?"

---

**Appendix C: Salesforce Integration**

"How does your Salesforce OAuth flow work — client credentials or user-based OAuth? Where are the tokens stored and how are they refreshed? What does a Salesforce CRMCase look like after an escalated conversation — what fields are populated, and which field carries the full transcript? How does Salesforce Omnichannel routing work and how does your system push to it? If your Enterprise edition is at 80% of its 100K daily API call limit, what's the first thing you do? How would you move to batch case creation for automated resolutions without breaking the compliance audit trail?"

---

**Appendix D: Regulatory and Compliance**

"For the RBI Master Direction on Digital Lending — what specifically does it say about AI/LLM usage in NBFC customer service? How does your design satisfy the requirement that a customer can request a record of all interactions? Under DPDP Act 2023, if a customer invokes their right to erasure, what data do you delete and from which systems? How do you handle Langfuse traces that contain the customer's message text — is that PII under DPDP? What's the retention period for NBFC customer interaction records under RBI guidelines? If the RBI auditor asks to see all interactions for customer X over the last 6 months, what's the exact query you run and in which system?"

---

**Appendix E: Scaling and Architecture**

"Your current system handles 5,000 messages/day. Design for 50,000 messages/day. What's your Salesforce API strategy? What cache tier does Redis need? Do you need a separate LangGraph server (LangGraph Platform) or can you still run in-process? What happens to your WhatsApp Business messaging costs? At 50,000 messages/day, what's the new dominant cost? If OpenAI GPT-4o-mini rate limits you at high volume, what's the plan? For zero-downtime deployments, how do you ensure in-flight conversations don't lose state when you update the Docker image?"

---

## 14. NEXT ACTIONS MENU

1. **"Mock interview on this system"** — 5–7 rapid-fire questions across Design, Scale, Failure, ML, and Compliance. You answer, critique follows with the model answer from this document.
2. **"Drill deeper on [component]"** — Any of: LangGraph checkpoint schema, structured output schema design, Salesforce Omnichannel handoff, identity verification subgraph logic, Langfuse evaluator setup, cost analysis assumptions, DPDP Act compliance mapping.
3. **"Show me the code for [specific logic]"** — LangGraph graph definition, router node with structured output, identity verification subgraph, CRM sync tool node, circuit breaker wrapper, confidence-based conditional edge.
4. **"Extend this system"** — Proactive outreach flows (EMI reminders via template messages), voice note handling (Whisper integration before router), multi-language expansion (Tamil, Telugu), agent assist mode (LLM-suggested responses for human agents).
5. **"Validate my assumptions"** — List all `[ASSUMPTION — verify]` markers in this document: Salesforce data residency contract, Langfuse self-hosted vs. cloud, Anthropic Haiku exact model ID, current Anthropic pricing tier.
