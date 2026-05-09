"""
OpenHeat v0.9-gamma hotfix
Clip building and vegetation DSM rasters for selected SOLWEIG tiles.

Hotfixes:
- avoids silently using 0 as nodata for masked pixels in QA rasters
- writes both masked rasters with nodata=-9999 and UMEP-ready rasters with ground=0
- documents that UMEP-ready DSMs are intended for QGIS/UMEP GUI use
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import geopandas as gpd
import rasterio
from rasterio.mask import mask

WORKING_CRS = "EPSG:3414"
DEFAULT_CONFIG = "configs/v09_gamma_solweig_config.example.json"
DEFAULT_TILES = "data/solweig/v09_tiles/v09_solweig_tiles_buffered.geojson"
DEFAULT_TILE_ROOT = "data/solweig/v09_tiles"
DEFAULT_BUILDING_DSM = "data/rasters/v08/dsm_buildings_2m_toapayoh.tif"
DEFAULT_VEG_DSM = "data/rasters/v08/dsm_vegetation_2m_toapayoh.tif"


def read_json(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_path(cfg: Dict[str, Any], *keys: str, default: str) -> str:
    paths = cfg.get("paths", {}) if isinstance(cfg, dict) else {}
    for key in keys:
        if key in paths and paths[key]:
            return str(paths[key])
        if key in cfg and cfg[key]:
            return str(cfg[key])
    return default


def safe_tile_folder_name(row) -> str:
    tile_id = str(row.get("tile_id", "tile"))
    tile_type = str(row.get("tile_type", "selected"))
    cell_id = str(row.get("focus_cell_id", row.get("cell_id", "cell")))
    raw = f"{tile_id}_{tile_type}_{cell_id}"
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in raw)


def clip_one(src_fp: Path, geom, out_masked: Path, out_umep: Path) -> None:
    if not src_fp.exists():
        print(f"[WARN] source raster missing: {src_fp}")
        return
    with rasterio.open(src_fp) as src:
        src_geoms = [geom]
        if src.crs and str(src.crs) != WORKING_CRS:
            # Caller should already have projected geometry. Keep explicit for clarity.
            pass
        arr, trans = mask(src, src_geoms, crop=True, nodata=-9999, filled=True)
        profile = src.profile.copy()
        profile.update({
            "height": arr.shape[1],
            "width": arr.shape[2],
            "transform": trans,
            "nodata": -9999,
            "compress": "lzw",
        })
        out_masked.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out_masked, "w", **profile) as dst:
            dst.write(arr)

        # UMEP-ready version: UMEP generally expects flat ground=0 and building/veg height >0.
        # This avoids -9999 being interpreted as terrain by UMEP if nodata handling fails.
        arr_umep = arr.copy()
        arr_umep[arr_umep == -9999] = 0
        profile_umep = profile.copy()
        profile_umep.update({"nodata": None})
        with rasterio.open(out_umep, "w", **profile_umep) as dst:
            dst.write(arr_umep)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--tiles", default=None)
    parser.add_argument("--tile-root", default=None)
    parser.add_argument("--building-dsm", default=None)
    parser.add_argument("--vegetation-dsm", default=None)
    args = parser.parse_args()

    cfg = read_json(args.config)
    tiles_fp = Path(args.tiles or get_path(cfg, "tiles_buffered_geojson", "tiles_buffered", default=DEFAULT_TILES))
    tile_root = Path(args.tile_root or get_path(cfg, "tile_root", "tile_dir", "tiles_dir", default=DEFAULT_TILE_ROOT))
    building_dsm = Path(args.building_dsm or get_path(cfg, "building_dsm", "building_dsm_tif", default=DEFAULT_BUILDING_DSM))
    veg_dsm = Path(args.vegetation_dsm or get_path(cfg, "vegetation_dsm", "veg_dsm", "vegetation_dsm_tif", default=DEFAULT_VEG_DSM))

    if not tiles_fp.exists():
        raise FileNotFoundError(f"Buffered tile GeoJSON not found: {tiles_fp}")
    tiles = gpd.read_file(tiles_fp)
    if tiles.crs is None:
        tiles = tiles.set_crs(WORKING_CRS)
    else:
        tiles = tiles.to_crs(WORKING_CRS)

    for _, row in tiles.iterrows():
        folder = tile_root / safe_tile_folder_name(row)
        folder.mkdir(parents=True, exist_ok=True)
        geom = row.geometry
        print(f"[INFO] clipping tile {folder.name}")
        clip_one(
            building_dsm,
            geom,
            folder / "dsm_buildings_tile_masked.tif",
            folder / "dsm_buildings_tile.tif",
        )
        clip_one(
            veg_dsm,
            geom,
            folder / "dsm_vegetation_tile_masked.tif",
            folder / "dsm_vegetation_tile.tif",
        )
        readme = folder / "README_SOLWEIG_STEPS.txt"
        if not readme.exists():
            readme.write_text(
                "Use the *_tile.tif rasters for QGIS/UMEP GUI runs.\n"
                "Masked QA rasters use nodata=-9999; UMEP-ready rasters fill outside-mask pixels with ground=0.\n"
                "After SOLWEIG, place Tmrt rasters in a solweig_outputs/ subfolder.\n"
                "Recommended filename pattern: Tmrt_YYYY_M_D_HHMMD.tif, e.g. Tmrt_2026_5_7_1500D.tif.\n",
                encoding="utf-8",
            )
    print("[OK] Tile raster clipping completed")


if __name__ == "__main__":
    main()
