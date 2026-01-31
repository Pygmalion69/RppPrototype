import argparse

from rpp.graph_loader import load_graphs
from rpp.required_edges import (
    build_required_graph_directed,
    build_required_graph_undirected,
)
from rpp.rpp_solver import solve_drpp, solve_rpp
from rpp.gpx_export import export_gpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--osm", default="data/area.osm", help="Path to .osm file")
    parser.add_argument(
        "--ignore-oneway",
        action="store_true",
        help="Treat one-way streets as bidirectional for driving graph shortest paths",
    )
    parser.add_argument(
        "--directed-service",
        action="store_true",
        help="Use directed service graph with directed required edges",
    )
    args = parser.parse_args()

    G_drive, G_service_undirected, G_service_directed = load_graphs(
        args.osm,
        ignore_oneway=args.ignore_oneway,
    )

    if args.directed_service:
        R = build_required_graph_directed(G_service_directed)
        E = solve_drpp(G_drive, G_service_directed, R)
        export_gpx(E, G_service_directed, "rpp_route.gpx")
    else:
        R = build_required_graph_undirected(G_service_undirected)
        E = solve_rpp(G_drive, G_service_undirected, R)
        export_gpx(E, G_service_undirected, "rpp_route.gpx")
    print("Done. GPX written: rpp_route.gpx")


if __name__ == "__main__":
    main()
