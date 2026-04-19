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

from .models import DayPlan, FeatureInfo, ParsedSpec, PlanResponse
from .state import STATE

log = logging.getLogger("routescout.service")


class PlannerError(Exception):
    """Raised when the request can't be satisfied — e.g., no feasible itinerary."""


def plan_from_prompt(prompt: str, *, beam_width: int) -> PlanResponse:
    timings: dict[str, float] = {}

    log.info("planning: %r", prompt)

    t0 = time.perf_counter()
    parsed_spec = parse(prompt, STATE.features)
    timings["parse"] = round(time.perf_counter() - t0, 3)
    log.info(
        "parsed start=%s days=%s miles/day=%s categories=%s",
        parsed_spec.start, parsed_spec.days, parsed_spec.miles_per_day,
        parsed_spec.preferred_categories,
    )

    spec = _to_trip_spec(parsed_spec)

    t0 = time.perf_counter()
    itinerary = plan(STATE.graph, STATE.features, spec, beam_width=beam_width)
    timings["plan"] = round(time.perf_counter() - t0, 3)

    if itinerary is None:
        raise PlannerError(
            "No feasible itinerary for this prompt. Try a different start region "
            "or relax the mileage/duration constraints."
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


def _cumulative_miles(graph, path: list[int]) -> list[float]:
    miles = [0.0]
    for u, v in zip(path[:-1], path[1:]):
        edges = graph.get_edge_data(u, v)
        length_m = min(d.get("length", 0.0) for d in edges.values()) if edges else 0.0
        miles.append(round(miles[-1] + length_m / 1609.344, 3))
    return miles


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
        coords = [
            (STATE.graph.nodes[n]["y"], STATE.graph.nodes[n]["x"])
            for n in day.path
        ]
        elevations = [
            float(STATE.graph.nodes[n].get("elevation") or 0.0) for n in day.path
        ]
        cumulative_miles = _cumulative_miles(STATE.graph, day.path)
        day_plans.append(
            DayPlan(
                day=day.day_index + 1,
                length_miles=round(day.length_miles, 2),
                gain_m=int(day.gain_m),
                camp_name=day.camp_name,
                camp_lat=camp["y"],
                camp_lon=camp["x"],
                path_coords=coords,
                path_elevations_m=elevations,
                path_cumulative_miles=cumulative_miles,
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
