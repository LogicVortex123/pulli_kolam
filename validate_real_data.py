"""Run multi-motif (set-cover) induction + validity checks across real
patterns from the Kaggle 'one-stroke-dotted-pulli-kolam' dataset and print
measured numbers -- per session exit criteria, no invented numbers.

Dataset audit: the dataset ships exactly 3 CSV files (kolam19.csv,
kolam29.csv, kolam109.csv -- one per grid size), not 4+. All 3 are used
here; there is no 4th file to add.

For every pattern: validity gate on the raw extracted graph, number of
motifs the greedy set-cover needs to reach >=95% edge recall (capped at
MAX_MOTIFS), the corrected compression ratio (motif rules + placements +
explicit residual edges, see engine.motifs.compression_ratio), and
whether the motif count stays small (real repeating structure) or
approaches the edge count (little/no repeating structure).
"""

from __future__ import annotations

import sys
import time

from engine import graph_io, motifs, validity

DATASET_FILES = [
    "kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv",
    "kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv",
    "kolam_data/Kolam CSV files/Kolam CSV files/kolam109.csv",
]
KOLAM_NUMBERS_PER_FILE = [1, 2, 3, 4, 5]
RADIUS = 1
MAX_MOTIFS = 20
RECALL_TARGET = 0.95


def analyze(csv_path: str, kolam_number: int, radius: int = RADIUS) -> dict:
    G = graph_io.load_kolam(csv_path, kolam_number)
    dots = graph_io.dots_set(G)

    v_original = validity.check_validity(G)
    v_original_ok = validity.is_valid_single_stroke(G)

    interior = motifs.interior_points(dots, radius=radius)
    total_edges = {frozenset(e) for e in G.edges()}
    n_total = len(total_edges)  # DISTINCT edges (connectivity basis) -- coverage/
    # recall/residual/compression are all computed on this basis, not raw
    # edge count with parallel-strand multiplicity (see compression_ratio
    # docstring). n_edges_raw below is reported only for context.
    n_edges_raw = G.number_of_edges()

    placements, residual, fully_covered = motifs.induce_motif_set(
        G, interior, dots, radius=radius, max_motifs=MAX_MOTIFS
    )

    # Cumulative recall after each motif is added, in selection order, to
    # find how many motifs it actually took to cross the recall target.
    covered = 0
    motifs_to_target = None
    for i, p in enumerate(placements, start=1):
        covered += len(p.new_edges)
        recall_so_far = covered / n_total if n_total else 1.0
        if motifs_to_target is None and recall_so_far >= RECALL_TARGET:
            motifs_to_target = i

    final_recall = covered / n_total if n_total else 1.0
    ratio = motifs.compression_ratio(G, placements, residual)

    return {
        "n_dots": G.number_of_nodes(),
        "n_edges_raw": n_edges_raw,
        "n_edges_distinct": n_total,
        "valid": v_original_ok,
        "eulerian_circuit": v_original["is_eulerian_circuit"],
        "n_motifs_used": len(placements),
        "final_recall": round(final_recall, 4),
        "motifs_to_95pct_recall": motifs_to_target,  # None = never reached within cap
        "fully_covered": fully_covered,
        "n_residual_edges": len(residual),
        "compression_ratio": round(ratio, 4),
    }


def main():
    print("(edges = DISTINCT connectivity edges, not raw strand count; "
          "see compression_ratio docstring for why)")
    header = (
        f"{'file':>10} {'kolam':>6} {'dots':>6} {'edges':>6} {'valid':>6} "
        f"{'n_motifs':>9} {'recall':>8} {'->95%@':>8} {'full_cov':>9} "
        f"{'residual':>9} {'compress':>9} {'sec':>6}"
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
            m95 = r["motifs_to_95pct_recall"]
            m95_str = str(m95) if m95 is not None else "none"
            print(
                f"{fname:>10} {k:>6} {r['n_dots']:>6} {r['n_edges_distinct']:>6} "
                f"{str(r['valid']):>6} {r['n_motifs_used']:>9} {r['final_recall']:>8} "
                f"{m95_str:>8} {str(r['fully_covered']):>9} {r['n_residual_edges']:>9} "
                f"{r['compression_ratio']:>9} {elapsed:>6.2f}"
            )

    n = len(rows)
    pct_valid = 100 * sum(r["valid"] for r in rows) / n
    reached_95 = [r for r in rows if r["motifs_to_95pct_recall"] is not None]
    pct_reached_95 = 100 * len(reached_95) / n
    avg_motifs_used = sum(r["n_motifs_used"] for r in rows) / n
    avg_recall = sum(r["final_recall"] for r in rows) / n
    avg_compression = sum(r["compression_ratio"] for r in rows) / n
    avg_edges = sum(r["n_edges_distinct"] for r in rows) / n
    avg_duplicate_frac = sum(
        1 - (r["n_edges_distinct"] / r["n_edges_raw"]) for r in rows
    ) / n

    print()
    print(f"n patterns analyzed: {n} (across {len(DATASET_FILES)} CSV files -- "
          f"all files in the dataset, see module docstring)")
    print(f"% passing check_validity (is_valid_single_stroke): {pct_valid:.1f}%")
    print(f"% reaching >={RECALL_TARGET*100:.0f}% recall within {MAX_MOTIFS} motifs: {pct_reached_95:.1f}%")
    if reached_95:
        avg_motifs_to_95 = sum(r["motifs_to_95pct_recall"] for r in reached_95) / len(reached_95)
        print(f"average motifs needed to reach >={RECALL_TARGET*100:.0f}% recall "
              f"(among those that did): {avg_motifs_to_95:.2f}")
    print(f"average motifs used (capped at {MAX_MOTIFS}): {avg_motifs_used:.2f}")
    print(f"average final recall: {avg_recall:.4f}")
    print(f"average distinct edge count per pattern: {avg_edges:.1f}")
    print(f"average fraction of edges that are duplicate parallel strands "
          f"(raw vs distinct): {avg_duplicate_frac:.4f}")
    print(f"average CORRECTED compression ratio (motifs+placements+residual "
          f"vs distinct edges): {avg_compression:.4f}")
    print(f"-> motif count vs. edge count: avg {avg_motifs_used:.1f} motifs "
          f"explain patterns averaging {avg_edges:.0f} edges each")


if __name__ == "__main__":
    sys.exit(main())
