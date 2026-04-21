"""Alternative-trailhead suggestions for when the planner can't fit a trip.

Score each trailhead by how many camp candidates lie within the requested
daily mileage radius. Same-region trailheads get a heavy bonus so we
suggest neighbors before sending the user across the park.
"""
from __future__ import annotations

import math


def suggest_alternative_starts(
    parsed_spec, trailheads: list[dict], camps: list[dict],
) -> list[str]:
    """Top trailheads by camp-density within the requested daily mileage."""
    target_m = parsed_spec.miles_per_day * 1609.344
    radius_m = 2.0 * target_m  # mirrors the optimizer's max-day straight-line bound

    failed = next(
        (t for t in trailheads if t["name"] == parsed_spec.start),
        None,
    )
    failed_region = (failed or {}).get("region")

    scored: list[tuple[int, str]] = []
    for th in trailheads:
        if th["name"] == parsed_spec.start:
            continue
        camps_in_range = sum(
            1 for c in camps
            if _haversine_m(th["lat"], th["lon"], c["lat"], c["lon"]) < radius_m
        )
        if camps_in_range == 0:
            continue
        region_bonus = 100 if th.get("region") == failed_region else 0
        scored.append((camps_in_range + region_bonus, th["name"]))

    scored.sort(reverse=True)
    return [name for _, name in scored[:3]]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) *
         math.sin(dlam / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))
