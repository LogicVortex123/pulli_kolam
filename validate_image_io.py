"""Validate engine/image_io.py's build_graph() against known ground truth
from the synthetic-photo generator (generate_synthetic_photos.py).

Since detect_lattice fits its OWN integer coordinate system (independent
origin/orientation from the source CSV's), dots are matched to ground
truth by PIXEL position (each ground-truth dot's known final pixel
position after warping, vs each detected dot's pixel position) -- not by
comparing lattice coordinate labels directly, which would never agree
even for a perfect detector.

Reports, per image: dot detection precision/recall, edge tracing
precision/recall (both on distinct connectivity AND exact multiplicity),
and whether motifs.induce_motif_set_adaptive still finds sensible
structure on the RECOVERED graph vs. the ground-truth graph.
"""

from __future__ import annotations

import glob
import json
from collections import Counter

import cv2
import numpy as np
from scipy.spatial import cKDTree

from engine import graph_io, image_io, motifs, validity

MATCH_TOLERANCE_PX = 6.0


def align_and_score(image_stem: str) -> dict:
    img_path = f"synthetic_photos/{image_stem}.jpg"
    gt = json.load(open(f"synthetic_photos/{image_stem}.json"))

    preprocessed = image_io.preprocess(img_path)
    lattice = image_io.detect_lattice(preprocessed)
    recovered_edges_raw = image_io.trace_path(preprocessed, lattice)

    # --- dot detection precision/recall (pixel-position based) ---
    # preprocess() deskews (rotates) the image before detection, so
    # ground-truth pixel positions (recorded in the ORIGINAL degraded
    # image's frame) must go through that SAME rotation before comparing
    # -- otherwise a perfectly correct detector looks like it's 0%
    # accurate purely from a coordinate-frame mismatch, not a real error.
    gt_labels = list(gt["dot_pixel_positions"].keys())
    gt_px_orig = np.array([gt["dot_pixel_positions"][k] for k in gt_labels], dtype=np.float32)
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    M_deskew = cv2.getRotationMatrix2D((w / 2, h / 2), preprocessed.rotation_deg, 1.0)
    gt_px = cv2.transform(gt_px_orig.reshape(-1, 1, 2), M_deskew).reshape(-1, 2)
    det_px = np.array(lattice.pixel_positions) if lattice.pixel_positions else np.empty((0, 2))

    if len(det_px) and len(gt_px):
        tree_det = cKDTree(det_px)
        d_gt_to_det, idx_gt_to_det = tree_det.query(gt_px)
        dot_recall = float((d_gt_to_det < MATCH_TOLERANCE_PX).sum()) / len(gt_px)

        tree_gt = cKDTree(gt_px)
        d_det_to_gt, idx_det_to_gt = tree_gt.query(det_px)
        dot_precision = float((d_det_to_gt < MATCH_TOLERANCE_PX).sum()) / len(det_px)
    else:
        dot_recall = dot_precision = 0.0

    # --- build a recovered-lattice-coord -> ground-truth-node map, via
    # nearest pixel position (only for detected dots that matched a real
    # ground-truth dot within tolerance) ---
    recovered_to_gt = {}
    if len(det_px) and len(gt_px):
        for i, (dx, dy) in enumerate(det_px):
            j = idx_det_to_gt[i]
            if d_det_to_gt[i] < MATCH_TOLERANCE_PX:
                gt_node = tuple(int(v) for v in gt_labels[j].split(","))
                recovered_to_gt[lattice.lattice_coords[i]] = gt_node

    # --- remap recovered edges into ground-truth node space; edges
    # touching an unmatched dot can't be scored and are dropped ---
    remapped_edges = []
    for a, b in recovered_edges_raw:
        if a in recovered_to_gt and b in recovered_to_gt:
            remapped_edges.append(frozenset({recovered_to_gt[a], recovered_to_gt[b]}))

    gt_edges_multi = Counter(frozenset({tuple(a), tuple(b)}) for a, b in gt["edges"])
    recovered_multi = Counter(remapped_edges)

    gt_distinct = set(gt_edges_multi.keys())
    recovered_distinct = set(recovered_multi.keys())

    edge_recall_distinct = len(recovered_distinct & gt_distinct) / len(gt_distinct) if gt_distinct else 1.0
    edge_precision_distinct = (
        len(recovered_distinct & gt_distinct) / len(recovered_distinct) if recovered_distinct else 0.0
    )

    # multiplicity-exact match: same edge AND same strand count
    exact_multi_matches = sum(
        min(recovered_multi[e], gt_edges_multi[e]) for e in gt_distinct
    )
    n_gt_instances = sum(gt_edges_multi.values())
    n_recovered_instances = sum(recovered_multi.values())
    edge_recall_exact = exact_multi_matches / n_gt_instances if n_gt_instances else 1.0
    edge_precision_exact = exact_multi_matches / n_recovered_instances if n_recovered_instances else 0.0

    return {
        "stem": image_stem,
        "gt_n_dots": len(gt_labels),
        "det_n_dots": len(det_px),
        "dot_precision": round(dot_precision, 4),
        "dot_recall": round(dot_recall, 4),
        "gt_n_edges_distinct": len(gt_distinct),
        "recovered_n_edges_distinct": len(recovered_distinct),
        "edge_precision_distinct": round(edge_precision_distinct, 4),
        "edge_recall_distinct": round(edge_recall_distinct, 4),
        "gt_n_edges_raw": n_gt_instances,
        "recovered_n_edges_raw": n_recovered_instances,
        "edge_precision_exact_multiplicity": round(edge_precision_exact, 4),
        "edge_recall_exact_multiplicity": round(edge_recall_exact, 4),
        "recovered_to_gt": recovered_to_gt,
        "lattice": lattice,
        "recovered_edges_raw": recovered_edges_raw,
    }


def induction_comparison(csv_path: str, kolam_number: int, recovered_graph):
    """Run induce_motif_set_adaptive on both the ground-truth CSV graph
    and the recovered (image-derived) graph, report both."""
    gt_graph = graph_io.load_kolam(csv_path, kolam_number)
    gt_dots = graph_io.dots_set(gt_graph)
    gt_interior = motifs.interior_points(gt_dots, radius=1)
    gt_placements, gt_residual, gt_full = motifs.induce_motif_set_adaptive(
        gt_graph, gt_interior, gt_dots, max_radius=2, max_motifs_per_radius=500
    )
    gt_total = len({frozenset(e) for e in gt_graph.edges()})
    gt_recall = (gt_total - len(gt_residual)) / gt_total if gt_total else 1.0

    rec_dots = set(recovered_graph.nodes())
    rec_interior = motifs.interior_points(rec_dots, radius=1)
    rec_placements, rec_residual, rec_full = motifs.induce_motif_set_adaptive(
        recovered_graph, rec_interior, rec_dots, max_radius=2, max_motifs_per_radius=500
    )
    rec_total = len({frozenset(e) for e in recovered_graph.edges()})
    rec_recall = (rec_total - len(rec_residual)) / rec_total if rec_total else 1.0

    return {
        "gt_valid": validity.is_valid_single_stroke(gt_graph),
        "gt_n_motifs": len(gt_placements),
        "gt_induction_recall": round(gt_recall, 4),
        "rec_valid": validity.is_valid_single_stroke(recovered_graph),
        "rec_n_motifs": len(rec_placements),
        "rec_induction_recall": round(rec_recall, 4),
    }


def main():
    stems = sorted(
        f.split("/")[-1].replace(".jpg", "").replace("\\", "/").split("/")[-1]
        for f in glob.glob("synthetic_photos/*.jpg")
    )

    print(f"{'image':>16} {'gt_dots':>8} {'det_dots':>9} {'dot_P':>7} {'dot_R':>7} "
          f"{'edgeP_d':>8} {'edgeR_d':>8} {'edgeP_m':>8} {'edgeR_m':>8}")
    rows = []
    for stem in stems:
        r = align_and_score(stem)
        rows.append(r)
        print(f"{r['stem']:>16} {r['gt_n_dots']:>8} {r['det_n_dots']:>9} "
              f"{r['dot_precision']:>7} {r['dot_recall']:>7} "
              f"{r['edge_precision_distinct']:>8} {r['edge_recall_distinct']:>8} "
              f"{r['edge_precision_exact_multiplicity']:>8} {r['edge_recall_exact_multiplicity']:>8}")

    n = len(rows)
    print()
    print(f"n synthetic photos: {n}")
    print(f"avg dot precision: {sum(r['dot_precision'] for r in rows)/n:.4f}")
    print(f"avg dot recall:    {sum(r['dot_recall'] for r in rows)/n:.4f}")
    print(f"avg edge precision (distinct connectivity): {sum(r['edge_precision_distinct'] for r in rows)/n:.4f}")
    print(f"avg edge recall    (distinct connectivity): {sum(r['edge_recall_distinct'] for r in rows)/n:.4f}")
    print(f"avg edge precision (exact multiplicity):    {sum(r['edge_precision_exact_multiplicity'] for r in rows)/n:.4f}")
    print(f"avg edge recall    (exact multiplicity):    {sum(r['edge_recall_exact_multiplicity'] for r in rows)/n:.4f}")

    print()
    print("=== downstream induction: recovered (image) graph vs ground-truth (CSV) graph ===")
    csv_lookup = {
        "kolam19_k1": ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 1),
        "kolam19_k2": ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 2),
        "kolam19_k3": ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 3),
        "kolam19_k27": ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 27),
        "kolam19_k50": ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 50),
        "kolam29_k1": ("kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv", 1),
        "kolam29_k2": ("kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv", 2),
    }
    for stem in stems:
        csv_path, kolam_number = csv_lookup[stem]
        recovered_graph = image_io.build_graph(f"synthetic_photos/{stem}.jpg")
        ic = induction_comparison(csv_path, kolam_number, recovered_graph)
        print(f"{stem:>16}  gt: valid={ic['gt_valid']} motifs={ic['gt_n_motifs']:>3} "
              f"recall={ic['gt_induction_recall']:.4f}   "
              f"recovered: valid={ic['rec_valid']} motifs={ic['rec_n_motifs']:>3} "
              f"recall={ic['rec_induction_recall']:.4f}")


if __name__ == "__main__":
    main()
