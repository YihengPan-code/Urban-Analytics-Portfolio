# OpenHeat-ToaPayoh Current Project Structure after v0.9 Freeze and v10 Start

> Recommended structure after `v0.9-audit-freeze` tag and creation of the v10 folders.
> This is a target structure. Some folders may be empty at the start of v10.

---

## 1. Root

```text
06-openheat_grid/
├── configs/
├── data/
├── docs/
├── outputs/
├── scripts/
├── src/
├── tests/
├── earth_engine/
├── requirements*.txt
├── README*.md
└── .git/
```

Use the existing `06-openheat_grid` repo. Do not create a fully separate project. v1.0 is an upstream morphology correction, not a new project.

Recommended branch/tag status:

```text
git tag:    v0.9-audit-freeze
branch:     v10-augmented-dsm
```

---

## 2. Configs

```text
configs/
├── v07_grid_features_config.example.json
├── v07_grid_features_config.no_osm.json
├── v071_risk_exposure_config.example.json
├── v08_umep_config.example.json                    # if present
├── v09_alpha_config.example.json
├── v09_beta_config.example.json
├── v09_beta_threshold_config.example.json
├── v09_gamma_solweig_config.example.json
├── v09_gamma_overhead_aware_config.example.json
└── v10_augmented_dsm_config.example.json            # new, to be created
```

v10 should get its own config file. Do not modify v09 configs unless fixing documentation paths.

---

## 3. Data directory

```text
data/
├── archive/
│   └── nea_realtime_observations.csv
│
├── raw/
│   ├── ura_masterplan2019_buildings.geojson
│   ├── ura_masterplan2019_land_use.geojson
│   ├── nparks_parks_nature_reserves.geojson
│   ├── osm_roads_toa_payoh.geojson
│   ├── osm_water_toa_payoh.geojson
│   ├── gee_height_vegetation_by_grid.csv
│   ├── canopy/
│   │   └── canopy_height_10m_toapayoh.tif
│   ├── hdb3d/
│   │   └── hdb3d-data/
│   │       └── hdb.json
│   ├── demographics/
│   │   └── singstat_subzone_age_2020.csv
│   ├── boundaries/
│   │   └── ura_mp19_subzone_no_sea.geojson
│   ├── poi/
│   │   ├── lta_bus_stops.geojson
│   │   ├── lta_mrt_exits.geojson
│   │   ├── nea_hawker_centres.geojson
│   │   ├── sportsg_facilities.geojson
│   │   ├── ecda_preschools.geojson
│   │   └── moh_eldercare_services.geojson
│   └── buildings_v10/                               # new v10 raw sources
│       ├── hdb3d_raw.geojson                        # standardized copy/export
│       ├── ura_buildings_raw.geojson
│       ├── osm_buildings_toapayoh.geojson
│       ├── microsoft_buildings_toapayoh.geojson      # optional
│       ├── google_open_buildings_toapayoh.geojson    # optional
│       └── onemap_buildings_toapayoh.geojson         # optional, if accessible
│
├── grid/
│   ├── toa_payoh_grid_v07_features.geojson
│   ├── toa_payoh_grid_v07_features_beta_final.csv
│   ├── toa_payoh_grid_v07_features_beta_final_v071_risk.csv
│   ├── toa_payoh_grid_v08_umep_morphology.csv
│   ├── toa_payoh_grid_v08_umep_morphology_with_veg.csv
│   └── toa_payoh_grid_v08_features_umep_with_veg.csv
│
├── features/
│   └── v071/
│       ├── v071_risk_exposure_features.csv
│       ├── v071_node_scores_raw.csv
│       └── v071_public_nodes_clean.geojson
│
├── features_3d/
│   ├── hdb3d_raw.geojson
│   ├── aoi_buffered_200m.geojson
│   ├── hdb3d_buildings_toapayoh.geojson
│   ├── ura_buildings_toapayoh.geojson
│   ├── merged_buildings_height_v08.geojson
│   └── v10/                                         # new v10 canonical layers
│       ├── source_standardized/
│       │   ├── hdb3d_standardized.geojson
│       │   ├── ura_standardized.geojson
│       │   ├── osm_standardized.geojson
│       │   ├── microsoft_standardized.geojson
│       │   └── google_standardized.geojson
│       ├── canonical_candidates/
│       ├── canonical_buildings_v10.geojson
│       ├── canonical_buildings_v10_height.geojson
│       └── manual_QA_sample.geojson
│
├── rasters/
│   ├── v08/
│   │   ├── dsm_buildings_2m_toapayoh.tif
│   │   ├── dsm_vegetation_2m_toapayoh.tif
│   │   ├── umep_svf/
│   │   ├── umep_shadow/
│   │   ├── umep_svf_with_veg/
│   │   └── umep_shadow_with_veg/
│   └── v10/                                         # new v10 rasters
│       ├── dsm_buildings_2m_augmented.tif
│       ├── dsm_overhead_2m.tif                      # future/optional
│       ├── dsm_vegetation_2m_toapayoh.tif           # copied or symlinked from v08
│       └── QA_rasters/
│
├── calibration/
│   ├── v09_historical_forecast_by_station_hourly.csv
│   └── v09_wbgt_station_pairs.csv
│
└── solweig/
    ├── v09_tiles/
    ├── v09_tiles_overhead_aware/
    │   ├── v09_solweig_tile_metadata_overhead_aware.csv
    │   ├── v09_solweig_tiles_overhead_aware.geojson
    │   ├── v09_solweig_tiles_overhead_aware_buffered.geojson
    │   ├── T01_clean_hazard_top/
    │   ├── T02_conservative_risk_top/
    │   ├── T03_social_risk_top/
    │   ├── T04_open_paved_hotspot/
    │   ├── T05_clean_shaded_reference/
    │   └── T06_overhead_confounded_hazard_case/
    └── v10_tiles/                                   # optional after augmented ranking
```

---

## 4. Outputs directory

```text
outputs/
├── v07_beta_final_forecast_live/
├── v071_risk_exposure/
├── v08_umep_with_veg_forecast_live/
│   ├── v08_umep_with_veg_hotspot_ranking_with_grid_features.csv
│   ├── v08_umep_with_veg_hotspot_ranking_with_grid_features.geojson
│   └── risk_scenarios/
│       ├── v08_risk_scenario_rankings.csv
│       ├── v08_risk_scenario_rankings.geojson
│       └── v08_risk_scenario_QA_report.md
│
├── v09_alpha_calibration/
├── v09_beta_calibration/
├── v09_beta_threshold_scan/
├── v09_gamma_qa/
│   ├── v09_overhead_structures.geojson
│   ├── v09_overhead_structures_per_cell.csv
│   ├── v09_building_completeness_per_tile.csv
│   └── v09_osm_buildings.geojson
├── v09_solweig/
├── v09_gamma_analysis/
│   ├── v09_gamma_solweig_vs_proxy_per_cell.csv
│   ├── v09_gamma_focus_cell_solweig_vs_proxy.csv
│   ├── v09_gamma_tiletype_hour_summary.csv
│   └── v09_gamma_solweig_vs_proxy_REPORT.md
│
├── v09_freeze/                                      # new frozen copy area
│   ├── v09_beta_calibration_report.md
│   ├── v09_beta_threshold_scan_report.md
│   ├── v09_gamma_solweig_vs_proxy_REPORT.md
│   ├── v09_building_completeness_per_tile.csv
│   ├── v09_osm_buildings.geojson
│   └── toa_payoh_grid_v08_features_umep_with_veg.csv
│
├── v10_dsm_audit/                                   # new v10 outputs
│   ├── v10_building_completeness_per_cell.csv
│   ├── v10_building_completeness_per_tile.csv
│   ├── v10_building_completeness_station_anchors.csv
│   ├── v10_completeness_gain_report.md
│   └── v10_building_completeness_map.geojson
│
├── v10_morphology/
│   ├── toa_payoh_grid_v10_features.csv
│   ├── toa_payoh_grid_v10_features.geojson
│   └── v10_morphology_QA_report.md
│
├── v10_ranking_audit/
│   ├── v10_hazard_rank_shift.csv
│   ├── v10_rank_shift_summary.md
│   ├── v10_old_false_positive_candidates.csv
│   └── v10_new_hotspot_candidates.csv
│
└── v10_solweig/                                     # optional later
    ├── v10_selected_tile_metadata.csv
    ├── v10_tmrt_grid_summary.csv
    └── v10_solweig_comparison_report.md
```

Do not overwrite v09 outputs. v10 must write to `outputs/v10_*` only.

---

## 5. Docs directory

```text
docs/
├── v09_freeze/
│   ├── V09_FREEZE_NOTE_CN.md
│   └── V09_REVISED_FINDINGS_CN.md
│
├── v10/
│   ├── V10_PROJECT_STRUCTURE_CN.md
│   ├── V10_AUGMENTED_DSM_PLAN_CN.md                 # to be written
│   ├── V10_BUILDING_SOURCE_SCHEMA_CN.md             # to be written
│   ├── V10_DEDUP_HEIGHT_IMPUTATION_METHOD_CN.md     # to be written
│   └── V10_RANK_SHIFT_AUDIT_METHOD_CN.md            # to be written
│
├── 32_V09_COMPLETE_WORK_RECORD_CN.md
├── 33_V09_BUILDING_DSM_GAP_AUDIT_CN.md
└── other previous docs...
```

---

## 6. Scripts directory

```text
scripts/
├── v07_*.py
├── v071_*.py
├── v08_*.py
├── v09_*.py
│
├── run_v09_archive_loop.bat
│
├── v10_download_building_sources.py                 # to be created
├── v10_standardize_building_sources.py              # to be created
├── v10_deduplicate_building_footprints.py           # to be created
├── v10_assign_building_heights.py                   # to be created
├── v10_rasterize_augmented_dsm.py                   # to be created
├── v10_building_completeness_audit.py               # to be created
├── v10_recompute_morphology_features.py             # to be created
├── v10_rerun_hazard_ranking.py                      # to be created
└── v10_rank_shift_audit.py                          # to be created
```

v10 script naming rule:

```text
v10_<verb>_<object>.py
```

Example:

```text
v10_deduplicate_building_footprints.py
```

Avoid reusing v08/v09 script names for v10 modifications.

---

## 7. Source code directory

```text
src/
├── openheat_forecast/
├── openheat_grid/
└── openheat_v10/                                    # optional if v10 code grows
    ├── buildings.py
    ├── dedup.py
    ├── height_imputation.py
    ├── rasterize.py
    └── qa.py
```

For the first v10 prototype, scripts can be standalone. If logic becomes reused, move it into `src/openheat_v10/`.

---

## 8. Tests

```text
tests/
├── test_v071_risk_helpers.py
├── test_v09_beta_calibration.py                     # optional
└── test_v10_building_dedup.py                       # to be created
```

Minimum v10 tests:

```text
1. duplicate footprint detection works for overlapping polygons
2. height fallback never returns null
3. rasterization output has expected bounds / CRS / resolution
4. completeness audit detects known gap cells
```

---

## 9. Practical workflow after freeze

### Freeze already completed

```text
git tag v0.9-audit-freeze
```

### Recommended next commands

```bat
git checkout -b v10-augmented-dsm
mkdir docs\v09_freeze
mkdir docs\v10
mkdir data\raw\buildings_v10
mkdir data\features_3d\v10
mkdir data\rasters\v10
mkdir data\grid\v10
mkdir outputs\v10_dsm_audit
mkdir outputs\v10_morphology
mkdir outputs\v10_ranking_audit
```

### Commit freeze docs

```bat
git add docs\v09_freeze\V09_FREEZE_NOTE_CN.md docs\v09_freeze\V09_REVISED_FINDINGS_CN.md docs\v10\V10_PROJECT_STRUCTURE_CN.md
git commit -m "Document v0.9 freeze and v10 project structure"
```

---

## 10. Development rule from now on

From this point forward:

```text
v09 = frozen current-DSM audit baseline
v10 = augmented building DSM development
```

Do not overwrite:

```text
data/rasters/v08/
outputs/v09_*/
data/solweig/v09_tiles_overhead_aware/
```

All new augmented DSM work should write to:

```text
data/raw/buildings_v10/
data/features_3d/v10/
data/rasters/v10/
data/grid/v10/
outputs/v10_*/
docs/v10/
```
