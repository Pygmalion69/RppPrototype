import networkx as nx

from rpp.required_edges import build_required_graph_directed
from rpp.rpp_solver import solve_drpp, solve_rpp


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
