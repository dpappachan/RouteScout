"""Build and cache the Yosemite trail graph.

Downloads hiking trails from OpenStreetMap (paths, footways, tracks, bridleways,
steps), stitches them into a NetworkX graph via OSMnx, annotates nodes with
elevation, computes edge grades (rise/run), and saves the result to GraphML so
subsequent runs load in seconds instead of minutes.

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
GRAPH_PATH = DATA_DIR / "yosemite_graph.graphml"

# Keep OSMnx's Overpass cache inside data/ so the repo root stays tidy.
ox.settings.cache_folder = str(DATA_DIR / "cache")

# Hiking-relevant OSM highway tags. Deliberately excludes roads: a router that
# thinks you can "walk" Tioga Road isn't useful.
HIKING_FILTER = '["highway"~"path|footway|track|bridleway|steps"]'

PLACE = "Yosemite National Park, California, USA"


def build(rebuild: bool = False):
    """Return the Yosemite trail graph (load from cache unless rebuild=True)."""
    if GRAPH_PATH.exists() and not rebuild:
        print(f"Loading cached graph: {GRAPH_PATH.name}")
        return ox.load_graphml(GRAPH_PATH)

    print(f"Downloading OSM trail network for: {PLACE}")
    graph = ox.graph_from_place(
        PLACE,
        custom_filter=HIKING_FILTER,
        simplify=True,
        retain_all=False,
    )
    # `retain_all=False` keeps only the largest weakly-connected component — you
    # can't plan a route across disconnected islands of trail, so we drop them.
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
    parser = argparse.ArgumentParser(description="Build the Yosemite trail graph.")
    parser.add_argument("--rebuild", action="store_true", help="Force re-download and re-elevation.")
    args = parser.parse_args()
    build(rebuild=args.rebuild)


if __name__ == "__main__":
    main()
