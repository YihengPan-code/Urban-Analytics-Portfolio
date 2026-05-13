from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle

from v10_figures_style_v3 import (
    BLUE,
    GRID,
    MUTED_ORANGE,
    NAVY,
    NAVY_2,
    SLATE,
    TEAL,
    WHITE,
    add_footer,
    add_title,
    ensure_dir,
    save_figure,
    setup_matplotlib,
)


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def draw_box(ax, x, y, w, h, num, title, subtitle, color):
    """Compact rounded workflow box with non-overlapping badge/text."""
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.010,rounding_size=0.018",
        facecolor=color,
        edgecolor="none",
        transform=ax.transAxes,
        zorder=2,
    )
    ax.add_patch(patch)

    # Fixed-size badge in axes coordinates.  Earlier versions scaled the badge too
    # large relative to text, causing overlap in the exported PNG.
    r = 0.020
    cx = x + 0.030
    cy = y + h * 0.64
    circ = Circle((cx, cy), r, facecolor=WHITE, edgecolor="none", transform=ax.transAxes, zorder=3)
    ax.add_patch(circ)
    ax.text(cx, cy, str(num), transform=ax.transAxes, ha="center", va="center", color=color, fontsize=9.5, fontweight="bold", zorder=4)

    tx = x + 0.060
    ax.text(tx, y + h * 0.64, title, transform=ax.transAxes, ha="left", va="center", color=WHITE, fontsize=8.8, fontweight="bold", zorder=4)
    ax.text(tx, y + h * 0.38, subtitle, transform=ax.transAxes, ha="left", va="center", color=WHITE, fontsize=7.8, fontweight="bold", zorder=4)


def arrow(ax, x1, y1, x2, y2, *, rad=0.0):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        transform=ax.transAxes,
        arrowstyle="-|>",
        connectionstyle=f"arc3,rad={rad}",
        mutation_scale=14,
        lw=1.35,
        color=NAVY,
        shrinkA=0,
        shrinkB=0,
        zorder=1,
    ))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v10/v10_final_figures_config.v4.json")
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    setup_matplotlib()
    out_dir = ensure_dir(Path(cfg["paths"]["output_dir"]) / "charts")

    fig = plt.figure(figsize=(13.2, 7.35))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    add_title(
        fig,
        "OpenHeat-ToaPayoh v10 audit → correct → validate workflow",
        "Data-integrity correction for neighbourhood-scale tropical heat-hazard modelling",
        x=0.055,
        y=0.955,
    )

    # Layout tuned to avoid any badge/text overlap and arrow collisions.
    w, h = 0.205, 0.125
    y_top = 0.645
    xs_top = [0.055, 0.305, 0.555, 0.805]
    steps_top = [
        (1, "v0.9 freeze", "DSM gap audit", NAVY_2, "Stop treating old ranking\nas ground truth."),
        (2, "v10-alpha", "Augmented DSM", BLUE, "DSM + manual QA +\nheight-QA review."),
        (3, "v10-beta", "Morphology shift", TEAL, "34 DSM-gap\nFP candidates."),
        (4, "v10-gamma", "UMEP reranking", TEAL, "Top20 overlap\nv08/v10 = 10/20."),
    ]

    for x, st in zip(xs_top, steps_top):
        draw_box(ax, x, y_top, w, h, st[0], st[1], st[2], st[3])
        ax.text(x + w/2, y_top - 0.055, st[4], transform=ax.transAxes, ha="center", va="top", fontsize=8.0, color=SLATE)
    for i in range(3):
        arrow(ax, xs_top[i] + w + 0.006, y_top + h/2, xs_top[i+1] - 0.006, y_top + h/2)

    # Robustness box. Put the note below the incoming arrow so it does not sit on top of the box text.
    x5, y5 = 0.805, 0.455
    draw_box(ax, x5, y5, w, h, 5, "Robustness audit", "FP definitions", MUTED_ORANGE)
    arrow(ax, x5 + w/2, y_top - 0.005, x5 + w/2, y5 + h + 0.004)
    ax.text(x5 + w/2, y5 + h + 0.026, "Top20 overlap\nv08/v10 = 10/20", transform=ax.transAxes, ha="center", va="bottom", fontsize=7.4, color=SLATE)

    # Bottom row.
    y_bot = 0.225
    xs_bot = [0.055, 0.305, 0.555]
    bottom = [
        (8, "v10-final", "Confident/caveated map", NAVY_2),
        (7, "v10-epsilon", "SOLWEIG validation", BLUE),
        (6, "v10-delta", "Overhead sensitivity", TEAL),
    ]
    for x, st in zip(xs_bot, bottom):
        draw_box(ax, x, y_bot, w, h, st[0], st[1], st[2], st[3])

    # Routed connector from robustness to v10-delta, avoiding crossing box labels.
    arrow(ax, x5 + w/2, y5 - 0.004, xs_bot[2] + w*0.50, y_bot + h + 0.004, rad=-0.05)
    arrow(ax, xs_bot[2] - 0.012, y_bot + h/2, xs_bot[1] + w + 0.012, y_bot + h/2)
    arrow(ax, xs_bot[1] - 0.012, y_bot + h/2, xs_bot[0] + w + 0.012, y_bot + h/2)

    # Three-map callout.
    callout = FancyBboxPatch(
        (0.055, 0.105), 0.89, 0.058,
        boxstyle="round,pad=0.010,rounding_size=0.010",
        facecolor="#F4F5F7",
        edgecolor="none",
        transform=ax.transAxes,
        zorder=1,
    )
    ax.add_patch(callout)
    ax.text(0.075, 0.134, "Three-map framework:", transform=ax.transAxes, ha="left", va="center", fontsize=9.2, fontweight="bold", color=NAVY)
    ax.text(0.210, 0.134, "base hazard  |  overhead sensitivity  |  confident/caveated interpretation", transform=ax.transAxes, ha="left", va="center", fontsize=8.6, color=SLATE)
    ax.text(0.865, 0.134, "Anchors: TP_0565, TP_0986", transform=ax.transAxes, ha="right", va="center", fontsize=8.8, color=NAVY)

    add_footer(fig, cfg["labels"].get("footer", "OpenHeat-ToaPayoh v10"))
    out = out_dir / "chart_00_v10_workflow_schematic"
    save_figure(fig, out, dpi=cfg["map"].get("dpi", 300), png=cfg["map"].get("png", True), svg=cfg["map"].get("svg", True))
    plt.close(fig)
    print(f"[OK] {out}.png/.svg")


if __name__ == "__main__":
    main()
