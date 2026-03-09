"""
agent_tools.py
--------------
Four tools, one per agent. Each tool is a plain Python function.
LangGraph nodes call these directly; they can also be wrapped as
LangChain StructuredTools if you want LLM tool-calling.
"""

from __future__ import annotations
from tools.graph_store import graph, SupplyChainGraph


# TOOL 1 — Semantic Modeler (state query)

def state_query_tool(entity_id: str | None = None, entity_type: str | None = None) -> dict:
    """
    Read current graph state.
    - If entity_id given: return that node + its direct neighbors.
    - If entity_type given: return all nodes of that type.
    - If neither: return full status summary.
    """
    if entity_id:
        node = graph.get_node(entity_id)
        if not node:
            # fuzzy match by label substring
            matches = [
                n for n in graph.get_all_nodes()
                if entity_id.lower() in n.get("label", "").lower()
                or entity_id.lower() in n["id"].lower()
            ]
            if not matches:
                return {"error": f"Entity '{entity_id}' not found", "available_ids": [n["id"] for n in graph.get_all_nodes()]}
            node = matches[0]
            entity_id = node["id"]

        neighbors = graph.get_neighbors(entity_id)
        return {
            "entity": node,
            "relationships": neighbors,
            "active_events": [
                e for e in graph.get_active_events()
                if entity_id in e.get("affected_nodes", [])
            ],
        }

    if entity_type:
        nodes = graph.get_nodes_by_type(entity_type)
        return {"entity_type": entity_type, "count": len(nodes), "entities": nodes}

    # Full summary
    return {
        "summary": graph.status_summary(),
        "node_count": graph.G.number_of_nodes(),
        "active_disruptions": len(graph.get_active_events()),
    }


# TOOL 2 — Root Cause Analyst (graph traversal)

def root_cause_tool(symptom_node_id: str) -> dict:
    """
    Given a node showing a problem (e.g. dc_north with low_stock),
    trace upstream to find the root cause chain.
    Returns the causal path + contributing events.
    """
    node = graph.get_node(symptom_node_id)
    if not node:
        return {"error": f"Node '{symptom_node_id}' not found"}

    causal_chain = []
    visited = set()

    def _trace(node_id: str, depth: int = 0):
        if node_id in visited or depth > 6:
            return
        visited.add(node_id)
        n = graph.get_node(node_id)
        if not n:
            return

        status = n.get("status", "unknown")
        is_problem = status in ("delayed", "at_risk", "low_stock", "suspended")

        # upstream nodes (predecessors in the directed graph)
        upstream = graph.get_neighbors(node_id, direction="in")

        entry = {
            "node_id": node_id,
            "label": n.get("label", node_id),
            "type": n.get("type"),
            "status": status,
            "is_problem": is_problem,
            "depth": depth,
            "events": [
                e["label"] for e in graph.get_active_events()
                if node_id in e.get("affected_nodes", [])
            ],
        }
        if n.get("delay_reason"):
            entry["delay_reason"] = n["delay_reason"]
        if n.get("risk_note"):
            entry["risk_note"] = n["risk_note"]

        causal_chain.append(entry)

        # only recurse into upstream nodes that also have problems
        for up in upstream:
            up_status = up.get("status", "unknown")
            if up_status in ("delayed", "at_risk", "suspended") or depth == 0:
                _trace(up["id"], depth + 1)

    _trace(symptom_node_id)

    problem_nodes = [c for c in causal_chain if c["is_problem"]]
    root_causes = [c for c in causal_chain if c["is_problem"] and c["depth"] > 0]

    return {
        "symptom": symptom_node_id,
        "causal_chain": causal_chain,
        "root_causes": root_causes,
        "contributing_events": [
            e for e in graph.get_active_events()
            if any(n["node_id"] in e.get("affected_nodes", []) for n in problem_nodes)
        ],
        "recommendation_hint": (
            f"Found {len(root_causes)} upstream problem(s). "
            "Consider checking vendor delays and route disruptions first."
            if root_causes else "No upstream problems found — issue may be internal."
        ),
    }


# ======================================================================
# TOOL 3 — Simulator (what-if on a cloned graph)
# ======================================================================

def simulate_tool(scenario: dict) -> dict:
    """
    Run a what-if scenario on a CLONE of the live graph.
    scenario = {
        "action": "suspend_node" | "reroute" | "increase_capacity" | "resolve_event",
        "target_node": str,          # node to modify
        "parameters": dict           # action-specific params
    }
    Returns: impact assessment on the cloned graph.
    """
    sim = graph.clone()

    action = scenario.get("action")
    target = scenario.get("target_node")
    params = scenario.get("parameters", {})

    changes_made = []
    impact = []

    if action == "suspend_node":
        sim.update_node(target, {"status": "suspended"})
        changes_made.append(f"Suspended {target}")
        # assess downstream impact
        downstream = sim.get_neighbors(target, direction="out")
        for d in downstream:
            impact.append({
                "node": d["id"],
                "label": d.get("label", d["id"]),
                "impact": "Supply interrupted — will cause delays",
            })

    elif action == "reroute":
        # Mark old route as bypassed, increase utilisation on new route
        new_route = params.get("new_route")
        if new_route and sim.get_node(new_route):
            old_delay = sim.get_node(target).get("current_delay_days", 0) if target else 0
            sim.update_node(new_route, {"status": "high_load", "extra_load": True})
            changes_made.append(f"Traffic rerouted from {target} to {new_route}")
            impact.append({
                "node": new_route,
                "label": sim.get_node(new_route).get("label", new_route),
                "impact": f"Volume increase; transit time may rise by 1-2 days. Previous delay was {old_delay}d.",
            })
            cost_mult = sim.get_node(new_route).get("cost_multiplier", 1.0)
            if cost_mult > 1:
                impact.append({
                    "node": new_route,
                    "label": "Cost",
                    "impact": f"Cost multiplier: {cost_mult}x compared to road transport",
                })

    elif action == "increase_capacity":
        pct = params.get("increase_pct", 20)
        node = sim.get_node(target)
        if node:
            old_cap = node.get("capacity", 0)
            new_cap = int(old_cap * (1 + pct / 100))
            sim.update_node(target, {"capacity": new_cap})
            changes_made.append(f"Increased {target} capacity by {pct}% ({old_cap} → {new_cap})")
            impact.append({
                "node": target,
                "label": node.get("label", target),
                "impact": f"Capacity increased to {new_cap} units/month. Can absorb upstream surge.",
            })

    elif action == "resolve_event":
        event_id = params.get("event_id")
        if event_id:
            sim.resolve_event(event_id)
            changes_made.append(f"Resolved event {event_id}")
            # find what was affected
            for e in graph.get_active_events():
                if e["id"] == event_id:
                    for aff in e.get("affected_nodes", []):
                        impact.append({
                            "node": aff,
                            "label": graph.get_node(aff).get("label", aff) if graph.get_node(aff) else aff,
                            "impact": "Disruption resolved — status should return to operational within 1-2 days",
                        })

    elif action == "split_reroute":
        # Split traffic from one disabled route equally across multiple alternate routes
        alt_routes = params.get("alt_routes", [])  # list of route ids
        if not alt_routes:
            return {"error": "split_reroute requires 'alt_routes' list in parameters"}

        share_pct = round(100 / len(alt_routes))
        changes_made.append(f"Route {target} traffic split equally ({share_pct}% each) across: {', '.join(alt_routes)}")

        if target and sim.get_node(target):
            sim.update_node(target, {"status": "suspended", "note": "bypassed via split reroute"})

        for r in alt_routes:
            node = sim.get_node(r)
            if not node:
                impact.append({"node": r, "label": r, "impact": "Route not found — skipped"})
                continue
            sim.update_node(r, {"status": "high_load", "extra_load_pct": share_pct})
            cost_mult = node.get("cost_multiplier", 1.0)
            transit   = node.get("avg_transit_days", "?")
            cost_note = f" Cost multiplier: {cost_mult}x." if cost_mult > 1 else ""
            impact.append({
                "node": r,
                "label": node.get("label", r),
                "impact": f"Absorbs {share_pct}% of diverted volume. Transit: {transit}d.{cost_note}",
            })

    else:
        return {"error": f"Unknown action: '{action}'. Valid: suspend_node, reroute, split_reroute, increase_capacity, resolve_event"}

    # Snapshot delta: which nodes changed status vs. live graph
    deltas = []
    for node_data in sim.get_all_nodes():
        live_node = graph.get_node(node_data["id"])
        if live_node and live_node.get("status") != node_data.get("status"):
            deltas.append({
                "node_id": node_data["id"],
                "label": node_data.get("label"),
                "before": live_node.get("status"),
                "after": node_data.get("status"),
            })

    return {
        "scenario": scenario,
        "changes_made": changes_made,
        "impact_assessment": impact,
        "status_deltas": deltas,
        "simulation_note": "This is a simulation on a cloned graph. Live graph is NOT modified.",
        "recommended_action": (
            "Proceed to Action Agent to apply changes to the live graph."
            if changes_made else "No changes were simulated."
        ),
    }


# ======================================================================
# TOOL 4 — Action Agent (write back to live graph)
# ======================================================================

def action_tool(action: dict) -> dict:
    """
    Apply a confirmed action to the LIVE graph.
    action = {
        "type": "update_node" | "add_event" | "resolve_event",
        "target": str,
        "updates": dict   (for update_node)
        "event": dict     (for add_event)
        "event_id": str   (for resolve_event)
    }
    This is gated behind human-in-the-loop approval in the LangGraph.
    """
    action_type = action.get("type")

    if action_type == "update_node":
        target = action["target"]
        updates = action["updates"]
        # Guard: if LLM hallucinated a node id, fuzzy-match to nearest real node
        if target not in graph.G:
            matches = [
                n["id"] for n in graph.get_all_nodes()
                if target.lower() in n["id"].lower()
                or target.lower() in n.get("label", "").lower()
            ]
            if matches:
                target = matches[0]
                action["target"] = target
            else:
                return {
                    "status": "error",
                    "message": f"Node '{target}' not found. Valid ids: {[n['id'] for n in graph.get_all_nodes()]}",
                }
        updated = graph.update_node(target, updates)
        return {
            "status": "applied",
            "action": action_type,
            "node": updated,
            "message": f"Node '{target}' updated in live graph.",
        }

    elif action_type == "add_event":
        event = action["event"]
        added = graph.add_event(event)
        return {
            "status": "applied",
            "action": action_type,
            "event": added,
            "message": f"Event '{added['label']}' added to live graph.",
        }

    elif action_type == "resolve_event":
        event_id = action["event_id"]
        success = graph.resolve_event(event_id)
        return {
            "status": "applied" if success else "not_found",
            "action": action_type,
            "event_id": event_id,
            "message": f"Event '{event_id}' resolved." if success else f"Event '{event_id}' not found.",
        }

    else:
        return {"error": f"Unknown action type: '{action_type}'"}
