"""Local-motif induction via canonical-signature clustering.

Works on nx.MultiGraph: signatures are multisets of relative edges (not
plain sets), so two dots with a genuine double strand between them are
distinguished from two dots with a single strand.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Union

import networkx as nx

from engine.kolam_pattern import KolamPattern

GraphLike = Union[nx.MultiGraph, KolamPattern]

RelEdge = tuple[tuple[int, int], tuple[int, int]]
Motif = tuple[RelEdge, ...]
Point = tuple[int, int]
Edge = frozenset  # frozenset({point, point}), used as the graph-level edge key

# Description-length accounting units, shared by description_size,
# compression_ratio, and mdl_gain -- defined ONCE here so every cost
# comparison in the module uses the same currency:
#   an edge = 2 endpoints x 2 coords = 4 numbers
#   a motif rule = len(motif) relative edges, each 4 numbers, stated once
#   a placement instance = (x, y, transform id) = 3 numbers
EDGE_UNIT_COST = 4
PLACEMENT_COST = 3


def interior_points(dots: set[tuple[int, int]], radius: int = 1) -> set[tuple[int, int]]:
    """Dots far enough from the bounding-box edge that a radius-`radius`
    window around them is never truncated by the grid boundary."""
    if not dots:
        return set()
    xs = [p[0] for p in dots]
    ys = [p[1] for p in dots]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return {
        (x, y)
        for (x, y) in dots
        if min_x + radius <= x <= max_x - radius and min_y + radius <= y <= max_y - radius
    }


def relative_multiedges(
    G: nx.MultiGraph,
    center: tuple[int, int],
    dots: set[tuple[int, int]],
    radius: int = 1,
) -> list[RelEdge]:
    """Multiset of edges in the induced subgraph around `center` (Chebyshev
    radius `radius`), re-expressed in coordinates relative to center."""
    cx, cy = center
    nearby = [
        (x, y) for (x, y) in dots if abs(x - cx) <= radius and abs(y - cy) <= radius
    ]
    sub = G.subgraph(nearby)
    rel_edges = []
    for a, b in sub.edges():
        ra = (a[0] - cx, a[1] - cy)
        rb = (b[0] - cx, b[1] - cy)
        rel_edges.append(tuple(sorted([ra, rb])))
    return rel_edges


def local_window(
    G: nx.MultiGraph,
    center: tuple[int, int],
    dots: set[tuple[int, int]],
    radius: int = 1,
) -> Motif:
    """Canonical, order-independent, multiplicity-preserving signature of
    the local neighborhood around `center`."""
    return tuple(sorted(relative_multiedges(G, center, dots, radius)))


def induce_motif(
    G: nx.MultiGraph,
    interior: set[tuple[int, int]],
    dots: set[tuple[int, int]],
    radius: int = 1,
) -> tuple[Motif, float]:
    """Find the dominant repeating local motif via canonical-signature
    clustering. Returns (motif, coverage_fraction)."""
    if not interior:
        return (), 0.0
    windows = {c: local_window(G, c, dots, radius) for c in interior}
    signatures = Counter(windows.values())
    motif, count = signatures.most_common(1)[0]
    return motif, count / len(interior)


@dataclass
class MotifPlacement:
    """One rule ('this motif') plus every point it was stamped at."""

    motif: Motif
    points: list[Point]
    transforms: dict[Point, str]
    new_edges: set = field(default_factory=set)  # edges this motif newly covered when selected
    radius: int | None = None  # which window radius this motif was found at (see induce_motif_set_adaptive)


def _stamped_edges(motif: Motif, points: list[Point], transforms: dict[Point, str], dots: set[Point]) -> set:
    """Edge set (deduped) produced by stamping `motif` at every point in
    `points`, applying each point's D4 transform. Edges landing outside
    `dots` are dropped, exactly as engine.generation.apply_motif does --
    inlined here (rather than imported) to avoid a circular import, since
    engine.generation imports engine.motifs."""
    from engine.symmetry import apply_transform  # local import: symmetry imports motifs

    edges = set()
    for cx, cy in points:
        t_name = transforms.get((cx, cy), "identity")
        rel_edges = motif if t_name == "identity" else apply_transform(t_name, motif)
        for (dx1, dy1), (dx2, dy2) in rel_edges:
            a = (cx + dx1, cy + dy1)
            b = (cx + dx2, cy + dy2)
            if a in dots and b in dots:
                edges.add(frozenset({a, b}))
    return edges


def _build_candidates(
    G: nx.MultiGraph, interior: set[Point], dots: set[Point], radius: int
) -> dict[Motif, tuple[list[Point], dict[Point, str], set]]:
    """Shared candidate-generation step used by both induce_motif_set and
    induce_motif_set_adaptive: D4-canonicalized local-window clustering
    (grouped by interior point, exactly as in symmetry.induce_motif_symmetric),
    each candidate's transform-per-point and full stamped edge set
    precomputed once (they don't change as a caller's `remaining` shrinks)."""
    from engine.symmetry import canonical_motif, find_transform  # local import, see _stamped_edges

    windows = {c: local_window(G, c, dots, radius) for c in interior}
    canon = {c: canonical_motif(w) for c, w in windows.items()}

    groups: dict[Motif, list[Point]] = {}
    for c, cm in canon.items():
        if not cm:  # empty window: no nearby edges, not a real motif
            continue
        groups.setdefault(cm, []).append(c)

    candidates: dict[Motif, tuple[list[Point], dict[Point, str], set]] = {}
    for cm, pts in groups.items():
        transforms = {p: find_transform(cm, windows[p]) for p in pts}
        edges = _stamped_edges(cm, pts, transforms, dots)
        candidates[cm] = (pts, transforms, edges)
    return candidates


def induce_motif_set(
    G: GraphLike,
    interior: set[Point] | None = None,
    dots: set[Point] | None = None,
    radius: int = 1,
    max_motifs: int = 10,
    target_edges: set | None = None,
) -> tuple[list[MotifPlacement], set, bool]:
    """Generalizes induce_motif to a SET of D4-symmetry-matched motifs,
    chosen by greedy set cover over the graph's edges.

    Candidate motifs are the window-signature clusters computed exactly as
    in symmetry.induce_motif_symmetric (D4-canonicalized local windows,
    grouped by interior point). At each step, the candidate whose stamped
    edge set covers the most currently-uncovered real edges is selected;
    its edges are marked covered; repeat until every edge of G is covered
    or `max_motifs` motifs have been selected, whichever comes first.

    `target_edges` overrides what counts as "needs covering": defaults to
    every distinct edge of G, but induce_motif_set_adaptive passes just
    the residual from a previous (smaller-radius) pass, so a retry at a
    larger radius only gets credit for edges still actually uncovered,
    not edges another tier already explained.

    `G` may be an nx.MultiGraph (existing behavior, `interior`/`dots`
    required) or a KolamPattern -- passing a KolamPattern auto-derives
    `dots` from pattern.dot_points and `interior` via interior_points()
    at the given `radius` if either is omitted, so `induce_motif_set(pattern)`
    works with no other arguments.

    Returns (placements, residual_edges, fully_covered) where
    residual_edges is the set of edges (as frozensets) no selected motif
    explains -- these must be listed explicitly for a lossless encoding,
    see compression_ratio.

    NOTE: this function maximizes COVERAGE (most new edges per pick), not
    description length -- it's kept as-is (and still tested/used this
    way) for straightforward fixed-radius induction. induce_motif_set_adaptive
    is the one that optimizes description length (see mdl_gain); it uses
    _build_candidates directly rather than calling this function.
    """
    if isinstance(G, KolamPattern):
        pattern = G
        G = pattern.graph
        if dots is None:
            dots = pattern.dot_points
        if interior is None:
            interior = interior_points(dots, radius=radius)
    if interior is None or dots is None:
        raise TypeError("interior and dots are required when G is a raw MultiGraph, not a KolamPattern")

    target = set(target_edges) if target_edges is not None else {frozenset(e) for e in G.edges()}

    if not interior:
        return [], target, len(target) == 0

    candidates = _build_candidates(G, interior, dots, radius)

    remaining = set(target)
    selected: list[MotifPlacement] = []

    while remaining and candidates and len(selected) < max_motifs:
        best_cm, best_gain, best_new = None, -1, None
        for cm, (pts, transforms, edges) in candidates.items():
            gain_set = edges & remaining
            if len(gain_set) > best_gain:
                best_cm, best_gain, best_new = cm, len(gain_set), gain_set
        if best_gain <= 0:
            break  # no remaining candidate explains any uncovered edge
        pts, transforms, _ = candidates.pop(best_cm)
        selected.append(MotifPlacement(motif=best_cm, points=pts, transforms=transforms, new_edges=best_new))
        remaining -= best_new

    return selected, remaining, len(remaining) == 0


def _points_near(points: set[Point], radius: int, universe: set[Point]) -> set[Point]:
    """Points in `universe` within Chebyshev `radius` of any of `points`."""
    near: set[Point] = set()
    for px, py in points:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                c = (px + dx, py + dy)
                if c in universe:
                    near.add(c)
    return near


def mdl_gain(
    candidate_motif: Motif,
    new_placements: list[Point],
    newly_covered_edges: set,
    is_new_motif_type: bool,
) -> int:
    """Net change in total description length (same field-count units as
    description_size/compression_ratio: EDGE_UNIT_COST, PLACEMENT_COST)
    from accepting `candidate_motif` with these placements right now.
    Positive = the encoding gets SHORTER; this is the only quantity
    induce_motif_set_adaptive uses to decide whether to add a motif.

      benefit: each newly-covered edge no longer needs to be listed as an
        explicit residual edge (EDGE_UNIT_COST each).
      cost: the motif RULE itself -- but only if this is the first time
        this exact D4-canonical rule is being introduced
        (len(candidate_motif) * EDGE_UNIT_COST, same convention as
        description_size); reusing an already-paid-for rule is free.
        Plus PLACEMENT_COST per new placement instance, charged every
        time regardless of whether the rule is new.

    A single-instance, single-relative-edge motif is ALWAYS net negative
    here (EDGE_UNIT_COST - EDGE_UNIT_COST - PLACEMENT_COST = -PLACEMENT_COST
    < 0 for any 1-edge, 1-placement, new-type candidate) -- a rule stated
    once is never cheaper than just writing down the raw edge, which is
    exactly the "not a real repeating rule" case this gate should reject.
    """
    benefit = EDGE_UNIT_COST * len(newly_covered_edges)
    motif_rule_cost = len(candidate_motif) * EDGE_UNIT_COST if is_new_motif_type else 0
    placement_cost = PLACEMENT_COST * len(new_placements)
    return benefit - motif_rule_cost - placement_cost


def induce_motif_set_adaptive(
    G: GraphLike,
    interior_points: set[Point] | None = None,
    dots_set: set[Point] | None = None,
    max_radius: int = 3,
    max_motifs_per_radius: int = 500,
) -> tuple[list[MotifPlacement], set, bool]:
    """Resolve the radius=1-vs-radius=2 tradeoff by making window radius
    ADAPTIVE PER REGION instead of a single global choice (see PULLI
    session notes: radius=1 alone plateaus around 85-93% recall on real
    kolams; radius=2 alone reaches 100% on a small pattern but drops to
    35% on a large one within the same motif budget, because the finer
    window fragments less-periodic regions into many tiny clusters).

    THE OBJECTIVE THIS OPTIMIZES: minimize total description length, not
    maximize recall. At every step it evaluates ALL remaining candidate
    motifs across every radius tier introduced so far by mdl_gain, picks
    the single best, and adds it ONLY if that gain is positive. It stops
    -- for good, not just for the current tier -- the moment no remaining
    candidate at any tried radius would shorten the encoding. Escalating
    to a larger radius is itself gated on there being uncovered edges
    left AND max_radius allowing it; it is not a fallback for "still not
    enough motifs," because motif COUNT is no longer a target at all.
    `max_motifs_per_radius` is kept only as a hard safety ceiling on total
    placements, set far above where the gate would ever naturally stop --
    it should not be relied on to actually terminate the loop.

    Radius escalation still only searches interior points near the
    current residual (not the whole pattern), for the same fragmentation
    reason as before: paying radius=2/3's finer-grained clustering cost
    only where radius=1 left edges unexplained, not everywhere.

    `G` may be an nx.MultiGraph (existing behavior, `interior_points`/
    `dots_set` required) or a KolamPattern -- passing a KolamPattern
    auto-derives `dots_set` from pattern.dot_points and `interior_points`
    at radius=1 if either is omitted, so `induce_motif_set_adaptive(pattern)`
    works with no other arguments.

    Each returned MotifPlacement has `.radius` set to the tier it was
    selected at. Returns (placements, residual_edges, fully_covered).
    """
    import engine.motifs as _self  # self-import: safe, the module is
    # already fully initialized by the time this function is called.
    # Needed because the `interior_points` PARAMETER shadows the
    # module-level `interior_points` FUNCTION for this entire function
    # body -- Python resolves names per-function, not line-by-line.

    if isinstance(G, KolamPattern):
        pattern = G
        G = pattern.graph
        if dots_set is None:
            dots_set = pattern.dot_points
        if interior_points is None:
            interior_points = _self.interior_points(dots_set, radius=1)
    if interior_points is None or dots_set is None:
        raise TypeError(
            "interior_points and dots_set are required when G is a raw MultiGraph, not a KolamPattern"
        )

    remaining = {frozenset(e) for e in G.edges()}
    all_placements: list[MotifPlacement] = []
    used_motif_types: set[Motif] = set()

    # cm -> (points, transforms, edges, radius_found_at); accumulates
    # across radius tiers as they're introduced, never rebuilt from
    # scratch, so gain evaluation always spans every tried radius at once.
    candidates: dict[Motif, tuple[list[Point], dict[Point, str], set, int]] = {}
    for cm, (pts, transforms, edges) in _self._build_candidates(G, interior_points, dots_set, 1).items():
        candidates[cm] = (pts, transforms, edges, 1)

    current_radius = 1

    while remaining:
        best_cm, best_gain, best_new = None, 0, None
        for cm, (pts, transforms, edges, _r) in candidates.items():
            gain_set = edges & remaining
            g = mdl_gain(cm, pts, gain_set, cm not in used_motif_types)
            if g > best_gain:
                best_cm, best_gain, best_new = cm, g, gain_set

        if best_cm is not None:
            pts, transforms, _edges, r = candidates.pop(best_cm)
            all_placements.append(
                MotifPlacement(motif=best_cm, points=pts, transforms=transforms, new_edges=best_new, radius=r)
            )
            used_motif_types.add(best_cm)
            remaining -= best_new
            if len(all_placements) >= max_motifs_per_radius:
                break  # hard safety ceiling only -- should not trigger in practice
            continue

        # No positive-gain candidate anywhere in the pool: escalate to the
        # next radius tier (if any budget left) rather than stopping,
        # since a larger window might still find a genuine repeating rule.
        if current_radius >= max_radius:
            break
        current_radius += 1
        radius_interior = _self.interior_points(dots_set, radius=current_radius)
        residual_points = {p for e in remaining for p in e}
        near = _points_near(residual_points, current_radius, radius_interior)
        if near:
            for cm, (pts, transforms, edges) in _self._build_candidates(G, near, dots_set, current_radius).items():
                if cm not in candidates:  # don't clobber a not-yet-selected lower-radius candidate
                    candidates[cm] = (pts, transforms, edges, current_radius)
        # if `near` is empty, the loop just tries the next radius tier
        # (current_radius already advanced) rather than looping forever.

    return all_placements, remaining, len(remaining) == 0


def description_size(placements: list[MotifPlacement], n_residual_edges: int) -> int:
    """Honest encoding cost, in the same EDGE_UNIT_COST/PLACEMENT_COST
    units as mdl_gain:
      - each distinct motif rule costs EDGE_UNIT_COST per relative edge
        (stated once, however many times it's placed -- NOTE: unlike
        mdl_gain, this charges every placement's rule cost once per
        MotifPlacement, since each entry here is already one distinct
        rule by construction)
      - each placement instance costs PLACEMENT_COST (x, y, transform id)
      - each residual (unexplained) edge must be listed explicitly at the
        same EDGE_UNIT_COST as a raw edge -- a motif grammar that leaves
        edges uncovered is not actually a lossless encoding of them.
    """
    total = 0
    for p in placements:
        total += len(p.motif) * EDGE_UNIT_COST + len(p.points) * PLACEMENT_COST
    total += n_residual_edges * EDGE_UNIT_COST
    return total


def compression_ratio(
    G: nx.MultiGraph, placements: list[MotifPlacement], residual_edges: set
) -> float:
    """Raw encoding size of the full pattern divided by the honest
    description size: motif rules + placements + explicit residual edges.
    Superseded from the old (naive) version, which only divided by a
    single motif's own edge count and silently assumed 100% coverage with
    free placement -- that inflated every compression number computed
    against real data, where a single motif typically covers well under
    half the pattern (see PULLI session notes).

    NOTE on multiplicity: `placements`/`residual_edges` (from
    induce_motif_set) identify edges by DISTINCT (a, b) connectivity, not
    exact parallel-strand count -- covering an edge once counts as fully
    explained even if the original has a double strand there. So raw_size
    is computed on that same distinct-edge basis (not G.number_of_edges(),
    which counts each parallel strand separately) to keep numerator and
    denominator on one accounting basis. This ratio therefore measures
    CONNECTIVITY compression, not exact strand-multiplicity reconstruction
    -- that stronger property is what validity.check_self_consistency
    checks instead, and is reported separately."""
    n_distinct_edges = len({frozenset(e) for e in G.edges()})
    raw_size = n_distinct_edges * EDGE_UNIT_COST
    size = description_size(placements, len(residual_edges))
    if size == 0:
        return float("inf") if raw_size == 0 else 0.0
    return raw_size / size
