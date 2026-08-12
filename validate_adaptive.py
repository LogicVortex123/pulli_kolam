"""Run ADAPTIVE (per-region radius) motif induction across the same 15
real patterns as validate_real_data.py, and compare directly against the
two fixed-radius baselines already on record from that run:

  radius=1 only (20-motif cap): avg 89.7% recall, avg 10.5 motifs,
    plateaus 85-93%, 0/15 reached 95% recall.
  radius=2 only (spot-checked, not run on all 15): 100% recall on
    kolam19 pattern 1 with 14 motifs, but only 35% recall on kolam109
    pattern 1 within a 30-motif cap (13 motifs got 91% at radius=1).

Adaptive strategy (engine.motifs.induce_motif_set_adaptive): radius=1
first over the whole pattern, then radius=2 retried ONLY around whatever
residual edges remain, then radius=3 if still residual. See its
docstring for why (avoids paying radius=2's fragmentation cost on
regions radius=1 already solved).
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
MAX_MOTIFS_PER_RADIUS = 20

# Baselines already measured this session (validate_real_data.py output
# and the follow-up radius=2 spot-check), reproduced here only for the
# printed side-by-side comparison -- not recomputed, not invented.
BASELINE_R1_AVG_RECALL = 0.8971
BASELINE_R1_AVG_MOTIFS = 10.47
BASELINE_R1_KOLAM19_P1 = {"recall": 0.8772, "motifs": 9}
BASELINE_R2_KOLAM19_P1 = {"recall": 1.0000, "motifs": 14}
BASELINE_R1_KOLAM109_P1 = {"recall": 0.9142, "motifs": 13}
BASELINE_R2_KOLAM109_P1 = {"recall": 0.3532, "motifs": 30}  # capped at 30, not 20


def analyze(csv_path: str, kolam_number: int) -> dict:
    G = graph_io.load_kolam(csv_path, kolam_number)
    dots = graph_io.dots_set(G)

    v_ok = validity.is_valid_single_stroke(G)

    interior_r1 = motifs.interior_points(dots, radius=1)
    total_edges = {frozenset(e) for e in G.edges()}
    n_total = len(total_edges)

    placements, residual, fully_covered = motifs.induce_motif_set_adaptive(
        G, interior_r1, dots, max_radius=MAX_RADIUS, max_motifs_per_radius=MAX_MOTIFS_PER_RADIUS
    )

    covered = n_total - len(residual)
    final_recall = covered / n_total if n_total else 1.0
    ratio = motifs.compression_ratio(G, placements, residual)

    by_radius = Counter(p.radius for p in placements)
    edges_by_radius = Counter()
    for p in placements:
        edges_by_radius[p.radius] += len(p.new_edges)

    return {
        "n_dots": G.number_of_nodes(),
        "n_edges": n_total,
        "valid": v_ok,
        "n_motifs_total": len(placements),
        "motifs_by_radius": dict(by_radius),
        "edges_by_radius": dict(edges_by_radius),
        "final_recall": round(final_recall, 4),
        "fully_covered": fully_covered,
        "n_residual_edges": len(residual),
        "compression_ratio": round(ratio, 4),
    }


def main():
    print(f"adaptive induction: radius=1 first (whole pattern), then radius=2..{MAX_RADIUS} "
          f"retried only around residual, {MAX_MOTIFS_PER_RADIUS} motif cap per tier")
    header = (
        f"{'file':>10} {'kolam':>6} {'dots':>6} {'edges':>6} {'valid':>6} "
        f"{'n_motifs':>9} {'by_radius':>18} {'recall':>8} {'full_cov':>9} "
        f"{'residual':>9} {'compress':>9} {'sec':>7}"
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
            print(
                f"{fname:>10} {k:>6} {r['n_dots']:>6} {r['n_edges']:>6} "
                f"{str(r['valid']):>6} {r['n_motifs_total']:>9} {by_radius_str:>18} "
                f"{r['final_recall']:>8} {str(r['fully_covered']):>9} {r['n_residual_edges']:>9} "
                f"{r['compression_ratio']:>9} {elapsed:>7.2f}"
            )

    n = len(rows)
    pct_valid = 100 * sum(r["valid"] for r in rows) / n
    pct_fully_covered = 100 * sum(r["fully_covered"] for r in rows) / n
    avg_motifs = sum(r["n_motifs_total"] for r in rows) / n
    avg_recall = sum(r["final_recall"] for r in rows) / n
    avg_compression = sum(r["compression_ratio"] for r in rows) / n
    avg_edges = sum(r["n_edges"] for r in rows) / n
    total_elapsed = sum(r["elapsed"] for r in rows)

    total_motifs_by_radius = Counter()
    for r in rows:
        for radius, count in r["motifs_by_radius"].items():
            total_motifs_by_radius[radius] += count

    print()
    print(f"n patterns analyzed: {n} (same 15 patterns as validate_real_data.py: "
          f"3 files x 5 kolams each)")
    print(f"% passing check_validity: {pct_valid:.1f}%")
    print(f"% reaching full (100%) coverage within {MAX_RADIUS} radius tiers: {pct_fully_covered:.1f}%")
    print(f"average motifs used (all tiers combined): {avg_motifs:.2f}")
    print(f"total motifs by radius tier across all 15 patterns: "
          f"{dict(sorted(total_motifs_by_radius.items()))}")
    print(f"average final recall: {avg_recall:.4f}")
    print(f"average CORRECTED compression ratio: {avg_compression:.4f}")
    print(f"total wall time for all 15 patterns: {total_elapsed:.1f}s")

    print()
    print("=== comparison against the two fixed-radius baselines already on record ===")
    print(f"radius=1 only, all 15 patterns:  avg recall {BASELINE_R1_AVG_RECALL:.4f}, "
          f"avg motifs {BASELINE_R1_AVG_MOTIFS:.2f}")
    print(f"adaptive,      all 15 patterns:  avg recall {avg_recall:.4f}, "
          f"avg motifs {avg_motifs:.2f}")
    print()
    r19 = next(r for r in rows if r["file"] == "kolam19.csv" and r["kolam"] == 1)
    print(f"kolam19 pattern 1 -- radius=1 only:  recall {BASELINE_R1_KOLAM19_P1['recall']:.4f}, "
          f"motifs {BASELINE_R1_KOLAM19_P1['motifs']}")
    print(f"kolam19 pattern 1 -- radius=2 only:  recall {BASELINE_R2_KOLAM19_P1['recall']:.4f}, "
          f"motifs {BASELINE_R2_KOLAM19_P1['motifs']}")
    print(f"kolam19 pattern 1 -- adaptive:       recall {r19['final_recall']:.4f}, "
          f"motifs {r19['n_motifs_total']} {r19['motifs_by_radius']}")
    print()
    r109 = next(r for r in rows if r["file"] == "kolam109.csv" and r["kolam"] == 1)
    print(f"kolam109 pattern 1 -- radius=1 only (cap 20): recall {BASELINE_R1_KOLAM109_P1['recall']:.4f}, "
          f"motifs {BASELINE_R1_KOLAM109_P1['motifs']}")
    print(f"kolam109 pattern 1 -- radius=2 only (cap 30):  recall {BASELINE_R2_KOLAM109_P1['recall']:.4f}, "
          f"motifs {BASELINE_R2_KOLAM109_P1['motifs']}")
    print(f"kolam109 pattern 1 -- adaptive (cap 20/tier):  recall {r109['final_recall']:.4f}, "
          f"motifs {r109['n_motifs_total']} {r109['motifs_by_radius']}")


if __name__ == "__main__":
    sys.exit(main())
