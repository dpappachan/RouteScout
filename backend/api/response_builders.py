"""Build the public PlanResponse from the planner's internal Itinerary.

Two responsibilities:
  · Reconstruct a detailed map polyline from each edge's OSM `geometry`
    (so the routed line on the map traces the trail's curves, not straight
    lines between simplified graph nodes).
  · Build a node-resolution elevation series with cumulative miles for the
    elevation chart's x-axis.
"""
from __future__ import annotations

import math
from typing import Iterable

from backend.routing.trip_spec import Itinerary

from .models import DayPlan, ElevationPoint, FeatureInfo


def build_day_plans(graph, itinerary: Itinerary) -> list[DayPlan]:
    """Convert each internal DaySegment into the API's DayPlan model."""
    out: list[DayPlan] = []
    for day in itinerary.days:
        camp = graph.nodes[day.camp_node]
        out.append(
            DayPlan(
                day=day.day_index + 1,
                length_miles=round(day.length_miles, 2),
                gain_m=int(day.gain_m),
                camp_name=day.camp_name,
                camp_lat=camp["y"],
                camp_lon=camp["x"],
                path_coords=detailed_polyline(graph, day.path),
                elevation_series=elevation_series(graph, day.path),
                features_passed=[
                    FeatureInfo(
                        name=f["name"], category=f["category"],
                        lat=f["lat"], lon=f["lon"],
                    )
                    for f in day.features_passed
                ],
            )
        )
    return out


def detailed_polyline(graph, path: list[int]) -> list[tuple[float, float]]:
    """Polyline that follows each OSM edge's `geometry` LineString.

    OSMnx stores simplified graphs where each *graph edge* is a single
    abstraction over potentially many real-world OSM nodes; the full
    geometry lives in the `geometry` attribute as a Shapely LineString.
    Without unpacking it, the rendered route looks like a zigzag of
    straight chords on top of a squiggly trail. With it, the line
    traces the trail.
    """
    coords: list[tuple[float, float]] = []
    for idx, (u, v) in enumerate(zip(path[:-1], path[1:])):
        edges = graph.get_edge_data(u, v) or {}
        # multiple parallel edges may exist; pick the shortest
        edge = min(
            edges.values(),
            key=lambda d: d.get("length", float("inf")),
            default=None,
        )
        geom = edge.get("geometry") if edge else None

        if geom is not None:
            segment = [(lat, lon) for lon, lat in geom.coords]
            # edges aren't oriented — flip if the LineString starts at v not u
            u_lat, u_lon = graph.nodes[u]["y"], graph.nodes[u]["x"]
            if segment and _haversine_m(segment[-1], (u_lat, u_lon)) < \
                           _haversine_m(segment[0], (u_lat, u_lon)):
                segment = list(reversed(segment))
        else:
            # straight chord between graph nodes when no geometry is stored
            segment = [
                (graph.nodes[u]["y"], graph.nodes[u]["x"]),
                (graph.nodes[v]["y"], graph.nodes[v]["x"]),
            ]

        if idx == 0:
            coords.extend(segment)
        else:
            # avoid duplicating the joining vertex between consecutive segments
            coords.extend(segment[1:])

    return [(round(lat, 6), round(lon, 6)) for lat, lon in coords]


def elevation_series(graph, path: list[int]) -> list[ElevationPoint]:
    """Per-graph-node elevation samples with cumulative trail-miles for the x-axis."""
    series: list[ElevationPoint] = []
    miles = 0.0
    for i, node in enumerate(path):
        if i > 0:
            edges = graph.get_edge_data(path[i - 1], node) or {}
            length_m = (
                min((d.get("length", 0.0) for d in edges.values()), default=0.0)
                if edges else 0.0
            )
            miles += length_m / 1609.344
        elev = float(graph.nodes[node].get("elevation") or 0.0)
        series.append(ElevationPoint(miles=round(miles, 3), elevation_m=round(elev, 1)))
    return series


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    R = 6_371_000.0
    lat1, lon1 = a
    lat2, lon2 = b
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def estimate_daily_hours(itinerary: Itinerary) -> list[float]:
    """Naismith's rule (lightly tuned): ~3 km/h on flat trail, plus 30 min
    per 300 m of cumulative ascent. Standard backpacking pace estimate."""
    return [
        round((day.length_m / 1000.0) / 3.0 + (day.gain_m / 300.0) * 0.5, 1)
        for day in itinerary.days
    ]


def difficulty_label(itinerary: Itinerary) -> str:
    """Difficulty label from average daily mileage + cumulative ascent.
    Loose bands aimed at a reasonably-fit backpacker."""
    if not itinerary.days:
        return "moderate"
    avg_mi = itinerary.total_length_miles / len(itinerary.days)
    avg_gain = itinerary.total_gain_m / len(itinerary.days)
    if avg_mi < 6 and avg_gain < 350:
        return "easy"
    if avg_mi < 10 and avg_gain < 700:
        return "moderate"
    if avg_mi < 14 and avg_gain < 1100:
        return "strenuous"
    return "very strenuous"


def max_elevation_on_route(graph, itinerary: Itinerary) -> float:
    """Highest node elevation visited across all days of the trip."""
    max_e = 0.0
    nodes: Iterable[int] = (n for d in itinerary.days for n in d.path)
    for n in nodes:
        elev = graph.nodes[n].get("elevation")
        if elev and elev > max_e:
            max_e = float(elev)
    return max_e
