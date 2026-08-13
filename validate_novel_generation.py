"""M3.7 evaluation: a small, reproducible set of novel structural
candidates -- motif libraries discovered from one real pattern, placed
onto a DIFFERENT dot layout (either another real pattern's layout, never
seen by that library, or a genuinely synthetic grid that appears nowhere
in the dataset).

For each candidate: valid?, connected?, Eulerian?, n_dots, n_edges,
motif count (library size), symmetry (D4 motif coverage fraction on the
CANDIDATE itself, via the existing engine.symmetry.analyze_symmetry --
reused, not reimplemented), whether it duplicates the library's own
source pattern, generation time.

"Novelty" here is measured structurally and narrowly, per the task's own
instruction not to claim artistic novelty without defining how it's
measured: a candidate counts as "not a duplicate" if and only if its
exact edge multiset differs from the specific source pattern its motif
library was extracted from (engine.novel_generation.duplicates_source).
This says nothing about visual/artistic originality -- it is a strict,
mechanical, structural check, and is reported as exactly that.
"""

from __future__ import annotations

import time

from engine.dataset import load_kolam
from engine.motif_selection import induce_motif_set_eulerian_aware
from engine.novel_generation import duplicates_source, extract_motif_library, generate_novel_kolam
from engine.symmetry import analyze_symmetry

CASES = [
    ("kolam19#1 library -> kolam19#2 layout", "kolam19", 1, "kolam19", 2),
    ("kolam19#1 library -> kolam19#3 layout", "kolam19", 1, "kolam19", 3),
    ("kolam29#1 library -> kolam29#2 layout", "kolam29", 1, "kolam29", 2),
    ("kolam19#1 library -> synthetic 15x15 grid", "kolam19", 1, None, None),
    ("kolam29#1 library -> synthetic 15x15 grid", "kolam29", 1, None, None),
]


def run_case(label, lib_collection, lib_pattern_id, target_collection, target_pattern_id):
    t0 = time.time()
    source = load_kolam(lib_collection, lib_pattern_id)
    induction_result = induce_motif_set_eulerian_aware(source, radius=1, max_radius=1)
    library = extract_motif_library(induction_result.placements)

    if target_collection is not None:
        target_pattern = load_kolam(target_collection, target_pattern_id)
        dot_points = target_pattern.dot_points
        target_label = f"{target_collection}#{target_pattern_id}"
    else:
        dot_points = {(x, y) for x in range(15) for y in range(15)}
        target_pattern = None
        target_label = "synthetic 15x15 grid"

    candidate = generate_novel_kolam(library, dot_points)
    elapsed = time.time() - t0

    _motif, symmetry_coverage, _transforms = analyze_symmetry(candidate.graph, dot_points)

    dup = duplicates_source(candidate.graph, target_pattern) if target_pattern is not None else False

    v = candidate.validity_result
    return {
        "label": label,
        "target_label": target_label,
        "valid": candidate.is_valid,
        "connected": v["largest_component_covers_all_nodes"] and v["connected_components"] == 1,
        "eulerian_circuit": v["is_eulerian_circuit"],
        "eulerian_path": v["has_eulerian_path"],
        "n_dots": candidate.n_dots,
        "n_edges": candidate.n_distinct_edges,
        "motif_library_size": len(library),
        "n_placements_used": len(candidate.placements),
        "symmetry_coverage": round(symmetry_coverage, 4),
        "duplicates_source": dup,
        "generation_time_sec": round(elapsed, 3),
    }


def main():
    rows = [run_case(*case) for case in CASES]

    for r in rows:
        print(f"--- {r['label']} ---")
        print(f"  target layout: {r['target_label']}")
        print(f"  valid={r['valid']}  connected={r['connected']}  "
              f"eulerian_circuit={r['eulerian_circuit']}  eulerian_path={r['eulerian_path']}")
        print(f"  n_dots={r['n_dots']}  n_edges={r['n_edges']}  "
              f"motif_library_size={r['motif_library_size']}  n_placements_used={r['n_placements_used']}")
        print(f"  symmetry_coverage={r['symmetry_coverage']}  "
              f"duplicates_source={r['duplicates_source']}  time={r['generation_time_sec']}s")
        print()

    n = len(rows)
    n_valid = sum(r["valid"] for r in rows)
    n_connected = sum(r["connected"] for r in rows)
    n_duplicates = sum(bool(r["duplicates_source"]) for r in rows)
    print(f"=== summary across {n} candidates ===")
    print(f"valid: {n_valid}/{n}")
    print(f"fully connected: {n_connected}/{n}")
    print(f"duplicate a source pattern (strict edge-multiset match): {n_duplicates}/{n}")


if __name__ == "__main__":
    main()
