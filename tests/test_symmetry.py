import networkx as nx

from engine.generation import apply_motif
from engine.motifs import induce_motif, local_window
from engine.symmetry import apply_transform, canonical_motif, induce_motif_symmetric


def grid_nodes(n: int) -> set[tuple[int, int]]:
    return {(i, j) for i in range(-n, n) for j in range(-n, n)}


def test_canonical_motif_unifies_rotated_edge():
    horizontal = (((0, 0), (1, 0)),)
    vertical = (((0, 0), (0, 1)),)  # a 90-degree rotation of `horizontal`
    assert canonical_motif(horizontal) == canonical_motif(vertical)


def test_canonical_motif_distinguishes_non_isomorphic_motifs():
    single_edge = (((0, 0), (1, 0)),)
    right_angle = (((0, 0), (1, 0)), ((0, 0), (0, 1)))
    assert canonical_motif(single_edge) != canonical_motif(right_angle)


def test_translation_only_induction_misses_rotated_repeat():
    nodes = grid_nodes(15)
    a, b = (0, 0), (10, 10)  # far enough apart windows never overlap
    motif = (((0, 0), (1, 0)),)

    G = apply_motif(motif, nodes, [a, b], transforms={b: "rot90"})

    _, coverage = induce_motif(G, {a, b}, nodes, radius=1)
    # translation-only clustering sees two distinct signatures -> the
    # dominant one covers only 1 of the 2 points
    assert coverage == 0.5


def test_symmetric_induction_recognizes_rotated_repeat():
    nodes = grid_nodes(15)
    a, b = (0, 0), (10, 10)
    motif = (((0, 0), (1, 0)),)

    G = apply_motif(motif, nodes, [a, b], transforms={b: "rot90"})

    motif_canon, coverage, transform_per_point = induce_motif_symmetric(
        G, {a, b}, nodes, radius=1
    )
    assert coverage == 1.0
    assert set(transform_per_point.keys()) == {a, b}

    # Whatever transform was assigned to each point, applying it to the
    # canonical motif must reproduce that point's actual local window.
    for point, t_name in transform_per_point.items():
        assert t_name is not None
        window = local_window(G, point, nodes, radius=1)
        assert apply_transform(t_name, motif_canon) == window


def test_symmetric_regeneration_round_trip():
    nodes = grid_nodes(15)
    a, b = (0, 0), (10, 10)
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [a, b], transforms={b: "rot90"})

    motif_canon, _, transform_per_point = induce_motif_symmetric(G, {a, b}, nodes, radius=1)
    G_regen = apply_motif(motif_canon, nodes, list(transform_per_point.keys()), transform_per_point)

    assert set(G.edges()) == set(G_regen.edges())
