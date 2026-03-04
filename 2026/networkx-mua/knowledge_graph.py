import networkx as nx
from typing import Dict, List, Set, Any, Optional
from enum import Enum
from collections import deque

class NodeType(Enum):
    VENDOR = "Vendor"
    FACTORY = "Factory"
    PRODUCT = "Product"
    ROUTE = "Route"
    PORT = "Port"
    WAREHOUSE = "Warehouse"
    EVENT = "Event"
    UNKNOWN = "Unknown"


class RelationshipType(Enum):
    SUPPLIES_TO = "supplies_to"
    PRODUCES = "produces"
    SHIPS_VIA = "ships_via"
    CONNECTS_TO = "connects_to"
    STORES = "stores"
    AFFECTS = "affects"


UNKNOWN_TYPE = NodeType.UNKNOWN
VALID_NODE_TYPES = {nt.value for nt in NodeType if nt != NodeType.UNKNOWN}

def get_node_type(node_data: Dict[str, Any]) -> NodeType:
    node_type = node_data.get("type")
    if node_type is None:
        return UNKNOWN_TYPE
    if isinstance(node_type, NodeType):
        return node_type
    if isinstance(node_type, str):
        if node_type in VALID_NODE_TYPES:
            for nt in NodeType:
                if nt.value == node_type:
                    return nt
    return UNKNOWN_TYPE

def get_node_attr(node_data: Dict[str, Any], key: str, default: Any = None) -> Any:
    
    return node_data.get(key, default)

    

def build_supply_chain_graph()->nx.DiGraph:
    G=nx.DiGraph()
    G.add_node("vendor_1",
               type=NodeType.VENDOR,
               name="Tata Steel",
               material="steel_coil",
               sla_adherence=92,
               reliability=0.88)
    
    G.add_node("vendor_2",
               type=NodeType.VENDOR,
               name="Reliance Industries",
               material="petrochemicals",
               sla_adherence=88,
               reliability=0.91)
    
    G.add_node("vendor_3",
               type=NodeType.VENDOR,
               name="JSW Steel",
               material="steel_sheet",
               sla_adherence=95,
               reliability=0.93)
    
    G.add_node("factory_1",
               type=NodeType.FACTORY,
               name="Mumbai Plant",
               location="Mumbai",
               status="operational",
               capacity_pct=85)
    
    G.add_node("factory_2",
               type=NodeType.FACTORY,
               name="Chennai Plant",
               location="Chennai",
               status="operational",
               capacity_pct=90)
    
    G.add_node("factory_3",
               type=NodeType.FACTORY,
               name="Kolkata Plant",
               location="Kolkata",
               status="maintenance",
               capacity_pct=40)
    
    G.add_node("product_1",
               type=NodeType.PRODUCT,
               name="Steel Coil",
               demand_level="high",
               priority="critical")
    
    G.add_node("product_2",
               type=NodeType.PRODUCT,
               name="Petrochemical Products",
               demand_level="medium",
               priority="standard")
    
    G.add_node("product_3",
               type=NodeType.PRODUCT,
               name="Steel Sheets",
               demand_level="high",
               priority="critical")
    
    G.add_node("route_1",
               type=NodeType.ROUTE,
               name="Mumbai-Vizag Sea Route",
               mode="sea",
               status="active",
               transit_time_days=5)
    
    G.add_node("route_2",
               type=NodeType.ROUTE,
               name="Chennai-Delhi Land Route",
               mode="land",
               status="disrupted",
               transit_time_days=3)
    
    G.add_node("route_3",
               type=NodeType.ROUTE,
               name="Kolkata-Delhi Rail Route",
               mode="rail",
               status="active",
               transit_time_days=2)
    G.add_node("port_1",
               type=NodeType.PORT,
               name="Vizag Port",
               location="Visakhapatnam",
               status="congested",
               throughput=1200)
    
    G.add_node("port_2",
               type=NodeType.PORT,
               name="Chennai Port",
               location="Chennai",
               status="operational",
               throughput=800)
    G.add_node("warehouse_1",
               type=NodeType.WAREHOUSE,
               name="Delhi Hub",
               location="Delhi",
               stock_level=450,
               status="operational")
    
    G.add_node("warehouse_2",
               type=NodeType.WAREHOUSE,
               name="Bangalore Hub",
               location="Bangalore",
               stock_level=280,
               status="operational")
    G.add_node("event_1",
               type=NodeType.EVENT,
               name="Cyclone Dana",
               event_type="weather",
               severity="high",
               status="active")
    
    G.add_node("event_2",
               type=NodeType.EVENT,
               name="Labor Strike",
               event_type="industrial",
               severity="medium",
               status="active")
    
    G.add_edge("vendor_1", "factory_1", relationship="supplies_to")
    G.add_edge("vendor_2", "factory_2", relationship="supplies_to")
    G.add_edge("vendor_3", "factory_3", relationship="supplies_to")
    G.add_edge("factory_1", "product_1", relationship="produces")
    G.add_edge("factory_2", "product_2", relationship="produces")
    G.add_edge("factory_3", "product_3", relationship="produces")
    G.add_edge("factory_1", "route_1", relationship="ships_via")
    G.add_edge("factory_2", "route_2", relationship="ships_via")
    G.add_edge("factory_3", "route_3", relationship="ships_via")
    G.add_edge("route_1", "port_1", relationship="connects_to")
    G.add_edge("route_2", "port_1", relationship="connects_to")  # Bottleneck!
    G.add_edge("route_3", "port_2", relationship="connects_to")
    G.add_edge("port_1", "warehouse_1", relationship="connects_to")
    G.add_edge("port_2", "warehouse_2", relationship="connects_to")
    G.add_edge("warehouse_1", "product_1", relationship="stores")
    G.add_edge("warehouse_1", "product_2", relationship="stores")
    G.add_edge("warehouse_2", "product_2", relationship="stores")
    G.add_edge("warehouse_2", "product_3", relationship="stores")
    G.add_edge("event_1", "port_1", relationship="affects")
    G.add_edge("event_1", "route_2", relationship="affects")
    G.add_edge("event_2", "factory_3", relationship="affects")
    return G

def trace_root_cause(G, node_id):
    visited = set()
    path = []
    
    def _dfs(node):
        # 1. what do you do first when you visit a node?
        # Get the node's data
        node_data = G.nodes[node]
        
        # 2. how do you record that you've been here?
        visited.add(node)
        path.append(node)
        
        # 3. what do you iterate over?
        for pred in G.predecessors(node):
            
            # 4. what's the condition before recursing?
            if pred not in visited:
                _dfs(pred)
    
    _dfs(node_id)
    return path

def find_downstream_impact(G, node_id):
    visited = set()
    impacted = []
    queue = deque([node_id])
    
    # what goes here?
    # hint: standard BFS loop
    while queue:
        current=queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for succ in G.successors(current):
            if succ not in visited:
                impacted.append(succ)
                queue.append(succ)
    #critical = [n for n in impacted if G.nodes[n].get("priority") == "critical"]
    # print(critical)

    
    return impacted


# G = build_supply_chain_graph()
# print(f"Nodes: {G.number_of_nodes()}")
# print(f"Edges: {G.number_of_edges()}")
# print(trace_root_cause(G, "warehouse_1"))
# print(find_downstream_impact(G, "event_1"))
