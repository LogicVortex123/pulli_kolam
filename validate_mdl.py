"""Run MDL-GATED motif induction (induce_motif_set_adaptive with cost-
benefit gating, no motif-count cap) across the same 15 real patterns used
by validate_real_data.py and validate_adaptive.py, and compare directly
against BOTH prior results already on record:

  radius=1 only (20-motif count cap):     avg recall 0.8971, avg motifs 10.47,
                                           avg compression 1.8202
  uncapped-recall adaptive (20/tier cap): avg recall 0.9949, avg motifs 28.87,
                                           avg compression 1.6432 -- WORSE
                                           compression than radius=1-only on
                                           15/15 patterns, verified per-pattern

This run replaces "add motifs until count cap or full coverage" with "add
a motif only if it shortens the total description (mdl_gain > 0), stop
the moment none do." See engine.motifs.mdl_gain and the rewritten
induce_motif_set_adaptive docstring for the exact accounting.
"""

from __future__ import annotations

import sys
import time
from collections import Counter

from engine import graph_io, motifs, validity

DATASET_FILES = [
    "kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv",
    "kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv",
    "kolam_data/Kolam CSV files/Kolam CSV files/kolam109.csv",
]
KOLAM_NUMBERS_PER_FILE = [1, 2, 3, 4, 5]
MAX_RADIUS = 3
SAFETY_CEILING = 2000  # far above where MDL gating should ever naturally stop

# Prior results already measured this session, reproduced only for the
# printed side-by-side comparison -- not recomputed here, not invented.
BASELINE_R1_AVG = {"recall": 0.8971, "motifs": 10.47, "compression": 1.8202}
BASELINE_ADAPTIVE_UNCAPPED_AVG = {"recall": 0.9949, "motifs": 28.87, "compression": 1.6432}
BASELINE_R1_PER_PATTERN_COMPRESSION = {
    ("kolam19.csv", 1): 1.4074, ("kolam19.csv", 2): 1.6757, ("kolam19.csv", 3): 1.5362,
    ("kolam19.csv", 4): 1.8289, ("kolam19.csv", 5): 1.6907,
    ("kolam29.csv", 1): 1.8529, ("kolam29.csv", 2): 1.7083, ("kolam29.csv", 3): 1.7475,
    ("kolam29.csv", 4): 2.1802, ("kolam29.csv", 5): 1.7302,
    ("kolam109.csv", 1): 2.0378, ("kolam109.csv", 2): 1.9649, ("kolam109.csv", 3): 1.9828,
    ("kolam109.csv", 4): 1.9099, ("kolam109.csv", 5): 2.0494,
}
BASELINE_R1_PER_PATTERN_RECALL = {
    ("kolam19.csv", 1): 0.8772, ("kolam19.csv", 2): 0.8871, ("kolam19.csv", 3): 0.8961,
    ("kolam19.csv", 4): 0.9161, ("kolam19.csv", 5): 0.8943,
    ("kolam29.csv", 1): 0.9294, ("kolam29.csv", 2): 0.9024, ("kolam29.csv", 3): 0.8636,
    ("kolam29.csv", 4): 0.9146, ("kolam29.csv", 5): 0.8475,
    ("kolam109.csv", 1): 0.9142, ("kolam109.csv", 2): 0.9044, ("kolam109.csv", 3): 0.9075,
    ("kolam109.csv", 4): 0.8901, ("kolam109.csv", 5): 0.9113,
}


def analyze(csv_path: str, kolam_number: int) -> dict:
    G = graph_io.load_kolam(csv_path, kolam_number)
    dots = graph_io.dots_set(G)

    v_ok = validity.is_valid_single_stroke(G)

    interior_r1 = motifs.interior_points(dots, radius=1)
    total_edges = {frozenset(e) for e in G.edges()}
    n_total = len(total_edges)

    placements, residual, fully_covered = motifs.induce_motif_set_adaptive(
        G, interior_r1, dots, max_radius=MAX_RADIUS, max_motifs_per_radius=SAFETY_CEILING
    )

    covered = n_total - len(residual)
    final_recall = covered / n_total if n_total else 1.0
    ratio = motifs.compression_ratio(G, placements, residual)
    by_radius = Counter(p.radius for p in placements)

    return {
        "n_dots": G.number_of_nodes(),
        "n_edges": n_total,
        "valid": v_ok,
        "n_motifs": len(placements),
        "motifs_by_radius": dict(by_radius),
        "recall": round(final_recall, 4),
        "fully_covered": fully_covered,
        "n_residual": len(residual),
        "compression_ratio": round(ratio, 4),
    }


def main():
    print(f"MDL-gated induction: add a motif only if mdl_gain > 0, stop when none do "
          f"(safety ceiling {SAFETY_CEILING}, should never trigger)")
    header = (
        f"{'file':>10} {'kolam':>6} {'edges':>6} {'valid':>6} {'n_motifs':>9} "
        f"{'by_radius':>18} {'recall':>8} {'full_cov':>9} {'residual':>9} "
        f"{'compress':>9} {'vs_r1':>8} {'sec':>7}"
    )
    print(header)
    rows = []
    for path in DATASET_FILES:
        fname = path.split("/")[-1]
        for k in KOLAM_NUMBERS_PER_FILE:
            t0 = time.time()
            r = analyze(path, k)
            elapsed = time.time() - t0
            r["file"] = fname
            r["kolam"] = k
            r["elapsed"] = elapsed
            rows.append(r)
            by_radius_str = ",".join(f"r{k_}:{v_}" for k_, v_ in sorted(r["motifs_by_radius"].items()))
            baseline_compress = BASELINE_R1_PER_PATTERN_COMPRESSION[(fname, k)]
            delta = r["compression_ratio"] - baseline_compress
            vs_r1 = f"{delta:+.3f}"
            print(
                f"{fname:>10} {k:>6} {r['n_edges']:>6} {str(r['valid']):>6} "
                f"{r['n_motifs']:>9} {by_radius_str:>18} {r['recall']:>8} "
                f"{str(r['fully_covered']):>9} {r['n_residual']:>9} "
                f"{r['compression_ratio']:>9} {vs_r1:>8} {elapsed:>7.2f}"
            )

    n = len(rows)
    pct_valid = 100 * sum(r["valid"] for r in rows) / n
    avg_motifs = sum(r["n_motifs"] for r in rows) / n
    avg_recall = sum(r["recall"] for r in rows) / n
    avg_compression = sum(r["compression_ratio"] for r in rows) / n
    beats_r1_compression = sum(
        1 for r in rows if r["compression_ratio"] > BASELINE_R1_PER_PATTERN_COMPRESSION[(r["file"], r["kolam"])]
    )
    beats_r1_recall = sum(
        1 for r in rows if r["recall"] > BASELINE_R1_PER_PATTERN_RECALL[(r["file"], r["kolam"])]
    )
    total_elapsed = sum(r["elapsed"] for r in rows)

    print()
    print(f"n patterns analyzed: {n}")
    print(f"% passing check_validity: {pct_valid:.1f}%")
    print(f"average motifs used: {avg_motifs:.2f}")
    print(f"average recall: {avg_recall:.4f}")
    print(f"average compression ratio: {avg_compression:.4f}")
    print(f"patterns where MDL-gated compression BEATS radius=1-only's per-pattern number: "
          f"{beats_r1_compression}/{n}")
    print(f"patterns where MDL-gated recall BEATS radius=1-only's per-pattern number: "
          f"{beats_r1_recall}/{n}")
    print(f"total wall time for all 15 patterns: {total_elapsed:.1f}s")

    print()
    print("=== three-way comparison (all averages over the same 15 patterns) ===")
    print(f"{'':>28} {'recall':>10} {'motifs':>10} {'compression':>12}")
    print(f"{'radius=1 only (capped)':>28} {BASELINE_R1_AVG['recall']:>10.4f} "
          f"{BASELINE_R1_AVG['motifs']:>10.2f} {BASELINE_R1_AVG['compression']:>12.4f}")
    print(f"{'adaptive (uncapped recall)':>28} {BASELINE_ADAPTIVE_UNCAPPED_AVG['recall']:>10.4f} "
          f"{BASELINE_ADAPTIVE_UNCAPPED_AVG['motifs']:>10.2f} "
          f"{BASELINE_ADAPTIVE_UNCAPPED_AVG['compression']:>12.4f}")
    print(f"{'adaptive (MDL-gated)':>28} {avg_recall:>10.4f} {avg_motifs:>10.2f} {avg_compression:>12.4f}")

    print()
    r109 = [r for r in rows if r["file"] == "kolam109.csv"]
    avg_recall_109 = sum(r["recall"] for r in r109) / len(r109)
    print(f"kolam109 (never reached full coverage under any approach) -- MDL-gated avg recall: "
          f"{avg_recall_109:.4f}, avg motifs: {sum(r['n_motifs'] for r in r109)/len(r109):.1f}")
    print("(uncapped-recall adaptive got ~98-99% on kolam109 by continuing to add motifs")
    print(" regardless of net cost; MDL-gating stopping earlier here is the gate doing its")
    print(" job, not a bug -- see accompanying interpretation in the session summary.)")


if __name__ == "__main__":
    sys.exit(main())
