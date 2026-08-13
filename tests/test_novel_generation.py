"""Tests for engine/novel_generation.py (M3.7).

Central claim under test: reconstruction and novel generation are
genuinely different code paths that must diverge on the same input --
reconstruct_kolam reproduces source exactly (it has residual to fall
back on); generate_novel_kolam does not (it never sees a source graph
at all, only an abstract motif library with no coordinates tied to any
specific pattern).
"""

from __future__ import annotations

from collections import Counter

from engine.dataset import load_kolam
from engine.motif_selection import induce_motif_set_eulerian_aware
from engine.novel_generation import (
    DEFAULT_MAX_MULTIPLICITY,
    duplicates_source,
    extract_motif_library,
    generate_novel_kolam,
    select_novel_placements,
)
from engine.motifs import interior_points
from engine.reconstruction import reconstruct_kolam


def _library_from(collection: str, pattern_id: int):
    source = load_kolam(collection, pattern_id)
    result = induce_motif_set_eulerian_aware(source, radius=1, max_radius=1)
    return source, extract_motif_library(result.placements)


# ============================================================
# Core distinction: reconstruction vs novel generation
# ============================================================


def test_novel_generation_never_copies_source_residual():
    source, library = _library_from("kolam19", 1)

    # generated on source's OWN layout -- the case most likely to
    # accidentally coincide with source if residual were leaking in
    novel = generate_novel_kolam(library, source.dot_points)
    reconstructed = reconstruct_kolam(source, [])  # placements=[] -> pure residual copy of source

    novel_mult = Counter(frozenset(e) for e in novel.graph.edges())
    source_mult = Counter(frozenset(e) for e in source.graph.edges())
    reconstructed_mult = Counter(frozenset(e) for e in reconstructed.candidate_graph.edges())

    # reconstruction (even with an EMPTY placement list) reproduces
    # source exactly via residual alone
    assert reconstructed_mult == dict(source_mult)
    # novel generation, given the SAME layout, does NOT -- it has no
    # residual mechanism to fall back on, so it cannot coincidentally
    # reproduce source's exact edge multiset from a small motif library
    assert novel_mult != dict(source_mult)


def test_novel_generation_on_unseen_layout_is_not_source_reconstruction():
    source, library = _library_from("kolam19", 1)
    target = load_kolam("kolam19", 2)

    novel = generate_novel_kolam(library, target.dot_points)

    # a genuinely different dot layout than the library's source
    assert novel.dot_points == target.dot_points
    assert novel.dot_points != source.dot_points
    # duplicates_source is well-defined here (same node set as `target`)
    # and must be False -- a 10-motif library greedily placed cannot
    # coincidentally reproduce an entire independent real pattern
    assert duplicates_source(novel.graph, target) is False


def test_duplicates_source_returns_none_for_mismatched_layout():
    _source, library = _library_from("kolam19", 1)
    other = load_kolam("kolam29", 1)  # different dot layout entirely
    novel = generate_novel_kolam(library, other.dot_points)
    # novel.dot_points == other.dot_points by construction, so compare
    # against a genuinely mismatched pattern instead
    mismatched = load_kolam("kolam19", 1)
    assert duplicates_source(novel.graph, mismatched) is None


# ============================================================
# Multiplicity constraint (flat cap, not source-relative)
# ============================================================


def test_max_multiplicity_cap_is_never_exceeded():
    _source, library = _library_from("kolam19", 1)
    grid = {(x, y) for x in range(10) for y in range(10)}

    placements = select_novel_placements(library, grid, max_multiplicity=1)
    from engine.generation import build_candidate_graph

    candidate = build_candidate_graph(placements, grid)
    mult = Counter(frozenset(e) for e in candidate.edges())
    assert all(count <= 1 for count in mult.values())


def test_max_multiplicity_cap_respects_higher_values():
    _source, library = _library_from("kolam19", 1)
    grid = {(x, y) for x in range(10) for y in range(10)}

    placements = select_novel_placements(library, grid, max_multiplicity=DEFAULT_MAX_MULTIPLICITY)
    from engine.generation import build_candidate_graph

    candidate = build_candidate_graph(placements, grid)
    mult = Counter(frozenset(e) for e in candidate.edges())
    assert all(count <= DEFAULT_MAX_MULTIPLICITY for count in mult.values())


# ============================================================
# General correctness
# ============================================================


def test_extract_motif_library_deduplicates_shapes():
    _source, library = _library_from("kolam19", 1)
    assert len(library) == len(set(library))  # no duplicate shapes


def test_generation_produces_some_structure_on_a_fresh_grid():
    _source, library = _library_from("kolam19", 1)
    grid = {(x, y) for x in range(15) for y in range(15)}
    candidate = generate_novel_kolam(library, grid)
    assert candidate.graph.number_of_edges() > 0  # bootstraps successfully,
    # not the degenerate zero-placements result the first (buggy) scoring
    # design produced -- see engine/novel_generation.py's _novel_score
    # docstring for why a naive parity-only score can never bootstrap.


def test_novel_generation_deterministic():
    _source, library = _library_from("kolam19", 1)
    grid = {(x, y) for x in range(10) for y in range(10)}

    a = generate_novel_kolam(library, grid)
    b = generate_novel_kolam(library, grid)

    assert {frozenset(e) for e in a.graph.edges()} == {frozenset(e) for e in b.graph.edges()}
    assert Counter(frozenset(e) for e in a.graph.edges()) == Counter(frozenset(e) for e in b.graph.edges())


def test_novel_generation_does_not_mutate_library_or_layout():
    _source, library = _library_from("kolam19", 1)
    library_before = list(library)
    grid = {(x, y) for x in range(10) for y in range(10)}
    grid_before = set(grid)

    generate_novel_kolam(library, grid)

    assert library == library_before
    assert grid == grid_before


def test_novel_candidate_reports_honest_validity_not_repaired():
    _source, library = _library_from("kolam19", 1)
    grid = {(x, y) for x in range(15) for y in range(15)}
    candidate = generate_novel_kolam(library, grid)

    # whatever the outcome, is_valid must agree with a direct check --
    # no special-cased "looks close enough" leniency for generated data
    from engine.validity import is_valid_single_stroke

    assert candidate.is_valid == is_valid_single_stroke(candidate.graph)
    if not candidate.is_valid:
        assert candidate.dot_trace is None  # never a fabricated trace for an invalid candidate
