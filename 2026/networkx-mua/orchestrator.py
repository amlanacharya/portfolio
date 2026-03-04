from typing import TypedDict, Optional, Dict, Any, List
from agent_tools import (
    query_state,
    find_root_cause,
    simulate_change,
    execute_action,
    G 
)

from langgraph.graph import StateGraph, END
from retrieval import search_docs
from llm_router import llm_router,AgentState
def query_handler(state):
    node_id = state["node_id"]
    result = query_state(G, node_id)
    if result is None:
        return {"result": {"error": f"Node '{node_id}' not found in graph"}}
    return {"result": {"node_id": node_id, "state": result}}

def rca_handler(state):
    node_id = state["node_id"]
    result = find_root_cause(G, node_id)
    return {"result": {"node_id": node_id, "root_cause_path": result}}

def simulate_handler(state):
    node_id = state["node_id"]
    changes = state.get("changes", {})
    result = simulate_change(G, node_id, changes)
    return {"result": result}

def action_handler(state):
    node_id = state["node_id"]
    changes = state.get("changes", {})
    approval = state.get("approval", False)
    if not approval:
        return {
            "result": {
                "status": "pending_approval",
                "message": "Action requires approval before execution",
                "node_id": node_id,
                "proposed_changes": changes
            }
        }
    
    result = execute_action(G, node_id, changes)
    return {"result": result}

def document_handler(state: AgentState) -> Dict[str, Any]:

    query = state["query"]
    
    docs = search_docs(query)
    
    return {
        "result": {
            "query": query,
            "documents": docs,
            "count": len(docs)
        }
    }

# #  query_handler
# print(query_handler({"node_id": "port_1"}))

# #  rca_handler
# print(rca_handler({"node_id": "warehouse_1"}))

# #  simulate_handler
# print(simulate_handler({"node_id": "port_1", "changes": {"status": "operational"}}))


def route_by_intent(state: AgentState) -> str:
    intent = state["intent"]
    intent_to_node = {
        "query": "query_node",
        "rca": "rca_node",
        "simulate": "simulate_node",
        "action": "action_node",
        "document": "document_node"
    }
    
    return intent_to_node.get(intent, "query_node")

def build_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("router", llm_router)
    workflow.add_node("query_node", query_handler)
    workflow.add_node("rca_node", rca_handler)
    workflow.add_node("simulate_node", simulate_handler)
    workflow.add_node("action_node", action_handler)
    workflow.add_node("document_node", document_handler)

    workflow.set_entry_point("router")
    workflow.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "query_node": "query_node",
            "rca_node": "rca_node",
            "simulate_node": "simulate_node",
            "action_node": "action_node",
            "document_node": "document_node"
        }
    )
    workflow.add_edge("query_node", END)
    workflow.add_edge("rca_node", END)
    workflow.add_edge("simulate_node", END)
    workflow.add_edge("action_node", END)
    workflow.add_edge("document_node", END)

    return workflow.compile()



app = build_agent_graph()
result = app.invoke({"query": "What is the status of port_1", "node_id": "port_1"})
# print(result)

# # RCA
# result = app.invoke({"query": "Why is warehouse_1 struggling", "node_id": "warehouse_1"})
# print(result["intent"], len(result["result"]["root_cause_path"]))

# # Simulate
# result = app.invoke({"query": "What if port_1 becomes operational", "node_id": "port_1", "changes": {"status": "operational"}})
# print(result["intent"], result["result"]["simulated"]["status"])

# # Human in loop
# result = app.invoke({"query": "Fix port_1 status", "node_id": "port_1", "changes": {"status": "operational"}, "approval": False})
# print(result["result"])

#RAG check
result = app.invoke({"query": "What is the penalty for late delivery?", "node_id": ""})
print(result["result"])