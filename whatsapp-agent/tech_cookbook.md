CRM-Integrated WhatsApp Chatbot with AI-Assisted Conversation Flows

## Line Item

> "Designed and deployed a CRM-integrated WhatsApp chatbot with LLM-powered intent classification and multi-turn conversation orchestration, enabling automated self-service for loan queries at an NBFC — handling multilingual (English/Hinglish) messages, integrating with Salesforce CRM and FinnOne LOS, and reducing manual follow-ups for the customer service team."

---

## Pre-Analysis

- **Core system/product**: WhatsApp chatbot for NBFC customer service, integrated with Salesforce CRM and FinnOne loan management system, with LLM-powered intent classification and LangGraph-based workflow orchestration
- **Tech stack**: WhatsApp Business API (via BSP), FastAPI, LangGraph (StateGraph + Redis checkpointing), LLM structured output (GPT-4o-mini / Claude Haiku), Salesforce REST API, FinnOne API, Langfuse, Redis, AWS
- **Scale**: ~3,000-5,000 messages/day, 10-12 intent categories, multilingual (English + Hinglish), ~60-65% automated resolution rate
- **Domain context**: Aeon Credit Service India (NBFC), consumer lending, customer service — EMI queries, payment status, foreclosure quotes, complaint escalation

---

## 1. SYSTEM OVERVIEW

A WhatsApp-based customer service chatbot deployed at Aeon Credit Service, integrated with Salesforce CRM and the loan management system (FinnOne). Borrowers self-serve on common queries — EMI due dates, outstanding balance, payment status, loan statements, foreclosure quotes — without calling the contact center or waiting for manual agent responses.

The AI layer uses an LLM (via OpenAI/Anthropic SDK) with structured output to classify intent and extract entities (loan number, date ranges, amounts) in a single call. This was a deliberate choice over a fine-tuned classifier — we had zero labeled training data at launch, and roughly 40-45% of inbound messages were Hinglish (Hindi-English code-mix). A single LLM call with structured output handled intent classification, entity extraction, sentiment detection, and language identification across English, Hindi, and Hinglish without any transliteration or preprocessing pipeline.

A LangGraph-based workflow orchestrator manages multi-turn conversation flows as stateful graphs, routing between automated resolution (CRM/LOS API lookups) and human agent escalation with full context. We adapted the LangGraph StateGraph pattern for a compliance-sensitive NBFC context — adding identity verification, regulatory audit logging via Salesforce cases, sentiment-based escalation overrides, and a button-based degraded mode for LLM outages.

CRM integration ensures every interaction is logged as a Salesforce case, agent handoffs carry full conversation history, and follow-up reminders are automated — eliminating the manual follow-up cycle where agents had to call back customers who messaged outside business hours.

### Scope and Limitations

- The LLM handles **routing and comprehension only** — it does not generate financial data. Loan amounts, due dates, and balances come from FinnOne/Salesforce API calls. This separation is non-negotiable for compliance.
- Multi-intent messages (e.g., "tell me my EMI and also send me a statement") are handled sequentially — the system resolves the primary intent first, then prompts "Is there anything else?" We evaluated adding a `secondary_intent` field to the schema but decided the added complexity wasn't justified given low multi-intent frequency (~5-8% of messages).
- The system supports text messages and interactive button/list replies. Media messages (images, voice notes) are acknowledged but not processed — voice notes are a known gap, since many users send voice messages in Hindi.

---

## 2. HIGH-LEVEL DESIGN (HLD)

### System Architecture

```
[Borrower on WhatsApp]
         |
         v (WhatsApp Business API / BSP)
[BSP Gateway (Gupshup)]
         |
         v (webhook - inbound message)
[Message Ingestion Service (FastAPI on AWS)]
         |
         +---> [Session Manager (Redis / ElastiCache)]
         |
         v
[LangGraph Workflow Orchestrator]
         |
         v
[Router Node (LLM-powered)]
  - Intent classification (12 categories)
  - Entity extraction (loan number, amount, dates)
  - Sentiment detection (4 levels)
  - Language identification
  - All in ONE structured output call
         |
         +--- automated intent -------> [Resolution Subgraph]
         |                                      |
         |                             +--------+--------+
         |                             |                 |
         |                             v                 v
         |                      [Salesforce CRM    [FinnOne/LOS
         |                       API Tool]          API Tool]
         |                             |                 |
         |                             v                 v
         |                      [Case Logger]     [Loan Data
         |                                        Fetcher]
         |                             |                 |
         |                             +--------+--------+
         |                                      |
         |                                      v
         |                             [Response Formatter Node]
         |                                      |
         +--- escalation intent -------> [Agent Handoff Node]
         |                                      |
         |                                      v
         |                             [Salesforce Omnichannel
         |                              Console]
         |
         v
[Outbound Message Node]
         |
         v (WhatsApp API - outbound)
[Borrower receives response]
         |
         v
[Observability: Langfuse (LLM traces) + CloudWatch (infra)]
```

### Component Interaction

- **WhatsApp to Ingestion**: The BSP (Gupshup) receives messages via WhatsApp Cloud API and forwards them to our FastAPI service via webhook (HTTPS POST). Payload includes phone number, message text, media attachments (if any), timestamp, and message ID. We validate the webhook signature (HMAC-SHA256) before processing.
- **Ingestion to LangGraph**: The FastAPI webhook handler creates or resumes a LangGraph workflow instance keyed by phone number. LangGraph manages the conversation state (current node, accumulated context, pending API results) via its built-in checkpointing with Redis as the persistence backend. We return 200 OK to the BSP immediately (within 1s requirement) and process asynchronously.
- **Router Node (LLM call)**: Single LLM call with structured output (JSON schema enforced) performs intent classification, entity extraction, and sentiment detection simultaneously. We primarily used GPT-4o-mini — fast, cheap, and sufficient for 10-12 intent categories. Returns a structured response that the LangGraph conditional edge uses to route to the correct subgraph.
- **Resolution Subgraph**: A LangGraph subgraph executes the appropriate flow — EMI inquiry, balance check, foreclosure quote, etc. Each flow is a sequence of nodes: validate identity → fetch data from CRM/LOS → format response → send outbound. API calls to Salesforce and FinnOne are LangGraph tool nodes with built-in retry.
- **Agent Handoff Node**: If the router classifies intent as escalation-worthy (complaint, low confidence, negative/frustrated sentiment), this node creates a Salesforce case with full conversation transcript and routes to the Omnichannel agent queue.
- **Case Logging**: Every conversation (automated or escalated) creates or updates a Salesforce case. Automated resolutions create a closed case with resolution details. Escalations create an open case assigned to the agent queue. This is an RBI compliance requirement — every customer interaction must be logged and trackable.

### Infrastructure

- **Message ingestion**: FastAPI service on AWS (EC2 behind ALB). Stateless — all conversation state managed by LangGraph checkpointing in Redis.
- **LangGraph runtime**: Runs in-process with the FastAPI service. LangGraph checkpointer uses Redis (ElastiCache) for state persistence. No separate LangGraph server needed at our scale.
- **BSP**: Gupshup (managed service). Handles WhatsApp API compliance, template approval, media handling, delivery receipts.
- **Redis**: ElastiCache instance for LangGraph checkpointing + session TTLs. Low data volume — peak concurrent sessions around 500-1,000 during month-end.
- **LLM Provider**: Primarily OpenAI (GPT-4o-mini) via SDK with structured output mode. Anthropic (Haiku) as fallback provider.
- **Salesforce integration**: REST API with OAuth 2.0. Rate-limited by Salesforce org limits (about 100K API calls/day on our Enterprise edition).
- **FinnOne integration**: API calls to the loan management system for loan data. Read-only queries for EMI schedules, balances, payment status.

### Scalability and Availability

- **Operating scale**: Approximately 3,000-5,000 messages per day under normal conditions. Spikes to 8,000-10,000+ around month-end due date reminders and payment confirmation queries.
- **Current bottleneck**: Salesforce API rate limits. Each automated resolution requires 2-3 Salesforce API calls (fetch customer, fetch case history, create/update case). At 5,000 daily conversations, that's 10-15K API calls — well within limits. At 10x, it would approach the ceiling.
- **10x strategy**: Cache frequently accessed CRM data (customer profile, loan details) in Redis with short TTL (5-10 min). Batch case creation instead of per-message. For FinnOne, implement a read-through cache for loan data that changes infrequently (EMI schedule, tenure — refresh daily). LLM calls scale linearly with volume — GPT-4o-mini handles 10x without rate limit concerns at this volume.
- **Availability**: Circuit breaker on LLM provider (failover from OpenAI to Anthropic). If both LLM providers are down, degrade to button-only menu — [EMI Info] [Balance] [Statement] [Complaint] [Talk to Agent]. Buttons are deterministic, no LLM needed. Graceful degradation preserves core functionality. Circuit breaker on Salesforce/FinnOne — if either is down, the customer still gets acknowledgment; the CRM sync happens retroactively when APIs recover (LangGraph's durable execution preserves conversation state).
- **Latency budget**: Target under 5 seconds end-to-end. Typical breakdown: BSP webhook delivery ~200ms, ingestion + LangGraph state restore ~50ms, LLM structured output call 200-400ms, CRM/LOS API calls 500-1500ms, response formatting ~50ms, outbound via BSP 200-500ms.

---

## 3. LOW-LEVEL DESIGN (LLD)

### Internal Structure: LangGraph Workflow

The conversation is modeled as a LangGraph StateGraph. We adapted the StateGraph pattern for financial services conversation management — the core graph structure handles routing and flow execution, while we added compliance-specific nodes (identity verification, CRM audit logging) and NBFC-specific constraints (sentiment-based escalation overrides, separation between LLM routing and data access).

**Graph State Schema** (shared across all nodes):

```
WhatsAppState: {
  phone_number: str,
  customer_id: str | null,
  loan_ids: list[str] | null,
  message_history: list[{role: str, content: str, timestamp: timestamp}],
  current_intent: IntentResult | null,
  current_flow: str | null,
  flow_step: int,
  tool_results: dict | null,
  escalation_reason: str | null,
  verification_status: enum(unverified, verified, restricted),
  turn_count: int,
  sentiment: enum(positive, neutral, negative, frustrated) | null
}
```

**Node topology**:

```
START --> [identity_verification_node]
              |
              v
         [router_node] (LLM structured output)
              |
       +------+------+------+
       |      |      |      |
       v      v      v      v
  [emi_flow] [balance_flow] [foreclosure_flow] [escalation_node]
  [statement_flow] [payment_status_flow] [complaint_flow]
       |      |      |
       +------+------+
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

**Conditional edges** — the router node's output (intent + confidence + sentiment) drives routing:

- `intent in [emi_due_date, outstanding_balance, ...] AND confidence >= 0.8 AND sentiment != frustrated` → corresponding flow subgraph
- `intent in [emi_due_date, ...] AND confidence 0.5-0.8` → confirmation node ("It looks like you want to check your EMI. Is that right?") → flow subgraph on confirm / re-route on deny
- `confidence < 0.5 OR intent == speak_to_agent OR sentiment == frustrated` → escalation node
- `intent == complaint` → always escalation node regardless of confidence (compliance decision — complaints must always reach a human)

The 0.8 confidence threshold was calibrated empirically. We started at 0.9, but that triggered too many unnecessary confirmation steps for straightforward English queries. 0.8 gave us the right balance — high-confidence queries go straight through, moderate confidence gets a quick confirmation, low confidence escalates.

### Data Schemas

```
IntentResult: {
  intent: enum(
    emi_due_date, outstanding_balance, payment_status,
    loan_statement, foreclosure_quote, emi_receipt,
    complaint, speak_to_agent, greeting,
    payment_confirmation, document_upload, unknown
  ),
  confidence: float,
  entities: {
    loan_number: str | null,
    date_range: {start: date, end: date} | null,
    amount: float | null,
    product_type: str | null
  },
  sentiment: enum(positive, neutral, negative, frustrated),
  language_detected: str,
  requires_verification: bool
}

CRMCase: {
  case_id: str,
  customer_id: str,
  phone_number: str,
  channel: "whatsapp",
  intent: str,
  conversation_transcript: list[{role: str, content: str, timestamp: timestamp}],
  resolution: str | null,
  resolution_type: enum(automated, agent_assisted, escalated),
  llm_intent_confidence: float,
  satisfaction_rating: int | null,
  created_at: timestamp,
  closed_at: timestamp | null
}

ConversationCheckpoint: {
  thread_id: str,           // phone_number as thread key
  checkpoint_id: str,
  state: WhatsAppState,
  node_id: str,             // current node in LangGraph
  created_at: timestamp,
  ttl: int                  // 30 min idle, 24 hr absolute
}
```

### API Contracts

```
POST /webhook/whatsapp (BSP -> Ingestion)
Headers: X-Hub-Signature: <hmac_sha256>
Body: { BSP-specific payload with message details }
Response 200: { status: "received" }  // Must respond within 1s to avoid BSP retry

Internal LLM Call (Router Node -> LLM Provider):
System Prompt: "You are an intent classifier for an NBFC customer service WhatsApp bot.
  Classify the user message into one of these intents: [enum list].
  Extract entities: loan_number (format: AC + 10 digits), date_range, amount.
  Detect sentiment: positive, neutral, negative, frustrated.
  Respond ONLY with the JSON schema provided. No explanation."
Response Schema (enforced via structured output):
{
  "intent": str,
  "confidence": float,
  "entities": { "loan_number": str|null, "date_range": obj|null, "amount": float|null },
  "sentiment": str,
  "language_detected": str,
  "requires_verification": bool
}

POST /v1/send-message (Internal -> BSP)
Headers: Authorization: Bearer <bsp_token>
Body: {
  phone_number: str,
  message_type: enum(text, template, interactive),
  text: str | null,
  interactive: {
    type: enum(button, list),
    body: str,
    buttons: list[{id: str, title: str}] | null
  } | null
}
Response 200: { message_id: str, status: "sent" }

GET /v1/conversation/{phone_number}/status (Dashboard / Agent Console)
Response 200: {
  graph_state: WhatsAppState,
  current_node: str,
  recent_messages: list[{role, content, timestamp}],
  customer_profile: { name, customer_id, active_loans: list }
}
```

### Design Patterns Applied

- **Graph-based Workflow (LangGraph StateGraph)** for conversation management: Each conversation is a stateful graph execution. Nodes are functional steps (classify, fetch data, format response). Conditional edges route based on LLM output. LangGraph's built-in checkpointing with Redis handles state persistence, resume-after-interruption, and TTL-based cleanup. We adapted this pattern from reference implementations and the LangGraph documentation, then extended it significantly for our compliance context — adding identity verification as a mandatory entry node, Salesforce case logging as an exit node, and sentiment-based override routing that bypasses normal confidence thresholds.
- **Structured Output Pattern** for intent + NER: LLM call with JSON schema enforcement (OpenAI's `response_format`) guarantees the response is parseable. No regex post-processing, no JSON repair. The schema is the contract between the LLM and the routing logic. This was the single most impactful architectural decision — it collapsed 4 separate pipeline stages into one API call.
- **Adapter Pattern** for CRM/LOS integration: Unified internal interface for customer data access. Concrete adapters for Salesforce REST API and FinnOne API. Registered as LangGraph tool nodes — the graph calls them like any other node, with built-in retry and error handling.
- **Circuit Breaker** on external dependencies: LLM provider, Salesforce, FinnOne each wrapped with circuit breakers. LangGraph's durable execution means a mid-conversation API failure does not lose the conversation state — the graph pauses and resumes when the dependency recovers.
- **Observer Pattern** for analytics: Every node execution emits traces to Langfuse (LLM calls with full request/response, tool calls, latency, token usage) and CloudWatch (infrastructure metrics, error rates).

### Error Handling and Failure Modes

|Failure|Impact|Mitigation|
|---|---|---|
|LLM provider timeout/5xx|Cannot classify intent. Conversation stuck.|Circuit breaker with failover: OpenAI → Anthropic. If both down, send button-based menu: [EMI Info] [Balance] [Statement] [Talk to Agent]. Buttons are deterministic — no LLM needed. LangGraph graph pauses at router node, resumes when LLM recovers.|
|FinnOne API returns stale or inconsistent data|Borrower gets wrong EMI amount or due date. Trust-destroying.|Cross-validate critical fields (EMI amount, due date) against Salesforce records if both systems store them. If discrepancy detected, do not serve the data — escalate to agent with "data discrepancy" flag.|
|LLM returns hallucinated intent|Wrong flow triggered, borrower gets irrelevant response.|Structured output mode guarantees valid JSON schema. Intent enum is enforced — LLM cannot invent new intents. Confidence threshold (0.8) ensures uncertain classifications get confirmation. Sentiment override: frustrated users always escalate regardless of classified intent.|
|Redis/checkpoint failure|Cannot restore conversation state. Multi-turn flow breaks.|Fallback: treat as new conversation. User may need to re-state their query. Log checkpoint failures for investigation. In practice, this happened rarely — ElastiCache was stable.|
|BSP webhook delivery failure|Message never reaches our service.|BSP retries (Gupshup retries 3 times with backoff). If all retries fail, message is lost — user would re-send. We monitored webhook success rates in CloudWatch.|

### Key Design Decisions

- **Chose LLM structured output over fine-tuned distilbert for intent classification**: We had zero labeled training data at launch. A fine-tuned classifier needs 5-10K labeled examples per intent, a training pipeline, retraining when intents change, and separate handling for Hinglish. The LLM handles all of this in one call — intent, entities, sentiment, language — across English, Hindi, Hinglish, typos, and abbreviations. Adding a new intent is a prompt edit, not a retrain cycle. Cost: approximately $0.03-0.05/day at our volume. Latency: 200-400ms, well within the WhatsApp budget. The trade-off is external API dependency, which we mitigate with provider failover and button-based fallback.
    
- **Chose LangGraph over custom state machine for conversation flows**: We initially prototyped with a simple if-else state tracker in Redis. It worked for 2-3 intents but became unmaintainable as we added more flows. LangGraph gave us checkpointed persistence (conversations survive server restarts), conditional routing as declarative graph edges, built-in retry on node failures, and graph introspection for debugging. The main trade-off is framework dependency — but at our scale, the development speed gain was worth it.
    
- **Chose structured conversation flows with LLM entry point over fully free-form LLM chat**: The LLM handles understanding (intent + NER at the entry point) but does NOT generate financial data responses. Loan amounts, due dates, balances come from FinnOne/Salesforce API calls — deterministic, auditable, zero hallucination risk. The LLM generates only two types of text: confirmation prompts ("You want to check EMI for loan AC2024001234?") and empathetic escalation messages ("I understand your concern. Connecting you with an agent."). For compliance-sensitive NBFC operations, this separation is non-negotiable.
    

---

## 4. AI/ML PROJECT ARCHITECTURE

### Pipeline Design

- **No custom model training**: This is an LLM-native system. Intelligence comes from prompt engineering + structured output schema + LangGraph workflow design, not custom-trained models. This was a deliberate choice — we needed to launch fast with zero training data, and the LLM approach let us go from design to production significantly faster than a train-from-scratch approach would have.
- **Inference pipeline**: Inbound WhatsApp message → LangGraph state restore from Redis checkpoint → Router node (LLM structured output: intent + NER + sentiment) → Conditional edge routing → Flow subgraph execution (API tool calls to Salesforce/FinnOne) → Response formatting → CRM case sync → Outbound message.
- **Prompt versioning**: The router node's system prompt (intent definitions, entity schemas, few-shot examples) is version-controlled in Git. Changes deployed via shadow mode — new prompt runs in parallel on a sample of traffic, outputs logged to Langfuse but not served to users, evaluated against our labeled message set before promotion. We went through approximately 5-6 major prompt iterations over the system's lifetime.
- **Flow definitions as config**: LangGraph subgraphs for each intent are defined in code but parameterized via config (which API endpoints to call, which fields to return, response templates). Adding a new flow is a new subgraph + config entry, no changes to the orchestration layer.

### Model Strategy

- **LLM for intent + NER + sentiment (Router Node)**: Primarily GPT-4o-mini. Chosen for speed (~200-400ms structured output), zero training data requirement, native multilingual handling, and single-call multi-extraction (intent + entities + sentiment + language). Cost: approximately $0.15/1M input tokens. At ~4,000 LLM calls/day (about 80% of messages — rest are button clicks or mid-flow continuations), daily cost was roughly $0.03-0.05. Monthly LLM spend under $2.
- **No model tiering needed**: Unlike more complex GenAI systems where query complexity varies, WhatsApp intent classification is uniformly simple — classify a short message into one of 12 categories. A single cheap, fast model handles everything.
- **Provider strategy**: OpenAI primary, Anthropic (Haiku) as fallback. We chose OpenAI as primary because their structured output mode (`response_format: json_schema`) was more mature at the time of implementation. Anthropic's tool-use-based structured output works differently (schema via tool definition), so the failover required maintaining compatible prompts for both providers.

### LLM Structured Output Schema

The single LLM call that replaces the traditional intent/NER/sentiment pipeline:

```
System Prompt:
"You are a customer service intent classifier for Aeon Credit Service,
an NBFC in India. Classify the customer's WhatsApp message.

INTENTS (pick exactly one):
- emi_due_date: Customer wants to know when their next EMI payment is due
- outstanding_balance: Customer wants to know remaining loan balance
- payment_status: Customer asking if a specific payment was received/processed
- loan_statement: Customer wants a loan account statement
- foreclosure_quote: Customer wants to know the amount to close the loan early
- emi_receipt: Customer wants a receipt for a past payment
- complaint: Customer is reporting a problem or expressing dissatisfaction
- speak_to_agent: Customer explicitly wants to talk to a human
- greeting: Simple hello/hi with no specific query
- payment_confirmation: Customer informing about a payment they just made
- document_upload: Customer sending a document (payment screenshot, ID, etc.)
- unknown: Message does not fit any category

CONFIDENCE: Float 0.0-1.0. High (>0.8) = clear intent. Medium (0.5-0.8) = probable.
Low (<0.5) = unclear.

ENTITY EXTRACTION:
- loan_number: Format 'AC' followed by 10 digits. Extract if present.
- date_range: Any date references (month, quarter, specific dates)
- amount: Any monetary amount mentioned

SENTIMENT: Detect from message tone:
- positive: Happy, thankful
- neutral: Normal inquiry
- negative: Unhappy but measured
- frustrated: Angry, repeated messages, ALL CAPS, threatening language

LANGUAGE: Detect primary language (english, hindi, hinglish, other)

REQUIRES_VERIFICATION: true if the query needs loan-specific data to answer

Indian NBFC customers frequently message in Hinglish (Hindi-English mix).
Treat Hinglish messages with the same confidence as English messages
when the intent is clear.

Few-shot examples:
User: 'mera EMI kab hai' -> {intent: 'emi_due_date', confidence: 0.95,
  entities: {}, sentiment: 'neutral', language: 'hinglish',
  requires_verification: true}
User: 'AC2024001234 ka balance batao' -> {intent: 'outstanding_balance',
  confidence: 0.95, entities: {loan_number: 'AC2024001234'},
  sentiment: 'neutral', language: 'hinglish', requires_verification: true}
User: 'I paid 5000 yesterday but still showing pending!!!'
  -> {intent: 'payment_status', confidence: 0.90,
  entities: {amount: 5000}, sentiment: 'frustrated',
  language: 'english', requires_verification: true}
User: 'hi' -> {intent: 'greeting', confidence: 0.99,
  entities: {}, sentiment: 'neutral', language: 'english',
  requires_verification: false}
User: 'loan band karna hai kitna dena hoga'
  -> {intent: 'foreclosure_quote', confidence: 0.92,
  entities: {}, sentiment: 'neutral', language: 'hinglish',
  requires_verification: true}
"
```

The LLM sees this prompt + the user message and returns a guaranteed-valid JSON object. LangGraph's conditional edge reads the `intent`, `confidence`, and `sentiment` fields to route.

**Why this works for Hinglish/multilingual**: The LLM has seen Hindi, Hinglish, and transliterated text in pre-training. Messages like "mera EMI kab hai", "EMI kb h", "EMI kab hoga", and "when is my EMI" all map to the same intent without preprocessing. No keyword dictionaries, no transliteration tables, no fuzzy matching. The few-shot examples anchor the LLM's behavior for our domain-specific vocabulary (loan numbers, EMI terminology).

**Prompt evolution**: This prompt went through 5-6 iterations. The initial version had 8 English and 2 Hinglish few-shot examples, which caused low confidence scores on Hinglish messages (see War Story 1). After rebalancing to 5+5, Hinglish accuracy improved significantly. We also added the explicit instruction about treating Hinglish equally — that single instruction line measurably improved confidence scores. Later iterations added examples for edge cases we caught in production: voice-to-text artifacts, abbreviated messages, and payment screenshots described in text.

### Experimentation Framework

- **Evaluation metrics** (measured regularly):
    - **Intent accuracy**: Weekly sample of ~200 messages, manually labeled and compared against LLM output. Accuracy stabilized around 90-93% across languages after prompt tuning. English was higher (~94-96%), Hinglish slightly lower (~88-92%).
    - **Entity extraction accuracy**: Loan number exact match was approximately 95%+ (the AC + 10 digit format is distinctive). Amount extraction occasionally struggled with ambiguous phrasing.
    - **Self-service resolution rate**: Approximately 60-65% of conversations resolved without agent escalation.
    - **Average resolution time**: Under 30 seconds for automated flows; approximately 3-5 minutes for agent pickup during business hours.
    - **Customer satisfaction**: Post-conversation survey ("Rate 1-5") averaged around 3.5-4.0.
    - **Escalation rate by intent**: Complaints always escalated (by design). Foreclosure quotes had the highest unintentional escalation rate (~15-20%) because they often involve frustrated customers.
- **Prompt evaluation**: New prompt versions tested via shadow mode — run in parallel on a sample of traffic, logged to Langfuse, compared against the production prompt on the same messages. Promoted only if accuracy improved or held steady on our labeled set.
- **Tracking**: Langfuse for LLM-specific traces (intent confidence distributions, token usage, latency per call, structured output compliance rate). CloudWatch for infrastructure (webhook success rate, API latency, error rates).

### Data Strategy

- **No training data needed upfront**: LLM structured output works with few-shot examples in the prompt. This was a major advantage — we launched without a labeled corpus and built our evaluation set organically from production traffic.
- **Continuous improvement loop**: Misclassified messages (identified via "Was this helpful? No" responses + agent corrections during escalation) were reviewed and the most instructive failures were added as few-shot examples. We did a prompt review roughly monthly — adding 2-3 new examples per cycle based on real misclassifications.
- **Language handling**: Handled natively by the LLM. No transliteration pipeline, no keyword expansion. Hinglish, pure Hindi, English, typos, voice-to-text artifacts — all handled in the same single LLM call.
- **Privacy**: Phone numbers are PII. Conversation content is logged in Salesforce (CRM is the system of record). For LLM calls, we scrubbed Aadhaar numbers from message text before sending to the LLM provider. Loan numbers are internal identifiers, not customer PII.
- **Prompt injection defense**: The structured output schema constrains the LLM to output ONLY the defined JSON structure. Even if a user sends adversarial messages, the LLM's response is forced into the intent/entity/sentiment schema. The LLM never has direct access to customer data — it only classifies the message. Actual loan data lives in FinnOne/Salesforce and is accessed by separate tool nodes.

---

## 5. CORE LOGIC AND ALGORITHMS

### Algorithm 1: LLM-Powered Intent Classification + NER via Structured Output

**What it does**: A single LLM call classifies the user's WhatsApp message into one of 12 intent categories, extracts structured entities (loan number, amounts, dates), detects sentiment, and identifies language — all returned as a guaranteed-valid JSON object.

**Why we chose this over alternatives**: We had no labeled corpus at launch — zero training examples. A fine-tuned distilbert would need 5-10K labeled examples per intent, plus a separate NER pipeline, plus a sentiment model, plus a transliteration layer for Hinglish. That's 4 pipeline stages, each a maintenance burden and failure point. The LLM collapses all four into one call, handles multilingual input natively, and needs only 5-10 few-shot examples that we wrote in an afternoon.

**Step-by-step logic**:

1. Receive WhatsApp message text + session context (is user mid-flow? previous intent?)
2. **Short-circuit check**: If the message is a button/list reply (structured WhatsApp interactive response), map directly to intent without LLM call. Button ID "emi_details" → intent `emi_due_date`, confidence 1.0. Zero latency, zero cost. This handles roughly 20% of messages.
3. **Session context check**: If the user is mid-flow in a LangGraph subgraph (e.g., foreclosure quote flow, step 3 of 5), the expected input type is known. If the message matches (e.g., user is selecting a loan from a list), continue the flow without an LLM call. If it doesn't match (user appears to be changing topic), proceed to LLM classification.
4. **LLM structured output call**: Send the message + system prompt to GPT-4o-mini with `response_format: { type: "json_schema", schema: IntentResultSchema }`. The LLM returns a JSON object conforming to the schema. No parsing errors possible — the schema is enforced by the API.
5. **Confidence routing** (implemented as LangGraph conditional edge):
    - Confidence >= 0.8 AND sentiment != frustrated: route to automated flow subgraph.
    - Confidence 0.5-0.8: route to confirmation node.
    - Confidence < 0.5: route to escalation node.
    - Sentiment == frustrated OR intent == complaint: always escalation, regardless of confidence.
6. **Entity pass-through**: Extracted entities are written to LangGraph state and passed to the flow subgraph as API parameters.
7. **Logging**: Message, full LLM response JSON, routing decision, latency, token count → Langfuse.

**Complexity**: O(1) per message — single LLM API call. Latency: 200-400ms for GPT-4o-mini structured output. Token usage: approximately 100-150 tokens per classification.

**Edge cases we handled**:

- **Multi-intent messages**: "Tell me my EMI date and also I want a statement." The schema forces a single intent. LLM picks the primary intent. After resolution, the response includes "Is there anything else?" which triggers the second intent on the next turn.
- **Adversarial input / prompt injection**: Structured output mode constrains the response to the JSON schema — the LLM cannot output free-form text. The response will always be a valid IntentResult JSON. The LLM never has access to customer data.
- **LLM provider outage**: Short-circuit to button-based menu. Buttons are deterministic — no LLM needed. Users lose free-text understanding but retain core functionality.
- **Ambiguous abbreviations**: "st" could be "statement" or "status." The LLM resolves via context — if the user previously asked about a payment, it leans toward payment_status. On cold start, it defaults to the more common interpretation with moderate confidence (~0.6-0.7), triggering a confirmation step.

**Trade-off**: LLM classification depends on an external API. If OpenAI has a global outage, intent classification fails. Mitigated by provider failover (OpenAI → Anthropic) and button-based fallback that requires zero AI. We traded independence for dramatically simpler architecture and zero training data requirement.

---

### Algorithm 2: LangGraph Stateful Conversation Flow Execution

**What it does**: Manages multi-turn conversation flows as LangGraph StateGraph instances, with checkpointed state persistence, conditional routing, tool-calling nodes for CRM/LOS integration, and durable execution across interruptions.

**Why we needed stateful orchestration**: NBFC customer queries are rarely single-turn. A foreclosure quote requires: verify identity → identify loan → fetch foreclosure amount from LOS → present amount + terms → confirm or decline → log case. That's 4-6 turns. Without stateful orchestration, multi-turn tracking becomes ad-hoc conditional logic that's impossible to debug or extend.

We initially prototyped with a simple Redis-backed state dict. It worked for the first 2-3 intents but became a maze of if-else statements as we added more flows. LangGraph gave us graph-based state management with automatic checkpointing (conversations survive server restarts), conditional routing as declarative edges, built-in retry on node failures, and graph visualization for debugging.

**Step-by-step logic**:

1. Receive inbound message + phone number
2. **State restore**: LangGraph loads the checkpoint for this phone_number (thread_id). If none exists, create new graph state. Checkpoint is in Redis with TTL (30 min idle, 24 hr absolute).
3. **Graph invocation**: Call `graph.invoke(state, config={"configurable": {"thread_id": phone_number}})`. LangGraph resumes from the last checkpointed node.
4. **Node execution**: Each node reads from the shared WhatsAppState, performs its action (LLM call, API call, message formatting), returns updated state fields. LangGraph checkpoints after each node.
5. **Conditional routing**: After the router node, LangGraph evaluates conditional edges based on intent, confidence, and sentiment.
6. **Flow subgraphs**: Each intent maps to a subgraph. Example — EMI inquiry:
    - Node 1: Check verification_status. If unverified, route to identity verification.
    - Node 2: If loan_number in entities, proceed. If not, ask "Which loan?" with button list from CRM.
    - Node 3: Call FinnOne API: `get_emi_details(loan_id)`.
    - Node 4: Format response: "Your next EMI of Rs {amount} for loan {loan_id} is due on {date}."
    - Node 5: Send outbound + "Was this helpful? [Yes] [No] [Other query]"
    - Node 6: CRM case sync (async).
7. **Interruption handling**: If the user sends a message that triggers a different intent mid-flow, the router re-classifies. If the new intent has high confidence, LangGraph transitions to the new flow. Previous flow state is preserved — the closing message includes "Would you like to continue with [previous query]?"
8. **Timeout**: Checkpoint TTL handles cleanup. 30 minutes idle → checkpoint expires. Next message starts fresh.

**Edge cases we handled**:

- **User sends just "Hi"**: Intent: greeting. No flow triggered. Router node responds with welcome message + menu buttons. Graph terminates at outbound node.
- **Multiple active loans**: Flow subgraph detects multiple loans, presents button list. User selection stored in state, subsequent nodes use it.
- **Server restart mid-conversation**: LangGraph checkpoint in Redis survives. On next message, graph resumes from exact node. User experiences no interruption.
- **Long-running API call**: FastAPI webhook immediately returns 200 OK to BSP. LangGraph runs asynchronously. If processing exceeds 10s, send a "working on it" interim message.

**Trade-off**: LangGraph adds a framework dependency vs. a custom state machine. We traded full control for significantly reduced boilerplate — checkpointing, retry, state serialization all handled by the framework. The graph model also makes flows visualizable, which helped enormously when onboarding team members and debugging conversation paths.

---

### Algorithm 3: CRM Synchronization and Agent Handoff Protocol

**What it does**: Ensures every WhatsApp interaction is reflected in Salesforce as a case with full context, and that agent handoffs carry complete conversation history so agents never ask the customer to repeat information.

**Why this matters**: Under RBI regulation, every customer interaction at an NBFC must be logged and trackable. A customer who queries via WhatsApp and later calls the contact center should find the agent already aware of the WhatsApp conversation. Without CRM sync, the WhatsApp channel becomes a silo.

**Step-by-step logic**:

1. **On conversation start** (first message from a new session):
    - Lookup customer in Salesforce by phone number.
    - If found: attach customer_id to LangGraph state. Check for open cases — if an open case exists on the same topic, link the conversation to it.
    - If not found: create session without customer_id. Route to identity verification node.
2. **On automated resolution** (flow subgraph completes):
    - CRM sync node creates Salesforce case: type = "WhatsApp Inquiry", status = "Closed - Automated", subject = intent description, description = full conversation transcript from LangGraph state, including LLM intent confidence and tool call results.
3. **On agent escalation**:
    - Escalation node creates Salesforce case: type = "WhatsApp Inquiry", status = "Open - Escalated", subject = intent + "Escalated: [reason]".
    - Push to Salesforce Omnichannel routing queue. Agent console displays: full conversation transcript, LLM-detected intent + confidence, customer profile (name, loan details, payment history), extracted entities.
    - Agent responds via console. Response routed back through outbound node to WhatsApp.
4. **Proactive follow-up**: If an escalated case is not picked up within approximately 15 minutes, send a template message: "We've received your query. Reference: [case_id]. An agent will respond shortly."

**Edge cases**:

- **Salesforce down during conversation**: CRM sync is the last node before outbound. If it fails, the customer still gets their response — CRM sync failure does not block the user-facing flow. Retry with exponential backoff. Case created retroactively.
- **Duplicate cases**: Deduplication window: one case per (customer_id, intent, 30-minute window).
- **24-hour WhatsApp window**: System tracks time since last customer message. If more than 20 hours elapsed before agent responds, use pre-approved template message instead of session message. (See War Story 3 for how we discovered and solved this.)

**Trade-off**: Real-time CRM sync for escalations (agent needs current data) vs. batch sync for automated resolutions (case created at conversation end, reducing API calls). Hybrid approach balances CRM freshness with API budget.

---

## 6. INTERVIEW ATTACK SURFACE

### Question 1 — Design

**"Why LLM-based intent classification instead of a fine-tuned classifier or rule-based NLP?"**

Three reasons. First, zero training data — we had no labeled corpus at launch. A fine-tuned distilbert needs 5-10K labeled examples per intent. We had zero. The LLM worked with 5-10 few-shot examples in the prompt, which we wrote in an afternoon. Second, multilingual handling — about 40-45% of our messages were Hinglish. A classifier would need a transliteration pipeline, separate Hindi keyword dictionaries, and fuzzy matching for typos. The LLM handles "mera EMI kab hai", "EMI kb h", and "when is my EMI" identically — no preprocessing. Third, single-call simplicity — one API call replaces four pipeline stages. Cost was under $2/month at our volume. The trade-off is external API dependency, which we mitigated with provider failover and a button-based fallback.

### Question 2 — Scale

**"What happens when WhatsApp message volume spikes 10x during month-end?"**

We saw 2-3x spikes during month-end organically. The LLM call scales linearly — GPT-4o-mini handles 10x without rate limit issues at our volume. The real bottleneck is Salesforce API limits. Our mitigation: cache frequently accessed CRM data (customer profile, loan details) in Redis with 5-minute TTL. On due-date days, 80% of queries are "what's my EMI" — answers change at most daily. Cache converts 10x message volume into roughly 1.5x API call volume. For case creation, we batch during spikes — queue in Redis, flush every 5 minutes. LangGraph's checkpointing handles concurrent conversations without issues — each conversation is an independent graph instance keyed by phone number.

### Question 3 — Failure

**"What if the LLM classifies a complaint as a balance inquiry and the customer gets an automated response instead of an agent?"**

Two safety nets. First, sentiment override: the structured output includes sentiment detection. If the LLM detects "frustrated" or "negative" sentiment — even if it misclassifies the intent — the routing logic always escalates to an agent. A frustrated customer should never interact with a bot. Second, every automated response ends with "Was this helpful? [Yes] [No] [Talk to agent]". "No" or "Talk to agent" triggers immediate escalation. The misclassification costs one bad turn, not the entire conversation. We tracked misclassification rates per intent weekly via Langfuse — when complaint-intent accuracy dipped, we added targeted few-shot examples.

### Question 4 — ML-Specific

**"How do you evaluate LLM intent accuracy without a training/test set?"**

Three methods. First, weekly human review: I sampled about 200 messages, manually labeled them, compared against LLM output. This was our ground truth — accuracy was around 90-93% across languages. Second, implicit feedback: "Was this helpful? No" rate per intent. When EMI inquiry "No" rate spiked, we investigated within 48 hours — sometimes the intent was correct but the API returned stale data, sometimes it was a genuine misclassification. Third, agent correction data: when a conversation escalated, the agent logged the actual intent. Mismatches between LLM classification and agent labels gave us labeled misclassification data. These corrections fed back into the few-shot examples — the improvement cycle was prompt editing, not model retraining.

### Question 5 — Trade-off

**"What would you do differently if you rebuilt this today?"**

Two things. First, proactive outreach flows from day one using WhatsApp template messages — "Your EMI of Rs 5,000 is due tomorrow. Reply PAY to confirm or HELP for options." This converts the chatbot from a reactive support channel into a proactive collections and engagement channel. We had the template infrastructure but deprioritized the trigger engine. Second, voice note handling — a significant number of users send voice messages in Hindi, and we had to respond with "Sorry, I can only read text messages." Integrating a speech-to-text step (Whisper or similar) before the LLM router would capture those users.

---

## 7. TROUBLESHOOTING WAR STORIES (STAR FORMAT)

---

### Scenario 1: LLM Structured Output Returning Low Confidence on Hinglish Patterns

**Situation**: After deploying the LLM-based router, intent accuracy on English messages was around 95% but Hinglish messages like "loan band karna hai kitna dena hoga" (I want to close the loan, how much do I need to pay) were returning confidence scores of 0.5-0.6, triggering unnecessary confirmation steps for roughly 30% of Hinglish queries. The LLM was classifying correctly (foreclosure_quote) but was uncertain — the confidence was low even when the intent was right.

**Task**: Improve LLM confidence on Hinglish inputs without degrading English accuracy.

**Action**:

1. Analyzed Langfuse traces: about 85% of low-confidence classifications were correct but lacked confidence. The LLM "knew" the right intent but hedged on the score.
2. Root cause: the initial prompt had 8 English and 2 Hinglish few-shot examples. The LLM had weak anchoring for Hinglish patterns in our domain.
3. Fix: Rebalanced few-shot examples to 5 English + 5 Hinglish, covering the most common Hinglish phrasings for each top-5 intent:
    - "mera EMI kab hai" (emi_due_date)
    - "loan ka balance batao" (outstanding_balance)
    - "paisa kata ki nahi" (payment_status)
    - "loan band karna hai" (foreclosure_quote)
    - "statement bhejo" (loan_statement)
4. Added an explicit prompt instruction: "Indian NBFC customers frequently message in Hinglish. Treat Hinglish messages with the same confidence as English messages when the intent is clear."
5. Tested on a shadow sample of around 300 Hinglish messages from the previous week before promoting.

**Result**: Hinglish confidence scores jumped from approximately 0.6 average to approximately 0.88 average. Unnecessary confirmation steps dropped from about 30% to about 8% of Hinglish queries. English accuracy unchanged. Total fix: about 30 minutes of prompt editing, zero code changes, zero retraining. This was the clearest demonstration of why we chose the LLM approach — a comparable fix with a fine-tuned classifier would have required collecting hundreds of Hinglish labeled examples and retraining.

---

### Scenario 2: Customer Identity Verification Bypass Attempt

**Situation**: A user sent a message with a valid loan number (obtained from a payment receipt found/shared) and requested loan details. The system verified the phone number against the CRM — no match. It then asked for the registered date of birth as a second factor. The user provided the correct DOB (potentially obtained through social engineering). The system would have disclosed loan details to a potentially unauthorized person.

**Task**: Strengthen identity verification without making the flow so cumbersome that legitimate customers abandon.

**Action**:

1. Analyzed the verification flow: phone number match (factor 1) + DOB (factor 2) was the initial design. DOB is a weak factor — it's commonly known, appears on various documents, and is easily socially engineered.
2. Redesigned to a three-tier verification model (implemented as LangGraph identity verification subgraph):
    - **Tier 1 (automatic)**: Phone number matches CRM registered mobile. No further verification needed. This is the happy path for the vast majority of users who message from their registered number.
    - **Tier 2 (lightweight verification)**: Phone number doesn't match. System asks for loan number + last 4 digits of registered phone number (not DOB). This information is only known to the borrower and doesn't appear on public documents.
    - **Tier 3 (restricted)**: If Tier 2 fails, user gets only generic information (branch locator, general FAQs, complaint registration). No loan-specific data disclosed. Directed to call the contact center with ID proof.
3. Rate-limited verification attempts per phone number to 3 per 24 hours to prevent brute-force attacks.
4. All verification failures logged as security events in Salesforce for the fraud team to review.

**Result**: Eliminated the DOB-based bypass vector. Legitimate customers on their registered number experienced no additional friction. Zero loan data disclosure incidents post-fix.

---

### Scenario 3: WhatsApp 24-Hour Window Causing Dropped Agent Responses

**Situation**: Customers messaged the bot outside business hours (10 PM-8 AM). The bot classified the intent, determined it needed agent escalation, and queued the case. Agent picked it up at 9 AM the next morning — but by then the customer had often moved on. Worse: if more than 24 hours elapsed, WhatsApp blocked the session message entirely, and the agent's response couldn't be delivered.

**Task**: Handle after-hours escalations without making customers wait until business hours.

**Action**:

1. Implemented a **time-aware conditional edge** in the LangGraph escalation subgraph:
    - During business hours (8 AM - 8 PM): escalate to live agent queue.
    - After hours: acknowledge immediately with a template message: "Thanks for reaching out. Our team will respond by [next business day 10 AM]. Your reference: [case_id]."
    - LangGraph state stores the escalation timestamp. The graph pauses at the escalation node with a checkpoint.
2. **Priority queue for after-hours cases**: Cases escalated after hours flagged as "overnight" and placed at the top of the agent queue for the morning shift.
3. **Proactive re-engagement via template message**: When the agent picks up an after-hours case, the system checks elapsed time. If more than 20 hours since customer's last message, the agent response is sent via a pre-approved WhatsApp template message (which works outside the 24-hour window): "Hi [name], regarding your query about [intent]: [agent_response]. Reply to continue."
4. **Expanded automated resolution**: Self-service coverage expanded so that more after-hours queries resolve automatically without needing an agent at all.

**Result**: After-hours customer experience improved significantly. Overnight case resolution dropped to first-thing-next-morning with proactive template re-engagement. The 24-hour window issue was eliminated by the template message fallback. This also pushed us to expand automated resolution — the fewer queries that need agents, the less the after-hours gap matters.

---

## 8. NEXT ACTIONS MENU

1. "Drill deeper into [any component]" — LangGraph graph topology details, LLM structured output prompt engineering, Salesforce Omnichannel handoff, identity verification subgraph, Langfuse observability setup
2. "Mock interview round on this line item" — 5 rapid-fire questions, you answer, critique follows
3. "Show me the code for [specific logic]" — LangGraph workflow definition, router node with structured output, CRM sync tool node, webhook handler, conversation flow subgraph
4. "Next line item" — proceed to next CV line item