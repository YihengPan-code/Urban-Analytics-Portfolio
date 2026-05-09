"""
Clip building and vegetation DSM rasters for overhead-aware v0.9-gamma SOLWEIG tiles.

Creates both:
- *_masked.tif: nodata=-9999 for Python QA/aggregation.
- *_tile.tif: nodata pixels filled with 0 for QGIS/UMEP use.

UMEP-ready rasters use 0 as ground; this is appropriate for flat-terrain building/canopy DSMs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_tile_name(tile_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in tile_id)


def clip_one(src_fp: Path, geom, out_masked: Path, out_umep: Path):
    with rasterio.open(src_fp) as src:
        out_image, out_transform = mask(src, [geom], crop=True, filled=True, nodata=-9999)
        profile = src.profile.copy()
        profile.update(
            height=out_image.shape[1],
            width=out_image.shape[2],
            transform=out_transform,
            nodata=-9999,
            compress="lzw",
        )
        out_masked.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out_masked, "w", **profile) as dst:
            dst.write(out_image)

        umep = out_image.copy()
        umep[umep == -9999] = 0
        profile_umep = profile.copy()
        profile_umep.update(nodata=0, compress="lzw")
        with rasterio.open(out_umep, "w", **profile_umep) as dst:
            dst.write(umep)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v09_gamma_overhead_aware_config.example.json")
    args = parser.parse_args()
    cfg = load_config(args.config)
    crs = cfg.get("working_crs", "EPSG:3414")

    out_dir = Path(cfg.get("out_dir", "data/solweig/v09_tiles_overhead_aware"))
    tiles_fp = out_dir / "v09_solweig_tiles_overhead_aware_buffered.geojson"
    if not tiles_fp.exists():
        raise FileNotFoundError(f"Buffered tiles not found: {tiles_fp}. Run v09_gamma_select_tiles_overhead_aware.py first.")

    building_dsm = Path(cfg["building_dsm"])
    vegetation_dsm = Path(cfg.get("vegetation_dsm", ""))
    if not building_dsm.exists():
        raise FileNotFoundError(f"Building DSM not found: {building_dsm}")
    veg_exists = vegetation_dsm.exists()
    if not veg_exists:
        print(f"[WARN] Vegetation DSM not found: {vegetation_dsm}; only building DSM will be clipped.")

    tiles = gpd.read_file(tiles_fp).to_crs(crs)
    print(f"[INFO] clipping rasters for {len(tiles)} tiles from {tiles_fp}")

    for _, row in tiles.iterrows():
        tile_id = str(row["tile_id"])
        folder = out_dir / safe_tile_name(tile_id)
        folder.mkdir(parents=True, exist_ok=True)
        geom = row.geometry

        clip_one(
            building_dsm,
            geom,
            folder / "dsm_buildings_tile_masked.tif",
            folder / "dsm_buildings_tile.tif",
        )
        if veg_exists:
            clip_one(
                vegetation_dsm,
                geom,
                folder / "dsm_vegetation_tile_masked.tif",
                folder / "dsm_vegetation_tile.tif",
            )

        boundary = gpd.GeoDataFrame([row.drop(labels=["geometry"]).to_dict()], geometry=[geom], crs=crs)
        boundary.to_file(folder / "tile_boundary_buffered.geojson", driver="GeoJSON")

        readme = f"""# SOLWEIG steps for {tile_id}

Use these UMEP-ready rasters in QGIS/UMEP:

- `dsm_buildings_tile.tif`
- `dsm_vegetation_tile.tif` if present

The `*_masked.tif` files use nodata=-9999 and are intended for Python QA / aggregation, not for UMEP GUI.

Recommended SOLWEIG times for v0.9-gamma:
- 2026-05-07 10:00
- 2026-05-07 12:00
- 2026-05-07 13:00
- 2026-05-07 15:00
- 2026-05-07 16:00

Put Tmrt outputs in this folder or a subfolder named `solweig_outputs/`.
Please keep HHMM in filenames, e.g.:
- `Tmrt_2026_5_7_1000D.tif`
- `Tmrt_2026_5_7_1300D.tif`

Tile notes:
- tile_type: {row.get('tile_type', '')}
- focus_cell_id: {row.get('cell_id', '')}
- overhead_fraction_cell: {row.get('overhead_fraction_cell', '')}
- tile_overhead_fraction: {row.get('tile_overhead_fraction', '')}
- selection_status: {row.get('selection_status', '')}
"""
        (folder / "README_SOLWEIG_STEPS.txt").write_text(readme, encoding="utf-8")
        print(f"[OK] {tile_id}: {folder}")

    print("[OK] Raster clipping complete.")


if __name__ == "__main__":
    main()
