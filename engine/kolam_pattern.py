"""Canonical Kolam pattern representation.

This is the single source of truth for "what is a Kolam, computationally"
-- see docs/DATA_FORMAT.md for the CSV-format evidence this is built on.
Every field here is either read directly from the source data or a
cheap, unambiguous, mechanical derivation of it (integer-coordinate
filtering, consecutive-duplicate collapsing, pairwise adjacency) -- NOT
an analysis result. Symmetry, motif structure, and validity are
deliberately NOT fields here; they are computed FROM a KolamPattern by
engine/symmetry.py, engine/motifs.py, engine/validity.py, and are cheap
enough to recompute that caching them on this object would just be a
staleness risk (the pattern doesn't change; there's nothing to
invalidate, but there's also nothing gained by baking an analysis result
into the data model).
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

Point = tuple[int, int]
TracePoint = tuple[float, float]
Edge = tuple[Point, Point]


@dataclass
class KolamPattern:
    """The canonical representation of one Kolam pattern.

    Field provenance (see docs/DATA_FORMAT.md for the verified rules
    each of these encodes):

      pattern_id, collection : identity, exactly as given to the loader
                                (1-based pattern index; collection name
                                e.g. "kolam19")
      raw_trace               : (N, 2) float64 array, EXACTLY the CSV's
                                 x/y columns for this pattern, in row
                                 order -- unmodified, kept for provenance
      trace_points             : the same N points as a tuple of (x, y)
                                 float tuples -- the canonical point
                                 sequence the rest of this object (and
                                 downstream code) actually works with.
                                 Same VALUES as raw_trace, different type
                                 (array vs. hashable point tuples) --
                                 kept as a separate field, not a derived
                                 property, so this stays a plain data
                                 container with no hidden computation.
      dot_points               : the SET of distinct integer-coordinate
                                 dot positions the stroke actually visits
                                 (dots the stroke merely loops around
                                 without touching are NOT included --
                                 see "Loop-around points" in
                                 DATA_FORMAT.md). Plain `set`, matching
                                 what engine/motifs.py's existing
                                 functions already expect.
      edges                    : every traversed edge INSTANCE, in stroke
                                 order, WITH duplicates preserved (a dot
                                 pair connected twice by two different
                                 strokes appears twice, in order)
      edge_multiplicity        : {frozenset({dot_a, dot_b}): count} --
                                 how many times each distinct dot pair
                                 was traversed. Directly derived from
                                 `edges` in one O(n) pass at load time,
                                 not a separate analysis step.
      graph                    : nx.MultiGraph, nodes = dot_points, one
                                 edge per entry in `edges` -- multiplicity
                                 is preserved exactly, never collapsed
                                 (see DATA_FORMAT.md: this is required,
                                 not a stylistic choice -- collapsing
                                 double strands corrupts vertex-degree
                                 parity and breaks Eulerian validity).
      bounding_box              : (min_x, min_y, max_x, max_y) over the
                                 FULL raw trace, including loop-around
                                 excursions -- the visual extent of the
                                 drawn curve, not just the dot lattice.
    """

    pattern_id: int
    collection: str

    raw_trace: np.ndarray
    trace_points: tuple[TracePoint, ...]
    dot_points: set[Point]

    edges: tuple[Edge, ...]
    edge_multiplicity: dict[frozenset, int]

    graph: nx.MultiGraph
    bounding_box: tuple[float, float, float, float]

    def __post_init__(self):
        if self.raw_trace.shape[0] != len(self.trace_points):
            raise ValueError(
                f"raw_trace ({self.raw_trace.shape[0]} rows) and trace_points "
                f"({len(self.trace_points)}) must have the same length"
            )
        if self.graph.number_of_nodes() and set(self.graph.nodes()) != set(self.dot_points):
            raise ValueError("graph node set must match dot_points exactly")

    @property
    def n_trace_points(self) -> int:
        return len(self.trace_points)

    @property
    def n_dots(self) -> int:
        return len(self.dot_points)

    @property
    def n_edge_instances(self) -> int:
        """Total traversed edges, WITH duplicates (matches graph.number_of_edges())."""
        return len(self.edges)

    @property
    def n_distinct_edges(self) -> int:
        """Distinct dot-pairs connected, ignoring multiplicity."""
        return len(self.edge_multiplicity)

    def __repr__(self) -> str:
        return (
            f"KolamPattern(collection={self.collection!r}, pattern_id={self.pattern_id}, "
            f"n_dots={self.n_dots}, n_distinct_edges={self.n_distinct_edges}, "
            f"n_edge_instances={self.n_edge_instances})"
        )
