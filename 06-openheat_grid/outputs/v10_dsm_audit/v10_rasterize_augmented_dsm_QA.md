# v1.0-alpha.1 augmented DSM rasterization QA

Output: `data\rasters\v10\dsm_buildings_2m_augmented.tif`
Shape: **1902 × 1652**
Resolution: **2.0 m**
Bounds: **(28498.0, 33998.0, 31802.0, 37802.0)**
Raster nodata metadata: **None**

## Flat-terrain convention
- `0.0` is valid ground / no-building height, not nodata.
- This file intentionally has no nodata value so UMEP/SVF/SOLWEIG will not mask ground pixels.

Buildings rasterized: **5226**
Building pixels >0.5m: **626274**
Building area m²: **2505096.0**
Height min/mean/max: **3.00 / 22.88 / 133.00 m**

## Hotfix notes
- Removed incorrect `nodata=0.0` metadata from v10-alpha.
- Removed duplicate/dead rasterize pass.
- Uses explicit `MergeAlg.replace` after sorting by height so taller buildings overwrite lower overlapping footprints.