from rpp.filters import is_driveable_edge
import networkx as nx

# Streets that must be serviced
REQUIRED_HIGHWAYS = {
    "residential",
    "living_street",
    "unclassified"
}

def build_required_graph(G_service: nx.MultiGraph) -> nx.Graph:
    R = nx.Graph()
    for u, v, data in G_service.edges(data=True):
        if not is_driveable_edge(data):
            continue
        hw = data.get("highway")
        if isinstance(hw, list):
            hw = hw[0]
        if hw in REQUIRED_HIGHWAYS:
            R.add_edge(u, v, weight=data["weight"])
    return R
