"""Multi-day itinerary planner.

Beam search over sequences of camp nodes drawn from the curated feature list.
Each day is an A\\* shortest-path segment between consecutive camps; we score
candidate itineraries by (a) how well each day's mileage matches the target,
(b) how many requested-category or named features are visited, and
(c) how closely the final day lands back at the start (for loops).

Beam search is a pragmatic middle ground between greedy ("pick the best-
scoring next camp each day and hope for the best") and full combinatorial
search (which on 100+ camps × multiple days is infeasible). Keeping the
top-K partial itineraries after each day gives us the option to recover from
a deceptively attractive early choice.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace

import networkx as nx

from .pathfinder import (
    haversine_m,
    path_elevation_gain_m,
    path_length_m,
    shortest_path,
)
from .trip_spec import DaySegment, Itinerary, TripSpec


# How far a day can stray from the target mileage before it's rejected. These
# bounds define the search space, not the preference — scoring penalizes
# anything that isn't close to target, but the optimizer won't even consider
# segments outside this band.
MIN_DAY_LENGTH_RATIO = 0.4
MAX_DAY_LENGTH_RATIO = 2.0

# Straight-line pre-filter: if even the crow-flies distance between two
# candidate camps exceeds max allowable day mileage, skip the A* call.
# This is a 10x speedup on a 151-feature search space.
STRAIGHT_LINE_SAFETY_FACTOR = 1.0


@dataclass
class _State:
    current_node: int
    days_done: list[DaySegment] = field(default_factory=list)
    total_length_m: float = 0.0
    total_gain_m: float = 0.0
    score: float = 0.0
    visited_camp_nodes: frozenset[int] = field(default_factory=frozenset)


def plan(
    graph: nx.MultiDiGraph,
    features: list[dict],
    spec: TripSpec,
    beam_width: int = 8,
) -> Itinerary | None:
    features_by_name: dict[str, dict] = {f["name"]: f for f in features}
    if spec.start not in features_by_name:
        raise ValueError(
            f"Unknown start feature '{spec.start}'. Must be a name in the features JSON."
        )
    end_name = spec.end or spec.start
    if end_name not in features_by_name:
        raise ValueError(f"Unknown end feature '{end_name}'.")

    start_node = features_by_name[spec.start]["node_id"]
    end_node = features_by_name[end_name]["node_id"]

    # node_id -> list of features at that node (for path-hit detection)
    features_at_node: dict[int, list[dict]] = defaultdict(list)
    for f in features:
        features_at_node[f["node_id"]].append(f)

    camps = list(features)  # every feature is a legal overnight stop

    target_m = spec.target_m_per_day
    beam: list[_State] = [_State(current_node=start_node)]

    for day_idx in range(spec.days):
        is_last_day = day_idx == spec.days - 1
        is_penultimate_day = day_idx == spec.days - 2
        next_beam: list[_State] = []

        for state in beam:
            candidate_camps = _candidate_camps_for_day(
                graph=graph,
                state=state,
                camps=camps,
                target_m=target_m,
                is_last_day=is_last_day,
                is_penultimate_day=is_penultimate_day,
                end_node=end_node,
            )

            for camp in candidate_camps:
                camp_node = camp["node_id"]
                if camp_node in state.visited_camp_nodes:
                    # forbid revisiting a camp we've already stayed at — small
                    # quality guard, makes itineraries feel like real trips
                    continue
                try:
                    path = shortest_path(graph, state.current_node, camp_node)
                except nx.NetworkXNoPath:
                    continue
                length_m = path_length_m(graph, path)
                if length_m < MIN_DAY_LENGTH_RATIO * target_m:
                    continue
                if length_m > MAX_DAY_LENGTH_RATIO * target_m:
                    continue

                gain_m = path_elevation_gain_m(graph, path)
                features_passed = _features_on_path(path, features_at_node)

                day = DaySegment(
                    day_index=day_idx,
                    path=path,
                    length_m=length_m,
                    gain_m=gain_m,
                    camp_node=camp_node,
                    camp_name=camp["name"],
                    features_passed=features_passed,
                )

                new_state = _append_day(state, day, spec, target_m, is_last_day, camp_node)
                next_beam.append(new_state)

        if not next_beam:
            return None

        next_beam.sort(key=lambda s: s.score, reverse=True)
        beam = next_beam[:beam_width]

    return _state_to_itinerary(beam[0])


def _candidate_camps_for_day(
    graph, state, camps, target_m, is_last_day, is_penultimate_day, end_node,
):
    """Candidates for the next camp, filtered by straight-line plausibility.

    On the penultimate day we additionally require the candidate to be within
    loop-back range of end_node — without this, beam search happily commits to
    camps that have no feasible return path, and then fails on the final day.
    """
    max_straight = MAX_DAY_LENGTH_RATIO * target_m * STRAIGHT_LINE_SAFETY_FACTOR
    current = state.current_node

    candidates = []
    for camp in camps:
        if is_last_day:
            if camp["node_id"] != end_node:
                continue
        else:
            if camp["node_id"] == end_node and state.days_done:
                continue
        straight = haversine_m(graph, current, camp["node_id"])
        if straight > max_straight:
            continue
        if is_penultimate_day:
            return_straight = haversine_m(graph, camp["node_id"], end_node)
            if return_straight > max_straight:
                continue
        candidates.append(camp)
    return candidates


def _features_on_path(path: list[int], features_at_node: dict[int, list[dict]]) -> list[dict]:
    seen_names: set[str] = set()
    hits: list[dict] = []
    for node in path:
        for feat in features_at_node.get(node, []):
            if feat["name"] in seen_names:
                continue
            seen_names.add(feat["name"])
            hits.append(feat)
    return hits


def _append_day(state, day, spec, target_m, is_last_day, camp_node) -> _State:
    added_score = _score_day(day, spec, target_m)
    if is_last_day and spec.is_loop:
        # bonus for cleanly closing a loop (camp_node == end_node is already
        # enforced in candidate filtering, but emphasize it in score)
        added_score += 2.0
    return _State(
        current_node=day.camp_node,
        days_done=state.days_done + [day],
        total_length_m=state.total_length_m + day.length_m,
        total_gain_m=state.total_gain_m + day.gain_m,
        score=state.score + added_score,
        visited_camp_nodes=state.visited_camp_nodes | {camp_node},
    )


def _score_day(day: DaySegment, spec: TripSpec, target_m: float) -> float:
    # mileage fit: 1.0 at target, 0.0 at 2x (or 0x) target, linear in between
    deviation_ratio = abs(day.length_m - target_m) / target_m
    mileage_fit = max(0.0, 1.0 - deviation_ratio)

    feature_reward = 0.0
    for feat in day.features_passed:
        if feat["category"] in spec.preferred_categories:
            feature_reward += 1.0
        if feat["name"] in spec.named_must_visit:
            feature_reward += 4.0

    return mileage_fit + feature_reward


def _state_to_itinerary(state: _State) -> Itinerary:
    return Itinerary(
        days=state.days_done,
        total_length_m=state.total_length_m,
        total_gain_m=state.total_gain_m,
        score=state.score,
    )
