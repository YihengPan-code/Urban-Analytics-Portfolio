# OpenHeat v0.7 grid features QA report

Rows / grid cells: **986**
Cell size: **100 m**

- `building_density`: missing=0, min=0.000, mean=0.066, max=0.778
- `road_fraction`: missing=0, min=0.000, mean=0.197, max=1.000
- `park_distance_m`: missing=0, min=0.000, mean=410.580, max=1080.181
- `large_park_distance_m`: missing=0, min=121.822, mean=1601.161, max=3677.949
- `mean_building_height_m`: missing=0, min=2.000, mean=9.378, max=44.662
- `svf`: missing=0, min=0.378, mean=0.891, max=0.980
- `shade_fraction`: missing=0, min=0.040, mean=0.205, max=0.859
- `gvi_percent`: missing=0, min=3.721, mean=12.345, max=39.000
- `tree_canopy_fraction`: missing=0, min=0.062, mean=0.206, max=0.650
- `impervious_fraction`: missing=0, min=0.000, mean=0.349, max=1.000

## land_use_hint counts
- residential: 518
- transport: 186
- civic_institutional: 133
- commercial: 76
- other: 28
- water: 23
- park_open_space: 22

## Interpretation notes
- `svf`, `shade_fraction`, and `gvi_percent` are screening-level proxies in v0.7-alpha unless replaced by external UMEP/GVI-derived CSVs.
- This file is designed to replace `data/sample/toa_payoh_grid_sample.csv` for forecast workflow testing.
