"""Build and cache the Sierra trail graph.

Coverage region: Yosemite National Park plus the contiguous wilderness
areas backpackers actually plan trips through —
  · Ansel Adams Wilderness (south, JMT corridor — Thousand Island Lake,
    Banner Peak, Mount Ritter)
  · Hoover Wilderness (east, Twin Lakes / Robinson Creek)
  · Emigrant Wilderness (north, Sonora Pass area)

Filters to hiking-relevant OSM `highway` tags only (path, footway, track,
bridleway, steps), keeps the largest weakly-connected trail component,
annotates every node with SRTM elevation via Open-Elevation, and computes
per-edge grade (rise/run) used by the difficulty heuristic.

Run directly:
    python -m backend.graph.build            # cached if available
    python -m backend.graph.build --rebuild  # force re-download
"""
from __future__ import annotations

import argparse
from pathlib import Path

import networkx as nx
import osmnx as ox

from . import elevation

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
GRAPH_PATH = DATA_DIR / "sierra_graph.graphml"
LEGACY_GRAPH_PATH = DATA_DIR / "yosemite_graph.graphml"

# Keep OSMnx's Overpass cache inside data/ so the repo root stays tidy.
ox.settings.cache_folder = str(DATA_DIR / "cache")

# Hiking-relevant OSM highway tags. Deliberately excludes roads: a router that
# thinks you can "walk" Tioga Road isn't useful.
HIKING_FILTER = '["highway"~"path|footway|track|bridleway|steps"]'

# Bounding box covering Yosemite + Ansel Adams + Hoover + Emigrant. Chosen
# to be tight enough that we don't pull in farmland or town footpaths but
# wide enough to capture full trail networks of all four wildernesses.
#   north: 38.35  (cuts top of Emigrant near Sonora Pass)
#   south: 37.45  (cuts bottom of Ansel Adams / Mariposa Grove)
#   east:  -118.95 (eastern slope of Hoover, just past Lee Vining)
#   west:  -119.95 (western edge of Stanislaus NF)
BBOX = {
    "north": 38.35,
    "south": 37.45,
    "east": -118.95,
    "west": -119.95,
}

# Used in user-facing messages and the LLM system prompt.
PLACE = "Yosemite + Ansel Adams + Hoover + Emigrant Wilderness"


def build(rebuild: bool = False):
    """Return the Sierra trail graph (load from cache unless rebuild=True)."""
    if GRAPH_PATH.exists() and not rebuild:
        print(f"Loading cached graph: {GRAPH_PATH.name}")
        return ox.load_graphml(GRAPH_PATH)

    # Smooth migration: if a legacy yosemite_graph.graphml exists but no
    # sierra_graph.graphml, fall back to it so the app keeps working until
    # the rebuild completes.
    if LEGACY_GRAPH_PATH.exists() and not rebuild:
        print(f"Loading legacy cached graph: {LEGACY_GRAPH_PATH.name}")
        return ox.load_graphml(LEGACY_GRAPH_PATH)

    print(f"Downloading OSM trail network for: {PLACE}")
    print(f"  bbox: N={BBOX['north']} S={BBOX['south']} W={BBOX['west']} E={BBOX['east']}")

    # OSMnx 2.x graph_from_bbox takes bbox as (left, bottom, right, top).
    graph = ox.graph_from_bbox(
        bbox=(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"]),
        custom_filter=HIKING_FILTER,
        simplify=True,
        retain_all=False,
    )
    # `retain_all=False` keeps only the largest weakly-connected component —
    # you can't plan a route across disconnected islands of trail.
    print(f"  nodes={graph.number_of_nodes():,}  edges={graph.number_of_edges():,}")

    print("Annotating nodes with SRTM elevation (Open-Elevation)...")
    elevation.annotate_nodes(graph)

    print("Computing edge grades...")
    graph = ox.elevation.add_edge_grades(graph)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, GRAPH_PATH)
    print(f"Saved: {GRAPH_PATH}")

    _print_summary(graph)
    return graph


def _print_summary(graph) -> None:
    elevs = [d["elevation"] for _, d in graph.nodes(data=True) if "elevation" in d]
    print("--- summary ---")
    print(f"  nodes:     {graph.number_of_nodes():,}")
    print(f"  edges:     {graph.number_of_edges():,}")
    if elevs:
        print(f"  elevation: min={min(elevs):.0f} m  max={max(elevs):.0f} m")
    print(f"  connected: {nx.is_weakly_connected(graph)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Sierra trail graph.")
    parser.add_argument("--rebuild", action="store_true", help="Force re-download and re-elevation.")
    args = parser.parse_args()
    build(rebuild=args.rebuild)


if __name__ == "__main__":
    main()
