from rpp.filters import is_driveable_edge
import networkx as nx

# Streets that must be serviced
REQUIRED_HIGHWAYS = {
    "residential",
    "living_street",
    "tertiary",
    "unclassified"
}

def build_required_graph_undirected(G_service_undirected: nx.MultiGraph) -> nx.Graph:
    R = nx.Graph()
    for u, v, data in G_service_undirected.edges(data=True):
        if not is_driveable_edge(data):
            continue
        hw = data.get("highway")
        if isinstance(hw, list):
            hw = hw[0]
        if hw in REQUIRED_HIGHWAYS:
            R.add_edge(u, v, weight=data["weight"])
    return R


def build_required_graph_directed(
    G_service_directed: nx.MultiDiGraph,
) -> nx.DiGraph:
    R = nx.DiGraph()
    for u, v, _key, data in G_service_directed.edges(keys=True, data=True):
        if not is_driveable_edge(data):
            continue
        hw = data.get("highway")
        if isinstance(hw, list):
            hw = hw[0]
        if hw in REQUIRED_HIGHWAYS:
            R.add_edge(u, v, weight=data["weight"])
    return R
