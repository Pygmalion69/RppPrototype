from rpp.graph_loader import load_graphs
from rpp.required_edges import build_required_graph
from rpp.rpp_solver import solve_rpp
from rpp.gpx_export import export_gpx

G_drive, G_service = load_graphs("data/area.osm")
R = build_required_graph(G_service)

# IMPORTANT: the shortest paths should use G_drive (directed, filtered)
E = solve_rpp(G_drive, G_service, R)

export_gpx(E, G_service, "rpp_route.gpx")
print("Done. GPX written.")

