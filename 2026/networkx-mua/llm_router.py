import json
import os
import re
from typing import Any, Dict, Optional, TypedDict

import requests
from dotenv import load_dotenv
from groq import Groq

from entity_resolver import (
    build_catalog_string,
    build_entity_index,
    keyword_extract_node_id,
    resolve_entity,
)
from knowledge_graph import build_supply_chain_graph

load_dotenv()


class AgentState(TypedDict):
    query: str
    intent: str
    node_id: str
    changes: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    approval: Optional[bool]


# ---------------------------------------------------------------------------
# Module-level singletons — built once at import time (~500 tokens in prompt)
# ---------------------------------------------------------------------------
_G_catalog = build_supply_chain_graph()
_entity_index: Dict[str, str] = build_entity_index(_G_catalog)
_catalog_string: str = build_catalog_string(_G_catalog)

# ---------------------------------------------------------------------------
# Prompt template — {catalog} is filled once; {query} filled per call.
# ---------------------------------------------------------------------------
_ROUTER_PROMPT_TEMPLATE = """You are a query classifier and entity extractor for a supply chain management system.

NODE CATALOG:
{catalog}

Given a user query, return a JSON object with exactly these fields:
- "intent": one of ["query", "rca", "simulate", "action", "document"]
- "node_id": the node_id from the catalog the user is asking about, OR "unknown"
- "changes": dict of field→value pairs if a state change is implied, OR null

INTENT DEFINITIONS:
1. query      — check current status/state of a supply chain node
2. rca        — understand why something is happening / root cause
3. simulate   — explore hypothetical "what if" scenarios
4. action     — execute or fix something in the system
5. document   — policies, contracts, procedures, regulations, thresholds, SOP

NOTE on query vs document: Use query ONLY for live real-time status of a named node.
Policy values, contractual thresholds, SOP-defined numbers → always document.

NODE RESOLUTION RULES:
- Match by node_id directly ("port_1" → "port_1")
- Match by name ("Vizag Port" → "port_1", "Tata Steel" → "vendor_1")
- Match by location ("Visakhapatnam" → "port_1", "Mumbai" → "factory_1")
- "Vizag" is an alias for Visakhapatnam → "port_1"
- "document" intent → node_id is always "unknown"
- Truly ambiguous or no node referenced → "unknown"

Return ONLY valid JSON. No explanation. No markdown fences.
Examples:
{{"intent": "query", "node_id": "port_1", "changes": null}}
{{"intent": "simulate", "node_id": "port_1", "changes": {{"status": "operational"}}}}
{{"intent": "document", "node_id": "unknown", "changes": null}}

User query: {{query}}
JSON:"""

ROUTER_ENTITY_PROMPT: str = _ROUTER_PROMPT_TEMPLATE.format(catalog=_catalog_string)

VALID_INTENTS = {"query", "rca", "simulate", "action", "document"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_llm_response(raw: str) -> Optional[Dict]:
    """Parse JSON from LLM response; validate and normalise fields."""
    raw = raw.strip()

    # Try direct parse first
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Extract first JSON object with regex fallback
        m = re.search(r"\{.*?\}", raw, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    intent = str(data.get("intent", "")).lower()
    if intent not in VALID_INTENTS:
        return None

    node_id = str(data.get("node_id", "unknown")).lower()
    # If LLM returned something unrecognised, try to resolve it
    if node_id not in _entity_index and node_id != "unknown":
        node_id = resolve_entity(node_id, _entity_index)

    changes = data.get("changes") or {}
    if not isinstance(changes, dict):
        changes = {}

    return {"intent": intent, "node_id": node_id, "changes": changes}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

def llm_router(state: Dict) -> Dict:
    """Route query through Ollama → Groq → keyword_router fallback chain.

    Returns {"intent": str, "node_id": str, "changes": dict}.
    """
    query = state["query"]
    prompt = ROUTER_ENTITY_PROMPT.replace("{query}", query)

    # --- Ollama ---
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.1:8b", "prompt": prompt, "stream": False},
            timeout=30,
        )
        raw = response.json()["response"].strip()
        result = _parse_llm_response(raw)
        if result:
            return result
        print(f"[Ollama] Unparseable response: {raw[:120]}, falling back...")
    except requests.exceptions.RequestException as e:
        print(f"[Ollama] Failed: {e}")

    # --- Groq ---
    try:
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        result = _parse_llm_response(raw)
        if result:
            return result
        print(f"[Groq] Unparseable response: {raw[:120]}, falling back...")
    except Exception as e:
        print(f"[Groq] Failed: {e}")

    print("[Fallback] Using keyword router")
    return keyword_router({"query": query})


def keyword_router(state: Dict) -> Dict:
    """Keyword-based fallback router.

    Returns {"intent": str, "node_id": str, "changes": dict}.
    """
    query = state["query"].lower()

    if "fix" in query or "execute" in query or "change" in query:
        intent = "action"
    elif "what if" in query or "simulate" in query:
        intent = "simulate"
    elif "why" in query or "root cause" in query:
        intent = "rca"
    elif "status" in query or "state" in query:
        intent = "query"
    elif any(
        kw in query
        for kw in [
            "penalty", "contract", "sla", "clause", "terms",
            "protocol", "procedure", "sop", "how do i", "what do i do",
            "policy", "threshold", "reorder",
            "force majeure", "covered", "allowed", "requirement",
            "escalation", "steps", "when", "what happens",
        ]
    ):
        intent = "document"
    else:
        intent = "document"

    node_id = keyword_extract_node_id(query, _entity_index)
    return {"intent": intent, "node_id": node_id, "changes": {}}


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_queries = [
        "What is the status of port_1?",
        "How is Vizag Port doing?",
        "What about the Delhi hub?",
        "Why is Tata Steel delayed?",
        "Fix the port",
        "What is the late delivery penalty?",
        "How do port and warehouse interact?",
        "Why is warehouse_1 struggling?",
        "What if port_1 becomes operational?",
        "Fix port_1 status to operational",
    ]

    for q in test_queries:
        result = llm_router({"query": q})
        print(f"Q: {q}")
        print(f"   intent={result['intent']}  node_id={result['node_id']}  changes={result['changes']}")
