"""Pathfinder tests — haversine heuristic + path metrics."""
import math

import networkx as nx
import pytest

from backend.routing.pathfinder import (
    haversine_m,
    path_elevation_gain_m,
    path_length_m,
    shortest_path,
)


def _line_graph():
    """4 nodes in a straight line: 1 → 2 → 3 → 4"""
    g = nx.MultiDiGraph()
    nodes = [
        (1, 37.0, -119.0, 2000),
        (2, 37.01, -119.0, 2200),
        (3, 37.02, -119.0, 2100),
        (4, 37.03, -119.0, 2500),
    ]
    for nid, y, x, elev in nodes:
        g.add_node(nid, y=y, x=x, elevation=float(elev))
    for u, v, length in [(1, 2, 1000), (2, 3, 1000), (3, 4, 1000)]:
        g.add_edge(u, v, length=float(length))
        g.add_edge(v, u, length=float(length))
    return g


def test_haversine_symmetric():
    g = _line_graph()
    assert abs(haversine_m(g, 1, 4) - haversine_m(g, 4, 1)) < 1e-6


def test_haversine_scale():
    g = _line_graph()
    # 0.01 deg lat ≈ 1.11 km
    d = haversine_m(g, 1, 2)
    assert 1000 < d < 1200


def test_haversine_same_node_is_zero():
    g = _line_graph()
    assert haversine_m(g, 1, 1) == 0.0


def test_shortest_path_trivial_end_to_end():
    g = _line_graph()
    path = shortest_path(g, 1, 4)
    assert path == [1, 2, 3, 4]


def test_path_length_m_sums_correctly():
    g = _line_graph()
    assert path_length_m(g, [1, 2, 3, 4]) == 3000


def test_path_length_m_infinity_for_disconnected_hop():
    g = _line_graph()
    g.add_node(99, y=38.0, x=-120.0, elevation=3000.0)
    # no edge — path_length_m should return inf
    assert math.isinf(path_length_m(g, [1, 99]))


def test_elevation_gain_only_counts_ascent():
    """Descents are not subtracted — we want total climb, not net."""
    g = _line_graph()
    # 1(2000) → 2(2200) → 3(2100) → 4(2500)
    # ascents: +200 (1→2), +400 (3→4) = 600. 2→3 is descent, not counted.
    gain = path_elevation_gain_m(g, [1, 2, 3, 4])
    assert gain == pytest.approx(600)
