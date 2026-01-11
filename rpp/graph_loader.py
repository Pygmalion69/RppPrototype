import osmnx as ox
import networkx as nx


def load_graph(osm_file: str) -> nx.MultiGraph:
    G = ox.graph_from_xml(osm_file, simplify=True)
    G = ox.convert.to_undirected(G)

    # Keep largest connected component
    if not nx.is_connected(G):
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

    # Ensure weights
    for u, v, k, data in G.edges(keys=True, data=True):
        if "length" in data:
            data["weight"] = data["length"]
        else:
            x1, y1 = G.nodes[u]["x"], G.nodes[u]["y"]
            x2, y2 = G.nodes[v]["x"], G.nodes[v]["y"]
            data["weight"] = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    return G
