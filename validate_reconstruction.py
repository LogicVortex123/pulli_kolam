"""M3.5 Task 5: real-data reconstruction experiment.

For each pattern: motif count, motif edge recall, residual edge count,
motif-only components/validity, motif+residual components/validity, and
edge agreement (does motif+residual recover every distinct source edge).

kolam109 patterns are large (~7-13k dots) -- induction is run at
max_radius=1 only here (this is a reconstruction-baseline check, not a
re-run of the MDL-gated recall experiments already on record; keeping it
fast and honest is more useful here than maximizing recall).
"""

from __future__ import annotations

from engine.dataset import load_kolam
from engine.motifs import induce_motif_set_adaptive
from engine.reconstruction import motif_only_report, reconstruct_kolam

REQUESTED = [
    ("kolam19", 1), ("kolam19", 26),
    ("kolam29", 1), ("kolam29", 26),
    ("kolam109", 1), ("kolam109", 26),
]


def run_one(collection: str, pattern_id: int) -> dict:
    pattern = load_kolam(collection, pattern_id)
    placements, residual, _fully_covered = induce_motif_set_adaptive(pattern, max_radius=1)

    mo = motif_only_report(pattern, placements)
    rec = reconstruct_kolam(pattern, placements)
    cmp = rec.compare_to_source()

    source_distinct = {frozenset(e) for e in pattern.graph.edges()}
    edge_agreement = len(source_distinct & {frozenset(e) for e in rec.candidate_graph.edges()}) / len(
        source_distinct
    )

    return {
        "source": f"{collection}#{pattern_id}",
        "n_dots": pattern.n_dots,
        "n_source_distinct_edges": pattern.n_distinct_edges,
        "motif_count": len(placements),
        "motif_edge_recall": round(mo["edge_recall"], 4),
        "residual_edge_count": len(rec.residual_edges),
        "motif_only_components": mo["connected_components"],
        "motif_only_valid": mo["is_valid"],
        "motif_residual_components": rec.connectivity["connected_components"],
        "motif_residual_valid": rec.is_valid,
        "edge_agreement": round(edge_agreement, 4),
        "multiplicity_exact_match": cmp["multiplicity_exact_match"],
        "source_total_strands": cmp["source_total_strands"],
        "candidate_total_strands": cmp["candidate_total_strands"],
    }


def main():
    print(f"{'source':>12} {'dots':>6} {'src_edges':>9} {'motifs':>7} {'recall':>7} "
          f"{'residual':>9} {'mo_comp':>8} {'mo_valid':>9} {'mr_comp':>8} {'mr_valid':>9} "
          f"{'agree':>7} {'mult_exact':>11} {'strands src->cand':>18}")
    rows = []
    for collection, pattern_id in REQUESTED:
        r = run_one(collection, pattern_id)
        rows.append(r)
        print(f"{r['source']:>12} {r['n_dots']:>6} {r['n_source_distinct_edges']:>9} "
              f"{r['motif_count']:>7} {r['motif_edge_recall']:>7} {r['residual_edge_count']:>9} "
              f"{r['motif_only_components']:>8} {str(r['motif_only_valid']):>9} "
              f"{r['motif_residual_components']:>8} {str(r['motif_residual_valid']):>9} "
              f"{r['edge_agreement']:>7} {str(r['multiplicity_exact_match']):>11} "
              f"{r['source_total_strands']:>6} -> {r['candidate_total_strands']:<6}")

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
