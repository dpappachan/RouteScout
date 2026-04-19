"""End-to-end demo: natural-language prompt → itinerary plan → narrative → PNG.

Run:
    python -m backend.demo_e2e --prompt "3-day loop from Tuolumne Pass that camps at lakes, 9 miles a day"
    python -m backend.demo_e2e --prompt-file prompts/weekend_falls.txt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from backend.graph.build import DATA_DIR, build
from backend.graph.features import FEATURES_PATH
from backend.graph.trailheads import build_trailheads
from backend.llm.narrator import narrate
from backend.llm.parser import parse
from backend.routing.optimizer import plan
from backend.routing.plot import render_itinerary
from backend.routing.trip_spec import TripSpec


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "trip"


def run(prompt: str, output_png: Path | None = None) -> None:
    features = json.loads(FEATURES_PATH.read_text())
    trailheads = build_trailheads()

    print("---")
    print(f"Prompt: {prompt}")
    print("---")

    print("Parsing with Gemini...")
    t0 = time.perf_counter()
    parsed = parse(prompt, features, trailheads)
    print(f"  parsed in {time.perf_counter() - t0:.2f}s")
    print(f"  days={parsed.days}  miles/day={parsed.miles_per_day}  start={parsed.start!r}")
    print(f"  preferred_categories={parsed.preferred_categories}")
    print(f"  named_must_visit={parsed.named_must_visit}")
    print(f"  rationale: {parsed.rationale}")

    spec = TripSpec(
        days=parsed.days,
        miles_per_day=parsed.miles_per_day,
        start=parsed.start,
        end=parsed.end,
        preferred_categories=tuple(parsed.preferred_categories),
        named_must_visit=tuple(parsed.named_must_visit),
    )

    print("\nLoading graph & planning...")
    graph = build()
    t0 = time.perf_counter()
    itinerary = plan(graph, features, trailheads, spec, beam_width=12)
    print(f"  planned in {time.perf_counter() - t0:.2f}s")

    if itinerary is None:
        print("\nNo feasible itinerary for this spec.")
        sys.exit(1)

    print(
        f"  {spec.days} days, {itinerary.total_length_miles:.1f} mi total, "
        f"{int(itinerary.total_gain_m)} m gain, score {itinerary.score:.2f}"
    )

    print("\nNarrating with Gemini...")
    t0 = time.perf_counter()
    narrative = narrate(itinerary, spec, prompt)
    print(f"  narrated in {time.perf_counter() - t0:.2f}s\n")
    print("=" * 72)
    print(narrative)
    print("=" * 72)

    out = output_png or (DATA_DIR / f"demo_e2e_{_slug(prompt)}.png")
    render_itinerary(
        graph,
        itinerary,
        features,
        save_to=out,
        title=prompt[:80] + ("…" if len(prompt) > 80 else ""),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt", type=str)
    src.add_argument("--prompt-file", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    text = args.prompt if args.prompt is not None else args.prompt_file.read_text()
    run(text.strip(), args.output)


if __name__ == "__main__":
    main()
