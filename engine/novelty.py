"""Structural novelty measurement for generated candidates.

Distinguishes two genuinely different comparisons, both real and both
reported, rather than collapsing them into one fuzzy "novelty score":

1. **Coordinate-exact comparison** -- only meaningful when a candidate
   and a source pattern share the exact same dot layout (same convention
   `engine.novel_generation.duplicates_source` already established:
   comparing different layouts is not "not novel," it's simply not a
   comparable pair at all, and this module returns `None`/excludes it
   from the rate rather than inventing a number for it).
2. **Topological/structural comparison** -- layout-independent, via a
   translation- and D4-symmetry-canonical graph fingerprint (the exact
   same 8-transform canonicalization idea `engine.symmetry.canonical_motif`
   already uses for local motif windows, applied here to a whole graph's
   edge multiset instead). Two candidates on DIFFERENT dot layouts can
   still be flagged as the same shape if one is a translated/rotated/
   reflected copy of the other.

Neither comparison claims anything about VISUAL or artistic novelty --
see docs/NOVEL_GENERATION.md's own explicit disclaimer on this, repeated
here because it still applies: these are strict, mechanical, structural
checks only.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import networkx as nx

from engine.symmetry import D4_TRANSFORMS

if TYPE_CHECKING:
    from engine.generated_kolam import GeneratedKolam
    from engine.kolam_pattern import KolamPattern

Point = tuple[int, int]


def graph_fingerprint(graph: nx.MultiGraph) -> tuple:
    """Translation- and D4-canonical fingerprint of `graph`'s edge
    multiset: the lexicographically smallest of the 8 D4-transformed,
    then translation-normalized (shifted so the edge set's own bounding
    box starts at the origin) representations. Two graphs with identical
    fingerprints are the same shape up to translation, rotation, and
    reflection -- NOT full arbitrary-relabeling graph isomorphism, but
    exactly the symmetry group this project's lattice data actually has
    (`engine.symmetry.D4_TRANSFORMS`), which is what "is this just a
    transformed copy of something else" needs.

    Empty graph (no edges) -> `()`, a single well-defined fingerprint for
    "nothing here" so it never collides by accident with a real shape.
    """
    edges: Counter = Counter(frozenset(e) for e in graph.edges())
    if not edges:
        return ()

    best: tuple | None = None
    for transform in D4_TRANSFORMS.values():
        transformed = []
        for e, count in edges.items():
            a, b = tuple(e)
            ta, tb = transform(a), transform(b)
            transformed.append((tuple(sorted([ta, tb])), count))

        xs = [pt[0] for edge, _ in transformed for pt in edge]
        ys = [pt[1] for edge, _ in transformed for pt in edge]
        min_x, min_y = min(xs), min(ys)

        normalized = tuple(
            sorted(
                (((ax - min_x, ay - min_y), (bx - min_x, by - min_y)), count)
                for ((ax, ay), (bx, by)), count in transformed
            )
        )
        if best is None or normalized < best:
            best = normalized

    return best  # type: ignore[return-value]


def _edge_counter(graph: nx.MultiGraph) -> Counter:
    return Counter(frozenset(e) for e in graph.edges())


def multiset_jaccard_similarity(a: Counter, b: Counter) -> float:
    """Multiplicity-aware Jaccard similarity: sum(min(count)) / sum(max(count))
    over the union of edge keys. 1.0 = identical edge multisets (including
    exact strand counts, not just connectivity); 0.0 = no shared edges.
    Two empty multisets are defined as identical (1.0), matching the
    conventional empty-set-Jaccard-is-1 convention."""
    keys = set(a) | set(b)
    if not keys:
        return 1.0
    inter = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    union = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return inter / union if union else 1.0


def coordinate_similarity(candidate_graph: nx.MultiGraph, source: "KolamPattern") -> "float | None":
    """Jaccard similarity of edge multisets, valid ONLY when `candidate_graph`
    and `source` share the exact same dot layout (`source.dot_points`) --
    matches `engine.novel_generation.duplicates_source`'s own convention.
    Returns None (not a meaningful comparison, not a low-similarity score)
    when the layouts differ."""
    if set(candidate_graph.nodes()) != source.dot_points:
        return None
    return multiset_jaccard_similarity(_edge_counter(candidate_graph), _edge_counter(source.graph))


def novelty_report(
    candidates: "list[GeneratedKolam]",
    sources: "list[KolamPattern]",
    near_duplicate_threshold: float = 0.9,
) -> dict:
    """Aggregate novelty measurement over a batch of candidates against a
    pool of source patterns. Every rate is computed from an executable
    comparison against the actual candidates/sources passed in -- nothing
    here is asserted or assumed.

    Fields:
      n_candidates                        : len(candidates)
      n_unique_fingerprints                : distinct graph_fingerprint()
                                              values across candidates --
                                              are candidates even distinct
                                              from EACH OTHER, not just
                                              from the sources
      unique_rate                          : n_unique_fingerprints / n_candidates
      exact_topological_duplicate_rate     : fraction of candidates whose
                                              graph_fingerprint matches ANY
                                              source's fingerprint (layout-
                                              independent -- a rotated/
                                              reflected/translated exact
                                              copy still counts)
      exact_coordinate_duplicate_rate      : among candidate/source PAIRS
                                              that share a dot layout
                                              (coordinate_similarity !=
                                              None), fraction with
                                              similarity == 1.0. None if
                                              zero such comparable pairs
                                              exist (e.g. every candidate
                                              was generated on a synthetic
                                              layout no source pattern
                                              uses) -- NOT reported as 0.
      near_duplicate_rate                  : fraction of candidates whose
                                              BEST coordinate_similarity
                                              against any comparable
                                              source is in
                                              [near_duplicate_threshold, 1.0)
                                              -- close but not exact.
      n_coordinate_comparable_pairs        : how many candidate/source
                                              pairs were even layout-
                                              comparable, so a reader can
                                              tell whether the coordinate-
                                              based rates rest on a
                                              meaningful sample size or a
                                              near-empty one.
    """
    n = len(candidates)
    source_fingerprints = {graph_fingerprint(s.graph) for s in sources}
    empty_fp = graph_fingerprint(nx.MultiGraph())  # == ()

    unique_fingerprints: set = set()
    n_exact_topological_dup = 0
    n_near_dup = 0
    n_comparable_pairs = 0
    n_exact_coordinate_dup = 0

    for c in candidates:
        fp = graph_fingerprint(c.graph)
        unique_fingerprints.add(fp)
        if fp != empty_fp and fp in source_fingerprints:
            n_exact_topological_dup += 1

        best_sim = None
        for s in sources:
            sim = coordinate_similarity(c.graph, s)
            if sim is None:
                continue
            n_comparable_pairs += 1
            if sim == 1.0:
                n_exact_coordinate_dup += 1
            if best_sim is None or sim > best_sim:
                best_sim = sim
        if best_sim is not None and near_duplicate_threshold <= best_sim < 1.0:
            n_near_dup += 1

    return {
        "n_candidates": n,
        "n_unique_fingerprints": len(unique_fingerprints),
        "unique_rate": (len(unique_fingerprints) / n) if n else None,
        "exact_topological_duplicate_rate": (n_exact_topological_dup / n) if n else None,
        "exact_coordinate_duplicate_rate": (n_exact_coordinate_dup / n_comparable_pairs) if n_comparable_pairs else None,
        "near_duplicate_rate": (n_near_dup / n) if n else None,
        "near_duplicate_threshold": near_duplicate_threshold,
        "n_coordinate_comparable_pairs": n_comparable_pairs,
    }
