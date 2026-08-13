"""M3.6: multiplicity-aware motif selection.

THE BUG THIS FIXES (see docs/RECONSTRUCTION.md's "over-explanation"
limitation): every existing induction function (induce_motif_set,
induce_motif_set_adaptive, mdl_gain) tracks edge coverage as a DISTINCT
PAIR SET -- `remaining = {frozenset(e) for e in G.edges()}` collapses a
source double-strand edge down to one boolean "covered or not," and
`build_candidate_graph` then stamps a placement's FULL edge set
(strand-for-strand) regardless of whether some OTHER already-selected
placement independently also stamps that same pair. Two placements can
each legitimately explain the same real double-strand edge once each,
netting 2 strands where only... or one covers it and another ALSO
touches it incidentally, netting MORE strands than source actually has.
Neither existing selection algorithm can even detect this, because
neither one tracks per-edge STRAND COUNT at all, only presence/absence.

This module tracks per-edge strand counts (Counter, not set) at the
granularity of ONE INDIVIDUAL (motif, point, transform) stamp, checks
every candidate against the running accumulated total BEFORE accepting
it, and REJECTS (never clips) any candidate that would push any touched
edge's count above what the source actually has. This is a structural
guarantee, not a heuristic: by construction, the motif-only candidate
this module produces can never over-explain any edge.

Candidates are still SCORED as whole motif-type GROUPS (one canonical
motif, every interior point that shares it), matching
engine.motifs.induce_motif_set_adaptive's own candidate shape -- a per-
POINT scoring pass was tried first and rejected (see git history):
evaluated one point at a time, a brand-new motif type always pays its
full rule cost on its very first, lone instance and scores negative,
even when it would clearly pay off after being reused across dozens of
points. Scoring the whole group at once lets the rule cost amortize
across every point that will reuse it, exactly like the existing
induction algorithm already does -- but UNLIKE the existing algorithm,
each point WITHIN an accepted group is still individually multiplicity-
checked before being added (see _filter_valid_points), so a group can be
selected and only PART of its points actually get placed.

Two selection modes, sharing one greedy core (_greedy_select) and
differing only in the scoring function:
  - induce_motif_set_multiplicity_aware: Task 2's baseline -- reward
    strands explained, penalize motif complexity and placement cost,
    using the SAME EDGE_UNIT_COST/PLACEMENT_COST currency
    engine.motifs already established (not a new arbitrary scale).
  - induce_motif_set_eulerian_aware: Task 4's second baseline -- the
    same score, PLUS a bonus for placements that move touched vertices
    toward even degree (closer to a valid Eulerian structure) and a
    matching penalty for placements that push a vertex further from
    even. Still gated by the exact same multiplicity constraint --
    parity never overrides it.

Deliberately NOT implemented (see docs/MOTIF_SELECTION.md
"Limitations of greedy selection"): no lookahead, no backtracking, no
ILP/CP-SAT formulation. This is a transparent, auditable baseline, not
an optimal solver -- greedy accept/reject decisions are permanent once
made, exactly like engine.motifs.induce_motif_set_adaptive's existing
greedy loop.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable

from engine.kolam_pattern import KolamPattern
from engine.motifs import (
    EDGE_UNIT_COST,
    PLACEMENT_COST,
    Motif,
    MotifPlacement,
    Point,
    _build_candidates,
)
from engine.motifs import interior_points as _interior_points
from engine.motifs import _points_near

# Same unit as one newly-explained strand (EDGE_UNIT_COST) -- a placement
# that fixes one odd-degree vertex is worth exactly as much, in this
# accounting, as explaining one more strand. Chosen for transparency
# (one named constant, not a tuned weight), not because it's provably
# optimal -- see docs/MOTIF_SELECTION.md.
PARITY_BONUS = EDGE_UNIT_COST


def simulate_placement_contribution(
    motif: Motif, point: Point, transform: str, dots: set[Point]
) -> Counter:
    """TASK 1: predicted per-edge STRAND contribution of one individual
    (motif, point, transform) stamp -- a Counter, not a set, so a motif
    with a repeated relative edge (e.g. a doubled-strand motif) correctly
    reports contributing 2 to that edge from this SINGLE stamp, and two
    different stamps that happen to land on the same physical edge can be
    summed correctly by the caller.

    Edges landing outside `dots` are dropped, same convention as
    engine.motifs._stamped_edges / engine.generation.apply_motif.
    """
    from engine.symmetry import apply_transform

    rel_edges = motif if transform == "identity" else apply_transform(transform, motif)
    contribution: Counter = Counter()
    cx, cy = point
    for (dx1, dy1), (dx2, dy2) in rel_edges:
        a = (cx + dx1, cy + dy1)
        b = (cx + dx2, cy + dy2)
        if a in dots and b in dots:
            contribution[frozenset({a, b})] += 1
    return contribution


def violates_multiplicity(
    contribution: Counter, accumulated: Counter, source_multiplicity: Counter
) -> bool:
    """TASK 1: True if accepting `contribution` on top of whatever is
    already `accumulated` would push ANY touched edge's strand count
    above `source_multiplicity` for that edge.

    This is a hard, binary predicate -- "the placement is incompatible,"
    per the task's own framing -- not a score, not a soft penalty. A
    caller that sees True must reject the WHOLE placement; there is no
    partial-acceptance path anywhere in this module (see module
    docstring: "never clips").
    """
    return any(
        accumulated.get(edge, 0) + count > source_multiplicity.get(edge, 0)
        for edge, count in contribution.items()
    )


def _score_multiplicity(
    motif: Motif, contribution: Counter, is_new_motif_type: bool, _degree_before: Counter
) -> float:
    """TASK 2 score: reward strands explained, penalize motif complexity
    (only once per NEW motif type -- reusing an already-paid-for rule is
    free, same convention as engine.motifs.mdl_gain) and this placement's
    own cost. All three terms reuse EDGE_UNIT_COST/PLACEMENT_COST, the
    SAME currency compression_ratio/mdl_gain already use -- not a new
    arbitrary scale.

    "Remaining uncovered edges" (the task's fourth factor) is satisfied
    structurally, not as an extra term: violates_multiplicity already
    guarantees every edge in an ACCEPTED contribution had real deficit
    remaining, so every strand counted here is, by construction, strictly
    useful progress toward the remaining uncovered total -- not an
    independent bonus to add on top.
    """
    strands_explained = sum(contribution.values())
    motif_rule_cost = len(motif) * EDGE_UNIT_COST if is_new_motif_type else 0
    return EDGE_UNIT_COST * strands_explained - motif_rule_cost - PLACEMENT_COST


def _parity_delta(contribution: Counter, degree_before: Counter) -> int:
    """Net number of vertices this contribution would move FROM odd TO
    even degree, minus the number it would move FROM even TO odd. A
    placement that fixes 2 odd vertices and breaks none scores +2; one
    that fixes 1 and breaks 1 (net neutral for parity, even though it
    changed two vertices) scores 0."""
    touched: set[Point] = set()
    for edge in contribution:
        a, b = tuple(edge)
        touched.add(a)
        touched.add(b)

    delta = 0
    for node in touched:
        deg_change = sum(count for edge, count in contribution.items() if node in edge)
        before_odd = degree_before.get(node, 0) % 2 == 1
        after_odd = (degree_before.get(node, 0) + deg_change) % 2 == 1
        if before_odd and not after_odd:
            delta += 1
        elif not before_odd and after_odd:
            delta -= 1
    return delta


def _score_multiplicity_eulerian(
    motif: Motif, contribution: Counter, is_new_motif_type: bool, degree_before: Counter
) -> float:
    """TASK 4 score: TASK 2's score plus a parity-improvement bonus/
    penalty. Still evaluated only for candidates that already passed
    violates_multiplicity -- parity considerations never override the
    hard multiplicity constraint, they only break ties among candidates
    that already satisfy it."""
    base = _score_multiplicity(motif, contribution, is_new_motif_type, degree_before)
    return base + PARITY_BONUS * _parity_delta(contribution, degree_before)


@dataclass
class SelectionResult:
    """Output of the multiplicity-aware greedy selectors.

    placements              : list[MotifPlacement], same type the rest
                               of engine/ (generate_kolam, reconstruct_kolam,
                               compression_ratio, ...) already consumes --
                               zero changes needed downstream.
    accumulated_multiplicity : {frozenset({a,b}): count} the motif-only
                               candidate actually produces. GUARANTEED
                               accumulated[e] <= source_multiplicity[e]
                               for every e, by construction (see module
                               docstring).
    residual_multiplicity    : source_multiplicity - accumulated, per
                               edge, only for edges with remaining
                               deficit (always >= 0 by the same
                               guarantee -- there is no over-explained
                               entry to represent as "negative residual").
    rejected_count            : number of individual (motif, point,
                               transform) candidates rejected outright
                               for violating the multiplicity constraint
                               across the whole run (diagnostic only).
    mode                      : "multiplicity" or "multiplicity_eulerian"
    """

    placements: list[MotifPlacement]
    accumulated_multiplicity: dict
    residual_multiplicity: dict
    rejected_count: int
    mode: str

    @property
    def residual_edges(self) -> set:
        """Distinct edges with any remaining deficit -- the same shape
        engine.motifs.compression_ratio's `residual_edges` argument
        expects, so SelectionResult plugs into the existing compression
        accounting with no adapter code."""
        return set(self.residual_multiplicity.keys())


def _filter_valid_points(
    motif: Motif,
    points: list[Point],
    transforms: dict[Point, str],
    dots: set[Point],
    accumulated: Counter,
    source_mult: Counter,
) -> tuple[list[tuple[Point, str, Counter]], Counter, int]:
    """Within ONE candidate motif-type group, walk its points in order and
    keep only those whose individual contribution does not violate the
    multiplicity constraint against `accumulated` PLUS whatever this same
    group's own earlier points already committed to (a later point in
    the same group CAN be rejected because an earlier point in the SAME
    group already used up the remaining budget on a shared edge -- this
    is the group-internal analog of Task 1's constraint, not just a
    cross-group check).

    Returns (valid_points, total_contribution, n_rejected) where
    valid_points is [(point, transform, its own contribution), ...] and
    total_contribution is the group's combined Counter across only the
    accepted points.
    """
    valid_points: list[tuple[Point, str, Counter]] = []
    total_contribution: Counter = Counter()
    n_rejected = 0

    for point in points:
        transform = transforms.get(point, "identity")
        contribution = simulate_placement_contribution(motif, point, transform, dots)
        if not contribution:
            continue
        combined_before = {
            edge: accumulated.get(edge, 0) + total_contribution.get(edge, 0) for edge in contribution
        }
        if violates_multiplicity(contribution, combined_before, source_mult):
            n_rejected += 1
            continue
        valid_points.append((point, transform, contribution))
        for edge, count in contribution.items():
            total_contribution[edge] += count

    return valid_points, total_contribution, n_rejected


def _greedy_select(
    source: KolamPattern,
    radius: int,
    max_radius: int,
    score_fn: Callable[[Motif, Counter, bool, Counter], float],
    mode: str,
) -> SelectionResult:
    dots = set(source.dot_points)
    source_mult = Counter(frozenset(e) for e in source.graph.edges())

    accumulated: Counter = Counter()
    degree: Counter = Counter()
    # motif -> {"points": [...], "transforms": {...}, "radius": int, "edges": set}
    selected: dict[Motif, dict] = {}
    used_motif_types: set[Motif] = set()
    rejected_count = 0

    for r in range(radius, max_radius + 1):
        deficit_edges = {e for e, s in source_mult.items() if accumulated.get(e, 0) < s}
        if not deficit_edges:
            break

        if r == radius:
            scope = _interior_points(dots, radius=r)
        else:
            radius_interior = _interior_points(dots, radius=r)
            residual_points = {p for e in deficit_edges for p in e}
            scope = _points_near(residual_points, r, radius_interior)
        if not scope:
            continue

        # {motif: (points, transforms, distinct_edges_set)} -- candidate
        # GROUPS (one canonical motif type, ALL its interior points at
        # this tier), matching engine.motifs.induce_motif_set_adaptive's
        # own candidate shape. Scoring a whole group (not one point at a
        # time) is what lets a motif's rule cost be amortized over all
        # its reuses -- see module docstring for why per-point scoring
        # alone was tried first and rejected (every fresh motif type
        # always scored negative on its first, lone instance).
        candidates = _build_candidates(source.graph, scope, dots, r)

        while candidates:
            best_motif, best_score = None, 0.0
            best_valid_points, best_contribution, best_rejected = None, None, 0

            for motif, (points, transforms, _edges) in candidates.items():
                valid_points, total_contribution, n_rejected = _filter_valid_points(
                    motif, points, transforms, dots, accumulated, source_mult
                )
                if not valid_points:
                    continue
                score = score_fn(motif, total_contribution, motif not in used_motif_types, degree)
                if score > best_score:
                    best_motif = motif
                    best_score = score
                    best_valid_points = valid_points
                    best_contribution = total_contribution
                    best_rejected = n_rejected

            if best_motif is None:
                break  # nothing left with positive score at this radius tier

            entry = selected.setdefault(
                best_motif, {"points": [], "transforms": {}, "radius": r, "edges": set()}
            )
            for point, transform, contribution in best_valid_points:
                for edge, count in contribution.items():
                    accumulated[edge] += count
                    a, b = tuple(edge)
                    degree[a] += count
                    degree[b] += count
                entry["points"].append(point)
                if transform != "identity":
                    entry["transforms"][point] = transform
            entry["edges"] |= set(best_contribution.keys())
            used_motif_types.add(best_motif)
            rejected_count += best_rejected

            del candidates[best_motif]  # permanently removed, matching
            # engine.motifs.induce_motif_set's own candidates.pop(best_cm)

    placements = [
        MotifPlacement(
            motif=motif,
            points=entry["points"],
            transforms=entry["transforms"],
            new_edges=entry["edges"],
            radius=entry["radius"],
        )
        for motif, entry in selected.items()
    ]
    residual_multiplicity = {
        edge: s - accumulated.get(edge, 0) for edge, s in source_mult.items() if accumulated.get(edge, 0) < s
    }

    return SelectionResult(
        placements=placements,
        accumulated_multiplicity=dict(accumulated),
        residual_multiplicity=residual_multiplicity,
        rejected_count=rejected_count,
        mode=mode,
    )


def induce_motif_set_multiplicity_aware(
    source: KolamPattern, radius: int = 1, max_radius: int = 3
) -> SelectionResult:
    """TASK 2: the multiplicity-aware greedy baseline. Never selects a
    placement that would push any edge's strand count above what
    `source` actually has -- see violates_multiplicity."""
    return _greedy_select(source, radius, max_radius, _score_multiplicity, mode="multiplicity")


def induce_motif_set_eulerian_aware(
    source: KolamPattern, radius: int = 1, max_radius: int = 3
) -> SelectionResult:
    """TASK 4: the multiplicity-aware baseline, plus scoring that also
    rewards moving vertices toward even degree. The multiplicity
    constraint is identical and non-negotiable -- parity only affects
    which of the ALREADY-VALID candidates is picked first, never whether
    an over-explaining candidate is allowed through."""
    return _greedy_select(
        source, radius, max_radius, _score_multiplicity_eulerian, mode="multiplicity_eulerian"
    )
