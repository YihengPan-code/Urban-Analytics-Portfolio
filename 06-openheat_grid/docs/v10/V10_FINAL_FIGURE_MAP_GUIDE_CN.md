
# OpenHeat v10 final figure / map code guide

## 1. Purpose

This figure set generates a coherent publication/portfolio-quality visual package for the OpenHeat-ToaPayoh v10 sprint.

It is designed around the final v10 interpretation:

1. v10-gamma reviewed-DSM base hazard map
2. v10-delta overhead-sensitivity map
3. confident / caveated hotspot interpretation map
4. v10-epsilon SOLWEIG validation charts
5. workflow schematic

The scripts use Python because the project already uses GeoPandas / pandas / rasterio, and the source layers are mostly CSV / GeoJSON.

---

## 2. Install dependencies

In the `openheat` conda environment:

```bat
conda install -c conda-forge geopandas matplotlib pandas numpy shapely pyogrio
```

Optional:

```bat
conda install -c conda-forge contextily
```

The scripts do not require contextily by default. Basemaps are disabled to keep outputs reproducible offline.

---

## 3. Required inputs

The scripts expect these files to exist:

```text
data/grid/toa_payoh_grid_v07_features.geojson

outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.csv
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.geojson

outputs/v10_gamma_comparison/v10_vs_v08_rank_comparison.csv
outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_rank_comparison.csv

outputs/v10_ranking_audit/v10_old_false_positive_candidates.csv
data/grid/v10/toa_payoh_grid_v10_basic_morphology.csv
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv
data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv

outputs/v10_epsilon_solweig/v10_epsilon_focus_tmrt_summary.csv
outputs/v10_epsilon_solweig/v10_epsilon_base_vs_overhead_tmrt_comparison.csv
```

Missing optional files will trigger warnings, but the most complete figure set needs the files above.

---

## 4. Run all figures

From project root:

```bat
scripts\v10_run_final_figures_pipeline.bat
```

Outputs:

```text
outputs/v10_final_figures/
├── maps/
│   ├── map_01_v10_gamma_base_hazard.png/.svg
│   ├── map_02_v08_to_v10_rank_shift.png/.svg
│   ├── map_03_overhead_fraction.png/.svg
│   ├── map_04_overhead_sensitivity_rank_shift.png/.svg
│   ├── map_05_building_density_gain.png/.svg
│   └── map_06_final_hotspot_interpretation.png/.svg
│
├── charts/
│   ├── chart_00_v10_workflow_schematic.png/.svg
│   ├── chart_01_epsilon_tmrt_timeseries.png/.svg
│   ├── chart_02_epsilon_tmrt_delta_bars.png/.svg
│   ├── chart_03_top20_overlap_summary.png/.svg
│   └── chart_04_morphology_summary_bars.png/.svg
│
├── v10_final_hotspot_interpretation_table.csv
├── v10_final_hotspot_interpretation_map.geojson
└── v10_final_hotspot_interpretation_counts.csv
```

---

## 5. What each figure means

### map_01_v10_gamma_base_hazard

Reviewed-DSM base physical hazard. This should be interpreted as the corrected building-morphology hazard before overhead sensitivity.

### map_02_v08_to_v10_rank_shift

Shows how reviewed building DSM changed the old hazard ranking. Large negative values indicate old DSM-gap hotspots that fell after correction.

### map_03_overhead_fraction

Cell-level overhead infrastructure fraction.

### map_04_overhead_sensitivity_rank_shift

Shows cells downgraded by overhead-shade sensitivity.

### map_05_building_density_gain

Shows where building DSM augmentation materially changed building density.

### map_06_final_hotspot_interpretation

The final interpretation layer. It is not a single raw hazard rank; it classifies cells into confident hotspots, overhead-confounded hotspots, DSM-gap corrected cells, dense built edge cases, and shaded reference cells.

### chart_01_epsilon_tmrt_timeseries

SOLWEIG Tmrt curves for five selected cells, base vs overhead scenarios.

### chart_02_epsilon_tmrt_delta_bars

Mean Tmrt delta from overhead-as-canopy scenario. Large negative values physically support overhead confounding.

### chart_03_top20_overlap_summary

Summarises how the top hotspot set changed under building correction and overhead sensitivity.

### chart_04_morphology_summary_bars

Mean v08 vs v10 building density, SVF and shade fraction.

---

## 6. Suggested dissertation / portfolio figure set

Use these as final figures:

```text
Figure 1. OpenHeat v10 workflow schematic
Figure 2. v08 → v10 building-density gain map
Figure 3. v10-gamma base hazard map
Figure 4. v10-delta overhead-fraction and overhead rank-shift maps
Figure 5. final confident/caveated hotspot interpretation map
Figure 6. v10-epsilon SOLWEIG Tmrt time series
Figure 7. v10-epsilon overhead Tmrt delta bar chart
```

For a portfolio webpage, combine maps 1/3/4/6 with charts 0/1/2.

---

## 7. Editing style

All scripts use the shared style file:

```text
scripts/figures/v10_figures_style.py
```

You can change colours, labels and figure formats there.

The default palette is designed to keep the same visual language across all figures:

```text
red      = confident heat hotspot
purple   = overhead-confounded
blue     = DSM-gap corrected
green    = shaded reference
gray     = dense built / edge cases
orange   = transition / sensitivity
```

---

## 8. Notes

- These maps do not use web basemaps by default. This is intentional for reproducibility.
- SVG outputs are useful for Illustrator / PowerPoint editing.
- PNG outputs are useful for reports and portfolio pages.
- The interpretation layer should be treated as the final explanatory map, not as a replacement for all raw hazard maps.
