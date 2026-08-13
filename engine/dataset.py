"""The single canonical loader: collection name + pattern id -> KolamPattern.

This module owns ALL CSV-specific interpretation (path resolution,
column naming, which points are dots vs. loop-around detours -- see
docs/DATA_FORMAT.md for the verified rules). It builds on
engine/graph_io.py's already-tested dot-sequence extraction and
MultiGraph construction rather than reimplementing them -- this module
adds collection-name resolution and the richer KolamPattern fields
(raw_trace, edge_multiplicity, bounding_box) on top, it does not
duplicate the core CSV-interpretation logic.

Every other module in engine/ (and every other script) should go through
load_kolam / load_dataset here rather than reading the CSVs directly.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from engine import graph_io
from engine.kolam_pattern import Edge, KolamPattern, Point

_DATA_ROOT = (
    Path(__file__).resolve().parent.parent
    / "kolam_data"
    / "Kolam CSV files"
    / "Kolam CSV files"
)

COLLECTIONS: dict[str, Path] = {
    "kolam19": _DATA_ROOT / "kolam19.csv",
    "kolam29": _DATA_ROOT / "kolam29.csv",
    "kolam109": _DATA_ROOT / "kolam109.csv",
}


def _csv_path(collection: str) -> Path:
    try:
        return COLLECTIONS[collection]
    except KeyError:
        raise ValueError(
            f"unknown collection {collection!r}; known collections: {sorted(COLLECTIONS)}"
        ) from None


def list_pattern_ids(collection: str) -> list[int]:
    """1-based pattern ids available in a collection."""
    return graph_io.list_kolam_numbers(str(_csv_path(collection)))


def load_kolam(collection: str, pattern_id: int) -> KolamPattern:
    """The single canonical entry point: collection name + 1-based pattern
    id -> a fully-populated KolamPattern. All CSV-format interpretation
    for a pattern happens here or in graph_io.py -- see docs/DATA_FORMAT.md.
    """
    path = _csv_path(collection)
    x_col, y_col = f"x-kolam {pattern_id}", f"y-kolam {pattern_id}"
    df = pd.read_csv(path, usecols=[x_col, y_col])
    x = df[x_col].dropna().astype(float).values
    y = df[y_col].dropna().astype(float).values

    raw_trace = pd.DataFrame({"x": x, "y": y}).to_numpy()
    trace_points: tuple[tuple[float, float], ...] = tuple(
        (float(px), float(py)) for px, py in raw_trace
    )

    dot_sequence: list[Point] = graph_io.extract_dot_sequence(x, y)
    dot_points: set[Point] = set(dot_sequence)

    edges: tuple[Edge, ...] = tuple(zip(dot_sequence, dot_sequence[1:]))
    edge_multiplicity: dict[frozenset, int] = dict(Counter(frozenset(e) for e in edges))

    graph = graph_io.dot_sequence_to_multigraph(dot_sequence)

    if len(raw_trace):
        min_x, min_y = raw_trace.min(axis=0)
        max_x, max_y = raw_trace.max(axis=0)
        bounding_box = (float(min_x), float(min_y), float(max_x), float(max_y))
    else:
        bounding_box = (0.0, 0.0, 0.0, 0.0)

    return KolamPattern(
        pattern_id=pattern_id,
        collection=collection,
        raw_trace=raw_trace,
        trace_points=trace_points,
        dot_points=dot_points,
        edges=edges,
        edge_multiplicity=edge_multiplicity,
        graph=graph,
        bounding_box=bounding_box,
    )


def load_dataset(collection: str) -> list[KolamPattern]:
    """Load every pattern in a collection. For kolam109 this is 100
    patterns of ~24k trace points each -- can be slow; prefer load_kolam
    for single-pattern work."""
    return [load_kolam(collection, pid) for pid in list_pattern_ids(collection)]
