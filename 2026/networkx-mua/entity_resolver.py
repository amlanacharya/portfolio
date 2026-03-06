import re
from collections import defaultdict
from typing import Dict

LOCATION_ALIASES: Dict[str, list] = {
    "visakhapatnam": ["vizag"],
    "kolkata": ["calcutta"],
    "chennai": ["madras"],
}


def build_entity_index(G) -> Dict[str, str]:
    """Build surface_form → node_id mapping from graph node attributes.

    Only unambiguous surface forms (those that resolve to exactly one node)
    are included. Ambiguous forms (e.g. "chennai" → factory_2 AND port_2)
    are silently omitted so resolve_entity() returns "unknown" for them.
    """
    candidates: Dict[str, list] = defaultdict(list)

    for node_id in G.nodes():
        data = G.nodes[node_id]
        surface_forms: set = set()

        # node_id itself (e.g. "port_1")
        surface_forms.add(node_id.lower())

        # name attribute (e.g. "vizag port")
        name = data.get("name", "")
        if name:
            surface_forms.add(name.lower())
            # first word of multi-word name (e.g. "tata" from "Tata Steel")
            words = name.split()
            if len(words) > 1:
                surface_forms.add(words[0].lower())

        # location attribute + aliases
        location = data.get("location", "")
        if location:
            loc_lower = location.lower()
            surface_forms.add(loc_lower)
            for alias in LOCATION_ALIASES.get(loc_lower, []):
                surface_forms.add(alias.lower())

        for form in surface_forms:
            candidates[form].append(node_id)

    # Keep only forms that map to a single node
    index: Dict[str, str] = {}
    for form, node_ids in candidates.items():
        unique = list(dict.fromkeys(node_ids))  # deduplicate, preserve order
        if len(unique) == 1:
            index[form] = unique[0]

    return index


def build_catalog_string(G) -> str:
    """Return a formatted table of all graph nodes for LLM system prompt injection."""
    lines = [
        f"{'node_id':<14} | {'name':<30} | {'location':<16} | type",
        "-" * 78,
    ]
    for node_id in sorted(G.nodes()):
        data = G.nodes[node_id]
        name = data.get("name", "")
        location = data.get("location", "")
        node_type = data.get("type", "")
        if hasattr(node_type, "value"):
            node_type = node_type.value
        lines.append(f"{node_id:<14} | {name:<30} | {location:<16} | {node_type}")
    return "\n".join(lines)


def resolve_entity(mention: str, index: Dict[str, str]) -> str:
    """Two-stage fuzzy match (no external libs).

    Stage 1: exact match on lowercased mention.
    Stage 2: substring containment (mention in key OR key in mention).
      - Exactly 1 unique candidate node_id → return it.
      - 0 or >1 candidates → return "unknown".
    """
    m = mention.lower().strip()

    if m in index:
        return index[m]

    matched: set = set()
    for form, node_id in index.items():
        if m in form or form in m:
            matched.add(node_id)

    if len(matched) == 1:
        return matched.pop()
    return "unknown"


def keyword_extract_node_id(query: str, index: Dict[str, str]) -> str:
    """Fallback entity extraction for keyword_router.

    Tries explicit node_id regex first (still valid for inputs like "port_1"),
    then falls back to resolve_entity().
    """
    match = re.search(
        r"(warehouse|port|factory|vendor|product|route|event)_\d+",
        query.lower(),
    )
    if match:
        return match.group(0)
    return resolve_entity(query, index)
