from rpp.graph_loader import load_graph
from rpp.required_edges import build_required_graph
from rpp.rpp_solver import solve_rpp
from rpp.gpx_export import export_gpx

G = load_graph("data/area.osm")
R = build_required_graph(G)
E = solve_rpp(G, R)

export_gpx(E, G, "rpp_route_first.gpx")

print("Done. GPX written.")
