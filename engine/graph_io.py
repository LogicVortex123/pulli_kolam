"""Load Kaggle 'one-stroke-dotted-pulli-kolam' CSV files into nx.MultiGraph.

Dataset format: each kolam is stored as a pair of columns
``x-kolam {n}`` / ``y-kolam {n}`` holding a dense polyline trace of the
single continuous stroke, sampled on a half-integer grid (all coordinates
are exact multiples of 0.5). Every trace is a closed loop (first point ==
last point).

Normalization convention (reverse-engineered from the raw data, see
session notes): dots ("pulli") sit at INTEGER lattice coordinates. The
traced curve visits a dot's exact coordinate whenever it passes straight
through/beside it, and loops around a dot (dipping to half-integer
offsets) without touching it when the stroke does not connect to that
dot. So:

  1. Keep only the polyline points whose (x, y) are exact integers --
     these are the dot-to-dot "visits".
  2. Collapse immediately-repeated visits (a loop that dips out and
     returns to the same dot means "no edge", not a self-loop).
  3. Each consecutive pair of *distinct* visits in the reduced sequence
     is one traversed edge between two dots.

Real data shows two dots are sometimes connected by more than one
traversal (a double strand, a genuine visual feature of kambi/sikku
kolam line art, not a data artifact -- see PULLI session notes). A plain
nx.Graph would silently collapse those into one edge and corrupt vertex
degree, which breaks the Eulerian validity gate. So the induced graph is
an nx.MultiGraph, which preserves parallel edges exactly.
"""

from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd


def _extract_dot_sequence(x: np.ndarray, y: np.ndarray) -> list[tuple[int, int]]:
    is_int = (x == np.round(x)) & (y == np.round(y))
    visited = [(int(x[i]), int(y[i])) for i in range(len(x)) if is_int[i]]
    if not visited:
        return []
    seq = [visited[0]]
    for p in visited[1:]:
        if p != seq[-1]:
            seq.append(p)
    return seq


def dot_sequence_to_multigraph(seq: list[tuple[int, int]]) -> nx.MultiGraph:
    """Build a MultiGraph from a reduced dot-visit sequence.

    Nodes are exactly the dots that appear in the sequence; edges are the
    consecutive dot-to-dot traversals, with multiplicity preserved.
    """
    G = nx.MultiGraph()
    G.add_nodes_from(seq)
    for a, b in zip(seq, seq[1:]):
        G.add_edge(a, b)
    return G


def load_kolam(csv_path: str, kolam_number: int) -> nx.MultiGraph:
    """Load a single kolam pattern from a Kaggle-format CSV as a MultiGraph."""
    df = pd.read_csv(csv_path)
    x = df[f"x-kolam {kolam_number}"].dropna().astype(float).values
    y = df[f"y-kolam {kolam_number}"].dropna().astype(float).values
    seq = _extract_dot_sequence(x, y)
    return dot_sequence_to_multigraph(seq)


def list_kolam_numbers(csv_path: str) -> list[int]:
    """Return the kolam indices available in a Kaggle-format CSV file."""
    df = pd.read_csv(csv_path, nrows=0)
    numbers = set()
    for col in df.columns:
        if col.startswith("x-kolam "):
            numbers.add(int(col.removeprefix("x-kolam ")))
    return sorted(numbers)


def dots_set(G: nx.MultiGraph) -> set[tuple[int, int]]:
    return set(G.nodes())
