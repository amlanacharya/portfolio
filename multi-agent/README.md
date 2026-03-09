# Supply Chain Decision Intelligence

A multi-agent system that acts as a reasoning layer over a live supply chain knowledge graph. Natural language queries are routed to specialized agents that read, analyze, simulate, and write back to an in-memory digital twin.

## What it does

Ask questions in plain English. The system decides which agent to invoke, runs the appropriate analysis against the graph, and returns an actionable response.

- **State queries** -- current health of any entity or the entire supply chain
- **Root cause analysis** -- upstream graph traversal to find why something is delayed
- **Simulation** -- what-if scenarios on a cloned graph without touching live state
- **Actions** -- human-approved writes back to the live graph (suspend, reroute, update)

## Architecture

```
User Query
    |
    v
Router (LLM classifies intent)
    |
    +-- Semantic Modeler     reads graph state, answers "what is" questions
    +-- Root Cause Analyst   BFS/DFS traversal to find upstream failure chain
    +-- Simulator            clones graph, applies change, returns impact delta
    +-- Action Agent         writes to live graph after human approval
    |
    v
Response Assembler (LLM summarizes tool output into plain English)
    |
    v
Streamlit UI + Plotly Digital Twin (live graph, hover tooltips, color by status)
```

The orchestrator is a LangGraph `StateGraph` with `interrupt_before=["action_executor"]` for human-in-the-loop gating on all write operations.

## Stack

| Layer | Choice |
|---|---|
| Agent framework | LangGraph |
| LLM | Groq (llama-3.1-8b-instant) |
| Knowledge graph | NetworkX in-memory directed graph |
| Graph visualization | Plotly (interactive, hover tooltips) |
| UI | Streamlit |

## Project structure

```
multi-agent/
  agents/
    orchestrator.py     LangGraph state machine, all nodes and routing logic
  tools/
    graph_store.py      SupplyChainGraph singleton (read, write, clone, reset)
    agent_tools.py      Four tool functions (state_query, root_cause, simulate, action)
  data/
    supply_chain_graph.json   Mock supply chain: 15 nodes, 20 edges, 3 active events
  ui/
    app.py              Streamlit app with Plotly digital twin
  config.py             Loads GROQ_API_KEY from .env
  test_agent.py         CLI test for all four agent paths
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install langgraph langchain-core langchain-groq networkx streamlit plotly python-dotenv
```

Create a `.env` file in this directory:

```
GROQ_API_KEY=your-key-here
```

Get a free key at console.groq.com.

## Running

```bash
# CLI test (validates all four agent paths)
python test_agent.py

# Streamlit UI
streamlit run ui/app.py
```

## The mock scenario

The graph is pre-seeded with a realistic disruption scenario:

- Vendor X (raw steel) is delayed 7 days due to Haldia port congestion
- Route 1 (Chennai to Delhi road) is delayed due to NH-44 flooding
- Factory B (Pune) is at risk from a labor dispute
- DC North (Delhi) has 3.2 days of inventory against a 5-day threshold

This creates a multi-hop causal chain: `DC North low stock -> Route 1 delayed -> Factory B at risk -> Vendor X delayed`.

## Demo queries

```
What is the current state of our supply chain?
Why are deliveries to DC North delayed?
What if we reroute shipments from route 1 to route 3?
What if we split route 1 traffic equally across route 2, route 3, and route 4?
Suspend vendor X due to port congestion
```

## Key design decisions

**LangGraph over a custom state machine** -- checkpointing, declarative conditional edges, and the interrupt mechanism for human-in-the-loop are built in.

**Simulation on a cloned graph** -- `graph.clone()` deep-copies the NetworkX graph so what-if scenarios never touch live state. The delta between cloned and live state is returned as the impact assessment.

**Router uses few-shot examples, not just schema** -- structured JSON extraction from natural language is unreliable with schema descriptions alone. Concrete input/output examples in the prompt are required for consistent extraction.

**Human approval gates all writes** -- the graph pauses at `interrupt_before=["action_executor"]`. `approve_action()` calls `update_state` then resumes with `invoke(None)`, not a fresh invocation.
