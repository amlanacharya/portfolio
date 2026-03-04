import copy
from collections import deque
from typing import Dict, List, Any, Optional
import networkx as nx

from knowledge_graph import (
    build_supply_chain_graph,
    trace_root_cause,
    find_downstream_impact
)

def query_state(G, node_id):
    if node_id not in G.nodes:
        return None
    return dict(G.nodes[node_id])

def find_root_cause(G,node_id):
    result=[]
    path=trace_root_cause(G,node_id)
    for node in path:
        attrs = query_state(G, node)
        attrs['id'] = node  
        result.append(attrs)
    return result

def simulate_change(G, node_id, changes):
    G_copy = copy.deepcopy(G)
    for k,v in changes.items():
        G_copy.nodes[node_id][k]=v

    impact_before = find_downstream_impact(G, node_id)
    impact_after = find_downstream_impact(G_copy, node_id)

    return {
        'original': query_state(G, node_id),
        'simulated': query_state(G_copy, node_id),
        'impact_before': impact_before,
        'impact_after': impact_after,
        'newly_affected': [n for n in impact_after if n not in impact_before],
        'no_longer_affected': [n for n in impact_before if n not in impact_after]
    }

def execute_action(G, node_id, changes):
    before = query_state(G, node_id)
    for k,v in changes.items():
        G.nodes[node_id][k] = v
    after = query_state(G, node_id)

    return {
        'node_id': node_id,
        'before': before,
        'after': after,
        'changes': changes
    }

G = build_supply_chain_graph()
# s=query_state(G, 'port_1')
# frc=find_root_cause(G,'port_1')
# sc=simulate_change(G, "port_1", {"status": "operational", "throughput": 1500})
#print(s)
#print(frc)
#print(sc)


