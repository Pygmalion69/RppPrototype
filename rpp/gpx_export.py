import gpxpy
import gpxpy.gpx
import networkx as nx


def export_gpx(E: nx.MultiGraph, G: nx.MultiGraph, filename: str):
    tour = list(nx.eulerian_circuit(E, keys=True))

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
