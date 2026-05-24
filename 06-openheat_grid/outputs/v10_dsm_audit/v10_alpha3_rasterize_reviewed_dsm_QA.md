# v1.0-alpha.3 reviewed DSM rasterization QA

Output: `data\rasters\v10\dsm_buildings_2m_augmented_reviewed.tif`
Shape: **1902 × 1652**
Resolution: **2.0 m**
Raster nodata metadata: **None**

## Flat-terrain convention
- `0.0` is valid ground / no-building height, not nodata.
- This file intentionally has no nodata value so UMEP/SVF/SOLWEIG will not mask ground pixels.

Buildings rasterized: **5319**
Building pixels >0.5m: **670052**
Building area m²: **2680208.0**
Height min/mean/max: **3.00 / 22.13 / 133.00 m**