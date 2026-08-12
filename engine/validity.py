"""Hard correctness gates: exact self-reconstruction and single-stroke validity.

Both checks are deterministic graph theory, not scored/fuzzy metrics --
check_validity in particular is the formal definition of a classical
single-stroke (ekarekha) Kolam: the largest connected component must be
Eulerian (closed loop) or have an Eulerian path (open single stroke).
This must never be softened; a pattern either satisfies it or it doesn't.
"""

from __future__ import annotations

from collections import Counter

import networkx as nx


def check_self_consistency(G_original: nx.MultiGraph, G_regenerated: nx.MultiGraph) -> bool:
    """Hard correctness check: edge multisets must match EXACTLY, including
    multiplicity (a regenerated single strand where the original had a
    double strand is NOT a match)."""
    e1 = Counter(frozenset(e) for e in G_original.edges())
    e2 = Counter(frozenset(e) for e in G_regenerated.edges())
    return e1 == e2


def check_validity(G: nx.MultiGraph) -> dict:
    largest = max(nx.connected_components(G), key=len)
    Gc = G.subgraph(largest)
    return {
        "connected_components": nx.number_connected_components(G),
        "is_eulerian_circuit": nx.is_eulerian(Gc),
        "has_eulerian_path": nx.has_eulerian_path(Gc),
        "largest_component_covers_all_nodes": len(largest) == G.number_of_nodes(),
    }


def is_valid_single_stroke(G: nx.MultiGraph) -> bool:
    """The single boolean hard gate: is `G` a valid ekarekha Kolam?"""
    result = check_validity(G)
    return (
        result["largest_component_covers_all_nodes"]
        and (result["is_eulerian_circuit"] or result["has_eulerian_path"])
    )
