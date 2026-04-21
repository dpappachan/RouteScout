"""Curate Yosemite features (peaks, lakes, meadows, passes, waterfalls) from OSM
and snap each one to its nearest trail-graph node.

The optimizer scores candidate routes by how close they pass to named features
at overnight positions and along the way. Working off OSM tags and then
filtering gives a higher-quality seed list than hand-typing 50 entries and is
trivially re-runnable when we widen scope beyond Yosemite.

Run:
    python -m backend.graph.features
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import osmnx as ox
import pandas as pd

from .build import BBOX, DATA_DIR, PLACE, build

FEATURES_PATH = DATA_DIR / "sierra_features.json"
LEGACY_FEATURES_PATH = DATA_DIR / "yosemite_features.json"

# A feature farther than this from any trail node is effectively unreachable
# and just pollutes the optimizer's scoring. Half-km matches hiker intuition.
MAX_SNAP_DISTANCE_M = 500

OSM_TAGS = {
    "natural": ["peak", "water", "meadow", "saddle"],
    "landuse": "meadow",
    "mountain_pass": True,
    "waterway": "waterfall",
    "tourism": "viewpoint",
}


def _cell(row, key, default=None):
    """Safely read a GeoDataFrame row cell — missing columns and NaN both
    return the default."""
    if key not in row:
        return default
    v = row[key]
    if isinstance(v, float) and math.isnan(v):
        return default
    return v


def _category(row) -> str | None:
    nat = _cell(row, "natural")
    mp = _cell(row, "mountain_pass")
    ww = _cell(row, "waterway")
    lu = _cell(row, "landuse")
    water = _cell(row, "water")
    tourism = _cell(row, "tourism")

    if nat == "peak":
        return "peak"
    if nat == "saddle" or mp == "yes":
        return "pass"
    if ww == "waterfall":
        return "waterfall"
    if tourism == "viewpoint":
        return "viewpoint"
    if nat == "water":
        # `water` sub-tag distinguishes lakes from rivers/streams; skip flowing water
        if water in (None, "lake", "pond", "reservoir"):
            return "lake"
        return None
    if nat == "meadow" or lu == "meadow":
        return "meadow"
    return None


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def curate() -> list[dict]:
    print("Loading trail graph...")
    graph = build()

    print(f"Pulling OSM features: {PLACE}")
    gdf = ox.features_from_bbox(
        bbox=(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"]),
        tags=OSM_TAGS,
    )
    print(f"  raw features returned: {len(gdf):,}")

    staged: list[dict] = []
    for _, row in gdf.iterrows():
        name = _cell(row, "name")
        if not isinstance(name, str) or not name.strip():
            continue
        category = _category(row)
        if category is None:
            continue
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        pt = geom if geom.geom_type == "Point" else geom.representative_point()
        staged.append({"name": name.strip(), "category": category, "lat": pt.y, "lon": pt.x})

    print(f"  named & categorized:     {len(staged):,}")

    print("Snapping features to nearest trail nodes...")
    xs = [f["lon"] for f in staged]
    ys = [f["lat"] for f in staged]
    node_ids = ox.distance.nearest_nodes(graph, X=xs, Y=ys)

    kept: list[dict] = []
    dropped_too_far = 0
    seen: set[tuple[str, str]] = set()
    for feat, node_id in zip(staged, node_ids):
        node = graph.nodes[node_id]
        snap_m = _haversine_m(feat["lat"], feat["lon"], node["y"], node["x"])
        if snap_m > MAX_SNAP_DISTANCE_M:
            dropped_too_far += 1
            continue
        dedupe_key = (feat["name"], feat["category"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        kept.append({
            "name": feat["name"],
            "category": feat["category"],
            "lat": round(feat["lat"], 6),
            "lon": round(feat["lon"], 6),
            "node_id": int(node_id),
            "snap_distance_m": round(snap_m, 1),
            "node_elevation_m": round(node.get("elevation", 0.0), 1),
        })

    kept.sort(key=lambda f: (f["category"], f["name"]))
    print(f"  dropped (> {MAX_SNAP_DISTANCE_M} m from any trail): {dropped_too_far}")
    print(f"  kept:                    {len(kept):,}")

    FEATURES_PATH.write_text(json.dumps(kept, indent=2))
    print(f"Saved: {FEATURES_PATH}")

    _summarize(kept)
    _audit_sac_scale(graph)
    return kept


def _summarize(features: list[dict]) -> None:
    counts = Counter(f["category"] for f in features)
    print("--- features by category ---")
    for cat in ("peak", "lake", "waterfall", "viewpoint", "meadow", "pass"):
        print(f"  {cat:10} {counts.get(cat, 0)}")
    print(f"  total      {len(features)}")


def _audit_sac_scale(graph) -> None:
    total = graph.number_of_edges()
    tagged = 0
    distribution: Counter[str] = Counter()
    for _, _, data in graph.edges(data=True):
        val = data.get("sac_scale")
        if val:
            tagged += 1
            distribution[str(val)] += 1
    pct = 100.0 * tagged / total if total else 0.0
    print(f"--- sac_scale coverage: {tagged}/{total} edges ({pct:.1f}%) ---")
    if distribution:
        for grade, n in distribution.most_common():
            print(f"    {grade}: {n}")


def features_path() -> Path:
    """Returns the live features file path, falling back to the legacy
    yosemite_features.json so the app keeps working until the rebuild."""
    if FEATURES_PATH.exists():
        return FEATURES_PATH
    return LEGACY_FEATURES_PATH


if __name__ == "__main__":
    curate()
