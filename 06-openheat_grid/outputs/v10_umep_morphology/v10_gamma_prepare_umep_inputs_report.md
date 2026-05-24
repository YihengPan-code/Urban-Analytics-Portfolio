# v10-gamma UMEP input preparation report

Generated: 2026-05-09T17:39:40

## Required input files

```text
grid_geojson                     OK       data\grid\toa_payoh_grid_v07_features.geojson
base_grid_csv                    OK       data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv
v10_basic_morphology_csv         OK       data\grid\v10\toa_payoh_grid_v10_basic_morphology.csv
v10_building_dsm                 OK       data\rasters\v10\dsm_buildings_2m_augmented_reviewed_heightqa.tif
vegetation_dsm                   OK       data\rasters\v08\dsm_vegetation_2m_toapayoh.tif
```

## Raster summaries

### v10_building_dsm

```text
path: data\rasters\v10\dsm_buildings_2m_augmented_reviewed_heightqa.tif
exists: True
crs: EPSG:3414
shape: 1902 x 1652
resolution: 2.0 x 2.0
bounds: (28498.0, 33998.0, 31802.0, 37802.0)
nodata: None
dtype: float32
```

### vegetation_dsm

```text
path: data\rasters\v08\dsm_vegetation_2m_toapayoh.tif
exists: True
crs: EPSG:3414
shape: 1902 x 1652
resolution: 2.0 x 2.0
bounds: (28498.0, 33998.0, 31802.0, 37802.0)
nodata: None
dtype: float32
```

## Grid summary

```text
rows: 986
crs: EPSG:4326
has cell_id: True
```

## UMEP output folders to use

```text
SVF output folder:    data/rasters/v10/umep_svf_with_veg
Shadow output folder: data/rasters/v10/umep_shadow_with_veg
```

## Manual UMEP instruction summary

1. In QGIS/UMEP, run Sky View Factor using the reviewed building DSM and vegetation DSM. Save outputs to the SVF folder above. Ensure `SkyViewFactor.tif`, `svfs.zip`, and preferably `shadowmats.npz` are present.

2. Run the UMEP shadow workflow using the same reviewed building DSM + vegetation DSM. Save `Shadow_YYYYMMDD_HHMM_LST.tif` rasters to the shadow folder above.

3. Keep vegetation settings consistent with v08 unless intentionally doing sensitivity: transmissivity = 3%, trunk zone = 25%.

4. After UMEP outputs exist, run `python scripts/v10_gamma_zonal_umep_to_grid.py --config configs/v10/v10_gamma_umep_config.example.json`.
