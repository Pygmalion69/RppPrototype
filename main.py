import argparse

from rpp.graph_loader import load_graphs
from rpp.required_edges import (
    build_required_graph_directed,
    build_required_graph_undirected,
)
from rpp.rpp_solver import find_drpp_blocking_edges, solve_drpp, solve_rpp
from rpp.gpx_export import export_edge_list_gpx, export_gpx


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
    parser.add_argument(
        "--drpp-diagnostics",
        default=None,
        help="Write DRPP diagnostics report to this path",
    )
    parser.add_argument(
        "--drop-drpp-blockers",
        action="store_true",
        help="Drop required edges outside the largest SCC before solving DRPP",
    )
    parser.add_argument(
        "--drpp-blockers-gpx",
        default=None,
        help="Write blocking required edges to this GPX path",
    )
    args = parser.parse_args()

    G_drive, G_service_undirected, G_service_directed = load_graphs(
        args.osm,
        ignore_oneway=args.ignore_oneway,
    )

    if args.directed_service:
        R = build_required_graph_directed(G_service_directed)
        if args.drop_drpp_blockers or args.drpp_blockers_gpx:
            blockers, _required_outside, _scc_index, _scc_sizes, _largest = find_drpp_blocking_edges(
                G_drive, R
            )
            blocker_edges = [(u, v) for u, v, _su, _sv in blockers]

            if args.drpp_blockers_gpx and blocker_edges:
                export_edge_list_gpx(
                    G_service_directed,
                    blocker_edges,
                    args.drpp_blockers_gpx,
                )

            if args.drop_drpp_blockers and blocker_edges:
                for u, v in blocker_edges:
                    if R.has_edge(u, v):
                        R.remove_edge(u, v)
        E = solve_drpp(
            G_drive,
            G_service_directed,
            R,
            diagnostics_path=args.drpp_diagnostics,
        )
        export_gpx(E, G_service_directed, "rpp_route.gpx")
    else:
        R = build_required_graph_undirected(G_service_undirected)
        E = solve_rpp(G_drive, G_service_undirected, R)
        export_gpx(E, G_service_undirected, "rpp_route.gpx")
    print("Done. GPX written: rpp_route.gpx")


if __name__ == "__main__":
    main()
