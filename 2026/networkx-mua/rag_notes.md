# RAG Knowledge Reference: Interview Prep Guide

## 1. RAG Architecture Spectrum

### Naive RAG (Basic)
Load docs -> fixed-size chunking -> embed -> vector store -> retrieve top-k -> LLM generates answer.
Problems: poor chunk boundaries, no relevance filtering, hallucination on low-quality retrieval.

### Advanced RAG
Improves each stage of naive RAG:
- **Pre-retrieval**: better chunking, metadata enrichment, query transformation
- **Retrieval**: hybrid search, re-ranking
- **Post-retrieval**: relevance filtering, compression, citation grounding

### Modular/Agentic RAG
Agent decides WHEN to retrieve, WHAT to retrieve, and WHETHER retrieved content is good enough. Can do multi-step retrieval, combine with structured data (knowledge graphs), and self-correct.

---

## 2. Chunking Strategies

### Fixed-size chunking
Split every N tokens/characters. Simple but dumb. Breaks mid-sentence, mid-paragraph.
Use case: when you need a quick baseline.

### Recursive character splitting (LangChain default)
Try splitting by paragraphs first, then sentences, then words. Respects natural boundaries.
Use case: general purpose, works well for most documents.

### Semantic chunking
Use embeddings to detect topic shifts. Split where cosine similarity between consecutive sentences drops.
Use case: documents with mixed topics, no clear structure.

### Document-structure-based chunking
Split by headers, sections, pages. Preserves document hierarchy.
Use case: structured documents (contracts, SOPs, policies) -- our use case.

### Parent-child (small-to-big) chunking
Embed small chunks (sentences) for precision matching. At retrieval time, return the parent chunk (full paragraph/section) for context.
Use case: when you need precise matching but full context for generation.

### Agentic chunking
LLM decides chunk boundaries based on content meaning.
Use case: complex documents where no heuristic works well. Expensive.

### Key parameters
- Chunk size: 200-1000 tokens typical. Smaller = more precise retrieval, less context. Larger = more context, noisier retrieval.
- Chunk overlap: 10-20% overlap between adjacent chunks prevents losing context at boundaries.

---

## 3. Embedding Models

### What they do
Convert text to dense vectors (768-1536 dimensions). Similar meaning = similar vectors.

### Popular models
- **OpenAI text-embedding-3-small**: 1536 dims, good quality, paid API
- **OpenAI text-embedding-3-large**: 3072 dims, best quality from OpenAI
- **Sentence-transformers (all-MiniLM-L6-v2)**: 384 dims, fast, free, runs locally
- **BGE (BAAI/bge-large-en-v1.5)**: 1024 dims, strong open-source option
- **Nomic embed**: 768 dims, works with Ollama locally
- **Cohere embed-v3**: strong multilingual, paid API

### Selection criteria
- Local vs API: for prototype/privacy, use local (sentence-transformers or nomic)
- Dimension size: higher dims = more expressive but more storage/compute
- Domain: general-purpose models work for most cases. Fine-tune only if domain is very specialized.

---

## 4. Vector Databases

### What they do
Store embeddings and support fast approximate nearest neighbor (ANN) search.

### Options
- **Qdrant**: Rust-based, fast, supports filtering, runs in Docker. Our choice.
- **ChromaDB**: Python-native, simple, good for prototypes. In-memory or persistent.
- **Pinecone**: Managed cloud, no infra management. Paid.
- **Weaviate**: GraphQL API, supports hybrid search natively.
- **FAISS**: Facebook's library, not a full DB. Very fast but no persistence by default.
- **Milvus**: Distributed, scalable, open-source.
- **pgvector**: PostgreSQL extension. Good when you already use Postgres.

### Why Qdrant for us
Docker setup, filtering by metadata (node type, document type), payload storage, hybrid search support.

---

## 5. Retrieval Strategies

### Dense retrieval (vector search)
Embed query, find nearest vectors by cosine similarity. Good for semantic meaning.
Weakness: misses exact keyword matches ("SLA clause 4.2").

### Sparse retrieval (BM25/keyword)
Traditional keyword matching with TF-IDF weighting. Good for exact terms.
Weakness: misses semantic similarity ("delivery delay" vs "shipment postponement").

### Hybrid search (dense + sparse)
Combine both with weighted fusion. Best of both worlds.
Implementation: Reciprocal Rank Fusion (RRF) merges ranked lists from both methods.
Formula: RRF_score = sum(1 / (k + rank_i)) across all retrievers.

### Re-ranking
Two-stage: fast retrieval (top-50) then cross-encoder re-ranks to top-5.
Cross-encoder sees query AND document together (not separately like bi-encoder).
Models: Cohere rerank, cross-encoder/ms-marco-MiniLM-L-6-v2 (free).
Much more accurate but slower -- that's why it's a second stage.

### Multi-query retrieval
LLM generates multiple query variations, retrieves for each, merges results.
Example: "Why is the port congested?" generates:
- "port congestion causes"
- "factors affecting port throughput"
- "supply chain port delays"

### Maximal Marginal Relevance (MMR)
Balances relevance with diversity. Prevents returning 5 chunks that all say the same thing.

---

## 6. Advanced RAG Patterns

### CRAG (Corrective RAG)
After retrieval, a grader LLM scores each chunk for relevance.
If relevance is low: reformulate query and retry, or fall back to web search.
If relevance is high: proceed to generation.
Paper: Yan et al., 2024.

### Self-RAG
LLM decides: (1) do I need retrieval? (2) are retrieved docs relevant? (3) is my answer supported by the docs? (4) is my answer useful?
Uses special tokens for self-reflection at each step.
More autonomous than CRAG -- the LLM is its own judge.

### Adaptive RAG
Routes queries to different retrieval strategies based on complexity.
Simple factual query -> direct LLM answer (no retrieval).
Moderate query -> single retrieval.
Complex query -> multi-step retrieval with reasoning.

### HyDE (Hypothetical Document Embeddings)
For vague queries: LLM generates a hypothetical answer first, embeds THAT, searches with it.
Why: the hypothetical answer is closer in embedding space to real documents than the short query is.
Example: query "supply chain issues" -> LLM generates "Supply chain disruptions caused by weather events including cyclones have led to port congestion..." -> embed this -> search.

### Graph RAG
Uses knowledge graph structure to enhance retrieval.
Steps: (1) extract entities from query (2) find related entities in graph (3) use graph context to enrich retrieval query (4) retrieve from vector store with enriched query.
This is what our system does: graph traversal + document retrieval.

### Raptor (Recursive Abstractive Processing for Tree-Organized Retrieval)
Builds a tree of summaries: leaf nodes are chunks, parent nodes are summaries of children, root is summary of everything.
Retrieval can happen at any level depending on query specificity.

### Context Compression
After retrieval, compress/extract only the relevant parts of each chunk before sending to LLM.
Reduces token usage and noise.

---

## 7. Query Transformation Techniques

### Query decomposition
Break complex query into sub-queries, retrieve for each, combine.
"Compare Tata Steel and JSW Steel contracts" -> two separate retrievals.

### Step-back prompting
Ask a more general question first to get broader context.
"What is the penalty for Tata Steel late delivery?" -> step back: "What are common vendor penalty structures?"

### Query routing
Classify query intent, route to appropriate retrieval source.
Our system does this: graph queries go to NetworkX, document queries go to Qdrant.

---

## 8. Evaluation (RAGAS Framework)

### What RAGAS measures

**Faithfulness**: Is the answer grounded in the retrieved context? (no hallucination)
- Score 0-1. Checks if each claim in the answer can be traced to retrieved chunks.

**Answer Relevance**: Does the answer actually address the question?
- Score 0-1. Generates questions from the answer, checks if they match the original.

**Context Precision**: Are the retrieved chunks relevant to the question?
- Score 0-1. Checks if relevant chunks are ranked higher than irrelevant ones.

**Context Recall**: Were all the necessary chunks retrieved?
- Score 0-1. Checks if ground truth answer can be attributed to retrieved context.

### Other evaluation approaches

**Hit Rate**: Was the correct document in the top-k results?
**MRR (Mean Reciprocal Rank)**: How high was the correct document ranked?
**NDCG (Normalized Discounted Cumulative Gain)**: Considers position-weighted relevance.

### Ground truth creation
Need question-answer-context triples for evaluation.
Can be created manually (expensive) or synthetically (LLM generates Q&A from documents).

---

## 9. Alternative Eval Frameworks

### 9.1 DeepEval (Confident AI)

**What it is**: A pytest-style eval framework with 14+ built-in metrics. Tests are written as Python functions and run in CI like any unit test suite. Each metric calls an LLM judge internally.

**Algorithm**:
Step 1: Define test cases as `LLMTestCase` objects — each holds `input`, `actual_output`, and `retrieval_context`
Step 2: Pick metrics: `FaithfulnessMetric`, `HallucinationMetric`, `ContextualRelevancyMetric`, etc.
Step 3: Decorate test functions with `@pytest.mark.parametrize`, call `assert_test()` which checks metric score against threshold
Step 4: CI fails if any metric score falls below the defined threshold — eval report generated per run

**Prod relevance for a multi-agent / ontology system**: HIGH
Why: pytest integration means eval runs automatically on every deploy. For a system with multiple LangGraph nodes, you can write targeted test cases per node (router, retriever, generator) and fail the build on regression.

---

### 9.2 TruLens (TruEra) — RAG Triad

**What it is**: A tracing-first eval framework built around three metrics called the "RAG Triad" — different names from RAGAS for the same underlying ideas. Wraps your app at the chain level and records inputs/outputs automatically.

**RAG Triad mapping**:
- Groundedness = Faithfulness (answer → context)
- Answer Relevance = Answer Relevance (answer → question)
- Context Relevance = Context Precision (context → question)

**Algorithm**:
Step 1: Wrap your RAG chain with `TruChain` or `TruCustomApp`
Step 2: Run queries — TruLens records inputs, outputs, and intermediate steps automatically
Step 3: Feedback functions evaluate each of the 3 triad metrics using an LLM judge
Step 4: View dashboard with per-query scores, traces, and aggregated metric trends

**Key distinction vs RAGAS**: TruLens is tracing-first (wraps the live app), RAGAS is dataset-first (evaluates a batch offline). TruLens dashboard is better for non-engineers to review.

**Prod relevance for a multi-agent / ontology system**: HIGH
Why: Real-time tracing fits production monitoring. For a multi-agent system, TruLens shows per-trace quality — you can see which specific queries degrade each metric.

---

### 9.3 ARES (Stanford)

**What it is**: Automated RAG Evaluation System — trains small lightweight LM judges (not GPT-4) on your domain data. Eval doesn't depend on expensive proprietary APIs and captures domain-specific knowledge that general LLM judges miss.

**Algorithm**:
Step 1: Sample a few hundred QA pairs from your corpus, or generate them synthetically
Step 2: Human-annotate ~50–100 as gold labels for faithfulness and context relevance
Step 3: Fine-tune a small classifier (DeBERTa-v3 or similar) on these annotated labels
Step 4: Use the fine-tuned judge for all future eval — runs locally, fast, cheap

**Prod relevance for a multi-agent / ontology system**: MEDIUM
Why: High value when your domain has jargon a GPT-4 judge misses (supply chain terminology, vendor-specific clause structures). Lower value if you're already paying for Groq/OpenAI and query volume is modest enough that API judge cost is negligible.

---

### 9.4 UpTrain

**What it is**: Open-source eval framework with 40+ modular checks covering hallucination, context relevance, completeness, and conversation quality. API is similar to RAGAS — pass a dataset, get scores back.

**Algorithm**:
Step 1: Define `EvalLLM` (your judge model)
Step 2: Pass dataset `{question, response, context}` to `Settings` and `evaluate()`
Step 3: Select checks: `Evals.RESPONSE_RELEVANCE`, `Evals.FACTUAL_ACCURACY`, `Evals.RESPONSE_COMPLETENESS`, etc.
Step 4: UpTrain scores each check and returns a DataFrame with per-row metric values

**Prod relevance for a multi-agent / ontology system**: MEDIUM
Why: Useful when you need checks RAGAS doesn't have — response completeness (did the answer cover all aspects?), jailbreak detection, conversation coherence across multi-turn sessions.

---

### 9.5 Arize Phoenix

**What it is**: Observability + eval in one open-source tool. Traces every LLM/RAG call (with retrieval spans, LLM spans, latency), and lets you run evals on the captured trace data. Integrates with LangChain and LlamaIndex.

**Algorithm**:
Step 1: Instrument your app with the Phoenix tracer (one-line setup)
Step 2: Every query is captured as a trace: retrieval spans + LLM spans + latency at each step
Step 3: Run evals on the captured traces using built-in or custom evaluators
Step 4: View in Phoenix UI — traces, per-span quality scores, latency heatmaps

**Prod relevance for a multi-agent / ontology system**: HIGH
Why: Traces show WHICH node (retrieval vs router vs generator) is degrading quality, not just end-to-end scores. For a system with KG lookup + RAG retrieval + intent routing, span-level attribution is essential for debugging.

---

### 9.6 Braintrust

**What it is**: Production eval platform focused on "eval ops" — dataset versioning, online eval, CI hooks, and A/B experiment comparison across model or prompt versions.

**Algorithm**:
Step 1: Define a dataset (list of `{input, expected}` pairs) and version it
Step 2: Write a scorer function (any Python function returning 0–1)
Step 3: Run an Experiment — Braintrust calls your app + scorers on every row
Step 4: Compare experiments side-by-side (model A vs B, prompt v1 vs v2, retriever config 1 vs 2)

**Prod relevance for a multi-agent / ontology system**: MEDIUM
Why: Most valuable when iterating quickly on the retrieval pipeline and tracking regressions across experiments. Less useful if your pipeline is stable and you just need ongoing monitoring.

---

### 9.7 Giskard

**What it is**: ML testing + LLM red-teaming framework. Automatically generates adversarial test cases — prompt injection probes, hallucination triggers, bias probes — without manual test authoring.

**Algorithm**:
Step 1: Wrap your RAG chain with `giskard.Model()`
Step 2: Run `giskard.scan()` — automatically generates adversarial probes across failure categories
Step 3: Review flagged issues: hallucination cases, robustness failures, bias patterns
Step 4: Export the generated test suite and add it to CI

**Prod relevance for a multi-agent / ontology system**: LOW-MEDIUM
Why: Most red-teaming value is for open-domain customer-facing chatbots. Still useful for testing negative rejection (unanswerable queries) in a closed-domain supply chain system.

---

## 10. LLM-as-Judge

**What it is**: Instead of rule-based metrics (BLEU, exact match), a capable LLM scores outputs based on criteria you define in a rubric. All modern eval frameworks — DeepEval, TruLens, RAGAS, UpTrain — are LLM-as-Judge under the hood.

**G-Eval algorithm (NLPeng et al., 2023 — the canonical paper)**:
Step 1: Define evaluation criteria in a rubric (e.g. "Score 1–5: Is the answer faithful to the context? 5 = all claims grounded, 1 = major hallucination")
Step 2: Generate chain-of-thought evaluation steps from the criteria via LLM
Step 3: For each output, feed `(criteria + CoT steps + output to evaluate)` to the judge LLM
Step 4: Ask the judge to produce a score. Average over multiple runs for stability.

**Pairwise vs Pointwise**:
- **Pointwise**: "Score this answer 1–5." — simpler, works for absolute thresholds
- **Pairwise**: "Which answer is better, A or B?" — more reliable; human raters also prefer this format. Use when comparing two systems or prompt versions.

**Bias types** (critical for interviews):
- **Position bias**: LLM prefers whichever answer appears first in a pairwise comparison → mitigation: swap A/B order, average both runs
- **Verbosity bias**: LLM prefers longer answers regardless of quality → mitigation: explicitly penalise unnecessary length in the rubric
- **Self-enhancement bias**: a model judges its own outputs higher → mitigation: use a different model family as judge (generate with Llama, judge with GPT-4)

**Prod relevance for a multi-agent / ontology system**: HIGH
Why: In a system with 5 intents and 2 retrieval paths (KG + RAG), rule-based metrics cannot evaluate "did the RCA node correctly synthesise graph context with document context?" — only an LLM judge can assess that kind of multi-step reasoning quality.

---

## 11. Robustness Evaluation (RGB's 4 Abilities)

**What it is**: RGB (Retrieval-Augmented Generation Benchmark, Chen et al. 2023) identifies 4 failure-mode abilities that RAGAS completely ignores. These are the failure modes that actually bite in production.

### Ability 1 — Noise Robustness

**What**: Inject N irrelevant chunks alongside the relevant ones. Does the model still answer correctly?

**Algorithm**:
Step 1: For each test query, retrieve the top-k relevant chunks
Step 2: Insert m noise chunks (randomly sampled from other documents in the corpus)
Step 3: Re-run generation, compare answer correctness with vs. without noise
Step 4: Noise robustness score = `accuracy_with_noise / accuracy_without_noise`

**Prod relevance**: HIGH — Qdrant cosine search always returns k chunks even when some are irrelevant. At `top_k=5` in multi-doc scenarios, noise chunks are guaranteed to appear.

### Ability 2 — Negative Rejection

**What**: Ask an unanswerable question — the corpus has NO relevant information. Does the model refuse, or does it hallucinate?

**Algorithm**:
Step 1: Craft questions that cannot be answered from any document in the corpus
Step 2: Retrieve top-k — all chunks will be irrelevant
Step 3: Check if the response contains a proper refusal ("I don't have information on this...")
Step 4: Score = fraction of unanswerable queries correctly refused

Note: This is exactly what T13–T15 in `eval_pipeline.py` test.

### Ability 3 — Information Integration

**What**: The correct answer requires synthesising facts from MULTIPLE retrieved chunks (from different documents). Tests multi-hop reasoning across docs.

**Algorithm**:
Step 1: Design queries where no single chunk is sufficient (requires doc A + doc B)
Step 2: Retrieve top-k, ensure both necessary chunks are present in context
Step 3: Evaluate whether the generated answer correctly combines both facts
Step 4: Score = fraction of multi-doc queries correctly integrated

Note: T11, T12 in `eval_pipeline.py` are integration cases.

### Ability 4 — Counterfactual Robustness

**What**: Inject a chunk containing a WRONG version of a fact that contradicts the real answer. Does the model blindly follow the injected doc or use correct knowledge?

**Algorithm**:
Step 1: For a question with a known answer, create a "poisoned" chunk with the wrong fact (e.g. "penalty for 3–5 days late is 2%")
Step 2: Include it in the retrieved context alongside correct chunks
Step 3: Check if the model follows the poison or the correct source
Step 4: Measure error rate introduced by counterfactual injection

**Prod relevance**: MEDIUM — most relevant when docs are user-editable or aggregated from multiple vendors who might have conflicting figures.

---

## 12. Online / Continuous Evaluation

**What it is**: RAGAS is offline batch eval — you run it on a fixed test set. Production systems need continuous eval on live traffic. Different problem, different tools.

### Pattern 1 — Golden Set Monitoring

Step 1: Curate a fixed set of ~50–100 high-priority queries with known expected answers
Step 2: Run this set automatically on every code / model / retriever deploy
Step 3: Alert if any metric drops >X% from the previous run baseline
Step 4: Track metric trends over time — catches gradual regression

### Pattern 2 — Shadow Evaluation

Step 1: Sample 5–10% of real production traffic
Step 2: Run async eval (faithfulness + relevance) on these samples
Step 3: Aggregate daily — track rolling 7-day metric averages
Step 4: Page the team if rolling faithfulness drops below threshold

Cost note: Each eval call costs ~$0.001–$0.01 depending on judge model. At 5% sample of 1,000 queries/day = 50 evals/day = negligible.

### Pattern 3 — User Signals as Proxy Metrics

Implicit feedback without explicit annotations:
- **Thumbs up/down** → direct signal
- **Re-query rate**: user asks same question again → implicit failure signal
- **Copy-to-clipboard rate** → implicit success signal
- **Time-on-answer** → engagement proxy

### Embedding Drift Detection

Step 1: At ingestion time, log mean cosine similarity of retrieved chunks per query
Step 2: Monitor this distribution over time
Step 3: A drop in mean similarity = either (a) new query types not matching the corpus, or (b) corpus is stale relative to evolving queries
Step 4: Trigger re-indexing or corpus expansion when drift detected

**Prod relevance for a multi-agent / ontology system**: HIGH
Why: A system with intent routing has a hidden failure mode — if the router misclassifies a "document" query as a "graph" query, RAG is never invoked. This never shows up in RAG metrics. Only continuous router accuracy monitoring catches it.

---

## 13. Benchmark Datasets

Used by researchers to compare RAG systems. Not what you'd use for your own domain — you'd run RAGAS on your own data. Know these for "how do you benchmark a RAG system" interview questions.

| Dataset | Type | What it tests |
|---|---|---|
| Natural Questions (NQ) | Open-domain QA | Standard open-domain retrieval |
| TriviaQA | Open-domain QA | Knowledge recall, multi-document retrieval |
| HotpotQA | Multi-hop QA | 2-hop reasoning across documents — closest to information integration |
| MSMARCO | Passage retrieval | Industry-standard retrieval ranking benchmark |
| RGB | RAG-specific | 4 robustness abilities (Section 11) |
| CRUD-RAG | RAG-specific | Create/Read/Update/Delete style query taxonomy |
| FactScore dataset | Fact verification | Atomic claim precision for knowledge-intensive generation |

**Prod relevance**: LOW for domain-specific systems. You don't need HotpotQA — your test dataset (the 15 cases in `eval_pipeline.py`) is more valuable because it's in-domain.

---

## 14. Metric Zoo

Metrics that appear in papers and production but aren't in RAGAS by default.

### FactScore

**Concept**: Instead of scoring the whole answer as a unit, decompose it into atomic facts and verify each claim independently against a knowledge source.

**Algorithm**:
Step 1: LLM decomposes the answer into a list of atomic claims: ["penalty is 5%", "applies to 3–5 day delays"]
Step 2: For each claim, retrieval system finds the most relevant passage
Step 3: LLM judges: is this claim supported by that passage?
Step 4: FactScore = `supported_claims / total_claims`

**Difference from faithfulness**: FactScore retrieves evidence for each claim independently, whereas faithfulness checks all claims against the already-retrieved context. FactScore doubles your LLM and retrieval calls.

**Prod relevance**: LOW — use faithfulness with claim extraction (as `eval_pipeline.py` does) instead.

---

### BERTScore

**Concept**: Semantic similarity between generated answer and a reference answer, computed using BERT contextual embeddings. Better than BLEU for meaning preservation.

**Algorithm**:
Step 1: Tokenize both candidate and reference sentences
Step 2: Get BERT embeddings for each token
Step 3: Greedy matching — for each token in candidate, find max cosine similarity to any token in reference
Step 4: Compute Precision, Recall, F1 over these token-level matches

**Prod relevance**: LOW-MEDIUM — useful when you have ground truth and want a fast reference-based score without an LLM judge. Doesn't catch factual errors well.

---

### BLEU / ROUGE

**Concept**: N-gram overlap between generated text and a reference. Legacy metrics from machine translation (BLEU) and summarisation (ROUGE).

**Why they're bad for RAG**: "The penalty is 5%" and "A 5% penalty applies" have the same meaning but near-zero BLEU overlap. These metrics measure phrasing similarity, not factual accuracy.

**Prod relevance**: VERY LOW — mention you know they exist and exactly why you don't use them.

---

### NDCG@k (fuller explanation — introduced in Section 8)

**Concept**: Position-weighted precision. A relevant chunk at rank 1 is worth more than one at rank 5.

**Algorithm**:
```
DCG@k  = Σ (2^rel_i - 1) / log2(i + 1)   for i = 1 to k
NDCG@k = DCG@k / IDCG@k                   (normalised by ideal ranking)
```
Where `rel_i = 1` if chunk at rank i is relevant, `0` otherwise. IDCG is the DCG of the perfect ranking.

**When to use over MRR**: When multiple relevant chunks exist and their rank ordering matters. MRR only cares about the first hit.

---

## 15. Monitoring and Observability

### LangFuse
Open-source observability for LLM applications.
Tracks: latency per step, token usage, cost, retrieval quality over time.
Integrates with LangChain/LangGraph via callbacks.
Key features: trace visualization, prompt versioning, user feedback collection.

### LangSmith
LangChain's observability platform.
Similar to LangFuse but tighter LangChain integration.
Tracks full agent traces, tool calls, intermediate steps.

### Key metrics to monitor in production
- Retrieval latency (p50, p95, p99)
- LLM latency and token consumption
- Retrieval relevance scores over time (drift detection)
- User satisfaction / feedback scores
- Hallucination rate (faithfulness score)
- Cost per query

### Embedding drift
Over time, new documents may shift the distribution. Monitor retrieval quality and re-embed periodically.

---

## 16. Production Considerations

### Chunking pipeline
- Document loaders: PyMuPDF (PDF), python-pptx (PPT), openpyxl (Excel), unstructured.io (multi-format)
- Tables: extract separately, serialize as markdown, embed as own chunks with "table" metadata
- Images in docs: OCR or multimodal embeddings (CLIP)

### Scaling
- Qdrant/Milvus for large-scale vector search
- Async ingestion pipeline
- Cache frequent queries and their results
- Batch embedding for ingestion (not one-at-a-time)

### Security
- PII detection before indexing
- Access control: metadata filtering ensures users only see docs they have access to
- Audit trail: log what was retrieved and generated

### Cost optimization
- Smaller embedding models for high-volume, low-stakes queries
- Caching embeddings (don't re-embed unchanged documents)
- Tiered retrieval: cheap BM25 first, expensive re-ranking only when needed