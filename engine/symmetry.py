"""D4-symmetry-aware motif matching.

`motifs.induce_motif` only recognizes a repeat if it is an EXACT match
under translation. Real kolam patterns repeat a local shape under
rotation and reflection just as often (a motif stamped facing "up" at
one dot and "sideways" at its rotated neighbor). This module extends
motif clustering to match under the full D4 group (4 rotations x 2
reflections = 8 transforms), so those repeats are recognized as the same
motif instead of counted as separate one-off signatures.
"""

from __future__ import annotations

from collections import Counter
from typing import Union

import networkx as nx

from engine.kolam_pattern import KolamPattern
from engine.motifs import Motif, RelEdge, interior_points as _interior_points, local_window

Point = tuple[int, int]
GraphLike = Union[nx.MultiGraph, KolamPattern]

# The 8 symmetries of the square, acting on integer-coordinate points.
D4_TRANSFORMS: dict[str, "callable[[Point], Point]"] = {
    "identity": lambda p: (p[0], p[1]),
    "rot90": lambda p: (-p[1], p[0]),
    "rot180": lambda p: (-p[0], -p[1]),
    "rot270": lambda p: (p[1], -p[0]),
    "reflect_x": lambda p: (p[0], -p[1]),
    "reflect_y": lambda p: (-p[0], p[1]),
    "reflect_diag": lambda p: (p[1], p[0]),
    "reflect_antidiag": lambda p: (-p[1], -p[0]),
}


def apply_transform(name: str, motif: Motif) -> Motif:
    t = D4_TRANSFORMS[name]
    edges: list[RelEdge] = []
    for a, b in motif:
        ta, tb = t(a), t(b)
        edges.append(tuple(sorted([ta, tb])))
    return tuple(sorted(edges))


def canonical_motif(motif: Motif) -> Motif:
    """Lexicographically-smallest representation of `motif` across all 8
    D4 transforms -- the symmetry-invariant signature used for clustering."""
    if not motif:
        return motif
    return min(apply_transform(name, motif) for name in D4_TRANSFORMS)


def find_transform(motif_canon: Motif, window: Motif) -> str | None:
    """Which D4 transform turns the canonical motif into `window`?
    Returns None if `window` is not a D4 image of `motif_canon` (both
    empty is always 'identity')."""
    for name in D4_TRANSFORMS:
        if apply_transform(name, motif_canon) == window:
            return name
    return None


def induce_motif_symmetric(
    G, interior: set[Point], dots: set[Point], radius: int = 1
) -> tuple[Motif, float, dict[Point, str]]:
    """Like motifs.induce_motif, but two windows count as the same motif if
    one is a D4 (rotation/reflection) image of the other.

    Returns (canonical_motif, coverage_fraction, transform_per_point) where
    transform_per_point maps each interior point whose window matched the
    dominant motif to the specific D4 transform that reproduces its window
    from the canonical motif.
    """
    if not interior:
        return (), 0.0, {}

    windows = {c: local_window(G, c, dots, radius) for c in interior}
    canon = {c: canonical_motif(w) for c, w in windows.items()}
    counts = Counter(canon.values())
    motif_canon, count = counts.most_common(1)[0]

    transform_per_point = {}
    for c, w in windows.items():
        if canon[c] == motif_canon:
            t = find_transform(motif_canon, w)
            transform_per_point[c] = t

    return motif_canon, count / len(interior), transform_per_point


def analyze_symmetry(
    G: GraphLike,
    dots: set[Point] | None = None,
    radius: int = 1,
) -> tuple[Motif, float, dict[Point, str]]:
    """Thin, pattern-friendly entry point for induce_motif_symmetric: `G`
    may be an nx.MultiGraph with `dots` given explicitly (existing
    behavior), or a KolamPattern, in which case `dots` defaults to
    pattern.dot_points and the interior-point set is computed
    automatically at the given `radius`. Returns exactly what
    induce_motif_symmetric returns -- this adds no new analysis, just a
    call signature that doesn't require the caller to already know the
    dots/interior split."""
    if isinstance(G, KolamPattern):
        pattern = G
        G = pattern.graph
        if dots is None:
            dots = pattern.dot_points
    if dots is None:
        raise TypeError("dots is required when G is a raw MultiGraph, not a KolamPattern")
    interior = _interior_points(dots, radius=radius)
    return induce_motif_symmetric(G, interior, dots, radius=radius)
