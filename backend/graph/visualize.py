"""Render the Sierra trail graph to a PNG, colored by node elevation, with
curated feature nodes overlaid when available.

Run directly:
    python -m backend.graph.visualize
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import osmnx as ox

from .build import DATA_DIR, PLACE, build
from .features import FEATURES_PATH

OUTPUT_PATH = DATA_DIR / "sierra_graph.png"

# marker + color per feature category (matplotlib markers)
CATEGORY_STYLE = {
    "peak":      {"marker": "^", "color": "#d62728", "label": "peak"},
    "pass":      {"marker": "v", "color": "#8c564b", "label": "pass"},
    "lake":      {"marker": "o", "color": "#1f77b4", "label": "lake"},
    "waterfall": {"marker": "*", "color": "#17becf", "label": "waterfall"},
    "viewpoint": {"marker": "s", "color": "#ff7f0e", "label": "viewpoint"},
    "meadow":    {"marker": "D", "color": "#2ca02c", "label": "meadow"},
}


def _load_features() -> list[dict]:
    if not FEATURES_PATH.exists():
        return []
    return json.loads(FEATURES_PATH.read_text())


def render(save_to: Path = OUTPUT_PATH) -> Path:
    graph = build()
    features = _load_features()

    node_data = [(data["x"], data["y"], data.get("elevation", 0.0)) for _, data in graph.nodes(data=True)]
    xs = [x for x, _, _ in node_data]
    ys = [y for _, y, _ in node_data]
    elevs = [e for _, _, e in node_data]

    fig, ax = ox.plot_graph(
        graph,
        node_size=0,
        edge_color="#888888",
        edge_linewidth=0.4,
        bgcolor="white",
        show=False,
        close=False,
    )

    scatter = ax.scatter(xs, ys, c=elevs, s=4, cmap="viridis", zorder=2, alpha=0.9)
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("elevation (m)")

    if features:
        plotted_categories: set[str] = set()
        for feat in features:
            style = CATEGORY_STYLE.get(feat["category"])
            if not style:
                continue
            label = style["label"] if feat["category"] not in plotted_categories else None
            ax.scatter(
                feat["lon"], feat["lat"],
                marker=style["marker"], c=style["color"],
                s=40, edgecolors="black", linewidths=0.5,
                zorder=4, label=label,
            )
            plotted_categories.add(feat["category"])
        ax.legend(loc="lower left", fontsize=8, frameon=True, title="features")

    title = f"{PLACE} — {graph.number_of_nodes():,} trail nodes, {graph.number_of_edges():,} edges"
    if features:
        title += f"  ·  {len(features)} features"
    ax.set_title(title)

    save_to.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_to, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_to}")
    return save_to


if __name__ == "__main__":
    render()
