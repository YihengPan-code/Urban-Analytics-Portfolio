"""
Aggregate SOLWEIG Tmrt rasters from overhead-aware selected tiles to the 100m grid.

This script is deliberately independent from earlier v0.9-gamma aggregators so it can
operate on `data/solweig/v09_tiles_overhead_aware/`.

It uses:
- dsm_buildings_tile_masked.tif for valid/open pixel masks;
- Tmrt rasters found recursively inside each tile folder;
- HHMM parser that avoids confusing year (2026) with hour (1300).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_tmrt_time_label(path: str | Path) -> str:
    name = Path(path).name
    stem = Path(path).stem
    patterns = [
        r"_(\d{4})[A-Za-z]?$",          # ..._1300D or ..._1300
        r"_(\d{4})[A-Za-z]?\.tif$",     # full filename fallback
        r"_(\d{2})(\d{2})_",            # ..._13_00_
        r"(?<!\d)([01]\d|2[0-3])([0-5]\d)(?!\d)",  # standalone HHMM
    ]
    for pat in patterns:
        target = name if pat.endswith(r"\.tif$") else stem
        m = re.search(pat, target)
        if m:
            if len(m.groups()) == 1:
                return m.group(1)
            if len(m.groups()) >= 2:
                return f"{m.group(1)}{m.group(2)}"
    return "unknown"


def raster_stats_for_geom(src, arr: np.ndarray, valid_open_mask: np.ndarray, geom) -> dict:
    mask_geom = geometry_mask([geom], transform=src.transform, invert=True, out_shape=arr.shape)
    mask_final = mask_geom & valid_open_mask & np.isfinite(arr)
    vals = arr[mask_final]
    if vals.size == 0:
        return {"n_pixels": 0, "tmrt_mean_c": np.nan, "tmrt_p10_c": np.nan, "tmrt_p90_c": np.nan, "tmrt_min_c": np.nan, "tmrt_max_c": np.nan}
    return {
        "n_pixels": int(vals.size),
        "tmrt_mean_c": float(np.nanmean(vals)),
        "tmrt_p10_c": float(np.nanpercentile(vals, 10)),
        "tmrt_p90_c": float(np.nanpercentile(vals, 90)),
        "tmrt_min_c": float(np.nanmin(vals)),
        "tmrt_max_c": float(np.nanmax(vals)),
    }


def aggregate(cfg: dict) -> dict:
    crs = cfg.get("working_crs", "EPSG:3414")
    out_dir = Path(cfg.get("out_dir", "data/solweig/v09_tiles_overhead_aware"))
    grid_fp = Path(cfg["grid_geojson"])
    tile_meta_fp = out_dir / "v09_solweig_tile_metadata_overhead_aware.csv"
    tiles_buf_fp = out_dir / "v09_solweig_tiles_overhead_aware_buffered.geojson"
    qa_out = Path(cfg.get("qa_dir", "outputs/v09_gamma_qa"))
    solweig_out = Path("outputs/v09_solweig")
    solweig_out.mkdir(parents=True, exist_ok=True)

    if not grid_fp.exists():
        raise FileNotFoundError(f"Grid GeoJSON not found: {grid_fp}")
    if not tile_meta_fp.exists():
        raise FileNotFoundError(f"Tile metadata not found: {tile_meta_fp}")
    if not tiles_buf_fp.exists():
        raise FileNotFoundError(f"Buffered tiles not found: {tiles_buf_fp}")

    grid = gpd.read_file(grid_fp).to_crs(crs)[["cell_id", "geometry"]]
    meta = pd.read_csv(tile_meta_fp)
    tiles = gpd.read_file(tiles_buf_fp).to_crs(crs)[["tile_id", "geometry"]]
    meta = meta.merge(tiles.rename(columns={"geometry": "tile_geometry"}), on="tile_id", how="left")

    pattern = cfg.get("solweig_tmrt_pattern", "**/*Tmrt*.tif")
    rows = []

    for _, tile in meta.iterrows():
        tile_id = str(tile["tile_id"])
        folder = out_dir / tile_id
        if not folder.exists():
            # Tile folder may have safe generated name; fallback search by prefix.
            matches = list(out_dir.glob(f"{tile_id}*"))
            folder = matches[0] if matches else folder
        if not folder.exists():
            print(f"[WARN] folder missing for {tile_id}: {folder}")
            continue

        dsm_fp = folder / "dsm_buildings_tile_masked.tif"
        if not dsm_fp.exists():
            print(f"[WARN] masked building DSM missing for {tile_id}: {dsm_fp}")
            continue

        tmrt_files = sorted(folder.glob(pattern))
        if not tmrt_files:
            print(f"[WARN] no Tmrt rasters found for {tile_id} using pattern {pattern}")
            continue

        with rasterio.open(dsm_fp) as dsm_src:
            dsm = dsm_src.read(1).astype("float32")
            nodata = dsm_src.nodata
            valid = np.ones_like(dsm, dtype=bool)
            if nodata is not None:
                valid &= dsm != nodata
            valid &= np.isfinite(dsm)
            open_mask = valid & (dsm <= 0.5)

            tile_geom = tile["tile_geometry"]
            grid_tile = grid[grid.intersects(tile_geom)].copy()

            for tmrt_fp in tmrt_files:
                with rasterio.open(tmrt_fp) as tmrt_src:
                    arr = tmrt_src.read(1).astype("float32")
                    arr_nodata = tmrt_src.nodata
                    if arr_nodata is not None:
                        arr[arr == arr_nodata] = np.nan
                    if arr.shape != dsm.shape:
                        print(f"[WARN] shape mismatch for {tmrt_fp}; expected {dsm.shape}, got {arr.shape}; skipping")
                        continue
                    label = parse_tmrt_time_label(tmrt_fp)
                    hour = int(label[:2]) if label != "unknown" and label[:2].isdigit() else np.nan
                    for _, cell in grid_tile.iterrows():
                        stats = raster_stats_for_geom(tmrt_src, arr, open_mask, cell.geometry)
                        if stats["n_pixels"] == 0:
                            continue
                        row = {
                            "tile_id": tile_id,
                            "tile_type": tile.get("tile_type", ""),
                            "focus_cell_id": tile.get("cell_id", ""),
                            "cell_id": cell["cell_id"],
                            "tmrt_raster": str(tmrt_fp),
                            "tmrt_time_label": label,
                            "tmrt_hour_sgt": hour,
                            "aggregation_mask": "open_pixels_dsm_le_0p5",
                        }
                        row.update(stats)
                        rows.append(row)

    out_csv = solweig_out / "v09_solweig_tmrt_grid_summary_overhead_aware.csv"
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)

    report_fp = solweig_out / "v09_solweig_tmrt_grid_summary_overhead_aware_report.md"
    labels = [] if df.empty else sorted(df["tmrt_time_label"].dropna().astype(str).unique())
    report = "# v0.9-gamma overhead-aware SOLWEIG Tmrt aggregation report\n\n"
    report += f"Rows: **{len(df)}**\n\n"
    report += f"Tmrt time labels: `{labels}`\n\n"
    if len(df):
        report += "## Tmrt summary by time\n\n"
        report += df.groupby("tmrt_time_label")["tmrt_mean_c"].describe().to_string() + "\n\n"
    report += "## Notes\n\n"
    report += "- Aggregation uses open pixels based on `dsm_buildings_tile_masked.tif` and `dsm <= 0.5`.\n"
    report += "- Tmrt time labels are parsed from HHMM near the end of filenames, avoiding confusion with year strings.\n"
    report_fp.write_text(report, encoding="utf-8")

    print(f"[OK] SOLWEIG Tmrt grid summary: {out_csv}")
    print(f"[OK] report: {report_fp}")
    if labels:
        print("[INFO] parsed time labels:", labels)
    return {"summary_csv": str(out_csv), "report": str(report_fp)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v09_gamma_overhead_aware_config.example.json")
    args = parser.parse_args()
    cfg = load_config(args.config)
    aggregate(cfg)


if __name__ == "__main__":
    main()
