"""
Model Benchmarking Harness — Router & Embedding model comparison.

Usage:
    python benchmark.py router                          # all router models
    python benchmark.py router --backends ollama         # ollama only
    python benchmark.py embedding                        # all embedding models
    python benchmark.py embedding --backends sentence_transformers
    python benchmark.py all --output benchmark_report.md # everything
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from groq import Groq
from sentence_transformers import SentenceTransformer
from chunking import load_and_chunk_docs
import numpy as np
import requests
from dotenv import load_dotenv
from embedding import build_vector_store
from eval_pipeline import TEST_DATASET as EVAL_DATASET


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
os.chdir(REPO_ROOT)
sys.path.insert(0, SCRIPT_DIR)

load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

from llm_router import ROUTER_ENTITY_PROMPT, VALID_INTENTS, _parse_llm_response

ROUTER_DATASET: List[Dict[str, Any]] = [
    {"id": "R01", "query": "What is the current status of port_1?", "expected_intent": "query", "expected_node_id": "port_1", "category": "query"},
    {"id": "R02", "query": "How is Vizag Port doing right now?", "expected_intent": "query", "expected_node_id": "port_1", "category": "query"},
    {"id": "R03", "query": "Show me the stock level at Delhi Hub", "expected_intent": "query", "expected_node_id": "warehouse_1", "category": "query"},
    {"id": "R04", "query": "What is the capacity utilization of Mumbai Plant?", "expected_intent": "query", "expected_node_id": "factory_1", "category": "query"},
    {"id": "R05", "query": "Is route_2 currently active?", "expected_intent": "query", "expected_node_id": "route_2", "category": "query"},
    {"id": "R06", "query": "Check the throughput at Chennai Port", "expected_intent": "query", "expected_node_id": "port_2", "category": "query"},
    {"id": "R07", "query": "What is the SLA adherence of Tata Steel?", "expected_intent": "query", "expected_node_id": "vendor_1", "category": "query"},
    {"id": "R08", "query": "Current state of Bangalore Hub warehouse", "expected_intent": "query", "expected_node_id": "warehouse_2", "category": "query"},
    {"id": "R09", "query": "Why is port_1 congested?", "expected_intent": "rca", "expected_node_id": "port_1", "category": "rca"},
    {"id": "R10", "query": "What is causing delays at Vizag Port?", "expected_intent": "rca", "expected_node_id": "port_1", "category": "rca"},
    {"id": "R11", "query": "Why is the Kolkata Plant under maintenance?", "expected_intent": "rca", "expected_node_id": "factory_3", "category": "rca"},
    {"id": "R12", "query": "Root cause of route_2 disruption", "expected_intent": "rca", "expected_node_id": "route_2", "category": "rca"},
    {"id": "R13", "query": "Why is warehouse_1 stock level low?", "expected_intent": "rca", "expected_node_id": "warehouse_1", "category": "rca"},
    {"id": "R14", "query": "What factors are affecting Tata Steel deliveries?", "expected_intent": "rca", "expected_node_id": "vendor_1", "category": "rca"},
    {"id": "R15", "query": "Why is Cyclone Dana impacting the supply chain?", "expected_intent": "rca", "expected_node_id": "event_1", "category": "rca"},
    {"id": "R16", "query": "What if port_1 becomes operational?", "expected_intent": "simulate", "expected_node_id": "port_1", "category": "simulate"},
    {"id": "R17", "query": "Simulate route_2 being restored to active", "expected_intent": "simulate", "expected_node_id": "route_2", "category": "simulate"},
    {"id": "R18", "query": "What happens if Mumbai Plant capacity drops to 50%?", "expected_intent": "simulate", "expected_node_id": "factory_1", "category": "simulate"},
    {"id": "R19", "query": "What if we reroute through Chennai Port instead?", "expected_intent": "simulate", "expected_node_id": "port_2", "category": "simulate"},
    {"id": "R20", "query": "What would happen if Kolkata Plant goes fully offline?", "expected_intent": "simulate", "expected_node_id": "factory_3", "category": "simulate"},
    {"id": "R21", "query": "Simulate warehouse_1 stock reaching 800 units", "expected_intent": "simulate", "expected_node_id": "warehouse_1", "category": "simulate"},
    {"id": "R22", "query": "What if JSW Steel reliability drops to 0.7?", "expected_intent": "simulate", "expected_node_id": "vendor_3", "category": "simulate"},
    {"id": "R23", "query": "Fix port_1 status to operational", "expected_intent": "action", "expected_node_id": "port_1", "category": "action"},
    {"id": "R24", "query": "Change route_2 status to active", "expected_intent": "action", "expected_node_id": "route_2", "category": "action"},
    {"id": "R25", "query": "Execute restock at Delhi Hub to 600 units", "expected_intent": "action", "expected_node_id": "warehouse_1", "category": "action"},
    {"id": "R26", "query": "Set Kolkata Plant status to operational", "expected_intent": "action", "expected_node_id": "factory_3", "category": "action"},
    {"id": "R27", "query": "Update Tata Steel SLA adherence to 95", "expected_intent": "action", "expected_node_id": "vendor_1", "category": "action"},
    {"id": "R28", "query": "Activate the backup rail route route_3", "expected_intent": "action", "expected_node_id": "route_3", "category": "action"},
    {"id": "R29", "query": "What is the late delivery penalty under the Tata Steel contract?", "expected_intent": "document", "expected_node_id": "unknown", "category": "document"},
    {"id": "R30", "query": "What is the SOP for handling a cyclone?", "expected_intent": "document", "expected_node_id": "unknown", "category": "document"},
    {"id": "R31", "query": "What is the reorder threshold for warehouses?", "expected_intent": "document", "expected_node_id": "unknown", "category": "document"},
    {"id": "R32", "query": "What are the escalation steps for a high severity incident?", "expected_intent": "document", "expected_node_id": "unknown", "category": "document"},
    {"id": "R33", "query": "What is the force majeure clause in the vendor contract?", "expected_intent": "document", "expected_node_id": "unknown", "category": "document"},
    {"id": "R34", "query": "How do I file an insurance claim for damaged inventory?", "expected_intent": "document", "expected_node_id": "unknown", "category": "document"},
    {"id": "R35", "query": "What is the backup route policy when sea routes are disrupted?", "expected_intent": "document", "expected_node_id": "unknown", "category": "document"},
    {"id": "R36", "query": "What are the quality acceptance criteria for steel shipments?", "expected_intent": "document", "expected_node_id": "unknown", "category": "document"},
    {"id": "R37", "query": "Tell me about port_1 and also the penalty clauses", "expected_intent": "query", "expected_node_id": "port_1", "category": "edge_multi_intent"},
    {"id": "R38", "query": "What is the weather like in Mumbai?", "expected_intent": "document", "expected_node_id": "unknown", "category": "edge_ood"},
    {"id": "R39", "query": "Hello", "expected_intent": "document", "expected_node_id": "unknown", "category": "edge_ambiguous"},
    {"id": "R40", "query": "Compare Vizag and Chennai ports", "expected_intent": "query", "expected_node_id": "port_1", "category": "edge_multi_entity"},
]


ROUTER_MODELS = {
    "ollama": [
        "llama3.1:8b",
        "mistral:7b",
        "phi3:3.8b",
        "gemma2:9b",
    ],
    "groq": [
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    "openrouter": [
        "meta-llama/llama-3.1-8b-instruct",
        "mistralai/mistral-7b-instruct",
        "microsoft/phi-3-mini-128k-instruct",
        "google/gemma-2-9b-it",
        "mistralai/mixtral-8x7b-instruct",
    ],
}



EMBEDDING_MODELS = {
    "sentence_transformers": [
        "all-MiniLM-L6-v2",
        "BAAI/bge-small-en-v1.5",
        "BAAI/bge-large-en-v1.5",
    ],
    "ollama": [
        "nomic-embed-text",
    ],
    "openrouter": [
        "openai/text-embedding-3-small",
        "openai/text-embedding-3-large",
    ],
}




def call_ollama_router(query: str, model: str, prompt_template: str) -> Tuple[str, float]:
    prompt = prompt_template.replace("{query}", query)
    t0 = time.perf_counter()
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    latency = time.perf_counter() - t0
    resp.raise_for_status()
    return resp.json()["response"].strip(), latency


def call_groq_router(query: str, model: str, prompt_template: str) -> Tuple[str, float]:


    prompt = prompt_template.replace("{query}", query)
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    latency = time.perf_counter() - t0
    return resp.choices[0].message.content.strip(), latency


def call_openrouter_router(query: str, model: str, prompt_template: str) -> Tuple[str, float]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    prompt = prompt_template.replace("{query}", query)
    t0 = time.perf_counter()
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0},
        timeout=120,
    )
    latency = time.perf_counter() - t0
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip(), latency


MODEL_EQUIVALENTS = {
    "llama3.1:8b":              {"groq": "llama-3.1-8b-instant",             "openrouter": "meta-llama/llama-3.1-8b-instruct"},
    "llama-3.1-8b-instant":     {"ollama": "llama3.1:8b",                    "openrouter": "meta-llama/llama-3.1-8b-instruct"},
    "meta-llama/llama-3.1-8b-instruct": {"ollama": "llama3.1:8b",           "groq": "llama-3.1-8b-instant"},
    "mistral:7b":               {"groq": None,                               "openrouter": "mistralai/mistral-7b-instruct"},
    "mistralai/mistral-7b-instruct": {"ollama": "mistral:7b",               "groq": None},
    "phi3:3.8b":                {"groq": None,                               "openrouter": "microsoft/phi-3-mini-128k-instruct"},
    "microsoft/phi-3-mini-128k-instruct": {"ollama": "phi3:3.8b",           "groq": None},
    "gemma2:9b":                {"groq": "gemma2-9b-it",                     "openrouter": "google/gemma-2-9b-it"},
    "gemma2-9b-it":             {"ollama": "gemma2:9b",                      "openrouter": "google/gemma-2-9b-it"},
    "google/gemma-2-9b-it":     {"ollama": "gemma2:9b",                      "groq": "gemma2-9b-it"},
    "mixtral-8x7b-32768":       {"ollama": None,                             "openrouter": "mistralai/mixtral-8x7b-instruct"},
    "mistralai/mixtral-8x7b-instruct": {"ollama": None,                     "groq": "mixtral-8x7b-32768"},
}

BACKEND_CALL_FNS = {
    "ollama": call_ollama_router,
    "groq": call_groq_router,
    "openrouter": call_openrouter_router,
}

FALLBACK_ORDER = ["ollama", "groq", "openrouter"]


def call_router_with_fallback(
    query: str, model: str, backend: str, prompt_template: str,
) -> Tuple[str, float, str]:
    """Try primary backend, then fallback chain. Returns (raw, latency, actual_backend)."""
    backends_to_try = [backend] + [b for b in FALLBACK_ORDER if b != backend]

    last_err = None
    for try_backend in backends_to_try:
        if try_backend == backend:
            try_model = model
        else:
            equiv = MODEL_EQUIVALENTS.get(model, {})
            try_model = equiv.get(try_backend)
            if not try_model:
                continue

        if try_backend == "groq" and not os.environ.get("GROQ_API_KEY"):
            continue
        if try_backend == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
            continue

        call_fn = BACKEND_CALL_FNS[try_backend]
        try:
            raw, lat = call_fn(query, try_model, prompt_template)
            if try_backend != backend:
                print(f"[fb->{try_backend}]", end="", flush=True)
            return raw, lat, try_backend
        except requests.exceptions.ConnectionError:
            last_err = f"{try_backend} unreachable"
            continue
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower():
                last_err = f"{try_backend} rate limited"
                if try_backend == "groq":
                    time.sleep(1)
                continue
            if "not found" in err_str.lower() or "does not exist" in err_str.lower():
                last_err = f"{try_backend}/{try_model} not available"
                continue
            raise

    raise RuntimeError(f"All backends failed for {model}: {last_err}")


def _evaluate_router_response(
    raw: str,
    expected_intent: str,
    expected_node_id: str,
) -> Dict[str, Any]:
    parsed = _parse_llm_response(raw)
    if parsed is None:
        return {
            "parsed": False,
            "intent_correct": False,
            "entity_correct": False,
            "combined_correct": False,
            "got_intent": None,
            "got_node_id": None,
        }
    got_intent = parsed["intent"]
    got_node_id = parsed["node_id"]
    intent_ok = got_intent == expected_intent
    entity_ok = got_node_id == expected_node_id
    return {
        "parsed": True,
        "intent_correct": intent_ok,
        "entity_correct": entity_ok,
        "combined_correct": intent_ok and entity_ok,
        "got_intent": got_intent,
        "got_node_id": got_node_id,
    }


def run_router_benchmark(
    models: List[Tuple[str, str, Callable]],  
    dataset: List[Dict],
    prompt: str,
    n_runs: int = 3,
) -> List[Dict[str, Any]]:
    all_results = []

    for backend, model_name, call_fn in models:
        label = f"{backend}/{model_name}"
        print(f"\n  [{label}] ", end="", flush=True)

        per_query: List[Dict] = []
        latencies: List[float] = []
        consistency_scores: List[float] = []
        skipped = False

        for qi, tc in enumerate(dataset):
            run_results = []
            for run_i in range(n_runs):
                try:
                    raw, lat, actual_backend = call_router_with_fallback(
                        tc["query"], model_name, backend, prompt,
                    )
                    ev = _evaluate_router_response(raw, tc["expected_intent"], tc["expected_node_id"])
                    ev["latency"] = lat
                    ev["raw"] = raw[:200]
                    ev["actual_backend"] = actual_backend
                    run_results.append(ev)
                    latencies.append(lat)
                except RuntimeError as e:
                    err_msg = str(e)
                    if "All backends failed" in err_msg:
                        print(f"\n    [SKIP] {label} — {err_msg}")
                        skipped = True
                        break
                    run_results.append({
                        "parsed": False, "intent_correct": False, "entity_correct": False,
                        "combined_correct": False, "got_intent": None, "got_node_id": None,
                        "latency": 0, "raw": f"ERROR: {err_msg[:100]}",
                    })
                except Exception as e:
                    err_msg = str(e)
                    run_results.append({
                        "parsed": False, "intent_correct": False, "entity_correct": False,
                        "combined_correct": False, "got_intent": None, "got_node_id": None,
                        "latency": 0, "raw": f"ERROR: {err_msg[:100]}",
                    })

                if backend == "groq" and run_i < n_runs - 1:
                    time.sleep(0.5)

            if skipped:
                break

            if run_results:
                tuples = [(r["got_intent"], r["got_node_id"]) for r in run_results]
                mode_count = Counter(tuples).most_common(1)[0][1]
                consistency_scores.append(mode_count / len(tuples))

            per_query.append({
                "test_id": tc["id"],
                "category": tc["category"],
                "runs": run_results,
                "first_run": run_results[0] if run_results else None,
            })

            if (qi + 1) % 10 == 0:
                print(f"{qi + 1}", end="", flush=True)
            else:
                print(".", end="", flush=True)

            if backend == "groq":
                time.sleep(0.5)

        if skipped:
            all_results.append({"label": label, "backend": backend, "model": model_name, "skipped": True})
            continue

        first_runs = [pq["first_run"] for pq in per_query if pq["first_run"]]
        n_total = len(first_runs)
        if n_total == 0:
            all_results.append({"label": label, "backend": backend, "model": model_name, "skipped": True})
            continue

        json_parse_rate = sum(1 for r in first_runs if r["parsed"]) / n_total
        intent_acc = sum(1 for r in first_runs if r["intent_correct"]) / n_total
        entity_acc = sum(1 for r in first_runs if r["entity_correct"]) / n_total
        combined_acc = sum(1 for r in first_runs if r["combined_correct"]) / n_total

        non_doc = [(pq, r) for pq, r in zip(per_query, first_runs) if pq["category"] != "document"]
        entity_acc_nondoc = (
            sum(1 for _, r in non_doc if r["entity_correct"]) / len(non_doc)
            if non_doc else 0.0
        )

        lat_arr = np.array(latencies) if latencies else np.array([0.0])
        consistency = float(np.mean(consistency_scores)) if consistency_scores else 0.0

        failures = []
        for pq in per_query:
            r = pq["first_run"]
            if r and not r["combined_correct"]:
                failures.append({
                    "id": pq["test_id"],
                    "category": pq["category"],
                    "got_intent": r["got_intent"],
                    "got_node_id": r["got_node_id"],
                })

        result = {
            "label": label,
            "backend": backend,
            "model": model_name,
            "skipped": False,
            "n_queries": n_total,
            "n_runs": n_runs,
            "intent_accuracy": round(intent_acc, 3),
            "entity_accuracy": round(entity_acc, 3),
            "entity_accuracy_nondoc": round(entity_acc_nondoc, 3),
            "combined_accuracy": round(combined_acc, 3),
            "json_parse_rate": round(json_parse_rate, 3),
            "consistency": round(consistency, 3),
            "latency_p50": round(float(np.percentile(lat_arr, 50)), 3),
            "latency_p95": round(float(np.percentile(lat_arr, 95)), 3),
            "latency_p99": round(float(np.percentile(lat_arr, 99)), 3),
            "failures": failures,
            "per_query": per_query,
        }
        all_results.append(result)
        print(f" done (intent={intent_acc:.2f} entity={entity_acc:.2f} combined={combined_acc:.2f})")

    return all_results


def generate_router_report(results: List[Dict]) -> str:
    lines = []
    lines.append("# PART 1: ROUTER MODEL COMPARISON\n")

    active = [r for r in results if not r.get("skipped")]
    skipped = [r for r in results if r.get("skipped")]

    if skipped:
        lines.append(f"Skipped models: {', '.join(r['label'] for r in skipped)}\n")

    if not active:
        lines.append("No router models were benchmarked.\n")
        return "\n".join(lines)

    # Table header
    header = f"{'Model':<30} | {'Intent':>6} | {'Entity':>6} | {'Ent-ND':>6} | {'Combined':>8} | {'JSON%':>5} | {'Consist':>7} | {'p50':>6} | {'p95':>6}"
    lines.append(header)
    lines.append("-" * len(header))

    for r in active:
        lines.append(
            f"{r['label']:<30} | {r['intent_accuracy']:>6.3f} | {r['entity_accuracy']:>6.3f} | "
            f"{r['entity_accuracy_nondoc']:>6.3f} | {r['combined_accuracy']:>8.3f} | "
            f"{r['json_parse_rate']:>5.3f} | {r['consistency']:>7.3f} | "
            f"{r['latency_p50']:>5.1f}s | {r['latency_p95']:>5.1f}s"
        )

    best = max(active, key=lambda r: r["combined_accuracy"])
    lines.append(f"\nBEST ROUTER: {best['label']} (combined={best['combined_accuracy']:.3f})\n")

    if best["failures"]:
        lines.append(f"PER-QUERY FAILURES ({best['label']}):")
        for f in best["failures"]:
            lines.append(f"  {f['id']} [{f['category']}] Got intent={f['got_intent']}, node_id={f['got_node_id']}")
    else:
        lines.append("No failures for best model.")

    lines.append("")
    return "\n".join(lines)


def embed_with_sentence_transformer(texts: List[str], model_name: str) -> np.ndarray:
    
    model = SentenceTransformer(model_name)
    return model.encode(texts, show_progress_bar=False)


def embed_with_ollama(texts: List[str], model: str) -> np.ndarray:
    resp = requests.post(
        "http://localhost:11434/api/embed",
        json={"model": model, "input": texts},
        timeout=120,
    )
    resp.raise_for_status()
    return np.array(resp.json()["embeddings"])


def embed_with_openrouter(texts: List[str], model: str) -> np.ndarray:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    resp = requests.post(
        "https://openrouter.ai/api/v1/embeddings",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "input": texts},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    data.sort(key=lambda x: x["index"])
    return np.array([d["embedding"] for d in data])


def build_test_vector_store(
    chunks: List[Dict],
    embed_fn: Callable[[List[str]], np.ndarray],
    dim: int,
    collection_name: str = "benchmark_test",
) -> "QdrantClient":
   


    texts = [c["text"] for c in chunks]
    embeddings = embed_fn(texts)

    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings[i].tolist(),
            payload={"text": c["text"], "source": c["source"], "section": c["section"]},
        )
        for i, c in enumerate(chunks)
    ]
    client.upsert(collection_name=collection_name, points=points)
    return client


def search_custom_store(
    query: str,
    client: "QdrantClient",
    embed_fn: Callable[[List[str]], np.ndarray],
    collection_name: str = "benchmark_test",
    top_k: int = 3,
) -> List[Dict]:
    q_emb = embed_fn([query])[0]
    results = client.query_points(
        collection_name=collection_name,
        query=q_emb.tolist(),
        limit=top_k,
    )
    return [
        {
            "text": p.payload["text"],
            "source": p.payload["source"],
            "section": p.payload["section"],
            "score": p.score,
        }
        for p in results.points
    ]


def _hit_rate(chunks: List[Dict], expected_sources: List[str], k: int = 3) -> float:
    if not expected_sources:
        return 1.0
    retrieved = {c["source"] for c in chunks[:k]}
    return 1.0 if any(s in retrieved for s in expected_sources) else 0.0


def _mrr(chunks: List[Dict], expected_sources: List[str]) -> float:
    if not expected_sources:
        return 1.0
    for rank, c in enumerate(chunks, start=1):
        if c["source"] in expected_sources:
            return 1.0 / rank
    return 0.0


def run_embedding_benchmark(
    models: List[Tuple[str, str]],  # (backend, model_name)
    dataset: List[Dict],
    chunks: List[Dict],
) -> List[Dict[str, Any]]:
    # Filter to answerable cases only
    answerable = [tc for tc in dataset if tc.get("expected_sources")]

    all_results = []

    for backend, model_name in models:
        label = f"{backend}/{model_name}"
        print(f"\n  [{label}] ", end="", flush=True)

     
        if backend == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
            print("SKIP — OPENROUTER_API_KEY not set")
            all_results.append({"label": label, "backend": backend, "model": model_name, "skipped": True})
            continue

        try:
            
            t_build_start = time.perf_counter()

            if backend == "sentence_transformers":
                
                client, st_model = build_vector_store(chunks, model_name=model_name)

                def _search(q: str, top_k: int = 3) -> List[Dict]:
                    q_emb = st_model.encode(q)
                    results = client.query_points(
                        collection_name="supply_chain_docs",
                        query=q_emb.tolist(),
                        limit=top_k,
                    )
                    return [
                        {"text": p.payload["text"], "source": p.payload["source"],
                         "section": p.payload["section"], "score": p.score}
                        for p in results.points
                    ]
            elif backend == "ollama":
                test_emb = embed_with_ollama(["test"], model_name)
                dim = test_emb.shape[1]
                embed_fn = lambda texts: embed_with_ollama(texts, model_name)
                custom_client = build_test_vector_store(chunks, embed_fn, dim)

                def _search(q: str, top_k: int = 3) -> List[Dict]:
                    return search_custom_store(q, custom_client, embed_fn, top_k=top_k)
            elif backend == "openrouter":
                test_emb = embed_with_openrouter(["test"], model_name)
                dim = test_emb.shape[1]
                embed_fn = lambda texts: embed_with_openrouter(texts, model_name)
                custom_client = build_test_vector_store(chunks, embed_fn, dim)

                def _search(q: str, top_k: int = 3) -> List[Dict]:
                    return search_custom_store(q, custom_client, embed_fn, top_k=top_k)
            else:
                print(f"SKIP — unknown backend '{backend}'")
                all_results.append({"label": label, "backend": backend, "model": model_name, "skipped": True})
                continue

            build_time = time.perf_counter() - t_build_start
            print(f"indexed ({build_time:.1f}s) ", end="", flush=True)

        except requests.exceptions.ConnectionError:
            if backend == "ollama" and os.environ.get("OPENROUTER_API_KEY"):
                # Fallback: try OpenRouter embedding equivalent
                or_equiv = {"nomic-embed-text": "openai/text-embedding-3-small"}
                or_model = or_equiv.get(model_name)
                if or_model:
                    try:
                        print(f"[fb->openrouter/{or_model}] ", end="", flush=True)
                        test_emb = embed_with_openrouter(["test"], or_model)
                        dim = test_emb.shape[1]
                        embed_fn = lambda texts: embed_with_openrouter(texts, or_model)
                        custom_client = build_test_vector_store(chunks, embed_fn, dim)

                        def _search(q: str, top_k: int = 3) -> List[Dict]:
                            return search_custom_store(q, custom_client, embed_fn, top_k=top_k)

                        build_time = time.perf_counter() - t_build_start
                        print(f"indexed ({build_time:.1f}s) ", end="", flush=True)
                    except Exception as e2:
                        print(f"SKIP — Ollama not reachable, OpenRouter fallback failed: {e2}")
                        all_results.append({"label": label, "backend": backend, "model": model_name, "skipped": True})
                        continue
                else:
                    print("SKIP — Ollama not reachable")
                    all_results.append({"label": label, "backend": backend, "model": model_name, "skipped": True})
                    continue
            else:
                print("SKIP — Ollama not reachable")
                all_results.append({"label": label, "backend": backend, "model": model_name, "skipped": True})
                continue
        except Exception as e:
            print(f"SKIP — {e}")
            all_results.append({"label": label, "backend": backend, "model": model_name, "skipped": True})
            continue

        hit_rates = []
        mrrs = []
        top1_scores = []
        latencies = []

        for tc in answerable:
            t0 = time.perf_counter()
            results = _search(tc["question"], top_k=tc.get("top_k", 5))
            lat = time.perf_counter() - t0
            latencies.append(lat)

            hr = _hit_rate(results, tc["expected_sources"], k=3)
            mrr_val = _mrr(results, tc["expected_sources"])
            top1 = results[0]["score"] if results else 0.0

            hit_rates.append(hr)
            mrrs.append(mrr_val)
            top1_scores.append(top1)

        lat_arr = np.array(latencies)
        result = {
            "label": label,
            "backend": backend,
            "model": model_name,
            "skipped": False,
            "n_queries": len(answerable),
            "hit_rate_at_3": round(float(np.mean(hit_rates)), 3),
            "mrr": round(float(np.mean(mrrs)), 3),
            "avg_top1_score": round(float(np.mean(top1_scores)), 3),
            "latency_p50": round(float(np.percentile(lat_arr, 50)), 3),
            "latency_p95": round(float(np.percentile(lat_arr, 95)), 3),
        }
        all_results.append(result)
        print(f"done (HR@3={result['hit_rate_at_3']:.3f} MRR={result['mrr']:.3f})")

    return all_results


def generate_embedding_report(results: List[Dict]) -> str:
    lines = []
    lines.append("# PART 2: EMBEDDING MODEL COMPARISON\n")

    active = [r for r in results if not r.get("skipped")]
    skipped = [r for r in results if r.get("skipped")]

    if skipped:
        lines.append(f"Skipped models: {', '.join(r['label'] for r in skipped)}\n")

    if not active:
        lines.append("No embedding models were benchmarked.\n")
        return "\n".join(lines)

    header = f"{'Model':<40} | {'HR@3':>5} | {'MRR':>5} | {'AvgTop1':>7} | {'p50':>6} | {'p95':>6}"
    lines.append(header)
    lines.append("-" * len(header))

    for r in active:
        lines.append(
            f"{r['label']:<40} | {r['hit_rate_at_3']:>5.3f} | {r['mrr']:>5.3f} | "
            f"{r['avg_top1_score']:>7.3f} | {r['latency_p50']:>5.3f}s | {r['latency_p95']:>5.3f}s"
        )

    best = max(active, key=lambda r: r["hit_rate_at_3"])
    lines.append(f"\nBEST EMBEDDING: {best['label']} (HR@3={best['hit_rate_at_3']:.3f}, MRR={best['mrr']:.3f})")
    lines.append("")
    return "\n".join(lines)



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Model benchmarking harness for networkx-mua")
    sub = p.add_subparsers(dest="command", required=True)

    rtr = sub.add_parser("router", help="Benchmark router models")
    rtr.add_argument("--backends", nargs="+", choices=["ollama", "groq", "openrouter"],
                      default=["ollama", "groq", "openrouter"])
    rtr.add_argument("--models", nargs="+", default=None, help="Specific model names to test")
    rtr.add_argument("--runs", type=int, default=3, help="Runs per query for consistency (default: 3)")
    rtr.add_argument("--output", default=None, help="Save report to this markdown file")

    emb = sub.add_parser("embedding", help="Benchmark embedding models")
    emb.add_argument("--backends", nargs="+", choices=["sentence_transformers", "ollama", "openrouter"],
                      default=["sentence_transformers", "ollama", "openrouter"])
    emb.add_argument("--models", nargs="+", default=None, help="Specific model names to test")
    emb.add_argument("--output", default=None, help="Save report to this markdown file")

    a = sub.add_parser("all", help="Run all benchmarks")
    a.add_argument("--output", default=None, help="Save combined report to this markdown file")
    a.add_argument("--runs", type=int, default=3, help="Router runs per query (default: 3)")

    return p.parse_args()


def _resolve_router_models(
    backends: List[str],
    model_filter: Optional[List[str]],
) -> List[Tuple[str, str, Callable]]:
    models = []
    for backend in backends:
        call_fn = BACKEND_CALL_FNS[backend]
        for m in ROUTER_MODELS.get(backend, []):
            if model_filter and m not in model_filter:
                continue
            models.append((backend, m, call_fn))
    return models


def _resolve_embedding_models(
    backends: List[str],
    model_filter: Optional[List[str]],
) -> List[Tuple[str, str]]:
    models = []
    for backend in backends:
        for m in EMBEDDING_MODELS.get(backend, []):
            if model_filter and m not in model_filter:
                continue
            models.append((backend, m))
    return models


def main() -> None:
    args = parse_args()
    output_path = getattr(args, "output", None)
    report_parts = []
    raw_data = {}

    print(f"Working directory: {os.getcwd()}")
    print(f"Command: {args.command}")

    # Backend availability check
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        ollama_status = "reachable"
    except Exception:
        ollama_status = "not reachable"
    groq_status = "API key set" if os.environ.get("GROQ_API_KEY") else "no API key"
    or_status = "API key set" if os.environ.get("OPENROUTER_API_KEY") else "no API key"
    print(f"[backends] ollama: {ollama_status} | groq: {groq_status} | openrouter: {or_status}")

    if args.command in ("router", "all"):
        print("\n" + "=" * 70)
        print("ROUTER BENCHMARK")
        print("=" * 70)

        backends = args.backends if args.command == "router" else ["ollama", "groq", "openrouter"]
        model_filter = getattr(args, "models", None)
        n_runs = args.runs

        router_models = _resolve_router_models(backends, model_filter)
        print(f"Models: {[f'{b}/{m}' for b, m, _ in router_models]}")
        print(f"Dataset: {len(ROUTER_DATASET)} queries, {n_runs} runs each")

        router_results = run_router_benchmark(
            router_models, ROUTER_DATASET, ROUTER_ENTITY_PROMPT, n_runs=n_runs,
        )

        report = generate_router_report(router_results)
        print("\n" + report)
        report_parts.append(report)
        raw_data["router"] = [
            {k: v for k, v in r.items() if k != "per_query"} for r in router_results
        ]

    if args.command in ("embedding", "all"):
        print("\n" + "=" * 70)
        print("EMBEDDING BENCHMARK")
        print("=" * 70)

        backends = args.backends if args.command == "embedding" else ["sentence_transformers", "ollama", "openrouter"]
        model_filter = getattr(args, "models", None)

        emb_models = _resolve_embedding_models(backends, model_filter)
        print(f"Models: {[f'{b}/{m}' for b, m in emb_models]}")

        docs_folder = os.path.join(SCRIPT_DIR, "docs_folder")
        print(f"Loading chunks from: {docs_folder}")
        chunks = load_and_chunk_docs(docs_folder)
        print(f"Loaded {len(chunks)} chunks")

        print(f"Eval dataset: {len(EVAL_DATASET)} queries")

        emb_results = run_embedding_benchmark(emb_models, EVAL_DATASET, chunks)

        report = generate_embedding_report(emb_results)
        print("\n" + report)
        report_parts.append(report)
        raw_data["embedding"] = emb_results

    if output_path:
        out_md = os.path.join(SCRIPT_DIR, output_path)
        with open(out_md, "w", encoding="utf-8") as f:
            f.write("\n\n".join(report_parts))
        print(f"\nReport saved to: {out_md}")

    json_path = os.path.join(SCRIPT_DIR, "benchmark_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=2, default=str)
    print(f"Raw data saved to: {json_path}")


if __name__ == "__main__":
    main()
