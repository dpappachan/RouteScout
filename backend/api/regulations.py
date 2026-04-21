"""Wilderness-aware regulations layer.

Each wilderness in our coverage area is managed by a different agency
(NPS Yosemite, Inyo NF, Humboldt-Toiyabe NF, Stanislaus NF) and has its
own permit process, road closures, and quota windows. Getting these right
is what separates a real planner from a toy demo — it's also the part
that requires the most domain knowledge.
"""
from __future__ import annotations

from backend.llm.parser import ParsedTripSpec
from backend.routing.trip_spec import Itinerary

from .models import Regulations
from .response_builders import max_elevation_on_route

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

# Glacier Point Road trailheads — separate seasonal closure schedule.
GLACIER_POINT_ROAD_TRAILHEADS = frozenset({
    "Glacier Point", "Taft Point trailhead", "Mono Meadow trailhead",
    "Ostrander Lake trailhead", "Bridalveil Creek campground trailhead",
})

# Sonora Pass (Hwy 108) closes in winter, affecting Emigrant trailheads.
SONORA_PASS_TRAILHEADS = frozenset({
    "Kennedy Meadows trailhead", "Crabtree trailhead", "Gianelli trailhead",
})

# Wilderness-region → permit info, sourced from the managing agency's website.
PERMIT_BY_REGION: dict[str, str] = {
    "Yosemite Valley":        "Yosemite Wilderness permit required for overnight trips (recreation.gov, ~24-week advance lottery + day-of walk-ups at the Wilderness Center).",
    "South Rim":              "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Wawona":                 "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Hetch Hetchy":           "Yosemite Wilderness permit required (recreation.gov). Hetch Hetchy quotas fill quickly in spring/fall.",
    "Big Oak Flat Road":      "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Tioga Road":             "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Tuolumne Meadows":       "Yosemite Wilderness permit required for overnight trips (recreation.gov).",
    "Tioga Pass":             "Yosemite Wilderness permit required (recreation.gov). Mono Pass / Mount Dana usually accessible through October.",
    "Ansel Adams Wilderness": "Ansel Adams Wilderness permit required (Inyo National Forest via recreation.gov). Quotas in effect May 1 – Nov 1.",
    "Hoover Wilderness":      "Hoover Wilderness permit required (Humboldt-Toiyabe National Forest, recreation.gov). Quotas Jun 15 – Sep 15.",
    "Emigrant Wilderness":    "Emigrant Wilderness permit required (Stanislaus National Forest, free). Self-issue at trailhead or Pinecrest / Summit ranger stations.",
}

HIGH_ELEVATION_THRESHOLD_M = 3300  # ~10,800 ft, above which altitude / lingering snow matter


def regulations_for(
    graph,
    itinerary: Itinerary,
    parsed_spec: ParsedTripSpec,
    trailhead: dict | None,
) -> Regulations:
    """Build the regulations + safety-notes block for a planned trip.

    Branches on:
      · day-hike vs overnight (permit, food storage)
      · wilderness region of the start trailhead (which agency, what process)
      · features visited along the route (Half Dome cables, Donohue Pass)
      · access road (Tioga / Glacier Point / Sonora Pass seasonal closures)
      · max elevation on route (altitude warning)
      · seasonal stream-crossing risk (snowmelt + waterfalls)
    """
    notes: list[str] = []
    is_overnight = len(itinerary.days) > 1
    region = (trailhead or {}).get("region")

    notes.append(_permit_note(is_overnight, region))
    notes.append(_food_storage_note(is_overnight))
    if is_overnight:
        notes.append(_lnt_note())

    visited_names = {f["name"] for d in itinerary.days for f in d.features_passed}
    visited_names.update(parsed_spec.named_must_visit)

    if "Half Dome" in visited_names:
        notes.append(_half_dome_note())
    if any("Donohue" in n or "Lyell" in n for n in visited_names):
        notes.append(_donohue_note())

    if parsed_spec.start in TIOGA_ROAD_TRAILHEADS:
        notes.append(_tioga_road_note())
    if parsed_spec.start in GLACIER_POINT_ROAD_TRAILHEADS:
        notes.append(_glacier_point_road_note())
    if parsed_spec.start in SONORA_PASS_TRAILHEADS:
        notes.append(_sonora_pass_note())

    max_elev = max_elevation_on_route(graph, itinerary)
    if max_elev > HIGH_ELEVATION_THRESHOLD_M:
        notes.append(_high_elevation_note(max_elev))

    if _has_snowmelt_risk(itinerary):
        notes.append(_snowmelt_note())

    return Regulations(
        permit_required=is_overnight,
        bear_canister_required=is_overnight,
        notes=notes,
    )


# Individual note builders — kept tiny and named so the regulations_for body
# reads as a checklist rather than a wall of strings.

def _permit_note(is_overnight: bool, region: str | None) -> str:
    if not is_overnight:
        return "No overnight permit needed for day hikes."
    return PERMIT_BY_REGION.get(
        region,
        "Wilderness permit required for any overnight trip in this area. "
        "Check recreation.gov for the managing agency.",
    )


def _food_storage_note(is_overnight: bool) -> str:
    if is_overnight:
        return (
            "Bear-resistant canister mandatory for all food and scented items "
            "(Yosemite, Ansel Adams, Hoover, Emigrant — same rule)."
        )
    return (
        "Day hikers: never leave food unattended. Bears actively patrol "
        "popular trailheads and parking lots."
    )


def _lnt_note() -> str:
    return (
        "Camp at least 100 ft (30 m) from water and 25 ft (8 m) from trails. "
        "Pack out all trash including toilet paper. Bury human waste in a 6-in cathole."
    )


def _half_dome_note() -> str:
    return (
        "Half Dome cables permit required separately (recreation.gov daily "
        "lottery). Cables typically up late May through mid-October."
    )


def _donohue_note() -> str:
    return (
        "Donohue Pass crosses the Yosemite ↔ Ansel Adams boundary. "
        "Yosemite-issued permits cover the through-trip; check that yours "
        "specifies the trailhead direction."
    )


def _tioga_road_note() -> str:
    return (
        "Tioga Road (Hwy 120) typically closed November through late May "
        "due to snow. Confirm at nps.gov/yose before driving."
    )


def _glacier_point_road_note() -> str:
    return (
        "Glacier Point Road typically closed mid-November through late May. "
        "Confirm at nps.gov/yose before driving."
    )


def _sonora_pass_note() -> str:
    return (
        "Sonora Pass (Hwy 108) typically closed mid-November through late May. "
        "Confirm at dot.ca.gov before driving."
    )


def _high_elevation_note(max_elev_m: float) -> str:
    return (
        f"Route reaches {int(max_elev_m)} m ({int(max_elev_m * 3.281)} ft). "
        "Watch for altitude effects; acclimatize if you live near sea level. "
        "Snow can linger above 10,000 ft well into July."
    )


def _has_snowmelt_risk(itinerary: Itinerary) -> bool:
    """Big climbs + waterfalls/lakes in the route are a proxy for high-snowmelt
    creek crossings (May–July) that sometimes catch hikers off-guard."""
    big_climbs = any(d.gain_m > 800 for d in itinerary.days)
    has_water_features = any(
        f["category"] in ("waterfall", "lake")
        for d in itinerary.days for f in d.features_passed
    )
    return big_climbs and has_water_features


def _snowmelt_note() -> str:
    return (
        "Snowmelt-fed creek crossings (May–July) can be dangerous. "
        "Look for log crossings or wait for afternoon flow to drop."
    )
