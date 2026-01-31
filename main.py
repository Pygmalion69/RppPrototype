import argparse

from rpp.graph_loader import load_graphs
from rpp.required_edges import build_required_graph_undirected
from rpp.rpp_solver import solve_rpp
from rpp.gpx_export import export_gpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--osm", default="data/area.osm", help="Path to .osm file")
    parser.add_argument(
        "--ignore-oneway",
        action="store_true",
        help="Treat one-way streets as bidirectional for driving graph shortest paths",
    )
    args = parser.parse_args()

    G_drive, G_service_undirected, _ = load_graphs(
        args.osm,
        ignore_oneway=args.ignore_oneway,
    )
    R = build_required_graph_undirected(G_service_undirected)
    E = solve_rpp(G_drive, G_service_undirected, R)

    export_gpx(E, G_service_undirected, "rpp_route.gpx")
    print("Done. GPX written: rpp_route.gpx")


if __name__ == "__main__":
    main()
