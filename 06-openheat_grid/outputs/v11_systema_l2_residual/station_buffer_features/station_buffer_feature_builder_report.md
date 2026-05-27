# System A A-L2.1a Station-Local Buffer Feature Builder

Generated: 2026-05-27
Decision status: `BLOCKED_MISSING_SOURCES`
Branch: `codex/systema-l2-station-buffer-features`
Config: `configs/v11/systema_l2_station_buffer_features.yaml`

## 1. Why This Is Needed After A-L2.0

A-L2.0 found stable station-level residual structure after Level 1 context controls, while probability-error station signal was not stable enough. A-L2.1a therefore only builds and audits station-local context feature availability before any scoped residual preflight model is considered.

## 2. Difference From Old M5/M6 Toa Payoh-Only Morphology

Old M5/M6 morphology and overhead fields were Toa Payoh AOI/grid proxies. This builder requires station-local sources that cover all 27 NEA WBGT stations. Toa Payoh-only and grid-nearest proxies are inventoried but excluded from the 27-station buffer feature table.

## 3. Source Inventory

| source_kind | coverage_status | allowed_for_27_station_buffer_model | source_count |
| --- | --- | --- | --- |
| requested_feature_group_unavailable | unavailable_no_27_station_source | 0 | 7 |
| spatial_or_grid_table | ToaPayoh_only_or_AOI_limited | 0 | 18 |
| spatial_or_grid_table | unknown_or_unbounded_source_coverage | 0 | 13 |
| spatial_raster | ToaPayoh_only_or_AOI_limited | 0 | 2 |
| spatial_vector | ToaPayoh_only_or_AOI_limited | 0 | 20 |
| spatial_vector | bbox_covers_all_27_stations | 0 | 1 |
| spatial_vector | bbox_covers_no_station_centroids | 0 | 5 |
| spatial_vector | bbox_partial_station_coverage | 0 | 5 |
| station_coordinate_or_preflight_inventory | not_a_feature_source | 0 | 2 |
| station_coordinate_or_preflight_inventory | station_coordinates_cover_27 | 0 | 2 |

## 4. Features Built And Unavailable

| feature_group | allowed_for_future_model | feature_count | max_non_null | mean_missing_fraction |
| --- | --- | --- | --- | --- |
| built_impervious | 0 | 5 | 0 | 1 |
| distance_context | 0 | 3 | 0 | 1 |
| landuse_lcz | 0 | 2 | 0 | 1 |
| morphology | 0 | 5 | 0 | 1 |
| surface | 0 | 3 | 0 | 1 |
| vegetation | 0 | 5 | 0 | 1 |
| water | 0 | 3 | 0 | 1 |

## 5. 27-Station Coverage

Station count: `27`. Features with all-27 non-null coverage: `0`.

## 6. CRS / Buffer Validation

Station coordinates read as EPSG:4326 and projected to EPSG:3414 for metric buffers.

Buffers are defined in meters after station centroids are projected to SVY21 EPSG:3414. The QA table records the 50 m, 100 m, 250 m, and 500 m buffer-area checks.

## 7. Missingness And Constant-Feature Summary

All-NaN schema rows: `104`. Constant non-null feature rows: `0` because no environmental feature values were computed from valid all-27 sources.

## 8. Safe Features For Future A-L2.1c Scoped Residual Preflight

No environmental station-buffer feature is currently marked safe for future modelling. Future use requires all-27 station-local coverage, no leakage tokens, and A-L2.1b QA review.

## 9. Features And Sources Excluded

Toa Payoh-only/AOI-limited sources excluded: `40`.

| source_name | source_path | candidate_feature_groups | coverage_status | exclusion_reason |
| --- | --- | --- | --- | --- |
| v10_beta1_height_geometry_corrections | data/features_3d/v10/manual_qa/v10_beta1_height_geometry_corrections.csv | built_impervious;morphology | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v07 | data/grid/toa_payoh_grid_v07.csv |  | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v07_features | data/grid/toa_payoh_grid_v07_features.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v07_features_alpha | data/grid/toa_payoh_grid_v07_features_alpha.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v07_features_alpha_backup | data/grid/toa_payoh_grid_v07_features_alpha_backup.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v07_features_beta_final | data/grid/toa_payoh_grid_v07_features_beta_final.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v07_features_beta_final_v071_risk | data/grid/toa_payoh_grid_v07_features_beta_final_v071_risk.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v07_features_beta_gee | data/grid/toa_payoh_grid_v07_features_beta_gee.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v07_features_beta_gee_impervfix | data/grid/toa_payoh_grid_v07_features_beta_gee_impervfix.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v08_features_umep_with_veg | data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v08_umep_morphology | data/grid/toa_payoh_grid_v08_umep_morphology.csv | built_impervious;morphology | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v08_umep_morphology_with_veg | data/grid/toa_payoh_grid_v08_umep_morphology_with_veg.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v10_basic_morphology | data/grid/v10/toa_payoh_grid_v10_basic_morphology.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v10_features_overhead_sensitivity | data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v10_features_umep_with_veg | data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation;water | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_v10_umep_morphology_with_veg | data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_grid_sample | data/sample/toa_payoh_grid_sample.csv | built_impervious;distance_context;landuse_lcz;morphology;vegetation | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| toa_payoh_pois_sample | data/sample/toa_payoh_pois_sample.csv |  | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| dsm_buildings_2m_toapayoh | data/rasters/v08/dsm_buildings_2m_toapayoh.tif | built_impervious;morphology | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |
| dsm_vegetation_2m_toapayoh | data/rasters/v08/dsm_vegetation_2m_toapayoh.tif | built_impervious;distance_context;morphology;vegetation | ToaPayoh_only_or_AOI_limited | Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features. |

_Showing 20 of 40 rows._

## 10. Claim Boundaries

- No model was trained.
- No causal station-context correction is claimed.
- No station-adjusted WBGT was created.
- No local 100m WBGT was created.
- Screening correlations are QA only, not modelling evidence.

## Collinearity Screen

| feature_a | feature_b | spearman_r | abs_spearman | n_pairwise_non_null | status |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  | 0 | NO_NUMERIC_FEATURE_PAIRS |

## Output Files

- `station_context_source_inventory.csv`
- `station_buffer_feature_long.csv`
- `station_buffer_feature_wide.csv`
- `station_buffer_feature_schema.csv`
- `station_buffer_feature_qa.csv`
- `station_buffer_feature_missingness.csv`
- `station_buffer_feature_collinearity_screen.csv`
- `A_L2_1A_STATUS.md`
