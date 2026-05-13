"""Shared style helpers for OpenHeat v10 final figure set v3.

v3 updates
- optional satellite basemap support (handled in map script)
- standard map ornament positions: north arrow upper-right, scale bar lower-right
- slightly softer overlays for polygon layers on imagery
- chart and map palette remains restrained and publication-oriented
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Polygon, Rectangle
import numpy as np

# Core palette.
NAVY = "#0B1F3A"
NAVY_2 = "#16395A"
SLATE = "#5E6B7F"
SLATE_2 = "#8A96A6"
BLUE = "#2F6F8F"
BLUE_LIGHT = "#AFC7D5"
TEAL = "#0F7C7D"
MUTED_PURPLE = "#6B5C9E"
MUTED_RED = "#A64942"
MUTED_ORANGE = "#C77B3D"
MUTED_GREEN = "#5F7F5A"
WARM_GRAY = "#B6B0A8"
LIGHT_GRAY = "#E9E7E2"
VERY_LIGHT = "#F7F5F0"
INK = "#121826"
GRID = "#D9D6CE"
WHITE = "#FFFFFF"

HAZARD_CMAP = LinearSegmentedColormap.from_list(
    "openheat_hazard_muted",
    ["#F8F4E8", "#E9D1A2", "#CE8C4A", "#A64942", "#5B4774", NAVY],
)
RANK_SHIFT_CMAP = LinearSegmentedColormap.from_list(
    "openheat_diverging_muted",
    ["#2C5E7B", "#8DB5C8", "#F3F0EA", "#D9A07B", "#9B493D"],
)
OVERHEAD_CMAP = LinearSegmentedColormap.from_list(
    "openheat_overhead_muted",
    ["#F7F5F0", "#DCDCEB", "#A9A3CC", "#6B5C9E", "#352A58"],
)
BUILDING_GAIN_CMAP = LinearSegmentedColormap.from_list(
    "openheat_building_gain_muted",
    ["#F8F4E8", "#EED8B8", "#D99A73", "#BC5F4A", "#7E2634"],
)

INTERPRETATION_COLORS = {
    "confident_hotspot": "#A64942",
    "overhead_confounded": "#6B5C9E",
    "dsm_gap_corrected": "#2F6F8F",
    "dense_built_edge_case": "#5E6570",
    "shaded_reference": "#5F7F5A",
    "v10_base_top_hazard": "#C77B3D",
    "other": "#ECE9E2",
}

INTERPRETATION_LABELS = {
    "confident_hotspot": "Confident hotspot",
    "overhead_confounded": "Overhead-confounded",
    "dsm_gap_corrected": "DSM-gap corrected",
    "dense_built_edge_case": "Dense built edge case",
    "shaded_reference": "Shaded reference",
    "v10_base_top_hazard": "v10 base top hazard",
    "other": "Other cells",
}


@dataclass
class FigureStyle:
    title_size: int = 18
    subtitle_size: int = 11
    label_size: int = 10
    tick_size: int = 9
    footer_size: int = 8
    font_family: str = "DejaVu Sans"


STYLE = FigureStyle()


def setup_matplotlib() -> None:
    plt.rcParams.update({
        "font.family": STYLE.font_family,
        "axes.titlesize": STYLE.title_size,
        "axes.labelsize": STYLE.label_size,
        "xtick.labelsize": STYLE.tick_size,
        "ytick.labelsize": STYLE.tick_size,
        "legend.fontsize": STYLE.tick_size,
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
        "savefig.facecolor": WHITE,
        "savefig.edgecolor": WHITE,
        "axes.edgecolor": NAVY,
        "axes.labelcolor": INK,
        "xtick.color": SLATE,
        "ytick.color": SLATE,
        "text.color": INK,
        "axes.grid": False,
    })


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_figure(fig, out_base: str | Path, dpi: int = 300, png: bool = True, svg: bool = True) -> None:
    out_base = Path(out_base)
    ensure_dir(out_base.parent)
    if png:
        fig.savefig(out_base.with_suffix(".png"), dpi=dpi, bbox_inches="tight", pad_inches=0.08)
    if svg:
        fig.savefig(out_base.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.08)


def add_title(fig, title: str, subtitle: str = "", *, x: float = 0.06, y: float = 0.955) -> None:
    fig.text(x, y, title, ha="left", va="top", fontsize=STYLE.title_size, fontweight="bold", color=NAVY)
    if subtitle:
        fig.text(x, y - 0.045, subtitle, ha="left", va="top", fontsize=STYLE.subtitle_size, color=SLATE, style="italic")


def add_footer(fig, footer: str, *, date_label: Optional[str] = None, y: float = 0.035) -> None:
    fig.lines.append(plt.Line2D([0.06, 0.94], [y + 0.035, y + 0.035], transform=fig.transFigure, color=GRID, lw=0.8))
    fig.text(0.06, y, footer, ha="left", va="bottom", fontsize=STYLE.footer_size, color=SLATE)
    if date_label:
        fig.text(0.94, y, date_label, ha="right", va="bottom", fontsize=STYLE.footer_size, color=SLATE)


def nice_scale_length(width_m: float) -> float:
    if width_m <= 0 or not np.isfinite(width_m):
        return 1000.0
    target = width_m * 0.20
    candidates = np.array([100, 200, 250, 500, 750, 1000, 1500, 2000, 2500, 5000, 7500, 10000, 20000, 25000, 50000], dtype=float)
    return float(candidates[np.argmin(np.abs(candidates - target))])


def add_scale_bar(ax, length_m: Optional[float] = None, *, location=(0.73, 0.05), segments: int = 4) -> None:
    """Add scale bar with default lower-right placement."""
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    width = xmax - xmin
    height = ymax - ymin
    if length_m is None:
        length_m = nice_scale_length(width)
    x0 = xmin + width * location[0]
    y0 = ymin + height * location[1]
    seg_len = length_m / segments
    bar_h = height * 0.0105
    for i in range(segments):
        color = NAVY if i % 2 == 0 else WHITE
        rect = Rectangle((x0 + i * seg_len, y0), seg_len, bar_h, facecolor=color, edgecolor=NAVY, lw=0.55, zorder=50)
        ax.add_patch(rect)
    ax.text(x0, y0 - height * 0.017, "0", ha="center", va="top", fontsize=8, color=INK)
    if length_m >= 1000:
        end_label = f"{length_m/1000:g} km"
        mid_label = f"{length_m/2000:g}"
    else:
        end_label = f"{int(length_m)} m"
        mid_label = f"{int(length_m/2)}"
    ax.text(x0 + length_m / 2.0, y0 - height * 0.017, mid_label, ha="center", va="top", fontsize=8, color=INK)
    ax.text(x0 + length_m, y0 - height * 0.017, end_label, ha="center", va="top", fontsize=8, color=INK)


def add_north_arrow(ax, *, location=(0.92, 0.84), size: float = 0.050) -> None:
    """Add stylized north arrow with default upper-right placement."""
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    width = xmax - xmin
    height = ymax - ymin
    cx = xmin + width * location[0]
    cy = ymin + height * location[1]
    s = min(width, height) * size
    tri = np.array([[cx, cy + s], [cx - s * 0.42, cy - s * 0.55], [cx, cy - s * 0.18], [cx + s * 0.42, cy - s * 0.55]])
    ax.add_patch(Polygon(tri, closed=True, facecolor=NAVY, edgecolor=NAVY, lw=0.8, zorder=60))
    ax.add_patch(Polygon(np.array([[cx, cy + s*0.72], [cx, cy - s*0.05], [cx + s*0.28, cy - s*0.42]]), closed=True, facecolor=WHITE, edgecolor=WHITE, lw=0, zorder=61, alpha=0.92))
    ax.text(cx, cy + s * 1.16, "N", ha="center", va="center", fontsize=10, color=NAVY, fontweight="bold", zorder=62)


def plot_aoi_outline(ax, gdf, *, color: str = NAVY, linewidth: float = 1.0) -> None:
    try:
        outline = gdf.unary_union
        import geopandas as gpd
        gpd.GeoSeries([outline], crs=gdf.crs).boundary.plot(ax=ax, color=color, linewidth=linewidth, zorder=45)
    except Exception:
        gdf.boundary.plot(ax=ax, color=color, linewidth=linewidth, zorder=45)


def set_equal_extent(ax, gdf, *, pad_frac: float = 0.04) -> None:
    minx, miny, maxx, maxy = gdf.total_bounds
    dx = maxx - minx
    dy = maxy - miny
    pad = max(dx, dy) * pad_frac
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal")
    ax.axis("off")
