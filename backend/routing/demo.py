"""Run a sample trip through the planner and print/plot the result.

Run:
    python -m backend.routing.demo                 # default preset
    python -m backend.routing.demo --preset falls  # other preset
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from backend.graph.build import DATA_DIR, build
from backend.graph.camps import build_camps
from backend.graph.features import FEATURES_PATH
from backend.graph.trailheads import build_trailheads

from .optimizer import plan
from .plot import render_itinerary
from .trip_spec import Itinerary, TripSpec

PRESETS: dict[str, TripSpec] = {
    "falls": TripSpec(
        days=2,
        miles_per_day=8,
        start="Glacier Point",
        preferred_categories=("waterfall",),
    ),
    "lakes": TripSpec(
        days=3,
        miles_per_day=9,
        start="Tuolumne Meadows Ranger Station",
        preferred_categories=("lake",),
    ),
    "summits": TripSpec(
        days=3,
        miles_per_day=10,
        start="Cathedral Lakes trailhead",
        preferred_categories=("peak",),
    ),
}


def _format_itinerary(it: Itinerary, spec: TripSpec) -> str:
    lines = [
        f"Trip: {spec.days}-day {'loop' if spec.is_loop else 'traverse'}, "
        f"target {spec.miles_per_day} mi/day",
        f"Start: {spec.start}" + (f"  →  End: {spec.end}" if spec.end else "  (loop)"),
        f"Preferences: categories={list(spec.preferred_categories) or '—'}, "
        f"must-visit={list(spec.named_must_visit) or '—'}",
        f"Score: {it.score:.2f}",
        f"Total: {it.total_length_miles:.1f} mi, {int(it.total_gain_m)} m gain",
        "",
    ]
    for day in it.days:
        lines.append(
            f"  Day {day.day_index + 1}: {day.length_miles:.1f} mi, "
            f"{int(day.gain_m)} m gain  →  camp at {day.camp_name!r}"
        )
        named = [
            f"{f['name']} ({f['category']})"
            for f in day.features_passed
            if f["name"] != day.camp_name
        ]
        if named:
            lines.append("    passes: " + ", ".join(named))
    return "\n".join(lines)


def run(preset: str, output_png: Path) -> Itinerary | None:
    if preset not in PRESETS:
        raise SystemExit(f"Unknown preset '{preset}'. Available: {list(PRESETS)}")
    spec = PRESETS[preset]

    graph = build()
    features = json.loads(FEATURES_PATH.read_text())
    trailheads = build_trailheads()
    camps = build_camps()

    t0 = time.perf_counter()
    it = plan(graph, features, trailheads, camps, spec, beam_width=12, adaptive=True)
    elapsed = time.perf_counter() - t0

    if it is None:
        print(f"No feasible itinerary for preset '{preset}'.")
        return None

    print(_format_itinerary(it, spec))
    print(f"\nPlanned in {elapsed:.2f}s")

    render_itinerary(
        graph,
        it,
        features,
        save_to=output_png,
        title=f"RouteScout — preset '{preset}' — "
              f"{it.total_length_miles:.1f} mi over {spec.days} days",
    )
    return it


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default="falls", choices=sorted(PRESETS.keys()))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = args.output or (DATA_DIR / f"demo_{args.preset}.png")
    run(args.preset, output)


if __name__ == "__main__":
    main()
