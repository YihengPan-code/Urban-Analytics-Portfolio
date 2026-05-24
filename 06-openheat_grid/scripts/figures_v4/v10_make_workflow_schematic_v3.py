from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle

from v10_figures_style_v3 import (
    BLUE,
    GRID,
    INK,
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


def box(ax, x, y, w, h, num, title, subtitle, color):
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.022", facecolor=color, edgecolor="none", transform=ax.transAxes)
    ax.add_patch(patch)
    circ = Circle((x + 0.06*w, y + 0.62*h), 0.035, facecolor=WHITE, edgecolor="none", transform=ax.transAxes)
    ax.add_patch(circ)
    ax.text(x + 0.06*w, y + 0.62*h, str(num), transform=ax.transAxes, ha="center", va="center", color=color, fontsize=13, fontweight="bold")
    ax.text(x + 0.14*w, y + 0.63*h, title, transform=ax.transAxes, ha="left", va="center", color=WHITE, fontsize=11, fontweight="bold")
    ax.text(x + 0.14*w, y + 0.36*h, subtitle, transform=ax.transAxes, ha="left", va="center", color=WHITE, fontsize=9.5, fontweight="bold")


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), transform=ax.transAxes, arrowstyle="-|>", mutation_scale=18, lw=1.6, color=NAVY, shrinkA=0, shrinkB=0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v10/v10_final_figures_config.v2.json")
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    setup_matplotlib()
    out_dir = ensure_dir(Path(cfg["paths"]["output_dir"]) / "charts")

    fig = plt.figure(figsize=(12.8, 7.2))
    ax = fig.add_axes([0,0,1,1])
    ax.axis("off")
    add_title(fig, "OpenHeat-ToaPayoh v10 audit → correct → validate workflow", "Data-integrity correction for neighbourhood-scale tropical heat-hazard modelling")

    # Top row
    xs = [0.06, 0.30, 0.54, 0.78]
    y = 0.64
    w = 0.19
    h = 0.13
    steps = [
        (1, "v0.9 freeze", "DSM gap audit", NAVY_2, "Stop treating old ranking\nas ground truth."),
        (2, "v10-alpha", "Augmented DSM", BLUE, "DSM + manual QA +\nheight-QA review."),
        (3, "v10-beta", "Morphology shift", TEAL, "34 DSM-gap\nFP candidates."),
        (4, "v10-gamma", "UMEP reranking", TEAL, "Top20 overlap\nv08/v10 = 10/20."),
    ]
    for x, st in zip(xs, steps):
        box(ax, x, y, w, h, st[0], st[1], st[2], st[3])
        ax.text(x + w/2, y - 0.07, st[4], transform=ax.transAxes, ha="center", va="top", fontsize=8.6, color=SLATE)
    for i in range(3):
        arrow(ax, xs[i]+w+0.01, y+0.065, xs[i+1]-0.01, y+0.065)

    # robustness box
    box(ax, 0.78, 0.43, w, h, 5, "Robustness audit", "FP definitions", MUTED_ORANGE)
    arrow(ax, 0.875, y-0.015, 0.875, 0.565)

    # Bottom row from right to left
    by = 0.22
    bx = [0.06, 0.30, 0.54]
    bottom = [
        (8, "v10-final", "Confident/caveated map", NAVY_2),
        (7, "v10-epsilon", "SOLWEIG validation", BLUE),
        (6, "v10-delta", "Overhead sensitivity", TEAL),
    ]
    for x, st in zip(bx, bottom):
        box(ax, x, by, w, h, st[0], st[1], st[2], st[3])
    arrow(ax, 0.875, 0.43, 0.635, by+h/2)
    arrow(ax, bx[2]-0.02, by+h/2, bx[1]+w+0.015, by+h/2)
    arrow(ax, bx[1]-0.02, by+h/2, bx[0]+w+0.015, by+h/2)

    # Three-map framework callout
    callout = FancyBboxPatch((0.06, 0.105), 0.88, 0.055, boxstyle="round,pad=0.012,rounding_size=0.012", facecolor="#F4F5F7", edgecolor="none", transform=ax.transAxes)
    ax.add_patch(callout)
    ax.text(0.08, 0.133, "Three-map framework:", transform=ax.transAxes, ha="left", va="center", fontsize=9.5, fontweight="bold", color=NAVY)
    ax.text(0.215, 0.133, "base hazard  |  overhead sensitivity  |  confident/caveated interpretation", transform=ax.transAxes, ha="left", va="center", fontsize=9.2, color=SLATE)
    ax.text(0.78, 0.133, "Anchors: TP_0565, TP_0986", transform=ax.transAxes, ha="right", va="center", fontsize=9.2, color=NAVY)

    add_footer(fig, cfg["labels"].get("footer", "OpenHeat-ToaPayoh v10"))
    out = out_dir / "chart_00_v10_workflow_schematic"
    save_figure(fig, out, dpi=cfg["map"].get("dpi", 300), png=cfg["map"].get("png", True), svg=cfg["map"].get("svg", True))
    plt.close(fig)
    print(f"[OK] {out}.png/.svg")


if __name__ == "__main__":
    main()
