"""Hard correctness gates: exact self-reconstruction and single-stroke validity.

Both checks are deterministic graph theory, not scored/fuzzy metrics --
check_validity in particular is the formal definition of a classical
single-stroke (ekarekha) Kolam: the largest connected component must be
Eulerian (closed loop) or have an Eulerian path (open single stroke).
This must never be softened; a pattern either satisfies it or it doesn't.
"""

from __future__ import annotations

from collections import Counter
from typing import Union

import networkx as nx

from engine.kolam_pattern import KolamPattern

GraphLike = Union[nx.MultiGraph, KolamPattern]


def _as_graph(G: GraphLike) -> nx.MultiGraph:
    """Every public function here accepts either a raw nx.MultiGraph
    (existing behavior, unchanged) or a KolamPattern (its .graph field is
    used) -- so check_validity(pattern) works exactly like
    check_validity(pattern.graph) without every caller needing to know
    which one they have."""
    return G.graph if isinstance(G, KolamPattern) else G


def check_self_consistency(G_original: GraphLike, G_regenerated: GraphLike) -> bool:
    """Hard correctness check: edge multisets must match EXACTLY, including
    multiplicity (a regenerated single strand where the original had a
    double strand is NOT a match)."""
    G_original = _as_graph(G_original)
    G_regenerated = _as_graph(G_regenerated)
    e1 = Counter(frozenset(e) for e in G_original.edges())
    e2 = Counter(frozenset(e) for e in G_regenerated.edges())
    return e1 == e2


def check_validity(G: GraphLike) -> dict:
    G = _as_graph(G)
    largest = max(nx.connected_components(G), key=len)
    Gc = G.subgraph(largest)
    return {
        "connected_components": nx.number_connected_components(G),
        "is_eulerian_circuit": nx.is_eulerian(Gc),
        "has_eulerian_path": nx.has_eulerian_path(Gc),
        "largest_component_covers_all_nodes": len(largest) == G.number_of_nodes(),
    }


def is_valid_single_stroke(G: GraphLike) -> bool:
    """The single boolean hard gate: is `G` a valid ekarekha Kolam?"""
    result = check_validity(G)
    return (
        result["largest_component_covers_all_nodes"]
        and (result["is_eulerian_circuit"] or result["has_eulerian_path"])
    )


def diagnose_validity(G: GraphLike) -> dict:
    """Companion to check_validity, NOT a replacement: check_validity stays
    a hard, unmodified pass/fail gate for CSV-sourced data, where the
    dataset is described as already-verified single-stroke and a failure
    means a bug in our code, not the data (see engine/validity.py module
    docstring and PULLI session notes).

    Image-derived graphs are different: detection noise means near-misses
    are expected and common, and "fails the strict gate" doesn't say
    whether that's 1 stray edge or the graph is structurally garbage. This
    gives a graded, explainable answer instead: which vertices have the
    wrong (odd) degree, the minimum-cost pairing between them (standard
    Route Inspection / Chinese Postman correction -- pair odd-degree
    vertices via shortest-path distance, minimum total weight), and
    exactly which nodes/edges each correction touches. `n_corrections`
    small and localized is evidence the reconstruction is fundamentally
    sound; large or sprawling is evidence it genuinely isn't -- this
    function reports which, it does not decide "valid" for you.

    Corrections are computed on the LARGEST connected component only
    (matching check_validity's own convention) -- shortest-path pairing
    only makes sense within one component. Disconnection itself (nodes
    outside the largest component) is a separate problem this doesn't
    fix, reported separately in the returned dict.
    """
    G = _as_graph(G)
    validity = check_validity(G)
    largest = max(nx.connected_components(G), key=len)
    Gc = G.subgraph(largest)

    odd_nodes = [n for n, d in Gc.degree() if d % 2 == 1]

    corrections = []
    if odd_nodes:
        H = nx.Graph()
        H.add_nodes_from(odd_nodes)
        for i, u in enumerate(odd_nodes):
            for v in odd_nodes[i + 1 :]:
                H.add_edge(u, v, weight=nx.shortest_path_length(Gc, u, v))
        matching = nx.min_weight_matching(H, weight="weight")
        for u, v in matching:
            path = nx.shortest_path(Gc, u, v)
            path_edges = list(zip(path, path[1:]))
            corrections.append(
                {
                    "pair": (u, v),
                    "path": path,
                    "path_edges": path_edges,
                    "cost": len(path_edges),
                }
            )

    return {
        "is_valid": (
            validity["largest_component_covers_all_nodes"]
            and (validity["is_eulerian_circuit"] or validity["has_eulerian_path"])
        ),
        "connected_components": validity["connected_components"],
        "n_nodes_outside_largest_component": G.number_of_nodes() - len(largest),
        "n_odd_degree_nodes": len(odd_nodes),
        "odd_degree_nodes": odd_nodes,
        "n_corrections": len(corrections),
        "corrections": corrections,
        "total_correction_cost": sum(c["cost"] for c in corrections),
    }
