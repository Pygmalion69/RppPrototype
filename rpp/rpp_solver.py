import itertools
import networkx as nx


def solve_rpp(
    G_drive: nx.Graph,  # <- accepts MultiDiGraph OR MultiGraph
    G_service: nx.MultiGraph,
    R: nx.Graph,
) -> nx.MultiGraph:
    """
    Solve an RPP-like problem where:
      - R defines the REQUIRED edges to be serviced (undirected)
      - shortest paths for CONNECTORS + MATCHING are computed on G_drive (directed, one-way aware)
      - edge geometry is taken from G_service (undirected view of the drivable network)

    Returns:
      - E: nx.MultiGraph, Eulerian multigraph whose edges include:
            weight: float
            geometry: shapely LineString or None (should be mostly present)
            kind: "required" | "connector" | "duplicate"
    """

    # ---- Step 0: connect required-edge components (using directed driving graph) ----
    components = list(nx.connected_components(R))
    reps = [next(iter(c)) for c in components]

    connector_paths = []
    for a, b in zip(reps[:-1], reps[1:]):
        # Directed shortest path respects one-ways
        try:
            _, path = nx.single_source_dijkstra(G_drive, a, b, weight="weight")
        except nx.NetworkXNoPath:
            # If the directed graph cannot connect components due to one-ways,
            # try the reverse direction (common around one-way rings), else fail clearly.
            try:
                _, path = nx.single_source_dijkstra(G_drive, b, a, weight="weight")
                path = list(reversed(path))
            except nx.NetworkXNoPath as e:
                raise RuntimeError(f"No directed path between required components: {a} <-> {b}") from e

        connector_paths.append(path)

    # ---- Step 1: Build Eulerian multigraph E with geometry (from service graph) ----
    E = nx.MultiGraph()

    # Required edges
    for u, v in R.edges():
        add_edge_with_geometry(E, G_service, u, v, kind="required")

    # Connector edges to join components
    for path in connector_paths:
        for u, v in zip(path[:-1], path[1:]):
            add_edge_with_geometry(E, G_service, u, v, kind="connector")

    # ---- Step 2: Fix odd degrees via min-weight matching (distances from directed graph) ----
    odd = [n for n in E.nodes if E.degree(n) % 2 == 1]
    if len(odd) % 2 != 0:
        raise RuntimeError(f"Odd node count is not even: {len(odd)}")

    # Build complete graph on odd nodes with directed shortest-path distances
    K = nx.Graph()
    sp_cache = {}

    for u, v in itertools.combinations(odd, 2):
        try:
            dist, path = nx.single_source_dijkstra(G_drive, u, v, weight="weight")
            K.add_edge(u, v, weight=dist)
            sp_cache[(u, v)] = path
        except nx.NetworkXNoPath:
            # If u->v doesn't exist due to direction, try v->u and reverse the path
            try:
                dist, path = nx.single_source_dijkstra(G_drive, v, u, weight="weight")
                K.add_edge(u, v, weight=dist)
                sp_cache[(u, v)] = list(reversed(path))
            except nx.NetworkXNoPath:
                # Leave this pair out; matching will fail if graph becomes disconnected.
                pass

    # Ensure matching graph is connected enough
    if K.number_of_nodes() != len(odd):
        missing = set(odd) - set(K.nodes())
        raise RuntimeError(f"Matching graph missing nodes (no paths found): {sorted(missing)[:10]}...")

    matching = nx.algorithms.matching.min_weight_matching(K, weight="weight")

    # Add matched shortest paths as DUPLICATED traversals
    for u, v in matching:
        # Normalize for cache
        key = (u, v) if (u, v) in sp_cache else (v, u)
        path = sp_cache[key]

        for a, b in zip(path[:-1], path[1:]):
            add_edge_with_geometry(E, G_service, a, b, kind="duplicate")

    # ---- Step 3: final invariants ----
    if not nx.is_connected(E):
        raise RuntimeError("RPP result is not connected (after connectors + matching).")

    if not nx.is_eulerian(E):
        odd_after = [n for n in E.nodes if E.degree(n) % 2 == 1]
        raise RuntimeError(f"RPP result is not Eulerian. Odd nodes remaining: {len(odd_after)}")

    return E


def solve_drpp(
    G_drive: nx.MultiDiGraph,
    G_service_directed: nx.MultiDiGraph,
    R: nx.DiGraph,
) -> nx.MultiDiGraph:
    """
    Solve a directed RPP-like problem where:
      - R defines the REQUIRED arcs to be serviced (directed)
      - shortest paths for CONNECTORS + DUPLICATES are computed on G_drive (directed, one-way aware)
      - edge geometry is taken from G_service_directed (directed view of the drivable network)

    Returns:
      - E: nx.MultiDiGraph, Eulerian multigraph whose edges include:
            weight: float
            geometry: shapely LineString or None (should be mostly present)
            kind: "required" | "connector" | "duplicate"
    """

    # ---- Step 0: connect required-arc components (using directed driving graph) ----
    components = list(nx.strongly_connected_components(R))
    reps = [next(iter(c)) for c in components]

    connector_paths = []
    for a, b in zip(reps[:-1], reps[1:]):
        try:
            _, path = nx.single_source_dijkstra(G_drive, a, b, weight="weight")
        except nx.NetworkXNoPath:
            try:
                _, path = nx.single_source_dijkstra(G_drive, b, a, weight="weight")
                path = list(reversed(path))
            except nx.NetworkXNoPath as e:
                raise RuntimeError(f"No directed path between required components: {a} <-> {b}") from e

        connector_paths.append(path)

    # ---- Step 1: Build Eulerian multigraph E with geometry (from service graph) ----
    E = nx.MultiDiGraph()

    # Required arcs
    for u, v in R.edges():
        add_arc_with_geometry(E, G_service_directed, u, v, kind="required")

    # Connector arcs to join components
    for path in connector_paths:
        for u, v in zip(path[:-1], path[1:]):
            add_arc_with_geometry(E, G_service_directed, u, v, kind="connector")

    # ---- Step 2: Balance in/out degrees via min-cost flow ----
    delta = {n: E.out_degree(n) - E.in_degree(n) for n in E.nodes}
    d_minus = [n for n, d in delta.items() if d < 0]
    d_plus = [n for n, d in delta.items() if d > 0]

    if d_minus or d_plus:
        sp_cache = {}
        flow_graph = nx.DiGraph()

        for n in d_minus:
            flow_graph.add_node(n, demand=delta[n])
        for n in d_plus:
            flow_graph.add_node(n, demand=delta[n])

        for i in d_minus:
            for j in d_plus:
                try:
                    dist, path = nx.single_source_dijkstra(G_drive, i, j, weight="weight")
                except nx.NetworkXNoPath as e:
                    raise RuntimeError(f"No directed path for imbalance repair: {i} -> {j}") from e

                sp_cache[(i, j)] = path
                flow_graph.add_edge(i, j, weight=dist, capacity=float("inf"))

        flow_result = nx.algorithms.flow.min_cost_flow(flow_graph)

        for i in d_minus:
            for j in d_plus:
                if flow_result[i].get(j, 0) > 0:
                    path = sp_cache[(i, j)]
                    for a, b in zip(path[:-1], path[1:]):
                        add_arc_with_geometry(E, G_service_directed, a, b, kind="duplicate")

    # ---- Step 3: final invariants ----
    for n in E.nodes:
        if E.out_degree(n) != E.in_degree(n):
            raise RuntimeError(f"Directed imbalance remains at {n}: out={E.out_degree(n)}, in={E.in_degree(n)}")

    if not nx.is_eulerian(E):
        raise RuntimeError("Directed RPP result is not Eulerian.")

    return E


def add_edge_with_geometry(
    E: nx.MultiGraph,
    G_service: nx.MultiGraph,
    u,
    v,
    kind: str,
):
    """
    Add an edge (u,v) to E using geometry/weight from G_service.
    Prefer candidates with geometry to avoid straight-line fallbacks.
    Do NOT pass a key so MultiGraph can represent duplicates.
    """
    edge_candidates = G_service.get_edge_data(u, v)
    if not edge_candidates:
        raise RuntimeError(f"No edge data in G_service for ({u}, {v})")

    # Prefer candidates with geometry
    with_geom = [d for d in edge_candidates.values() if d.get("geometry") is not None]

    if with_geom:
        data = min(with_geom, key=lambda d: d.get("weight", d.get("length", 1.0)))
    else:
        data = min(edge_candidates.values(), key=lambda d: d.get("weight", d.get("length", 1.0)))

    weight = data.get("weight", data.get("length", 1.0))
    geom = data.get("geometry")

    E.add_edge(
        u,
        v,
        weight=weight,
        geometry=geom,
        kind=kind,
    )


def add_arc_with_geometry(
    E: nx.MultiDiGraph,
    G_service_directed: nx.MultiDiGraph,
    u,
    v,
    kind: str,
):
    """
    Add a directed arc (u,v) to E using geometry/weight from G_service_directed.
    Prefer candidates with geometry to avoid straight-line fallbacks.
    Do NOT pass a key so MultiDiGraph can represent duplicates.
    """
    edge_candidates = G_service_directed.get_edge_data(u, v)
    if not edge_candidates:
        raise RuntimeError(f"No edge data in G_service_directed for ({u}, {v})")

    with_geom = [d for d in edge_candidates.values() if d.get("geometry") is not None]

    if with_geom:
        data = min(with_geom, key=lambda d: d.get("weight", d.get("length", 1.0)))
    else:
        data = min(edge_candidates.values(), key=lambda d: d.get("weight", d.get("length", 1.0)))

    weight = data.get("weight", data.get("length", 1.0))
    geom = data.get("geometry")

    E.add_edge(
        u,
        v,
        weight=weight,
        geometry=geom,
        kind=kind,
    )
