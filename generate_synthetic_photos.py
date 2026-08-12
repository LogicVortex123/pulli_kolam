"""Render real, already-validated Kaggle CSV kolam patterns as synthetic
"photos": draw dots + the traced line, then degrade with rotation, mild
perspective warp, blur, noise, uneven lighting, and JPEG compression to
roughly simulate a phone photo of a hand-drawn kolam.

This is EXPLICITLY a synthetic-photo proxy, not a real photograph -- it
gives known ground truth (the exact source CSV graph, and the exact
final pixel position of every dot after warping) to validate
engine/image_io.py against, which a genuinely random real photo could
not. See PULLI session notes: this is a stated limitation, not a hidden
shortcut -- a real phone photo has lighting/ink/paper variation this
generator does not attempt to model.
"""

from __future__ import annotations

import json
import math
import random

import cv2
import numpy as np

from engine import graph_io

OUT_DIR = "synthetic_photos"
IMAGE_SIZE = 900
MARGIN = 90
# Dot/line size are fractions of the lattice pixel spacing (`scale`), not
# fixed pixel constants -- a denser lattice needs proportionally smaller
# dots to stay visually distinguishable, same as real kolams do. A fixed
# DOT_RADIUS=7 looked fine on kolam19 (scale~21px) but made kolam29's
# dots (scale~13px) nearly touch their neighbors, breaking dot detection
# entirely (see PULLI session notes).
DOT_RADIUS_FRAC = 0.28
LINE_THICKNESS_FRAC = 0.12
# Wide enough that the two strands of a genuine double-strand edge survive
# blur/JPEG/skeletonization as visually and topologically SEPARATE paths,
# not merge into one (tuned empirically against kolam19 pattern 1's known
# 84 double-strand edges: 0.40 recovers 228/228 distinct pairs and 82/84
# doubles; wider (0.45) actually gets WORSE -- the offset strand starts
# intruding into neighboring dots' capture radius). Real kambi-kolam
# double strands are typically drawn closer together than this -- a known
# simplification, flagged in the session report, not hidden.
PARALLEL_OFFSET_FRAC = 0.40

PATTERNS = [
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 1),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 2),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 3),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 27),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam19.csv", 50),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv", 1),
    ("kolam_data/Kolam CSV files/Kolam CSV files/kolam29.csv", 2),
]


def lattice_to_pixel_transform(dots: set[tuple[int, int]]) -> tuple[float, float, float]:
    """Return (scale, offset_x, offset_y) s.t. pixel = (lattice*scale + offset),
    with a y-flip (image y grows down) baked into `scale`'s y sign via the
    caller. Fits the pattern into IMAGE_SIZE with MARGIN on each side."""
    xs = [p[0] for p in dots]
    ys = [p[1] for p in dots]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1)
    span_y = max(max_y - min_y, 1)
    usable = IMAGE_SIZE - 2 * MARGIN
    scale = usable / max(span_x, span_y)
    offset_x = MARGIN - min_x * scale + (usable - span_x * scale) / 2
    offset_y = MARGIN - min_y * scale + (usable - span_y * scale) / 2
    return scale, offset_x, offset_y


def render_clean(G, dots, scale, offset_x, offset_y) -> np.ndarray:
    img = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), 250, dtype=np.uint8)  # off-white paper

    dot_radius = max(3, round(scale * DOT_RADIUS_FRAC))
    line_thickness = max(1, round(scale * LINE_THICKNESS_FRAC))
    parallel_offset = max(2, round(scale * PARALLEL_OFFSET_FRAC))

    def to_px(node):
        x, y = node
        # y-flip: image row grows downward, lattice y grows upward (matches
        # the matplotlib convention used elsewhere in this project)
        return (int(round(x * scale + offset_x)), int(round(IMAGE_SIZE - (y * scale + offset_y))))

    # Draw edges first (so dots sit visually on top, like real kolam ink
    # where the dot is placed and the line loops around it)
    seen_pairs: dict[frozenset, int] = {}
    for a, b in G.edges():
        pair = frozenset({a, b})
        idx = seen_pairs.get(pair, 0)
        seen_pairs[pair] = idx + 1
        pa, pb = to_px(a), to_px(b)
        if idx == 0:
            cv2.line(img, pa, pb, (40, 40, 45), line_thickness, cv2.LINE_AA)
        else:
            # genuine second strand: offset perpendicular to the segment
            dx, dy = pb[0] - pa[0], pb[1] - pa[1]
            length = math.hypot(dx, dy) or 1.0
            nx_, ny_ = -dy / length * parallel_offset, dx / length * parallel_offset
            pa2 = (int(pa[0] + nx_), int(pa[1] + ny_))
            pb2 = (int(pb[0] + nx_), int(pb[1] + ny_))
            cv2.line(img, pa2, pb2, (40, 40, 45), line_thickness, cv2.LINE_AA)

    dot_pixels = {}
    for node in dots:
        px = to_px(node)
        cv2.circle(img, px, dot_radius, (20, 20, 25), -1, cv2.LINE_AA)
        dot_pixels[node] = px

    return img, dot_pixels


def degrade(img: np.ndarray, dot_pixels: dict, rng: random.Random) -> tuple[np.ndarray, dict]:
    h, w = img.shape[:2]
    pts = np.array(list(dot_pixels.values()), dtype=np.float32).reshape(-1, 1, 2)
    keys = list(dot_pixels.keys())

    # 1. mild rotation
    angle = rng.uniform(-8, 8)
    M_rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    img = cv2.warpAffine(img, M_rot, (w, h), borderValue=(250, 248, 245))
    pts = cv2.transform(pts, M_rot)

    # 2. mild perspective warp (phone-camera skew, not extreme keystone)
    jitter = 0.025 * w
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                       [w + rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                       [w + rng.uniform(-jitter, jitter), h + rng.uniform(-jitter, jitter)],
                       [rng.uniform(-jitter, jitter), h + rng.uniform(-jitter, jitter)]])
    M_persp = cv2.getPerspectiveTransform(src, dst)
    img = cv2.warpPerspective(img, M_persp, (w, h), borderValue=(250, 248, 245))
    pts = cv2.perspectiveTransform(pts, M_persp)

    # 3. uneven lighting (soft vignette/gradient)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = rng.uniform(0.3, 0.7) * w, rng.uniform(0.3, 0.7) * h
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (0.8 * math.hypot(w, h))
    light = np.clip(1.0 - 0.25 * dist, 0.6, 1.05)[..., None]
    img = np.clip(img.astype(np.float32) * light, 0, 255).astype(np.uint8)

    # 4. blur + noise
    img = cv2.GaussianBlur(img, (3, 3), 0.6)
    noise = np.random.normal(0, 6, img.shape).astype(np.float32)
    img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    new_dot_pixels = {k: (float(p[0][0]), float(p[0][1])) for k, p in zip(keys, pts)}
    return img, new_dot_pixels


def generate_one(csv_path: str, kolam_number: int, seed: int, out_stem: str):
    G = graph_io.load_kolam(csv_path, kolam_number)
    dots = graph_io.dots_set(G)
    scale, offset_x, offset_y = lattice_to_pixel_transform(dots)

    img, dot_pixels = render_clean(G, dots, scale, offset_x, offset_y)
    rng = random.Random(seed)
    img, dot_pixels = degrade(img, dot_pixels, rng)

    img_path = f"{OUT_DIR}/{out_stem}.jpg"
    cv2.imwrite(img_path, img, [cv2.IMWRITE_JPEG_QUALITY, 80])

    ground_truth = {
        "csv_path": csv_path,
        "kolam_number": kolam_number,
        "image_path": img_path,
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "render_scale_px_per_lattice_unit": scale,
        "edges": [[list(a), list(b)] for a, b in G.edges()],
        "dot_pixel_positions": {f"{k[0]},{k[1]}": v for k, v in dot_pixels.items()},
    }
    with open(f"{OUT_DIR}/{out_stem}.json", "w") as f:
        json.dump(ground_truth, f)

    print(f"{out_stem}: {G.number_of_nodes()} dots, {G.number_of_edges()} edges -> {img_path}")


def main():
    for i, (csv_path, kolam_number) in enumerate(PATTERNS):
        fname = csv_path.split("/")[-1].replace(".csv", "")
        stem = f"{fname}_k{kolam_number}"
        generate_one(csv_path, kolam_number, seed=1000 + i, out_stem=stem)


if __name__ == "__main__":
    main()
