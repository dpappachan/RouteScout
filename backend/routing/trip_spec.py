"""Dataclasses that describe the input (TripSpec) and output (Itinerary) of
the planner."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TripSpec:
    """Structured form of a hiker's request.

    `start` and `end` are feature names (e.g. "Glacier Point") that must exist
    in the curated features JSON. If `end` is None, the itinerary loops back
    to `start`.
    """

    days: int
    miles_per_day: float
    start: str
    end: str | None = None
    preferred_categories: tuple[str, ...] = ()
    named_must_visit: tuple[str, ...] = ()

    @property
    def is_loop(self) -> bool:
        return self.end is None or self.end == self.start

    @property
    def target_m_per_day(self) -> float:
        return self.miles_per_day * 1609.344


@dataclass
class DaySegment:
    """One day of a multi-day itinerary."""

    day_index: int                           # 0-based
    path: list[int]                          # graph node ids, start → camp
    length_m: float
    gain_m: float
    camp_node: int
    camp_name: str                           # nearest feature to camp (descriptive)
    features_passed: list[dict] = field(default_factory=list)  # raw feature dicts

    @property
    def length_miles(self) -> float:
        return self.length_m / 1609.344


@dataclass
class Itinerary:
    days: list[DaySegment]
    total_length_m: float
    total_gain_m: float
    score: float

    @property
    def total_length_miles(self) -> float:
        return self.total_length_m / 1609.344
