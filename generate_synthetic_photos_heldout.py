"""HELD-OUT synthetic photo batch, for checking whether image_io.py's
accuracy numbers were an artifact of tuning DOT_RADIUS_FRAC/LINE_THICKNESS_
FRAC/PARALLEL_OFFSET_FRAC (in generate_synthetic_photos.py) and the
detection thresholds in engine/image_io.py by direct measurement against
the original 7 images before reporting accuracy on those same 7 images.

Rules for this batch, to keep it a genuine held-out test:
  - DIFFERENT kolam patterns than the original 7 (not just different
    noise on the same 7 source patterns).
  - DIFFERENT random seed range for the degradation (rotation/perspective/
    noise instances).
  - Reuses generate_synthetic_photos.py's rendering code UNCHANGED (same
    DOT_RADIUS_FRAC etc -- those are generator properties, not something
    to re-tune per batch).
  - Written to a separate synthetic_photos_heldout/ directory so the
    original tuned set is untouched and the two are never confused.
  - After generating, engine/image_io.py itself must NOT be modified in
    response to whatever accuracy this batch measures -- that would just
    move the tuning-on-the-test-set problem here instead of solving it.
"""

from __future__ import annotations

import os

import generate_synthetic_photos as gsp

OUT_DIR = "synthetic_photos_heldout"

HELD_OUT_PATTERNS = [
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 75),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 100),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 150),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 250),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 350),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv", 20),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv", 50),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv", 80),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    gsp.OUT_DIR = OUT_DIR  # redirect output, everything else unchanged
    for i, (csv_path, kolam_number) in enumerate(HELD_OUT_PATTERNS):
        fname = csv_path.split("/")[-1].replace(".csv", "")
        stem = f"{fname}_k{kolam_number}"
        # seed range 7000+ is disjoint from the original set's 1000+i
        gsp.generate_one(csv_path, kolam_number, seed=7000 + i, out_stem=stem)


if __name__ == "__main__":
    main()
