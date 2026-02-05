from __future__ import annotations

import math

import gpxpy
import gpxpy.gpx
import networkx as nx


def export_gpx(
    E: nx.MultiGraph,
    G: nx.MultiGraph,
    filename: str,
    start: tuple[float, float] | None = None,
):
    if start is None:
        tour = list(nx.eulerian_circuit(E, keys=True))
    else:
        start_node, snapped, distance_m, component_strategy = select_start_node(E, G, start)
        print(
            "Requested start (lat, lon): "
            f"({start[0]:.6f}, {start[1]:.6f}); "
            "snapped start (lat, lon): "
            f"({snapped[0]:.6f}, {snapped[1]:.6f}); "
            f"node={start_node}; distance_m={distance_m:.2f}; "
            f"component={component_strategy}"
        )
        tour = list(nx.eulerian_circuit(E, source=start_node, keys=True))

    gpx = gpxpy.gpx.GPX()
    trk = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(trk)
    seg = gpxpy.gpx.GPXTrackSegment()
    trk.segments.append(seg)

    last_point = None

    for u, v, k in tour:
        data = E.get_edge_data(u, v, k)
        geom = data.get("geometry")

        if geom is None:
            coords = [
                (G.nodes[u]["x"], G.nodes[u]["y"]),
                (G.nodes[v]["x"], G.nodes[v]["y"]),
            ]
        else:
            coords = list(geom.coords)

            ux, uy = G.nodes[u]["x"], G.nodes[u]["y"]
            vx, vy = G.nodes[v]["x"], G.nodes[v]["y"]

            start = coords[0]
            end = coords[-1]

            du_start = dist2(start, (ux, uy))
            dv_start = dist2(start, (vx, vy))
            du_end = dist2(end, (ux, uy))
            dv_end = dist2(end, (vx, vy))

            if not (du_start <= dv_start and dv_end <= du_end):
                coords.reverse()

        for x, y in coords:
            pt = (y, x)

            # avoid zero-length or jump duplicates
            if last_point != pt:
                seg.points.append(gpxpy.gpx.GPXTrackPoint(y, x))
                last_point = pt

    with open(filename, "w") as f:
        f.write(gpx.to_xml())


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def select_start_node(
    E: nx.MultiGraph,
    G: nx.MultiGraph,
    start: tuple[float, float],
) -> tuple[int, tuple[float, float], float, str]:
    component_nodes, component_strategy = _select_component_nodes(E)

    start_lat, start_lon = start
    best_node = None
    best_distance = None
    best_coords = None
    for node in component_nodes:
        node_data = G.nodes.get(node)
        if node_data is None:
            continue
        if "x" not in node_data or "y" not in node_data:
            raise ValueError("Node coordinate attributes x/y missing for start point snapping.")
        node_lon = node_data["x"]
        node_lat = node_data["y"]
        distance = haversine_m(start_lat, start_lon, node_lat, node_lon)
        if best_distance is None or distance < best_distance:
            best_node = node
            best_distance = distance
            best_coords = (node_lat, node_lon)

    if best_node is None or best_distance is None or best_coords is None:
        raise ValueError("Unable to snap start point: no nodes with coordinates found.")

    return best_node, best_coords, best_distance, component_strategy


def _select_component_nodes(E: nx.MultiGraph) -> tuple[set[int], str]:
    if E.number_of_nodes() == 0:
        raise ValueError("Cannot select start node from empty graph.")

    if nx.is_directed(E):
        components = list(nx.weakly_connected_components(E))
    else:
        components = list(nx.connected_components(E))

    if not components:
        raise ValueError("Cannot select start node from graph with no components.")

    largest = max(components, key=len)
    return set(largest), "largest_component"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_m * c


def export_edge_list_gpx(G: nx.MultiGraph, edges, filename: str):
    gpx = gpxpy.gpx.GPX()
    trk = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(trk)

    for u, v in edges:
        data = _best_edge_data(G, u, v)
        geom = data.get("geometry")
        ux, uy = G.nodes[u]["x"], G.nodes[u]["y"]
        vx, vy = G.nodes[v]["x"], G.nodes[v]["y"]
        if geom is None:
            coords = [(ux, uy), (vx, vy)]
        else:
            coords = list(geom.coords)

        start = coords[0]
        end = coords[-1]

        du_start = dist2(start, (ux, uy))
        dv_start = dist2(start, (vx, vy))
        du_end = dist2(end, (ux, uy))
        dv_end = dist2(end, (vx, vy))

        if not (du_start <= dv_start and dv_end <= du_end):
            coords.reverse()

        seg = gpxpy.gpx.GPXTrackSegment()
        trk.segments.append(seg)
        for x, y in coords:
            seg.points.append(gpxpy.gpx.GPXTrackPoint(y, x))

    with open(filename, "w") as f:
        f.write(gpx.to_xml())


def _best_edge_data(G: nx.MultiGraph, u, v):
    edge_candidates = G.get_edge_data(u, v)
    if not edge_candidates:
        raise RuntimeError(f"No edge data in G for ({u}, {v})")

    with_geom = [d for d in edge_candidates.values() if d.get("geometry") is not None]
    if with_geom:
        return min(with_geom, key=lambda d: d.get("weight", d.get("length", 1.0)))
    return min(edge_candidates.values(), key=lambda d: d.get("weight", d.get("length", 1.0)))
