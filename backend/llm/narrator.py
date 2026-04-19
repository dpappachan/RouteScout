"""Turn a planned Itinerary into an engaging human-readable trip description."""
from __future__ import annotations

from backend.routing.trip_spec import Itinerary, TripSpec

from .client import MODEL_ID, client


def _format_itinerary_for_llm(itinerary: Itinerary, spec: TripSpec) -> str:
    lines = [
        f"Trip type: {spec.days}-day {'loop' if spec.is_loop else 'point-to-point'}",
        f"Start: {spec.start}",
        f"Target: {spec.miles_per_day} mi/day",
        f"Total distance: {itinerary.total_length_miles:.1f} mi",
        f"Total elevation gain: {int(itinerary.total_gain_m)} m",
        "",
    ]
    for day in itinerary.days:
        lines.append(
            f"Day {day.day_index + 1}: {day.length_miles:.1f} mi, "
            f"{int(day.gain_m)} m gain, camp at {day.camp_name}"
        )
        features = [f"{f['name']} ({f['category']})" for f in day.features_passed]
        if features:
            lines.append(f"  features passed: {', '.join(features)}")
    return "\n".join(lines)


def narrate(itinerary: Itinerary, spec: TripSpec, user_prompt: str) -> str:
    system = (
        "You write short, vivid trip descriptions for a hiking route planner. "
        "Given a planned Yosemite itinerary, write a description the user can read "
        "before their trip.\n\n"
        "Requirements:\n"
        "- Second-person present tense ('You leave the trailhead...')\n"
        "- Mention mileage and elevation gain for each day\n"
        "- Name specific features the route passes\n"
        "- Do NOT invent places, names, or distances that aren't in the itinerary data\n"
        "- 150-250 words total\n"
        "- Use plain prose paragraphs, not bullet lists or markdown headers\n"
        "- Open with a one-sentence hook that captures the trip's character"
    )

    summary = _format_itinerary_for_llm(itinerary, spec)

    resp = client().models.generate_content(
        model=MODEL_ID,
        contents=[
            system,
            f"User's original request:\n{user_prompt}",
            f"Planned itinerary:\n{summary}",
        ],
        config={"temperature": 0.7},
    )
    return resp.text.strip()
