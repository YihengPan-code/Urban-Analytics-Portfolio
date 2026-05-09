"""
scripts/v08_prepare_vegetation_dsm.py

Stage 7-bis: Resample 10m canopy height to 2m, aligning EXACTLY to building DSM.

Why:
  UMEP Shadow Generator requires Vegetation Canopy DSM and Building DSM to share
  the same grid (transform, shape, CRS). 10m -> 2m upsampling uses bilinear
  interpolation to smooth canopy edges (continuous quantity).

Post-processing:
  - Mask out vegetation pixels where buildings exist (avoid double-counting:
    ETH canopy data sometimes assigns canopy heights to building edges).
  - Set canopy < 2m to 0 (UMEP doesn't shadow-cast meaningfully below 2m,
    and these are likely shrubs/noise from 10m pixel mixed cells).
"""
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

# ---- inputs ----
CANOPY_10M_FP = Path(r"data\raw\canopy\canopy_height_10m_toapayoh.tif")
BUILDING_DSM_FP = Path(r"data\rasters\v08\dsm_buildings_2m_toapayoh.tif")

# ---- output ----
OUT_FP = Path(r"data\rasters\v08\dsm_vegetation_2m_toapayoh.tif")

# ---- params ----
MIN_CANOPY_HEIGHT = 2.0  # m, drop noise below this
RESAMPLING_METHOD = Resampling.bilinear

print("=" * 60)
print("Stage 7-bis: Build vegetation DSM at 2m, aligned to building DSM")
print("=" * 60)

# ---- read building DSM as the reference grid ----
with rasterio.open(BUILDING_DSM_FP) as ref:
    ref_transform = ref.transform
    ref_shape = ref.shape
    ref_crs = ref.crs
    ref_profile = ref.profile.copy()
    bdsm = ref.read(1)
print(f"  Building DSM (reference):")
print(f"    shape: {ref_shape}, CRS: {ref_crs}, res: {ref_transform.a}m")

# ---- read source canopy ----
with rasterio.open(CANOPY_10M_FP) as src:
    print(f"\n  Source canopy:")
    print(f"    shape: {src.shape}, CRS: {src.crs}, res: {src.transform.a}m")
    src_data = src.read(1).astype(np.float32)
    src_transform = src.transform
    src_crs = src.crs

# ---- reproject + resample to reference grid ----
veg_arr = np.zeros(ref_shape, dtype=np.float32)

reproject(
    source=src_data,
    destination=veg_arr,
    src_transform=src_transform,
    src_crs=src_crs,
    dst_transform=ref_transform,
    dst_crs=ref_crs,
    resampling=RESAMPLING_METHOD,
)

print(f"\n  After resampling to 2m:")
print(f"    shape: {veg_arr.shape}")
print(f"    range: [{veg_arr.min():.2f}, {veg_arr.max():.2f}]")
print(f"    mean (all):    {veg_arr.mean():.2f}")
print(f"    > 2m: {(veg_arr > 2).sum():,} ({(veg_arr > 2).mean()*100:.1f}%)")

# ---- post-processing ----
# 1. Drop noise below MIN_CANOPY_HEIGHT
veg_arr[veg_arr < MIN_CANOPY_HEIGHT] = 0.0
n_after_threshold = (veg_arr > 0).sum()
print(f"\n  After dropping <{MIN_CANOPY_HEIGHT}m: {n_after_threshold:,} canopy pixels")

# 2. Mask out building pixels — avoid canopy "leaking" onto buildings
# (UMEP would handle this internally, but explicit zero is cleaner)
n_overlap = ((bdsm > 0) & (veg_arr > 0)).sum()
veg_arr[bdsm > 0] = 0.0
print(f"  Removed {n_overlap:,} pixels where canopy overlapped buildings")

# ---- summary ----
total = veg_arr.size
n_canopy = (veg_arr > 0).sum()
print(f"\n  Final vegetation DSM:")
print(f"    canopy pixels: {n_canopy:,} ({n_canopy/total*100:.1f}% of AOI)")
print(f"    canopy mean height (where >0): {veg_arr[veg_arr>0].mean():.2f} m")
print(f"    canopy max:  {veg_arr.max():.2f} m")

# ---- write ----
out_profile = ref_profile.copy()
out_profile.update({
    "dtype": "float32",
    "compress": "lzw",
    "tiled": True,
    "blockxsize": 256,
    "blockysize": 256,
    "nodata": None,
})

with rasterio.open(OUT_FP, "w", **out_profile) as dst:
    dst.write(veg_arr, 1)
    dst.update_tags(
        source="ETH GlobalCanopyHeight 2020 10m, resampled to 2m bilinear",
        ground_value="0",
        canopy_value="canopy_top_height_m",
        masked="building pixels set to 0",
        producer="v08_prepare_vegetation_dsm.py",
    )

print(f"\nWrote {OUT_FP} ({OUT_FP.stat().st_size/1024:.0f} KB)")

# ---- final shape sanity check ----
with rasterio.open(OUT_FP) as v:
    with rasterio.open(BUILDING_DSM_FP) as b:
        assert v.shape == b.shape, f"shape mismatch: {v.shape} vs {b.shape}"
        assert v.transform == b.transform, "transform mismatch"
        assert v.crs == b.crs, "CRS mismatch"
print("\n  ✓ Vegetation DSM shape/transform/CRS exactly match building DSM")