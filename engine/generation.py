"""Regenerate a graph by stamping a motif at a set of points, and (new)
the first structural generation pipeline: motif rules -> candidate graph
-> validity check -> trace reconstruction -> GeneratedKolam candidate.

apply_motif (below) is the pre-existing, unmodified stamping primitive --
used both for self-consistency verification (stamp the induced motif
back onto the same dot set and diff against the original) and now as the
building block generate_kolam uses for actual generation.

STRUCTURAL GENERATION, NOT ML: generate_kolam builds a candidate graph
deterministically from a list of MotifPlacement rules (the exact type
engine.motifs.induce_motif_set/induce_motif_set_adaptive already
produce -- see "reuse the existing motif representation" in
docs/GENERATION.md), runs it through the SAME hard validity gate CSV
data is checked with (engine.validity.check_validity, unmodified), and
-- only if valid -- deterministically traverses it into an ordered dot
trace using networkx's own Eulerian-circuit/path algorithms. No image is
generated or inspected at any point; "valid" means exactly what it means
for CSV-sourced data: the largest connected component is Eulerian.
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from engine.generated_kolam import GeneratedKolam
from engine.motifs import Motif, MotifPlacement
from engine.symmetry import apply_transform
from engine.validity import check_validity, diagnose_validity

Point = tuple[int, int]


def apply_motif(
    motif: Motif,
    nodes: "set[tuple[int, int]] | list[tuple[int, int]]",
    points: "list[tuple[int, int]] | set[tuple[int, int]]",
    transforms: "dict[tuple[int, int], str] | None" = None,
) -> nx.MultiGraph:
    """Regenerate a MultiGraph by translating (and optionally rotating /
    reflecting, per `transforms`) `motif` onto every point in `points`.

    `nodes` is the full node set of the target lattice (arbitrary shape,
    not necessarily a square grid) -- edges landing outside it are dropped.
    `transforms` maps a subset of `points` to a D4 transform name (see
    engine.symmetry.D4_TRANSFORMS); points absent from it are stamped with
    a plain translation (identity transform).
    """
    G = nx.MultiGraph()
    node_set = set(nodes)
    G.add_nodes_from(node_set)

    for cx, cy in points:
        t_name = transforms.get((cx, cy), "identity") if transforms else "identity"
        edges = motif if t_name == "identity" else apply_transform(t_name, motif)
        for (dx1, dy1), (dx2, dy2) in edges:
            a = (cx + dx1, cy + dy1)
            b = (cx + dx2, cy + dy2)
            if a in node_set and b in node_set:
                G.add_edge(a, b)
    return G


def build_candidate_graph(
    placements: "list[MotifPlacement]",
    dot_points: "set[Point]",
) -> nx.MultiGraph:
    """Stage 1: motif rules -> candidate graph.

    Each placement is stamped independently via apply_motif and its
    edges are added ONE AT A TIME into a single accumulator graph via
    `add_edge` (never `compose`, never a fresh-graph merge) -- MultiGraph
    auto-assigns a fresh parallel-edge key on every `add_edge` call, so
    this can never silently overwrite an edge a previous placement
    already added, and multiplicity accumulates correctly across
    DIFFERENT placements targeting the same dot pair, exactly like it
    does within a single placement.

    Defensively copies `dot_points` and never touches `placements`'
    contents -- the source motifs and dot layout are read-only inputs.
    """
    dot_points = set(dot_points)  # never mutate the caller's set
    G = nx.MultiGraph()
    G.add_nodes_from(dot_points)

    for placement in placements:
        stamped = apply_motif(placement.motif, dot_points, placement.points, placement.transforms)
        for a, b in stamped.edges():
            G.add_edge(a, b)

    return G


def reconstruct_dot_trace(G: nx.MultiGraph) -> "list[Point] | None":
    """Stage 3: deterministic graph -> ordered dot-visit trace.

    Traverses G's LARGEST connected component (matching
    engine.validity.check_validity's own convention) using networkx's own
    Eulerian-circuit/path algorithms -- not a reimplementation of
    Hierholzer's algorithm, reusing a tested standard graph algorithm the
    same way this project already reuses nx.min_weight_matching for
    diagnose_validity. A fixed, sorted `source` node is chosen so the
    traversal is reproducible across calls on the same graph.

    Returns None if the largest component is not itself Eulerian (circuit
    or path) -- this function does NOT repair or approximate; that
    determination belongs to engine.validity.check_validity, not here.

    IMPORTANT (see docs/GENERATION.md "Trace reconstruction"): this
    returns a DOT-level trace only. It does NOT reconstruct the
    half-integer loop-around points the source CSV format uses (see
    docs/DATA_FORMAT.md) -- which side of a skipped dot the curve arcs
    around is a drawing decision the graph topology alone does not
    determine (the same dot pair can be double-stranded with one strand
    on each side, see DATA_FORMAT.md's concrete example), so inventing a
    specific side would not be justified by the established rules.
    Reconstructing loop-around geometry is explicitly left as separate
    future work, not attempted here.
    """
    if G.number_of_nodes() == 0:
        return []

    largest = max(nx.connected_components(G), key=len)
    Gc = G.subgraph(largest).copy()  # copy: traversal should not risk touching the caller's graph

    odd_nodes = sorted(n for n, d in Gc.degree() if d % 2 == 1)

    if len(odd_nodes) == 0 and nx.is_eulerian(Gc):
        source = min(Gc.nodes())
        edge_sequence = list(nx.eulerian_circuit(Gc, source=source))
    elif len(odd_nodes) == 2 and nx.has_eulerian_path(Gc):
        source = odd_nodes[0]
        edge_sequence = list(nx.eulerian_path(Gc, source=source))
    else:
        return None

    trace = [edge_sequence[0][0]]
    trace.extend(v for _u, v in edge_sequence)
    return trace


def generate_kolam(
    placements: "list[MotifPlacement]",
    dot_points: "set[Point]",
) -> GeneratedKolam:
    """The full structural generation pipeline: motif rules -> candidate
    graph -> validity check -> trace reconstruction -> GeneratedKolam.

    `placements` are MotifPlacement objects -- the SAME type
    engine.motifs.induce_motif_set/induce_motif_set_adaptive return, so
    motifs discovered from real data can be fed straight back in (see
    docs/GENERATION.md "First real-data experiment"), or constructed by
    hand for a controlled synthetic case.

    check_validity runs unconditionally and its result is always
    populated on the returned object -- a candidate is never reported as
    a plain graph without its validity having been checked. If invalid,
    dot_trace stays None (no silent repair) and `diagnosis` (from
    engine.validity.diagnose_validity) explains exactly which vertices
    and edge-corrections would be needed, without applying them.
    """
    graph = build_candidate_graph(placements, dot_points)

    validity_result = check_validity(graph)
    diagnosis = diagnose_validity(graph)

    is_valid = (
        validity_result["largest_component_covers_all_nodes"]
        and (validity_result["is_eulerian_circuit"] or validity_result["has_eulerian_path"])
    )
    dot_trace = reconstruct_dot_trace(graph) if is_valid else None

    # same convention as KolamPattern.edge_multiplicity (engine/dataset.py)
    edge_multiplicity = dict(Counter(frozenset(e) for e in graph.edges()))

    return GeneratedKolam(
        dot_points=set(dot_points),
        graph=graph,
        placements=list(placements),
        edge_multiplicity=edge_multiplicity,
        validity_result=validity_result,
        diagnosis=diagnosis,
        dot_trace=dot_trace,
    )
