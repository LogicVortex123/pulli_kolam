"""M3.6 Task 5: compare three motif-selection modes on the same six real
patterns used throughout M3.5:

  A. existing motif induction   -- engine.motifs.induce_motif_set_adaptive
                                    (unmodified, MDL-gated, no multiplicity
                                    tracking -- can over-explain)
  B. multiplicity-aware         -- engine.motif_selection.
                                    induce_motif_set_multiplicity_aware
                                    (structurally guaranteed no
                                    over-explanation)
  C. multiplicity + Eulerian    -- engine.motif_selection.
                                    induce_motif_set_eulerian_aware
                                    (same guarantee, plus scoring that
                                    rewards moving vertices toward even
                                    degree)

All metrics are computed on the MOTIF-ONLY candidate graph (no residual
added back) for every mode -- this is the meaningful comparison. Adding
residual on top of B/C trivially reaches full validity by construction
(see docs/RECONSTRUCTION.md's over-explanation finding: a multiplicity-
respecting motif set plus its own exact residual always reconstructs
source's edge multiset exactly, which is always valid since source
itself always is) -- that fact is reported once, not re-measured per
pattern as if it were a meaningful per-pattern result.

Radius policy matches validate_reconstruction.py's established
precedent: max_radius=3 for kolam19/kolam29 (fast), max_radius=1 for
kolam109 (the existing diagnose_validity O(k^2) scalability finding from
the M3.5 session applies to a DIFFERENT function, not this script, but
kolam109's sheer candidate-pool size still makes higher radii slow --
measured, not assumed, at ~20s for max_radius=2 on kolam109#1). The SAME
radius policy is applied to all three modes for a given pattern, so the
comparison stays apples-to-apples per pattern.
"""

from __future__ import annotations

import time
from collections import Counter

from engine.dataset import load_kolam
from engine.generation import build_candidate_graph
from engine.motif_selection import induce_motif_set_eulerian_aware, induce_motif_set_multiplicity_aware
from engine.motifs import compression_ratio, induce_motif_set_adaptive
from engine.validity import check_validity

REQUESTED = [
    ("kolam19", 1), ("kolam19", 26),
    ("kolam29", 1), ("kolam29", 26),
    ("kolam109", 1), ("kolam109", 26),
]


def _radius_for(collection: str) -> int:
    return 1 if collection == "kolam109" else 3


def _metrics(source_graph, source_mult: Counter, placements, residual_edges, motif_count: int, elapsed: float) -> dict:
    candidate = build_candidate_graph(placements, set(source_graph.nodes()))
    candidate_mult = Counter(frozenset(e) for e in candidate.edges())

    source_distinct = set(source_mult.keys())
    covered_distinct = {e for e, c in candidate_mult.items() if c > 0}
    over_explained = {e for e, c in candidate_mult.items() if c > source_mult.get(e, 0)}
    agreeing = {e for e in source_distinct if candidate_mult.get(e, 0) == source_mult[e]}

    validity = check_validity(candidate)
    is_valid = validity["largest_component_covers_all_nodes"] and (
        validity["is_eulerian_circuit"] or validity["has_eulerian_path"]
    )
    odd_count = sum(1 for _n, d in candidate.degree() if d % 2 == 1)
    ratio = compression_ratio(source_graph, placements, residual_edges)

    return {
        "motif_count": motif_count,
        "unique_source_edges": len(source_distinct),
        "covered_edges": len(covered_distinct),
        "edge_recall": round(len(covered_distinct) / len(source_distinct), 4) if source_distinct else 1.0,
        "over_explained_edges": len(over_explained),
        "multiplicity_agreement": round(len(agreeing) / len(source_distinct), 4) if source_distinct else 1.0,
        "connected_components": validity["connected_components"],
        "odd_degree_count": odd_count,
        "is_valid": is_valid,
        "compression_ratio": round(ratio, 4),
        "runtime_sec": round(elapsed, 3),
    }


def run_pattern(collection: str, pattern_id: int) -> dict:
    pattern = load_kolam(collection, pattern_id)
    source_mult = Counter(frozenset(e) for e in pattern.graph.edges())
    r = _radius_for(collection)

    t0 = time.time()
    placements_a, residual_a, _full_a = induce_motif_set_adaptive(pattern, max_radius=r)
    time_a = time.time() - t0
    metrics_a = _metrics(pattern.graph, source_mult, placements_a, residual_a, len(placements_a), time_a)

    t0 = time.time()
    result_b = induce_motif_set_multiplicity_aware(pattern, radius=1, max_radius=r)
    time_b = time.time() - t0
    metrics_b = _metrics(
        pattern.graph, source_mult, result_b.placements, result_b.residual_edges, len(result_b.placements), time_b
    )

    t0 = time.time()
    result_c = induce_motif_set_eulerian_aware(pattern, radius=1, max_radius=r)
    time_c = time.time() - t0
    metrics_c = _metrics(
        pattern.graph, source_mult, result_c.placements, result_c.residual_edges, len(result_c.placements), time_c
    )

    return {
        "source": f"{collection}#{pattern_id}",
        "radius": r,
        "A": metrics_a,
        "B": metrics_b,
        "C": metrics_c,
    }


def _print_mode_row(label: str, m: dict):
    print(
        f"  {label:>1} | motifs={m['motif_count']:>4} recall={m['edge_recall']:>7} "
        f"over_expl={m['over_explained_edges']:>4} mult_agree={m['multiplicity_agreement']:>7} "
        f"components={m['connected_components']:>5} odd={m['odd_degree_count']:>5} "
        f"valid={str(m['is_valid']):>5} compress={m['compression_ratio']:>7} "
        f"time={m['runtime_sec']:>7}s"
    )


def main():
    rows = []
    for collection, pattern_id in REQUESTED:
        r = run_pattern(collection, pattern_id)
        rows.append(r)
        print(f"=== {r['source']} (radius policy: max_radius={r['radius']}, unique_source_edges="
              f"{r['A']['unique_source_edges']}) ===")
        _print_mode_row("A", r["A"])
        _print_mode_row("B", r["B"])
        _print_mode_row("C", r["C"])
        print()

    print("=== summary across all 6 patterns ===")
    for mode in ("A", "B", "C"):
        n = len(rows)
        avg_recall = sum(r[mode]["edge_recall"] for r in rows) / n
        avg_over = sum(r[mode]["over_explained_edges"] for r in rows) / n
        avg_agree = sum(r[mode]["multiplicity_agreement"] for r in rows) / n
        avg_odd = sum(r[mode]["odd_degree_count"] for r in rows) / n
        n_valid = sum(r[mode]["is_valid"] for r in rows)
        avg_compress = sum(r[mode]["compression_ratio"] for r in rows) / n
        total_time = sum(r[mode]["runtime_sec"] for r in rows)
        print(f"mode {mode}: avg_recall={avg_recall:.4f} avg_over_explained={avg_over:.1f} "
              f"avg_mult_agreement={avg_agree:.4f} avg_odd_degree={avg_odd:.1f} "
              f"valid={n_valid}/{n} avg_compression={avg_compress:.4f} total_time={total_time:.2f}s")


if __name__ == "__main__":
    main()
