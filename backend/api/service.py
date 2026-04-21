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

from .models import DayPlan, ElevationPoint, FeatureInfo, ParsedSpec, PlanResponse, Regulations
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
    itinerary = plan(
        STATE.graph, STATE.features, STATE.trailheads, STATE.camps, spec,
        beam_width=beam_width,
    )
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

    estimated_hours = _estimate_daily_hours(itinerary)
    difficulty = _difficulty_label(itinerary)
    start_trailhead = next(
        (t for t in STATE.trailheads if t["name"] == parsed_spec.start), None,
    )
    regulations = _regulations_for(itinerary, parsed_spec, start_trailhead)

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
        difficulty=difficulty,
        estimated_hours_per_day=estimated_hours,
        days=day_plans,
        narrative=narrative,
        regulations=regulations,
        elapsed_seconds=timings,
    )


def _estimate_daily_hours(itinerary: Itinerary) -> list[float]:
    """Naismith's rule (lightly tuned): ~3 km/h on flat trail, plus 30 min
    per 300 m of cumulative ascent. Standard backpacking pace estimate."""
    hours_per_day: list[float] = []
    for day in itinerary.days:
        flat_hours = (day.length_m / 1000.0) / 3.0
        ascent_hours = (day.gain_m / 300.0) * 0.5
        hours_per_day.append(round(flat_hours + ascent_hours, 1))
    return hours_per_day


def _difficulty_label(itinerary: Itinerary) -> str:
    """Difficulty is a function of daily mileage and daily ascent. Loose bands,
    aimed at a reasonably-fit backpacker."""
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


# Trailheads on Tioga Road close roughly Nov–late May (snow-dependent).
TIOGA_ROAD_TRAILHEADS = frozenset({
    "Tenaya Lake trailhead", "May Lake trailhead", "Cathedral Lakes trailhead",
    "Lembert Dome / Dog Lake trailhead", "Elizabeth Lake trailhead",
    "Tuolumne Meadows Ranger Station", "Mono Pass trailhead",
    "Ten Lakes trailhead", "White Wolf trailhead", "Lukens Lake trailhead",
    "Yosemite Creek trailhead", "North Dome / Porcupine Creek trailhead",
    "Sunrise Lakes / Clouds Rest trailhead", "Glen Aulin trailhead",
    "Gaylor Lakes trailhead", "Mount Dana trailhead", "Tamarack Flat trailhead",
    "Saddlebag Lake trailhead",
})

# Glacier Point Road trailheads also seasonally closed but on a different schedule.
GLACIER_POINT_ROAD_TRAILHEADS = frozenset({
    "Glacier Point", "Taft Point trailhead", "Mono Meadow trailhead",
    "Ostrander Lake trailhead", "Bridalveil Creek campground trailhead",
})

# Sonora Pass (Hwy 108) closes in winter, affecting Emigrant trailheads.
SONORA_PASS_TRAILHEADS = frozenset({
    "Kennedy Meadows trailhead", "Crabtree trailhead", "Gianelli trailhead",
})

# Wilderness → permit info. Each managed by a different agency with different
# rules; getting this right is what separates "real planner" from "toy demo".
PERMIT_BY_REGION: dict[str, str] = {
    "Yosemite Valley":         "Yosemite Wilderness permit required for overnight trips (recreation.gov, ~24-week advance lottery + day-of walk-ups at the Wilderness Center).",
    "South Rim":               "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Wawona":                  "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Hetch Hetchy":            "Yosemite Wilderness permit required (recreation.gov). Hetch Hetchy quotas fill quickly in spring/fall.",
    "Big Oak Flat Road":       "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Tioga Road":              "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Tuolumne Meadows":        "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Tioga Pass":              "Yosemite Wilderness permit required (recreation.gov). Mono Pass / Mount Dana usually accessible through October.",
    "Ansel Adams Wilderness":  "Ansel Adams Wilderness permit required (Inyo National Forest via recreation.gov). Quotas in effect May 1 – Nov 1.",
    "Hoover Wilderness":       "Hoover Wilderness permit required (Humboldt-Toiyabe National Forest, recreation.gov). Quotas Jun 15 – Sep 15.",
    "Emigrant Wilderness":     "Emigrant Wilderness permit required (Stanislaus National Forest, free). Self-issue at trailhead or Pinecrest / Summit ranger stations.",
}


def _regulations_for(itinerary: Itinerary, parsed_spec, trailhead: dict | None) -> Regulations:
    """Build the regulations / safety notes block for a planned trip.
    Branches on (a) whether it's a day hike vs overnight, (b) the wilderness
    the start trailhead is in, and (c) features visited along the way."""
    notes: list[str] = []
    is_overnight = len(itinerary.days) > 1

    # Permit by wilderness — different agencies, different rules
    region = (trailhead or {}).get("region")
    if is_overnight:
        permit_note = PERMIT_BY_REGION.get(
            region,
            "Wilderness permit required for any overnight trip in this area. "
            "Check recreation.gov for the managing agency.",
        )
        notes.append(permit_note)
    else:
        notes.append("No overnight permit needed for day hikes.")

    # Bear country — true everywhere we operate
    if is_overnight:
        notes.append(
            "Bear-resistant canister mandatory for all food and scented items "
            "(Yosemite, Ansel Adams, Hoover, Emigrant — same rule)."
        )
    else:
        notes.append(
            "Day hikers: never leave food unattended. Bears actively patrol "
            "popular trailheads and parking lots."
        )

    # Leave No Trace basics for overnight
    if is_overnight:
        notes.append(
            "Camp at least 100 ft (30 m) from water and 25 ft (8 m) from trails. "
            "Pack out all trash including toilet paper. Bury human waste in a 6-in cathole."
        )

    # Half Dome cables permit
    visited_names = {f["name"] for d in itinerary.days for f in d.features_passed}
    visited_names.update(parsed_spec.named_must_visit)
    if "Half Dome" in visited_names:
        notes.append(
            "Half Dome cables permit required separately (recreation.gov daily "
            "lottery). Cables typically up late May through mid-October."
        )

    # Cross-jurisdiction notes (JMT through Donohue Pass = Yosemite ↔ Ansel Adams)
    if any("Donohue" in n or "Lyell" in n for n in visited_names):
        notes.append(
            "Donohue Pass crosses the Yosemite ↔ Ansel Adams boundary. Yosemite-issued "
            "permits cover the through-trip; check that yours specifies "
            "the trailhead direction."
        )

    # Road closure warnings (only for overnight or any hike if relevant)
    if parsed_spec.start in TIOGA_ROAD_TRAILHEADS:
        notes.append(
            "Tioga Road (Hwy 120) typically closed November through late May "
            "due to snow. Confirm at nps.gov/yose before driving."
        )
    if parsed_spec.start in GLACIER_POINT_ROAD_TRAILHEADS:
        notes.append(
            "Glacier Point Road typically closed mid-November through late May. "
            "Confirm at nps.gov/yose before driving."
        )
    if parsed_spec.start in SONORA_PASS_TRAILHEADS:
        notes.append(
            "Sonora Pass (Hwy 108) typically closed mid-November through late May. "
            "Confirm at dot.ca.gov before driving."
        )

    # High-elevation warning
    max_elev = max(
        (pt.elevation_m for d in itinerary.days for pt in []),  # placeholder; we recompute below
        default=0.0,
    )
    # The day's path elevations live on the DaySegment.path nodes — use STATE.
    max_elev = _max_elevation_on_route(itinerary)
    if max_elev > 3300:
        notes.append(
            f"Route reaches {int(max_elev)} m ({int(max_elev * 3.281)} ft). "
            "Watch for altitude effects; acclimatize if you live near sea level. "
            "Snow can linger above 10,000 ft well into July."
        )

    # Stream crossings in spring snowmelt
    if any(d.gain_m > 800 for d in itinerary.days) and any(
        f["category"] in ("waterfall", "lake") for d in itinerary.days for f in d.features_passed
    ):
        notes.append(
            "Snowmelt-fed creek crossings (May–July) can be dangerous. "
            "Look for log crossings or wait for afternoon flow to drop."
        )

    return Regulations(
        permit_required=is_overnight,
        bear_canister_required=is_overnight,
        notes=notes,
    )


def _max_elevation_on_route(itinerary: Itinerary) -> float:
    """Pull max node elevation across all path nodes from STATE.graph."""
    max_e = 0.0
    for day in itinerary.days:
        for n in day.path:
            elev = STATE.graph.nodes[n].get("elevation")
            if elev and elev > max_e:
                max_e = float(elev)
    return max_e
