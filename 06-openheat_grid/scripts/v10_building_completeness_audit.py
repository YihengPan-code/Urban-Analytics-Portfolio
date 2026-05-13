"""
OpenHeat v1.0-alpha.1 hotfix
Old-vs-new building DSM completeness audit with clearer notes and v0.9 tile recovery highlights.

Uses OSM-mapped buildings as a reference layer, not absolute ground truth.
Ratios can exceed 1.0 when augmented DSM contains buildings missing from OSM or when OSM denominator is small.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask

DEFAULT_CONFIG = {
    "crs": "EPSG:3414",
    "paths": {
        "base_grid_geojson": "data/grid/toa_payoh_grid_v07_features.geojson",
        "old_building_dsm": "data/rasters/v08/dsm_buildings_2m_toapayoh.tif",
        "augmented_dsm": "data/rasters/v10/dsm_buildings_2m_augmented.tif",
        "osm_reference_buildings": "data/raw/buildings_v10/osm_buildings_toapayoh.geojson",
        "osm_standardized": "data/features_3d/v10/source_standardized/osm_standardized.geojson",
        "tile_buffers": "data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware_buffered.geojson",
        "per_cell_csv": "outputs/v10_dsm_audit/v10_building_completeness_per_cell.csv",
        "per_tile_csv": "outputs/v10_dsm_audit/v10_building_completeness_per_tile.csv",
        "map_geojson": "outputs/v10_dsm_audit/v10_building_completeness_map.geojson",
        "negative_gain_cells": "outputs/v10_dsm_audit/v10_negative_gain_cells.csv",
        "report": "outputs/v10_dsm_audit/v10_completeness_gain_report.md"
    }
}


def load_config(path: Optional[str]) -> Dict[str, Any]:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path and Path(path).exists():
        user = json.loads(Path(path).read_text(encoding="utf-8"))
        def deep_update(a, b):
            for k, v in b.items():
                if isinstance(v, dict) and isinstance(a.get(k), dict):
                    deep_update(a[k], v)
                else:
                    a[k] = v
        deep_update(cfg, user)
    return cfg


def read_vector(path: str, crs: str) -> gpd.GeoDataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Vector not found: {p}")
    g = gpd.read_file(p)
    if g.crs is None:
        print(f"[WARN] {p} has no CRS. Assuming {crs}.")
        g = g.set_crs(crs)
    else:
        g = g.to_crs(crs)
    g = g[g.geometry.notna() & (~g.geometry.is_empty)].copy()
    try:
        g["geometry"] = g.geometry.make_valid()
    except Exception:
        g["geometry"] = g.geometry.buffer(0)
    return g[g.geometry.notna() & (~g.geometry.is_empty)].copy()


def find_osm_path(paths: Dict[str, str]) -> str:
    for key in ["osm_standardized", "osm_reference_buildings"]:
        p = Path(paths.get(key, ""))
        if p.exists():
            return str(p)
    raise FileNotFoundError("No OSM reference building file found. Expected osm_standardized or osm_reference_buildings.")


def dsm_area_for_geom(raster_path: str, geom, threshold: float = 0.5) -> float:
    with rasterio.open(raster_path) as src:
        out, _ = mask(src, [geom], crop=True, filled=True, nodata=0)
        arr = out[0]
        # Positive-height area only. nodata metadata does not affect this threshold count.
        pix_area = abs(src.transform.a * src.transform.e)
        return float((arr > threshold).sum() * pix_area)


def osm_area_by_zones(zones: gpd.GeoDataFrame, osm: gpd.GeoDataFrame, zone_id: str) -> pd.DataFrame:
    # Avoid retaining unneeded columns to reduce overlay complexity.
    z = zones[[zone_id, "geometry"]].copy()
    o = osm[["geometry"]].copy()
    try:
        inter = gpd.overlay(z, o, how="intersection")
    except Exception as e:
        print(f"[WARN] overlay failed with {e}; attempting buffer(0) fix.")
        z["geometry"] = z.geometry.buffer(0)
        o["geometry"] = o.geometry.buffer(0)
        inter = gpd.overlay(z, o, how="intersection")
    if inter.empty:
        return pd.DataFrame({zone_id: zones[zone_id], "osm_area_m2": 0.0, "osm_count_intersections": 0})
    inter["inter_area_m2"] = inter.geometry.area
    agg = inter.groupby(zone_id).agg(osm_area_m2=("inter_area_m2", "sum"), osm_count_intersections=("inter_area_m2", "size")).reset_index()
    return zones[[zone_id]].merge(agg, on=zone_id, how="left").fillna({"osm_area_m2": 0.0, "osm_count_intersections": 0})


def completeness_table(zones: gpd.GeoDataFrame, zone_id: str, old_dsm: str, new_dsm: str, osm: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, r in zones.iterrows():
        rows.append({
            zone_id: r[zone_id],
            "old_dsm_area_m2": dsm_area_for_geom(old_dsm, r.geometry),
            "new_dsm_area_m2": dsm_area_for_geom(new_dsm, r.geometry),
        })
    df = pd.DataFrame(rows)
    osm_df = osm_area_by_zones(zones, osm, zone_id)
    df = df.merge(osm_df, on=zone_id, how="left")
    df["osm_area_m2"] = df["osm_area_m2"].fillna(0.0)
    df["old_vs_osm_completeness"] = np.where(df["osm_area_m2"] > 0, df["old_dsm_area_m2"] / df["osm_area_m2"], np.nan)
    df["new_vs_osm_completeness"] = np.where(df["osm_area_m2"] > 0, df["new_dsm_area_m2"] / df["osm_area_m2"], np.nan)
    df["coverage_gain_vs_osm"] = df["new_vs_osm_completeness"] - df["old_vs_osm_completeness"]
    df["new_minus_old_dsm_area_m2"] = df["new_dsm_area_m2"] - df["old_dsm_area_m2"]
    return df


def aggregate_line(df: pd.DataFrame) -> Dict[str, float]:
    old = float(df["old_dsm_area_m2"].sum())
    new = float(df["new_dsm_area_m2"].sum())
    osm = float(df["osm_area_m2"].sum())
    return {
        "old_dsm_area_sum_m2": old,
        "new_dsm_area_sum_m2": new,
        "osm_area_sum_m2": osm,
        "old_vs_osm_completeness": old / osm if osm > 0 else np.nan,
        "new_vs_osm_completeness": new / osm if osm > 0 else np.nan,
    }


def md_describe(df: pd.DataFrame, cols: list[str]) -> str:
    existing = [c for c in cols if c in df.columns]
    if not existing:
        return "No columns."
    return df[existing].describe().to_string()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_alpha_augmented_dsm_config.example.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    paths = cfg["paths"]
    crs = cfg.get("crs", "EPSG:3414")

    grid = read_vector(paths["base_grid_geojson"], crs)
    if "cell_id" not in grid.columns:
        raise KeyError("Grid must contain cell_id column.")
    osm_path = find_osm_path(paths)
    osm = read_vector(osm_path, crs)

    old_dsm = paths["old_building_dsm"]
    new_dsm = paths["augmented_dsm"]
    if not Path(old_dsm).exists():
        raise FileNotFoundError(old_dsm)
    if not Path(new_dsm).exists():
        raise FileNotFoundError(new_dsm)

    per_cell = completeness_table(grid[["cell_id", "geometry"]].copy(), "cell_id", old_dsm, new_dsm, osm)
    per_cell_fp = Path(paths["per_cell_csv"])
    per_cell_fp.parent.mkdir(parents=True, exist_ok=True)
    per_cell.to_csv(per_cell_fp, index=False)

    # GeoJSON map
    map_fp = Path(paths["map_geojson"])
    map_fp.parent.mkdir(parents=True, exist_ok=True)
    grid_map = grid.merge(per_cell, on="cell_id", how="left")
    grid_map.to_file(map_fp, driver="GeoJSON")

    # Negative gain cells for manual QA.
    neg = per_cell[per_cell["new_minus_old_dsm_area_m2"] < -100].copy()
    neg_fp = Path(paths["negative_gain_cells"])
    neg_fp.parent.mkdir(parents=True, exist_ok=True)
    neg.to_csv(neg_fp, index=False)

    # Optional tile buffers.
    tile_df = pd.DataFrame()
    tile_fp = Path(paths.get("tile_buffers", ""))
    if tile_fp.exists():
        tiles = read_vector(str(tile_fp), crs)
        # Choose a tile id column.
        tile_id_col = None
        for c in ["tile_id", "tile_type", "id", "name"]:
            if c in tiles.columns:
                tile_id_col = c
                break
        if tile_id_col is None:
            tiles["tile_id"] = [f"tile_{i+1:02d}" for i in range(len(tiles))]
            tile_id_col = "tile_id"
        # Keep extra metadata for final merge.
        tile_df = completeness_table(tiles[[tile_id_col, "geometry"]].rename(columns={tile_id_col: "tile_id"}), "tile_id", old_dsm, new_dsm, osm)
        meta_cols = [c for c in ["tile_id", "tile_type", "focus_cell_id", "cell_id"] if c in tiles.columns]
        if meta_cols and "tile_id" in tiles.columns:
            meta = tiles[meta_cols].drop_duplicates("tile_id")
            tile_df = tile_df.merge(meta, on="tile_id", how="left")
        per_tile_fp = Path(paths["per_tile_csv"])
        per_tile_fp.parent.mkdir(parents=True, exist_ok=True)
        tile_df.to_csv(per_tile_fp, index=False)

    cell_agg = aggregate_line(per_cell)
    tile_agg = aggregate_line(tile_df) if not tile_df.empty else None

    report = []
    report.append("# v1.0-alpha.1 building completeness gain report")
    report.append("")
    report.append("## Interpretation note")
    report.append("- Completeness is calculated relative to OSM-mapped building footprint area, not absolute real-world completeness.")
    report.append("- Ratios can exceed 1.0 because OSM is a reference layer, not ground truth. HDB3D/URA/canonical footprints may include buildings missing from OSM, and small OSM denominators can inflate cell-level ratios.")
    report.append("- Use manual QA for final interpretation, especially for transport facilities, shelters, roofs, and overhead structures.")
    report.append("")
    report.append("## Per-cell completeness")
    report.append(f"Rows: **{len(per_cell)}**")
    report.append(f"Old DSM area sum: **{cell_agg['old_dsm_area_sum_m2']:.1f} m²**")
    report.append(f"New DSM area sum: **{cell_agg['new_dsm_area_sum_m2']:.1f} m²**")
    report.append(f"OSM area sum: **{cell_agg['osm_area_sum_m2']:.1f} m²**")
    report.append(f"Old vs OSM completeness: **{cell_agg['old_vs_osm_completeness']:.3f}**")
    report.append(f"New vs OSM completeness: **{cell_agg['new_vs_osm_completeness']:.3f}**")
    report.append("")
    report.append("Completeness distribution:")
    report.append("```text")
    report.append(md_describe(per_cell, ["old_vs_osm_completeness", "new_vs_osm_completeness", "coverage_gain_vs_osm", "new_minus_old_dsm_area_m2"]))
    report.append("```")
    report.append("")

    if tile_agg is not None:
        report.append("## Per-tile completeness")
        report.append(f"Rows: **{len(tile_df)}**")
        report.append(f"Old DSM area sum: **{tile_agg['old_dsm_area_sum_m2']:.1f} m²**")
        report.append(f"New DSM area sum: **{tile_agg['new_dsm_area_sum_m2']:.1f} m²**")
        report.append(f"OSM area sum: **{tile_agg['osm_area_sum_m2']:.1f} m²**")
        report.append(f"Old vs OSM completeness: **{tile_agg['old_vs_osm_completeness']:.3f}**")
        report.append(f"New vs OSM completeness: **{tile_agg['new_vs_osm_completeness']:.3f}**")
        report.append("")
        report.append("Completeness distribution:")
        report.append("```text")
        report.append(md_describe(tile_df, ["old_vs_osm_completeness", "new_vs_osm_completeness", "coverage_gain_vs_osm", "new_minus_old_dsm_area_m2"]))
        report.append("```")
        report.append("")
        report.append("## Critical v0.9 tile recovery")
        crit_cols = [c for c in ["tile_id", "tile_type", "focus_cell_id", "cell_id", "old_dsm_area_m2", "new_dsm_area_m2", "osm_area_m2", "old_vs_osm_completeness", "new_vs_osm_completeness", "coverage_gain_vs_osm"] if c in tile_df.columns]
        report.append("```text")
        report.append(tile_df[crit_cols].to_string(index=False))
        report.append("```")
        report.append("")

    report.append("## Negative-gain cell QA")
    report.append(f"Cells with new_minus_old_dsm_area_m2 < -100: **{len(neg)}**")
    report.append(f"CSV: `{neg_fp}`")
    report.append("")
    report.append("## Notes")
    report.append("- The v10-alpha.1 DSM should have no nodata metadata; 0.0 is valid ground/no-building height.")
    report.append("- Do not use this audit alone to decide final hazard ranking; it is a morphology data-integrity check before v10 morphology/ranking rerun.")

    report_fp = Path(paths["report"])
    report_fp.parent.mkdir(parents=True, exist_ok=True)
    report_fp.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] per-cell: {per_cell_fp}")
    if not tile_df.empty:
        print(f"[OK] per-tile: {paths['per_tile_csv']}")
    print(f"[OK] map: {map_fp}")
    print(f"[OK] report: {report_fp}")


if __name__ == "__main__":
    main()
