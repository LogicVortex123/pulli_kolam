"""Tests for engine/reconstruction.py (M3.5).

Keeps the three modes distinguishable per docs/RECONSTRUCTION.md:
  - motif_only_report / generate_kolam  -- motif-only baseline
  - reconstruct_kolam                    -- motif + EXACT source residual
  - (novel generation on unseen layouts is out of scope, not tested here)
"""

from __future__ import annotations

import copy
from collections import Counter

import networkx as nx
import numpy as np
import pytest

from engine.dataset import load_kolam
from engine.generation import build_candidate_graph
from engine.kolam_pattern import KolamPattern
from engine.motifs import MotifPlacement
from engine.reconstruction import motif_only_report, reconstruct_kolam


def _synthetic_pattern(graph: nx.MultiGraph, pattern_id: int = 0, collection: str = "synthetic") -> KolamPattern:
    """Minimal KolamPattern wrapping a hand-built graph, for white-box
    testing of reconstruct_kolam's logic only -- raw_trace/trace_points
    are intentionally empty (no real CSV trace exists for a synthetic
    graph); only .graph/.dot_points are exercised by reconstruction."""
    dot_points = set(graph.nodes())
    edges = tuple(graph.edges())
    edge_multiplicity = dict(Counter(frozenset(e) for e in graph.edges()))
    return KolamPattern(
        pattern_id=pattern_id,
        collection=collection,
        raw_trace=np.empty((0, 2)),
        trace_points=(),
        dot_points=dot_points,
        edges=edges,
        edge_multiplicity=edge_multiplicity,
        graph=graph,
        bounding_box=(0.0, 0.0, 0.0, 0.0),
    )


def doubled_square_graph() -> nx.MultiGraph:
    """Same known-valid shape as tests/test_generation.py's controlled
    synthetic case: a 4-cycle with every edge doubled -> clean Eulerian
    circuit, multiplicity 2 everywhere."""
    G = nx.MultiGraph()
    cycle = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for a, b in zip(cycle, cycle[1:] + cycle[:1]):
        G.add_edge(a, b)
        G.add_edge(a, b)
    return G


def doubled_square_placement() -> MotifPlacement:
    cycle_edges = (
        ((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 0)),
        ((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 0)),
    )
    return MotifPlacement(motif=cycle_edges, points=[(0, 0)], transforms={})


def doubled_square_with_extra_edge_graph() -> nx.MultiGraph:
    """The doubled square PLUS a doubled edge hanging off an EXISTING
    node (1, 1) -- stays ONE connected component (unlike a disjoint
    extra edge, which check_validity would correctly still fail even
    after residual restoration, since it requires the WHOLE graph
    connected, not just a valid sub-piece -- residual can only copy back
    edges that exist in source, it can't invent a NEW edge connecting
    two genuinely disjoint components that source itself never had).
    Every node stays even-degree, so the source itself is realistically
    a valid single-stroke pattern too."""
    G = doubled_square_graph()
    G.add_edge((1, 1), (2, 1))
    G.add_edge((1, 1), (2, 1))
    return G


def test_exact_reconstruction_of_known_synthetic_pattern():
    # placements alone already reproduce the source exactly -> residual
    # should be empty and the candidate should exactly equal source.
    source = _synthetic_pattern(doubled_square_graph())
    placement = doubled_square_placement()

    result = reconstruct_kolam(source, [placement])

    assert len(result.residual_edges) == 0
    assert result.is_valid is True
    cmp = result.compare_to_source()
    assert cmp["multiplicity_exact_match"] is True
    assert cmp["source_unique_edges"] == cmp["candidate_unique_edges"] == 4
    assert cmp["source_total_strands"] == cmp["candidate_total_strands"] == 8
    assert cmp["candidate_valid"] is True


def test_motif_only_produces_disconnected_candidate():
    # source = the doubled square PLUS a separate 2-dot edge the motif
    # placement does not cover at all -> motif-only must be disconnected.
    source = _synthetic_pattern(doubled_square_with_extra_edge_graph())
    placement = doubled_square_placement()  # only covers the original square

    mo = motif_only_report(source, [placement])

    assert mo["connected_components"] >= 2
    assert mo["is_valid"] is False
    assert mo["edge_recall"] < 1.0
    assert mo["motif_count"] == 1


def test_residual_restoration_reconnects_and_covers_all_edges():
    source = _synthetic_pattern(doubled_square_with_extra_edge_graph())
    placement = doubled_square_placement()

    result = reconstruct_kolam(source, [placement])

    assert frozenset({(1, 1), (2, 1)}) in result.residual_edges
    assert result.connectivity["connected_components"] == 1
    cmp = result.compare_to_source()
    assert cmp["candidate_unique_edges"] == cmp["source_unique_edges"]


def test_multiplicity_is_preserved_in_reconstruction():
    graph = doubled_square_with_extra_edge_graph()
    source = _synthetic_pattern(graph)
    placement = doubled_square_placement()

    result = reconstruct_kolam(source, [placement])

    source_counts = dict(Counter(frozenset(e) for e in graph.edges()))
    assert result.edge_multiplicity == source_counts


def test_eulerian_validity_after_residual_restoration():
    source = _synthetic_pattern(doubled_square_with_extra_edge_graph())
    placement = doubled_square_placement()

    mo = motif_only_report(source, [placement])
    result = reconstruct_kolam(source, [placement])

    assert mo["is_valid"] is False  # motif-only: disconnected, invalid
    assert result.is_valid is True  # +residual: fully valid


def test_reconstruction_does_not_mutate_source():
    source = _synthetic_pattern(doubled_square_graph())
    placement = doubled_square_placement()
    dots_before = set(source.dot_points)
    edges_before = {frozenset(e) for e in source.graph.edges()}
    placement_before = copy.deepcopy((placement.motif, placement.points, placement.transforms))

    reconstruct_kolam(source, [placement])

    assert source.dot_points == dots_before
    assert {frozenset(e) for e in source.graph.edges()} == edges_before
    assert (placement.motif, placement.points, placement.transforms) == placement_before


def test_reconstruction_is_deterministic():
    source = _synthetic_pattern(doubled_square_graph())
    placement = doubled_square_placement()

    a = reconstruct_kolam(source, [placement])
    b = reconstruct_kolam(source, [placement])

    assert a.edge_multiplicity == b.edge_multiplicity
    assert {frozenset(e) for e in a.candidate_graph.edges()} == {frozenset(e) for e in b.candidate_graph.edges()}
    assert a.is_valid == b.is_valid


def test_motif_only_and_reconstruction_remain_distinguishable():
    source = _synthetic_pattern(doubled_square_with_extra_edge_graph())
    placement = doubled_square_placement()

    mo = motif_only_report(source, [placement])
    result = reconstruct_kolam(source, [placement])

    # different edge counts -- the two modes must not collapse into the
    # same answer just because they share build_candidate_graph internally
    assert mo["candidate"].graph.number_of_edges() != result.candidate_graph.number_of_edges()
    assert mo["is_valid"] != result.is_valid


def test_unsupported_residual_policy_raises():
    source = _synthetic_pattern(doubled_square_graph())
    placement = doubled_square_placement()
    with pytest.raises(ValueError):
        reconstruct_kolam(source, [placement], residual_policy="approximate")


def test_reconstruction_on_real_pattern_uses_source_dot_layout():
    pattern = load_kolam("kolam19", 1)
    from engine.motifs import induce_motif_set_adaptive

    placements, _residual, _full = induce_motif_set_adaptive(pattern, max_radius=1)
    result = reconstruct_kolam(pattern, placements)

    assert set(result.candidate_graph.nodes()) == pattern.dot_points
    # build_candidate_graph reused, not reimplemented: motif-only edge
    # set from build_candidate_graph directly must be a subset of the
    # candidate's edges (residual only ADDS, never removes/replaces)
    motif_graph = build_candidate_graph(placements, pattern.dot_points)
    assert {frozenset(e) for e in motif_graph.edges()} <= {frozenset(e) for e in result.candidate_graph.edges()}


def test_reconstruction_caps_over_explained_motif_strands():
    # Regression test for the over-explanation fix: a source pair with
    # multiplicity 1 that TWO different placements each independently
    # try to explain (motif contribution = 2) must end up with exactly
    # 1 strand in the final candidate, not 2 -- and the excess must be
    # explicitly reported in capped_excess, not silently dropped.
    edge = frozenset({(0, 0), (1, 0)})
    G = nx.MultiGraph()
    G.add_edge((0, 0), (1, 0))  # source multiplicity 1

    source = _synthetic_pattern(G)
    motif = (((0, 0), (1, 0)),)
    # two SEPARATE placements of the same motif, both landing on the
    # same pair -- build_candidate_graph would happily produce 2 strands
    # here (that's its documented, correct behavior for a caller that
    # WANTS accumulation); reconstruct_kolam must not let that leak
    # through uncapped into a reconstruction of `source`.
    placement_a = MotifPlacement(motif=motif, points=[(0, 0)], transforms={})
    placement_b = MotifPlacement(motif=motif, points=[(0, 0)], transforms={})

    motif_graph_uncapped = build_candidate_graph([placement_a, placement_b], {(0, 0), (1, 0)})
    assert motif_graph_uncapped.number_of_edges((0, 0), (1, 0)) == 2  # confirms this really would over-explain

    result = reconstruct_kolam(source, [placement_a, placement_b])

    assert result.edge_multiplicity[edge] == 1  # capped to source's real count
    assert result.capped_excess[edge] == 1  # the 1 excess strand is explicitly reported
    cmp = result.compare_to_source()
    assert cmp["multiplicity_exact_match"] is True
    assert cmp["self_consistent"] is True
    assert cmp["n_capped_excess_pairs"] == 1
    assert cmp["n_capped_excess_strands"] == 1


# ============================================================
# Physical multiplicity materialization audit (session 11):
# construct adversarial cases and inspect ACTUAL nx.MultiGraph edge keys,
# not counters/metrics. No bug found here; these are the proof.
# ============================================================


def _pair_graph_pattern(n_strands: int, a=(0, 0), b=(1, 0)) -> KolamPattern:
    """A minimal KolamPattern: two dots, connected by exactly `n_strands`
    parallel edges -- the source target for the adversarial cases below."""
    G = nx.MultiGraph()
    for _ in range(n_strands):
        G.add_edge(a, b)
    dots = {a, b}
    return _synthetic_pattern(G)


def test_multiplicity_case_c_motif_plus_residual_sum_correctly():
    # Case C: motif contributes N=2, source target (and therefore
    # residual) needs 3 more -> expect N+M=5 PHYSICAL edges, verified via
    # the actual MultiGraph's own edge count, not a Counter.
    a, b = (0, 0), (1, 0)
    source = _pair_graph_pattern(5, a, b)
    motif_doubled = (((0, 0), (1, 0)), ((0, 0), (1, 0)))  # contributes N=2
    placement = MotifPlacement(motif=motif_doubled, points=[a], transforms={})

    result = reconstruct_kolam(source, [placement])

    assert result.candidate_graph.number_of_edges(a, b) == 5
    pair = frozenset({a, b})
    assert result.residual_multiplicity[pair] == 3  # M=3, the exposed per-pair count
    assert result.edge_multiplicity[pair] == 5


def test_multiplicity_case_d_duplicate_motif_contribution_not_collapsed():
    # Case D: TWO SEPARATE placements each independently contribute 2
    # strands to the SAME pair (as if selection picked the same motif
    # type twice, or two structurally-identical overlapping candidates)
    # -- their contributions must SUM (4 total), not collapse to 2 as if
    # "duplicate" meant "redundant." Source target is 6, so residual adds
    # the remaining 2.
    a, b = (0, 0), (1, 0)
    source = _pair_graph_pattern(6, a, b)
    motif_doubled = (((0, 0), (1, 0)), ((0, 0), (1, 0)))
    p1 = MotifPlacement(motif=motif_doubled, points=[a], transforms={})
    p2 = MotifPlacement(motif=motif_doubled, points=[a], transforms={})  # duplicate

    result = reconstruct_kolam(source, [p1, p2])

    assert result.candidate_graph.number_of_edges(a, b) == 6
    assert result.capped_excess == {}  # 4 (motif) + 2 (residual) == 6 exactly, nothing capped
    pair = frozenset({a, b})
    assert result.residual_multiplicity[pair] == 2


def test_multiplicity_over_explanation_is_capped_and_reported_not_dropped():
    # The original over-explanation bug this whole investigation started
    # from: a motif that produces MORE strands than source's real target
    # must be CAPPED at the target, with the excess explicitly reported
    # (capped_excess), never silently discarded and never left in the
    # physical graph uncapped.
    a, b = (0, 0), (1, 0)
    source = _pair_graph_pattern(2, a, b)  # source target is only 2
    motif_5x = tuple([((0, 0), (1, 0))] * 5)  # produces 5
    placement = MotifPlacement(motif=motif_5x, points=[a], transforms={})

    result = reconstruct_kolam(source, [placement])

    assert result.candidate_graph.number_of_edges(a, b) == 2  # capped, not 5
    pair = frozenset({a, b})
    assert result.capped_excess[pair] == 3  # 5 produced - 2 kept = 3 explicitly reported
    assert result.residual_multiplicity.get(pair, 0) == 0  # no deficit -- motif already covered the target
