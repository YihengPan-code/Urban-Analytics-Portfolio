from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.cm import ScalarMappable
import numpy as np
import pandas as pd

from v10_figures_style_v2 import (
    BUILDING_GAIN_CMAP,
    HAZARD_CMAP,
    INTERPRETATION_COLORS,
    INTERPRETATION_LABELS,
    NAVY,
    OVERHEAD_CMAP,
    RANK_SHIFT_CMAP,
    SLATE,
    WHITE,
    add_footer,
    add_north_arrow,
    add_scale_bar,
    add_title,
    discrete_colorbar,
    ensure_dir,
    plot_aoi_outline,
    save_figure,
    set_equal_extent,
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


def first_present(df: pd.DataFrame, candidates) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_geom(cfg: dict) -> gpd.GeoDataFrame:
    crs = cfg.get("map", {}).get("crs", "EPSG:3414")
    g = gpd.read_file(cfg["paths"]["grid_geojson"])
    if g.crs is None:
        g = g.set_crs(crs)
    return g.to_crs(crs)[["cell_id", "geometry"]].drop_duplicates("cell_id")


def merge_data(geom: gpd.GeoDataFrame, df: pd.DataFrame) -> gpd.GeoDataFrame:
    if df.empty:
        out = geom.copy()
    else:
        d = df.copy()
        d["cell_id"] = d["cell_id"].astype(str)
        out = geom.merge(d, on="cell_id", how="left")
    return out


def figure_map_base(cfg: dict, title: str, subtitle: str):
    figsize = tuple(cfg.get("map", {}).get("figsize_4x3", [10.5, 7.875]))
    fig = plt.figure(figsize=figsize)
    add_title(fig, title, subtitle)
    ax = fig.add_axes([0.055, 0.14, 0.72, 0.72])
    return fig, ax


def plot_numeric_map(cfg, gdf, column, title, subtitle, cmap, *, vmin=None, vmax=None, center=None, legend_title="", out_name="map"):
    fig, ax = figure_map_base(cfg, title, subtitle)
    plot_gdf = gdf.copy()
    plot_gdf[column] = pd.to_numeric(plot_gdf[column], errors="coerce")
    plot_gdf.plot(ax=ax, color="#F1F0EC", edgecolor=cfg["map"].get("cell_edge_color", "#D6D2C9"), linewidth=0.04)
    if center is not None:
        norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=center, vmax=vmax)
    else:
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    plot_gdf.dropna(subset=[column]).plot(
        ax=ax,
        column=column,
        cmap=cmap,
        norm=norm,
        edgecolor=cfg["map"].get("cell_edge_color", "#D6D2C9"),
        linewidth=cfg["map"].get("cell_edge_linewidth", 0.10),
        zorder=5,
    )
    plot_aoi_outline(ax, plot_gdf, color=cfg["map"].get("aoi_edge_color", NAVY), linewidth=cfg["map"].get("aoi_edge_linewidth", 1.0))
    set_equal_extent(ax, plot_gdf)
    if cfg.get("map", {}).get("show_scale_bar", True):
        add_scale_bar(ax)
    if cfg.get("map", {}).get("show_north_arrow", True):
        add_north_arrow(ax)
    cax = fig.add_axes([0.82, 0.33, 0.030, 0.38])
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax)
    cb.ax.set_title(legend_title, fontsize=9, color=NAVY, pad=8, loc="left")
    cb.outline.set_edgecolor("#D6D2C9")
    cb.outline.set_linewidth(0.7)
    cb.ax.tick_params(labelsize=8, colors=SLATE)
    add_footer(fig, cfg["labels"].get("footer", "OpenHeat-ToaPayoh v10"), date_label=cfg["labels"].get("date_label"))
    out_base = Path(cfg["paths"]["output_dir"]) / "maps" / out_name
    save_figure(fig, out_base, dpi=cfg["map"].get("dpi", 300), png=cfg["map"].get("png", True), svg=cfg["map"].get("svg", True))
    plt.close(fig)
    print(f"[OK] {out_base}.png/.svg")


def plot_interpretation_map(cfg, interp_gdf):
    title = "Final heat-hazard interpretation"
    subtitle = "Confident and caveated hotspots from v10-gamma, v10-delta, and selected v10-epsilon validation."
    fig, ax = figure_map_base(cfg, title, subtitle)

    # Plot other cells first, then highlighted categories in fixed order.
    order = ["other", "dsm_gap_corrected", "v10_base_top_hazard", "overhead_confounded", "dense_built_edge_case", "shaded_reference", "confident_hotspot"]
    for cls in order:
        sub = interp_gdf[interp_gdf["interpretation_class"] == cls]
        if len(sub) == 0:
            continue
        alpha = 0.45 if cls == "other" else 0.92
        lw = 0.03 if cls == "other" else 0.09
        sub.plot(ax=ax, color=INTERPRETATION_COLORS.get(cls, "#E9E7E2"), edgecolor="#FFFFFF", linewidth=lw, alpha=alpha, zorder=3 if cls == "other" else 8)
    plot_aoi_outline(ax, interp_gdf, color=cfg["map"].get("aoi_edge_color", NAVY), linewidth=cfg["map"].get("aoi_edge_linewidth", 1.0))
    set_equal_extent(ax, interp_gdf)
    add_scale_bar(ax)
    add_north_arrow(ax, location=(0.88, 0.10))

    # Legend panel
    legend_ax = fig.add_axes([0.80, 0.24, 0.17, 0.52])
    legend_ax.axis("off")
    legend_ax.text(0, 1.00, "Interpretation", fontsize=11, fontweight="bold", color=NAVY, va="top")
    y = 0.86
    for cls in ["confident_hotspot", "overhead_confounded", "dsm_gap_corrected", "dense_built_edge_case", "shaded_reference", "v10_base_top_hazard", "other"]:
        legend_ax.add_patch(plt.Rectangle((0, y - 0.035), 0.10, 0.055, color=INTERPRETATION_COLORS[cls], transform=legend_ax.transAxes, clip_on=False))
        legend_ax.text(0.15, y - 0.008, INTERPRETATION_LABELS[cls], transform=legend_ax.transAxes, fontsize=8.5, color=NAVY, va="center")
        y -= 0.105

    add_footer(fig, cfg["labels"].get("footer", "OpenHeat-ToaPayoh v10"), date_label=cfg["labels"].get("date_label"))
    out_base = Path(cfg["paths"]["output_dir"]) / "maps" / "map_06_final_hotspot_interpretation"
    save_figure(fig, out_base, dpi=cfg["map"].get("dpi", 300), png=cfg["map"].get("png", True), svg=cfg["map"].get("svg", True))
    plt.close(fig)
    print(f"[OK] {out_base}.png/.svg")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v10/v10_final_figures_config.v2.json")
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    setup_matplotlib()
    ensure_dir(Path(cfg["paths"]["output_dir"]) / "maps")

    geom = load_geom(cfg)

    # 1. Base v10-gamma hazard.
    gamma = read_csv_optional(cfg["paths"].get("v10_gamma_ranking_csv", ""))
    if not gamma.empty:
        # Prefer physical hazard_score, not risk rank.
        if "hazard_score" not in gamma.columns:
            print("[WARN] hazard_score missing in gamma ranking; skipping map_01")
        else:
            g = merge_data(geom, gamma[["cell_id", "hazard_score"]])
            plot_numeric_map(
                cfg,
                g,
                "hazard_score",
                "v10-gamma reviewed-DSM base hazard",
                "Reviewed building DSM + vegetation UMEP morphology; overhead treated as caveat layer.",
                HAZARD_CMAP,
                vmin=0,
                vmax=max(0.75, float(pd.to_numeric(g["hazard_score"], errors="coerce").max(skipna=True) or 0.75)),
                legend_title="Hazard score",
                out_name="map_01_v10_gamma_base_hazard",
            )

    # 2. v08 to v10 rank shift.
    comp = read_csv_optional(cfg["paths"].get("v08_v10_rank_comparison_csv", ""))
    if not comp.empty:
        col = first_present(comp, ["rank_change_v08_minus_v10", "rank_change_proxy_minus_umep"])
        if col:
            g = merge_data(geom, comp[["cell_id", col]].rename(columns={col: "rank_shift"}))
            vmax = np.nanpercentile(np.abs(pd.to_numeric(g["rank_shift"], errors="coerce")), 98)
            vmax = max(100, min(800, vmax))
            plot_numeric_map(
                cfg,
                g,
                "rank_shift",
                "v08 → v10-gamma hazard rank shift",
                "Positive values move toward the v10 top set; negative values drop under reviewed DSM.",
                RANK_SHIFT_CMAP,
                vmin=-vmax,
                vmax=vmax,
                center=0,
                legend_title="Rank change\nv08 − v10",
                out_name="map_02_v08_to_v10_rank_shift",
            )

    # 3. Overhead fraction.
    ohgrid = read_csv_optional(cfg["paths"].get("overhead_sensitivity_grid_csv", ""))
    if not ohgrid.empty:
        col = first_present(ohgrid, ["overhead_fraction_total", "overhead_shade_proxy_cell_scope", "overhead_shade_proxy"])
        if col:
            g = merge_data(geom, ohgrid[["cell_id", col]].rename(columns={col: "overhead_fraction_total"}))
            plot_numeric_map(
                cfg,
                g,
                "overhead_fraction_total",
                "v10-delta overhead infrastructure fraction",
                "Cell-level overhead footprint fraction; separate from ground-up building DSM.",
                OVERHEAD_CMAP,
                vmin=0,
                vmax=1,
                legend_title="Overhead fraction",
                out_name="map_03_overhead_fraction",
            )

    # 4. Base to overhead-sensitivity rank shift.
    ohcomp = read_csv_optional(cfg["paths"].get("base_overhead_rank_comparison_csv", ""))
    if not ohcomp.empty:
        col = first_present(ohcomp, ["rank_change_base_minus_overhead", "rank_change_v10_base_minus_overhead"])
        if col:
            g = merge_data(geom, ohcomp[["cell_id", col]].rename(columns={col: "rank_shift"}))
            vals = pd.to_numeric(g["rank_shift"], errors="coerce")
            vmax = np.nanpercentile(np.abs(vals), 98)
            vmax = max(100, min(800, vmax))
            plot_numeric_map(
                cfg,
                g,
                "rank_shift",
                "v10 base → overhead-sensitivity rank shift",
                "Negative values indicate cells downgraded by overhead-shade sensitivity.",
                RANK_SHIFT_CMAP,
                vmin=-vmax,
                vmax=vmax,
                center=0,
                legend_title="Rank change\nbase − overhead",
                out_name="map_04_overhead_sensitivity_rank_shift",
            )

    # 5. Building density gain.
    morph = read_csv_optional(cfg["paths"].get("basic_morphology_csv", ""))
    if not morph.empty:
        col = first_present(morph, ["delta_building_density", "delta_building_area_m2"])
        if col:
            outcol = "delta_building_density" if col == "delta_building_density" else "delta_building_area_m2"
            g = merge_data(geom, morph[["cell_id", col]].rename(columns={col: outcol}))
            vals = pd.to_numeric(g[outcol], errors="coerce")
            vmax = np.nanpercentile(vals.clip(lower=0), 98)
            if outcol == "delta_building_area_m2":
                legend = "Delta building area (m²)"
            else:
                legend = "Delta building density"
            plot_numeric_map(
                cfg,
                g,
                outcol,
                "Building density gain after reviewed DSM",
                "v10 reviewed DSM building density minus old v08/current DSM building density.",
                BUILDING_GAIN_CMAP,
                vmin=0,
                vmax=max(0.1, vmax),
                legend_title=legend,
                out_name="map_05_building_density_gain",
            )

    # 6. Interpretation map.
    interp_path = Path(cfg["paths"]["output_dir"]) / "v10_final_hotspot_interpretation_map.geojson"
    if interp_path.exists():
        interp = gpd.read_file(interp_path)
        if interp.crs is None:
            interp = interp.set_crs(cfg.get("map", {}).get("crs", "EPSG:3414"))
        interp = interp.to_crs(cfg.get("map", {}).get("crs", "EPSG:3414"))
        plot_interpretation_map(cfg, interp)
    else:
        print(f"[WARN] interpretation map not found; run v10_build_final_interpretation_layer_v2.py first: {interp_path}")


if __name__ == "__main__":
    main()
