import html
import json
import os
import re
import time
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import networkx as nx
import requests
import streamlit as st

from pageindex_client import PageIndexClient
from knowledge_graph import NodeType, build_supply_chain_graph
from agent_tools import (
    execute_action as _execute_action,
    find_root_cause as _find_root_cause,
    query_state as _query_state,
    simulate_change as _simulate_change,
)
from llm_router import keyword_router, llm_router
from retrieval import search_docs

st.set_page_config(
    page_title="Supply Chain Digital Twin",
    layout="wide",
)

if "graph" not in st.session_state:
    st.session_state.graph = build_supply_chain_graph()

if "history" not in st.session_state:
    st.session_state.history = []

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": (
                "I am ready. Ask me about node status, root cause, simulations, actions, or policy docs."
            ),
        }
    ]

if "last_llm_backend" not in st.session_state:
    st.session_state.last_llm_backend = "fallback"

if "pageindex_results" not in st.session_state:
    st.session_state.pageindex_results = []

if "pageindex_latency" not in st.session_state:
    st.session_state.pageindex_latency = None

if "pageindex_error" not in st.session_state:
    st.session_state.pageindex_error = None


def visualize_graph(G: nx.DiGraph, highlight_node: str = None):
    fig, ax = plt.subplots(figsize=(10, 6))

    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    type_colors = {
        NodeType.VENDOR: "#2F855A",
        NodeType.FACTORY: "#2B6CB0",
        NodeType.PRODUCT: "#B7791F",
        NodeType.ROUTE: "#6B46C1",
        NodeType.PORT: "#C53030",
        NodeType.WAREHOUSE: "#0F766E",
        NodeType.EVENT: "#BE185D",
        NodeType.UNKNOWN: "#64748B",
    }

    node_colors = []
    for node in G.nodes():
        node_data = G.nodes[node]
        node_type = node_data.get("type", NodeType.UNKNOWN)
        if isinstance(node_type, str):
            for nt in NodeType:
                if nt.value == node_type:
                    node_type = nt
                    break

        color = type_colors.get(node_type, "#64748B")
        if node == highlight_node:
            color = "#D97706"
        node_colors.append(color)

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=880, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color="#64748B", arrows=True, width=1.2, ax=ax)

    labels = {n: G.nodes[n].get("name", n)[:12] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=7, font_color="#0F172A", ax=ax)

    ax.set_axis_off()
    return fig


def handle_query(node_id: str) -> Dict[str, Any]:
    result = _query_state(st.session_state.graph, node_id)
    return {"type": "query", "node_id": node_id, "data": result}


def handle_rca(node_id: str) -> Dict[str, Any]:
    path = _find_root_cause(st.session_state.graph, node_id)
    return {"type": "rca", "node_id": node_id, "path": path}


def handle_simulate(node_id: str, changes: Dict) -> Dict[str, Any]:
    result = _simulate_change(st.session_state.graph, node_id, changes)
    return {"type": "simulate", "node_id": node_id, "data": result}


def handle_action(node_id: str, changes: Dict, approved: bool = False) -> Dict[str, Any]:
    if not approved:
        return {
            "type": "action",
            "status": "pending",
            "node_id": node_id,
            "changes": changes,
            "message": "Action requires approval",
        }

    result = _execute_action(st.session_state.graph, node_id, changes)
    return {"type": "action", "status": "executed", "data": result}


def handle_document(query: str) -> Dict[str, Any]:
    docs = search_docs(query, top_k=3)
    return {"type": "document", "query": query, "documents": docs}


def classify_intent(query: str) -> str:
    llm_result = llm_router({"query": query})
    if llm_result:
        return llm_result.get("intent", "query")

    kw_result = keyword_router({"query": query})
    return kw_result.get("intent", "query")


def extract_node_id(query: str) -> str:
    match = re.search(r"(warehouse|port|factory|vendor|product|route|event)_\d+", query.lower())
    return match.group(0) if match else ""


def extract_changes(query: str) -> Dict:
    changes = {}
    query_lower = query.lower()

    status_map = ["operational", "shutdown", "congested", "maintenance", "resolved", "active"]
    for status in status_map:
        if status in query_lower:
            changes["status"] = status
            break

    capacity_match = re.search(r"capacity[:\s]*(\d+)", query_lower)
    if capacity_match:
        changes["capacity_pct"] = int(capacity_match.group(1))

    return changes


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return str(value)


def _compact_result(result: Dict[str, Any]) -> Dict[str, Any]:
    result_type = result.get("type")
    compact: Dict[str, Any] = {"type": result_type}
    if "node_id" in result:
        compact["node_id"] = result.get("node_id")

    if result_type == "query":
        compact["data"] = result.get("data", {})
    elif result_type == "rca":
        path_steps = []
        for step in result.get("path", []):
            if isinstance(step, dict):
                path_steps.append(
                    {
                        "id": step.get("id") or step.get("node_id"),
                        "name": step.get("name"),
                        "status": step.get("status"),
                    }
                )
            else:
                path_steps.append({"id": str(step)})
        compact["path"] = path_steps
    elif result_type == "simulate":
        data = result.get("data", {})
        compact["summary"] = {
            "original": data.get("original", {}),
            "simulated": data.get("simulated", {}),
            "newly_affected_count": len(data.get("newly_affected", [])),
            "no_longer_affected_count": len(data.get("no_longer_affected", [])),
        }
    elif result_type == "action":
        compact["status"] = result.get("status")
        compact["message"] = result.get("message")
        compact["changes"] = result.get("changes")
        compact["data"] = result.get("data")
    elif result_type == "document":
        docs = []
        for doc in result.get("documents", []):
            text = doc.get("text", "")
            docs.append(
                    {
                        "source": doc.get("source", ""),
                        "section": doc.get("section", ""),
                        "score": round(float(doc.get("score", 0.0) or 0.0), 3),
                        "text": (text[:260] + "...") if len(text) > 260 else text,
                    }
                )
        compact["documents"] = docs

    return compact


def _format_tree(node: Dict[str, Any], depth: int = 0, lines: Optional[list] = None) -> str:
    if lines is None:
        lines = []
    label = node.get("title") or node.get("name") or node.get("text") or node.get("summary") or "step"
    detail = node.get("reason") or node.get("description") or ""
    score = node.get("score")
    suffix = ""
    if score is not None:
        suffix += f" [score: {score}]"
    if detail:
        suffix += f" — {detail}"
    lines.append(("  " * depth) + f"- {label}{suffix}")
    for child in node.get("children", []) or []:
        _format_tree(child, depth + 1, lines)
    return "\n".join(lines)


def _fallback_answer(user_query: str, intent: str, result: Dict[str, Any]) -> str:
    if intent == "query":
        data = result.get("data") or {}
        if not data:
            return "I could not find that node in the graph. Try a valid id like `port_1` or `warehouse_1`."
        node_id = result.get("node_id", "node")
        name = data.get("name", node_id)
        status = data.get("status", "N/A")
        key_fields = []
        for key in ["throughput", "capacity_pct", "stock_level", "location", "severity", "priority"]:
            if key in data:
                key_fields.append(f"{key}: {data[key]}")
        extras = f"\n\nKey fields: {', '.join(key_fields)}." if key_fields else ""
        return f"`{node_id}` ({name}) is currently **{status}**.{extras}"

    if intent == "rca":
        lines = []
        for i, step in enumerate(result.get("path", []), 1):
            if isinstance(step, dict):
                node = step.get("id") or step.get("node_id") or f"step_{i}"
                name = step.get("name", node)
                status = step.get("status", "N/A")
            else:
                node = str(step)
                node_data = {}
                if node in st.session_state.graph.nodes:
                    node_data = dict(st.session_state.graph.nodes[node])
                name = node_data.get("name", node)
                status = node_data.get("status", "N/A")
            lines.append(f"{i}. `{node}` - **{name}** ({status})")
        if not lines:
            return "I could not build a root cause path for that query."
        return "Root cause path:\n\n" + "\n".join(lines)

    if intent == "simulate":
        data = result.get("data", {})
        original = data.get("original", {})
        simulated = data.get("simulated", {})
        newly = len(data.get("newly_affected", []))
        removed = len(data.get("no_longer_affected", []))
        return (
            "Simulation complete.\n\n"
            f"- Before status: **{original.get('status', 'N/A')}**\n"
            f"- After status: **{simulated.get('status', 'N/A')}**\n"
            f"- Newly affected nodes: **{newly}**\n"
            f"- No longer affected: **{removed}**"
        )

    if intent == "action":
        if result.get("status") == "pending":
            return (
                "I prepared the action but did not execute it yet.\n\n"
                "Use the **Approvals** panel to Approve or Reject."
            )
        if result.get("status") == "executed":
            data = result.get("data", {})
            node_id = data.get("node_id", result.get("node_id", "node"))
            return f"Action executed successfully for `{node_id}`."
        return "Action request processed."

    if intent == "document":
        docs = result.get("documents", [])
        if not docs:
            return "I could not find matching policy documents."
        top = docs[0]
        snippet = top.get("text", "")[:240]
        return (
            f"Top citation: **{top.get('source', 'Unknown source')}** "
            f"({top.get('section', 'N/A')}, score {float(top.get('score', 0) or 0):.3f})\n\n"
            f"{snippet}..."
        )

    return f"I processed your request: {user_query}"


def _call_response_llm(prompt: str) -> str:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
            },
            timeout=45,
        )
        response.raise_for_status()
        answer = response.json().get("response", "").strip()
        if answer:
            st.session_state.last_llm_backend = "ollama"
            return answer
    except Exception:
        pass

    try:
        from groq import Groq  # type: ignore

        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=400,
            )
            answer = (completion.choices[0].message.content or "").strip()
            if answer:
                st.session_state.last_llm_backend = "groq"
                return answer
    except Exception:
        pass

    st.session_state.last_llm_backend = "fallback"
    return ""


def generate_assistant_answer(user_query: str, intent: str, result: Dict[str, Any]) -> str:
    compact_payload = _json_safe(_compact_result(result))
    fallback = _fallback_answer(user_query, intent, result)

    prompt = f"""You are a supply-chain operations copilot.
You must answer the user based ONLY on the structured tool output.
If data is missing, say that directly.
Keep the response concise and operationally useful.
For document answers, cite source and section inline.
If an action is pending approval, explicitly ask the user to approve/reject.

User query:
{user_query}

Detected intent:
{intent}

Structured tool result:
{json.dumps(compact_payload, indent=2)}

Draft fallback answer:
{fallback}

Now provide the final answer in markdown.
"""
    llm_answer = _call_response_llm(prompt)
    if llm_answer:
        return llm_answer
    return fallback


def process_user_turn(user_query: str) -> None:
    clean_query = user_query.strip()
    if not clean_query:
        return

    st.session_state.chat_messages.append({"role": "user", "content": clean_query})

    intent = classify_intent(clean_query)
    node_id = extract_node_id(clean_query)
    changes = extract_changes(clean_query)

    start_time = time.time()
    if intent == "query":
        result = handle_query(node_id or "port_1")
    elif intent == "rca":
        result = handle_rca(node_id or "warehouse_1")
    elif intent == "simulate":
        result = handle_simulate(node_id or "port_1", changes or {"status": "operational"})
    elif intent == "action":
        st.session_state.pending_action = {
            "node_id": node_id or "port_1",
            "changes": changes or {"status": "operational"},
        }
        result = handle_action(node_id or "port_1", changes or {"status": "operational"}, approved=False)
    elif intent == "document":
        result = handle_document(clean_query)
    else:
        result = {"type": "error", "message": "Unknown intent"}

    latency = time.time() - start_time
    st.session_state.history.append(
        {
            "query": clean_query,
            "intent": intent,
            "result": result,
            "latency": latency,
        }
    )

    assistant_text = generate_assistant_answer(clean_query, intent, result)
    st.session_state.chat_messages.append({"role": "assistant", "content": assistant_text})


def inject_custom_css() -> None:
    st.markdown(
        """
<style>
    .stApp {
        background:
            radial-gradient(1200px 640px at 0% -5%, #E4EEFC 0%, transparent 56%),
            radial-gradient(1000px 500px at 100% 0%, #DAF2EC 0%, transparent 45%),
            linear-gradient(180deg, #F4F8FC 0%, #ECF2F8 100%);
        color: #0F172A;
    }

    .block-container {
        padding-top: 1.05rem;
        padding-bottom: 1.2rem;
        max-width: 1500px;
    }

    .hero-banner {
        border: 1px solid #D4E2EE;
        background: linear-gradient(130deg, #FFFFFF 0%, #EDF4FB 100%);
        border-radius: 16px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.07);
    }

    .hero-title {
        margin: 0;
        font-size: 1.65rem;
        letter-spacing: 0.01em;
    }

    .hero-subtitle {
        margin-top: 0.4rem;
        margin-bottom: 0;
        color: #475569;
        font-size: 0.95rem;
    }

    .intent-badge {
        display: inline-block;
        border: 1px solid;
        border-radius: 999px;
        padding: 0.15rem 0.64rem;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    .section-caption {
        color: #475569;
        font-size: 0.82rem;
        margin-top: -0.1rem;
    }

    [data-testid="stMetric"] {
        border: 1px solid #D4E2EE;
        background: #FFFFFF;
        border-radius: 12px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
        padding: 0.3rem 0.6rem;
    }

    [data-testid="stMetricLabel"] p {
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.66rem;
        color: #64748B;
    }

    [data-testid="stMetricValue"] {
        color: #0F172A;
        font-size: 1.35rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
        border: 1px solid #D4E2EE;
        background: rgba(255, 255, 255, 0.9);
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    }

    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 1px solid #B5C8DA;
        background: #F8FBFF;
    }

    .stSelectbox > div > div {
        border-radius: 10px;
        border: 1px solid #B5C8DA;
    }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid #AFC1D2;
        background: #FFFFFF;
        color: #1E293B;
        font-weight: 600;
        transition: all 0.18s ease;
    }

    .stButton > button:hover {
        border-color: #7A96B0;
        box-shadow: 0 3px 12px rgba(21, 40, 64, 0.12);
        transform: translateY(-1px);
    }

    .stButton > button[data-testid="baseButton-primary"] {
        border: none;
        background: linear-gradient(90deg, #0F766E 0%, #1D4ED8 100%);
        color: #FFFFFF;
    }

    .trace-card {
        border: 1px solid #D6E1EC;
        border-radius: 10px;
        padding: 0.55rem 0.6rem;
        margin-bottom: 0.5rem;
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
    }

    .trace-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.22rem;
    }

    .trace-intent {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        color: #0F172A;
    }

    .trace-latency {
        font-size: 0.72rem;
        color: #64748B;
    }

    .trace-query {
        font-size: 0.8rem;
        color: #334155;
        line-height: 1.3;
    }
</style>
        """,
        unsafe_allow_html=True,
    )

inject_custom_css()
st.markdown(
    """
<div class="hero-banner">
    <h1 class="hero-title">Supply Chain Digital Twin Agent</h1>
    <p class="hero-subtitle">
        Inspect node state, run root-cause analysis, simulate interventions, and manage action approvals from one control panel.
    </p>
</div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(4)
metric_cols[0].metric("Nodes", st.session_state.graph.number_of_nodes())
metric_cols[1].metric("Edges", st.session_state.graph.number_of_edges())
metric_cols[2].metric("Queries", len(st.session_state.history))
metric_cols[3].metric("Pending Actions", 1 if st.session_state.pending_action else 0)

st.markdown("")
col_chat, col_graph, col_sidebar = st.columns([2.2, 2.8, 1.4], gap="large")

with col_chat:
    with st.container(border=True):
        st.subheader("Supply Chain Copilot Chat")
        st.markdown(
            "<div class='section-caption'>Conversation-first workflow with tool-backed answers.</div>",
            unsafe_allow_html=True,
        )

        quick_prompts = [
            ("Status: port_1", "What is the status of port_1?"),
            ("RCA: warehouse_1", "Why is warehouse_1 affected?"),
            ("Simulate: port_1", "Simulate port_1 status operational"),
            ("Docs: penalties", "What is the penalty for late delivery?"),
        ]
        qp_cols = st.columns(2)
        for idx, (label, prompt) in enumerate(quick_prompts):
            with qp_cols[idx % 2]:
                if st.button(label, key=f"quick_prompt_{idx}", use_container_width=True):
                    process_user_turn(prompt)
                    st.rerun()

        st.caption(f"Response engine: `{st.session_state.last_llm_backend}`")
        for msg in st.session_state.chat_messages[-16:]:
            with st.chat_message(msg.get("role", "assistant")):
                st.markdown(msg.get("content", ""))

        chat_query = st.chat_input(
            "Ask about the supply chain (status, RCA, simulation, actions, docs)",
            key="chat_input",
        )
        if chat_query:
            process_user_turn(chat_query)
            st.rerun()

    with st.container(border=True):
        st.subheader("Approvals")
        if st.session_state.pending_action:
            st.warning("Action requires approval.")
            st.json(st.session_state.pending_action)

            col_approve, col_reject = st.columns(2)
            with col_approve:
                if st.button("Approve", key="approve_action", type="primary", use_container_width=True):
                    pa = st.session_state.pending_action
                    result = handle_action(pa["node_id"], pa["changes"], approved=True)
                    st.session_state.history.append(
                        {
                            "query": f"Approved action on {pa['node_id']}",
                            "intent": "action",
                            "result": result,
                            "latency": 0.1,
                        }
                    )
                    assistant_text = generate_assistant_answer(
                        f"Approve action on {pa['node_id']} with changes {pa['changes']}",
                        "action",
                        result,
                    )
                    st.session_state.chat_messages.append({"role": "assistant", "content": assistant_text})
                    st.session_state.pending_action = None
                    st.rerun()
            with col_reject:
                if st.button("Reject", key="reject_action", use_container_width=True):
                    st.session_state.chat_messages.append(
                        {
                            "role": "assistant",
                            "content": "Action rejected. No graph changes were applied.",
                        }
                    )
                    st.session_state.pending_action = None
                    st.info("Action rejected.")
                    st.rerun()
        else:
            st.caption("No pending approvals.")

    with st.container(border=True):
        st.subheader("Structured Result")
        if st.session_state.history:
            last = st.session_state.history[-1]
            result = last["result"]

            if result["type"] == "query":
                st.json(result.get("data", {}))

            elif result["type"] == "rca":
                st.markdown("**Root Cause Path:**")
                for i, step in enumerate(result.get("path", [])):
                    # `find_root_cause` returns dict entries with `id`; older flows may return node ids.
                    if isinstance(step, dict):
                        node = step.get("id") or step.get("node_id") or f"path_step_{i + 1}"
                        node_data = step
                    else:
                        node = step
                        node_data = {}
                        if node in st.session_state.graph.nodes:
                            node_data = dict(st.session_state.graph.nodes[node])

                    name = node_data.get("name", node)
                    status = node_data.get("status", "N/A")
                    st.markdown(f"{i + 1}. `{node}` - **{name}** ({status})")

            elif result["type"] == "simulate":
                data = result.get("data", {})
                col_before, col_after = st.columns(2)
                with col_before:
                    st.markdown("**Before**")
                    st.json(data.get("original", {}))
                with col_after:
                    st.markdown("**After**")
                    st.json(data.get("simulated", {}))
                st.info(f"Impact change: {len(data.get('newly_affected', []))} newly affected node(s).")

            elif result["type"] == "action":
                if result.get("status") == "executed":
                    st.success("Action executed.")
                    st.json(result.get("data", {}))
                else:
                    st.warning("Awaiting approval.")

            elif result["type"] == "document":
                st.markdown("**Document Citations:**")
                for doc in result.get("documents", []):
                    with st.expander(f"{doc['source']} - {doc['section']} (score: {doc['score']:.3f})"):
                        st.markdown(doc["text"][:500] + "...")
        else:
            st.caption("Run a query to see output.")

with col_graph:
    with st.container(border=True):
        st.subheader("Supply Chain Graph")
        highlight = None
        if st.session_state.history:
            last = st.session_state.history[-1]
            if "node_id" in last.get("result", {}):
                highlight = last["result"]["node_id"]

        fig = visualize_graph(st.session_state.graph, highlight)
        st.pyplot(fig, use_container_width=True)
        st.caption(
            f"Nodes: {st.session_state.graph.number_of_nodes()} | "
            f"Edges: {st.session_state.graph.number_of_edges()}"
        )

    with st.container(border=True):
        st.subheader("Node Inspector")
        selected = st.selectbox("Inspect node:", list(st.session_state.graph.nodes), key="inspect_node")
        if selected:
            node_data = dict(st.session_state.graph.nodes[selected])
            st.json(node_data)

with col_sidebar:
    with st.container(border=True):
        st.subheader("Agent Trace")
        if st.session_state.history:
            for entry in reversed(st.session_state.history[-8:]):
                snippet = entry["query"]
                if len(snippet) > 62:
                    snippet = snippet[:62] + "..."
                st.markdown(
                    f"""
<div class="trace-card">
    <div class="trace-top">
        <span class="trace-intent">{entry['intent'].upper()}</span>
        <span class="trace-latency">{entry['latency']:.3f}s</span>
    </div>
    <div class="trace-query">{html.escape(snippet)}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No queries yet.")

        if st.button("Clear History", key="clear_history", use_container_width=True):
            st.session_state.history = []
            st.session_state.chat_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "History cleared. Ask me for a fresh status, root cause, simulation, action, or document lookup."
                    ),
                }
            ]
            st.session_state.pending_action = None
            st.rerun()

with st.container(border=True):
    with st.expander("Document Citation Panel", expanded=False):
        if st.session_state.history:
            last = st.session_state.history[-1]
            if last.get("result", {}).get("type") == "document":
                docs = last["result"].get("documents", [])
                if docs:
                    cols = st.columns(len(docs))
                    for i, doc in enumerate(docs):
                        with cols[i]:
                            st.markdown(f"**{doc['source']}**")
                            st.caption(f"Section: {doc['section']}")
                            st.metric("Score", f"{doc['score']:.3f}")
                            st.text(doc["text"][:200] + "...")
                else:
                    st.info("No documents found.")
            else:
                st.info("Run a document query to see citations.")
        else:
            st.info("No queries yet.")

# PageIndex vectorless RAG section
st.markdown("---")
with st.container(border=True):
    st.subheader("PageIndex RAG (Vectorless)")
    api_url = os.environ.get("PAGEINDEX_API_URL", "https://api.pageindex.ai")
    api_key = os.environ.get("PAGEINDEX_API_KEY")

    if not api_key:
        st.warning("PAGEINDEX_API_KEY is not set. Configure .env to enable PageIndex queries.")

    col_pi_input, col_pi_meta = st.columns([3, 1])
    with col_pi_input:
        pi_query = st.text_input(
            "Ask PageIndex (vectorless RAG)",
            key="pageindex_query",
            placeholder="e.g., What is the penalty for late delivery?",
        )
    with col_pi_meta:
        st.caption(f"API: {api_url}")

    run_pi = st.button("Run (PageIndex)", key="run_pageindex", type="primary", use_container_width=True)
    if run_pi and pi_query:
        start = time.time()
        try:
            pi_client = PageIndexClient(api_url=api_url, api_key=api_key)
            st.session_state.pageindex_results = pi_client.search(pi_query, top_k=5)
            st.session_state.pageindex_error = None
        except Exception as exc:
            st.session_state.pageindex_results = []
            st.session_state.pageindex_error = str(exc)
        st.session_state.pageindex_latency = time.time() - start

    if st.session_state.pageindex_latency is not None:
        st.caption(
            f"Last query latency: {st.session_state.pageindex_latency:.3f}s | Backend: PageIndex | Results: {len(st.session_state.pageindex_results)}"
        )

    if st.session_state.pageindex_error:
        st.error(st.session_state.pageindex_error)

    for idx, res in enumerate(st.session_state.pageindex_results):
        with st.expander(f"[{idx+1}] {res.source or 'source?'} — {res.section or 'section?'} | score={res.score}", expanded=False):
            st.write(res.text[:800] + ("..." if len(res.text) > 800 else ""))
            if res.url:
                st.caption(f"URL: {res.url}")
            if res.tree:
                st.markdown("**Trace / Tree**")
                tree_str = _format_tree(res.tree)
                st.markdown(tree_str)
