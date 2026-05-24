"""Aggregate v10 overhead infrastructure footprints to 100m grid cells."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import geopandas as gpd
import pandas as pd


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def flag_from_fraction(frac: float, clean_max: float, moderate_max: float) -> str:
    if pd.isna(frac):
        return "unknown"
    if frac < clean_max:
        return "clean_or_minor"
    if frac < moderate_max:
        return "moderate_confounding"
    return "major_confounding"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_delta_overhead_config.example.json")
    args = ap.parse_args()

    cfg = read_json(Path(args.config))
    crs = cfg.get("crs", "EPSG:3414")
    inp = cfg["inputs"]
    out = cfg["outputs"]
    thresholds = cfg.get("classification", {}).get("cell_flag_thresholds", {})
    clean_max = float(thresholds.get("clean_or_minor_max", 0.02))
    moderate_max = float(thresholds.get("moderate_max", 0.10))

    grid = gpd.read_file(inp["grid_geojson"])
    if grid.crs is None:
        grid = grid.set_crs(crs)
    grid = grid.to_crs(crs)
    if "cell_id" not in grid.columns:
        raise KeyError("grid_geojson must contain cell_id")
    grid = grid[["cell_id", "geometry"]].copy()
    grid["cell_area_m2"] = grid.geometry.area

    overhead_path = Path(out["overhead_structures_geojson"])
    if not overhead_path.exists():
        raise FileNotFoundError(f"Overhead layer not found: {overhead_path}. Run v10_delta_build_overhead_layer.py first.")
    overhead = gpd.read_file(overhead_path).to_crs(crs)
    overhead = overhead[overhead.geometry.notna() & (~overhead.geometry.is_empty)].copy()
    if "overhead_type" not in overhead.columns:
        overhead["overhead_type"] = "unknown_overhead"
    if "opacity" not in overhead.columns:
        overhead["opacity"] = 0.6
    overhead["overhead_area_m2"] = overhead.geometry.area

    if overhead.empty:
        summary = grid[["cell_id", "cell_area_m2"]].copy()
        summary["overhead_area_total_m2"] = 0.0
    else:
        # Spatial overlay only with relevant fields.
        inter = gpd.overlay(
            grid[["cell_id", "cell_area_m2", "geometry"]],
            overhead[["overhead_id", "overhead_type", "opacity", "geometry"]],
            how="intersection",
        )
        if inter.empty:
            summary = grid[["cell_id", "cell_area_m2"]].copy()
            summary["overhead_area_total_m2"] = 0.0
        else:
            inter["inter_area_m2"] = inter.geometry.area
            inter["weighted_shade_area_m2"] = inter["inter_area_m2"] * pd.to_numeric(inter["opacity"], errors="coerce").fillna(0.6)
            total = inter.groupby("cell_id", as_index=False).agg(
                overhead_area_total_m2=("inter_area_m2", "sum"),
                overhead_weighted_shade_area_m2=("weighted_shade_area_m2", "sum"),
                n_overhead_features=("overhead_id", "nunique"),
            )
            summary = grid[["cell_id", "cell_area_m2"]].merge(total, on="cell_id", how="left")
            # Type-specific summaries.
            by_type = inter.groupby(["cell_id", "overhead_type"], as_index=False).agg(
                inter_area_m2=("inter_area_m2", "sum"),
                n=("overhead_id", "nunique"),
            )
            types = sorted(by_type["overhead_type"].dropna().astype(str).unique())
            for t in types:
                sub = by_type[by_type["overhead_type"] == t][["cell_id", "inter_area_m2", "n"]].copy()
                sub = sub.rename(columns={
                    "inter_area_m2": f"overhead_area_{t}_m2",
                    "n": f"n_{t}",
                })
                summary = summary.merge(sub, on="cell_id", how="left")

    for c in summary.columns:
        if c.startswith("overhead_area") or c.startswith("n_") or c in ["n_overhead_features", "overhead_weighted_shade_area_m2"]:
            summary[c] = pd.to_numeric(summary[c], errors="coerce").fillna(0)

    if "overhead_area_total_m2" not in summary.columns:
        summary["overhead_area_total_m2"] = 0.0
    if "overhead_weighted_shade_area_m2" not in summary.columns:
        summary["overhead_weighted_shade_area_m2"] = 0.0
    if "n_overhead_features" not in summary.columns:
        summary["n_overhead_features"] = 0

    summary["overhead_fraction_total"] = (summary["overhead_area_total_m2"] / summary["cell_area_m2"]).clip(0, 1)
    summary["overhead_shade_proxy"] = (summary["overhead_weighted_shade_area_m2"] / summary["cell_area_m2"]).clip(0, 1)

    # Type-specific fractions.
    for c in list(summary.columns):
        if c.startswith("overhead_area_") and c.endswith("_m2") and c != "overhead_area_total_m2":
            t = c.replace("overhead_area_", "").replace("_m2", "")
            summary[f"overhead_fraction_{t}"] = (summary[c] / summary["cell_area_m2"]).clip(0, 1)

    # Pedestrian shelter vs transport deck interpretation groups.
    pedestrian_types = ["covered_walkway", "pedestrian_bridge", "station_canopy"]
    transport_types = ["elevated_road", "elevated_rail", "viaduct"]
    summary["pedestrian_shelter_fraction"] = 0.0
    summary["transport_deck_fraction"] = 0.0
    for t in pedestrian_types:
        col = f"overhead_fraction_{t}"
        if col in summary.columns:
            summary["pedestrian_shelter_fraction"] += summary[col]
    for t in transport_types:
        col = f"overhead_fraction_{t}"
        if col in summary.columns:
            summary["transport_deck_fraction"] += summary[col]
    summary["pedestrian_shelter_fraction"] = summary["pedestrian_shelter_fraction"].clip(0, 1)
    summary["transport_deck_fraction"] = summary["transport_deck_fraction"].clip(0, 1)
    summary["overhead_confounding_flag"] = summary["overhead_fraction_total"].apply(lambda x: flag_from_fraction(x, clean_max, moderate_max))
    summary["overhead_interpretation"] = "minor_or_none"
    summary.loc[summary["pedestrian_shelter_fraction"] >= 0.02, "overhead_interpretation"] = "pedestrian_shelter_shade"
    summary.loc[summary["transport_deck_fraction"] >= 0.02, "overhead_interpretation"] = "transport_deck_or_viaduct"
    summary.loc[(summary["pedestrian_shelter_fraction"] >= 0.02) & (summary["transport_deck_fraction"] >= 0.02), "overhead_interpretation"] = "mixed_pedestrian_and_transport_overhead"

    csv_path = Path(out["overhead_per_cell_csv"])
    ensure_dir(csv_path)
    summary.drop(columns=[]).to_csv(csv_path, index=False)

    gout = grid.merge(summary.drop(columns=["cell_area_m2"], errors="ignore"), on="cell_id", how="left")
    gout = gpd.GeoDataFrame(gout, geometry="geometry", crs=grid.crs)
    geo_path = Path(out["overhead_per_cell_geojson"])
    ensure_dir(geo_path)
    gout.to_file(geo_path, driver="GeoJSON")

    flag_counts = summary["overhead_confounding_flag"].value_counts(dropna=False).reset_index()
    flag_counts.columns = ["flag", "n_cells"]
    interp_counts = summary["overhead_interpretation"].value_counts(dropna=False).reset_index()
    interp_counts.columns = ["interpretation", "n_cells"]
    report_path = Path(out["overhead_cell_report"])
    ensure_dir(report_path)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# v10-delta overhead cell QA report\n\n")
        f.write(f"Rows: **{len(summary)}**\n\n")
        f.write("## Overhead flag counts\n\n```text\n")
        f.write(flag_counts.to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Overhead interpretation counts\n\n```text\n")
        f.write(interp_counts.to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Summary statistics\n\n```text\n")
        cols = ["overhead_fraction_total", "overhead_shade_proxy", "pedestrian_shelter_fraction", "transport_deck_fraction", "n_overhead_features"]
        f.write(summary[cols].describe().to_string())
        f.write("\n```\n\n")
        f.write("## Top overhead cells\n\n```text\n")
        show_cols = ["cell_id", "overhead_fraction_total", "overhead_shade_proxy", "pedestrian_shelter_fraction", "transport_deck_fraction", "n_overhead_features", "overhead_confounding_flag", "overhead_interpretation"]
        f.write(summary.sort_values("overhead_fraction_total", ascending=False)[show_cols].head(30).to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Interpretation\n")
        f.write("- These metrics flag overhead infrastructure separately from ground-up buildings.\n")
        f.write("- Elevated transport deck cells should not automatically be treated as pedestrian heat-risk cells.\n")
        f.write("- Covered walkway/station canopy cells may represent pedestrian adaptation infrastructure.\n")

    print(f"[OK] per-cell overhead CSV: {csv_path}")
    print(f"[OK] per-cell overhead GeoJSON: {geo_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
