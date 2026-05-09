"""
OpenHeat v0.9-gamma: generate flat-DEM rasters for SOLWEIG v2025a tiles.

SOLWEIG v2025a requires a DEM input even though the UI labels it [optional]
(known regression from v2022a). Toa Payoh is approximately flat, so we
synthesize a constant-elevation DEM matching each tile's building DSM
extent/resolution. This satisfies the file-existence check without
introducing terrain features that would conflict with the DSM.

Usage:
    python scripts/v09_gamma_make_flat_dem.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio


TILE_ROOT = Path("data/solweig/v09_tiles_overhead_aware")

TILES = [
    "T01_clean_hazard_top",
    "T02_conservative_risk_top",
    "T03_social_risk_top",
    "T04_open_paved_hotspot",
    "T05_clean_shaded_reference",
    "T06_overhead_confounded_hazard_case",
]

# Constant ground elevation. Value doesn't matter for SOLWEIG radiative
# computations on a flat domain - only relative DSM-DEM differences enter
# the geometry. 0.0 keeps the DEM in the same "relative" frame as our DSM.
ELEVATION_M = 0.0


def main() -> None:
    n_ok, n_skip = 0, 0
    for tile in TILES:
        src_fp = TILE_ROOT / tile / "dsm_buildings_tile.tif"
        dst_fp = TILE_ROOT / tile / "dem_flat.tif"

        if not src_fp.exists():
            print(f"[SKIP] {tile}: DSM not found at {src_fp}")
            n_skip += 1
            continue

        with rasterio.open(src_fp) as src:
            profile = src.profile.copy()
            profile.update(dtype="float32", nodata=None, compress="lzw", count=1)
            arr = np.full((src.height, src.width), ELEVATION_M, dtype="float32")
            with rasterio.open(dst_fp, "w", **profile) as dst:
                dst.write(arr, 1)

        print(f"[OK] {tile}: {dst_fp} ({src.height}x{src.width}, elev={ELEVATION_M} m)")
        n_ok += 1

    print(f"\n[DONE] Generated {n_ok} flat DEMs ({n_skip} skipped) at elevation {ELEVATION_M} m")
    print("Use these as the 'Digital Elevation Model (DEM)' input in UMEP SOLWEIG.")


if __name__ == "__main__":
    main()
