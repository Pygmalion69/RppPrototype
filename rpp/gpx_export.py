from __future__ import annotations

import math

import gpxpy
import gpxpy.gpx
import networkx as nx


def export_gpx(
    E: nx.MultiGraph,
    G: nx.MultiGraph,
    filename: str,
    *,
    start_node=None,
    end_node=None,
):
    if end_node is not None and start_node is None:
        raise ValueError("end_node requires start_node for GPX export.")
    open_route = end_node is not None and start_node is not None and end_node != start_node

    if start_node is None:
        tour = list(nx.eulerian_circuit(E, keys=True))
    else:
        if open_route:
            tour = list(nx.eulerian_path(E, source=start_node, keys=True))
        else:
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
    node, coords, distance = _select_nearest_node(component_nodes, G, start)
    return node, coords, distance, component_strategy


def select_end_node(
    E: nx.MultiGraph,
    G: nx.MultiGraph,
    end: tuple[float, float],
) -> tuple[int, tuple[float, float], float, str]:
    component_nodes, component_strategy = _select_component_nodes(E)
    node, coords, distance = _select_nearest_node(component_nodes, G, end)
    return node, coords, distance, component_strategy


def select_endpoint_nodes(
    E: nx.MultiGraph,
    G: nx.MultiGraph,
    start: tuple[float, float],
    end: tuple[float, float] | None,
) -> tuple[
    int,
    tuple[float, float],
    float,
    int | None,
    tuple[float, float] | None,
    float | None,
    str,
]:
    component_nodes, component_strategy = _select_component_nodes(E)
    start_node, start_coords, start_distance = _select_nearest_node(component_nodes, G, start)
    if end is None:
        return start_node, start_coords, start_distance, None, None, None, component_strategy
    end_node, end_coords, end_distance = _select_nearest_node(component_nodes, G, end)
    return (
        start_node,
        start_coords,
        start_distance,
        end_node,
        end_coords,
        end_distance,
        component_strategy,
    )


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


def _select_nearest_node(
    component_nodes: set[int],
    G: nx.MultiGraph,
    target: tuple[float, float],
) -> tuple[int, tuple[float, float], float]:
    target_lat, target_lon = target
    best_node = None
    best_distance = None
    best_coords = None
    for node in component_nodes:
        node_data = G.nodes.get(node)
        if node_data is None:
            continue
        if "x" not in node_data or "y" not in node_data:
            raise ValueError("Node coordinate attributes x/y missing for point snapping.")
        node_lon = node_data["x"]
        node_lat = node_data["y"]
        distance = haversine_m(target_lat, target_lon, node_lat, node_lon)
        if best_distance is None or distance < best_distance:
            best_node = node
            best_distance = distance
            best_coords = (node_lat, node_lon)

    if best_node is None or best_distance is None or best_coords is None:
        raise ValueError("Unable to snap point: no nodes with coordinates found.")

    return best_node, best_coords, best_distance


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
