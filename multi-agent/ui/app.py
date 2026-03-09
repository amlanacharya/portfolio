"""
app.py  —  Streamlit UI for Supply Chain Decision Intelligence
Run: streamlit run ui/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import networkx as nx
import plotly.graph_objects as go

from agents.orchestrator import run_query, approve_action, reject_action
from tools.graph_store import graph

# ══════════════════════════════════════════════════════════════════════
# PAGE CONFIG  (must be first Streamlit call)
# ══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="SC Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════
# GLOBAL CSS — injects once, overrides Streamlit defaults
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Erase Streamlit chrome ───────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* ── App shell ────────────────────────────────────────── */
.stApp {
    background: #06090f;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.block-container {
    padding: 1.8rem 2.2rem 2rem 2.2rem !important;
    max-width: 100% !important;
}

/* ── Headings ─────────────────────────────────────────── */
h1, h2, h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px !important;
}

/* ── Buttons — default (demo queries) ────────────────── */
.stButton > button {
    background: #111827 !important;
    color: #9ca3af !important;
    border: 1px solid #1f2937 !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 11.5px !important;
    font-weight: 500 !important;
    padding: 7px 12px !important;
    transition: all 0.18s ease !important;
    text-align: left !important;
}
.stButton > button:hover {
    background: #1f2937 !important;
    border-color: #374151 !important;
    color: #f3f4f6 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.4) !important;
}

/* ── Primary button (Approve) ─────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45) !important;
    transform: translateY(-1px) !important;
}

/* ── Secondary button (Reset, Reject) ────────────────── */
.stButton > button[kind="secondary"] {
    background: #111827 !important;
    border: 1px solid #374151 !important;
    color: #d1d5db !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #ef4444 !important;
    color: #ef4444 !important;
}

/* ── Chat input ───────────────────────────────────────── */
[data-testid="stChatInput"] textarea {
    background: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 10px !important;
    color: #f3f4f6 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
}

/* ── Dividers ─────────────────────────────────────────── */
hr { border-color: #111827 !important; margin: 0.6rem 0 !important; }

/* ── Warning / info alerts ────────────────────────────── */
[data-testid="stAlert"] {
    background: #111827 !important;
    border-radius: 10px !important;
    border-left-width: 3px !important;
}

/* ── Spinner ──────────────────────────────────────────── */
[data-testid="stSpinner"] { color: #6366f1 !important; }

/* ── Scrollbar ────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #06090f; }
::-webkit-scrollbar-thumb { background: #1f2937; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #374151; }

/* ── Toast ────────────────────────────────────────────── */
[data-testid="stToast"] {
    background: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 10px !important;
    color: #f3f4f6 !important;
}

/* ── Caption / small text ─────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #4b5563 !important;
    font-size: 11.5px !important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════
if "history" not in st.session_state:
    st.session_state.history = []
if "pending_action" not in st.session_state:
    st.session_state.pending_action = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "ui-session"
if "graph_v" not in st.session_state:
    st.session_state.graph_v = 0


# ══════════════════════════════════════════════════════════════════════
# GRAPH CONFIG
# ══════════════════════════════════════════════════════════════════════
STATUS_COLORS = {
    "operational": "#22c55e",
    "delayed":     "#ef4444",
    "at_risk":     "#f59e0b",
    "low_stock":   "#f97316",
    "suspended":   "#a855f7",
    "high_load":   "#f97316",
    "unknown":     "#4b5563",
}

NODE_SHAPES = {
    "vendor":              "D",
    "factory":             "s",
    "route":               "v",
    "distribution_center": "o",
    "product":             "p",
}

DISPLAY_LABELS = {
    "vendor_X":   "Steel\nJamshedpur",
    "vendor_Y":   "Electronics\nShenzhen",
    "vendor_Z":   "Packaging\nMumbai",
    "factory_A":  "Factory\nChennai",
    "factory_B":  "Factory\nPune",
    "factory_C":  "Factory\nKolkata",
    "route_1":    "Road\nChn→Del",
    "route_2":    "Rail\nPune→Del",
    "route_3":    "Air\nKol→Del",
    "route_4":    "Road\nChn→Mum",
    "dc_north":   "DC\nDelhi",
    "dc_west":    "DC\nMumbai",
    "dc_south":   "DC\nBangalore",
    "product_P1": "Motors\nP1",
    "product_P2": "Panels\nP2",
}

COLUMN_HEADERS = [
    (-3.5, "VENDORS"),
    (-1.5, "FACTORIES"),
    ( 0.5, "ROUTES"),
    ( 2.5, "DCs"),
    ( 4.2, "PRODUCTS"),
]

POS = {
    "vendor_X":   (-3.5,  1.8),
    "vendor_Y":   (-3.5,  0.0),
    "vendor_Z":   (-3.5, -1.8),
    "factory_A":  (-1.5,  1.8),
    "factory_B":  (-1.5,  0.0),
    "factory_C":  (-1.5, -1.8),
    "route_1":    ( 0.5,  2.4),
    "route_2":    ( 0.5,  0.8),
    "route_3":    ( 0.5, -0.8),
    "route_4":    ( 0.5, -2.4),
    "dc_north":   ( 2.5,  1.5),
    "dc_west":    ( 2.5,  0.0),
    "dc_south":   ( 2.5, -1.5),
    "product_P1": ( 4.2,  0.8),
    "product_P2": ( 4.2, -0.8),
}

BG      = "#06090f"
CARD_BG = "#0d1117"
BORDER  = "#1f2937"


PLOTLY_SYMBOLS = {
    "vendor":              "diamond",
    "factory":             "square",
    "route":               "triangle-down",
    "distribution_center": "circle",
    "product":             "star",
}


def _tooltip(node: dict) -> str:
    lines = [f"<b>{node.get('label', node['id'])}</b>",
             f"Status: <b>{node.get('status','unknown').replace('_',' ').upper()}</b>"]
    if node.get("delay_days"):
        lines.append(f"Delay: {node['delay_days']} days")
    if node.get("delay_reason"):
        lines.append(f"Reason: {node['delay_reason']}")
    if node.get("risk_note"):
        lines.append(f"Risk: {node['risk_note']}")
    if node.get("inventory_days"):
        lines.append(f"Inventory: {node['inventory_days']} days")
    if node.get("capacity"):
        lines.append(f"Capacity: {node['capacity']} units")
    if node.get("utilization"):
        lines.append(f"Utilization: {int(node['utilization'] * 100)}%")
    if node.get("reliability_score"):
        lines.append(f"Reliability: {int(node['reliability_score'] * 100)}%")
    return "<br>".join(lines)


def draw_graph() -> go.Figure:
    all_nodes = graph.get_all_nodes()
    node_lookup = {n["id"]: n for n in all_nodes}
    fig = go.Figure()

    # ── Column dividers ───────────────────────────────────────────────
    for x in [-2.52, -0.52, 1.48, 3.35]:
        fig.add_vline(x=x, line=dict(color="#1f2937", width=1, dash="dot"), opacity=0.7)

    for x, label in COLUMN_HEADERS:
        fig.add_annotation(x=x, y=3.0, text=label, showarrow=False,
                           font=dict(color="#374151", size=9, family="monospace"),
                           xref="x", yref="y")

    # ── Edges ─────────────────────────────────────────────────────────
    ex, ey = [], []
    for u, v in graph.G.edges():
        if u in POS and v in POS:
            x0, y0 = POS[u]
            x1, y1 = POS[v]
            ex += [x0, x1, None]
            ey += [y0, y1, None]

    fig.add_trace(go.Scatter(
        x=ex, y=ey, mode="lines",
        line=dict(color="#1e2a3a", width=1.8),
        hoverinfo="none", showlegend=False,
    ))

    # ── Edge direction markers (midpoint triangles) ────────────────────
    for u, v in graph.G.edges():
        if u in POS and v in POS:
            x0, y0 = POS[u]
            x1, y1 = POS[v]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            fig.add_annotation(
                x=x1, y=y1, ax=mx, ay=my,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=1.2,
                arrowwidth=1.5, arrowcolor="#2d3f55",
            )

    # ── Nodes ─────────────────────────────────────────────────────────
    for ntype, symbol in PLOTLY_SYMBOLS.items():
        ids = [n["id"] for n in all_nodes if n.get("type") == ntype and n["id"] in POS]
        if not ids:
            continue

        xs       = [POS[i][0] for i in ids]
        ys       = [POS[i][1] for i in ids]
        statuses = [node_lookup[i].get("status", "unknown") for i in ids]
        colors   = [STATUS_COLORS.get(s, "#4b5563") for s in statuses]
        tooltips = [_tooltip(node_lookup[i]) for i in ids]
        labels   = [DISPLAY_LABELS.get(i, i).replace("\n", "<br>") for i in ids]

        # problem nodes: thick glowing border in status color
        border_colors = [STATUS_COLORS.get(s, "#4b5563") if s != "operational" else "#1e2a3a" for s in statuses]
        border_widths = [4 if s != "operational" else 1.5 for s in statuses]

        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers+text",
            marker=dict(
                symbol=symbol, size=34,
                color=colors, opacity=0.92,
                line=dict(color=border_colors, width=border_widths),
            ),
            text=labels,
            textposition="bottom center",
            textfont=dict(color="#94a3b8", size=8, family="Inter"),
            hovertext=tooltips,
            hoverinfo="text",
            hoverlabel=dict(
                bgcolor="#111827", bordercolor="#374151",
                font=dict(color="white", size=11, family="Inter"),
            ),
            showlegend=False,
        ))

    # ── Event warning badges ──────────────────────────────────────────
    for e in graph.get_active_events():
        for nid in e.get("affected_nodes", []):
            if nid in POS:
                x, y = POS[nid]
                fig.add_annotation(
                    x=x, y=y + 0.52,
                    text=f"⚠ {e['severity'].upper()}",
                    showarrow=False,
                    font=dict(color="#fbbf24", size=8, family="monospace"),
                    xref="x", yref="y",
                    bgcolor="#1c1500", bordercolor="#f59e0b",
                    borderwidth=1, borderpad=3, opacity=0.9,
                )

    fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        showlegend=False,
        margin=dict(l=5, r=5, t=10, b=5),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-4.8, 5.4]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-3.4, 3.4]),
        hovermode="closest",
        height=440,
        dragmode="pan",
        font=dict(family="Inter"),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════
# CUSTOM HEADER
# ══════════════════════════════════════════════════════════════════════
def _badge(text: str, color: str) -> str:
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:20px;font-size:11px;font-weight:600;"
        f"letter-spacing:0.4px'>{text}</span>"
    )

st.markdown(f"""
<div style='display:flex;align-items:center;justify-content:space-between;
            padding:0 0 1rem 0;border-bottom:1px solid {BORDER};margin-bottom:1.4rem'>
  <div>
    <h1 style='margin:0;font-size:22px;color:#f9fafb;
               background:linear-gradient(90deg,#6366f1,#a78bfa);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
      Supply Chain Decision Intelligence
    </h1>
    <p style='margin:4px 0 0 0;color:#4b5563;font-size:12px'>
      {_badge("Semantic Modeler","#2563eb")}
      &nbsp;{_badge("Root Cause","#dc2626")}
      &nbsp;{_badge("Simulator","#7c3aed")}
      &nbsp;{_badge("Action Agent","#059669")}
    </p>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ══════════════════════════════════════════════════════════════════════
left, right = st.columns([1, 1], gap="large")

# ── RIGHT: Digital Twin ───────────────────────────────────────────────
with right:
    twin_header, twin_reset = st.columns([3, 1])
    with twin_header:
        st.markdown(
            "<p style='color:#9ca3af;font-size:11px;font-weight:600;"
            "letter-spacing:1px;margin:0;text-transform:uppercase'>"
            "Digital Twin</p>",
            unsafe_allow_html=True,
        )
    with twin_reset:
        if st.button("Reset", key="reset_btn", use_container_width=True):
            graph.reset()
            st.session_state.history = []
            st.session_state.pending_action = None
            st.session_state.thread_id = "ui-session"
            st.toast("Graph reset to initial state.", icon="🔄")
            st.rerun()

    # Problem node chips
    all_nodes = graph.get_all_nodes()
    problem_nodes = [n for n in all_nodes if n.get("status") not in ("operational", None)]
    if problem_nodes:
        chip_html = "<div style='display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 10px 0'>"
        for n in problem_nodes:
            status = n.get("status", "unknown")
            color  = STATUS_COLORS.get(status, "#4b5563")
            label  = DISPLAY_LABELS.get(n["id"], n["id"]).replace("\n", " ")
            chip_html += (
                f"<span style='background:{color}22;border:1px solid {color}66;"
                f"color:{color};padding:3px 10px;border-radius:20px;"
                f"font-size:10.5px;font-weight:600'>"
                f"{label} · {status.replace('_',' ')}</span>"
            )
        chip_html += "</div>"
        st.markdown(chip_html, unsafe_allow_html=True)

    graph_placeholder = st.empty()

    def refresh_graph():
        st.session_state.graph_v += 1
        graph_placeholder.plotly_chart(
            draw_graph(), use_container_width=True,
            config={"displayModeBar": False},
            key=f"graph_{st.session_state.graph_v}",
        )

    refresh_graph()


# ── LEFT: Chat ────────────────────────────────────────────────────────
INTENT_META = {
    "state_query": ("STATE",      "#2563eb"),
    "root_cause":  ("ROOT CAUSE", "#dc2626"),
    "simulate":    ("SIMULATE",   "#7c3aed"),
    "action":      ("ACTION",     "#059669"),
}

DEMO_QUERIES = [
    "What is the current state of our supply chain?",
    "Why are deliveries to DC North delayed?",
    "What if we reroute shipments from route 1 to route 3?",
    "Suspend vendor X due to port congestion",
]

with left:
    st.markdown(
        "<p style='color:#9ca3af;font-size:11px;font-weight:600;"
        "letter-spacing:1px;margin:0 0 10px 0;text-transform:uppercase'>"
        "Query</p>",
        unsafe_allow_html=True,
    )

    # Demo buttons
    cols = st.columns(2)
    demo_clicked = None
    for i, q in enumerate(DEMO_QUERIES):
        label = q if len(q) <= 35 else q[:34] + "…"
        if cols[i % 2].button(label, key=f"demo_{i}", use_container_width=True):
            demo_clicked = q

    query = st.chat_input("Ask about your supply chain…")
    if demo_clicked:
        query = demo_clicked

    # ── Handle query ──────────────────────────────────────────────────
    if query and not st.session_state.pending_action:
        with st.spinner("Agents working…"):
            state = run_query(query, thread_id=st.session_state.thread_id)

        entry = {
            "query":    query,
            "intent":   state.get("intent", ""),
            "entity":   state.get("target_entity"),
            "response": state.get("final_response", ""),
            "pending":  state.get("pending_action"),
        }
        st.session_state.history.append(entry)

        if state.get("pending_action"):
            st.session_state.pending_action = state["pending_action"]

        refresh_graph()

    # ── Approval panel ─────────────────────────────────────────────────
    if st.session_state.pending_action:
        action  = st.session_state.pending_action
        target  = action.get("target", "")
        updates = action.get("updates", {})

        st.markdown(f"""
<div style='background:#111827;border:1px solid #f59e0b44;border-left:3px solid #f59e0b;
            border-radius:10px;padding:14px 16px;margin:10px 0'>
  <p style='margin:0 0 6px 0;color:#fbbf24;font-size:11px;font-weight:700;
            letter-spacing:0.5px'>ACTION PENDING APPROVAL</p>
  <p style='margin:0;color:#9ca3af;font-size:12px'>
    Target: <code style='background:#1f2937;padding:1px 6px;border-radius:4px;
    color:#a78bfa'>{target}</code>
    &nbsp;&nbsp;Updates: <code style='background:#1f2937;padding:1px 6px;
    border-radius:4px;color:#86efac'>{updates}</code>
  </p>
</div>
""", unsafe_allow_html=True)

        col_a, col_r, _ = st.columns([1, 1, 2])
        if col_a.button("Approve", type="primary", use_container_width=True):
            with st.spinner("Applying to live graph…"):
                state = approve_action(thread_id=st.session_state.thread_id)
            st.session_state.history[-1]["response"] = state.get("final_response", "")
            st.session_state.pending_action = None
            refresh_graph()
            st.rerun()

        if col_r.button("Reject", use_container_width=True):
            with st.spinner("Rejecting…"):
                state = reject_action(thread_id=st.session_state.thread_id)
            st.session_state.history[-1]["response"] = state.get("final_response", "")
            st.session_state.pending_action = None
            st.rerun()

    # ── Conversation history ───────────────────────────────────────────
    st.markdown(
        "<p style='color:#9ca3af;font-size:11px;font-weight:600;"
        "letter-spacing:1px;margin:14px 0 6px 0;text-transform:uppercase'>"
        "Conversation</p>",
        unsafe_allow_html=True,
    )

    if not st.session_state.history:
        st.markdown(
            "<p style='color:#374151;font-size:12px'>Use the demo buttons or type a query.</p>",
            unsafe_allow_html=True,
        )

    for entry in reversed(st.session_state.history):
        intent = entry.get("intent", "")
        badge_text, badge_color = INTENT_META.get(intent, ("?", "#374151"))
        entity_html = (
            f"&nbsp;<code style='background:#1f2937;padding:1px 6px;border-radius:4px;"
            f"font-size:10px;color:#9ca3af'>{entry['entity']}</code>"
            if entry.get("entity") else ""
        )

        st.markdown(f"""
<div style='margin:6px 0 2px 0'>
  <span style='background:{badge_color};color:white;padding:2px 9px;border-radius:20px;
               font-size:10px;font-weight:700;letter-spacing:0.5px'>{badge_text}</span>
  {entity_html}
</div>
<p style='margin:4px 0 6px 0;color:#e5e7eb;font-size:13px;font-weight:500'>
  {entry['query']}
</p>
""", unsafe_allow_html=True)

        if entry.get("pending") and not entry.get("response"):
            st.info("Waiting for approval…")
        elif entry.get("response"):
            st.markdown(
                f"<div style='color:#9ca3af;font-size:12.5px;line-height:1.6;"
                f"padding:0 0 6px 0'>{entry['response']}</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<hr style='border-color:{BORDER};margin:8px 0'/>",
            unsafe_allow_html=True,
        )
