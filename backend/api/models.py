"""Request / response schemas for the FastAPI surface.

Separated from internal dataclasses (TripSpec, Itinerary) so we can evolve the
public API independently of the planner's internals.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    prompt: str = Field(
        min_length=5,
        max_length=500,
        description="Natural-language hiking trip request.",
    )


class FeatureInfo(BaseModel):
    name: str
    category: str
    lat: float
    lon: float


class DayPlan(BaseModel):
    day: int
    length_miles: float
    gain_m: int
    camp_name: str
    camp_lat: float
    camp_lon: float
    path_coords: list[tuple[float, float]]        # [(lat, lon), ...] for map
    path_elevations_m: list[float]                 # elevation at each coord, meters
    path_cumulative_miles: list[float]             # distance from start, miles, per coord
    features_passed: list[FeatureInfo]


class ParsedSpec(BaseModel):
    days: int
    miles_per_day: float
    start: str
    end: str | None = None
    preferred_categories: list[str]
    named_must_visit: list[str]
    rationale: str


class PlanResponse(BaseModel):
    prompt: str
    parsed: ParsedSpec
    total_length_miles: float
    total_gain_m: int
    score: float
    days: list[DayPlan]
    narrative: str
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
