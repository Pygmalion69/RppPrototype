import osmnx as ox
import networkx as nx
from rpp.filters import filter_graph_edges

def load_graphs(osm_file: str):
    # Directed driving graph (keeps one-ways)
    G_drive = ox.graph_from_xml(osm_file, simplify=True)

    # Ensure CRS exists (graph_from_xml may not set it)
    G_drive.graph.setdefault("crs", "EPSG:4326")

    # Filter out foot/cycle/parking aisles etc.
    G_drive = filter_graph_edges(G_drive)

    # Keep the largest weakly connected component (directed graph)
    if not nx.is_weakly_connected(G_drive):
        largest = max(nx.weakly_connected_components(G_drive), key=len)
        G_drive = G_drive.subgraph(largest).copy()

    # Add weights
    for u, v, k, data in G_drive.edges(keys=True, data=True):
        data["weight"] = data.get("length", 1.0)

    # Undirected service graph for "required edges" extraction
    G_service = ox.convert.to_undirected(G_drive)
    return G_drive, G_service

