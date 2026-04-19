"""Elevation lookup via Open-Elevation (free, SRTM-sourced), with a local JSON cache.

Open-Elevation is rate-limited and occasionally slow, so we batch requests and
persist results to disk. Re-running the graph build after the cache is warm is
effectively free.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CACHE_PATH = DATA_DIR / "elevation_cache.json"

API_URL = "https://api.open-elevation.com/api/v1/lookup"
BATCH_SIZE = 100
BETWEEN_BATCHES_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 120


def _key(lat: float, lon: float) -> str:
    return f"{round(lat, 5)},{round(lon, 5)}"


def _load_cache() -> dict[str, float]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict[str, float]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache))


def lookup(coords: list[tuple[float, float]]) -> list[float]:
    """Return elevations (meters) for a list of (lat, lon) pairs, in order."""
    cache = _load_cache()
    results: list[float | None] = [None] * len(coords)
    misses: list[tuple[int, float, float]] = []

    for i, (lat, lon) in enumerate(coords):
        cached = cache.get(_key(lat, lon))
        if cached is not None:
            results[i] = cached
        else:
            misses.append((i, lat, lon))

    total_batches = (len(misses) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_idx, start in enumerate(range(0, len(misses), BATCH_SIZE)):
        chunk = misses[start : start + BATCH_SIZE]
        payload = {"locations": [{"latitude": lat, "longitude": lon} for _, lat, lon in chunk]}
        try:
            resp = requests.post(API_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            _save_cache(cache)
            raise RuntimeError(
                f"Open-Elevation request failed on batch {batch_idx + 1}/{total_batches}: {exc}"
            ) from exc

        for (i, lat, lon), row in zip(chunk, data["results"]):
            elev = float(row["elevation"])
            results[i] = elev
            cache[_key(lat, lon)] = elev

        print(f"  elevation batch {batch_idx + 1}/{total_batches} ok")
        if batch_idx + 1 < total_batches:
            time.sleep(BETWEEN_BATCHES_SECONDS)

    _save_cache(cache)
    return [e for e in results if e is not None]  # type: ignore[misc]


def annotate_nodes(graph) -> None:
    """In-place: write an `elevation` attribute onto every node in the graph."""
    nodes = list(graph.nodes(data=True))
    coords = [(data["y"], data["x"]) for _, data in nodes]
    elevations = lookup(coords)
    for (node_id, _), elev in zip(nodes, elevations):
        graph.nodes[node_id]["elevation"] = elev
