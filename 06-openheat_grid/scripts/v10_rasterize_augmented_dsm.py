"""
OpenHeat v1.0-alpha.1 hotfix
Rasterize augmented building DSM with correct flat-terrain convention.

Important fix:
  nodata is intentionally NOT set. In this DSM, 0.0 is valid ground/no-building height,
  not missing data. This matches the v0.8 flat-terrain convention and is required for UMEP.
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
from rasterio.enums import MergeAlg
from rasterio.features import rasterize
from rasterio.transform import from_origin

DEFAULT_CONFIG = {
    "crs": "EPSG:3414",
    "resolution_m": 2.0,
    "aoi_buffer_m": 200.0,
    "paths": {
        "base_grid_geojson": "data/grid/toa_payoh_grid_v07_features.geojson",
        "canonical_buildings_height": "data/features_3d/v10/height_imputed/canonical_buildings_v10_height.geojson",
        "augmented_dsm": "data/rasters/v10/dsm_buildings_2m_augmented.tif",
        "rasterize_report": "outputs/v10_dsm_audit/v10_rasterize_augmented_dsm_QA.md"
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


def compute_bounds_from_grid(grid_path: str, crs: str, buffer_m: float) -> tuple[float, float, float, float]:
    grid = gpd.read_file(grid_path)
    if grid.crs is None:
        grid = grid.set_crs(crs)
    else:
        grid = grid.to_crs(crs)
    geom = grid.unary_union.buffer(buffer_m)
    return geom.bounds


def aligned_grid(bounds: tuple[float, float, float, float], res: float) -> tuple[rasterio.Affine, int, int, tuple[float,float,float,float]]:
    minx, miny, maxx, maxy = bounds
    # Align to resolution grid.
    minx = np.floor(minx / res) * res
    miny = np.floor(miny / res) * res
    maxx = np.ceil(maxx / res) * res
    maxy = np.ceil(maxy / res) * res
    width = int(round((maxx - minx) / res))
    height = int(round((maxy - miny) / res))
    transform = from_origin(minx, maxy, res, res)
    return transform, height, width, (minx, miny, maxx, maxy)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_alpha_augmented_dsm_config.example.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    paths = cfg["paths"]
    crs = cfg.get("crs", "EPSG:3414")
    res = float(cfg.get("resolution_m", 2.0))
    buffer_m = float(cfg.get("aoi_buffer_m", 200.0))

    bldg_fp = Path(paths["canonical_buildings_height"])
    if not bldg_fp.exists():
        raise FileNotFoundError(f"Height-imputed buildings not found: {bldg_fp}")
    b = gpd.read_file(bldg_fp)
    if b.crs is None:
        b = b.set_crs(crs)
    else:
        b = b.to_crs(crs)
    b = b[b.geometry.notna() & (~b.geometry.is_empty)].copy()
    b["height_m"] = pd.to_numeric(b["height_m"], errors="coerce")
    b = b[b["height_m"].notna() & (b["height_m"] > 0)].copy()
    b["area_m2"] = b.geometry.area

    bounds = compute_bounds_from_grid(paths["base_grid_geojson"], crs, buffer_m)
    transform, height, width, aligned_bounds = aligned_grid(bounds, res)

    # Rasterize once. Sort ascending so taller buildings are written last.
    b_sorted = b.sort_values("height_m", ascending=True)
    shapes = ((geom, float(h)) for geom, h in zip(b_sorted.geometry, b_sorted["height_m"]))
    arr = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0.0,
        dtype="float32",
        all_touched=False,
        merge_alg=MergeAlg.replace,
    )

    out_fp = Path(paths["augmented_dsm"])
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        # DO NOT set nodata. 0.0 is valid ground / no-building height.
    }
    with rasterio.open(out_fp, "w", **profile) as dst:
        dst.write(arr, 1)

    with rasterio.open(out_fp) as src:
        written_nodata = src.nodata
        shape = (src.height, src.width)
        bounds_written = src.bounds

    building_pixels = int((arr > 0.5).sum())
    building_area = building_pixels * res * res
    vals = arr[arr > 0.5]
    hmin = float(vals.min()) if vals.size else np.nan
    hmean = float(vals.mean()) if vals.size else np.nan
    hmax = float(vals.max()) if vals.size else np.nan

    report = []
    report.append("# v1.0-alpha.1 augmented DSM rasterization QA")
    report.append("")
    report.append(f"Output: `{out_fp}`")
    report.append(f"Shape: **{shape[0]} × {shape[1]}**")
    report.append(f"Resolution: **{res} m**")
    report.append(f"Bounds: **{tuple(round(x, 2) for x in bounds_written)}**")
    report.append(f"Raster nodata metadata: **{written_nodata}**")
    report.append("")
    report.append("## Flat-terrain convention")
    report.append("- `0.0` is valid ground / no-building height, not nodata.")
    report.append("- This file intentionally has no nodata value so UMEP/SVF/SOLWEIG will not mask ground pixels.")
    report.append("")
    report.append(f"Buildings rasterized: **{len(b)}**")
    report.append(f"Building pixels >0.5m: **{building_pixels}**")
    report.append(f"Building area m²: **{building_area:.1f}**")
    report.append(f"Height min/mean/max: **{hmin:.2f} / {hmean:.2f} / {hmax:.2f} m**")
    report.append("")
    report.append("## Hotfix notes")
    report.append("- Removed incorrect `nodata=0.0` metadata from v10-alpha.")
    report.append("- Removed duplicate/dead rasterize pass.")
    report.append("- Uses explicit `MergeAlg.replace` after sorting by height so taller buildings overwrite lower overlapping footprints.")
    report_fp = Path(paths["rasterize_report"])
    report_fp.parent.mkdir(parents=True, exist_ok=True)
    report_fp.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] DSM: {out_fp}")
    print(f"[OK] report: {report_fp}")
    print(f"[INFO] nodata={written_nodata} | building_area_m2={building_area:.1f}")


if __name__ == "__main__":
    main()
