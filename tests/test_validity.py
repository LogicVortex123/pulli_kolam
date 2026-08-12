import networkx as nx

from engine.validity import check_self_consistency, check_validity, is_valid_single_stroke


def cycle_multigraph(n: int) -> nx.MultiGraph:
    G = nx.MultiGraph()
    pts = [(i, 0) for i in range(n)]
    G.add_nodes_from(pts)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        G.add_edge(a, b)
    return G


def test_closed_loop_passes_validity_gate():
    G = cycle_multigraph(6)
    result = check_validity(G)
    assert result["is_eulerian_circuit"] is True
    assert result["has_eulerian_path"] is True
    assert result["largest_component_covers_all_nodes"] is True
    assert is_valid_single_stroke(G) is True


def test_disconnected_graph_fails_validity_gate():
    G = nx.disjoint_union(cycle_multigraph(4), cycle_multigraph(4))
    result = check_validity(G)
    assert result["connected_components"] == 2
    assert result["largest_component_covers_all_nodes"] is False
    assert is_valid_single_stroke(G) is False


def test_more_than_two_odd_degree_vertices_fails_validity_gate():
    # A "plus" shape: center connected to 4 arms. Center has degree 4
    # (even), each arm has degree 1 (odd) -> 4 odd-degree vertices ->
    # no Eulerian circuit and no Eulerian path, despite being connected.
    G = nx.MultiGraph()
    center = (0, 0)
    arms = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    G.add_node(center)
    for a in arms:
        G.add_edge(center, a)
    result = check_validity(G)
    assert result["connected_components"] == 1
    assert result["largest_component_covers_all_nodes"] is True
    assert result["is_eulerian_circuit"] is False
    assert result["has_eulerian_path"] is False
    assert is_valid_single_stroke(G) is False


def test_open_single_stroke_passes_via_eulerian_path():
    # A path graph (not closed): valid single stroke, pen never lifted,
    # but start != end so it's an Eulerian path, not a circuit.
    G = nx.MultiGraph()
    pts = [(i, 0) for i in range(5)]
    G.add_nodes_from(pts)
    for a, b in zip(pts, pts[1:]):
        G.add_edge(a, b)
    result = check_validity(G)
    assert result["is_eulerian_circuit"] is False
    assert result["has_eulerian_path"] is True
    assert is_valid_single_stroke(G) is True


def test_self_consistency_exact_match():
    G1 = cycle_multigraph(5)
    G2 = cycle_multigraph(5)
    assert check_self_consistency(G1, G2) is True


def test_self_consistency_detects_missing_parallel_edge():
    # Two dots connected by a double strand in the original but only a
    # single strand in the regenerated graph must NOT count as a match --
    # multiplicity is part of correctness, not a set-equality afterthought.
    G1 = nx.MultiGraph()
    G1.add_edge((0, 0), (1, 0))
    G1.add_edge((0, 0), (1, 0))  # double strand

    G2 = nx.MultiGraph()
    G2.add_edge((0, 0), (1, 0))  # single strand

    assert check_self_consistency(G1, G2) is False
