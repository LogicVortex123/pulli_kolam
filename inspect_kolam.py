"""Debugging tool for the canonical KolamPattern data model.

    python inspect_kolam.py --collection kolam19 --pattern 26

Prints a concise report of every canonical field, plus the first/last
few trace points, so a KolamPattern can be sanity-checked by eye without
dropping into a REPL.
"""

from __future__ import annotations

import argparse

from engine.dataset import load_kolam

N_PREVIEW = 5


def main():
    parser = argparse.ArgumentParser(description="Inspect a canonical KolamPattern.")
    parser.add_argument("--collection", required=True, help="kolam19 | kolam29 | kolam109")
    parser.add_argument("--pattern", required=True, type=int, help="1-based pattern id")
    args = parser.parse_args()

    pattern = load_kolam(args.collection, args.pattern)

    n_repeated_pairs = sum(1 for v in pattern.edge_multiplicity.values() if v > 1)
    min_x, min_y, max_x, max_y = pattern.bounding_box

    print(f"Collection:          {pattern.collection}")
    print(f"Pattern:              {pattern.pattern_id}")
    print()
    print(f"Raw trace points:     {pattern.raw_trace.shape[0]}")
    print(f"Trace points:         {pattern.n_trace_points}")
    print(f"Dot points:           {pattern.n_dots}")
    print(f"Unique edges:         {pattern.n_distinct_edges}")
    print(f"Total edge strands:   {pattern.n_edge_instances}")
    print(f"Repeated edges:       {n_repeated_pairs}")
    print(f"Bounding box:         ({min_x}, {min_y}) -> ({max_x}, {max_y})")
    print()
    print(f"Graph nodes:          {pattern.graph.number_of_nodes()}")
    print(f"Graph edges:          {pattern.graph.number_of_edges()}")
    print()

    n = len(pattern.trace_points)
    head = pattern.trace_points[: min(N_PREVIEW, n)]
    tail = pattern.trace_points[max(0, n - N_PREVIEW) :]
    print(f"First {len(head)} trace points:")
    for i, (x, y) in enumerate(head):
        print(f"  [{i}] ({x}, {y})")
    print(f"Last {len(tail)} trace points:")
    for i, (x, y) in zip(range(n - len(tail), n), tail):
        print(f"  [{i}] ({x}, {y})")


if __name__ == "__main__":
    main()
