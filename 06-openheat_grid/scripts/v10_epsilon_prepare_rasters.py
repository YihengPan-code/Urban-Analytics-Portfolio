from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import reproject


def read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_raster(path: Path, arr: np.ndarray, transform, crs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": arr.shape[0],
        "width": arr.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype("float32"), 1)


def raster_to_bounds_grid(src_path: Path, bounds, res: float, crs) -> tuple[np.ndarray, Any]:
    minx, miny, maxx, maxy = bounds
    width = int(np.ceil((maxx - minx) / res))
    height = int(np.ceil((maxy - miny) / res))
    transform = from_origin(minx, maxy, res, res)
    dst = np.zeros((height, width), dtype="float32")
    with rasterio.open(src_path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=crs,
            resampling=Resampling.nearest,
            dst_nodata=0.0,
        )
    dst[~np.isfinite(dst)] = 0.0
    return dst, transform


def infer_overhead_height(row, defaults: dict[str, float]) -> float:
    for col in ["height_m", "manual_height_m", "height"]:
        if col in row and pd.notna(row[col]):
            try:
                val = float(row[col])
                if val > 0:
                    return val
            except Exception:
                pass
    typ = str(row.get("overhead_type", "unknown_overhead")).lower()
    return float(defaults.get(typ, defaults.get("unknown_overhead", 5.0)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_epsilon_solweig_config.example.json")
    args = ap.parse_args()
    cfg = read_json(Path(args.config))
    crs = cfg.get("crs", "EPSG:3414")
    paths = cfg["paths"]
    defaults = cfg.get("overhead_height_defaults_m", {})
    tile_root = Path(paths["tile_root"])
    out_root = Path(paths["output_root"])
    out_root.mkdir(parents=True, exist_ok=True)

    meta_path = tile_root / "v10_epsilon_tile_metadata.csv"
    tiles_path = tile_root / "v10_epsilon_tiles_buffered.geojson"
    if not meta_path.exists() or not tiles_path.exists():
        raise FileNotFoundError("Tile metadata not found. Run v10_epsilon_select_cells.py first.")
    meta = pd.read_csv(meta_path)
    tiles = gpd.read_file(tiles_path).to_crs(crs)

    building_dsm = Path(paths["building_dsm"])
    vegetation_dsm = Path(paths["vegetation_dsm"])
    overhead_path = Path(paths["overhead_structures_geojson"])
    with rasterio.open(building_dsm) as src:
        res = abs(src.res[0])
        raster_crs = src.crs
    if raster_crs is not None:
        crs = raster_crs
        tiles = tiles.to_crs(crs)

    overhead = gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=crs)
    if overhead_path.exists():
        overhead = gpd.read_file(overhead_path).to_crs(crs)

    qa_rows = []
    for _, tile in tiles.iterrows():
        tile_id = tile["tile_id"]
        tile_dir = Path(tile["tile_dir"])
        bounds = tile.geometry.bounds
        b_arr, transform = raster_to_bounds_grid(building_dsm, bounds, res, crs)
        v_arr, _ = raster_to_bounds_grid(vegetation_dsm, bounds, res, crs)
        oh = overhead[overhead.geometry.intersects(tile.geometry)].copy() if len(overhead) else overhead.copy()
        shapes = []
        if len(oh):
            for _, row in oh.iterrows():
                geom = row.geometry.intersection(tile.geometry)
                if geom is not None and not geom.is_empty:
                    shapes.append((geom, infer_overhead_height(row, defaults)))
        oh_arr = rasterize(shapes, out_shape=b_arr.shape, transform=transform, fill=0.0, dtype="float32") if shapes else np.zeros_like(b_arr, dtype="float32")
        v_oh = np.maximum(v_arr, oh_arr)

        write_raster(tile_dir / "dsm_buildings_tile.tif", b_arr, transform, crs)
        write_raster(tile_dir / "dsm_vegetation_tile_base.tif", v_arr, transform, crs)
        write_raster(tile_dir / "dsm_overhead_canopy_tile.tif", oh_arr, transform, crs)
        write_raster(tile_dir / "dsm_vegetation_tile_overhead.tif", v_oh, transform, crs)
        qa_rows.append({
            "tile_id": tile_id,
            "cell_id": tile["cell_id"],
            "role": tile["role"],
            "n_overhead_features": len(oh),
            "building_pixels": int((b_arr > 0.5).sum()),
            "vegetation_pixels_base": int((v_arr > 0.5).sum()),
            "overhead_pixels": int((oh_arr > 0.5).sum()),
            "vegetation_pixels_overhead": int((v_oh > 0.5).sum()),
            "raster_shape": f"{b_arr.shape[0]}x{b_arr.shape[1]}",
        })

    qa = pd.DataFrame(qa_rows)
    qa.to_csv(out_root / "v10_epsilon_prepare_rasters_QA.csv", index=False)
    (out_root / "v10_epsilon_prepare_rasters_report.md").write_text(
        "# v10-epsilon raster preparation report\n\n" + qa.to_markdown(index=False) +
        "\n\nNotes:\n- `dsm_vegetation_tile_overhead.tif` = max(base vegetation DSM, overhead canopy DSM).\n"
        "- This is an overhead-as-canopy sensitivity approximation, not a final physical bridge model.\n",
        encoding="utf-8",
    )
    print(f"[OK] prepared rasters for {len(qa)} tiles")
    print(f"[OK] report: {out_root / 'v10_epsilon_prepare_rasters_report.md'}")


if __name__ == "__main__":
    main()
