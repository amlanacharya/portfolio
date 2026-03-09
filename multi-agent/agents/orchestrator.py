"""
orchestrator.py
---------------
LangGraph state machine that routes user queries to the right agent.

Graph topology:
  START -> router -> semantic_modeler  -> assembler -> END
                  -> root_cause_analyst -> assembler -> END
                  -> simulator          -> assembler -> END
                  -> action_proposal    -> [HUMAN APPROVAL] -> action_executor -> END
"""

from __future__ import annotations
import json
from typing import Literal, Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import GROQ_API_KEY, GROQ_MODEL
from tools.agent_tools import (
    state_query_tool,
    root_cause_tool,
    simulate_tool,
    action_tool,
)
from tools.graph_store import graph


llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0)


class AgentState(TypedDict):
    user_query: str
    intent: str                        # classified by router
    target_entity: str | None          # extracted entity id/name
    scenario: dict | None              # for simulator
    action: dict | None                # for action agent
    tool_result: dict | None           # raw tool output
    final_response: str                # assembled natural-language answer
    pending_action: dict | None        # action waiting for human approval
    human_approved: bool | None        # approval decision


INTENT_SYSTEM = """You are a supply chain query router. Classify the user's query into exactly one intent and extract structured data.

Intents:
- state_query   : asking about current status of the supply chain, a specific entity, or overall health
- root_cause    : asking WHY something is delayed, at risk, or has a problem
- simulate      : asking what-if, what would happen if, impact of a hypothetical change
- action        : requesting to make a LIVE change (suspend, update, resolve, reroute something NOW)

Node IDs to use exactly: factory_A, factory_B, factory_C, vendor_X, vendor_Y, vendor_Z,
route_1, route_2, route_3, route_4, dc_north, dc_west, dc_south, product_P1, product_P2

For simulate intent, always populate "scenario" with:
  { "action": <one of: suspend_node | reroute | split_reroute | increase_capacity | resolve_event>,
    "target_node": <node_id of the route/node being DISABLED or changed — NOT the destination>,
    "parameters": <dict of extra params> }

  CRITICAL: target_node is always the SOURCE being changed, never the destination.

  Examples:
  - "What if we reroute from route 1 to route 3?"
    -> {"action": "reroute", "target_node": "route_1", "parameters": {"new_route": "route_3"}}
  - "What if Factory B shuts down?"
    -> {"action": "suspend_node", "target_node": "factory_B", "parameters": {}}
  - "What if we increase Factory C capacity by 30%?"
    -> {"action": "increase_capacity", "target_node": "factory_C", "parameters": {"increase_pct": 30}}
  - "What if we split route 1 traffic equally across route 2, 3, and 4?"
    -> {"action": "split_reroute", "target_node": "route_1", "parameters": {"alt_routes": ["route_2", "route_3", "route_4"]}}
  - "What if route 1 traffic goes to route 2 and route 4 equally?"
    -> {"action": "split_reroute", "target_node": "route_1", "parameters": {"alt_routes": ["route_2", "route_4"]}}

For action intent, always populate "action" with:
  { "type": <one of: update_node | resolve_event>,
    "target": <node_id>,
    "updates": <dict of field updates> }

  Examples:
  - "Suspend vendor X"
    -> {"type": "update_node", "target": "vendor_X", "updates": {"status": "suspended"}}
  - "Mark route 1 as operational"
    -> {"type": "update_node", "target": "route_1", "updates": {"status": "operational", "current_delay_days": 0}}

Respond ONLY with valid JSON, no explanation:
{
  "intent": "<intent>",
  "target_entity": "<node_id or null>",
  "scenario": <dict or null>,
  "action": <dict or null>
}"""


def router_node(state: AgentState) -> AgentState:
    query = state["user_query"]
    response = llm.invoke([
        SystemMessage(content=INTENT_SYSTEM),
        HumanMessage(content=query),
    ])
    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        # fallback
        parsed = {"intent": "state_query", "target_entity": None, "scenario": None, "action": None}

    return {
        **state,
        "intent": parsed.get("intent", "state_query"),
        "target_entity": parsed.get("target_entity"),
        "scenario": parsed.get("scenario"),
        "action": parsed.get("action"),
    }


def route_to_agent(state: AgentState) -> Literal["semantic_modeler", "root_cause_analyst", "simulator", "action_proposal"]:
    return {
        "state_query": "semantic_modeler",
        "root_cause": "root_cause_analyst",
        "simulate": "simulator",
        "action": "action_proposal",
    }.get(state["intent"], "semantic_modeler")


def semantic_modeler_node(state: AgentState) -> AgentState:
    result = state_query_tool(entity_id=state.get("target_entity"))
    return {**state, "tool_result": result}


def root_cause_analyst_node(state: AgentState) -> AgentState:
    target = state.get("target_entity") or "dc_north"
    result = root_cause_tool(target)
    return {**state, "tool_result": result}


def simulator_node(state: AgentState) -> AgentState:
    scenario = state.get("scenario")
    if not scenario:
        result = {"error": "No simulation scenario provided. Please specify what change to simulate."}
    else:
        result = simulate_tool(scenario)
    return {**state, "tool_result": result}


def action_proposal_node(state: AgentState) -> AgentState:
    """
    Prepares the action but does NOT execute it.
    Sets pending_action for human review.
    """
    action = state.get("action")
    if not action:
        return {
            **state,
            "tool_result": {"error": "Could not parse action from query."},
            "pending_action": None,
        }
    return {
        **state,
        "pending_action": action,
        "tool_result": {
            "status": "awaiting_approval",
            "proposed_action": action,
            "message": "Action prepared. Awaiting human approval before applying to live graph.",
        },
    }


def action_executor_node(state: AgentState) -> AgentState:
    if not state.get("human_approved"):
        result = {"status": "rejected", "message": "Action was not approved. No changes made."}
    else:
        result = action_tool(state["pending_action"])
    return {**state, "tool_result": result, "pending_action": None}


def route_after_proposal(state: AgentState) -> Literal["action_executor", "assembler"]:
    """If no pending action (parse error), skip to assembler."""
    if state.get("pending_action") is None:
        return "assembler"
    return "action_executor"


ASSEMBLER_SYSTEM = """You are a supply chain intelligence assistant.
Given a user query and raw tool data, produce a clear, concise, actionable response.
- Lead with the direct answer.
- Highlight problems, risks, and recommendations.
- Keep it under 150 words.
- Use plain text, no markdown tables."""


def assembler_node(state: AgentState) -> AgentState:
    tool_result = state.get("tool_result", {})
    prompt = f"""User query: {state['user_query']}

Tool data:
{json.dumps(tool_result, indent=2)}

Produce a concise, actionable response."""

    response = llm.invoke([
        SystemMessage(content=ASSEMBLER_SYSTEM),
        HumanMessage(content=prompt),
    ])
    return {**state, "final_response": response.content}


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("router", router_node)
    builder.add_node("semantic_modeler", semantic_modeler_node)
    builder.add_node("root_cause_analyst", root_cause_analyst_node)
    builder.add_node("simulator", simulator_node)
    builder.add_node("action_proposal", action_proposal_node)
    builder.add_node("action_executor", action_executor_node)
    builder.add_node("assembler", assembler_node)

    builder.add_edge(START, "router")
    builder.add_conditional_edges("router", route_to_agent)

    builder.add_edge("semantic_modeler", "assembler")
    builder.add_edge("root_cause_analyst", "assembler")
    builder.add_edge("simulator", "assembler")

    builder.add_conditional_edges("action_proposal", route_after_proposal)
    builder.add_edge("action_executor", "assembler")

    builder.add_edge("assembler", END)

    memory = MemorySaver()
    return builder.compile(
        checkpointer=memory,
        interrupt_before=["action_executor"],  # pause here for human approval
    )


app = build_graph()


def run_query(user_query: str, thread_id: str = "demo") -> dict:
    """
    Run a query through the graph. Returns state dict.
    If intent is 'action', the graph pauses before execution —
    call approve_action() or reject_action() next.
    """
    config = {"configurable": {"thread_id": thread_id}}
    state = app.invoke(
        {
            "user_query": user_query,
            "intent": "",
            "target_entity": None,
            "scenario": None,
            "action": None,
            "tool_result": None,
            "final_response": "",
            "pending_action": None,
            "human_approved": None,
        },
        config=config,
    )
    return state


def approve_action(thread_id: str = "demo") -> dict:
    """Update state with approval=True then resume the paused graph."""
    config = {"configurable": {"thread_id": thread_id}}
    app.update_state(config, {"human_approved": True})
    state = app.invoke(None, config=config)
    return state


def reject_action(thread_id: str = "demo") -> dict:
    """Update state with approval=False then resume the paused graph."""
    config = {"configurable": {"thread_id": thread_id}}
    app.update_state(config, {"human_approved": False})
    state = app.invoke(None, config=config)
    return state
