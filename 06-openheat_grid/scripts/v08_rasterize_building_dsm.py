"""
scripts/v08_rasterize_building_dsm.py

Stage 5: Rasterize merged buildings into a 2m building-height DSM.

Output is a "flat-terrain building DSM":
  - ground pixels (no building) = 0
  - building pixels             = height_m (from merged layer)

This is NOT a true terrain DSM — HDB3D documents that terrain is set to 0,
so we inherit that limitation. This is the input UMEP needs for SVF and
shadow computation.

Why 2m and not 1m?
  AOI ~ 3.3 x 3.8 km @ 1m = ~12.5M pixels (over UMEP 4M-pixel safe limit)
  AOI ~ 3.3 x 3.8 km @ 2m = ~3.1M pixels  (safely under, single-pass OK)
"""
from pathlib import Path
import numpy as np
import geopandas as gpd
import rasterio
from rasterio import features
from rasterio.transform import from_origin

# ---- inputs ----
BLDG_FP = Path(r"data\features_3d\merged_buildings_height_v08.geojson")
AOI_FP  = Path(r"data\features_3d\aoi_buffered_200m.geojson")

# ---- output ----
OUT_DIR = Path(r"data\rasters\v08")
OUT_FP  = OUT_DIR / "dsm_buildings_2m_toapayoh.tif"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- parameters ----
RES_M       = 2.0          # raster resolution in meters
WORKING_CRS = "EPSG:3414"
NODATA_VAL  = -9999.0      # only used outside any pixel; for our case ground=0
DTYPE       = "float32"

# ============================================================
print("=" * 60)
print("Stage 5: Rasterize buildings -> 2m DSM")
print("=" * 60)

# ---- load ----
bldg = gpd.read_file(BLDG_FP).to_crs(WORKING_CRS)
aoi  = gpd.read_file(AOI_FP).to_crs(WORKING_CRS)
print(f"  buildings: {len(bldg)}")
print(f"  height_m  min={bldg['height_m'].min():.1f}  "
      f"mean={bldg['height_m'].mean():.1f}  "
      f"max={bldg['height_m'].max():.1f}")

# ---- compute raster grid ----
minx, miny, maxx, maxy = aoi.total_bounds
# Snap to whole-meter grid aligned with EPSG:3414 origin
minx = np.floor(minx / RES_M) * RES_M
miny = np.floor(miny / RES_M) * RES_M
maxx = np.ceil(maxx / RES_M) * RES_M
maxy = np.ceil(maxy / RES_M) * RES_M

width  = int((maxx - minx) / RES_M)
height = int((maxy - miny) / RES_M)
total_px = width * height

print(f"\n  raster grid:")
print(f"    bounds: x=[{minx:.0f}, {maxx:.0f}], y=[{miny:.0f}, {maxy:.0f}]")
print(f"    size:   {width} x {height} = {total_px:,} pixels")
print(f"    res:    {RES_M} m")
print(f"    UMEP 4M-pixel safe limit: {'OK' if total_px < 4_000_000 else 'EXCEEDED'}")

# from_origin uses (west, north, x_res, y_res) — y_res is positive going down
transform = from_origin(minx, maxy, RES_M, RES_M)

# ---- prepare burn shapes ----
# Drop buildings with null/zero height defensively
bldg_v = bldg[bldg["height_m"].notna() & (bldg["height_m"] > 0)].copy()
if len(bldg_v) < len(bldg):
    print(f"  WARNING: dropped {len(bldg) - len(bldg_v)} buildings with bad height")

# (geometry, value) pairs for rasterize
shapes = ((geom, float(h)) for geom, h
          in zip(bldg_v.geometry, bldg_v["height_m"]))

# ---- rasterize ----
# fill=0 means ground pixels stay at 0 (HDB3D convention)
# When two buildings overlap (rare here since we deduplicated via 35% rule),
# rasterio uses the LAST shape's value. Use 'merge_alg=replace' (default).
print("\n  rasterizing ...")
dsm = features.rasterize(
    shapes=shapes,
    out_shape=(height, width),
    transform=transform,
    fill=0.0,
    dtype=DTYPE,
    all_touched=False,   # only pixels whose CENTER is inside polygon
)

# ---- QA stats ----
n_building_px = int((dsm > 0).sum())
n_ground_px   = int((dsm == 0).sum())
b_frac = n_building_px / total_px

print(f"\n  DSM stats:")
print(f"    building pixels: {n_building_px:,} ({b_frac*100:.1f}%)")
print(f"    ground pixels:   {n_ground_px:,} ({(1-b_frac)*100:.1f}%)")
print(f"    height min:      {dsm[dsm>0].min():.1f} m")
print(f"    height mean:     {dsm[dsm>0].mean():.1f} m")
print(f"    height max:      {dsm.max():.1f} m")

# ---- write ----
profile = {
    "driver": "GTiff",
    "dtype": DTYPE,
    "count": 1,
    "width": width,
    "height": height,
    "crs": WORKING_CRS,
    "transform": transform,
    "nodata": None,        # no nodata: 0 = ground (legitimate value)
    "compress": "lzw",
    "tiled": True,
    "blockxsize": 256,
    "blockysize": 256,
}

with rasterio.open(OUT_FP, "w", **profile) as dst:
    dst.write(dsm, 1)
    dst.update_tags(
        source="HDB3D + URA non-HDB merged",
        ground_value="0",
        building_value="height_m",
        terrain="flat (HDB3D convention)",
        resolution_m="2",
        producer="v08_rasterize_building_dsm.py",
    )

size_mb = OUT_FP.stat().st_size / 1e6
print(f"\nWrote {OUT_FP} ({size_mb:.1f} MB)")
print("\nNext: load in QGIS to verify, then run UMEP SVF Calculator.")