"""M3.5 Task 5: real-data reconstruction experiment.

For each pattern: motif count, motif edge recall, residual edge count,
motif-only components/validity, motif+residual components/validity, and
edge agreement (does motif+residual recover every distinct source edge).

SCALABILITY NOTE (discovered running this script, not theorized): the
full engine.reconstruction.reconstruct_kolam / engine.generation.
generate_kolam pipelines unconditionally call
engine.validity.diagnose_validity, whose odd-degree-vertex matching is
O(k^2) shortest-path computations for k odd-degree nodes. On kolam19/29
(k in the tens) this is instant. On kolam109 (k ~1500+ at radius=1
induction -- measured directly, not estimated) this is computationally
infeasible: a first attempt was killed after 10+ minutes of CPU time
with no result (see session report). This script therefore computes the
SAME Task-5-required fields (source, motif count, motif edge recall,
residual edge count, motif-only/motif+residual components and validity,
edge agreement) via the real engine functions
(induce_motif_set_adaptive, build_candidate_graph, check_validity) MINUS
the expensive diagnose_validity call, uniformly for all 6 patterns --
this is not a different algorithm, just skipping one optional diagnostic
field this script doesn't need. The full ReconstructionResult (with
diagnosis) is still exercised and tested on kolam19-scale data
elsewhere (tests/test_reconstruction.py, and the earlier kolam19 #26
example in the session report, which DID complete via the full
pipeline).
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from engine.dataset import load_kolam
from engine.generation import build_candidate_graph
from engine.motifs import induce_motif_set_adaptive
from engine.validity import check_validity

REQUESTED = [
    ("kolam19", 1), ("kolam19", 26),
    ("kolam29", 1), ("kolam29", 26),
    ("kolam109", 1), ("kolam109", 26),
]


def run_one(collection: str, pattern_id: int) -> dict:
    pattern = load_kolam(collection, pattern_id)
    placements, _residual, _fully_covered = induce_motif_set_adaptive(pattern, max_radius=1)

    dot_points = set(pattern.dot_points)
    motif_graph = build_candidate_graph(placements, dot_points)

    source_counts = Counter(frozenset(e) for e in pattern.graph.edges())
    motif_counts = Counter(frozenset(e) for e in motif_graph.edges())
    source_distinct = set(source_counts.keys())
    motif_distinct = {p for p, c in motif_counts.items() if c > 0}

    motif_only_validity = check_validity(motif_graph)
    edge_recall = len(motif_distinct & source_distinct) / len(source_distinct) if source_distinct else 1.0

    residual_counts: Counter = Counter()
    for pair, s_count in source_counts.items():
        deficit = s_count - motif_counts.get(pair, 0)
        if deficit > 0:
            residual_counts[pair] = deficit

    candidate = nx.MultiGraph()
    candidate.add_nodes_from(dot_points)
    for a, b in motif_graph.edges():
        candidate.add_edge(a, b)
    for pair, count in residual_counts.items():
        a, b = tuple(pair)
        for _ in range(count):
            candidate.add_edge(a, b)

    candidate_validity = check_validity(candidate)
    candidate_counts = dict(Counter(frozenset(e) for e in candidate.edges()))
    edge_agreement = len(source_distinct & {frozenset(e) for e in candidate.edges()}) / len(source_distinct)

    def is_valid(v):
        return v["largest_component_covers_all_nodes"] and (v["is_eulerian_circuit"] or v["has_eulerian_path"])

    return {
        "source": f"{collection}#{pattern_id}",
        "n_dots": pattern.n_dots,
        "n_source_distinct_edges": pattern.n_distinct_edges,
        "motif_count": len(placements),
        "motif_edge_recall": round(edge_recall, 4),
        "residual_edge_count": len(residual_counts),
        "motif_only_components": motif_only_validity["connected_components"],
        "motif_only_valid": is_valid(motif_only_validity),
        "motif_residual_components": candidate_validity["connected_components"],
        "motif_residual_valid": is_valid(candidate_validity),
        "edge_agreement": round(edge_agreement, 4),
        "multiplicity_exact_match": candidate_counts == dict(source_counts),
        "source_total_strands": pattern.graph.number_of_edges(),
        "candidate_total_strands": candidate.number_of_edges(),
        "motif_only_odd_nodes": sum(1 for _n, d in motif_graph.degree() if d % 2 == 1),
        "candidate_odd_nodes": sum(1 for _n, d in candidate.degree() if d % 2 == 1),
    }


def main():
    print(f"{'source':>12} {'dots':>6} {'src_edges':>9} {'motifs':>7} {'recall':>7} "
          f"{'residual':>9} {'mo_comp':>8} {'mo_valid':>9} {'mr_comp':>8} {'mr_valid':>9} "
          f"{'agree':>7} {'mult_exact':>11} {'strands src->cand':>18} {'odd mo->mr':>12}")
    rows = []
    for collection, pattern_id in REQUESTED:
        r = run_one(collection, pattern_id)
        rows.append(r)
        print(f"{r['source']:>12} {r['n_dots']:>6} {r['n_source_distinct_edges']:>9} "
              f"{r['motif_count']:>7} {r['motif_edge_recall']:>7} {r['residual_edge_count']:>9} "
              f"{r['motif_only_components']:>8} {str(r['motif_only_valid']):>9} "
              f"{r['motif_residual_components']:>8} {str(r['motif_residual_valid']):>9} "
              f"{r['edge_agreement']:>7} {str(r['multiplicity_exact_match']):>11} "
              f"{r['source_total_strands']:>6} -> {r['candidate_total_strands']:<6} "
              f"{r['motif_only_odd_nodes']:>5} -> {r['candidate_odd_nodes']:<5}")

    n = len(rows)
    print()
    print(f"n patterns: {n}")
    print(f"motif-only valid: {sum(r['motif_only_valid'] for r in rows)}/{n}")
    print(f"motif+residual valid: {sum(r['motif_residual_valid'] for r in rows)}/{n}")
    print(f"motif+residual edge agreement == 1.0 (all distinct source edges present): "
          f"{sum(r['edge_agreement'] == 1.0 for r in rows)}/{n}")
    print(f"motif+residual multiplicity exact match: "
          f"{sum(r['multiplicity_exact_match'] for r in rows)}/{n}")


if __name__ == "__main__":
    main()
