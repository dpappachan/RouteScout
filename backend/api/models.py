"""Request / response schemas for the FastAPI surface.

Separated from internal dataclasses (TripSpec, Itinerary) so we can evolve the
public API independently of the planner's internals.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=500,
        description="Natural-language hiking trip request.",
    )


class FeatureInfo(BaseModel):
    name: str
    category: str
    lat: float
    lon: float


class ElevationPoint(BaseModel):
    miles: float
    elevation_m: float


class DayPlan(BaseModel):
    day: int
    length_miles: float
    gain_m: int
    camp_name: str
    camp_lat: float
    camp_lon: float
    # Detailed polyline that follows every turn of the OSM trail geometry.
    path_coords: list[tuple[float, float]]   # [(lat, lon), ...]
    # Elevation samples at node-resolution (sparser than path_coords because
    # elevation is node-attached, not per-segment).
    elevation_series: list[ElevationPoint]
    features_passed: list[FeatureInfo]


class ParsedSpec(BaseModel):
    days: int
    miles_per_day: float
    start: str
    end: str | None = None
    preferred_categories: list[str]
    named_must_visit: list[str]
    rationale: str


class Regulations(BaseModel):
    permit_required: bool
    bear_canister_required: bool
    notes: list[str]


class PlanResponse(BaseModel):
    prompt: str
    parsed: ParsedSpec
    total_length_miles: float
    total_gain_m: int
    score: float
    difficulty: str  # "easy" | "moderate" | "strenuous" | "very strenuous"
    estimated_hours_per_day: list[float]  # one entry per day
    days: list[DayPlan]
    narrative: str
    regulations: Regulations
    elapsed_seconds: dict[str, float]  # {"parse": .., "plan": .., "narrate": ..}


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    graph_nodes: int
    graph_edges: int
    features: int
    plans_served_today: int
