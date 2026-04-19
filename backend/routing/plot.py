"""Render a planned itinerary on the trail graph.

Each day's path is drawn in a distinct color; camps are marked. The base
graph is muted so the route stands out.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import osmnx as ox

from .trip_spec import Itinerary

DAY_COLORS = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628", "#f781bf"]

# fraction of route bbox to add as padding on each side
ZOOM_PADDING = 0.15


def _zoom_to_itinerary(ax, graph, itinerary: Itinerary) -> None:
    xs, ys = [], []
    for day in itinerary.days:
        for node in day.path:
            xs.append(graph.nodes[node]["x"])
            ys.append(graph.nodes[node]["y"])
    if not xs:
        return
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    # minimum span so very short trips don't get an awkward tight crop
    span_x = max(x_max - x_min, 0.02)
    span_y = max(y_max - y_min, 0.02)
    pad_x = span_x * ZOOM_PADDING
    pad_y = span_y * ZOOM_PADDING
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    ax.set_xlim(cx - span_x / 2 - pad_x, cx + span_x / 2 + pad_x)
    ax.set_ylim(cy - span_y / 2 - pad_y, cy + span_y / 2 + pad_y)


def render_itinerary(
    graph,
    itinerary: Itinerary,
    features: list[dict],
    save_to: Path,
    title: str | None = None,
) -> Path:
    fig, ax = ox.plot_graph(
        graph,
        node_size=0,
        edge_color="#cccccc",
        edge_linewidth=0.4,
        bgcolor="white",
        show=False,
        close=False,
    )

    feature_by_node = {f["node_id"]: f for f in features}

    for i, day in enumerate(itinerary.days):
        color = DAY_COLORS[i % len(DAY_COLORS)]
        xs = [graph.nodes[n]["x"] for n in day.path]
        ys = [graph.nodes[n]["y"] for n in day.path]
        ax.plot(xs, ys, color=color, linewidth=2.4, alpha=0.9, zorder=3,
                label=f"day {i+1}: {day.length_miles:.1f} mi, {int(day.gain_m)} m gain")

        # camp marker at end of day
        camp_x = graph.nodes[day.camp_node]["x"]
        camp_y = graph.nodes[day.camp_node]["y"]
        ax.scatter(camp_x, camp_y, marker="*", c=color, s=220,
                   edgecolors="black", linewidths=0.8, zorder=5)
        ax.annotate(
            day.camp_name,
            xy=(camp_x, camp_y),
            xytext=(6, 6), textcoords="offset points",
            fontsize=8, color="black",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.75),
            zorder=6,
        )

    # start marker
    if itinerary.days:
        start_node = itinerary.days[0].path[0]
        sx, sy = graph.nodes[start_node]["x"], graph.nodes[start_node]["y"]
        ax.scatter(sx, sy, marker="o", c="black", s=100, zorder=6)
        start_label = feature_by_node.get(start_node, {}).get("name", "start")
        ax.annotate(
            f"start: {start_label}",
            xy=(sx, sy), xytext=(6, -12), textcoords="offset points",
            fontsize=8, color="black",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.75),
            zorder=6,
        )

    _zoom_to_itinerary(ax, graph, itinerary)

    ax.legend(loc="lower left", fontsize=8, frameon=True)
    if title:
        ax.set_title(title)

    save_to.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_to, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {save_to}")
    return save_to
