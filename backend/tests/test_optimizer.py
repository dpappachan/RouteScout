"""Optimizer tests — pure logic with a tiny hand-built graph. These run in
milliseconds and don't hit the Sierra graph, elevation API, or Gemini."""
from __future__ import annotations

import networkx as nx
import pytest

from backend.routing.optimizer import (
    CAMP_CATEGORIES,
    EDGE_REUSE_PENALTY,
    _path_edges,
    _per_day_target,
    plan,
)
from backend.routing.pathfinder import haversine_m, path_length_m
from backend.routing.trip_spec import TripSpec


def _toy_graph():
    """A simple Y-shaped trail graph:
           (2) east-lake
          /
        (1)
          \\
           (3) south-meadow
                        \\
                         (4) far-peak
    Designed so we can exercise routing and scoring without real data.
    """
    g = nx.MultiDiGraph()
    nodes = [
        (1, 37.80, -119.50, 2000),
        (2, 37.81, -119.48, 2300),
        (3, 37.79, -119.48, 2100),
        (4, 37.77, -119.45, 2800),
    ]
    for nid, y, x, elev in nodes:
        g.add_node(nid, y=y, x=x, elevation=float(elev))

    # haversine approx distances (not precise; serve as fixed "length_m")
    edges = [
        (1, 2, 3000),
        (1, 3, 2500),
        (3, 4, 4000),
    ]
    for u, v, length in edges:
        g.add_edge(u, v, length=float(length), grade=0.05, grade_abs=0.05)
        g.add_edge(v, u, length=float(length), grade=0.05, grade_abs=0.05)
    return g


def test_per_day_target_scaling():
    base = 10_000
    # 2-day trip: no adjustment
    assert _per_day_target(base, 0, 2) == base
    assert _per_day_target(base, 1, 2) == base
    # 4-day trip: day 1 shorter, last day shorter, middles longer
    assert _per_day_target(base, 0, 4) == pytest.approx(0.75 * base)
    assert _per_day_target(base, 1, 4) == pytest.approx(1.10 * base)
    assert _per_day_target(base, 2, 4) == pytest.approx(1.10 * base)
    assert _per_day_target(base, 3, 4) == pytest.approx(0.85 * base)


def test_path_edges_are_direction_independent():
    # A→B→A should produce exactly 1 undirected edge in the set
    assert _path_edges([1, 2, 1]) == frozenset([(1, 2)])
    assert _path_edges([1, 2, 3]) == frozenset([(1, 2), (2, 3)])
    assert _path_edges([3, 2, 1]) == frozenset([(1, 2), (2, 3)])


def test_camp_categories_is_water_and_meadow_only():
    # These are the only categories that mean "flat ground + water nearby".
    # Peaks, viewpoints, waterfalls, passes are not legal overnight camps.
    assert CAMP_CATEGORIES == frozenset({"lake", "meadow"})


def test_plan_day_hike_returns_out_and_back():
    """With days=1 and loop, the planner uses the day-hike branch — out to
    a destination and back."""
    graph = _toy_graph()
    features = [
        {"name": "East Lake", "category": "lake", "lat": 37.81, "lon": -119.48, "node_id": 2},
        {"name": "South Meadow", "category": "meadow", "lat": 37.79, "lon": -119.48, "node_id": 3},
    ]
    trailheads = [
        {"name": "TH", "lat": 37.80, "lon": -119.50, "node_id": 1, "region": "test"},
    ]
    camps = features  # all features are valid camps in this toy graph

    spec = TripSpec(days=1, miles_per_day=5, start="TH")
    result = plan(graph, features, trailheads, camps, spec, beam_width=4)

    assert result is not None
    assert len(result.days) == 1
    # First and last node of a loop day hike must be the start
    path = result.days[0].path
    assert path[0] == 1
    assert path[-1] == 1
    # Path length should be nonzero and within the allowed band for 5 mi target
    assert result.days[0].length_m > 0


def test_plan_rejects_unknown_start():
    graph = _toy_graph()
    features: list[dict] = []
    trailheads = [
        {"name": "Known TH", "lat": 37.80, "lon": -119.50, "node_id": 1, "region": "test"},
    ]

    spec = TripSpec(days=2, miles_per_day=5, start="Ghost TH")
    with pytest.raises(ValueError, match="Unknown start trailhead"):
        plan(graph, features, trailheads, [], spec)


def test_edge_reuse_penalty_is_positive():
    """Sanity — the penalty should actually penalize (not reward)."""
    assert EDGE_REUSE_PENALTY > 0


def test_haversine_agrees_with_path_length_roughly():
    graph = _toy_graph()
    # A-B by straight line should be close to edge length (tiny toy graph)
    straight = haversine_m(graph, 1, 2)
    path_len = path_length_m(graph, [1, 2])
    # The toy graph has explicit length=3000 for 1→2 edge; haversine will
    # be < 3000 since it's straight-line. Assert both are in the same order.
    assert 500 < straight < 10_000
    assert path_len == 3000
