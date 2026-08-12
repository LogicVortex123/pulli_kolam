import copy

from engine.dataset import load_kolam
from engine.generation import apply_motif, build_candidate_graph, generate_kolam, reconstruct_dot_trace
from engine.motifs import MotifPlacement


def edge_set(G):
    return {frozenset(e) for e in G.edges()}


def doubled_square_placement():
    """A tiny known-valid synthetic case: a 4-cycle with every relative
    edge doubled, stamped at one center. Every node ends up degree 4
    (even) -> a clean Eulerian circuit with known multiplicity 2 on
    every edge -- see Phase 2 of the generation task ("controlled
    synthetic case")."""
    cycle_edges = (
        ((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 0)),
        ((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 0)),
    )
    placement = MotifPlacement(motif=cycle_edges, points=[(0, 0)], transforms={})
    dot_points = {(0, 0), (1, 0), (1, 1), (0, 1)}
    return placement, dot_points


def test_apply_motif_stamps_translated_edges():
    nodes = {(i, j) for i in range(5) for j in range(5)}
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [(0, 0), (2, 2)])
    assert edge_set(G) == {frozenset({(0, 0), (1, 0)}), frozenset({(2, 2), (3, 2)})}


def test_apply_motif_drops_edges_outside_node_set():
    nodes = {(0, 0), (1, 0)}  # (2, 0) deliberately absent
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [(0, 0), (1, 0)])
    # stamp at (1,0) would need node (2,0), which doesn't exist -> dropped
    assert edge_set(G) == {frozenset({(0, 0), (1, 0)})}


def test_apply_motif_respects_per_point_transform():
    nodes = {(i, j) for i in range(-3, 4) for j in range(-3, 4)}
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [(0, 0)], transforms={(0, 0): "rot90"})
    # rot90: (x,y) -> (-y,x); (1,0) -> (0,1)
    assert edge_set(G) == {frozenset({(0, 0), (0, 1)})}


def test_apply_motif_preserves_multiplicity():
    nodes = {(0, 0), (1, 0)}
    motif = (((0, 0), (1, 0)), ((0, 0), (1, 0)))  # double strand
    G = apply_motif(motif, nodes, [(0, 0)])
    assert G.number_of_edges() == 2
    assert [frozenset(e) for e in G.edges()] == [frozenset({(0, 0), (1, 0)})] * 2


def test_apply_motif_on_empty_points_yields_no_edges():
    nodes = {(0, 0), (1, 0)}
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [])
    assert G.number_of_edges() == 0
    assert set(G.nodes()) == nodes


# ============================================================
# Structural generation pipeline: motif rules -> candidate graph ->
# validity check -> trace reconstruction -> GeneratedKolam candidate.
# ============================================================


def test_generation_is_deterministic():
    placement, dot_points = doubled_square_placement()
    a = generate_kolam([placement], dot_points)
    b = generate_kolam([placement], dot_points)
    assert a.dot_trace == b.dot_trace
    assert edge_set(a.graph) == edge_set(b.graph)
    assert a.edge_multiplicity == b.edge_multiplicity


def test_known_valid_synthetic_graph_generates_correctly():
    placement, dot_points = doubled_square_placement()
    candidate = generate_kolam([placement], dot_points)

    assert candidate.dot_points == dot_points
    assert candidate.n_dots == 4
    assert candidate.n_distinct_edges == 4
    assert candidate.n_edge_instances == 8  # every edge doubled
    assert candidate.is_valid is True
    assert candidate.validity_result["is_eulerian_circuit"] is True


def test_edge_multiplicity_is_preserved_through_generation():
    placement, dot_points = doubled_square_placement()
    candidate = generate_kolam([placement], dot_points)
    # every one of the 4 distinct edges must show multiplicity exactly 2
    assert set(candidate.edge_multiplicity.values()) == {2}
    assert sum(candidate.edge_multiplicity.values()) == candidate.n_edge_instances
    # the MultiGraph itself must actually carry 2 parallel edges, not a
    # single edge with a "count" attribute bolted on
    a, b = (0, 0), (1, 0)
    assert candidate.graph.number_of_edges(a, b) == 2


def test_d4_motif_placement_applies_per_point_transform():
    motif = (((0, 0), (1, 0)),)
    placement = MotifPlacement(
        motif=motif,
        points=[(0, 0), (5, 5)],
        transforms={(5, 5): "rot90"},  # (0, 0) left at default identity
    )
    dot_points = {(0, 0), (1, 0), (5, 5), (5, 6)}
    candidate = generate_kolam([placement], dot_points)
    # rot90: (x, y) -> (-y, x); relative (1, 0) -> (0, 1)
    assert edge_set(candidate.graph) == {
        frozenset({(0, 0), (1, 0)}),
        frozenset({(5, 5), (5, 6)}),
    }


def test_overlapping_motif_placements_accumulate_not_overwrite():
    # two DIFFERENT placements stamping the SAME edge must produce 2
    # parallel edges, not 1 -- this is the "avoid silently overwriting
    # existing edges" requirement, checked directly against the graph.
    motif = (((0, 0), (1, 0)),)
    placement_a = MotifPlacement(motif=motif, points=[(0, 0)], transforms={})
    placement_b = MotifPlacement(motif=motif, points=[(0, 0)], transforms={})
    dot_points = {(0, 0), (1, 0)}

    candidate = generate_kolam([placement_a, placement_b], dot_points)
    assert candidate.n_edge_instances == 2
    assert candidate.graph.number_of_edges((0, 0), (1, 0)) == 2


def test_invalid_candidate_is_rejected_not_repaired():
    # a "plus" shape: 4 odd-degree endpoints -> structurally invalid,
    # matches the known-invalid case in tests/test_validity.py.
    plus_motif = (((0, 0), (1, 0)), ((0, 0), (-1, 0)), ((0, 0), (0, 1)), ((0, 0), (0, -1)))
    placement = MotifPlacement(motif=plus_motif, points=[(0, 0)], transforms={})
    dot_points = {(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)}

    candidate = generate_kolam([placement], dot_points)

    assert candidate.is_valid is False
    assert candidate.validity_result["is_eulerian_circuit"] is False
    assert candidate.validity_result["has_eulerian_path"] is False
    # not silently repaired: no fabricated trace
    assert candidate.dot_trace is None
    # but WHY is exposed, not just a bare False
    assert candidate.diagnosis["n_odd_degree_nodes"] == 4
    assert candidate.diagnosis["n_corrections"] == 2


def test_valid_candidate_passes_check_validity():
    from engine.validity import check_validity, is_valid_single_stroke

    placement, dot_points = doubled_square_placement()
    candidate = generate_kolam([placement], dot_points)

    assert is_valid_single_stroke(candidate) is True
    assert check_validity(candidate) == check_validity(candidate.graph)


def test_generated_graph_has_deterministic_traversal():
    placement, dot_points = doubled_square_placement()
    candidate = generate_kolam([placement], dot_points)

    assert candidate.dot_trace is not None
    # closed loop: starts and ends at the same dot
    assert candidate.dot_trace[0] == candidate.dot_trace[-1]
    # every dot in the candidate is visited
    assert set(candidate.dot_trace) == candidate.dot_points
    # consecutive trace points must be actual graph edges
    for a, b in zip(candidate.dot_trace, candidate.dot_trace[1:]):
        assert candidate.graph.has_edge(a, b)
    # re-running reconstruct_dot_trace directly on the same graph gives
    # the identical sequence (determinism at the function level, not
    # just at the generate_kolam wrapper level)
    assert reconstruct_dot_trace(candidate.graph) == candidate.dot_trace


def test_generation_does_not_mutate_source_motifs():
    placement, dot_points = doubled_square_placement()
    before = copy.deepcopy((placement.motif, placement.points, placement.transforms))

    generate_kolam([placement], dot_points)
    build_candidate_graph([placement], dot_points)

    after = (placement.motif, placement.points, placement.transforms)
    assert after == before


def test_generation_does_not_mutate_source_kolam_pattern():
    pattern = load_kolam("kolam19", 1)
    dots_before = set(pattern.dot_points)
    graph_edges_before = edge_set(pattern.graph)

    motif = (((0, 0), (1, 0)),)
    placement = MotifPlacement(motif=motif, points=[next(iter(pattern.dot_points))], transforms={})
    generate_kolam([placement], pattern.dot_points)

    assert pattern.dot_points == dots_before
    assert edge_set(pattern.graph) == graph_edges_before
