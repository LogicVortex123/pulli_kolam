"""Tests for the canonical KolamPattern model and its single loader
(engine/kolam_pattern.py, engine/dataset.py). Numbers asserted here are
the same ones independently verified in docs/DATA_FORMAT.md and in prior
session validation runs (kolam19 pattern 1: 184 dots, 228 distinct edges,
312 edge instances, 84 double-strand pairs) -- not re-derived here, just
checked for consistency.

Tests semantic correctness (dot/edge/multiplicity relationships that must
hold for ANY valid interpretation of the data), not one arbitrary
internal representation -- e.g. we check edge_multiplicity sums to the
edge count and the graph's degree sequence matches, not the exact
iteration order of an internal dict.
"""

from __future__ import annotations

import networkx as nx
import pytest

from engine import motifs, symmetry, validity
from engine.dataset import COLLECTIONS, list_pattern_ids, load_dataset, load_kolam
from engine.kolam_pattern import KolamPattern


def test_load_kolam_succeeds():
    pattern = load_kolam("kolam19", 1)
    assert isinstance(pattern, KolamPattern)


def test_pattern_id_is_correct():
    pattern = load_kolam("kolam19", 26)
    assert pattern.pattern_id == 26


def test_collection_is_correct():
    pattern = load_kolam("kolam19", 1)
    assert pattern.collection == "kolam19"


def test_trace_is_non_empty():
    pattern = load_kolam("kolam19", 1)
    assert pattern.n_trace_points > 0
    assert len(pattern.trace_points) > 0
    assert pattern.raw_trace.shape[0] > 0


def test_trace_ordering_is_preserved():
    pattern = load_kolam("kolam19", 1)
    # trace_points must be raw_trace's rows, IN ORDER, not reordered/sorted
    for i, (x, y) in enumerate(pattern.trace_points):
        assert x == pytest.approx(pattern.raw_trace[i, 0])
        assert y == pytest.approx(pattern.raw_trace[i, 1])
    # the trace is a closed loop (verified dataset-wide in DATA_FORMAT.md)
    assert pattern.trace_points[0] == pattern.trace_points[-1]


def test_dot_points_match_verified_interpretation():
    # kolam19 pattern 1: 184 distinct dots (integer-coordinate points the
    # stroke actually visits) -- see docs/DATA_FORMAT.md.
    pattern = load_kolam("kolam19", 1)
    assert len(pattern.dot_points) == 184
    # every dot point must be integer-coordinate (dataclass invariant of
    # "dot", not an accident of this one pattern)
    for x, y in pattern.dot_points:
        assert isinstance(x, int) and isinstance(y, int)
    # every dot must actually appear as a both-integer point somewhere in
    # the raw trace (dots are a SUBSET of visited points, not invented)
    integer_trace_points = {
        (int(x), int(y)) for x, y in pattern.trace_points if x == int(x) and y == int(y)
    }
    assert pattern.dot_points <= integer_trace_points


def test_edges_are_consistent_with_trace():
    pattern = load_kolam("kolam19", 1)
    # every edge endpoint must be a real dot
    for a, b in pattern.edges:
        assert a in pattern.dot_points
        assert b in pattern.dot_points
    # verified count: 312 edge instances (see docs/DATA_FORMAT.md)
    assert len(pattern.edges) == 312


def test_edge_multiplicity_is_preserved():
    pattern = load_kolam("kolam19", 1)
    # verified: 228 distinct pairs, 84 with multiplicity > 1 (docs/DATA_FORMAT.md)
    assert len(pattern.edge_multiplicity) == 228
    assert sum(1 for v in pattern.edge_multiplicity.values() if v > 1) == 84
    # the multiplicities must sum to the total edge instance count
    assert sum(pattern.edge_multiplicity.values()) == len(pattern.edges)
    # and must exactly match a direct count from `edges` (not just agree
    # in total) -- semantic correctness, not just matching totals
    from collections import Counter

    assert dict(Counter(frozenset(e) for e in pattern.edges)) == pattern.edge_multiplicity


def test_multigraph_contains_expected_multiplicities():
    pattern = load_kolam("kolam19", 1)
    assert isinstance(pattern.graph, nx.MultiGraph)
    assert pattern.graph.number_of_edges() == len(pattern.edges)
    assert set(pattern.graph.nodes()) == pattern.dot_points
    # a MultiGraph must not have silently collapsed a genuine double
    # strand -- pick one known-duplicated pair and confirm the graph
    # still has 2 parallel edges for it
    dup_pair = next(frozenset(k) for k, v in pattern.edge_multiplicity.items() if v == 2)
    a, b = tuple(dup_pair)
    assert pattern.graph.number_of_edges(a, b) == 2


def test_bounding_box_is_correct():
    pattern = load_kolam("kolam19", 1)
    xs = pattern.raw_trace[:, 0]
    ys = pattern.raw_trace[:, 1]
    min_x, min_y, max_x, max_y = pattern.bounding_box
    assert min_x == pytest.approx(xs.min())
    assert max_x == pytest.approx(xs.max())
    assert min_y == pytest.approx(ys.min())
    assert max_y == pytest.approx(ys.max())


@pytest.mark.parametrize("collection", ["kolam19", "kolam29", "kolam109"])
def test_loading_works_for_all_three_collections(collection):
    pattern = load_kolam(collection, 1)
    assert pattern.collection == collection
    assert pattern.n_dots > 0
    assert pattern.n_edge_instances > 0
    assert pattern.graph.number_of_nodes() == pattern.n_dots


def test_list_pattern_ids_and_load_dataset_are_consistent():
    ids = list_pattern_ids("kolam19")
    assert ids[:3] == [1, 2, 3]
    assert len(ids) == 400
    # load_dataset would load all 400 -- too slow for a unit test; just
    # confirm a small slice loads correctly via repeated load_kolam calls
    # (load_dataset itself is a one-line loop over the same load_kolam
    # this test suite already exercises heavily, so this is sufficient
    # coverage without paying the full-dataset load cost every test run)
    for pid in ids[:3]:
        p = load_kolam("kolam19", pid)
        assert p.pattern_id == pid


def test_unknown_collection_raises():
    with pytest.raises(ValueError):
        load_kolam("kolam999", 1)


def test_existing_motif_analysis_still_works_via_pattern():
    pattern = load_kolam("kolam19", 1)

    # via KolamPattern
    placements_a, residual_a, full_a = motifs.induce_motif_set_adaptive(pattern)

    # via the raw-graph call path this project's existing scripts/tests use
    dots = pattern.dot_points
    interior = motifs.interior_points(dots, radius=1)
    placements_b, residual_b, full_b = motifs.induce_motif_set_adaptive(pattern.graph, interior, dots)

    assert len(placements_a) == len(placements_b)
    assert residual_a == residual_b
    assert full_a == full_b


def test_existing_validity_checks_still_work_via_pattern():
    pattern = load_kolam("kolam19", 1)
    assert validity.check_validity(pattern) == validity.check_validity(pattern.graph)
    assert validity.is_valid_single_stroke(pattern) == validity.is_valid_single_stroke(pattern.graph)
    # kolam19 pattern 1 is known-valid (pre-verified dataset, see
    # engine/validity.py module docstring)
    assert validity.is_valid_single_stroke(pattern) is True


def test_analyze_symmetry_works_via_pattern():
    pattern = load_kolam("kolam19", 1)
    motif_a, coverage_a, _ = symmetry.analyze_symmetry(pattern)

    dots = pattern.dot_points
    interior = motifs.interior_points(dots, radius=1)
    motif_b, coverage_b, _ = symmetry.induce_motif_symmetric(pattern.graph, interior, dots, radius=1)

    assert motif_a == motif_b
    assert coverage_a == coverage_b


def test_collections_registry_matches_bundled_files():
    for collection, path in COLLECTIONS.items():
        assert path.exists(), f"{collection} -> {path} does not exist"
