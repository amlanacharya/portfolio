import streamlit as st
import time
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional, List
import copy
from collections import deque
import os
import re

from knowledge_graph import build_supply_chain_graph, NodeType
from agent_tools import (query_state as _query_state,
find_root_cause as _find_root_cause,
simulate_change as _simulate_change,
execute_action as _execute_action)

from llm_router import llm_router, keyword_router
from retrieval import search_docs
st.set_page_config(
    page_title="Supply Chain Digital Twin",
    layout="wide"
)

if "graph" not in st.session_state:
    st.session_state.graph = build_supply_chain_graph()

if "history" not in st.session_state:
    st.session_state.history = []

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None


def visualize_graph(G: nx.DiGraph, highlight_node: str = None):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    type_colors = {
        NodeType.VENDOR: "#4CAF50",
        NodeType.FACTORY: "#2196F3", 
        NodeType.PRODUCT: "#FF9800",
        NodeType.ROUTE: "#9C27B0",
        NodeType.PORT: "#F44336",
        NodeType.WAREHOUSE: "#00BCD4",
        NodeType.EVENT: "#E91E63",
        NodeType.UNKNOWN: "#9E9E9E"
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
        color = type_colors.get(node_type, "#9E9E9E")
        
        if node == highlight_node:
            color = "#FFD700"  # Gold
        node_colors.append(color)

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color="#666666", arrows=True, ax=ax)
    
    labels = {n: G.nodes[n].get("name", n)[:10] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=7, ax=ax)
    
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

def handle_action(node_id: str, 
                  changes: Dict, approved: bool = False) -> Dict[str, Any]:
    if not approved:
        return {
            "type": "action", 
            "status": "pending", 
            "node_id": node_id, 
            "changes": changes,
            "message": "Action requires approval"
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
    else:
        kw_result=keyword_router({"query": query})
        return kw_result.get("intent", "query")

def extract_node_id(query: str) -> str:
    match = re.search(r'(warehouse|port|factory|vendor|product|route|event)_\d+', query.lower())
    return match.group(0) if match else ""

def extract_changes(query: str) -> Dict:
    changes = {}
    query_lower = query.lower()
    
    status_map = ["operational", "shutdown", "congested", "maintenance", "resolved", "active"]
    for status in status_map:
        if status in query_lower:
            changes["status"] = status
            break
    
    capacity_match = re.search(r'capacity[:\s]*(\d+)', query_lower)
    if capacity_match:
        changes["capacity_pct"] = int(capacity_match.group(1))
    
    return changes


st.title("Supply Chain Digital Twin Agent")
st.markdown("---")
col_chat, col_graph, col_sidebar = st.columns([2, 3, 1])

with col_chat:
    st.subheader("Query")
    
    # Chat input
    user_query = st.text_input(
        "Ask about the supply chain:",
        placeholder="e.g., What is the status of port_1? or Why is warehouse_1 affected?"
    )
    
    # Intent badge display
    if user_query:
        intent = classify_intent(user_query)
        intent_colors = {
            "query": "🔵", "rca": "🟠", "simulate": "🟣", 
            "action": "🔴", "document": "📄"
        }
        st.markdown(f"**Intent:** {intent_colors.get(intent, '⚪')} `{intent}`")
        
        node_id = extract_node_id(user_query)
        changes = extract_changes(user_query)
        
        if st.button("Submit", type="primary"):
            start_time = time.time()
            
            # Route to handler based on intent
            if intent == "query":
                result = handle_query(node_id or "port_1")
            elif intent == "rca":
                result = handle_rca(node_id or "warehouse_1")
            elif intent == "simulate":
                result = handle_simulate(node_id or "port_1", changes or {"status": "operational"})
            elif intent == "action":
                # Store pending action for approval
                st.session_state.pending_action = {
                    "node_id": node_id or "port_1",
                    "changes": changes or {"status": "operational"}
                }
                result = handle_action(node_id or "port_1", changes or {"status": "operational"}, approved=False)
            elif intent == "document":
                result = handle_document(user_query)
            else:
                result = {"type": "error", "message": "Unknown intent"}
            
            latency = time.time() - start_time
            
            # Store in history
            st.session_state.history.append({
                "query": user_query,
                "intent": intent,
                "result": result,
                "latency": latency
            })
            st.rerun()
    
    # Action approval section
    if st.session_state.pending_action:
        st.markdown("---")
        st.warning("**Action Requires Approval**")
        st.json(st.session_state.pending_action)
        
        col_approve, col_reject = st.columns(2)
        with col_approve:
            if st.button("Approve", type="primary"):
                pa = st.session_state.pending_action
                result = handle_action(pa["node_id"], pa["changes"], approved=True)
                st.session_state.history.append({
                    "query": f"Approved action on {pa['node_id']}",
                    "intent": "action",
                    "result": result,
                    "latency": 0.1
                })
                st.session_state.pending_action = None
                st.rerun()
        
        with col_reject:
            if st.button("Reject"):
                st.session_state.pending_action = None
                st.info("Action rejected.")
                st.rerun()
    
    # Result display
    st.markdown("---")
    st.subheader("Result")
    
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
                    node = step.get("id") or step.get("node_id") or f"path_step_{i+1}"
                    node_data = step
                else:
                    node = step
                    node_data = {}
                    if node in st.session_state.graph.nodes:
                        node_data = dict(st.session_state.graph.nodes[node])

                name = node_data.get("name", node)
                status = node_data.get("status", "N/A")
                st.markdown(f"{i+1}. `{node}` - **{name}** ({status})")
        
        elif result["type"] == "simulate":
            data = result.get("data", {})
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Before:**")
                st.json(data.get("original", {}))
            with col2:
                st.markdown("**After:**")
                st.json(data.get("simulated", {}))
            
            st.markdown(f"**Impact Change:** {len(data.get('newly_affected', []))} newly affected")
        
        elif result["type"] == "action":
            if result.get("status") == "executed":
                st.success("Action executed!")
                st.json(result.get("data", {}))
            else:
                st.warning("Pending approval")
        
        elif result["type"] == "document":
            st.markdown("**Document Citations:**")
            for doc in result.get("documents", []):
                with st.expander(f"{doc['source']} - {doc['section']} (score: {doc['score']:.3f})"):
                    st.markdown(doc["text"][:500] + "...")
with col_graph:
    st.subheader("Supply Chain Graph")
    
    # Get highlighted node
    highlight = None
    if st.session_state.history:
        last = st.session_state.history[-1]
        if "node_id" in last.get("result", {}):
            highlight = last["result"]["node_id"]
    
    # Render graph
    fig = visualize_graph(st.session_state.graph, highlight)
    st.pyplot(fig)
    
    # Graph stats
    st.caption(f"Nodes: {st.session_state.graph.number_of_nodes()} | Edges: {st.session_state.graph.number_of_edges()}")
    
    # Node selector for inspection
    selected = st.selectbox("Inspect node:", list(st.session_state.graph.nodes))
    if selected:
        node_data = dict(st.session_state.graph.nodes[selected])
        st.json(node_data)

with col_sidebar:
    st.subheader("Agent Trace")
    
    if st.session_state.history:
        for i, entry in enumerate(reversed(st.session_state.history[-5:])):
            with st.container():
                st.markdown(f"**{entry['intent'].upper()}**")
                st.caption(f"{entry['latency']:.3f}s")
                st.caption(f"{entry['query'][:30]}...")
                st.markdown("---")
    else:
        st.info("No queries yet.")
    
    # Clear history
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()

st.markdown("---")
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







    





    





