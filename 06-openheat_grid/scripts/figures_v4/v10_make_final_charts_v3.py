from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from v10_figures_style_v3 import (
    BLUE,
    GRID,
    MUTED_ORANGE,
    MUTED_PURPLE,
    MUTED_RED,
    NAVY,
    SLATE,
    WARM_GRAY,
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


def read_csv_optional(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        print(f"[WARN] Missing optional CSV: {p}")
        return pd.DataFrame()
    return pd.read_csv(p)


def first_present(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def add_panel_header(ax, text: str):
    ax.add_patch(plt.Rectangle((0, 1.02), 1, 0.08, transform=ax.transAxes, color=NAVY, clip_on=False))
    ax.text(0.5, 1.06, text, transform=ax.transAxes, ha="center", va="center", color=WHITE, fontsize=11, fontweight="bold")


def make_tmrt_timeseries(cfg: dict):
    df = read_csv_optional(cfg["paths"].get("epsilon_tmrt_summary_csv", ""))
    if df.empty:
        return

    hour_col = first_present(df, ["tmrt_hour_sgt", "hour", "time_hour"])
    if hour_col is None:
        if "tmrt_time_label" in df.columns:
            df["tmrt_hour_sgt"] = pd.to_numeric(df["tmrt_time_label"], errors="coerce") / 100
            hour_col = "tmrt_hour_sgt"
        else:
            print("[WARN] No hour column found; skipping chart_01")
            return
    value_col = first_present(df, ["tmrt_mean_c", "tmrt_mean", "mean_tmrt_c"])
    if value_col is None:
        print("[WARN] No Tmrt mean column found; skipping timeseries")
        return
    delta_df = read_csv_optional(cfg["paths"].get("epsilon_tmrt_comparison_csv", ""))
    delta_col = first_present(delta_df, ["delta_overhead_minus_base_c", "delta", "tmrt_delta_c"])
    delta_by_cell = {}
    if not delta_df.empty and delta_col:
        delta_by_cell = delta_df.groupby("cell_id")[delta_col].mean().to_dict()

    role_col = "role" if "role" in df.columns else None
    scenario_col = "scenario"
    order = ["TP_0565", "TP_0986", "TP_0088", "TP_0916", "TP_0433"]
    role_colors = {
        "confident_hot_anchor_1": MUTED_RED,
        "confident_hot_anchor_2": "#7E2E2A",
        "overhead_confounded_rank1_case": MUTED_PURPLE,
        "saturated_overhead_case": "#4E5D87",
        "clean_shaded_reference": "#647582",
    }
    cell_default = {
        "TP_0565": MUTED_RED,
        "TP_0986": "#7E2E2A",
        "TP_0088": MUTED_PURPLE,
        "TP_0916": "#4E5D87",
        "TP_0433": "#647582",
    }
    role_labels = {
        "TP_0565": "confident hotspot",
        "TP_0986": "confident hotspot",
        "TP_0088": "overhead-confounded",
        "TP_0916": "overhead-saturated",
        "TP_0433": "shaded reference",
    }

    fig = plt.figure(figsize=(10.8, 9.6))
    add_title(fig, "v10-epsilon SOLWEIG Tmrt time series", "Focus-cell mean Tmrt (°C): small-multiple view of base vs overhead scenario")

    axes = []
    left, width = 0.10, 0.73
    start_y, h, gap = 0.14, 0.11, 0.03
    # create top-to-bottom axes
    for i in range(5):
        y = start_y + (4 - i) * (h + gap)
        ax = fig.add_axes([left, y, width, h])
        axes.append(ax)

    x_all = sorted(pd.to_numeric(df[hour_col], errors="coerce").dropna().unique())
    global_min = pd.to_numeric(df[value_col], errors="coerce").min()
    global_max = pd.to_numeric(df[value_col], errors="coerce").max()
    ypad = max(0.8, 0.06 * (global_max - global_min))

    for ax, cell in zip(axes, order):
        sub = df[df["cell_id"].astype(str) == cell].copy()
        if sub.empty:
            ax.axis("off")
            continue
        role = str(sub[role_col].dropna().iloc[0]) if role_col and not sub[role_col].dropna().empty else cell
        color = role_colors.get(role, cell_default.get(cell, BLUE))

        for scenario, linestyle, marker, alpha in [("base", "-", "o", 0.95), ("overhead", "--", "s", 0.85)]:
            ss = sub[sub[scenario_col].astype(str).str.lower() == scenario].copy()
            if ss.empty:
                continue
            ss[hour_col] = pd.to_numeric(ss[hour_col], errors="coerce")
            ss[value_col] = pd.to_numeric(ss[value_col], errors="coerce")
            ss = ss.sort_values(hour_col)
            ax.plot(ss[hour_col], ss[value_col], linestyle=linestyle, marker=marker, color=color, alpha=alpha, lw=2.0, ms=4.5)

        ax.set_xlim(min(x_all) - 0.2, max(x_all) + 0.2)
        ax.set_ylim(global_min - ypad, global_max + ypad)
        ax.grid(True, color=GRID, linewidth=0.7, linestyle="--", alpha=0.8)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(NAVY)
        ax.tick_params(axis="x", labelbottom=(ax is axes[-1]))
        ax.text(0.01, 0.88, cell, transform=ax.transAxes, ha="left", va="top", fontsize=10.5, fontweight="bold", color=NAVY)
        ax.text(0.01, 0.70, role_labels.get(cell, role.replace("_", " ")), transform=ax.transAxes, ha="left", va="top", fontsize=8.5, color=SLATE)
        d = delta_by_cell.get(cell, np.nan)
        if pd.notna(d):
            ax.text(0.99, 0.86, f"mean ΔTmrt = {d:+.1f}°C", transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=NAVY,
                    bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=GRID, lw=0.7, alpha=0.92))

    axes[2].set_ylabel("Focus-cell mean Tmrt (°C)")
    axes[-1].set_xlabel("Hour (SGT)")

    legend_handles = [
        Line2D([0], [0], color="#555555", lw=2.2, linestyle="-", marker="o", ms=5, label="Base scenario"),
        Line2D([0], [0], color="#555555", lw=2.2, linestyle="--", marker="s", ms=5, label="Overhead scenario"),
    ]
    fig.legend(handles=legend_handles, loc="upper right", bbox_to_anchor=(0.94, 0.905), frameon=True, facecolor=WHITE, edgecolor=GRID, ncol=1, title="Scenario", title_fontsize=9)

    add_footer(fig, cfg["labels"].get("footer", "OpenHeat-ToaPayoh v10"))
    out = Path(cfg["paths"]["output_dir"]) / "charts" / "chart_01_epsilon_tmrt_timeseries"
    save_figure(fig, out, dpi=cfg["map"].get("dpi", 300), png=cfg["map"].get("png", True), svg=cfg["map"].get("svg", True))
    plt.close(fig)
    print(f"[OK] {out}.png/.svg")


def make_tmrt_delta_bars(cfg: dict):
    df = read_csv_optional(cfg["paths"].get("epsilon_tmrt_comparison_csv", ""))
    if df.empty:
        return
    delta_col = first_present(df, ["delta_overhead_minus_base_c", "delta", "tmrt_delta_c"])
    if delta_col is None:
        print("[WARN] No delta column found; skipping delta bars")
        return
    group_cols = ["cell_id"]
    if "role" in df.columns:
        group_cols.append("role")
    mean = df.groupby(group_cols, as_index=False)[delta_col].mean()
    order = ["TP_0986", "TP_0433", "TP_0565", "TP_0088", "TP_0916"]
    mean["_order"] = mean["cell_id"].map({c: i for i, c in enumerate(order)}).fillna(99)
    mean = mean.sort_values("_order")
    labels = []
    for _, r in mean.iterrows():
        role = str(r.get("role", "")).replace("_", " ")
        labels.append(f"{r['cell_id']}\n{role}")

    fig = plt.figure(figsize=(9.2, 6.4))
    add_title(fig, "v10-epsilon overhead SOLWEIG effect", "Mean Tmrt delta: overhead scenario minus base scenario")
    ax = fig.add_axes([0.32, 0.18, 0.62, 0.68])
    vals = pd.to_numeric(mean[delta_col], errors="coerce").values
    y = np.arange(len(mean))
    colors = [MUTED_PURPLE if v < -2 else WARM_GRAY for v in vals]
    ax.barh(y, vals, color=colors, height=0.52)
    ax.axvline(0, color=NAVY, lw=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Mean Tmrt delta: overhead − base (°C)")
    ax.grid(True, axis="x", color=GRID, linestyle="--", lw=0.7)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(NAVY)
    xmin = min(-1, np.nanmin(vals) - 2)
    ax.set_xlim(xmin, max(0.5, np.nanmax(vals) + 0.5))
    for yi, v in zip(y, vals):
        if np.isfinite(v):
            ha = "right" if v < 0 else "left"
            x = v - 0.25 if v < 0 else v + 0.15
            ax.text(x, yi, f"{v:.1f}°C", ha=ha, va="center", fontsize=8, color=NAVY)
    add_footer(fig, cfg["labels"].get("footer", "OpenHeat-ToaPayoh v10"))
    out = Path(cfg["paths"]["output_dir"]) / "charts" / "chart_02_epsilon_tmrt_delta_bars"
    save_figure(fig, out, dpi=cfg["map"].get("dpi", 300), png=cfg["map"].get("png", True), svg=cfg["map"].get("svg", True))
    plt.close(fig)
    print(f"[OK] {out}.png/.svg")


def make_summary_panels(cfg: dict):
    fig = plt.figure(figsize=(12.0, 6.8))
    add_title(fig, "v10 hotspot stability and morphology shifts", "Top-20 retention and morphology change across reviewed DSM and overhead sensitivity steps")

    ax1 = fig.add_axes([0.07, 0.18, 0.42, 0.60])
    add_panel_header(ax1, "A. Top-20 hotspot set sensitivity")
    retained = np.array([10, 8])
    changed = 20 - retained
    x = np.arange(2)
    ax1.bar(x, retained, color=NAVY, width=0.55, label="Top-20 retained")
    ax1.bar(x, changed, bottom=retained, color=MUTED_ORANGE, width=0.55, label="Top-20 changed")
    for i in range(2):
        ax1.text(x[i], retained[i]/2, f"{retained[i]}/20\nretained", color=WHITE, ha="center", va="center", fontsize=10, fontweight="bold")
        ax1.text(x[i], retained[i] + changed[i]/2, f"{changed[i]}/20\nchanged", color=WHITE, ha="center", va="center", fontsize=10, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(["v08 → v10-gamma", "v10-gamma → v10-delta"])
    ax1.set_ylabel("Cells")
    ax1.set_ylim(0, 20)
    ax1.set_yticks([0,5,10,15,20])
    ax1.grid(True, axis="y", color=GRID, linestyle="--", lw=0.7)
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False)

    ax2 = fig.add_axes([0.56, 0.18, 0.38, 0.60])
    add_panel_header(ax2, "B. UMEP morphology shift after reviewed DSM")
    cats = ["Building\ndensity", "Open-pixel\nSVF", "Shade\nfraction"]
    v08 = np.array([0.066, 0.491, 0.423])
    v10 = np.array([0.215, 0.380, 0.466])
    xx = np.arange(len(cats))
    w = 0.34
    ax2.bar(xx - w/2, v08, width=w, color=WARM_GRAY, label="v08 baseline")
    ax2.bar(xx + w/2, v10, width=w, color=BLUE, label="v10 reviewed")
    for xi, val in zip(xx - w/2, v08):
        ax2.text(xi, val + 0.012, f"{val:.2f}", ha="center", va="bottom", fontsize=8, color=SLATE)
    for xi, val in zip(xx + w/2, v10):
        ax2.text(xi, val + 0.012, f"{val:.2f}", ha="center", va="bottom", fontsize=8, color=BLUE)
    ax2.set_xticks(xx)
    ax2.set_xticklabels(cats)
    ax2.set_ylabel("Mean value")
    ax2.set_ylim(0, 0.58)
    ax2.grid(True, axis="y", color=GRID, linestyle="--", lw=0.7)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.legend(loc="upper left", frameon=False)
    add_footer(fig, cfg["labels"].get("footer", "OpenHeat-ToaPayoh v10"))
    out = Path(cfg["paths"]["output_dir"]) / "charts" / "chart_03_04_top20_and_morphology_summary"
    save_figure(fig, out, dpi=cfg["map"].get("dpi", 300), png=cfg["map"].get("png", True), svg=cfg["map"].get("svg", True))
    plt.close(fig)
    print(f"[OK] {out}.png/.svg")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v10/v10_final_figures_config.v3.json")
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    setup_matplotlib()
    ensure_dir(Path(cfg["paths"]["output_dir"]) / "charts")
    make_tmrt_timeseries(cfg)
    make_tmrt_delta_bars(cfg)
    make_summary_panels(cfg)


if __name__ == "__main__":
    main()
