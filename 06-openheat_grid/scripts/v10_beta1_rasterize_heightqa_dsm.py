#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rasterize v10 beta.1 height-QA canonical buildings to a 2m DSM."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.enums import MergeAlg

DEFAULT_CONFIG = Path("configs/v10/v10_beta1_height_geometry_config.example.json")


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    inp = cfg["inputs"]
    out = cfg["outputs"]
    rast_cfg = cfg.get("rasterize", {})

    canonical_path = Path(out["heightqa_canonical_geojson"])
    ref_raster = Path(inp["reference_raster"])
    dsm_out = Path(out["heightqa_dsm"])
    report_path = Path(out["rasterize_report"])

    if not canonical_path.exists():
        raise FileNotFoundError(f"Height-QA canonical not found: {canonical_path}")
    if not ref_raster.exists():
        raise FileNotFoundError(f"Reference raster not found: {ref_raster}")

    b = gpd.read_file(canonical_path)
    with rasterio.open(ref_raster) as src:
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs
        out_shape = src.shape
        bounds = src.bounds

    if b.crs is None:
        b = b.set_crs(crs)
    else:
        b = b.to_crs(crs)

    b = b[b.geometry.notna() & (~b.geometry.is_empty)].copy()
    try:
        b["geometry"] = b.geometry.make_valid()
    except Exception:
        b["geometry"] = b.geometry.buffer(0)
    b = b[b.geometry.notna() & (~b.geometry.is_empty)].copy()

    b["height_m"] = pd.to_numeric(b["height_m"], errors="coerce")
    min_height = float(rast_cfg.get("min_height_m", 0.5))
    b = b[b["height_m"].fillna(0) > min_height].copy()
    b = b.sort_values("height_m", ascending=True)

    shapes = ((geom, float(h)) for geom, h in zip(b.geometry, b["height_m"]))
    arr = rasterize(
        shapes=shapes,
        out_shape=out_shape,
        transform=transform,
        fill=0.0,
        dtype="float32",
        all_touched=bool(rast_cfg.get("all_touched", False)),
        merge_alg=MergeAlg.replace,
    )

    # Critical: no nodata. 0.0 is valid ground/no-building height.
    profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        compress=rast_cfg.get("compress", "deflate"),
        nodata=None,
    )
    # Remove nodata key if rasterio profile retains it as 0 from old files.
    profile.pop("nodata", None)

    ensure_parent(dsm_out)
    with rasterio.open(dsm_out, "w", **profile) as dst:
        dst.write(arr.astype("float32"), 1)

    with rasterio.open(dsm_out) as chk:
        nodata = chk.nodata
        shape = chk.shape
        res = chk.res
        out_bounds = chk.bounds

    pix_area = abs(transform.a * transform.e)
    building_pixels = int((arr > min_height).sum())
    building_area = building_pixels * pix_area
    positive = arr[arr > min_height]

    ensure_parent(report_path)
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# v10-beta.1 height-QA DSM rasterization QA report\n\n")
        f.write(f"Output: `{dsm_out}`\n")
        f.write(f"Shape: **{shape[0]} × {shape[1]}**\n")
        f.write(f"Resolution: **{res[0]} × {res[1]} m**\n")
        f.write(f"Bounds: **{tuple(round(x, 3) for x in out_bounds)}**\n")
        f.write(f"Raster nodata metadata: **{nodata}**\n\n")
        f.write("## Flat-terrain convention\n")
        f.write("- `0.0` is valid ground / no-building height, not nodata.\n")
        f.write("- This file intentionally has no nodata value for UMEP/SVF/SOLWEIG.\n\n")
        f.write(f"Buildings rasterized: **{len(b)}**\n")
        f.write(f"Building pixels >{min_height}m: **{building_pixels}**\n")
        f.write(f"Building area m²: **{building_area:.1f}**\n")
        if len(positive):
            f.write(f"Height min/mean/max: **{positive.min():.2f} / {positive.mean():.2f} / {positive.max():.2f} m**\n")
        else:
            f.write("Height min/mean/max: **NA**\n")

    print(f"[OK] height-QA DSM: {dsm_out}")
    print(f"[OK] report: {report_path}")
    print(f"[CHECK] nodata: {nodata}")


if __name__ == "__main__":
    main()
