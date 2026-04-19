"""Render the Yosemite trail graph to a PNG, colored by node elevation.

Run directly:
    python -m backend.graph.visualize
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import osmnx as ox

from .build import DATA_DIR, build

OUTPUT_PATH = DATA_DIR / "yosemite_graph.png"


def render(save_to: Path = OUTPUT_PATH) -> Path:
    graph = build()

    node_data = [(data["x"], data["y"], data.get("elevation", 0.0)) for _, data in graph.nodes(data=True)]
    xs = [x for x, _, _ in node_data]
    ys = [y for _, y, _ in node_data]
    elevs = [e for _, _, e in node_data]

    fig, ax = ox.plot_graph(
        graph,
        node_size=0,
        edge_color="#777777",
        edge_linewidth=0.4,
        bgcolor="white",
        show=False,
        close=False,
    )

    scatter = ax.scatter(xs, ys, c=elevs, s=6, cmap="viridis", zorder=3)
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("elevation (m)")

    ax.set_title(
        f"Yosemite trail graph — {graph.number_of_nodes():,} nodes, "
        f"{graph.number_of_edges():,} edges"
    )

    save_to.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_to, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_to}")
    return save_to


if __name__ == "__main__":
    render()
