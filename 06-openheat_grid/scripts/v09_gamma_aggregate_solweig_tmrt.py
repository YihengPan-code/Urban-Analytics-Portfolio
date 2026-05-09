"""
OpenHeat v0.9-gamma hotfix
Aggregate SOLWEIG/UMEP Tmrt rasters to the OpenHeat 100 m grid.

Hotfixes:
- robust HHMM parser for SOLWEIG filenames like Tmrt_2026_3_20_1300D.tif
- explicit tmrt_time_label and tmrt_hour_sgt output
- nodata-safe open-pixel mask: valid pixels and building pixels are separated
- open-pixel pedestrian aggregation, avoiding rooftop contamination

Default inputs follow the OpenHeat v0.9-gamma project layout.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

WORKING_CRS = "EPSG:3414"

DEFAULT_CONFIG = "configs/v09_gamma_solweig_config.example.json"
DEFAULT_TILE_ROOT = "data/solweig/v09_tiles"
DEFAULT_GRID_GEOJSON = "data/grid/toa_payoh_grid_v07_features.geojson"
DEFAULT_TILE_METADATA = "data/solweig/v09_tiles/v09_solweig_tile_metadata.csv"
DEFAULT_OUT_CSV = "outputs/v09_solweig/v09_solweig_tmrt_grid_summary.csv"
DEFAULT_TMRTPATTERN = "**/*Tmrt*.tif"


def read_json(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_path(cfg: Dict[str, Any], *keys: str, default: str) -> str:
    """Fetch nested config path from either top-level or paths block."""
    paths = cfg.get("paths", {}) if isinstance(cfg, dict) else {}
    for key in keys:
        if key in paths and paths[key]:
            return str(paths[key])
        if key in cfg and cfg[key]:
            return str(cfg[key])
    return default


def parse_tmrt_time_label(path: str | Path) -> str:
    """
    Extract HHMM from common SOLWEIG/UMEP Tmrt filenames.

    Supported examples:
      Tmrt_2026_3_20_1300D.tif -> 1300
      Tmrt_20260320_1300.tif   -> 1300
      tile_T01_1300.tif        -> 1300
      Tmrt_1300.tif            -> 1300
      Tmrt_13_00.tif           -> 1300

    Returns:
      HHMM string, or "unknown" if no time is detected.
    """
    name = Path(path).name
    stem = Path(path).stem

    # Prefer the last HHMM token before optional D/S/LST suffix and extension.
    patterns = [
        r"_(\d{4})[A-Za-z]*$",                 # stem ending ..._1300D
        r"_(\d{4})[A-Za-z]*\.tif$",            # name ending ..._1300D.tif
        r"_(\d{2})[_-]?([0-5]\d)[A-Za-z]*$",   # stem ending ..._13_00
        r"(?<!\d)([01]\d|2[0-3])([0-5]\d)(?!\d)",  # standalone HHMM
    ]
    for pat in patterns:
        target = name if pat.endswith(r"\.tif$") else stem
        m = re.search(pat, target)
        if not m:
            continue
        if len(m.groups()) == 1:
            val = m.group(1)
        else:
            val = f"{m.group(1)}{m.group(2)}"
        # Avoid returning years such as 2026: valid hour must be 00-23.
        if len(val) == 4 and 0 <= int(val[:2]) <= 23 and 0 <= int(val[2:]) <= 59:
            return val
    return "unknown"


def time_label_to_hour(label: str) -> Optional[int]:
    if isinstance(label, str) and len(label) == 4 and label.isdigit():
        hour = int(label[:2])
        if 0 <= hour <= 23:
            return hour
    return None


def infer_tile_id_from_path(fp: Path, tile_root: Path) -> str:
    try:
        rel = fp.relative_to(tile_root)
        return rel.parts[0]
    except Exception:
        return fp.parent.name


def load_tile_metadata(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    # Helpful aliases in case earlier scripts used slightly different names.
    if "tile_id" not in df.columns:
        for cand in ["tile", "tile_name", "folder", "tile_folder"]:
            if cand in df.columns:
                df["tile_id"] = df[cand].astype(str)
                break
    return df


def find_tmrt_files(tile_root: Path, pattern: str) -> List[Path]:
    files = sorted(tile_root.glob(pattern))
    # Some UMEP outputs may be lower/upper case.
    if not files:
        files = sorted([p for p in tile_root.rglob("*.tif") if "tmrt" in p.name.lower()])
    return files


def bounds_intersects(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
    left, bottom, right, top = a
    left2, bottom2, right2, top2 = b
    return not (right < left2 or right2 < left or top < bottom2 or top2 < bottom)


def safe_percentile(values: np.ndarray, q: float) -> float:
    if values.size == 0:
        return float("nan")
    return float(np.nanpercentile(values, q))


def aggregate_one_raster(
    tmrt_fp: Path,
    dsm_fp: Optional[Path],
    grid: gpd.GeoDataFrame,
    tile_id: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    tmrt_label = parse_tmrt_time_label(tmrt_fp)
    tmrt_hour = time_label_to_hour(tmrt_label)

    with rasterio.open(tmrt_fp) as t_src:
        t_bounds = t_src.bounds
        t_nodata = t_src.nodata
        transform = t_src.transform
        crs = t_src.crs
        tmrt = t_src.read(1).astype("float64")

    if crs is not None and grid.crs is not None and str(crs) != str(grid.crs):
        grid_work = grid.to_crs(crs)
    else:
        grid_work = grid

    # DSM should be aligned with Tmrt in the recommended workflow. If missing or
    # not aligned, all valid non-nodata Tmrt pixels are considered open pixels.
    dsm = None
    dsm_nodata = None
    if dsm_fp and Path(dsm_fp).exists():
        with rasterio.open(dsm_fp) as d_src:
            dsm_arr = d_src.read(1).astype("float64")
            dsm_nodata = d_src.nodata
            # If dimensions differ, skip DSM mask to avoid invalid alignment.
            if dsm_arr.shape == tmrt.shape and d_src.transform == transform:
                dsm = dsm_arr
            else:
                print(f"[WARN] DSM not aligned with {tmrt_fp.name}; using all valid Tmrt pixels as open pixels.")

    valid_tmrt = np.isfinite(tmrt)
    if t_nodata is not None:
        valid_tmrt &= tmrt != t_nodata

    if dsm is not None:
        valid_dsm = np.isfinite(dsm)
        if dsm_nodata is not None:
            valid_dsm &= dsm != dsm_nodata
        # Positive threshold: building pixels are >0.5 m. Ground is 0.
        building_mask = valid_dsm & (dsm > 0.5)
        open_base_mask = valid_tmrt & valid_dsm & (~building_mask)
    else:
        open_base_mask = valid_tmrt

    raster_bounds_tuple = (t_bounds.left, t_bounds.bottom, t_bounds.right, t_bounds.top)
    candidates = grid_work[grid_work.geometry.bounds.apply(
        lambda b: bounds_intersects(raster_bounds_tuple, (b["minx"], b["miny"], b["maxx"], b["maxy"])),
        axis=1,
    )].copy()

    for _, cell in candidates.iterrows():
        geom = cell.geometry
        if geom is None or geom.is_empty:
            continue
        try:
            minx, miny, maxx, maxy = geom.bounds
            window = from_bounds(minx, miny, maxx, maxy, transform=transform)
            window = window.round_offsets().round_lengths()
            row0, col0 = int(window.row_off), int(window.col_off)
            h, w = int(window.height), int(window.width)
            if h <= 0 or w <= 0:
                continue
            row1, col1 = row0 + h, col0 + w
            row0_clip, col0_clip = max(row0, 0), max(col0, 0)
            row1_clip, col1_clip = min(row1, tmrt.shape[0]), min(col1, tmrt.shape[1])
            if row1_clip <= row0_clip or col1_clip <= col0_clip:
                continue
            sub_tmrt = tmrt[row0_clip:row1_clip, col0_clip:col1_clip]
            sub_open = open_base_mask[row0_clip:row1_clip, col0_clip:col1_clip]
            sub_transform = rasterio.windows.transform(
                rasterio.windows.Window(col0_clip, row0_clip, col1_clip - col0_clip, row1_clip - row0_clip),
                transform,
            )
            cell_mask = geometry_mask(
                [geom],
                out_shape=sub_tmrt.shape,
                transform=sub_transform,
                invert=True,
                all_touched=False,
            )
            pix_mask = cell_mask & sub_open
            vals = sub_tmrt[pix_mask]
            vals = vals[np.isfinite(vals)]
            if vals.size == 0:
                continue
            rows.append({
                "tile_id": tile_id,
                "cell_id": cell["cell_id"],
                "tmrt_raster": str(tmrt_fp),
                "tmrt_filename": tmrt_fp.name,
                "tmrt_time_label": tmrt_label,
                "tmrt_hour_sgt": tmrt_hour,
                "tmrt_mean_c": float(np.nanmean(vals)),
                "tmrt_median_c": float(np.nanmedian(vals)),
                "tmrt_p10_c": safe_percentile(vals, 10),
                "tmrt_p90_c": safe_percentile(vals, 90),
                "tmrt_min_c": float(np.nanmin(vals)),
                "tmrt_max_c": float(np.nanmax(vals)),
                "n_pixels": int(vals.size),
                "aggregation_mask": "open_pixels_dsm_le_0_5_valid_nodata_excluded" if dsm is not None else "all_valid_tmrt_pixels_no_dsm_mask",
            })
        except Exception as exc:
            print(f"[WARN] Failed cell {cell.get('cell_id')} for {tmrt_fp.name}: {exc}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--tile-root", default=None)
    parser.add_argument("--grid-geojson", default=None)
    parser.add_argument("--tile-metadata", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--pattern", default=None)
    args = parser.parse_args()

    cfg = read_json(args.config)
    tile_root = Path(args.tile_root or get_path(cfg, "tile_root", "tile_dir", "tiles_dir", default=DEFAULT_TILE_ROOT))
    grid_fp = Path(args.grid_geojson or get_path(cfg, "grid_geojson", "grid", default=DEFAULT_GRID_GEOJSON))
    metadata_fp = args.tile_metadata or get_path(cfg, "tile_metadata_csv", "tile_metadata", default=DEFAULT_TILE_METADATA)
    out_fp = Path(args.out or get_path(cfg, "solweig_tmrt_grid_summary_csv", "tmrt_summary_csv", default=DEFAULT_OUT_CSV))
    pattern = args.pattern or cfg.get("solweig_tmrt_pattern", DEFAULT_TMRTPATTERN)

    if not grid_fp.exists():
        raise FileNotFoundError(f"Grid GeoJSON not found: {grid_fp}")
    if not tile_root.exists():
        raise FileNotFoundError(f"Tile root not found: {tile_root}")

    grid = gpd.read_file(grid_fp)
    if grid.crs is None:
        grid = grid.set_crs(WORKING_CRS)
    else:
        grid = grid.to_crs(WORKING_CRS)

    metadata = load_tile_metadata(metadata_fp)
    meta_by_tile: Dict[str, Dict[str, Any]] = {}
    if not metadata.empty and "tile_id" in metadata.columns:
        meta_by_tile = metadata.set_index(metadata["tile_id"].astype(str)).to_dict(orient="index")

    tmrt_files = find_tmrt_files(tile_root, pattern)
    if not tmrt_files:
        raise FileNotFoundError(f"No Tmrt rasters found under {tile_root} using pattern {pattern}")
    print(f"[INFO] Tmrt rasters found: {len(tmrt_files)}")

    rows: List[Dict[str, Any]] = []
    for fp in tmrt_files:
        tile_id = infer_tile_id_from_path(fp, tile_root)
        # Preferred DSM in the same tile folder. Use building DSM so open-pixel mask excludes buildings.
        possible_dsms = [
            fp.parent.parent / "dsm_buildings_tile.tif",
            fp.parent / "dsm_buildings_tile.tif",
            fp.parent.parent / "dsm_buildings_tile_umep.tif",
            fp.parent / "dsm_buildings_tile_umep.tif",
        ]
        dsm_fp = next((p for p in possible_dsms if p.exists()), None)
        if dsm_fp is None:
            print(f"[WARN] No tile DSM found for {fp}; all valid Tmrt pixels will be used.")
        print(f"[INFO] aggregating {fp.name} | tile={tile_id} | time={parse_tmrt_time_label(fp)}")
        sub_rows = aggregate_one_raster(fp, dsm_fp, grid, tile_id)
        # Add tile metadata if matching exact folder/tile id. If no exact match, try contains.
        meta = meta_by_tile.get(tile_id, {})
        if not meta:
            for k, v in meta_by_tile.items():
                if str(k) in tile_id or tile_id in str(k):
                    meta = v
                    break
        for r in sub_rows:
            for mk, mv in meta.items():
                if mk not in r:
                    r[mk] = mv
        rows.extend(sub_rows)

    out_fp.parent.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(rows)
    if not out.empty:
        sort_cols = [c for c in ["tile_id", "cell_id", "tmrt_hour_sgt", "tmrt_filename"] if c in out.columns]
        out = out.sort_values(sort_cols)
    out.to_csv(out_fp, index=False)
    print(f"[OK] wrote: {out_fp}")
    print(f"[OK] rows: {len(out)}")
    if not out.empty:
        print(out[[c for c in ["tile_id", "cell_id", "tmrt_time_label", "tmrt_hour_sgt", "tmrt_mean_c", "n_pixels"] if c in out.columns]].head(20).to_string(index=False))
        unknown = int((out["tmrt_time_label"] == "unknown").sum()) if "tmrt_time_label" in out.columns else 0
        if unknown:
            print(f"[WARN] rows with unknown time label: {unknown}")


if __name__ == "__main__":
    main()
