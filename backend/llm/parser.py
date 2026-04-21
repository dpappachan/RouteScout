"""Turn a natural-language hiking prompt into a structured TripSpec.

Gemini 2.5 Flash is instructed with the full list of valid feature names and
categories so that its structured JSON output plugs straight into the planner
without a second translation step. We validate after the call to make sure the
LLM picked something real.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .client import MODEL_ID, client

VALID_CATEGORIES = ("peak", "lake", "waterfall", "meadow", "pass", "viewpoint")


class ParsedTripSpec(BaseModel):
    days: int = Field(
        description="Total trip length in days. '2 night 3 day' means 3. "
        "Treat 'weekend' as 2-3 depending on context."
    )
    miles_per_day: float = Field(
        description="Target daily mileage. If the user gives a total, divide by days."
    )
    start: str = Field(
        description="Starting trailhead name (where the hiker parks the car), "
        "chosen from the provided list of trailheads."
    )
    end: str | None = Field(
        default=None,
        description="Ending trailhead name, or null for a loop back to start. "
        "Loops are the default unless the user asks for a point-to-point or thru-hike.",
    )
    preferred_categories: list[str] = Field(
        default_factory=list,
        description=(
            "Feature categories the hiker wants to visit en-route. Valid values: "
            "peak, lake, waterfall, meadow, pass, viewpoint."
        ),
    )
    named_must_visit: list[str] = Field(
        default_factory=list,
        description=(
            "Specific feature (destination) names the user mentioned by name. "
            "Must come from the valid feature names list."
        ),
    )
    rationale: str = Field(
        description="One or two sentences explaining how you interpreted the prompt."
    )


def _build_system_prompt(
    trailheads: list[dict], feature_names: list[str]
) -> str:
    # IMPORTANT: format such that the LLM cannot copy the description as part
    # of the name. Bare name first, then description as a separate clause.
    trailhead_lines = "\n".join(
        f"  · \"{th['name']}\" — region: {th['region']}; accesses: {th['accesses']}"
        for th in trailheads
    )
    trailhead_names = [th["name"] for th in trailheads]

    return (
        "You turn natural-language hiking trip requests into structured trip "
        "parameters for a route planner operating across Yosemite National Park "
        "and the contiguous Sierra wilderness areas (Ansel Adams, Hoover, "
        "Emigrant). Always return a valid, plannable spec — never refuse "
        "because the prompt is short or vague. Fill in sensible defaults.\n\n"
        "KEY CONCEPT: A trip begins and ends at a TRAILHEAD (a parking lot, "
        "not a destination). When the user names a destination (e.g., 'hike to "
        "Half Dome'), pick the trailhead that actually accesses it (Happy Isles "
        "for Half Dome) and put the destination in `named_must_visit`.\n\n"
        "Interpretation rules:\n"
        "1. `days` = trip length in days. 'day hike'/'short'/'quick' → 1. "
        "'overnight'/'2 night 3 day' → 3. 'weekend' → 2. Missing → 2.\n"
        "2. `miles_per_day` target daily mileage. 'easy'/'gentle' → 5. "
        "'moderate' → 8. 'hard'/'challenging'/'long' → 12. If user gives total, "
        "divide by days. Missing → 7.\n"
        "3. `start` MUST be EXACTLY ONE trailhead name copied verbatim from "
        "the list below — never a disjunction, never two names joined with "
        "'or' or '/'. Region defaults (pick the single named trailhead):\n"
        "   · 'Yosemite Valley', 'falls' → Happy Isles\n"
        "   · 'Glacier Point', 'south rim' → Glacier Point\n"
        "   · 'Tuolumne', 'high country' → Lembert Dome / Dog Lake trailhead\n"
        "   · 'Cathedral', 'Sunrise', 'JMT through Yosemite' → Cathedral Lakes trailhead\n"
        "   · 'Wawona', 'south Yosemite' → Chilnualna Falls trailhead\n"
        "   · 'Hetch Hetchy', 'Wapama Falls' → Hetch Hetchy trailhead\n"
        "   · 'Tioga Pass', 'Mount Dana', 'Gaylor Lakes' → Mono Pass trailhead\n"
        "   · 'Ansel Adams', 'Banner', 'Ritter', 'Thousand Island Lake', 'JMT south', "
        "'Donohue Pass', 'Garnet Lake' → Rush Creek trailhead (Silver Lake)\n"
        "   · 'Devils Postpile', 'Reds Meadow', 'Mammoth' → Devils Postpile / Reds Meadow trailhead\n"
        "   · 'Hoover', 'Twin Lakes (Bridgeport)', 'Matterhorn Peak' → Twin Lakes trailhead\n"
        "   · 'Virginia Lakes' → Virginia Lakes trailhead\n"
        "   · 'Green Creek', 'Green Lake' → Green Creek trailhead\n"
        "   · 'Saddlebag Lake', 'Twenty Lakes' → Saddlebag Lake trailhead\n"
        "   · 'Emigrant', 'Sonora Pass', 'Kennedy Meadows', 'Relief Reservoir' → Kennedy Meadows trailhead\n"
        "   · 'easy day from a trailhead', no region → Tenaya Lake trailhead\n"
        "4. Default to a loop (`end` = null). Only set `end` when the user "
        "explicitly asks for point-to-point.\n"
        "5. `preferred_categories` from: "
        f"{', '.join(VALID_CATEGORIES)}. "
        "'waterfall'/'falls' → waterfall; 'lake'/'camp at lakes' → lake; "
        "'peak'/'summit'/'dome' → peak; 'pass' → pass; "
        "'scenic'/'view'/'overlook' → viewpoint; 'meadow' → meadow.\n"
        "6. `named_must_visit`: only if the user names a specific destination. "
        "Must come exactly from the feature names list below.\n"
        "7. `rationale`: briefly say which defaults you filled and why the "
        "trailhead choice fits the request.\n\n"
        "TRAILHEADS — `start` and `end` must be the bare name in quotes "
        "below, with NO parenthetical region or extra text appended:\n"
        f"{trailhead_lines}\n\n"
        "Valid destination feature names for `named_must_visit`:\n"
        + ", ".join(feature_names)
        + "\n\nNote: some trailhead names overlap with feature names "
        f"(like Glacier Point). When this happens, `start` uses the trailhead; "
        "`named_must_visit` uses the feature."
    )


def _resolve_trailhead_name(name: str, valid: set[str]) -> str:
    """Tolerant lookup. The LLM occasionally appends a parenthetical region,
    drops the 'trailhead' suffix, or capitalizes inconsistently. Try a
    sequence of relaxed matches before failing validation."""

    def candidates(s: str) -> list[str]:
        s = s.strip().strip('"').strip("'").strip()
        out = [s]
        # strip parenthetical "(Region)" suffix
        if "(" in s:
            out.append(s.split("(")[0].strip())
        # split on " or " — LLM occasionally returns "X or Y"
        if " or " in s.lower():
            for part in s.split(" or "):
                out.append(part.strip())
        # add/remove a " trailhead" suffix
        for c in list(out):
            if c.lower().endswith(" trailhead"):
                out.append(c[: -len(" trailhead")].strip())
            else:
                out.append(c + " trailhead")
        return out

    valid_lower = {v.lower(): v for v in valid}
    for cand in candidates(name):
        if cand in valid:
            return cand
        match = valid_lower.get(cand.lower())
        if match:
            return match

    raise ValueError(
        f"Parser chose start/end={name!r}, which is not a valid trailhead name."
    )


def parse(
    user_prompt: str,
    available_features: list[dict],
    trailheads: list[dict],
) -> ParsedTripSpec:
    feature_names = sorted({f["name"] for f in available_features})
    feature_name_set = set(feature_names)
    trailhead_name_set = {th["name"] for th in trailheads}

    system = _build_system_prompt(trailheads, feature_names)

    resp = client().models.generate_content(
        model=MODEL_ID,
        contents=[system, f"User request:\n{user_prompt}"],
        config={
            "response_mime_type": "application/json",
            "response_schema": ParsedTripSpec,
            "temperature": 0.2,
        },
    )

    parsed: ParsedTripSpec = resp.parsed

    parsed.start = _resolve_trailhead_name(parsed.start, trailhead_name_set)
    if parsed.end is not None:
        parsed.end = _resolve_trailhead_name(parsed.end, trailhead_name_set)
    parsed.named_must_visit = [n for n in parsed.named_must_visit if n in feature_name_set]
    parsed.preferred_categories = [
        c for c in parsed.preferred_categories if c in VALID_CATEGORIES
    ]

    # Sanity clamps: protect the planner from absurd LLM outputs. These mirror
    # what a reasonable human answer would be — someone asking for a "20-day
    # 50 mi/day thru-hike" doesn't belong in a park-scoped planner.
    parsed.days = max(1, min(parsed.days, 7))
    parsed.miles_per_day = max(3.0, min(parsed.miles_per_day, 18.0))

    return parsed
