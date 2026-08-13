"""M3.7: novel structural generation.

THE DISTINCTION THIS MODULE EXISTS TO ENFORCE (see docs/RECONSTRUCTION.md
and docs/MOTIF_SELECTION.md): `engine.reconstruction.reconstruct_kolam`
answers "can THIS SOURCE be rebuilt," and does so by copying the exact
source residual edges back in -- it can only ever reproduce something
that already exists. This module answers a genuinely different
question: given a MOTIF LIBRARY (a set of abstract, reusable relative-
edge shapes -- engine.motifs.Motif, NOT engine.motifs.MotifPlacement,
which is tied to specific source coordinates) and a NEW dot layout the
library was never discovered from, can the library alone produce a
valid structural candidate?

There is no source graph anywhere in this module's placement logic --
select_novel_placements never receives one, so there is structurally
nothing for it to copy a residual FROM. This is the strongest possible
guarantee of the source-reconstruction/novel-generation distinction: not
"we chose not to copy," but "there was never anything available to copy."

PIPELINE (matches the task's own diagram):
  motif library + new dot layout
        -> select_novel_placements   (motif placement + multiplicity cap)
        -> engine.generation.generate_kolam (UNCHANGED, reused as-is:
           MultiGraph construction, Eulerian validity, deterministic
           trace -- exactly the M3 pipeline, pointed at placements that
           happen to have no source provenance instead of induced ones)
        -> GeneratedKolam candidate

"Multiplicity constraints" here means something different from M3.6's
source-relative check (there is no per-edge source count to check
against on an unseen layout) -- it is a flat structural cap,
`max_multiplicity`, informed by the real, verified dataset-wide fact
(docs/DATA_FORMAT.md) that source patterns only ever exhibit strand
multiplicity 1 or 2 on any edge, never more. Default 2, the observed
real-data ceiling, not an arbitrary number.
"""

from __future__ import annotations

from collections import Counter

from engine.generated_kolam import GeneratedKolam
from engine.generation import generate_kolam
from engine.kolam_pattern import KolamPattern
from engine.motifs import PLACEMENT_COST, EDGE_UNIT_COST, Motif, MotifPlacement, Point, interior_points
from engine.symmetry import D4_TRANSFORMS, apply_transform

DEFAULT_MAX_MULTIPLICITY = 2  # verified dataset-wide ceiling, see docs/DATA_FORMAT.md
DEFAULT_MAX_PLACEMENTS = 3000  # safety ceiling only, not a target -- see docs/NOVEL_GENERATION.md


def _stamp_contribution(motif: Motif, point: Point, transform: str, dots: set[Point]) -> Counter:
    """Same computation as engine.motif_selection.simulate_placement_contribution,
    duplicated here at module scope only to avoid a cross-module private
    import for something this small; identical semantics (edges landing
    outside `dots` are dropped, multiplicity within one stamp is counted
    exactly)."""
    rel_edges = motif if transform == "identity" else apply_transform(transform, motif)
    contribution: Counter = Counter()
    cx, cy = point
    for (dx1, dy1), (dx2, dy2) in rel_edges:
        a = (cx + dx1, cy + dy1)
        b = (cx + dx2, cy + dy2)
        if a in dots and b in dots:
            contribution[frozenset({a, b})] += 1
    return contribution


def extract_motif_library(placements: list[MotifPlacement]) -> list[Motif]:
    """The abstraction step: strips MotifPlacement objects (motif shape +
    SPECIFIC source coordinates + transforms) down to just the distinct
    motif SHAPES -- the reusable, source-independent part. This is what
    makes a "motif library": rules with no memory of where they came
    from, safe to hand to a layout that never produced them."""
    seen: dict[Motif, None] = {}
    for p in placements:
        seen.setdefault(p.motif, None)
    return list(seen.keys())


def _novel_score(motif: Motif, contribution: Counter, degree_before: Counter) -> float:
    """Scoring for placement onto an UNSEEN layout, deliberately NOT a
    reuse of engine.motif_selection._parity_delta as-is: that function
    treats every touched node's PRE-EXISTING degree as a baseline to
    protect, which is correct when there is already a partial
    reconstruction in progress (M3.6), but wrong here -- on a brand-new
    layout every node starts at degree 0, and _parity_delta would score
    the very FIRST edge ever placed as "breaking" two nodes from even
    (0) to odd (1), permanently blocking any placement from ever
    bootstrapping a structure at all (found by direct testing, not
    theorized: the naive reuse produced zero placements on every input).

    Fix: a node touched for the first time (degree_before == 0) has no
    parity state to protect -- giving it any structure at all is pure
    growth, not a tradeoff. Only nodes that already have degree > 0
    (touched by a PREVIOUS accepted placement) get the parity
    reward/penalty treatment."""
    touched: set[Point] = set()
    for edge in contribution:
        a, b = tuple(edge)
        touched.add(a)
        touched.add(b)

    growth = 0
    parity = 0
    for node in touched:
        deg_before = degree_before.get(node, 0)
        if deg_before == 0:
            growth += 1
            continue
        deg_change = sum(count for edge, count in contribution.items() if node in edge)
        before_odd = deg_before % 2 == 1
        after_odd = (deg_before + deg_change) % 2 == 1
        if before_odd and not after_odd:
            parity += 1
        elif not before_odd and after_odd:
            parity -= 1

    complexity_cost = len(motif) * EDGE_UNIT_COST + PLACEMENT_COST
    return EDGE_UNIT_COST * (growth + parity) - complexity_cost


def select_novel_placements(
    motif_library: list[Motif],
    dot_points: set[Point],
    max_multiplicity: int = DEFAULT_MAX_MULTIPLICITY,
    max_placements: int = DEFAULT_MAX_PLACEMENTS,
) -> list[MotifPlacement]:
    """Greedy placement of `motif_library`'s shapes onto `dot_points`,
    with NO source graph involved anywhere -- see module docstring.

    Every (motif, point, D4 transform) combination is a candidate.
    Scoring (_novel_score) rewards growing the structure into untouched
    dots and improving parity at already-touched ones -- moving the
    CANDIDATE toward a valid Eulerian structure is the only meaningful
    goal when there is no source recall to optimize for -- minus the
    same EDGE_UNIT_COST/PLACEMENT_COST complexity currency used
    everywhere else in this project. A candidate is rejected outright
    (never clipped) if it would push any touched edge's strand count
    above `max_multiplicity` -- the flat, source-independent
    multiplicity constraint this module uses instead of M3.6's per-edge
    source count.

    `max_placements` is a hard safety ceiling (there is no natural
    "fully covered" stopping condition on a new layout the way there is
    against a known source), not a target -- matches the same "ceiling,
    not target" convention engine.motifs.induce_motif_set_adaptive
    already established.
    """
    dots = set(dot_points)
    interior = interior_points(dots, radius=1)

    accumulated: Counter = Counter()
    degree: Counter = Counter()
    selected: dict[tuple[Motif, str], dict] = {}  # (motif, transform) -> {"points": [...], "edges": set}
    n_placed = 0

    # Fixed, deterministic candidate order (sorted points x library
    # motifs x D4 transforms) so results are reproducible across runs.
    candidate_keys = [
        (point, motif, transform)
        for point in sorted(interior)
        for motif in motif_library
        for transform in sorted(D4_TRANSFORMS)
    ]

    for point, motif, transform in candidate_keys:
        if n_placed >= max_placements:
            break
        contribution = _stamp_contribution(motif, point, transform, dots)
        if not contribution:
            continue
        if any(accumulated.get(e, 0) + c > max_multiplicity for e, c in contribution.items()):
            continue  # reject outright -- never clip, same discipline as M3.6

        score = _novel_score(motif, contribution, degree)
        # Unlike M3.6, there is no "recall against a known source" term
        # at all here -- growth + parity improvement net of complexity is the
        # WHOLE objective, since there is nothing else to optimize for
        # on a layout with no ground truth.
        if score <= 0:
            continue

        for edge, count in contribution.items():
            accumulated[edge] += count
            a, b = tuple(edge)
            degree[a] += count
            degree[b] += count
        key = (motif, transform)
        entry = selected.setdefault(key, {"points": [], "edges": set()})
        entry["points"].append(point)
        entry["edges"] |= set(contribution.keys())
        n_placed += 1

    placements = []
    for (motif, transform), entry in selected.items():
        transforms = {} if transform == "identity" else {p: transform for p in entry["points"]}
        placements.append(
            MotifPlacement(motif=motif, points=entry["points"], transforms=transforms, new_edges=entry["edges"])
        )
    return placements


def generate_novel_kolam(
    motif_library: list[Motif],
    dot_points: set[Point],
    max_multiplicity: int = DEFAULT_MAX_MULTIPLICITY,
) -> GeneratedKolam:
    """The full M3.7 pipeline: motif library + new dot layout ->
    select_novel_placements -> engine.generation.generate_kolam
    (unmodified). No source pattern is ever passed in or referenced --
    there is nothing for this to reconstruct FROM, only a rule set and a
    target lattice. See module docstring for why this is the strongest
    available guarantee of the source-reconstruction/novel-generation
    distinction."""
    placements = select_novel_placements(motif_library, dot_points, max_multiplicity)
    return generate_kolam(placements, dot_points)


def duplicates_source(candidate_graph, source: KolamPattern) -> bool | None:
    """Does `candidate_graph`'s edge multiset exactly reproduce `source`?
    Returns None (not a meaningful comparison) if the candidate's node
    set isn't even the same as source's dot layout -- a candidate on a
    genuinely different layout cannot be a "duplicate" in any literal
    sense, and reporting False there would misleadingly suggest a close
    call that was actually never possible."""
    if set(candidate_graph.nodes()) != source.dot_points:
        return None
    candidate_mult = Counter(frozenset(e) for e in candidate_graph.edges())
    source_mult = Counter(frozenset(e) for e in source.graph.edges())
    return candidate_mult == source_mult
