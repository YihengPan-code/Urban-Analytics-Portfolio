# OpenHeat v0.7-beta: GEE height / vegetation integration

This helper integrates a Google Earth Engine export containing GHSL building height,
Dynamic World vegetation / built-up / water fractions, and Sentinel-2 NDVI into the
v0.7 grid feature table.

## Required input

Place the GEE export here:

```text
data/raw/gee_height_vegetation_by_grid.csv
```

Required columns:

```text
cell_id
mean_building_height_m
tree_canopy_fraction
grass_fraction
water_fraction
built_up_fraction
ndvi_mean
```

## Run

After you have already created the v0.7-alpha base grid feature table:

```bat
python scripts\v07_build_grid_features.py --config configs\v07_grid_features_config.no_osm.json
```

run:

```bat
python scripts\v07_beta_apply_gee_to_grid_features.py ^
  --base data\grid\toa_payoh_grid_v07_features.csv ^
  --gee data\raw\gee_height_vegetation_by_grid.csv ^
  --out data\grid\toa_payoh_grid_v07_features_beta_gee.csv
```

Then run the forecast engine:

```bat
python scripts\run_live_forecast_v06.py --mode live ^
  --grid data\grid\toa_payoh_grid_v07_features_beta_gee.csv ^
  --out-dir outputs\v07_beta_forecast_live
```

## Important interpretation notes

- `gvi_percent` is a screening-level proxy derived from Dynamic World tree/grass and Sentinel-2 NDVI. It is not true street-view GVI.
- `svf` and `shade_fraction` remain morphology proxies. They are not UMEP/SOLWEIG-derived values.
- The beta grid is suitable for hotspot-screening and portfolio workflow demonstration, not official public-health warning.
