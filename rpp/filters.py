from __future__ import annotations

from typing import Any, Iterable
import networkx as nx


EXCLUDED_HIGHWAYS = {
    "footway", "pedestrian", "steps", "path", "corridor",
    "cycleway",
}

# Some OSM encoders put multiple values in a single string
EXCLUDED_HIGHWAY_TOKENS = {
    "footway", "pedestrian", "steps", "path", "corridor", "cycleway",
}


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def _highway_has_excluded_token(highway_value: Any) -> bool:
    vals = _as_list(highway_value)
    for s in vals:
        # handle "cycleway;footway" etc.
        tokens = [t.strip() for t in s.split(";")]
        if any(t in EXCLUDED_HIGHWAY_TOKENS for t in tokens):
            return True
        if s in EXCLUDED_HIGHWAYS:
            return True
    return False


def is_driveable_edge(data: dict) -> bool:
    """
    Decide whether an edge is allowed in the vehicle/driving graph.
    """
    # Exclude explicit non-driveable highway types
    if _highway_has_excluded_token(data.get("highway")):
        return False

    # Exclude parking aisles
    if str(data.get("service", "")).strip().lower() == "parking_aisle":
        return False

    # Exclude where motor vehicles are disallowed (common on foot/cycle paths)
    for k in ("motor_vehicle", "vehicle"):
        v = data.get(k)
        if v is not None and str(v).strip().lower() in {"no", "private"}:
            return False

    # Optional: exclude private access altogether (uncomment if desired)
    access = str(data.get("access", "")).strip().lower()
    if access in {"private", "no"}:
        return False

    return True


def filter_graph_edges(G: nx.MultiDiGraph | nx.MultiGraph) -> nx.MultiDiGraph | nx.MultiGraph:
    H = G.__class__()  # keep MultiDiGraph vs MultiGraph

    # Copy OSMnx graph metadata (crs, etc.)
    H.graph.update(G.graph)

    H.add_nodes_from(G.nodes(data=True))

    for u, v, k, data in G.edges(keys=True, data=True):
        if is_driveable_edge(data):
            H.add_edge(u, v, key=k, **data)

    return H

