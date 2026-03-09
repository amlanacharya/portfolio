import json
import copy
from pathlib import Path
import networkx as nx

DATA_FILE=Path(__file__).parent.parent/"data"/"supply_chain_graph.json"

class SupplyChainGraph