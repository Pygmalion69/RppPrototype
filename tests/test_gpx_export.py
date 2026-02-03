import networkx as nx

from rpp.gpx_export import select_start_node


def test_select_start_node_snaps_to_largest_component():
    G = nx.MultiGraph()
    G.add_node(1, x=0.0, y=0.0)
    G.add_node(2, x=0.0, y=0.1)
    G.add_edge(1, 2, key=0, weight=1)

    G.add_node(3, x=10.0, y=10.0)
    G.add_edge(3, 3, key=0, weight=1)

    start = (10.0, 10.0)
    node, coords, distance, strategy = select_start_node(G, G, start)

    assert node in {1, 2}
    assert strategy == "largest_component"
    assert coords in {(0.0, 0.0), (0.1, 0.0)}
    assert distance > 0
