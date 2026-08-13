"""Tests for engine/motif_selection.py (M3.6).

Central claim under test: unlike engine.motifs.induce_motif_set_adaptive
(the existing, unmodified "mode A"), the selectors here can NEVER
over-explain a source edge -- accumulated_multiplicity[e] <=
source_multiplicity[e] is a structural guarantee, verified directly
against a synthetic case where the OLD algorithm demonstrably does
over-explain (see test_greedy_selection_avoids_over_explaining_placement,
which runs BOTH algorithms on the same input for a direct before/after).
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
from engine.motif_selection import (
    SelectionResult,
    _parity_delta,
    induce_motif_set_eulerian_aware,
    induce_motif_set_multiplicity_aware,
    simulate_placement_contribution,
    violates_multiplicity,
)
from engine.motifs import induce_motif_set_adaptive
from engine.validity import check_validity, is_valid_single_stroke


def _synthetic_pattern(graph: nx.MultiGraph, pattern_id: int = 0, collection: str = "synthetic") -> KolamPattern:
    """Same helper as tests/test_reconstruction.py -- minimal KolamPattern
    wrapping a hand-built graph, for white-box testing."""
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


def overlapping_row_graph(half_width: int = 5) -> nx.MultiGraph:
    """A row of single-strand edges along y=0, flanked by dots at y=-1/+1
    purely to satisfy interior_points' 2D margin requirement (radius=1
    needs BOTH x and y margin -- a pure 1D line has none). Every
    interior point's radius=1 local window sees the SAME "edge to my
    left, edge to my right" motif; consecutive interior points'
    2-edge windows OVERLAP on the edge directly between them, which is
    exactly the natural, deterministic case where the OLD (distinct-
    edge, no multiplicity tracking) algorithm over-explains: it stamps
    the shared edge once from EACH of the two neighboring points,
    reaching multiplicity 2 where source only has 1."""
    G = nx.MultiGraph()
    dots = {(x, y) for x in range(-half_width, half_width + 1) for y in range(-1, 2)}
    G.add_nodes_from(dots)
    for x in range(-half_width, half_width):
        G.add_edge((x, 0), (x + 1, 0))
    return G


# ============================================================
# Task 1: multiplicity constraint
# ============================================================


def test_placement_rejected_when_it_exceeds_source_multiplicity():
    motif = (((0, 0), (1, 0)),)
    contribution = simulate_placement_contribution(motif, (0, 0), "identity", {(0, 0), (1, 0)})
    edge = frozenset({(0, 0), (1, 0)})
    assert contribution == {edge: 1}

    source_mult = Counter({edge: 1})
    # nothing accumulated yet -> fits exactly, not a violation
    assert violates_multiplicity(contribution, Counter(), source_mult) is False
    # 1 already accumulated -> this contribution would push it to 2 > 1
    assert violates_multiplicity(contribution, Counter({edge: 1}), source_mult) is True


def test_greedy_selection_never_exceeds_source_multiplicity_on_real_data():
    pattern = load_kolam("kolam19", 1)
    source_mult = Counter(frozenset(e) for e in pattern.graph.edges())

    result = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=3)

    for edge, count in result.accumulated_multiplicity.items():
        assert count <= source_mult.get(edge, 0), f"edge {edge} over-explained: {count} > {source_mult.get(edge, 0)}"


# ============================================================
# Task 3: MultiGraph / parallel strands preserved
# ============================================================


def test_valid_parallel_strands_preserved_through_selection_and_build():
    # a doubled-edge motif (2 relative-edge instances on the SAME pair)
    # stamped at one point, source also has multiplicity 2 there -> must
    # be fully accepted, not clipped to 1.
    motif = (((0, 0), (1, 0)), ((0, 0), (1, 0)))
    G = nx.MultiGraph()
    G.add_edge((0, 0), (1, 0))
    G.add_edge((0, 0), (1, 0))
    dots = {(0, 0), (1, 0)}
    contribution = simulate_placement_contribution(motif, (0, 0), "identity", dots)
    edge = frozenset({(0, 0), (1, 0)})
    assert contribution[edge] == 2

    source_mult = Counter({edge: 2})
    assert violates_multiplicity(contribution, Counter(), source_mult) is False

    pattern = _synthetic_pattern(G)
    result = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=1)
    candidate = build_candidate_graph(result.placements, dots)
    assert candidate.number_of_edges((0, 0), (1, 0)) <= 2  # never exceeds source
    assert isinstance(candidate, nx.MultiGraph)


# ============================================================
# Task 2: greedy multiplicity-aware selection baseline
# ============================================================


def test_greedy_selection_avoids_over_explaining_placement():
    G = overlapping_row_graph()
    pattern = _synthetic_pattern(G)
    source_mult = Counter(frozenset(e) for e in G.edges())

    # Mode A (induce_motif_set_adaptive) -- its own internal ACCOUNTING is
    # now multiplicity-exact (session 10 fix), but that fix does not, by
    # itself, stop build_candidate_graph from physically over-explaining:
    # build_candidate_graph blindly re-stamps every point in a selected
    # MotifPlacement, with no memory of what the accounting layer capped/
    # credited during selection -- a real, separately-discovered gap (see
    # PROJECT_STATE.md), NOT fixed this session (out of the literal scope
    # of "fix the accounting"). So mode A STILL demonstrably over-explains
    # the MATERIALIZED graph on this exact input, verified directly below
    # (not asserted from memory) -- for a different, now-understood reason
    # than before the accounting fix.
    old_placements, _residual, _full = induce_motif_set_adaptive(pattern, max_radius=1)
    old_graph = build_candidate_graph(old_placements, pattern.dot_points)
    old_mult = Counter(frozenset(e) for e in old_graph.edges())
    old_over_explained = {e: c for e, c in old_mult.items() if c > source_mult.get(e, 0)}
    assert len(old_over_explained) > 0  # confirms the synthetic case is a real repro, not a strawman

    # NEW multiplicity-aware selection on the SAME input -- must have
    # zero over-explained edges.
    result = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=1)
    new_over_explained = {
        e: c for e, c in result.accumulated_multiplicity.items() if c > source_mult.get(e, 0)
    }
    assert len(new_over_explained) == 0
    assert result.rejected_count > 0  # it had to actively reject something to achieve this


def test_selection_result_fields_are_consistent():
    pattern = load_kolam("kolam19", 1)
    result = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=1)

    assert isinstance(result, SelectionResult)
    assert result.mode == "multiplicity"
    # residual_edges is exactly the key set of residual_multiplicity
    assert result.residual_edges == set(result.residual_multiplicity.keys())
    # every residual entry is a strictly positive deficit
    assert all(v > 0 for v in result.residual_multiplicity.values())
    # accumulated + residual reconstructs source exactly, per edge
    source_mult = Counter(frozenset(e) for e in pattern.graph.edges())
    for edge, s in source_mult.items():
        assert result.accumulated_multiplicity.get(edge, 0) + result.residual_multiplicity.get(edge, 0) == s


# ============================================================
# Task 4: Eulerian-aware second baseline
# ============================================================


def test_parity_delta_rewards_fixing_odd_vertices():
    edge = frozenset({(0, 0), (1, 0)})
    contribution = Counter({edge: 1})
    # (0,0) currently odd (degree 1), (1,0) currently even (degree 0) ->
    # adding 1 strand: (0,0) 1->2 (odd->even, +1), (1,0) 0->1 (even->odd, -1)
    degree_before = Counter({(0, 0): 1, (1, 0): 0})
    assert _parity_delta(contribution, degree_before) == 0  # one fixed, one broken -> net neutral

    # both currently odd -> fixing both -> net +2
    degree_before2 = Counter({(0, 0): 1, (1, 0): 1})
    assert _parity_delta(contribution, degree_before2) == 2


def test_eulerian_aware_scoring_reduces_odd_degree_where_possible():
    pattern = load_kolam("kolam19", 1)

    mult_result = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=3)
    eulerian_result = induce_motif_set_eulerian_aware(pattern, radius=1, max_radius=3)

    mult_graph = build_candidate_graph(mult_result.placements, pattern.dot_points)
    eulerian_graph = build_candidate_graph(eulerian_result.placements, pattern.dot_points)

    mult_odd = sum(1 for _n, d in mult_graph.degree() if d % 2 == 1)
    eulerian_odd = sum(1 for _n, d in eulerian_graph.degree() if d % 2 == 1)

    assert eulerian_odd < mult_odd  # measured on kolam19#1: 18 -> 6

    # still respects the exact same hard multiplicity constraint -- parity
    # scoring must never override it
    source_mult = Counter(frozenset(e) for e in pattern.graph.edges())
    for edge, count in eulerian_result.accumulated_multiplicity.items():
        assert count <= source_mult.get(edge, 0)


# ============================================================
# General correctness (Task 6 items 6-10)
# ============================================================


def test_no_source_mutation():
    pattern = load_kolam("kolam19", 1)
    dots_before = set(pattern.dot_points)
    edges_before = {frozenset(e) for e in pattern.graph.edges()}
    edge_mult_before = dict(pattern.edge_multiplicity)

    induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=1)
    induce_motif_set_eulerian_aware(pattern, radius=1, max_radius=1)

    assert pattern.dot_points == dots_before
    assert {frozenset(e) for e in pattern.graph.edges()} == edges_before
    assert pattern.edge_multiplicity == edge_mult_before


def test_deterministic_results():
    pattern = load_kolam("kolam19", 1)

    a = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=2)
    b = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=2)

    assert a.accumulated_multiplicity == b.accumulated_multiplicity
    assert a.residual_multiplicity == b.residual_multiplicity
    assert a.rejected_count == b.rejected_count
    assert len(a.placements) == len(b.placements)


def test_existing_behavior_remains_available_as_baseline():
    # mode A (engine.motifs.induce_motif_set_adaptive) remains independently
    # callable -- M3.6 adds new selectors, it does not replace or gate the
    # existing one. NOTE: mode A itself was later given a multiplicity-exact
    # ACCOUNTING fix (session 10 -- see PROJECT_STATE.md), so "unmodified"
    # no longer describes it precisely: its residual is now a Counter
    # (multiplicity-exact deficit), not a plain set of distinct pairs. This
    # is a real, intentional type change, asserted directly below.
    pattern = load_kolam("kolam19", 1)
    placements, residual, fully_covered = induce_motif_set_adaptive(pattern, max_radius=1)
    assert isinstance(placements, list)
    assert isinstance(residual, Counter)
    assert isinstance(fully_covered, bool)


def test_known_valid_synthetic_reconstruction_remains_valid():
    # the M3-era doubled-square case: every relative edge doubled,
    # stamped once -> a clean Eulerian circuit. Multiplicity-aware
    # selection must still find and accept this motif (source
    # multiplicity is exactly 2 everywhere, matching the motif's own
    # doubled relative edges, so no rejection should occur).
    G = nx.MultiGraph()
    cycle = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for a, b in zip(cycle, cycle[1:] + cycle[:1]):
        G.add_edge(a, b)
        G.add_edge(a, b)
    pattern = _synthetic_pattern(G)

    result = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=1)
    # a 4-node square has NO radius=1 interior points (needs 2D margin,
    # same reasoning as overlapping_row_graph's flanking dots) -- this
    # motif cannot be automatically induced from such a tiny layout, so
    # the meaningful check here is that selection runs cleanly (no
    # crash, no violation) and reports an honest empty result rather
    # than fabricating a placement.
    assert result.rejected_count == 0
    assert result.accumulated_multiplicity == {}

    # confirm reconstruct_kolam still recovers full validity via residual
    # even when motif selection itself finds nothing -- residual alone
    # reproduces source exactly here.
    from engine.reconstruction import reconstruct_kolam

    rec = reconstruct_kolam(pattern, result.placements)
    assert rec.is_valid is True
    assert rec.compare_to_source()["multiplicity_exact_match"] is True


def test_invalid_candidates_are_never_silently_repaired():
    pattern = load_kolam("kolam19", 1)
    result = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=1)
    candidate = build_candidate_graph(result.placements, pattern.dot_points)

    # motif-only (no residual) is expected to be disconnected/invalid at
    # this point -- confirm it's reported AS invalid, not silently
    # patched into something that passes.
    validity = check_validity(candidate)
    is_valid = (
        validity["largest_component_covers_all_nodes"]
        and (validity["is_eulerian_circuit"] or validity["has_eulerian_path"])
    )
    if not is_valid:
        assert is_valid_single_stroke(candidate) is False  # same conclusion via the public gate
    # (if it happened to already be valid, there's nothing to "repair"
    # in the first place -- the meaningful assertion is the consistency
    # between the two ways of asking, not a specific outcome)


def test_placements_deepcopy_independent_of_selection_internals():
    pattern = load_kolam("kolam19", 1)
    result = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=1)
    if not result.placements:
        pytest.skip("no placements produced at this radius for kolam19#1")
    before = copy.deepcopy(
        [(p.motif, list(p.points), dict(p.transforms)) for p in result.placements]
    )
    # calling again must not mutate or share state with the first result
    induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=1)
    after = [(p.motif, list(p.points), dict(p.transforms)) for p in result.placements]
    assert after == before
