"""Regenerate a graph by stamping a motif at a set of points.

Used both for self-consistency verification (stamp the induced motif back
onto the same dot set and diff against the original) and for generative
extension (stamp the same motif onto a new/larger dot lattice to produce
a novel pattern from the same rule).
"""

from __future__ import annotations

import networkx as nx

from engine.motifs import Motif
from engine.symmetry import apply_transform


def apply_motif(
    motif: Motif,
    nodes: "set[tuple[int, int]] | list[tuple[int, int]]",
    points: "list[tuple[int, int]] | set[tuple[int, int]]",
    transforms: "dict[tuple[int, int], str] | None" = None,
) -> nx.MultiGraph:
    """Regenerate a MultiGraph by translating (and optionally rotating /
    reflecting, per `transforms`) `motif` onto every point in `points`.

    `nodes` is the full node set of the target lattice (arbitrary shape,
    not necessarily a square grid) -- edges landing outside it are dropped.
    `transforms` maps a subset of `points` to a D4 transform name (see
    engine.symmetry.D4_TRANSFORMS); points absent from it are stamped with
    a plain translation (identity transform).
    """
    G = nx.MultiGraph()
    node_set = set(nodes)
    G.add_nodes_from(node_set)

    for cx, cy in points:
        t_name = transforms.get((cx, cy), "identity") if transforms else "identity"
        edges = motif if t_name == "identity" else apply_transform(t_name, motif)
        for (dx1, dy1), (dx2, dy2) in edges:
            a = (cx + dx1, cy + dy1)
            b = (cx + dx2, cy + dy2)
            if a in node_set and b in node_set:
                G.add_edge(a, b)
    return G
