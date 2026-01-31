import osmnx as ox
import networkx as nx

from rpp.filters import filter_graph_edges


def load_graphs(osm_file: str, ignore_oneway: bool = False):
    # Load raw (directed, one-way aware)
    G_raw = ox.graph_from_xml(osm_file, simplify=True)
    G_raw.graph.setdefault("crs", "EPSG:4326")

    # Filter edges (IMPORTANT: filter_graph_edges must copy G.graph metadata)
    G_filt = filter_graph_edges(G_raw)

    # Keep largest weakly connected component (directed)
    if not nx.is_weakly_connected(G_filt):
        largest = max(nx.weakly_connected_components(G_filt), key=len)
        G_filt = G_filt.subgraph(largest).copy()

    # Ensure weights on the filtered graph
    for u, v, k, data in G_filt.edges(keys=True, data=True):
        data["weight"] = data.get("length", 1.0)

    # Driving graph: directed or undirected depending on flag
    if ignore_oneway:
        # Undirected driving graph ignores one-ways for shortest paths
        G_drive = ox.convert.to_undirected(G_filt)
    else:
        # Directed driving graph respects one-ways
        G_drive = G_filt

    # Service graph for required edges + geometry lookup is always undirected
    G_service = ox.convert.to_undirected(G_filt)

    return G_drive, G_service
