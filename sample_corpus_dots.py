"""Sample the bundled Kaggle dataset's rendered JPGs (kolam19/29/109
"Images" folders -- NOT the synthetic photos we generated) and check,
programmatically, whether each one has visible dot markers or is
line-only art like kolam19-26.jpg.

Heuristic, calibrated against known examples (see PULLI session notes):
run build_graph() and compute the fraction of odd-degree nodes.
  - Known dot-marked synthetic images: 0.000-0.022 (0-2.2%)
  - The one known dot-LESS bundled image (kolam19-26.jpg): 0.388 (38.8%)
There's a ~20x gap between those two populations, so a graph with
odd-degree fraction above ODD_FRACTION_THRESHOLD is classified as
"likely no visible dots / degenerate lattice detection," below it as
"likely has visible dots." This is a heuristic proxy, not a ground-truth
label (we have no independent dot-marker annotation for this corpus) --
reported as such.
"""

from __future__ import annotations

import glob
import random

from engine import image_io

ODD_FRACTION_THRESHOLD = 0.10

FOLDERS = {
    "kolam19": "kolam_data/Kolam19 Images/Kolam19 Images",
    "kolam29": "kolam_data/Kolam29 Images/Kolam29 Images",
    "kolam109": "kolam_data/Kolam109 Images/Kolam109 Images",
}
N_PER_FAMILY = 10


def classify(path: str) -> dict:
    try:
        G = image_io.build_graph(path)
    except Exception as e:
        return {"path": path, "error": str(e), "n_nodes": 0, "odd_frac": None, "likely_dotted": False}
    if G.number_of_nodes() == 0:
        return {"path": path, "error": None, "n_nodes": 0, "odd_frac": None, "likely_dotted": False}
    odd = sum(1 for _n, d in G.degree() if d % 2 == 1)
    frac = odd / G.number_of_nodes()
    return {
        "path": path,
        "error": None,
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "odd_frac": frac,
        "likely_dotted": frac <= ODD_FRACTION_THRESHOLD,
    }


def main():
    rng = random.Random(42)
    results = []
    for family, folder in FOLDERS.items():
        all_paths = sorted(glob.glob(f"{folder}/*.jpg"))
        sample = rng.sample(all_paths, min(N_PER_FAMILY, len(all_paths)))
        print(f"\n--- {family}: sampling {len(sample)} of {len(all_paths)} images ---")
        for p in sample:
            r = classify(p)
            r["family"] = family
            results.append(r)
            if r["error"]:
                print(f"  {p}: ERROR {r['error']}")
            elif r["n_nodes"] == 0:
                print(f"  {p}: no dots detected at all")
            else:
                print(f"  {p}: n_nodes={r['n_nodes']:>5} odd_frac={r['odd_frac']:.4f} "
                      f"-> {'DOTTED' if r['likely_dotted'] else 'LINE-ONLY (likely)'}")

    n = len(results)
    n_dotted = sum(1 for r in results if r["likely_dotted"])
    n_errors = sum(1 for r in results if r["error"] or r["n_nodes"] == 0)
    print(f"\n=== summary across {n} sampled images ===")
    for family in FOLDERS:
        fam_results = [r for r in results if r["family"] == family]
        fam_dotted = sum(1 for r in fam_results if r["likely_dotted"])
        print(f"{family}: {fam_dotted}/{len(fam_results)} classified as having visible dots")
    print(f"overall: {n_dotted}/{n} classified as having visible dots "
          f"({n_errors} failed/degenerate outright)")


if __name__ == "__main__":
    main()
