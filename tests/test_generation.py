from engine.generation import apply_motif


def edge_set(G):
    return {frozenset(e) for e in G.edges()}


def test_apply_motif_stamps_translated_edges():
    nodes = {(i, j) for i in range(5) for j in range(5)}
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [(0, 0), (2, 2)])
    assert edge_set(G) == {frozenset({(0, 0), (1, 0)}), frozenset({(2, 2), (3, 2)})}


def test_apply_motif_drops_edges_outside_node_set():
    nodes = {(0, 0), (1, 0)}  # (2, 0) deliberately absent
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [(0, 0), (1, 0)])
    # stamp at (1,0) would need node (2,0), which doesn't exist -> dropped
    assert edge_set(G) == {frozenset({(0, 0), (1, 0)})}


def test_apply_motif_respects_per_point_transform():
    nodes = {(i, j) for i in range(-3, 4) for j in range(-3, 4)}
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [(0, 0)], transforms={(0, 0): "rot90"})
    # rot90: (x,y) -> (-y,x); (1,0) -> (0,1)
    assert edge_set(G) == {frozenset({(0, 0), (0, 1)})}


def test_apply_motif_preserves_multiplicity():
    nodes = {(0, 0), (1, 0)}
    motif = (((0, 0), (1, 0)), ((0, 0), (1, 0)))  # double strand
    G = apply_motif(motif, nodes, [(0, 0)])
    assert G.number_of_edges() == 2
    assert [frozenset(e) for e in G.edges()] == [frozenset({(0, 0), (1, 0)})] * 2


def test_apply_motif_on_empty_points_yields_no_edges():
    nodes = {(0, 0), (1, 0)}
    motif = (((0, 0), (1, 0)),)
    G = apply_motif(motif, nodes, [])
    assert G.number_of_edges() == 0
    assert set(G.nodes()) == nodes
