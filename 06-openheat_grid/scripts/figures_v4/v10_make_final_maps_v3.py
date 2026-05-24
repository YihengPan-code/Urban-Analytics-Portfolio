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

from v10_figures_style_v3 import (
    BUILDING_GAIN_CMAP,
    HAZARD_CMAP,
    INTERPRETATION_COLORS,
    INTERPRETATION_LABELS,
    NAVY,
    OVERHEAD_CMAP,
    RANK_SHIFT_CMAP,
    SLATE,
    add_footer,
    add_north_arrow,
    add_scale_bar,
    add_title,
    ensure_dir,
    plot_aoi_outline,
    save_figure,
    set_equal_extent,
    setup_matplotlib,
)

try:
    import contextily as ctx
except Exception:
    ctx = None


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
        return geom.copy()
    d = df.copy()
    d["cell_id"] = d["cell_id"].astype(str)
    return geom.merge(d, on="cell_id", how="left")


def maybe_to_web_mercator(gdf: gpd.GeoDataFrame, cfg: dict) -> gpd.GeoDataFrame:
    if cfg.get("basemap", {}).get("enabled", True):
        return gdf.to_crs("EPSG:3857")
    return gdf


def maybe_add_satellite_basemap(ax, cfg: dict):
    bcfg = cfg.get("basemap", {})
    if not bcfg.get("enabled", True):
        return
    if ctx is None:
        print("[WARN] contextily not installed; drawing maps without satellite basemap.")
        return
    provider_name = str(bcfg.get("provider", "Esri.WorldImagery"))
    try:
        provider = ctx.providers
        for part in provider_name.split("."):
            provider = provider[part]
        ctx.add_basemap(
            ax,
            source=provider,
            attribution=False,
            zoom=bcfg.get("zoom", None),
            interpolation="bilinear",
            alpha=bcfg.get("alpha", 1.0),
        )
    except Exception as e:
        print(f"[WARN] Could not add basemap {provider_name}: {e}")


def figure_map_base(cfg: dict, title: str, subtitle: str):
    figsize = tuple(cfg.get("map", {}).get("figsize_4x3", [10.5, 7.875]))
    fig = plt.figure(figsize=figsize)
    add_title(fig, title, subtitle)
    ax = fig.add_axes([0.055, 0.14, 0.72, 0.72])
    return fig, ax


def plot_numeric_map(cfg, gdf, column, title, subtitle, cmap, *, vmin=None, vmax=None, center=None, legend_title="", out_name="map"):
    fig, ax = figure_map_base(cfg, title, subtitle)
    plot_gdf = maybe_to_web_mercator(gdf.copy(), cfg)
    plot_gdf[column] = pd.to_numeric(plot_gdf[column], errors="coerce")

    set_equal_extent(ax, plot_gdf)
    maybe_add_satellite_basemap(ax, cfg)

    # subtle underlay of all cells
    plot_gdf.plot(
        ax=ax,
        color="#F7F5F0",
        edgecolor=cfg["map"].get("cell_edge_color", "#D6D2C9"),
        linewidth=0.03,
        alpha=0.22,
        zorder=5,
    )
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
        linewidth=cfg["map"].get("cell_edge_linewidth", 0.09),
        alpha=cfg.get("map", {}).get("overlay_alpha", 0.68),
        zorder=12,
    )
    plot_aoi_outline(ax, plot_gdf, color=cfg["map"].get("aoi_edge_color", NAVY), linewidth=cfg["map"].get("aoi_edge_linewidth", 1.0))
    set_equal_extent(ax, plot_gdf)
    if cfg.get("map", {}).get("show_scale_bar", True):
        add_scale_bar(ax, location=tuple(cfg.get("map", {}).get("scale_bar_location", [0.73, 0.05])))
    if cfg.get("map", {}).get("show_north_arrow", True):
        add_north_arrow(ax, location=tuple(cfg.get("map", {}).get("north_arrow_location", [0.92, 0.84])))

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
    fig, ax = figure_map_base(
        cfg,
        "Final heat-hazard interpretation",
        "Confident and caveated hotspots from v10-gamma, v10-delta, and selected v10-epsilon validation.",
    )
    interp_gdf = maybe_to_web_mercator(interp_gdf.copy(), cfg)
    set_equal_extent(ax, interp_gdf)
    maybe_add_satellite_basemap(ax, cfg)

    order = ["other", "dsm_gap_corrected", "v10_base_top_hazard", "overhead_confounded", "dense_built_edge_case", "shaded_reference", "confident_hotspot"]
    for cls in order:
        sub = interp_gdf[interp_gdf["interpretation_class"] == cls]
        if len(sub) == 0:
            continue
        alpha = 0.28 if cls == "other" else 0.82
        lw = 0.03 if cls == "other" else 0.10
        sub.plot(ax=ax, color=INTERPRETATION_COLORS.get(cls, "#E9E7E2"), edgecolor="#FFFFFF", linewidth=lw, alpha=alpha, zorder=8 if cls == "other" else 16)
    plot_aoi_outline(ax, interp_gdf, color=cfg["map"].get("aoi_edge_color", NAVY), linewidth=cfg["map"].get("aoi_edge_linewidth", 1.0))
    set_equal_extent(ax, interp_gdf)
    add_scale_bar(ax, location=tuple(cfg.get("map", {}).get("scale_bar_location", [0.73, 0.05])))
    add_north_arrow(ax, location=tuple(cfg.get("map", {}).get("north_arrow_location", [0.92, 0.84])))

    legend_ax = fig.add_axes([0.80, 0.24, 0.18, 0.54])
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
    parser.add_argument("--config", default="configs/v10/v10_final_figures_config.v3.json")
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    setup_matplotlib()
    ensure_dir(Path(cfg["paths"]["output_dir"]) / "maps")

    geom = load_geom(cfg)

    gamma = read_csv_optional(cfg["paths"].get("v10_gamma_ranking_csv", ""))
    if not gamma.empty and "hazard_score" in gamma.columns:
        g = merge_data(geom, gamma[["cell_id", "hazard_score"]])
        vmax = max(0.75, float(pd.to_numeric(g["hazard_score"], errors="coerce").max(skipna=True) or 0.75))
        plot_numeric_map(cfg, g, "hazard_score", "v10-gamma reviewed-DSM base hazard", "Reviewed building DSM + vegetation UMEP morphology; satellite basemap shown for spatial context.", HAZARD_CMAP, vmin=0, vmax=vmax, legend_title="Hazard score", out_name="map_01_v10_gamma_base_hazard")

    comp = read_csv_optional(cfg["paths"].get("v08_v10_rank_comparison_csv", ""))
    if not comp.empty:
        col = first_present(comp, ["rank_change_v08_minus_v10", "rank_change_proxy_minus_umep"])
        if col:
            g = merge_data(geom, comp[["cell_id", col]].rename(columns={col: "rank_shift"}))
            vmax = np.nanpercentile(np.abs(pd.to_numeric(g["rank_shift"], errors="coerce")), 98)
            vmax = max(100, min(800, vmax))
            plot_numeric_map(cfg, g, "rank_shift", "v08 → v10-gamma hazard rank shift", "Positive values move toward the v10 top set; negative values drop under reviewed DSM.", RANK_SHIFT_CMAP, vmin=-vmax, vmax=vmax, center=0, legend_title="Rank change\nv08 − v10", out_name="map_02_v08_to_v10_rank_shift")

    ohgrid = read_csv_optional(cfg["paths"].get("overhead_sensitivity_grid_csv", ""))
    if not ohgrid.empty:
        col = first_present(ohgrid, ["overhead_fraction_total", "overhead_shade_proxy_cell_scope", "overhead_shade_proxy"])
        if col:
            g = merge_data(geom, ohgrid[["cell_id", col]].rename(columns={col: "overhead_fraction_total"}))
            plot_numeric_map(cfg, g, "overhead_fraction_total", "v10-delta overhead infrastructure fraction", "Cell-level overhead footprint fraction, overlaid on satellite basemap.", OVERHEAD_CMAP, vmin=0, vmax=1, legend_title="Overhead fraction", out_name="map_03_overhead_fraction")

    ohcomp = read_csv_optional(cfg["paths"].get("base_overhead_rank_comparison_csv", ""))
    if not ohcomp.empty:
        col = first_present(ohcomp, ["rank_change_base_minus_overhead", "rank_change_v10_base_minus_overhead"])
        if col:
            g = merge_data(geom, ohcomp[["cell_id", col]].rename(columns={col: "rank_shift"}))
            vals = pd.to_numeric(g["rank_shift"], errors="coerce")
            vmax = np.nanpercentile(np.abs(vals), 98)
            vmax = max(100, min(800, vmax))
            plot_numeric_map(cfg, g, "rank_shift", "v10 base → overhead-sensitivity rank shift", "Negative values indicate cells downgraded by overhead-shade sensitivity.", RANK_SHIFT_CMAP, vmin=-vmax, vmax=vmax, center=0, legend_title="Rank change\nbase − overhead", out_name="map_04_overhead_sensitivity_rank_shift")

    morph = read_csv_optional(cfg["paths"].get("basic_morphology_csv", ""))
    if not morph.empty:
        col = first_present(morph, ["delta_building_density", "delta_building_area_m2"])
        if col:
            outcol = "delta_building_density" if col == "delta_building_density" else "delta_building_area_m2"
            g = merge_data(geom, morph[["cell_id", col]].rename(columns={col: outcol}))
            vals = pd.to_numeric(g[outcol], errors="coerce")
            vmax = np.nanpercentile(vals.clip(lower=0), 98)
            legend = "Delta building density" if outcol == "delta_building_density" else "Delta building area (m²)"
            plot_numeric_map(cfg, g, outcol, "Building density gain after reviewed DSM", "v10 reviewed DSM building density minus old v08/current DSM building density.", BUILDING_GAIN_CMAP, vmin=0, vmax=max(0.1, vmax), legend_title=legend, out_name="map_05_building_density_gain")

    interp_path = Path(cfg["paths"]["output_dir"]) / "v10_final_hotspot_interpretation_map.geojson"
    if interp_path.exists():
        interp = gpd.read_file(interp_path)
        if interp.crs is None:
            interp = interp.set_crs(cfg.get("map", {}).get("crs", "EPSG:3414"))
        plot_interpretation_map(cfg, interp.to_crs(cfg.get("map", {}).get("crs", "EPSG:3414")))
    else:
        print(f"[WARN] interpretation map not found; run v10_build_final_interpretation_layer_v2.py first: {interp_path}")


if __name__ == "__main__":
    main()
