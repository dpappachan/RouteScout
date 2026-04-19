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
        description="Starting feature name, chosen from the provided list of valid feature names."
    )
    end: str | None = Field(
        default=None,
        description="Ending feature name, or null for a loop back to start. "
        "Loops are the default unless the user asks for a point-to-point or thru-hike.",
    )
    preferred_categories: list[str] = Field(
        default_factory=list,
        description=(
            "Feature categories the hiker prefers. Valid values: "
            "peak, lake, waterfall, meadow, pass, viewpoint."
        ),
    )
    named_must_visit: list[str] = Field(
        default_factory=list,
        description=(
            "Specific feature names the user mentioned by name. "
            "Must come from the provided valid names list."
        ),
    )
    rationale: str = Field(
        description="One or two sentences explaining how you interpreted the prompt."
    )


def _build_system_prompt(valid_names: list[str]) -> str:
    return (
        "You turn natural-language hiking trip requests into structured trip "
        "parameters for a route planner that operates within Yosemite National Park.\n"
        "Always return a valid, plannable spec — never refuse because the prompt is "
        "short or vague. Fill in sensible defaults for anything missing.\n\n"
        "Interpretation rules:\n"
        "1. `days` is the total trip length in days. "
        "'day hike', 'short', 'quick' → 1. "
        "'overnight', '2 night / 3 day' → 3. "
        "'weekend' → 2. "
        "Missing → 2.\n"
        "2. `miles_per_day` is the target daily mileage. "
        "'easy', 'gentle', 'relaxed' → 5. "
        "'moderate' → 8. "
        "'hard', 'challenging', 'long' → 12. "
        "If the user gives a total trip mileage, divide by days. "
        "Missing → 7.\n"
        "3. `start` MUST be an exact name from the valid feature names list below. "
        "For a specific region name, pick the list feature inside that region. "
        "For 'easy' / 'waterfalls' / no region given, prefer `Glacier Point` "
        "(iconic, accessible, central). For 'Tuolumne' or 'high country', prefer "
        "`Tuolumne Pass` or `Lembert Dome`. For 'peaks' / 'summits', prefer "
        "`Tuolumne Pass` (richer surrounding peak network than Glacier Point).\n"
        "4. Default to a loop (`end` = null) unless the user explicitly asks for "
        "point-to-point or thru-hike.\n"
        "5. `preferred_categories` values must be from: "
        f"{', '.join(VALID_CATEGORIES)}. "
        "Infer from descriptors: 'waterfall'/'falls' → waterfall; "
        "'lake'/'tarn'/'camp at lakes' → lake; 'peak'/'summit'/'dome' → peak; "
        "'pass' → pass; 'scenic'/'view'/'overlook' → viewpoint; "
        "'meadow' → meadow.\n"
        "6. `named_must_visit` must only contain exact names from the valid "
        "names list, and only when the user names a specific place.\n"
        "7. `rationale` briefly explains the choices you made, especially the "
        "defaults you filled in when the prompt was vague.\n\n"
        "Valid feature names (pick `start`, `end`, and any `named_must_visit` from this list):\n"
        + ", ".join(valid_names)
    )


def parse(user_prompt: str, available_features: list[dict]) -> ParsedTripSpec:
    valid_names = sorted({f["name"] for f in available_features})
    valid_name_set = set(valid_names)

    system = _build_system_prompt(valid_names)

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

    if parsed.start not in valid_name_set:
        raise ValueError(
            f"Parser chose start='{parsed.start}', which is not a valid feature name."
        )
    if parsed.end is not None and parsed.end not in valid_name_set:
        raise ValueError(
            f"Parser chose end='{parsed.end}', which is not a valid feature name."
        )
    parsed.named_must_visit = [n for n in parsed.named_must_visit if n in valid_name_set]
    parsed.preferred_categories = [
        c for c in parsed.preferred_categories if c in VALID_CATEGORIES
    ]

    # Sanity clamps: protect the planner from absurd LLM outputs. These mirror
    # what a reasonable human answer would be — someone asking for a "20-day
    # 50 mi/day thru-hike" doesn't belong in a park-scoped planner.
    parsed.days = max(1, min(parsed.days, 7))
    parsed.miles_per_day = max(3.0, min(parsed.miles_per_day, 18.0))

    return parsed
