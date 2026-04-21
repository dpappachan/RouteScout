"""Load hand-curated Sierra trailheads and snap each to its nearest trail
graph node.

Trailheads are distinct from features: features are *destinations* (peaks,
lakes, waterfalls), trailheads are *where you park your car*. Every hike has
to start and end at a trailhead — having the planner start at a summit would
produce plans that are physically impossible to begin.

Coverage spans Yosemite NP plus Ansel Adams, Hoover, and Emigrant Wildernesses.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import osmnx as ox

from .build import DATA_DIR, build

# Source JSON name kept as `yosemite_trailheads.json` for git history continuity;
# the contents now span the wider Sierra coverage area.
TRAILHEADS_SOURCE = DATA_DIR / "yosemite_trailheads.json"
TRAILHEADS_SNAPPED = DATA_DIR / "sierra_trailheads_snapped.json"

MAX_SNAP_DISTANCE_M = 1500  # trailheads sit by the road — allow more tolerance


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def build_trailheads(force: bool = False) -> list[dict]:
    """Snap each curated trailhead to its nearest trail-graph node. Caches to
    data/yosemite_trailheads_snapped.json so we don't repeat the snap on every
    start."""
    if TRAILHEADS_SNAPPED.exists() and not force:
        return json.loads(TRAILHEADS_SNAPPED.read_text())

    graph = build()
    raw = json.loads(TRAILHEADS_SOURCE.read_text())

    xs = [th["lon"] for th in raw]
    ys = [th["lat"] for th in raw]
    node_ids = ox.distance.nearest_nodes(graph, X=xs, Y=ys)

    snapped: list[dict] = []
    dropped: list[str] = []
    for th, node_id in zip(raw, node_ids):
        node = graph.nodes[node_id]
        snap_m = _haversine_m(th["lat"], th["lon"], node["y"], node["x"])
        if snap_m > MAX_SNAP_DISTANCE_M:
            dropped.append(f"{th['name']} ({snap_m:.0f} m from graph)")
            continue
        snapped.append({
            **th,
            "node_id": int(node_id),
            "snap_distance_m": round(snap_m, 1),
        })

    snapped.sort(key=lambda t: t["name"])
    TRAILHEADS_SNAPPED.write_text(json.dumps(snapped, indent=2))
    if dropped:
        print(f"trailheads dropped (> {MAX_SNAP_DISTANCE_M} m from any trail): {dropped}")
    return snapped


@lru_cache(maxsize=1)
def trailheads() -> list[dict]:
    return build_trailheads()


if __name__ == "__main__":
    ths = build_trailheads(force=True)
    print(f"Snapped {len(ths)} trailheads:")
    for t in ths:
        print(f"  {t['name']:42}  node={t['node_id']:<12}  snap={t['snap_distance_m']:>6.1f} m")
