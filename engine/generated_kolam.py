"""GeneratedKolam: the candidate structure produced by structural
generation (engine/generation.py's generate_kolam).

WHY THIS IS A SEPARATE TYPE FROM KolamPattern, NOT A REUSE OF IT:
KolamPattern's fields (pattern_id, collection, raw_trace, trace_points)
all mean "this came from a specific row/column of a specific source
CSV." A generated candidate has no such provenance -- it wasn't read
from a file at any pattern_id. Populating those fields with fabricated
values (pattern_id=None, raw_trace=empty array, ...) would either break
KolamPattern's own invariants (raw_trace/trace_points must have matching
length -- see engine/kolam_pattern.py __post_init__) or silently claim a
generated candidate "is" source data when it isn't -- exactly what the
generation task instructions explicitly forbid ("Do not force the
candidate to pretend it came directly from a CSV file"). So this is a
distinct, smaller type that only claims what's actually true of a
generated candidate.

WHAT THIS DELIBERATELY DOES NOT CLAIM:
This object's validity_result/diagnosis come from engine.validity's
existing, unmodified hard gate -- STRUCTURAL validity (Eulerian
circuit/path on the largest component) is the only thing this object
asserts. It makes NO claim about visual plausibility (how the candidate
would look drawn) and NO claim about exact CSV trace reconstruction
(dot_trace is an ordered DOT-level traversal only -- see
docs/GENERATION.md "Trace reconstruction" for why half-integer
loop-around points are NOT reconstructed in this first version).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from engine.motifs import MotifPlacement

Point = tuple[int, int]


@dataclass
class GeneratedKolam:
    """One structural-generation candidate.

    dot_points        : the target dot lattice the candidate was built on
    graph             : nx.MultiGraph, nodes = dot_points, edges built by
                        stamping `placements` -- multiplicity preserved,
                        never collapsed (same MultiGraph requirement as
                        KolamPattern, see engine/generation.py)
    placements        : the MotifPlacement rules used to build this
                        candidate (the SAME type engine.motifs.
                        induce_motif_set/induce_motif_set_adaptive
                        return -- this is what "reuse the existing motif
                        representation" means here)
    edge_multiplicity : {frozenset({dot_a, dot_b}): count}, derived from
                        `graph` -- same convention as KolamPattern's field
                        of the same name
    validity_result   : engine.validity.check_validity(graph)'s dict --
                        the hard structural gate. Always populated by
                        generate_kolam (never left for the caller to
                        remember to check).
    diagnosis         : engine.validity.diagnose_validity(graph)'s dict --
                        WHY it's invalid (or confirmation it needs no
                        corrections), never a repair.
    dot_trace         : ordered dot-visit sequence from a deterministic
                        Eulerian traversal of graph's largest component,
                        or None if the candidate is not Eulerian (circuit
                        or path) -- generation does NOT silently repair
                        an invalid candidate to produce a fake trace.
    """

    dot_points: set[Point]
    graph: nx.MultiGraph
    placements: list[MotifPlacement]
    edge_multiplicity: dict[frozenset, int]
    validity_result: dict
    diagnosis: dict
    dot_trace: list[Point] | None = field(default=None)

    @property
    def is_valid(self) -> bool:
        return (
            self.validity_result["largest_component_covers_all_nodes"]
            and (self.validity_result["is_eulerian_circuit"] or self.validity_result["has_eulerian_path"])
        )

    @property
    def n_dots(self) -> int:
        return len(self.dot_points)

    @property
    def n_distinct_edges(self) -> int:
        return len(self.edge_multiplicity)

    @property
    def n_edge_instances(self) -> int:
        return self.graph.number_of_edges()

    def __repr__(self) -> str:
        return (
            f"GeneratedKolam(n_dots={self.n_dots}, n_distinct_edges={self.n_distinct_edges}, "
            f"n_edge_instances={self.n_edge_instances}, n_placements={len(self.placements)}, "
            f"is_valid={self.is_valid}, has_trace={self.dot_trace is not None})"
        )
