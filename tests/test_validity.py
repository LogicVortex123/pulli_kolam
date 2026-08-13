import networkx as nx

from engine.validity import check_self_consistency, check_validity, diagnose_validity, is_valid_single_stroke


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


def two_triangles_bridged_by_double_edge() -> tuple[nx.MultiGraph, tuple, tuple]:
    """A fully valid (all-even-degree) MultiGraph: two triangles (each an
    independently even-degree loop) connected by a DOUBLE-strand bridge.
    Returns (G, u, v) where u, v are the two bridge endpoints -- removing
    one bridge strand should break parity at exactly those two nodes and
    nowhere else."""
    G = nx.MultiGraph()
    u, a, b = (0, 0), (1, 1), (1, -1)
    v, c, d = (5, 0), (4, 1), (4, -1)
    for x, y in [(u, a), (a, b), (b, u), (v, c), (c, d), (d, v)]:
        G.add_edge(x, y)
    G.add_edge(u, v)
    G.add_edge(u, v)  # double-strand bridge
    return G, u, v


def test_diagnose_validity_on_fully_valid_graph_needs_no_corrections():
    G, _u, _v = two_triangles_bridged_by_double_edge()
    d = diagnose_validity(G)
    assert d["is_valid"] is True
    assert d["n_odd_degree_nodes"] == 0
    assert d["n_corrections"] == 0
    assert d["corrections"] == []


def test_diagnose_validity_localizes_single_flipped_edge():
    # Simulates a single missed double-strand detection: removing ONE of
    # the two bridge strands (as an image pipeline might miss one strand
    # of a genuine double-strand edge) breaks parity at exactly the 2
    # bridge endpoints and must NOT affect the other 4 (untouched)
    # triangle nodes.
    #
    # Note: exactly 2 odd-degree nodes is precisely the Eulerian PATH
    # condition, so is_valid_single_stroke actually stays True here (a
    # valid OPEN stroke, just no longer a closed loop) -- diagnose_validity
    # still correctly identifies and localizes the parity break; it isn't
    # gated on the pattern having failed check_validity's is_valid flag.
    G, u, v = two_triangles_bridged_by_double_edge()
    # remove exactly one of the two parallel (u, v) edges
    key = next(iter(G[u][v]))
    G.remove_edge(u, v, key=key)

    d = diagnose_validity(G)
    assert d["is_valid"] is True  # still a valid OPEN Eulerian path
    assert d["n_odd_degree_nodes"] == 2
    assert set(d["odd_degree_nodes"]) == {u, v}
    assert d["n_corrections"] == 1
    assert set(d["corrections"][0]["pair"]) == {u, v}
    # the remaining bridge strand is still a direct edge -> minimal cost 1
    assert d["corrections"][0]["cost"] == 1
    assert d["total_correction_cost"] == 1


def test_diagnose_validity_detects_genuinely_invalid_case():
    # Two INDEPENDENT double-strand bridges (disjoint node sets), each
    # losing one strand -> 4 distinct odd-degree nodes total (one per
    # triangle's bridge-attachment point). No single open path can cover
    # 4 odd-degree nodes, so is_valid must be False, with 2 correction
    # pairs found, still localized to only the affected nodes.
    G = nx.MultiGraph()
    u1, a1, b1 = (0, 0), (1, 1), (1, -1)
    u2, a2, b2 = (5, 0), (4, 1), (4, -1)
    u3, a3, b3 = (10, 0), (11, 1), (11, -1)
    u4, a4, b4 = (15, 0), (14, 1), (14, -1)
    for x, y in [(u1, a1), (a1, b1), (b1, u1), (u2, a2), (a2, b2), (b2, u2),
                 (u3, a3), (a3, b3), (b3, u3), (u4, a4), (a4, b4), (b4, u4)]:
        G.add_edge(x, y)
    G.add_edge(u1, u2)
    G.add_edge(u1, u2)  # double bridge A (triangle 1 <-> triangle 2)
    G.add_edge(u3, u4)
    G.add_edge(u3, u4)  # double bridge B (triangle 3 <-> triangle 4)
    # connect the two bridge-groups into ONE component (diagnose_validity
    # only considers the largest component, matching check_validity) via
    # a DOUBLE edge between two otherwise-untouched nodes, so it doesn't
    # disturb anyone's parity (+2 is still even).
    G.add_edge(a2, a3)
    G.add_edge(a2, a3)

    G.remove_edge(u1, u2, key=next(iter(G[u1][u2])))
    G.remove_edge(u3, u4, key=next(iter(G[u3][u4])))

    d = diagnose_validity(G)
    assert d["is_valid"] is False
    assert d["n_odd_degree_nodes"] == 4
    assert set(d["odd_degree_nodes"]) == {u1, u2, u3, u4}
    assert d["n_corrections"] == 2
    # untouched (non-bridge) nodes must not appear anywhere in the diagnosis
    untouched = {a1, b1, a2, b2, a3, b3, a4, b4}
    assert untouched.isdisjoint(d["odd_degree_nodes"])
    # corrections must pair within each bridge, not across bridges A/B
    pairs = [frozenset(c["pair"]) for c in d["corrections"]]
    assert frozenset({u1, u2}) in pairs
    assert frozenset({u3, u4}) in pairs
