"""Compute overnight camp candidates from terrain + water proximity.

A good backpacker camp needs (a) flat-enough ground to set up a tent and
(b) a water source within walking distance for cooking. Rather than
hand-picking features tagged 'lake' or 'meadow', we derive campability
from the graph's actual geometry: a node is a camp candidate if its
local slope (computed from edge grades — already on every edge from the
graph-build phase) is below a backpacker-reasonable threshold AND it
sits within a short distance of a curated water feature.

This produces a richer set of candidates than the category filter and
it's demonstrably derived from real data, which is the interview story.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from .build import DATA_DIR, build
from .features import FEATURES_PATH

CAMPS_CACHE = DATA_DIR / "sierra_camps.json"

# Local slope threshold for a tent-able node. 10% (rise/run) is about the
# steepest you'd want to sleep on; above 15% you'll roll downhill in the
# night. We're conservative on the hiker's side.
MAX_LOCAL_GRADE = 0.10

# How close to water a camp must be. Backpackers routinely walk 5–10
# minutes to fetch water from a lake, which is roughly 500–700m.
MAX_WATER_DISTANCE_M = 700

WATER_CATEGORIES = frozenset({"lake"})

# Yosemite Wilderness rules: no camping within 4 trail-miles of these
# developed areas (we approximate with straight-line buffer in meters).
# This is a real NPS regulation, not arbitrary — the corridors around
# Yosemite Valley, Tuolumne Meadows, Wawona, and Crane Flat are designated
# day-use only for backpackers entering or leaving the wilderness.
# Source: Yosemite Wilderness Permit and Trip Planner.
DEVELOPED_AREA_BUFFERS = [
    # name, lat, lon, buffer in meters (~4 trail-mi straight-line approximation)
    ("Yosemite Valley", 37.7459, -119.5936, 6500),
    ("Tuolumne Meadows", 37.8755, -119.3399, 4000),
    ("Wawona",           37.5379, -119.6533, 3000),
    ("Crane Flat",       37.7575, -119.7993, 3000),
]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _max_local_grade(graph, node) -> float:
    """Largest |grade| across all edges touching this node. OSMnx stores
    `grade` and `grade_abs` on edges after add_edge_grades."""
    max_g = 0.0
    for nbr in graph.neighbors(node):
        edges = graph.get_edge_data(node, nbr) or {}
        for data in edges.values():
            g = data.get("grade_abs")
            if g is None:
                g = abs(data.get("grade") or 0.0)
            if g > max_g:
                max_g = g
    return max_g


def _in_developed_area(lat: float, lon: float) -> str | None:
    """Returns the name of the developed area containing this point, or None
    if it's clear of all of them."""
    for name, ar_lat, ar_lon, buffer_m in DEVELOPED_AREA_BUFFERS:
        if _haversine_m(lat, lon, ar_lat, ar_lon) < buffer_m:
            return name
    return None


def compute_camps(graph, features: list[dict]) -> list[dict]:
    """Return all trail-graph nodes that pass the terrain + water proximity
    test AND aren't inside an NPS developed-area exclusion zone.
    """
    water_features = [f for f in features if f["category"] in WATER_CATEGORIES]

    camps: list[dict] = []
    seen_nodes: set[int] = set()

    for node_id, data in graph.nodes(data=True):
        if _max_local_grade(graph, node_id) > MAX_LOCAL_GRADE:
            continue

        node_lat, node_lon = data["y"], data["x"]

        # NPS no-camp zones (Yosemite Valley, Tuolumne Meadows, etc.)
        if _in_developed_area(node_lat, node_lon):
            continue

        # nearest water feature
        best_water: dict | None = None
        best_dist = float("inf")
        for w in water_features:
            d = _haversine_m(node_lat, node_lon, w["lat"], w["lon"])
            if d < best_dist:
                best_dist = d
                best_water = w
        if best_water is None or best_dist > MAX_WATER_DISTANCE_M:
            continue

        if node_id in seen_nodes:
            continue
        seen_nodes.add(node_id)

        # Human-readable camp name: use the water feature's name, with a
        # "near" prefix when the node isn't right at it.
        name = (
            best_water["name"]
            if best_dist < 60
            else f"near {best_water['name']}"
        )

        camps.append({
            "name": name,
            "node_id": int(node_id),
            "lat": round(node_lat, 6),
            "lon": round(node_lon, 6),
            "category": best_water["category"],
            "near_water": best_water["name"],
            "water_distance_m": round(best_dist, 1),
            "local_grade": round(_max_local_grade(graph, node_id), 3),
        })

    return camps


def build_camps(force: bool = False) -> list[dict]:
    if CAMPS_CACHE.exists() and not force:
        return json.loads(CAMPS_CACHE.read_text())
    graph = build()
    features = json.loads(FEATURES_PATH.read_text())
    camps = compute_camps(graph, features)
    CAMPS_CACHE.write_text(json.dumps(camps, indent=2))
    return camps


@lru_cache(maxsize=1)
def camps() -> list[dict]:
    return build_camps()


if __name__ == "__main__":
    result = build_camps(force=True)
    from collections import Counter
    cats = Counter(c["near_water"] for c in result)
    print(f"Total camp candidates: {len(result)}")
    print("Top water features by # of flat camp spots within reach:")
    for water, n in cats.most_common(12):
        print(f"  {water:30}  {n}")
