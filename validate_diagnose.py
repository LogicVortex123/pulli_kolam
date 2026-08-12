"""Run diagnose_validity() on the image-recovered graph for every
synthetic photo (both the original tuned set and the held-out batch) and
report, for the patterns that FAIL the strict check_validity gate, how
many edge-corrections diagnose_validity actually finds. Small, localized
correction counts would support reframing the strict-gate failures as
"the reconstruction is fundamentally sound, the strict gate is just the
wrong tool for noisy image-derived data" rather than "the pipeline
produced garbage" -- but this script measures that, it doesn't assume it.
"""

from __future__ import annotations

import glob
import json

from engine import image_io, validity

DIRS = ["synthetic_photos", "synthetic_photos_heldout"]


def main():
    rows = []
    for photo_dir in DIRS:
        for jpath in sorted(glob.glob(f"{photo_dir}/*.jpg")):
            stem = jpath.replace("\\", "/").split("/")[-1].replace(".jpg", "")
            gt = json.load(open(jpath.replace(".jpg", ".json")))
            G = image_io.build_graph(jpath)
            d = validity.diagnose_validity(G)
            rows.append({
                "dir": photo_dir,
                "stem": stem,
                "n_nodes": G.number_of_nodes(),
                "gt_n_nodes": gt["n_nodes"],
                "is_valid": d["is_valid"],
                "n_odd_degree_nodes": d["n_odd_degree_nodes"],
                "n_corrections": d["n_corrections"],
                "total_correction_cost": d["total_correction_cost"],
                "n_components": d["connected_components"],
                "n_outside_largest": d["n_nodes_outside_largest_component"],
            })

    print(f"{'set':>10} {'image':>16} {'nodes':>6} {'valid':>6} {'n_odd':>6} "
          f"{'n_corr':>7} {'corr_cost':>10} {'n_comp':>7} {'outside':>8}")
    for r in rows:
        tag = "TUNED" if r["dir"] == "synthetic_photos" else "HELDOUT"
        print(f"{tag:>10} {r['stem']:>16} {r['n_nodes']:>6} {str(r['is_valid']):>6} "
              f"{r['n_odd_degree_nodes']:>6} {r['n_corrections']:>7} "
              f"{r['total_correction_cost']:>10} {r['n_components']:>7} {r['n_outside_largest']:>8}")

    print()
    failed = [r for r in rows if not r["is_valid"]]
    passed = [r for r in rows if r["is_valid"]]
    print(f"n images: {len(rows)}  ({len(passed)} pass strict gate, {len(failed)} fail)")
    if failed:
        avg_corrections_when_failed = sum(r["n_corrections"] for r in failed) / len(failed)
        avg_cost_when_failed = sum(r["total_correction_cost"] for r in failed) / len(failed)
        max_corrections = max(r["n_corrections"] for r in failed)
        max_cost = max(r["total_correction_cost"] for r in failed)
        print(f"among the {len(failed)} that fail check_validity:")
        print(f"  avg n_corrections needed: {avg_corrections_when_failed:.2f} "
              f"(max {max_corrections})")
        print(f"  avg total correction cost (edges to add): {avg_cost_when_failed:.2f} "
              f"(max {max_cost})")
        print(f"  as a fraction of graph size: avg cost/n_nodes = "
              f"{sum(r['total_correction_cost']/r['n_nodes'] for r in failed)/len(failed):.4f}")
        n_disconnection_involved = sum(1 for r in failed if r["n_outside_largest"] > 0)
        print(f"  of these, {n_disconnection_involved}/{len(failed)} also have nodes "
              f"outside the largest component (a SEPARATE issue matching can't fix)")


if __name__ == "__main__":
    main()
