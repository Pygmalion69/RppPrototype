from __future__ import annotations

import argparse
import sys

from rpp.graph_loader import load_graphs
from rpp.required_edges import (
    build_required_graph_directed,
    build_required_graph_undirected,
)
from rpp.rpp_solver import (
    build_drpp_base_graph,
    build_rpp_base_graph,
    find_drpp_blocking_edges,
    solve_drpp,
    solve_rpp,
)
from rpp.gpx_export import export_edge_list_gpx, export_gpx, select_endpoint_nodes


def _parse_point(label: str, raw: str | None) -> tuple[float, float] | None:
    if raw is None:
        return None
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"--{label} must be provided as 'lat,lon'.")
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError as exc:
        raise ValueError(
            f"--{label} must contain valid numbers like '51.0,6.1'."
        ) from exc
    return lat, lon


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
    parser.add_argument(
        "--start",
        default=None,
        help="Optional start coordinate as 'lat,lon' to snap to the nearest node",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Optional end coordinate as 'lat,lon' to snap to the nearest node",
    )
    args = parser.parse_args()

    start_request = _parse_point("start", args.start)
    end_request = _parse_point("end", args.end)
    if end_request is not None and start_request is None:
        raise ValueError("--end requires --start.")

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
                print(
                    f"WARNING: Dropping {len(blocker_edges)} blocking required edges outside the largest SCC.",
                    file=sys.stderr,
                )
                for u, v in blocker_edges:
                    if R.has_edge(u, v):
                        R.remove_edge(u, v)
                isolates = [n for n in R.nodes if R.degree(n) == 0]
                if isolates:
                    R.remove_nodes_from(isolates)
        base_graph = build_drpp_base_graph(
            G_drive,
            G_service_directed,
            R,
            diagnostics_path=args.drpp_diagnostics,
        )
        if start_request is not None:
            (
                start_node,
                start_snap,
                start_dist,
                end_node,
                end_snap,
                end_dist,
                component_strategy,
            ) = select_endpoint_nodes(base_graph, G_service_directed, start_request, end_request)
            print(
                "Requested start (lat, lon): "
                f"({start_request[0]:.6f}, {start_request[1]:.6f}); "
                "snapped start (lat, lon): "
                f"({start_snap[0]:.6f}, {start_snap[1]:.6f}); "
                f"node={start_node}; distance_m={start_dist:.2f}; "
                f"component={component_strategy}"
            )
            if end_request is not None and end_node is not None and end_snap is not None and end_dist is not None:
                print(
                    "Requested end (lat, lon): "
                    f"({end_request[0]:.6f}, {end_request[1]:.6f}); "
                    "snapped end (lat, lon): "
                    f"({end_snap[0]:.6f}, {end_snap[1]:.6f}); "
                    f"node={end_node}; distance_m={end_dist:.2f}; "
                    f"component={component_strategy}"
                )
        else:
            start_node = None
            end_node = None
        E = solve_drpp(
            G_drive,
            G_service_directed,
            R,
            diagnostics_path=args.drpp_diagnostics,
            start_node=start_node,
            end_node=end_node,
            base_graph=base_graph,
        )
        export_gpx(E, G_service_directed, "rpp_route.gpx", start_node=start_node, end_node=end_node)
    else:
        R = build_required_graph_undirected(G_service_undirected)
        base_graph = build_rpp_base_graph(G_drive, G_service_undirected, R)
        if start_request is not None:
            (
                start_node,
                start_snap,
                start_dist,
                end_node,
                end_snap,
                end_dist,
                component_strategy,
            ) = select_endpoint_nodes(base_graph, G_service_undirected, start_request, end_request)
            print(
                "Requested start (lat, lon): "
                f"({start_request[0]:.6f}, {start_request[1]:.6f}); "
                "snapped start (lat, lon): "
                f"({start_snap[0]:.6f}, {start_snap[1]:.6f}); "
                f"node={start_node}; distance_m={start_dist:.2f}; "
                f"component={component_strategy}"
            )
            if end_request is not None and end_node is not None and end_snap is not None and end_dist is not None:
                print(
                    "Requested end (lat, lon): "
                    f"({end_request[0]:.6f}, {end_request[1]:.6f}); "
                    "snapped end (lat, lon): "
                    f"({end_snap[0]:.6f}, {end_snap[1]:.6f}); "
                    f"node={end_node}; distance_m={end_dist:.2f}; "
                    f"component={component_strategy}"
                )
        else:
            start_node = None
            end_node = None
        E = solve_rpp(
            G_drive,
            G_service_undirected,
            R,
            start_node=start_node,
            end_node=end_node,
            base_graph=base_graph,
        )
        export_gpx(E, G_service_undirected, "rpp_route.gpx", start_node=start_node, end_node=end_node)
    print("Done. GPX written: rpp_route.gpx")


if __name__ == "__main__":
    main()
