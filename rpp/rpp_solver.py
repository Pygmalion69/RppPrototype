import itertools
import networkx as nx


def solve_rpp(G: nx.MultiGraph, R: nx.Graph) -> nx.MultiGraph:
    # --- Step 1: connect required components (record paths only) ---
    components = list(nx.connected_components(R))
    reps = [next(iter(c)) for c in components]

    connector_paths = []

    for a, b in zip(reps[:-1], reps[1:]):
        _, path = nx.single_source_dijkstra(G, a, b, weight="weight")
        connector_paths.append(path)

    # --- Step 2: build Eulerian multigraph with geometry ---
    E = nx.MultiGraph()

    # required edges
    for u, v in R.edges():
        add_edge_with_geometry(E, G, u, v)

    # connector edges
    for path in connector_paths:
        for u, v in zip(path[:-1], path[1:]):
            add_edge_with_geometry(E, G, u, v)

    # --- Step 3: fix odd degrees ---
    odd = [n for n in E.nodes if E.degree(n) % 2 == 1]

    K = nx.Graph()
    sp_cache = {}

    for u, v in itertools.combinations(odd, 2):
        dist, path = nx.single_source_dijkstra(G, u, v, weight="weight")
        K.add_edge(u, v, weight=dist)
        sp_cache[(u, v)] = path

    matching = nx.algorithms.matching.min_weight_matching(K, weight="weight")

    for u, v in matching:
        # normalize pair
        key = (u, v) if (u, v) in sp_cache else (v, u)
        path = sp_cache[key]

        for a, b in zip(path[:-1], path[1:]):
            add_edge_with_geometry(E, G, a, b)

    # --- Step 4: final invariants ---
    assert nx.is_connected(E), "RPP result is not connected"
    assert nx.is_eulerian(E), "RPP result is not Eulerian"

    return E


def add_edge_with_geometry(E: nx.MultiGraph, G: nx.MultiGraph, u, v):
    edge_candidates = G.get_edge_data(u, v)

    if not edge_candidates:
        raise RuntimeError(f"No edge data in G for ({u}, {v})")

    # 1) Prefer edges WITH geometry
    with_geom = [
        d for d in edge_candidates.values()
        if d.get("geometry") is not None
    ]

    if with_geom:
        data = min(with_geom, key=lambda d: d["weight"])
    else:
        # fallback only if unavoidable
        data = min(edge_candidates.values(), key=lambda d: d["weight"])

    E.add_edge(
        u,
        v,
        weight=data["weight"],
        geometry=data.get("geometry")
    )

