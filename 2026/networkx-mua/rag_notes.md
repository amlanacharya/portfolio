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

## 9. Monitoring and Observability

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

## 10. Production Considerations

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