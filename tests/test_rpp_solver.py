import networkx as nx

from rpp.required_edges import build_required_graph_directed
from rpp.rpp_solver import (
    build_drpp_base_graph,
    build_rpp_base_graph,
    solve_drpp,
    solve_rpp,
)


def _add_directed_edge(G, u, v, weight=1.0, highway="residential"):
    G.add_edge(u, v, weight=weight, highway=highway, geometry=None)


def _add_undirected_edge(G, u, v, weight=1.0, highway="residential"):
    G.add_edge(u, v, weight=weight, highway=highway, geometry=None)


def test_build_required_graph_directed_filters_directional_arcs():
    G = nx.MultiDiGraph()
    _add_directed_edge(G, "A", "B", highway="residential")
    _add_directed_edge(G, "B", "A", highway="secondary")
    _add_directed_edge(G, "B", "C", highway="footway")

    R = build_required_graph_directed(G)

    assert set(R.edges()) == {("A", "B")}


def test_solve_drpp_respects_one_way_arcs_and_is_eulerian():
    G_drive = nx.MultiDiGraph()
    _add_directed_edge(G_drive, "A", "B")
    _add_directed_edge(G_drive, "B", "C")
    _add_directed_edge(G_drive, "C", "A")

    G_service = nx.MultiDiGraph(G_drive)
    R = nx.DiGraph()
    R.add_edge("A", "B")

    result = solve_drpp(G_drive, G_service, R)

    assert nx.is_eulerian(result)

    allowed_arcs = set(G_service.edges())
    assert set(result.edges()).issubset(allowed_arcs)


def test_solve_rpp_regression_undirected_eulerian():
    G_drive = nx.MultiDiGraph()
    _add_directed_edge(G_drive, "A", "B")
    _add_directed_edge(G_drive, "B", "A")
    _add_directed_edge(G_drive, "B", "C")
    _add_directed_edge(G_drive, "C", "B")

    G_service = nx.MultiGraph()
    _add_undirected_edge(G_service, "A", "B")
    _add_undirected_edge(G_service, "B", "C")

    R = nx.Graph()
    R.add_edge("A", "B")
    R.add_edge("B", "C")

    result = solve_rpp(G_drive, G_service, R)

    assert nx.is_eulerian(result)


def test_solve_rpp_open_route_uses_start_end():
    G_drive = nx.MultiDiGraph()
    _add_directed_edge(G_drive, "A", "B")
    _add_directed_edge(G_drive, "B", "A")
    _add_directed_edge(G_drive, "B", "C")
    _add_directed_edge(G_drive, "C", "B")

    G_service = nx.MultiGraph()
    _add_undirected_edge(G_service, "A", "B")
    _add_undirected_edge(G_service, "B", "C")

    R = nx.Graph()
    R.add_edge("A", "B")
    R.add_edge("B", "C")

    base_graph = build_rpp_base_graph(G_drive, G_service, R)
    result = solve_rpp(
        G_drive,
        G_service,
        R,
        start_node="A",
        end_node="C",
        base_graph=base_graph,
    )

    odd_after = {n for n in result.nodes if result.degree(n) % 2 == 1}
    assert odd_after == {"A", "C"}
    assert nx.has_eulerian_path(result)


def test_solve_drpp_open_route_uses_start_end():
    G_drive = nx.MultiDiGraph()
    _add_directed_edge(G_drive, "A", "B")
    _add_directed_edge(G_drive, "B", "C")
    _add_directed_edge(G_drive, "C", "A")

    G_service = nx.MultiDiGraph(G_drive)
    R = nx.DiGraph()
    R.add_edge("A", "B")

    base_graph = build_drpp_base_graph(G_drive, G_service, R)
    result = solve_drpp(
        G_drive,
        G_service,
        R,
        start_node="A",
        end_node="C",
        base_graph=base_graph,
    )

    delta_after = {n: result.out_degree(n) - result.in_degree(n) for n in result.nodes}
    assert delta_after["A"] == 1
    assert delta_after["C"] == -1
    assert all(d == 0 for n, d in delta_after.items() if n not in {"A", "C"})
    assert nx.has_eulerian_path(result)
