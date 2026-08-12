"""M3.5: real-data RECONSTRUCTION, kept deliberately separate from
generate_kolam() (motif-only structural generation, engine/generation.py)
and from any future novel-layout generation.

THE CORE DISTINCTION THIS MODULE EXISTS TO PRESERVE (see docs/RECONSTRUCTION.md):

  1. Motif explanation  -- how many source edges are explained by reusable
     motifs? (already answered by engine.motifs.induce_motif_set_adaptive's
     own recall bookkeeping; not re-litigated here)
  2. Reconstruction      -- can a source Kolam be reconstructed as ONE
     connected Eulerian structure? THIS is what reconstruct_kolam answers,
     by adding back the exact source edges no motif explained.
  3. Novel generation    -- can motifs produce a valid structure on a NEW
     dot layout without copying source-specific residual edges? NOT
     implemented here (see docs/RECONSTRUCTION.md "Novel generation" --
     explicitly future work, out of scope for M3.5).

reconstruct_kolam() is NOT novel generation: it deliberately copies
source-specific residual edges verbatim. It exists to answer one narrow
question -- is the motif/residual DECOMPOSITION of a real pattern itself
consistent, i.e. does motif-edges + residual-edges reproduce something
structurally valid? -- not to produce new patterns.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import networkx as nx

from engine.generation import build_candidate_graph, generate_kolam
from engine.kolam_pattern import KolamPattern
from engine.motifs import MotifPlacement
from engine.validity import check_validity, diagnose_validity, is_valid_single_stroke

Point = tuple[int, int]
EdgeKey = frozenset  # frozenset({dot_a, dot_b})

SUPPORTED_RESIDUAL_POLICIES = ("exact",)


@dataclass
class ReconstructionResult:
    """Result of reconstruct_kolam(): motif placements + the EXACT
    residual edges needed to reproduce `source`, as one candidate graph.

    Does not fabricate source provenance: `source` is the real
    KolamPattern this was reconstructed FROM (a reference, not a copy
    pretending to be independent data), and `residual_edges` are copied
    verbatim from `source.graph`, not invented.

    motif_edges     : distinct dot-pairs explained by >=1 placement
                       (frozenset({a, b}) per pair)
    residual_edges  : distinct dot-pairs where `source` has MORE strands
                       than the motif-only candidate produced -- i.e. what
                       had to be copied back from source to make up the
                       deficit. NOT "noise" -- see docs/RECONSTRUCTION.md
                       "Do not call residuals noise".
    candidate_graph  : motif-only graph + residual strands added back,
                       full multiplicity, nodes = source.dot_points
    edge_multiplicity: {frozenset({a,b}): count} for candidate_graph,
                       same convention as KolamPattern/GeneratedKolam
    connectivity     : {"connected_components": int,
                        "largest_component_covers_all_nodes": bool}
    validity_result  : engine.validity.check_validity(candidate_graph)
    diagnosis        : engine.validity.diagnose_validity(candidate_graph)
    """

    source: KolamPattern
    placements: list[MotifPlacement]
    residual_policy: str

    motif_edges: set
    residual_edges: set
    candidate_graph: nx.MultiGraph
    edge_multiplicity: dict

    connectivity: dict
    validity_result: dict
    diagnosis: dict

    @property
    def is_valid(self) -> bool:
        return (
            self.validity_result["largest_component_covers_all_nodes"]
            and (self.validity_result["is_eulerian_circuit"] or self.validity_result["has_eulerian_path"])
        )

    def compare_to_source(self) -> dict:
        """Source graph vs. reconstructed candidate, on exactly the axes
        Task 2 asks for: unique edges, total edge strands, edge
        multiplicity, connected components, Eulerian validity."""
        source_graph = self.source.graph
        source_multiplicity = dict(Counter(frozenset(e) for e in source_graph.edges()))
        source_validity = check_validity(source_graph)

        return {
            "source_unique_edges": len(source_multiplicity),
            "candidate_unique_edges": len(self.edge_multiplicity),
            "source_total_strands": source_graph.number_of_edges(),
            "candidate_total_strands": self.candidate_graph.number_of_edges(),
            "multiplicity_exact_match": source_multiplicity == self.edge_multiplicity,
            "source_connected_components": source_validity["connected_components"],
            "candidate_connected_components": self.connectivity["connected_components"],
            "source_valid": is_valid_single_stroke(source_graph),
            "candidate_valid": self.is_valid,
        }

    def __repr__(self) -> str:
        return (
            f"ReconstructionResult(source={self.source.collection}#{self.source.pattern_id}, "
            f"motif_edges={len(self.motif_edges)}, residual_edges={len(self.residual_edges)}, "
            f"is_valid={self.is_valid})"
        )


def reconstruct_kolam(
    source: KolamPattern,
    placements: list[MotifPlacement],
    residual_policy: str = "exact",
) -> ReconstructionResult:
    """TASK 1/2: motif placements + EXACT residual source edges -> one
    candidate graph, reconstructing `source`'s own dot layout.

    This is NOT novel generation (see module docstring) -- dot_points is
    always source.dot_points, and residual edges are copied verbatim
    from source.graph, never invented. The only baseline implemented so
    far is residual_policy="exact": for every dot pair where source has
    more parallel strands than the motif-only candidate produced, copy
    the DEFICIT strands back from source exactly. Other residual
    strategies (e.g. an approximate/synthetic residual) are future work,
    not implemented -- passing anything else raises.

    Never mutates `source` or `placements` -- see
    tests/test_reconstruction.py's mutation tests.
    """
    if residual_policy not in SUPPORTED_RESIDUAL_POLICIES:
        raise ValueError(
            f"unsupported residual_policy {residual_policy!r}; "
            f"only {SUPPORTED_RESIDUAL_POLICIES} is implemented in this baseline"
        )

    dot_points = set(source.dot_points)
    motif_graph = build_candidate_graph(placements, dot_points)

    source_counts = Counter(frozenset(e) for e in source.graph.edges())
    motif_counts = Counter(frozenset(e) for e in motif_graph.edges())

    motif_edges = {pair for pair, count in motif_counts.items() if count > 0}

    residual_counts: Counter = Counter()
    for pair, source_count in source_counts.items():
        deficit = source_count - motif_counts.get(pair, 0)
        if deficit > 0:
            residual_counts[pair] = deficit
    residual_edges = set(residual_counts.keys())

    candidate_graph = nx.MultiGraph()
    candidate_graph.add_nodes_from(dot_points)
    for a, b in motif_graph.edges():
        candidate_graph.add_edge(a, b)
    for pair, count in residual_counts.items():
        a, b = tuple(pair) if len(pair) == 2 else (next(iter(pair)),) * 2
        for _ in range(count):
            candidate_graph.add_edge(a, b)

    edge_multiplicity = dict(Counter(frozenset(e) for e in candidate_graph.edges()))
    validity_result = check_validity(candidate_graph)
    diagnosis = diagnose_validity(candidate_graph)
    connectivity = {
        "connected_components": validity_result["connected_components"],
        "largest_component_covers_all_nodes": validity_result["largest_component_covers_all_nodes"],
    }

    return ReconstructionResult(
        source=source,
        placements=list(placements),
        residual_policy=residual_policy,
        motif_edges=motif_edges,
        residual_edges=residual_edges,
        candidate_graph=candidate_graph,
        edge_multiplicity=edge_multiplicity,
        connectivity=connectivity,
        validity_result=validity_result,
        diagnosis=diagnosis,
    )


def motif_only_report(source: KolamPattern, placements: list[MotifPlacement]) -> dict:
    """TASK 3: the motif-only baseline, for honest contrast against
    reconstruct_kolam(). Reuses engine.generation.generate_kolam()
    UNCHANGED -- no residual edges added, exactly its existing behavior --
    and adds the edge-recall measurement against `source` that
    generate_kolam itself has no reason to know about (it doesn't take a
    source pattern as input at all)."""
    candidate = generate_kolam(placements, source.dot_points)

    source_distinct = {frozenset(e) for e in source.graph.edges()}
    motif_distinct = {frozenset(e) for e in candidate.graph.edges()}
    edge_recall = len(motif_distinct & source_distinct) / len(source_distinct) if source_distinct else 1.0

    return {
        "candidate": candidate,
        "connected_components": candidate.validity_result["connected_components"],
        "is_valid": candidate.is_valid,
        "edge_recall": edge_recall,
        "motif_count": len(placements),
    }
