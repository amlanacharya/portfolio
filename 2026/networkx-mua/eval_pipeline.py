"""
eval_pipeline.py — RAGAS-style evaluation for the networkx-mua supply chain RAG system.

Run from the repo root (C:/portfolio) or from 2026/networkx-mua/ — the script
fixes its own working directory.

    # Groq backend (default, requires GROQ_API_KEY in .env)
    python 2026/networkx-mua/eval_pipeline.py
    python 2026/networkx-mua/eval_pipeline.py --backend groq --model llama-3.3-70b-versatile

    # Ollama backend (local, no API key — requires `ollama serve` + model pulled)
    python 2026/networkx-mua/eval_pipeline.py --backend ollama
    python 2026/networkx-mua/eval_pipeline.py --backend ollama --model llama3.2:3b

RAGAS optional comparison:
    pip install ragas langchain-groq langchain-huggingface     # Groq
    pip install ragas langchain-ollama langchain-huggingface   # Ollama

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEPTUAL Q&A
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1: What is the difference between Faithfulness and Answer Relevance, and when
    would you see one fail without the other?

Faithfulness (answer → context): every factual claim in the generated answer
must be grounded in the retrieved context. It catches hallucination — the model
inventing facts not present in any retrieved document.

Answer Relevance (answer → question): the answer must address what the user
actually asked. It catches topical drift — the model retrieving correct facts and
writing a faithful answer, but about the wrong topic.

They are orthogonal:
  - High faithfulness + low relevance: "The penalty for 1-2 day delays is 2%,
    and for 3-5 days is 5%." is perfectly grounded in the contract, but answers
    the wrong question if the user asked "What is the rush order lead time?"
  - Low faithfulness + high relevance: "The rush order lead time is 5 days." is
    on-topic but hallucinates — the correct answer is 3 business days.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q2: Why does context recall require ground truth but faithfulness does not?

Faithfulness checks answer → context: given what was retrieved and what the
model said, are the claims supported? You only need the answer and the retrieved
chunks — no external reference required.

Context recall checks ground_truth → context: "Was everything that SHOULD be in
the context actually retrieved?" You must know what the ideal answer contains
before you can ask whether the retriever surfaced the evidence for it. Without
a ground truth reference, you cannot measure what was missed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q3: How would you generate synthetic test data without human annotations?

Three approaches:
  1. Reverse HyDE: for each chunk, prompt the LLM "What question does this
     passage best answer?" → generates question→passage pairs automatically,
     with the chunk itself as the ground truth context.
  2. LLM-as-annotator: feed each document to an LLM, ask it to generate N
     diverse QA pairs with answers grounded only in the text. A second LLM
     call verifies that each answer is actually in the source.
  3. Embedding diversity sampling: embed all chunks, cluster them (k-means or
     HDBSCAN), then sample one chunk per cluster to ensure full semantic coverage
     of the corpus before applying approaches 1 or 2.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q4: What thresholds would you set for production, and what metrics would you add
    beyond RAGAS?

Production thresholds (empirically calibrated for this supply chain domain):
  - Faithfulness       > 0.80   hard requirement — hallucination guard
  - Answer Relevance   > 0.75
  - Context Precision  > 0.60
  - Context Recall     > 0.70   (requires ground truth)

Beyond RAGAS:
  - Hit Rate @k: did the correct source document appear anywhere in the top-k
    retrieved chunks? Measures retrieval coverage independent of ranking.
  - MRR (Mean Reciprocal Rank): where in the ranking did the first correct chunk
    appear? 1/rank — rewards systems that surface the right evidence at position 1.
  - Router Accuracy: for this multi-intent system, does the intent classifier
    correctly route document queries to the document handler? Misrouting to
    "query" or "action" bypasses RAG entirely.
  - Hallucination Guard: pattern check for refusal markers ("I don't have
    information", "not mentioned in the provided documents") — flags correct
    abstentions on unanswerable questions and catches silent hallucinations.
  - Latency p95: end-to-end query latency at the 95th percentile. RAGAS scores
    are irrelevant if the system cannot respond within SLA in production.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ─── Path fix ───────────────────────────────────────────────────────────────
# get_vector_store() uses the relative path r"2026\networkx-mua\docs_folder".
# We must chdir to the repo root BEFORE importing any local modules.
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))          # …/networkx-mua
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))  # C:/portfolio
os.chdir(REPO_ROOT)
sys.path.insert(0, SCRIPT_DIR)

# ─── Standard imports ───────────────────────────────────────────────────────
import argparse
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from groq import Groq

load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

# Local modules (importable now that SCRIPT_DIR is on sys.path)
from embedding import get_vector_store
from llm_router import llm_router
from retrieval import search_docs

# ─── TEST DATASET ────────────────────────────────────────────────────────────

TEST_DATASET: List[Dict[str, Any]] = [
    # ── Single-document: tata_steel_contract.md ──────────────────────────────
    {
        "id": "T01",
        "category": "single_doc",
        "question": "What is the penalty percentage for a delivery that is 3-5 days late?",
        "ground_truth": "A delivery that is 3-5 days late incurs a penalty of 5% of the order value.",
        "expected_sources": ["tata_steel_contract.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T02",
        "category": "single_doc",
        "question": "What is the maximum storage capacity of the Delhi Hub warehouse?",
        "ground_truth": "The Delhi Hub (warehouse_1) has a maximum storage capacity of 800 units.",
        "expected_sources": ["warehouse_capacity_policy.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T03",
        "category": "single_doc",
        "question": "At what stock level is an automatic reorder triggered?",
        "ground_truth": "An automatic purchase order is generated when stock at any warehouse hits the reorder trigger of 250 units.",
        "expected_sources": ["warehouse_capacity_policy.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T04",
        "category": "single_doc",
        "question": "What is the lead time for rush orders under the Tata Steel contract?",
        "ground_truth": "Rush orders have a lead time of 3 business days.",
        "expected_sources": ["tata_steel_contract.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T05",
        "category": "single_doc",
        "question": "How quickly must a high severity incident be acknowledged?",
        "ground_truth": "High severity incidents require acknowledgment within 1 hour and an action plan within 4 hours.",
        "expected_sources": ["incident_management_sop.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T06",
        "category": "single_doc",
        "question": "What is the backup route if route_1 sea route is disrupted?",
        "ground_truth": "If route_1 (sea) is disrupted, route_3 (rail) is used as the backup.",
        "expected_sources": ["shipping_policy.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T07",
        "category": "single_doc",
        "question": "What is the cost increase when diverting cargo from Vizag Port to Chennai Port?",
        "ground_truth": "Diverting from Vizag Port (port_1) to Chennai Port (port_2) incurs a 12% cost increase.",
        "expected_sources": ["shipping_policy.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T08",
        "category": "single_doc",
        "question": "What happens when the defect rate in a Tata Steel shipment exceeds 10%?",
        "ground_truth": "A defect rate above 10% requires full replacement at vendor cost plus a 10% penalty.",
        "expected_sources": ["tata_steel_contract.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T09",
        "category": "single_doc",
        "question": "Within how many hours must an insurance claim be filed for damaged warehouse inventory?",
        "ground_truth": "Insurance claims for damaged inventory must be filed within 48 hours.",
        "expected_sources": ["warehouse_capacity_policy.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T10",
        "category": "single_doc",
        "question": "What port throughput level triggers a high severity classification?",
        "ground_truth": "When port throughput drops below 30% of capacity, the incident is classified as high severity.",
        "expected_sources": ["incident_management_sop.md"],
        "expected_intent": "document",
        "top_k": 5,
    },
    # ── Multi-document ────────────────────────────────────────────────────────
    {
        "id": "T11",
        "category": "multi_doc",
        "question": "Is Tata Steel exempt from delivery penalties during a cyclone, and what procedure applies to routes affected by the weather?",
        "ground_truth": (
            "Yes. The Tata Steel contract includes a force majeure clause covering natural disasters "
            "including cyclones, with no penalties applied. During an active cyclone, affected routes "
            "such as route_2 are suspended and cargo is redirected — for example, to route_3 "
            "(Kolkata-Delhi rail). Vizag Port operations are reduced to emergency-only berthing, "
            "with shipments diverted to Chennai Port."
        ),
        "expected_sources": ["tata_steel_contract.md", "cyclone_response_protocol.md"],
        "expected_intent": "document",
        "top_k": 7,
    },
    {
        "id": "T12",
        "category": "multi_doc",
        "question": "If Vizag Port has been congested for more than 7 days, what actions are required according to both the shipping policy and the incident management SOP?",
        "ground_truth": (
            "Per the shipping policy, congestion exceeding 7 days requires escalation to the Supply "
            "Chain Director and consideration of emergency procurement from alternative suppliers. "
            "Per the incident management SOP, if port throughput drops below 30%, it is classified "
            "as high severity requiring acknowledgment within 1 hour and an action plan within 4 hours. "
            "Priority berthing for critical products such as Steel Coil should also be negotiated."
        ),
        "expected_sources": ["shipping_policy.md", "incident_management_sop.md"],
        "expected_intent": "document",
        "top_k": 7,
    },
    # ── Unanswerable ─────────────────────────────────────────────────────────
    {
        "id": "T13",
        "category": "unanswerable",
        "question": "What is the vendor support phone number for Tata Steel?",
        "ground_truth": None,
        "expected_sources": [],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T14",
        "category": "unanswerable",
        "question": "What is the current price per ton of steel coil?",
        "ground_truth": None,
        "expected_sources": [],
        "expected_intent": "document",
        "top_k": 5,
    },
    {
        "id": "T15",
        "category": "unanswerable",
        "question": "What is the annual insurance premium rate for warehouse inventory?",
        "ground_truth": None,
        "expected_sources": [],
        "expected_intent": "document",
        "top_k": 5,
    },
]

# ─── Prompts ─────────────────────────────────────────────────────────────────

ANSWER_PROMPT = """\
You are a supply chain expert assistant. Answer the user's question based ONLY \
on the provided context documents. If the context does not contain enough \
information to answer the question, say exactly:
"I don't have enough information in the provided documents to answer this question."

Rules for your answer:
- Write 1–3 sentences. Do not pad with background information or restate the question.
- When the answer is a specific number, threshold, or time limit, quote the exact value \
from the document and name the section it comes from (e.g. "Per Section 2. Penalty \
Structure of tata_steel_contract.md, the penalty is 5% of order value.").
- Do not add information that is not explicitly stated in the context.

Context:
{context}

Question: {question}

Answer:"""

CLAIMS_EXTRACT_PROMPT = """\
Extract every distinct factual claim from the answer below. \
Return ONLY a JSON array of strings, one claim per element. \
Each claim must be a single, atomic, self-contained statement.

Answer: {answer}

JSON array of claims:"""

CLAIM_SUPPORT_PROMPT = """\
Does the context support the claim below, either verbatim or through equivalent meaning? \
Minor paraphrasing, unit equivalences, and reordering count as support. \
Reply YES if the claim is substantively grounded in the context. \
Reply NO only if the context contradicts the claim or is entirely silent on it.

Context:
{context}

Claim: {claim}

Answer (YES or NO):"""

SYNTHETIC_QUESTIONS_PROMPT = """\
Given the answer below, generate exactly 3 different questions that this answer \
would be a good response to. Return ONLY a JSON array of 3 question strings.

Answer: {answer}

JSON array of questions:"""

CHUNK_RELEVANCE_PROMPT = """\
Is the following context chunk relevant to answering the question? \
Reply with exactly YES or NO.

Question: {question}

Context chunk:
{chunk}

Answer (YES or NO):"""

SENTENCE_SUPPORT_PROMPT = """\
Does the context below contain enough information to support the following \
statement? Reply with exactly YES or NO.

Statement: {sentence}

Context:
{context}

Answer (YES or NO):"""

# ─── LLM backend ─────────────────────────────────────────────────────────────
# All metric functions accept an LLMCallable — a plain (prompt: str) -> str
# function. Use the factories below to build one for your chosen backend.

LLMCallable = Callable[[str], str]

DEFAULT_GROQ_MODEL   = "llama-3.3-70b-versatile"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"  


def make_groq_llm(model: str = DEFAULT_GROQ_MODEL) -> LLMCallable:
    """Returns an LLMCallable backed by the Groq API."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Check 2026/networkx-mua/.env")
    client = Groq(api_key=api_key)

    def _call(prompt: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content.strip()

    return _call


def make_ollama_llm(model: str = DEFAULT_OLLAMA_MODEL) -> LLMCallable:
    """Returns an LLMCallable backed by a local Ollama server (localhost:11434).

    Requires Ollama to be running: `ollama serve`
    Pull the model first: `ollama pull llama3.1:8b`
    """
    import requests

    def _call(prompt: str) -> str:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    return _call


def call_llm(llm: LLMCallable, prompt: str) -> str:
    """Thin wrapper so callers don't need to know the backend."""
    return llm(prompt)


def _parse_json_list(text: str, fallback_split: str = "\n") -> List[str]:
    """Parse a JSON array from LLM output, with line-by-line fallback."""
    # Try to find a JSON array in the text
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return [str(item).strip() for item in result if str(item).strip()]
        except json.JSONDecodeError:
            pass
    # Fallback: split on newlines and strip bullets/numbering
    lines = [re.sub(r"^[\d\.\-\*\s]+", "", ln).strip() for ln in text.split(fallback_split)]
    return [ln for ln in lines if ln]


# ─── RAG pipeline (adds generation step missing from orchestrator.py) ─────────

def run_rag_pipeline(
    question: str,
    llm: LLMCallable,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Retrieves chunks and generates an answer with Groq.

    Returns:
        {
            "question": str,
            "answer": str,
            "chunks": List[Dict],   # [{text, source, section, score}]
            "context": str,         # concatenated chunk texts
            "latency_s": float,
        }
    """
    t0 = time.perf_counter()
    chunks = search_docs(question, top_k=top_k)

    context = "\n\n---\n\n".join(
        f"[Source: {c['source']} | Section: {c['section']}]\n{c['text']}"
        for c in chunks
    )
    prompt = ANSWER_PROMPT.format(context=context, question=question)
    answer = call_llm(llm, prompt)
    latency = time.perf_counter() - t0

    return {
        "question": question,
        "answer": answer,
        "chunks": chunks,
        "context": context,
        "latency_s": latency,
    }


# ─── Metric 1: Faithfulness ──────────────────────────────────────────────────

def faithfulness_score(
    answer: str,
    context: str,
    llm: LLMCallable,
) -> Tuple[float, Dict[str, Any]]:
    """
    Algorithm:
      1. Extract atomic claims from the answer via LLM.
      2. For each claim, ask the LLM whether it is supported by the context.
      3. score = supported_claims / total_claims

    Correct refusals (unanswerable questions where the model says "I don't have
    information") are assigned a score of 1.0 by convention — they are the right
    behaviour and contain no hallucinated claims.
    """
    refusal_markers = [
        "i don't have enough information",
        "i don't have information",
        "not mentioned in the provided",
        "cannot be found in",
        "no information",
    ]
    if any(m in answer.lower() for m in refusal_markers):
        return 1.0, {"claims": [], "supported": 0, "total": 0, "note": "correct_refusal"}

    # Step 1: extract claims
    raw = call_llm(llm, CLAIMS_EXTRACT_PROMPT.format(answer=answer))
    claims = _parse_json_list(raw)

    if not claims:
        return 0.0, {"claims": [], "supported": 0, "total": 0, "note": "no_claims_extracted"}

    # Step 2: verify each claim
    supported = []
    for claim in claims:
        verdict = call_llm(
            llm,
            CLAIM_SUPPORT_PROMPT.format(context=context, claim=claim),
        )
        supported.append(verdict.strip().upper().startswith("YES"))

    score = sum(supported) / len(claims)
    return score, {
        "claims": claims,
        "supported_flags": supported,
        "supported": sum(supported),
        "total": len(claims),
    }


# ─── Metric 2: Answer Relevance ──────────────────────────────────────────────

def answer_relevance_score(
    question: str,
    answer: str,
    llm: LLMCallable,
) -> Tuple[float, Dict[str, Any]]:
    """
    Algorithm:
      1. Generate 3 synthetic questions from the answer via LLM.
      2. Embed the original question and each synthetic question using the same
         all-MiniLM-L6-v2 model that powers the vector store.
      3. score = mean cosine similarity between original and synthetic questions.

    Correct refusals are assigned 0.95 by convention.
    """
    refusal_markers = [
        "i don't have enough information",
        "i don't have information",
        "not mentioned in the provided",
    ]
    if any(m in answer.lower() for m in refusal_markers):
        return 0.95, {"generated_questions": [], "per_sim": [], "mean": 0.95, "note": "correct_refusal"}

    raw = call_llm(llm, SYNTHETIC_QUESTIONS_PROMPT.format(answer=answer))
    gen_questions = _parse_json_list(raw)[:3]  # cap at 3

    if not gen_questions:
        return 0.0, {"generated_questions": [], "per_sim": [], "mean": 0.0, "note": "no_questions_generated"}

    _, embed_model = get_vector_store()

    all_texts = [question] + gen_questions
    embeddings = embed_model.encode(all_texts, show_progress_bar=False)

    q_emb = embeddings[0]
    sims = []
    for gen_emb in embeddings[1:]:
        sim = float(
            np.dot(q_emb, gen_emb) / (np.linalg.norm(q_emb) * np.linalg.norm(gen_emb) + 1e-9)
        )
        sims.append(sim)

    mean_sim = float(np.mean(sims)) if sims else 0.0
    return mean_sim, {
        "generated_questions": gen_questions,
        "per_sim": sims,
        "mean": mean_sim,
    }


# ─── Metric 3: Context Precision ─────────────────────────────────────────────

def context_precision_score(
    question: str,
    chunks: List[Dict],
    llm: LLMCallable,
) -> Tuple[float, Dict[str, Any]]:
    """
    Algorithm (Average Precision):
      1. For each retrieved chunk (in rank order), ask LLM: relevant? YES/NO.
      2. AP = (1/|R|) * sum_{k where rank_k is relevant} Precision@k
         where Precision@k = (relevant in top-k) / k
      3. If no chunks are relevant, AP = 0.0.

    AP rewards systems that rank relevant chunks higher.
    """
    if not chunks:
        return 0.0, {"ranked_relevance": [], "num_relevant": 0}

    relevance = []
    for chunk in chunks:
        verdict = call_llm(
            llm,
            CHUNK_RELEVANCE_PROMPT.format(question=question, chunk=chunk["text"][:800]),
        )
        relevance.append(verdict.strip().upper().startswith("YES"))

    num_relevant = sum(relevance)
    if num_relevant == 0:
        return 0.0, {"ranked_relevance": relevance, "num_relevant": 0}

    # Compute AP
    running_relevant = 0
    ap_sum = 0.0
    for k, is_rel in enumerate(relevance, start=1):
        if is_rel:
            running_relevant += 1
            ap_sum += running_relevant / k

    ap = ap_sum / num_relevant
    return ap, {"ranked_relevance": relevance, "num_relevant": num_relevant}


# ─── Metric 4: Context Recall ─────────────────────────────────────────────────

def context_recall_score(
    ground_truth: Optional[str],
    context: str,
    llm: LLMCallable,
) -> Tuple[float, Dict[str, Any]]:
    """
    Algorithm:
      1. Split ground truth into individual sentences.
      2. For each sentence, ask LLM: is it supported by the context? YES/NO.
      3. score = supported_sentences / total_sentences

    Returns (1.0, note="no_ground_truth") when GT is None (unanswerable cases).
    """
    if not ground_truth:
        return 1.0, {"sentences": [], "supported": 0, "total": 0, "note": "no_ground_truth"}

    # Split on sentence boundaries
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ground_truth) if s.strip()]

    if not sentences:
        return 1.0, {"sentences": [], "supported": 0, "total": 0, "note": "empty_ground_truth"}

    supported_flags = []
    for sentence in sentences:
        verdict = call_llm(
            llm,
            SENTENCE_SUPPORT_PROMPT.format(sentence=sentence, context=context),
        )
        supported_flags.append(verdict.strip().upper().startswith("YES"))

    score = sum(supported_flags) / len(sentences)
    return score, {
        "sentences": sentences,
        "supported_flags": supported_flags,
        "supported": sum(supported_flags),
        "total": len(sentences),
    }


# ─── Extra metrics ────────────────────────────────────────────────────────────

def hit_rate_at_k(
    chunks: List[Dict],
    expected_sources: List[str],
    k: Optional[int] = None,
) -> float:
    """
    Returns 1.0 if any expected source appears in the top-k retrieved chunks,
    0.0 otherwise. If k is None, checks all returned chunks.
    """
    if not expected_sources:
        return 1.0  # unanswerable — no source expected
    candidates = chunks[:k] if k else chunks
    retrieved_sources = {c["source"] for c in candidates}
    return 1.0 if any(src in retrieved_sources for src in expected_sources) else 0.0


def mean_reciprocal_rank(
    chunks: List[Dict],
    expected_sources: List[str],
) -> float:
    """
    Returns 1/rank of the first chunk whose source matches an expected source.
    Returns 0.0 if no match found.
    """
    if not expected_sources:
        return 1.0  # unanswerable — not penalised
    for rank, chunk in enumerate(chunks, start=1):
        if chunk["source"] in expected_sources:
            return 1.0 / rank
    return 0.0


def check_router_accuracy(question: str, expected_intent: str) -> bool:
    """Calls the existing llm_router and compares against expected intent."""
    result = llm_router({"query": question})
    return result.get("intent") == expected_intent


def check_hallucination(answer: str) -> bool:
    """
    Returns True if the answer contains a proper refusal marker, indicating
    the model correctly abstained rather than hallucinating.
    """
    markers = [
        "i don't have enough information",
        "i don't have information",
        "not mentioned in the provided",
        "cannot be found in",
        "no information in the",
        "the documents do not",
        "the provided documents do not",
    ]
    lower = answer.lower()
    return any(m in lower for m in markers)


# ─── RAGAS library comparison (optional) ─────────────────────────────────────

def run_ragas_eval(
    rag_results: List[Dict[str, Any]],
    test_cases: List[Dict[str, Any]],
    backend: str = "groq",
    model: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    """
    Runs the official RAGAS library over the same results for comparison.
    Skips gracefully if ragas or its dependencies are not installed.

    Install (Groq):
        pip install ragas langchain-groq langchain-huggingface
    Install (Ollama):
        pip install ragas langchain-ollama langchain-huggingface
    """
    try:
        from datasets import Dataset
        from langchain_huggingface import HuggingFaceEmbeddings
        from ragas import evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics.collections import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as e:
        print(f"\n[RAGAS] Skipped — missing dependency: {e}")
        print("  Install with: pip install ragas langchain-groq langchain-huggingface")
        return None

    print("\n[RAGAS] Running library comparison...")

    rows: Dict[str, List] = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
    }

    for res, tc in zip(rag_results, test_cases):
        if tc["category"] == "unanswerable":
            continue
        rows["question"].append(tc["question"])                          # fix: was res["question"]
        rows["answer"].append(res["answer"])
        rows["contexts"].append([c["text"] for c in res["chunks"]])     # text preserved in chunks
        rows["ground_truth"].append(tc["ground_truth"] or "")

    if not rows["question"]:
        print("[RAGAS] No answerable cases to evaluate.")
        return None

    dataset = Dataset.from_dict(rows)

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper

        if backend == "ollama":
            from langchain_ollama import ChatOllama
            _model = model or DEFAULT_OLLAMA_MODEL
            ragas_llm = LangchainLLMWrapper(ChatOllama(model=_model, temperature=0))
        else:
            from langchain_groq import ChatGroq
            _model = model or DEFAULT_GROQ_MODEL
            groq_key = os.environ.get("GROQ_API_KEY")
            ragas_llm = LangchainLLMWrapper(
                ChatGroq(model=_model, api_key=groq_key, temperature=0)
            )

        ragas_emb = LangchainEmbeddingsWrapper(
            HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        )

        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=ragas_llm,
            embeddings=ragas_emb,
        )
        scores = dict(result)
        print("[RAGAS] Library scores:")
        for k, v in scores.items():
            if isinstance(v, float):
                print(f"  {k:<25} {v:.3f}")
        return scores
    except Exception as e:
        print(f"[RAGAS] Evaluation failed: {e}")
        return None


# ─── Report generation ────────────────────────────────────────────────────────

THRESHOLDS = {
    "faithfulness": 0.80,
    "answer_relevance": 0.75,
    "context_precision": 0.60,
    "context_recall": 0.70,
    "hit_rate": 0.80,
    "mrr": 0.50,
    "router_accuracy": 0.90,  # aggregate target
}


def _fmt(val: Optional[float], threshold: Optional[float] = None) -> str:
    if val is None:
        return "  —   "
    s = f"{val:.3f}"
    if threshold is not None:
        s += " PASS" if val >= threshold else " FAIL"
    return s


def generate_report(results: List[Dict[str, Any]]) -> None:
    """Prints a full evaluation report: per-case breakdown + aggregate table."""
    sep = "=" * 90

    print(f"\n{sep}")
    print("  EVALUATION REPORT — networkx-mua RAG System")
    print(sep)

    # ── Per-question breakdown ────────────────────────────────────────────────
    print("\nPER-QUESTION BREAKDOWN")
    print("-" * 90)
    header = f"{'ID':<5} {'Cat':<12} {'Faith':>7} {'Rel':>7} {'Prec':>7} {'Recall':>7} {'HR@k':>6} {'MRR':>6} {'Rtr':>5} {'Lat':>6}"
    print(header)
    print("-" * 90)

    for r in results:
        tc = r["test_case"]
        m = r["metrics"]
        print(
            f"{tc['id']:<5} {tc['category']:<12} "
            f"{_fmt(m.get('faithfulness')):>7} "
            f"{_fmt(m.get('answer_relevance')):>7} "
            f"{_fmt(m.get('context_precision')):>7} "
            f"{_fmt(m.get('context_recall')):>7} "
            f"{_fmt(m.get('hit_rate')):>6} "
            f"{_fmt(m.get('mrr')):>6} "
            f"{'Y' if m.get('router_correct') else 'N':>5} "
            f"{r.get('latency_s', 0):.2f}s"
        )

    # ── Aggregate table ───────────────────────────────────────────────────────
    def _agg(results_subset: List[Dict], key: str) -> Optional[float]:
        vals = [r["metrics"].get(key) for r in results_subset if r["metrics"].get(key) is not None]
        return float(np.mean(vals)) if vals else None

    all_r  = results
    single = [r for r in results if r["test_case"]["category"] == "single_doc"]
    multi  = [r for r in results if r["test_case"]["category"] == "multi_doc"]

    print(f"\n{sep}")
    print("AGGREGATE METRICS")
    print("-" * 90)
    row_fmt = f"{'Metric':<22} {'Threshold':>10} {'All (n=' + str(len(all_r)) + ')':>12} {'Single (n=' + str(len(single)) + ')':>14} {'Multi (n=' + str(len(multi)) + ')':>13}"
    print(row_fmt)
    print("-" * 90)

    metrics_to_agg = [
        ("faithfulness",     THRESHOLDS["faithfulness"]),
        ("answer_relevance", THRESHOLDS["answer_relevance"]),
        ("context_precision",THRESHOLDS["context_precision"]),
        ("context_recall",   THRESHOLDS["context_recall"]),
        ("hit_rate",         THRESHOLDS["hit_rate"]),
        ("mrr",              THRESHOLDS["mrr"]),
    ]

    for metric, threshold in metrics_to_agg:
        v_all    = _agg(all_r,  metric)
        v_single = _agg(single, metric)
        v_multi  = _agg(multi,  metric)
        print(
            f"{metric:<22} {threshold:>10.2f} "
            f"{_fmt(v_all, threshold):>12} "
            f"{_fmt(v_single, threshold):>14} "
            f"{_fmt(v_multi, threshold):>13}"
        )

    # Router accuracy row
    router_correct = sum(1 for r in results if r["metrics"].get("router_correct"))
    router_acc = router_correct / len(results) if results else 0.0
    print(
        f"{'router_accuracy':<22} {THRESHOLDS['router_accuracy']:>10.2f} "
        f"{_fmt(router_acc, THRESHOLDS['router_accuracy']):>12}"
    )

    # Hallucination guard (unanswerable cases only)
    unans = [r for r in results if r["test_case"]["category"] == "unanswerable"]
    if unans:
        correct_refusals = sum(1 for r in unans if r["metrics"].get("is_refusal"))
        refusal_rate = correct_refusals / len(unans)
        print(f"{'hallucination_guard':<22} {'1.00':>10} {_fmt(refusal_rate, 1.0):>12}  (unanswerable n={len(unans)})")

    # Latency
    lats = [r.get("latency_s", 0) for r in results]
    if lats:
        lat_p95 = float(np.percentile(lats, 95))
        lat_mean = float(np.mean(lats))
        print(f"\n{'Latency mean':<22} {'':>10} {lat_mean:>10.2f}s")
        print(f"{'Latency p95':<22} {'':>10} {lat_p95:>10.2f}s")

    # ── Failure analysis ──────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("FAILURE ANALYSIS")
    print("-" * 90)

    failure_metrics = [
        ("faithfulness",      THRESHOLDS["faithfulness"]),
        ("answer_relevance",  THRESHOLDS["answer_relevance"]),
        ("context_precision", THRESHOLDS["context_precision"]),
        ("context_recall",    THRESHOLDS["context_recall"]),
    ]

    failures_found = False
    for r in results:
        tc = r["test_case"]
        m  = r["metrics"]
        failed = [
            metric for metric, threshold in failure_metrics
            if m.get(metric) is not None and m[metric] < threshold
        ]
        if not m.get("router_correct"):
            failed.append("router")
        if tc["category"] == "unanswerable" and not m.get("is_refusal"):
            failed.append("hallucination_guard")
        if failed:
            failures_found = True
            print(f"  {tc['id']} [{tc['category']}]: FAILED {failed}")
            print(f"    Q: {tc['question'][:80]}")
            print(f"    A: {r.get('answer','')[:100]}...")
            print()

    if not failures_found:
        print("  All cases passed all thresholds.")

    print(sep)


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RAG eval pipeline for networkx-mua")
    p.add_argument(
        "--backend", choices=["groq", "ollama"], default="groq",
        help="Generation backend (default: groq)",
    )
    p.add_argument(
        "--model", default=None,
        help="Override generation model name",
    )
    p.add_argument(
        "--judge-backend", choices=["groq", "ollama"], default=None,
        help="Judge backend (default: same as --backend)",
    )
    p.add_argument(
        "--judge-model", default=None,
        help="Override judge model name (default: same as --model)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Working directory: {os.getcwd()}")

    # ── Generation LLM ────────────────────────────────────────────────────────
    if args.backend == "ollama":
        gen_llm = make_ollama_llm(args.model or DEFAULT_OLLAMA_MODEL)
        gen_label = f"ollama/{args.model or DEFAULT_OLLAMA_MODEL}"
    else:
        gen_llm = make_groq_llm(args.model or DEFAULT_GROQ_MODEL)
        gen_label = f"groq/{args.model or DEFAULT_GROQ_MODEL}"

    # ── Judge LLM (may differ from generator) ────────────────────────────────
    judge_backend = args.judge_backend or args.backend
    if judge_backend == "ollama":
        judge_model = args.judge_model or args.model or DEFAULT_OLLAMA_MODEL
        judge_llm = make_ollama_llm(judge_model)
        judge_label = f"ollama/{judge_model}"
    else:
        judge_model = args.judge_model or (DEFAULT_GROQ_MODEL if args.backend == "groq" else DEFAULT_GROQ_MODEL)
        judge_llm = make_groq_llm(judge_model)
        judge_label = f"groq/{judge_model}"

    print(f"Generator : {gen_label}")
    print(f"Judge     : {judge_label}" + (" [split]" if judge_label != gen_label else ""))
    print("Warming up vector store (builds on first call)...")
    get_vector_store()

    # keep llm as alias for backward-compat with RAGAS helper
    llm = gen_llm

    results: List[Dict[str, Any]] = []

    print(f"\nRunning {len(TEST_DATASET)} test cases...\n")
    print(f"{'ID':<5} {'Status'}")
    print("-" * 50)

    for tc in TEST_DATASET:
        print(f"{tc['id']:<5} ", end="", flush=True)

        # 1. RAG pipeline (generation LLM)
        rag = run_rag_pipeline(tc["question"], gen_llm, top_k=tc["top_k"])

        # 2. Compute metrics (judge LLM)
        faith, faith_detail = faithfulness_score(rag["answer"], rag["context"], judge_llm)
        rel,   rel_detail   = answer_relevance_score(tc["question"], rag["answer"], judge_llm)
        prec,  prec_detail  = context_precision_score(tc["question"], rag["chunks"], judge_llm)
        recall,rec_detail   = context_recall_score(tc["ground_truth"], rag["context"], judge_llm)

        hr  = hit_rate_at_k(rag["chunks"], tc["expected_sources"])
        mrr = mean_reciprocal_rank(rag["chunks"], tc["expected_sources"])
        router_ok  = check_router_accuracy(tc["question"], tc["expected_intent"])
        is_refusal = check_hallucination(rag["answer"])

        metrics = {
            "faithfulness":      faith,
            "answer_relevance":  rel,
            "context_precision": prec,
            "context_recall":    recall,
            "hit_rate":          hr,
            "mrr":               mrr,
            "router_correct":    router_ok,
            "is_refusal":        is_refusal,
        }

        result = {
            "test_case":  tc,
            "answer":     rag["answer"],
            "chunks":     [
                {"source": c["source"], "section": c["section"], "score": c["score"], "text": c["text"]}
                for c in rag["chunks"]
            ],
            "metrics":    metrics,
            "details": {
                "faithfulness":      faith_detail,
                "answer_relevance":  rel_detail,
                "context_precision": prec_detail,
                "context_recall":    rec_detail,
            },
            "latency_s": rag["latency_s"],
        }
        results.append(result)

        flag = "PASS" if all(
            metrics.get(m, 1.0) >= t
            for m, t in [
                ("faithfulness", THRESHOLDS["faithfulness"]),
                ("answer_relevance", THRESHOLDS["answer_relevance"]),
                ("context_recall", THRESHOLDS["context_recall"]),
            ]
        ) else "FAIL"
        print(
            f"faith={faith:.2f} rel={rel:.2f} prec={prec:.2f} "
            f"recall={recall:.2f} hr={hr:.0f} mrr={mrr:.2f} "
            f"router={'Y' if router_ok else 'N'} [{flag}]"
        )

    # 3. RAGAS library comparison
    ragas_scores = run_ragas_eval(results, TEST_DATASET, backend=args.backend, model=args.model)

    # 4. Save results
    output_path = os.path.join(SCRIPT_DIR, "eval_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "date": "2026-03-05",
                    "gen_model": gen_label,
                    "judge_model": judge_label,
                    "embeddings": "all-MiniLM-L6-v2",
                    "n_cases": len(TEST_DATASET),
                },
                "results": results,
                "ragas_library_scores": ragas_scores,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\nResults saved to: {output_path}")

    # 5. Full report
    generate_report(results)


if __name__ == "__main__":
    main()
