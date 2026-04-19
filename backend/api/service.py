"""Orchestration layer: prompt → parsed spec → itinerary → narrative → response.

Kept separate from the HTTP handler so the same code path is easy to unit test
without spinning up a TestClient.
"""
from __future__ import annotations

import logging
import time

from backend.llm.narrator import narrate
from backend.llm.parser import ParsedTripSpec, parse
from backend.routing.optimizer import plan
from backend.routing.trip_spec import Itinerary, TripSpec

from .models import DayPlan, ElevationPoint, FeatureInfo, ParsedSpec, PlanResponse
from .state import STATE

log = logging.getLogger("routescout.service")


class PlannerError(Exception):
    """Raised when the request can't be satisfied — e.g., no feasible itinerary."""


def plan_from_prompt(prompt: str, *, beam_width: int) -> PlanResponse:
    timings: dict[str, float] = {}

    log.info("planning: %r", prompt)

    t0 = time.perf_counter()
    parsed_spec = parse(prompt, STATE.features, STATE.trailheads)
    timings["parse"] = round(time.perf_counter() - t0, 3)
    log.info(
        "parsed start=%s days=%s miles/day=%s categories=%s",
        parsed_spec.start, parsed_spec.days, parsed_spec.miles_per_day,
        parsed_spec.preferred_categories,
    )

    spec = _to_trip_spec(parsed_spec)

    t0 = time.perf_counter()
    itinerary = plan(STATE.graph, STATE.features, STATE.trailheads, spec, beam_width=beam_width)
    timings["plan"] = round(time.perf_counter() - t0, 3)

    if itinerary is None:
        raise PlannerError(
            f"I couldn't fit a {parsed_spec.days}-day trip at "
            f"{parsed_spec.miles_per_day:g} miles/day starting from "
            f"{parsed_spec.start} — the trail geometry near that start node "
            "doesn't allow a route of that length to close. Try a shorter "
            "trip, a different start (Tuolumne Pass and Lembert Dome have "
            "richer surrounding trail networks than Glacier Point), or fewer "
            "miles per day."
        )

    log.info(
        "planned %d days, %.1f mi, %d m gain, score %.2f",
        len(itinerary.days), itinerary.total_length_miles,
        int(itinerary.total_gain_m), itinerary.score,
    )

    t0 = time.perf_counter()
    narrative = narrate(itinerary, spec, prompt)
    timings["narrate"] = round(time.perf_counter() - t0, 3)

    return _build_response(prompt, parsed_spec, spec, itinerary, narrative, timings)


def _detailed_polyline(graph, path: list[int]) -> list[tuple[float, float]]:
    """Build a polyline that follows the full OSM geometry of each edge, not
    just the straight line between graph nodes.

    OSMnx stores simplified graphs with `geometry` LineStrings on edges that
    curve. Without this, the routed line looks like zigzag abstract art on top
    of a squiggly real trail; with this, the line traces the trail exactly.
    """
    coords: list[tuple[float, float]] = []
    for idx, (u, v) in enumerate(zip(path[:-1], path[1:])):
        edges = graph.get_edge_data(u, v) or {}
        # pick the shortest parallel edge between u and v
        edge = min(edges.values(), key=lambda d: d.get("length", float("inf")), default=None)
        geom = edge.get("geometry") if edge else None

        if geom is not None:
            segment = [(lat, lon) for lon, lat in geom.coords]
            # edges can be oriented either direction — flip if the first
            # point isn't at u's coordinates
            u_lat, u_lon = graph.nodes[u]["y"], graph.nodes[u]["x"]
            if segment and _haversine_m_coords(segment[-1], (u_lat, u_lon)) < \
               _haversine_m_coords(segment[0], (u_lat, u_lon)):
                segment = list(reversed(segment))
        else:
            segment = [
                (graph.nodes[u]["y"], graph.nodes[u]["x"]),
                (graph.nodes[v]["y"], graph.nodes[v]["x"]),
            ]

        if idx == 0:
            coords.extend(segment)
        else:
            # skip the first vertex of each subsequent segment to avoid dup
            coords.extend(segment[1:])
    return [(round(lat, 6), round(lon, 6)) for lat, lon in coords]


def _elevation_series(graph, path: list[int]) -> list[ElevationPoint]:
    """Node-resolution elevation series with cumulative miles for the x-axis."""
    series: list[ElevationPoint] = []
    miles = 0.0
    for i, node in enumerate(path):
        if i > 0:
            prev = path[i - 1]
            edges = graph.get_edge_data(prev, node) or {}
            length_m = min(
                (d.get("length", 0.0) for d in edges.values()), default=0.0
            ) if edges else 0.0
            miles += length_m / 1609.344
        elev = float(graph.nodes[node].get("elevation") or 0.0)
        series.append(ElevationPoint(miles=round(miles, 3), elevation_m=round(elev, 1)))
    return series


def _haversine_m_coords(a: tuple[float, float], b: tuple[float, float]) -> float:
    import math
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _to_trip_spec(parsed: ParsedTripSpec) -> TripSpec:
    return TripSpec(
        days=parsed.days,
        miles_per_day=parsed.miles_per_day,
        start=parsed.start,
        end=parsed.end,
        preferred_categories=tuple(parsed.preferred_categories),
        named_must_visit=tuple(parsed.named_must_visit),
    )


def _build_response(
    prompt: str,
    parsed_spec: ParsedTripSpec,
    spec: TripSpec,
    itinerary: Itinerary,
    narrative: str,
    timings: dict[str, float],
) -> PlanResponse:
    day_plans: list[DayPlan] = []
    for day in itinerary.days:
        camp = STATE.graph.nodes[day.camp_node]
        detailed_coords = _detailed_polyline(STATE.graph, day.path)
        elevation_series = _elevation_series(STATE.graph, day.path)
        day_plans.append(
            DayPlan(
                day=day.day_index + 1,
                length_miles=round(day.length_miles, 2),
                gain_m=int(day.gain_m),
                camp_name=day.camp_name,
                camp_lat=camp["y"],
                camp_lon=camp["x"],
                path_coords=detailed_coords,
                elevation_series=elevation_series,
                features_passed=[
                    FeatureInfo(name=f["name"], category=f["category"],
                                lat=f["lat"], lon=f["lon"])
                    for f in day.features_passed
                ],
            )
        )

    return PlanResponse(
        prompt=prompt,
        parsed=ParsedSpec(
            days=parsed_spec.days,
            miles_per_day=parsed_spec.miles_per_day,
            start=parsed_spec.start,
            end=parsed_spec.end,
            preferred_categories=parsed_spec.preferred_categories,
            named_must_visit=parsed_spec.named_must_visit,
            rationale=parsed_spec.rationale,
        ),
        total_length_miles=round(itinerary.total_length_miles, 2),
        total_gain_m=int(itinerary.total_gain_m),
        score=round(itinerary.score, 3),
        days=day_plans,
        narrative=narrative,
        elapsed_seconds=timings,
    )
