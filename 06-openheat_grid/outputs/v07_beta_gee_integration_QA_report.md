# OpenHeat v0.7-beta GEE integration QA

Base grid rows after merge: **986**
GEE rows: **986**
Base cells missing from GEE: **0**
GEE cells not in base grid: **0**

- `mean_building_height_m`: missing=0, min=0.043, mean=17.304, p50=17.770, max=41.417
- `dynamic_world_tree_fraction`: missing=0, min=0.000, mean=0.046, p50=0.000, max=1.000
- `dynamic_world_grass_fraction`: missing=0, min=0.000, mean=0.014, p50=0.000, max=0.988
- `dynamic_world_water_fraction`: missing=0, min=0.000, mean=0.027, p50=0.000, max=0.961
- `dynamic_world_built_up_fraction`: missing=0, min=0.000, mean=0.908, p50=1.000, max=1.000
- `ndvi_mean`: missing=0, min=0.006, mean=0.321, p50=0.306, max=0.851
- `gvi_percent`: missing=0, min=0.000, mean=10.132, p50=8.516, max=60.000
- `svf`: missing=0, min=0.400, mean=0.862, p50=0.915, max=0.980
- `shade_fraction`: missing=0, min=0.040, mean=0.250, p50=0.236, max=0.637
- `impervious_fraction`: missing=0, min=0.000, mean=0.841, p50=0.945, max=1.000

## Notes
- `gvi_percent` is a v0.7-beta screening proxy derived from Dynamic World tree/grass and Sentinel-2 NDVI. It is **not** true street-view GVI.
- `svf` and `shade_fraction` remain morphology proxies, not UMEP/SOLWEIG outputs.
- Use this output as a real-grid forecast input, then upgrade SVF/shade/GVI in later versions.
