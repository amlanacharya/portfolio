"""
graph_store.py
--------------
In-memory Digital Twin backed by NetworkX.
All agents read/write through this singleton.
"""

import json
import copy
from pathlib import Path
import networkx as nx

DATA_FILE = Path(__file__).parent.parent / "data" / "supply_chain_graph.json"


class SupplyChainGraph:
    """
    The Digital Twin. A directed graph where:
      - Nodes  = entities (factories, vendors, routes, DCs, products)
      - Edges  = relationships (supplies, produces, delivers_to, etc.)
      - Events = active disruptions layered on top

    All agents share a single instance (module-level singleton below).
    """

    def __init__(self, data_file: Path = DATA_FILE):
        self._raw = json.loads(data_file.read_text())
        self.G = nx.DiGraph()
        self.events: list[dict] = []
        self._load()

    def _load(self):
        for node in self._raw["nodes"]:
            node_id = node["id"]
            self.G.add_node(node_id, **{k: v for k, v in node.items() if k != "id"})

        for edge in self._raw["edges"]:
            self.G.add_edge(
                edge["source"],
                edge["target"],
                **{k: v for k, v in edge.items() if k not in ("source", "target")},
            )

        self.events = self._raw.get("events", [])

    # ------------------------------------------------------------------
    # READ helpers
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> dict | None:
        if node_id not in self.G:
            return None
        return {"id": node_id, **self.G.nodes[node_id]}

    def get_nodes_by_type(self, node_type: str) -> list[dict]:
        return [
            {"id": n, **d}
            for n, d in self.G.nodes(data=True)
            if d.get("type") == node_type
        ]

    def get_neighbors(self, node_id: str, direction: str = "both") -> list[dict]:
        """Return neighboring nodes. direction: 'in', 'out', 'both'"""
        if direction == "out":
            neighbors = list(self.G.sucaddcessors(node_id))
        elif direction == "in":
            neighbors = list(self.G.predecessors(node_id))
        else:
            neighbors = list(self.G.successors(node_id)) + list(
                self.G.predecessors(node_id)
            )
        return [{"id": n, **self.G.nodes[n]} for n in neighbors]

    def get_active_events(self) -> list[dict]:
        return [e for e in self.events if e.get("active", False)]

    def find_path(self, source: str, target: str) -> list[str] | None:
        try:
            return nx.shortest_path(self.G, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_all_nodes(self) -> list[dict]:
        return [{"id": n, **d} for n, d in self.G.nodes(data=True)]

    def get_all_edges(self) -> list[dict]:
        return [
            {"source": u, "target": v, **d}
            for u, v, d in self.G.edges(data=True)
        ]

    def snapshot(self) -> dict:
        """Full serialisable snapshot of current graph state."""
        return {
            "nodes": self.get_all_nodes(),
            "edges": self.get_all_edges(),
            "events": self.events,
        }

    # ------------------------------------------------------------------
    # WRITE helpers (used by Action Agent after approval)
    # ------------------------------------------------------------------

    def update_node(self, node_id: str, updates: dict) -> dict:
        if node_id not in self.G:
            raise ValueError(f"Node '{node_id}' not found in graph")
        self.G.nodes[node_id].update(updates)
        return self.get_node(node_id)

    def add_event(self, event: dict) -> dict:
        import uuid, datetime
        event.setdefault("id", f"event_{uuid.uuid4().hex[:6]}")
        event.setdefault("created_at", datetime.date.today().isoformat())
        event.setdefault("active", True)
        self.events.append(event)
        return event

    def resolve_event(self, event_id: str) -> bool:
        for e in self.events:
            if e["id"] == event_id:
                e["active"] = False
                return True
        return False

    def reset(self):
        """Reload graph from the original JSON file, discarding all in-memory changes."""
        self.G.clear()
        self.events = []
        self._raw = json.loads(DATA_FILE.read_text())
        self._load()

    def clone(self) -> "SupplyChainGraph":
        """Return a deep copy for simulation (Simulator Agent)."""
        cloned = SupplyChainGraph.__new__(SupplyChainGraph)
        cloned.G = copy.deepcopy(self.G)
        cloned.events = copy.deepcopy(self.events)
        cloned._raw = copy.deepcopy(self._raw)
        return cloned

    # ------------------------------------------------------------------
    # Summary helpers (for agent prompts)
    # ------------------------------------------------------------------

    def status_summary(self) -> str:
        """Human-readable health summary for LLM context."""
        lines = ["=== Supply Chain Status ==="]

        for node_type in ("factory", "vendor", "route", "distribution_center", "product"):
            nodes = self.get_nodes_by_type(node_type)
            if not nodes:
                continue
            lines.append(f"\n[{node_type.upper()}S]")
            for n in nodes:
                status = n.get("status", "unknown")
                label = n.get("label", n["id"])
                note = ""
                if n.get("delay_days"):
                    note = f" | delay: {n['delay_days']}d"
                if n.get("risk_note"):
                    note = f" | {n['risk_note']}"
                if n.get("inventory_days"):
                    note = f" | inventory: {n['inventory_days']}d"
                lines.append(f"  {label}: [{status.upper()}]{note}")

        active_events = self.get_active_events()
        if active_events:
            lines.append("\n[ACTIVE DISRUPTIONS]")
            for e in active_events:
                lines.append(
                    f"  [{e['severity'].upper()}] {e['label']} -> affects: {', '.join(e['affected_nodes'])}"
                )

        return "\n".join(lines)


# Module-level singleton — import this everywhere
graph = SupplyChainGraph()
