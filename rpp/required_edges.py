import networkx as nx
from typing import Set

REQUIRED_HIGHWAYS: Set[str] = {
    "residential",
    "living_street",
    "unclassified",
    "service",
}


def build_required_graph(G: nx.MultiGraph) -> nx.Graph:
    R = nx.Graph()

    for u, v, data in G.edges(data=True):
        hw = data.get("highway")
        if isinstance(hw, list):
            hw = hw[0]

        if hw in REQUIRED_HIGHWAYS:
            R.add_edge(u, v, weight=data["weight"])

    return R
