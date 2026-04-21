"""Orchestration: prompt → parsed spec → itinerary → narrative → response.

Kept thin: each phase delegates to a single module so the data flow reads
top-to-bottom. Built deliberately so unit tests can exercise the pipeline
without spinning up a TestClient (no FastAPI request/response objects in
this layer).
"""
from __future__ import annotations

import logging
import time

from backend.llm.narrator import narrate
from backend.llm.parser import ParsedTripSpec, parse
from backend.routing.optimizer import plan
from backend.routing.trip_spec import TripSpec

from .models import ParsedSpec, PlanResponse, TrailheadInfo
from .regulations import regulations_for
from .response_builders import build_day_plans, difficulty_label, estimate_daily_hours
from .state import STATE
from .suggestions import suggest_alternative_starts

log = logging.getLogger("routescout.service")


class PlannerError(Exception):
    """Raised when the request can't be satisfied — e.g., no feasible itinerary."""


def plan_from_prompt(prompt: str, *, beam_width: int) -> PlanResponse:
    """The end-to-end pipeline. Times each phase for telemetry."""
    timings: dict[str, float] = {}

    log.info("planning: %r", prompt)

    # 1. Natural language → structured TripSpec via Gemini schema-constrained output
    t0 = time.perf_counter()
    parsed_spec = parse(prompt, STATE.features, STATE.trailheads)
    timings["parse"] = round(time.perf_counter() - t0, 3)
    log.info(
        "parsed start=%s days=%s miles/day=%s categories=%s",
        parsed_spec.start, parsed_spec.days, parsed_spec.miles_per_day,
        parsed_spec.preferred_categories,
    )
    spec = _to_trip_spec(parsed_spec)

    # 2. Plan the itinerary; widen the beam adaptively before declaring failure
    t0 = time.perf_counter()
    itinerary = plan(
        STATE.graph, STATE.features, STATE.trailheads, STATE.camps, spec,
        beam_width=beam_width, adaptive=True,
    )
    timings["plan"] = round(time.perf_counter() - t0, 3)

    if itinerary is None:
        raise PlannerError(_infeasibility_message(parsed_spec))

    log.info(
        "planned %d days, %.1f mi, %d m gain, score %.2f",
        len(itinerary.days), itinerary.total_length_miles,
        int(itinerary.total_gain_m), itinerary.score,
    )

    # 3. Trip narrative — Gemini generates prose grounded only on the resolved
    #    itinerary so it can't invent features or distances.
    t0 = time.perf_counter()
    narrative = narrate(itinerary, spec, prompt)
    timings["narrate"] = round(time.perf_counter() - t0, 3)

    # 4. Assemble the public PlanResponse
    start_trailhead = _find_trailhead(parsed_spec.start)
    end_trailhead = _find_trailhead(parsed_spec.end or parsed_spec.start)

    return PlanResponse(
        prompt=prompt,
        parsed=_parsed_spec_to_public(parsed_spec),
        total_length_miles=round(itinerary.total_length_miles, 2),
        total_gain_m=int(itinerary.total_gain_m),
        score=round(itinerary.score, 3),
        difficulty=difficulty_label(itinerary),
        estimated_hours_per_day=estimate_daily_hours(itinerary),
        start_trailhead=_to_trailhead_info(start_trailhead),
        end_trailhead=_to_trailhead_info(end_trailhead),
        days=build_day_plans(STATE.graph, itinerary),
        narrative=narrative,
        regulations=regulations_for(STATE.graph, itinerary, parsed_spec, start_trailhead),
        elapsed_seconds=timings,
    )


def _find_trailhead(name: str) -> dict:
    """Look up a trailhead by name; raise loudly if missing (parser already
    validated this, so it shouldn't fail in practice)."""
    th = next((t for t in STATE.trailheads if t["name"] == name), None)
    if th is None:
        raise ValueError(f"Trailhead {name!r} not found in state.")
    return th


def _to_trailhead_info(th: dict) -> TrailheadInfo:
    """Public response uses the curated parking-lot lat/lon, NOT the snapped
    graph node, so the map pin sits where the car actually parks."""
    return TrailheadInfo(
        name=th["name"], lat=th["lat"], lon=th["lon"],
        region=th.get("region", ""),
    )


def _to_trip_spec(parsed: ParsedTripSpec) -> TripSpec:
    return TripSpec(
        days=parsed.days,
        miles_per_day=parsed.miles_per_day,
        start=parsed.start,
        end=parsed.end,
        preferred_categories=tuple(parsed.preferred_categories),
        named_must_visit=tuple(parsed.named_must_visit),
    )


def _parsed_spec_to_public(parsed: ParsedTripSpec) -> ParsedSpec:
    return ParsedSpec(
        days=parsed.days,
        miles_per_day=parsed.miles_per_day,
        start=parsed.start,
        end=parsed.end,
        preferred_categories=parsed.preferred_categories,
        named_must_visit=parsed.named_must_visit,
        rationale=parsed.rationale,
    )


def _infeasibility_message(parsed_spec: ParsedTripSpec) -> str:
    suggestions = suggest_alternative_starts(parsed_spec, STATE.trailheads, STATE.camps)
    suggestion_phrase = (
        f" Try a different start trailhead — {', '.join(suggestions[:3])} "
        "have richer surrounding trail networks for loops of this size."
        if suggestions else ""
    )
    return (
        f"Couldn't fit a {parsed_spec.days}-day trip at "
        f"{parsed_spec.miles_per_day:g} miles/day starting from "
        f"{parsed_spec.start}.{suggestion_phrase} Or shorten the trip / "
        "reduce mileage per day."
    )
