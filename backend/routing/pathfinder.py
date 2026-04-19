"""Single-segment shortest path on the trail graph, plus path metrics.

A\\* with great-circle (haversine) distance as the heuristic. Haversine is
admissible because trail distance is always >= straight-line distance on the
earth's surface, so A\\* is guaranteed to find the optimal path without over-
exploration — the same guarantee Dijkstra gives, but with fewer expansions on
a graph this geographically spread out.
"""
from __future__ import annotations

import math

import networkx as nx

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(graph, u, v) -> float:
    """Great-circle distance in meters between two graph nodes."""
    ux, uy = graph.nodes[u]["x"], graph.nodes[u]["y"]
    vx, vy = graph.nodes[v]["x"], graph.nodes[v]["y"]
    phi1, phi2 = math.radians(uy), math.radians(vy)
    dphi = math.radians(vy - uy)
    dlam = math.radians(vx - ux)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def shortest_path(graph, source, target) -> list[int]:
    """A* shortest path by edge length. Returns the sequence of node ids."""
    def heuristic(u, v):
        return haversine_m(graph, u, v)
    return nx.astar_path(graph, source, target, heuristic=heuristic, weight="length")


def path_length_m(graph, path: list[int]) -> float:
    """Sum of minimum parallel-edge lengths along a node path."""
    total = 0.0
    for u, v in zip(path[:-1], path[1:]):
        edges = graph.get_edge_data(u, v)
        if edges is None:
            return float("inf")
        total += min(d.get("length", 0.0) for d in edges.values())
    return total


def path_elevation_gain_m(graph, path: list[int]) -> float:
    """Cumulative ascent along a node path — descent is not subtracted."""
    gain = 0.0
    for u, v in zip(path[:-1], path[1:]):
        eu = graph.nodes[u].get("elevation")
        ev = graph.nodes[v].get("elevation")
        if eu is None or ev is None:
            continue
        if ev > eu:
            gain += ev - eu
    return gain
