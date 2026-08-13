from collections import Counter

import networkx as nx

from engine.generation import apply_motif
from engine.motifs import (
    MotifPlacement,
    compression_ratio,
    description_size,
    induce_motif,
    induce_motif_set,
    induce_motif_set_adaptive,
    interior_points,
    local_window,
    mdl_gain,
)
from engine.symmetry import canonical_motif


def grid_nodes(n: int) -> set[tuple[int, int]]:
    return {(i, j) for i in range(n) for j in range(n)}


def test_local_window_is_translation_invariant():
    G = nx.MultiGraph()
    G.add_edge((5, 5), (6, 5))
    G.add_edge((5, 5), (5, 6))
    dots = {(5, 5), (6, 5), (5, 6), (4, 5), (4, 4)}
    window = local_window(G, (5, 5), dots, radius=1)
    assert window == (((0, 0), (0, 1)), ((0, 0), (1, 0)))


def test_local_window_preserves_edge_multiplicity():
    G = nx.MultiGraph()
    G.add_edge((0, 0), (1, 0))
    G.add_edge((0, 0), (1, 0))  # double strand
    dots = {(0, 0), (1, 0)}
    window = local_window(G, (0, 0), dots, radius=1)
    assert window == (((0, 0), (1, 0)), ((0, 0), (1, 0)))


def test_interior_points_excludes_boundary():
    dots = grid_nodes(5)  # 0..4 square
    interior = interior_points(dots, radius=1)
    assert interior == {(i, j) for i in range(1, 4) for j in range(1, 4)}


def test_induce_motif_recovers_known_motif_with_full_coverage():
    # Centers spaced 3 apart so their radius-1 windows never overlap --
    # each interior point's window is *exactly* the stamped motif, with
    # no aggregation from a neighboring stamp.
    nodes = grid_nodes(12)
    centers = [(0, 0), (3, 0), (6, 0), (9, 0)]
    known_motif = (((0, 0), (1, 0)),)  # single edge along +x

    G = apply_motif(known_motif, nodes, centers)

    motif, coverage = induce_motif(G, set(centers), nodes, radius=1)
    assert motif == known_motif
    assert coverage == 1.0


def test_induce_motif_round_trip_reconstructs_covered_edges_exactly():
    nodes = grid_nodes(12)
    centers = [(0, 0), (3, 0), (6, 0), (9, 0)]
    known_motif = (((0, 0), (1, 0)),)

    G = apply_motif(known_motif, nodes, centers)
    motif, coverage = induce_motif(G, set(centers), nodes, radius=1)
    G_regen = apply_motif(motif, nodes, centers)

    assert set(G.edges()) == set(G_regen.edges())


def test_compression_ratio_accounts_for_placement_cost():
    nodes = grid_nodes(12)
    centers = [(0, 0), (3, 0), (6, 0), (9, 0)]
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, centers)
    placement = MotifPlacement(motif=motif, points=centers, transforms={}, new_edges=set())

    # raw_size = 4 edges * 4 = 16
    # description_size = (1 rel-edge * 4) + (4 placements * 3) + 0 residual = 16
    # -> ratio 1.0: stating a 1-edge motif 4 times is exactly as expensive
    # as just listing the 4 edges -- correctly, zero real compression.
    assert description_size([placement], 0) == 16
    assert compression_ratio(G, [placement], set()) == 1.0


def test_compression_ratio_counts_residual_edges_explicitly():
    G = nx.MultiGraph()
    G.add_edge((0, 0), (1, 0))
    G.add_edge((5, 5), (6, 5))  # not explained by any motif
    residual = {frozenset({(5, 5), (6, 5)})}
    motif = (((0, 0), (1, 0)),)
    placement = MotifPlacement(motif=motif, points=[(0, 0)], transforms={}, new_edges=set())

    # raw_size = 2 edges * 4 = 8
    # description_size = (1*4 + 1*3) + 1 residual*4 = 7 + 4 = 11
    assert description_size([placement], len(residual)) == 11
    assert compression_ratio(G, [placement], residual) == 8 / 11


def test_compression_ratio_no_motifs_no_edges():
    G = nx.MultiGraph()
    G.add_node((0, 0))
    assert compression_ratio(G, [], set()) == float("inf")


def test_induce_motif_set_recovers_two_distinct_motifs():
    # Two spatially-separated regions, each fully covered by its OWN
    # distinct (non-D4-equivalent) repeating motif. A correct set-cover
    # induction should find exactly 2 motifs that jointly explain
    # everything -- not merge them into one wrong motif, and not need
    # anywhere near one motif per edge (that would mean it found no
    # structure at all).
    nodes = grid_nodes(30)

    # Region A (x in 0..9): horizontal-edge motif, centers spaced 3 apart
    # so windows never overlap.
    motif_a = (((0, 0), (1, 0)),)
    centers_a = [(2, 2), (5, 2), (8, 2), (11, 2)]  # kept off the (0,0) grid corner

    # Region B (x in 20..29): a right-angle motif, not a D4 image of
    # motif_a (different edge count), also non-overlapping centers.
    motif_b = (((0, 0), (1, 0)), ((0, 0), (0, 1)))
    centers_b = [(20, 20), (23, 20), (26, 20), (20, 23)]

    G = apply_motif(motif_a, nodes, centers_a)
    G = nx.compose(G, apply_motif(motif_b, nodes, centers_b))

    interior = interior_points(nodes, radius=1)
    interior_used = (set(centers_a) | set(centers_b)) & interior

    placements, residual, fully_covered = induce_motif_set(
        G, interior_used, nodes, radius=1, max_motifs=10
    )

    assert fully_covered is True
    assert len(residual) == 0
    assert len(placements) == 2
    # induce_motif_set reports each motif in its D4-canonical form, which
    # need not be the literal orientation used to build the fixture --
    # compare against the same canonicalization, not the raw motif tuples.
    found_motifs = {p.motif for p in placements}
    assert found_motifs == {canonical_motif(motif_a), canonical_motif(motif_b)}


def test_induce_motif_set_respects_max_motifs_cap():
    nodes = grid_nodes(30)
    motif_a = (((0, 0), (1, 0)),)
    centers_a = [(2, 2), (5, 2), (8, 2), (11, 2)]  # kept off the (0,0) grid corner
    motif_b = (((0, 0), (1, 0)), ((0, 0), (0, 1)))
    centers_b = [(20, 20), (23, 20), (26, 20), (20, 23)]

    G = apply_motif(motif_a, nodes, centers_a)
    G = nx.compose(G, apply_motif(motif_b, nodes, centers_b))

    interior = interior_points(nodes, radius=1)
    interior_used = (set(centers_a) | set(centers_b)) & interior

    placements, residual, fully_covered = induce_motif_set(
        G, interior_used, nodes, radius=1, max_motifs=1
    )

    assert len(placements) == 1
    assert fully_covered is False
    assert len(residual) > 0


def test_induce_motif_set_adaptive_uses_right_radius_per_region():
    # Region A: a plain radius=1 motif (adjacent-dot edge).
    # Region B: an edge that SKIPS a dot (Chebyshev distance 2) -- this
    # cannot appear in ANY radius=1 window at all (the far endpoint falls
    # outside a radius=1 neighborhood entirely, so the window is empty,
    # not approximate), so a radius=1-only pass leaves it fully
    # untouched; only a radius=2 retry can see it. This mirrors real
    # kolam data, which genuinely has distance-2 "skip a dot" strands
    # (see PULLI session notes).
    #
    # Under MDL gating, a 1-relative-edge motif stamped at exactly 4
    # points is a break-even case (benefit 4*4=16 == rule 4 + placements
    # 4*3=12 -> gain 0), which the strict gain>0 gate correctly rejects.
    # Use 8 placements per region instead so each is clearly net-positive
    # (gain = 4*8 - 4 - 3*8 = 4), so this test verifies the "right radius
    # per region" placement, not the gate's break-even threshold.
    nodes = grid_nodes(60)

    motif_a = (((0, 0), (1, 0)),)
    centers_a = [(2, 2), (5, 2), (8, 2), (11, 2), (14, 2), (17, 2), (20, 2), (23, 2)]

    motif_b = (((0, 0), (2, 0)),)
    # 5 apart: radius=2 windows don't overlap; far from region A
    centers_b = [(2, 40), (7, 40), (12, 40), (17, 40), (22, 40), (27, 40), (32, 40), (37, 40)]

    G = apply_motif(motif_a, nodes, centers_a)
    G = nx.compose(G, apply_motif(motif_b, nodes, centers_b))

    interior_r1 = interior_points(nodes, radius=1)
    interior_used = (set(centers_a) | set(centers_b)) & interior_r1

    placements, residual, fully_covered = induce_motif_set_adaptive(
        G, interior_used, nodes, max_radius=2, max_motifs_per_radius=10
    )

    assert fully_covered is True
    assert len(residual) == 0

    edges_a = {frozenset(e) for e in apply_motif(motif_a, nodes, centers_a).edges()}
    edges_b = {frozenset(e) for e in apply_motif(motif_b, nodes, centers_b).edges()}

    covered_at_radius: dict[int, set] = {}
    for p in placements:
        covered_at_radius.setdefault(p.radius, set()).update(p.new_edges)

    # region A's edges were covered by the radius=1 tier and NOTHING from
    # region B leaked in there (geometrically impossible, but assert it);
    # region B's edges needed the radius=2 retry, not radius=1. Neither
    # region was forced into the other's radius.
    assert set(covered_at_radius.keys()) == {1, 2}
    assert covered_at_radius[1] == edges_a
    assert covered_at_radius[2] == edges_b


def test_induce_motif_set_adaptive_stops_when_max_radius_exhausted():
    nodes = grid_nodes(40)
    motif_b = (((0, 0), (2, 0)),)
    centers_b = [(20, 20), (25, 20), (30, 20), (20, 25)]
    G = apply_motif(motif_b, nodes, centers_b)

    interior_r1 = interior_points(nodes, radius=1)
    interior_used = set(centers_b) & interior_r1

    # max_radius=1 never reaches the radius that could explain these
    # distance-2 edges -- they must end up in the residual, not silently
    # dropped or crash the function.
    placements, residual, fully_covered = induce_motif_set_adaptive(
        G, interior_used, nodes, max_radius=1, max_motifs_per_radius=10
    )

    assert fully_covered is False
    assert len(placements) == 0
    assert len(residual) == 4  # the 4 stamped edges, all unexplained at radius=1


def test_induce_motif_set_residual_is_multiplicity_exact_not_just_identity():
    # A pair whose TRUE target need is 2 strands, but whose only
    # available candidate contributes just 1, must be left with a
    # residual DEFICIT of 1 -- not marked "fully covered" the instant
    # its identity is touched once. Uses the documented target_edges
    # override (a Counter) to isolate the accounting fix directly,
    # without depending on emergent local_window multiplicity-matching
    # behavior (which is already correct at the single-window level and
    # was never the bug -- see PROJECT_STATE.md's audit).
    G = nx.MultiGraph()
    dots = {(x, y) for x in range(-1, 2) for y in range(-1, 2)}
    G.add_nodes_from(dots)
    G.add_edge((-1, 0), (0, 0))
    G.add_edge((0, 0), (1, 0))  # single strand in G's own local-window shape

    interior = interior_points(dots, radius=1)
    target_pair = frozenset({(0, 0), (1, 0)})
    target = Counter(frozenset(e) for e in G.edges())
    target[target_pair] = 2  # override: true source need for this pair is 2

    placements, residual, fully_covered = induce_motif_set(
        G, interior, dots, radius=1, max_motifs=10, target_edges=target
    )

    assert residual.get(target_pair, 0) == 1  # deficit correctly tracked, not zeroed
    assert fully_covered is False


def test_induce_motif_set_adaptive_residual_is_a_counter():
    # Return-type contract: residual is now a multiplicity-exact Counter,
    # not a plain set of distinct pairs (session 10 fix, ported from the
    # same fix already applied to reconstruct_kolam in session 9).
    nodes = grid_nodes(12)
    centers = [(0, 0), (3, 0), (6, 0), (9, 0)]
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, centers)

    interior = interior_points(nodes, radius=1)
    placements, residual, fully_covered = induce_motif_set_adaptive(
        G, interior & set(centers), nodes, max_radius=1
    )
    assert isinstance(residual, Counter)


def test_mdl_gain_formula():
    # 2-edge motif, 2 placements, 3 newly-covered edges (one placement's
    # window overlapped a previously-covered edge from elsewhere).
    motif = (((0, 0), (1, 0)), ((0, 0), (0, 1)))  # 2 relative edges -> rule cost 8
    new_placements = [(0, 0), (3, 0)]  # 2 placements -> placement cost 6
    newly_covered = {
        frozenset({(0, 0), (1, 0)}),
        frozenset({(0, 0), (0, 1)}),
        frozenset({(3, 0), (4, 0)}),
    }  # 3 edges -> benefit 12

    gain_new_rule = mdl_gain(motif, new_placements, newly_covered, is_new_motif_type=True)
    assert gain_new_rule == 12 - 8 - 6  # == -2: paying for the rule makes this net negative

    gain_reused_rule = mdl_gain(motif, new_placements, newly_covered, is_new_motif_type=False)
    assert gain_reused_rule == 12 - 0 - 6  # == 6: rule already paid for -> net positive


def test_mdl_gain_single_edge_single_placement_is_always_negative():
    # A rule stated once, applied once, is never cheaper than just writing
    # the raw edge down -- this is the built-in property that makes the
    # gate reject one-off "motifs" without any special-casing.
    motif = (((0, 0), (1, 0)),)
    gain = mdl_gain(motif, [(5, 5)], {frozenset({(5, 5), (6, 5)})}, is_new_motif_type=True)
    assert gain < 0


def test_induce_motif_set_adaptive_rejects_expensive_one_off_despite_recall_gain():
    # A dominant, clearly-beneficial motif (8 placements, net gain +4 per
    # the earlier fixture) should be accepted. A single isolated edge far
    # away, with a DIFFERENT D4-canonical shape (diagonal, not horizontal
    # -- so it can't just be folded into the already-paid-for rule),
    # would strictly increase recall if covered, but as its own new motif
    # type costs: benefit 4*1 - rule 4*1 - placement 3*1 = -3 < 0. It
    # must be rejected even though covering it is possible and would
    # improve recall -- proving the gate does cost-benefit reasoning, not
    # recall-seeking with extra steps.
    nodes = grid_nodes(60)

    motif_main = (((0, 0), (1, 0)),)
    centers_main = [(2, 2), (5, 2), (8, 2), (11, 2), (14, 2), (17, 2), (20, 2), (23, 2)]
    G = apply_motif(motif_main, nodes, centers_main)

    stray_point = (50, 50)
    G.add_edge(stray_point, (51, 51))  # isolated diagonal edge, appears exactly once

    interior = interior_points(nodes, radius=1)
    interior_used = (set(centers_main) | {stray_point}) & interior

    placements, residual, fully_covered = induce_motif_set_adaptive(
        G, interior_used, nodes, max_radius=1, max_motifs_per_radius=50
    )

    stray_edge = frozenset({stray_point, (51, 51)})
    covered_edges = {e for p in placements for e in p.new_edges}
    edges_main = {frozenset(e) for e in apply_motif(motif_main, nodes, centers_main).edges()}

    assert fully_covered is False
    assert covered_edges == edges_main  # the beneficial motif WAS accepted
    assert stray_edge in residual  # the one-off edge was correctly rejected
    assert stray_edge not in covered_edges
