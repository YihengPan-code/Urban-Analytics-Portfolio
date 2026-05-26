# B8.1 Surrogate Validation Split Protocol

Status: **PASS**

## Why Random Row Split Is Not Main Evidence

The row unit is `cell_id x hour_sgt x scenario`. A random row split would leak static cell-level features because the same cell could appear in both train and test rows. B8.1 therefore prioritizes cell-grouped, spatial, and feature-bin holdouts for cell generalization, with hour and scenario holdouts kept as transfer diagnostics.

## Split Family Definitions

- `cell_grouped_holdout`: deterministic five-fold cell holdout; group-safe by `cell_id`.
- `spatial_holdout`: Used `centroid_x_svy21` / `centroid_y_svy21` median-bin spatial blocks.
- `feature_bin_holdout`: low/high bins of available non-leaky feature families; group-safe by `cell_id`.
- `hour_holdout`: leave one `hour_sgt` out; tests hour transfer and may reuse cells across train/test by design.
- `scenario_holdout`: train one scenario and test the other; tests scenario transfer and may reuse cells across train/test by design.

## Leakage Checks For Grouped Splits

- cell_grouped_holdout cell leakage: PASS
- spatial_holdout cell leakage: PASS
- feature_bin_holdout cell leakage: PASS

## Group-Safe And Transfer Diagnostics

- Group-safe by cell_id: `cell_grouped_holdout`, valid `spatial_holdout`, `feature_bin_holdout`.
- Transfer diagnostics: `hour_holdout`, `scenario_holdout`.

## Feature-Bin Families

- Available families: svf -> `svf_umep_selected`, shade -> `shade_fraction_base_v10`, overhead -> `overhead_fraction_total`, water -> `water_fraction`, road_hardscape -> `road_fraction`, building_density -> `v10_building_density`
- Unavailable families: (none)
- Valid feature-bin splits: svf_low_bin, svf_high_bin, shade_low_bin, shade_high_bin, overhead_low_bin, overhead_high_bin, road_hardscape_low_bin, road_hardscape_high_bin, building_density_low_bin, building_density_high_bin
- Blocked/degenerate feature-bin splits: water_low_bin, water_high_bin
- A feature-bin split is valid only when both train and test have at least 30 unique cells.

## Spatial Split Status

- Spatial status: PASS
- Spatial note: Used `centroid_x_svy21` / `centroid_y_svy21` median-bin spatial blocks.

## Cell-Grouped Counts

| split_name | fold_id | role | row_count | cell_count |
|---|---:|---|---:|---:|
| cell_grouped_5fold | 1 | test | 300 | 30 |
| cell_grouped_5fold | 1 | train | 1200 | 120 |
| cell_grouped_5fold | 2 | test | 300 | 30 |
| cell_grouped_5fold | 2 | train | 1200 | 120 |
| cell_grouped_5fold | 3 | test | 300 | 30 |
| cell_grouped_5fold | 3 | train | 1200 | 120 |
| cell_grouped_5fold | 4 | test | 300 | 30 |
| cell_grouped_5fold | 4 | train | 1200 | 120 |
| cell_grouped_5fold | 5 | test | 300 | 30 |
| cell_grouped_5fold | 5 | train | 1200 | 120 |

## Spatial Counts

| split_name | fold_id | role | row_count | cell_count |
|---|---:|---|---:|---:|
| spatial_block_east_north | 1 | test | 370 | 37 |
| spatial_block_east_north | 1 | train | 1130 | 113 |
| spatial_block_east_south | 2 | test | 380 | 38 |
| spatial_block_east_south | 2 | train | 1120 | 112 |
| spatial_block_west_north | 3 | test | 350 | 35 |
| spatial_block_west_north | 3 | train | 1150 | 115 |
| spatial_block_west_south | 4 | test | 400 | 40 |
| spatial_block_west_south | 4 | train | 1100 | 110 |

## Feature-Bin Counts

| split_name | fold_id | role | row_count | cell_count |
|---|---:|---|---:|---:|
| building_density_high_bin | 12 | test | 300 | 30 |
| building_density_high_bin | 12 | train | 1200 | 120 |
| building_density_low_bin | 11 | test | 300 | 30 |
| building_density_low_bin | 11 | train | 1200 | 120 |
| overhead_high_bin | 6 | test | 300 | 30 |
| overhead_high_bin | 6 | train | 1200 | 120 |
| overhead_low_bin | 5 | test | 730 | 73 |
| overhead_low_bin | 5 | train | 770 | 77 |
| road_hardscape_high_bin | 10 | test | 300 | 30 |
| road_hardscape_high_bin | 10 | train | 1200 | 120 |
| road_hardscape_low_bin | 9 | test | 350 | 35 |
| road_hardscape_low_bin | 9 | train | 1150 | 115 |
| shade_high_bin | 4 | test | 300 | 30 |
| shade_high_bin | 4 | train | 1200 | 120 |
| shade_low_bin | 3 | test | 300 | 30 |
| shade_low_bin | 3 | train | 1200 | 120 |
| svf_high_bin | 2 | test | 300 | 30 |
| svf_high_bin | 2 | train | 1200 | 120 |
| svf_low_bin | 1 | test | 300 | 30 |
| svf_low_bin | 1 | train | 1200 | 120 |

## Hour-Holdout Counts

| split_name | fold_id | role | row_count | cell_count |
|---|---:|---|---:|---:|
| leave_hour_10_out | 1 | test | 300 | 150 |
| leave_hour_10_out | 1 | train | 1200 | 150 |
| leave_hour_12_out | 2 | test | 300 | 150 |
| leave_hour_12_out | 2 | train | 1200 | 150 |
| leave_hour_13_out | 3 | test | 300 | 150 |
| leave_hour_13_out | 3 | train | 1200 | 150 |
| leave_hour_15_out | 4 | test | 300 | 150 |
| leave_hour_15_out | 4 | train | 1200 | 150 |
| leave_hour_16_out | 5 | test | 300 | 150 |
| leave_hour_16_out | 5 | train | 1200 | 150 |

## Scenario-Holdout Counts

| split_name | fold_id | role | row_count | cell_count |
|---|---:|---|---:|---:|
| train_base_test_overhead_as_canopy | 2 | test | 750 | 150 |
| train_base_test_overhead_as_canopy | 2 | train | 750 | 150 |
| train_overhead_as_canopy_test_base | 1 | test | 750 | 150 |
| train_overhead_as_canopy_test_base | 1 | train | 750 | 150 |

## How B8.2 Should Consume These Manifests

- Join each manifest to `surrogate_label_feature_matrix.csv` by `row_id`.
- Use only `feature_schema.csv` rows with `role == feature` and `predictor_tier == physical_core` as headline candidate predictors.
- Do not consume feature-bin rows where `split_status == BLOCKED_DEGENERATE` as validation folds.
- Treat `delta_tmrt_p90_c` as the primary physical target and `tmrt_p90_c` as the secondary target.
- Retain `m_rad_pct01` as a reference-domain modifier/label for post-prediction interpretation, not as the only regression target.
- Do not use random row split as headline evidence.

## Caveats

- No models are trained in B8.1.
- No Tmrt value is converted to WBGT.
- No AOI-wide final output is created.
