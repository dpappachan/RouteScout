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

# A real backpacker camps near water, on flat ground — not on summits or
# clifftop viewpoints. OSM categories with reliable water + camp-able
# terrain in Yosemite are lakes and meadows.
CAMP_CATEGORIES = frozenset({"lake", "meadow"})

# Penalty for walking trail segments already used on a previous day. Scaled
# by overlap fraction (0–1) so the strongest possible penalty per day is
# this constant. Set high enough to break ties decisively but not so high
# that the search refuses geographically necessary out-and-back returns.
EDGE_REUSE_PENALTY = 3.0


@dataclass
class _State:
    current_node: int
    days_done: list[DaySegment] = field(default_factory=list)
    total_length_m: float = 0.0
    total_gain_m: float = 0.0
    score: float = 0.0
    visited_camp_nodes: frozenset[int] = field(default_factory=frozenset)
    # frozenset of canonicalized (min(u,v), max(u,v)) edge keys we've walked
    visited_edges: frozenset = field(default_factory=frozenset)


def plan(
    graph: nx.MultiDiGraph,
    features: list[dict],
    trailheads: list[dict],
    camps: list[dict],
    spec: TripSpec,
    beam_width: int = 12,
    adaptive: bool = False,
) -> Itinerary | None:
    """Plan an itinerary. If `adaptive=True`, transparently widens the beam
    (×2, ×3) before declaring infeasibility — feature-preference scoring can
    push the top-K toward dead-end branches that fail the penultimate-day
    lookahead, and a wider beam gives the search more breathing room."""
    if adaptive:
        for bw in (beam_width, beam_width * 2, beam_width * 3):
            result = _plan_once(graph, features, trailheads, camps, spec, bw)
            if result is not None:
                return result
        return None
    return _plan_once(graph, features, trailheads, camps, spec, beam_width)


def _plan_once(
    graph: nx.MultiDiGraph,
    features: list[dict],
    trailheads: list[dict],
    camps: list[dict],
    spec: TripSpec,
    beam_width: int,
) -> Itinerary | None:
    trailheads_by_name: dict[str, dict] = {t["name"]: t for t in trailheads}
    if spec.start not in trailheads_by_name:
        raise ValueError(
            f"Unknown start trailhead '{spec.start}'. "
            f"Valid trailheads: {list(trailheads_by_name)}"
        )
    end_name = spec.end or spec.start
    if end_name not in trailheads_by_name:
        raise ValueError(f"Unknown end trailhead '{end_name}'.")

    start_node = trailheads_by_name[spec.start]["node_id"]
    end_node = trailheads_by_name[end_name]["node_id"]

    features_by_name: dict[str, dict] = {f["name"]: f for f in features}

    # node_id -> list of features at that node (for path-hit detection)
    features_at_node: dict[int, list[dict]] = defaultdict(list)
    for f in features:
        features_at_node[f["node_id"]].append(f)

    # Day-hike loops (days=1 + end=start) can't be planned by the usual
    # multi-day beam search — a zero-length "segment from X to X" has no
    # midpoint. Route them as out-and-back to a scenic destination instead.
    if spec.days == 1 and spec.is_loop:
        return _plan_day_hike(graph, features, features_by_name, features_at_node, spec, start_node)

    # `camps` is the precomputed terrain-based candidate list; nothing more
    # to filter here.

    target_m = spec.target_m_per_day
    beam: list[_State] = [_State(current_node=start_node)]

    for day_idx in range(spec.days):
        is_last_day = day_idx == spec.days - 1
        is_penultimate_day = day_idx == spec.days - 2
        # Per-day mileage target: shorter on first/last day for 3+ day trips.
        # Used ONLY in scoring — the candidate filter bands stay at the
        # base target so we don't artificially shrink the search space.
        day_target_m = _per_day_target(target_m, day_idx, spec.days)
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
                end_name=end_name,
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

                new_state = _append_day(state, day, spec, day_target_m, is_last_day, camp_node)
                next_beam.append(new_state)

        if not next_beam:
            return None

        next_beam.sort(key=lambda s: s.score, reverse=True)
        beam = next_beam[:beam_width]

    itinerary = _state_to_itinerary(beam[0])
    _relabel_last_day_camp(itinerary, end_node, spec)
    return itinerary


def _plan_day_hike(
    graph, features, features_by_name, features_at_node, spec, start_node,
) -> Itinerary | None:
    """Pick a scenic destination at roughly half the target distance from
    start, route there and back, return as a single-day itinerary.

    We score each candidate destination on (a) how close the round-trip is to
    the target mileage, (b) how many preferred-category features the path
    passes, with a bonus for the destination itself matching a preference.
    """
    target_m = spec.target_m_per_day
    best: tuple[float, DaySegment] | None = None

    for destination in features:
        dest_node = destination["node_id"]
        if dest_node == start_node:
            continue
        straight = haversine_m(graph, start_node, dest_node)
        # straight-line from start to destination should be <= half of max
        # round-trip; prune aggressively to keep this fast
        if straight > MAX_DAY_LENGTH_RATIO * target_m / 2:
            continue
        try:
            out_path = shortest_path(graph, start_node, dest_node)
            back_path = shortest_path(graph, dest_node, start_node)
        except nx.NetworkXNoPath:
            continue

        full_path = out_path + back_path[1:]
        length_m = path_length_m(graph, full_path)
        if length_m < MIN_DAY_LENGTH_RATIO * target_m:
            continue
        if length_m > MAX_DAY_LENGTH_RATIO * target_m:
            continue

        gain_m = path_elevation_gain_m(graph, full_path)
        features_passed = _features_on_path(full_path, features_at_node)

        day = DaySegment(
            day_index=0,
            path=full_path,
            length_m=length_m,
            gain_m=gain_m,
            camp_node=start_node,
            camp_name=spec.start,
            features_passed=features_passed,
        )
        score = _score_day(day, spec, target_m)
        if destination["category"] in spec.preferred_categories:
            score += 1.5  # turnaround point matters more than a drive-by feature
        if best is None or score > best[0]:
            best = (score, day)

    if best is None:
        return None

    _, day = best
    return Itinerary(
        days=[day],
        total_length_m=day.length_m,
        total_gain_m=day.gain_m,
        score=best[0],
    )


def _relabel_last_day_camp(itinerary: Itinerary, end_node: int, spec: TripSpec) -> None:
    """When the final day lands at the trailhead node, the optimizer may label
    it with whichever feature happens to also snap to that node. Force the
    display to match the declared trailhead for clarity."""
    if not itinerary.days:
        return
    end_name = spec.end or spec.start
    last_day = itinerary.days[-1]
    if last_day.camp_node == end_node:
        last_day.camp_name = end_name


def _candidate_camps_for_day(
    graph, state, camps, target_m, is_last_day, is_penultimate_day, end_node, end_name,
):
    """Candidates for the next camp, filtered by straight-line plausibility.

    On the last day the candidate MUST land at the end trailhead node, which
    is typically not in the features list, so we synthesize an end-of-trip
    camp pointing at it. On the penultimate day we additionally require the
    candidate to be within loop-back range of end_node — without this, beam
    search happily commits to camps that have no feasible return path, and
    then fails on the final day.
    """
    if is_last_day:
        # The "camp" at the end of the trip is just the trailhead — we don't
        # literally camp at a parking lot. The optimizer treats it as the
        # terminal node for the search.
        return [{"name": end_name, "node_id": end_node, "category": "trailhead"}]

    max_straight = MAX_DAY_LENGTH_RATIO * target_m * STRAIGHT_LINE_SAFETY_FACTOR
    current = state.current_node

    candidates = []
    for camp in camps:
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

    new_edges = _path_edges(day.path)
    overlap = new_edges & state.visited_edges
    if new_edges:
        overlap_fraction = len(overlap) / len(new_edges)
        added_score -= overlap_fraction * EDGE_REUSE_PENALTY

    return _State(
        current_node=day.camp_node,
        days_done=state.days_done + [day],
        total_length_m=state.total_length_m + day.length_m,
        total_gain_m=state.total_gain_m + day.gain_m,
        score=state.score + added_score,
        visited_camp_nodes=state.visited_camp_nodes | {camp_node},
        visited_edges=state.visited_edges | new_edges,
    )


def _per_day_target(base_target_m: float, day_idx: int, days_total: int) -> float:
    """Bias day 1 (drove in) and day N (drive out) shorter, middle days
    longer. No-op for short trips where adjustment would be excessive."""
    if days_total < 3:
        return base_target_m
    if day_idx == 0:
        return base_target_m * 0.75
    if day_idx == days_total - 1:
        return base_target_m * 0.85
    # middle-day boost: total mileage stays roughly proportional
    return base_target_m * 1.10


def _path_edges(path: list[int]) -> frozenset:
    """Canonicalized undirected edge set for a path. Direction-independent so
    walking A→B then B→A counts as 100% overlap."""
    return frozenset(
        (min(u, v), max(u, v)) for u, v in zip(path[:-1], path[1:])
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
