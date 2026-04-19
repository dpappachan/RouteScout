"""Lazy-loaded, process-wide planner state.

The trail graph and feature list are loaded once at first request (or at
startup — see lifespan in main.py) and reused across every `/plan` call. This
is important: loading the GraphML and features JSON each request would add
several hundred ms and hit disk needlessly.
"""
from __future__ import annotations

import json
import threading
from datetime import date

from backend.graph.build import build
from backend.graph.features import FEATURES_PATH


class PlannerState:
    def __init__(self):
        self._lock = threading.Lock()
        self._graph = None
        self._features: list[dict] | None = None
        self._plans_today = 0
        self._counter_day = date.today()

    def load(self) -> None:
        with self._lock:
            if self._graph is None:
                self._graph = build()
            if self._features is None:
                self._features = json.loads(FEATURES_PATH.read_text())

    @property
    def graph(self):
        if self._graph is None:
            self.load()
        return self._graph

    @property
    def features(self) -> list[dict]:
        if self._features is None:
            self.load()
        return self._features  # type: ignore[return-value]

    def bump_daily_counter(self) -> int:
        """Increment today's counter (resetting at midnight) and return new value."""
        with self._lock:
            today = date.today()
            if today != self._counter_day:
                self._counter_day = today
                self._plans_today = 0
            self._plans_today += 1
            return self._plans_today

    def plans_today(self) -> int:
        with self._lock:
            if date.today() != self._counter_day:
                return 0
            return self._plans_today


STATE = PlannerState()
