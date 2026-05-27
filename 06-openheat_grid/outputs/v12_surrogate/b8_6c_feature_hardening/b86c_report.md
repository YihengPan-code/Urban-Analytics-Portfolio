# B8.6c Feature Hardening and Failure Audit

Generated: 2026-05-27 19:28:28

Status: `B86C_TWO_STAGE_PROMISING`

## 1. Why B8.6c Follows B8.6b

B8.6b showed strong forcing-day and hour transfer, but weak cell-group, spatial, and typology support. B8.6c therefore audits compact feature representation and failure modes before any AOI-wide or B9 work.

## 2. Feature Inventory and Leakage Guard

- Feature candidates scanned: 289
- Safe feature count: 158
- Rejected/metadata/leakage/future-required count: 131

| source_table | column_name | dataset_column | feature_group_hint |
| --- | --- | --- | --- |
| n150_sampling_feature_matrix | svf_or_open_sky | svf_or_open_sky | built_canyon_svf |
| n150_sampling_feature_matrix | shade_fraction | shade_fraction | overhead_shade |
| n150_sampling_feature_matrix | building_density | building_density | built_canyon_svf |
| n150_sampling_feature_matrix | building_height_or_canyon_proxy | building_height_or_canyon_proxy | built_canyon_svf |
| n150_sampling_feature_matrix | road_or_hardscape_fraction | road_or_hardscape_fraction | road_hardscape |
| n150_sampling_feature_matrix | tree_or_gvi_fraction | tree_or_gvi_fraction | vegetation_water |
| n150_sampling_feature_matrix | grass_fraction | grass_fraction | vegetation_water |
| n150_sampling_feature_matrix | water_edge_or_water_fraction | water_edge_or_water_fraction | vegetation_water |
| n150_sampling_feature_matrix | overhead_fraction | overhead_fraction | overhead_shade |
| n150_sampling_feature_matrix | impervious_or_built_fraction | impervious_or_built_fraction | road_hardscape |
| n150_candidate_universe | typology_label | cu__typology_label | typology_context |
| n150_candidate_universe | svf | cu__svf | built_canyon_svf |
| n150_candidate_universe | shade_fraction_base_v10 | cu__shade_fraction_base_v10 | overhead_shade |
| n150_candidate_universe | shade_fraction_overhead_sens | cu__shade_fraction_overhead_sens | overhead_shade |
| n150_candidate_universe | building_density | cu__building_density | built_canyon_svf |
| n150_candidate_universe | mean_building_height | cu__mean_building_height | built_canyon_svf |
| n150_candidate_universe | building_height_p90 | cu__building_height_p90 | built_canyon_svf |
| n150_candidate_universe | open_pixel_fraction | cu__open_pixel_fraction | full_safe_compact |
| ... | 140 more rows | | |

| source_table | column_name | classification | rejection_reason |
| --- | --- | --- | --- |
| n150_sampling_feature_matrix | cell_id | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | in_n24_completed | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | typology_label | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | primary_role | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | secondary_roles | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | source_feature_completeness | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | sampling_feature_completeness | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | centroid_x | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | centroid_y | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | centroid_x_normalized | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | centroid_y_normalized | metadata | Identifier, split, or lane metadata; not a predictor. |
| n150_sampling_feature_matrix | svf_or_open_sky_missing | metadata | Sampling imputation/bin diagnostic column; not primary evidence predictor. |
| n150_sampling_feature_matrix | shade_fraction_missing | metadata | Sampling imputation/bin diagnostic column; not primary evidence predictor. |
| n150_sampling_feature_matrix | building_density_missing | metadata | Sampling imputation/bin diagnostic column; not primary evidence predictor. |
| n150_sampling_feature_matrix | building_height_or_canyon_proxy_missing | metadata | Sampling imputation/bin diagnostic column; not primary evidence predictor. |
| n150_sampling_feature_matrix | road_or_hardscape_fraction_missing | metadata | Sampling imputation/bin diagnostic column; not primary evidence predictor. |
| n150_sampling_feature_matrix | tree_or_gvi_fraction_missing | metadata | Sampling imputation/bin diagnostic column; not primary evidence predictor. |
| n150_sampling_feature_matrix | grass_fraction_missing | metadata | Sampling imputation/bin diagnostic column; not primary evidence predictor. |
| ... | 113 more rows | | |

## 3. Failure Mode Summary

| split_family | MAE | Spearman | top10pct_overlap | failure_type |
| --- | --- | --- | --- | --- |
| cell_group_holdout | 0.1856 | 0.5309 | 0.2667 | missing-feature-likely |
| forcing_day_holdout | 0.0881 | 0.7714 | 0.8667 | not-flagged |
| hour_holdout | 0.0899 | 0.7684 | 0.8933 | not-flagged |
| spatial_holdout | 0.1883 | 0.4133 | 0.2500 | spatial-bin-out-of-domain |
| typology_holdout | 0.1921 | 0.3721 | 0.2190 | typology-out-of-domain |

## 4. Spatial / Typology / Anchor Diagnostics

- spatial flagged 2/4 bins; typology flagged 2/5 bins.
- anchor underprediction rows 17; neutral confusion rows 29; unstable flagged rows 68.

| split_name | n_cells | MAE | Spearman | top10pct_overlap | failure_type |
| --- | --- | --- | --- | --- | --- |
| spatial_east_north | 37 | 0.3228 | 0.5350 | 0.2500 | not-flagged |
| spatial_east_south | 38 | 0.1328 | 0.3796 | 0.2500 | spatial-bin-out-of-domain |
| spatial_west_north | 35 | 0.1308 | 0.2896 | 0.5000 | not-flagged |
| spatial_west_south | 40 | 0.1668 | 0.4490 | 0.0000 | spatial-bin-out-of-domain |

| split_name | n_cells | MAE | Spearman | top10pct_overlap | failure_type |
| --- | --- | --- | --- | --- | --- |
| typology_civic_institutional | 27 | 0.1385 | 0.2094 | 0.0000 | typology-out-of-domain |
| typology_commercial | 8 | 0.1670 | -0.1174 | 0.0000 | typology-out-of-domain |
| typology_park_open_space | 6 | 0.2809 | 0.6296 | 0.0000 | not-flagged |
| typology_residential | 65 | 0.1247 | 0.5007 | 0.4286 | not-flagged |
| typology_transport | 25 | 0.2495 | 0.6381 | 0.6667 | not-flagged |

## 5. Target Sensitivity Implications

B8.6c keeps `delta_tmrt_p90_c` as the primary target because it matches the local radiative priority-card role. Mean, p50, and p95 deltas remain companion checks rather than replacements.

## 6. Two-Stage Pretest Result

- full_safe_compact, threshold=0.05, random_forest_classifier+random_forest_regressor: neutral_accuracy=0.770, supporting Spearman=0.489, top10pct=0.361, anchor_MAE=0.673.

| feature_set | neutral_threshold_c | classifier | regressor | neutral_accuracy | Spearman | top10pct | anchor_MAE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| b86b_baseline_features | 0.0500 | hist_gradient_boosting_classifier | hist_gradient_boosting_regressor | 0.6831 | 0.3673 | 0.1573 | 0.7380 |
| b86b_baseline_features | 0.0500 | hist_gradient_boosting_classifier | random_forest_regressor | 0.6831 | 0.3780 | 0.2449 | 0.8169 |
| b86b_baseline_features | 0.0500 | hist_gradient_boosting_classifier | ridge | 0.6831 | 0.3382 | 0.2066 | 0.7487 |
| b86b_baseline_features | 0.0500 | logistic_regression | hist_gradient_boosting_regressor | 0.7071 | 0.4180 | 0.2432 | 0.7085 |
| b86b_baseline_features | 0.0500 | logistic_regression | random_forest_regressor | 0.7071 | 0.4178 | 0.2313 | 0.7639 |
| b86b_baseline_features | 0.0500 | logistic_regression | ridge | 0.7071 | 0.3782 | 0.2032 | 0.7053 |
| b86b_baseline_features | 0.0500 | random_forest_classifier | hist_gradient_boosting_regressor | 0.7268 | 0.4096 | 0.1811 | 0.6625 |
| b86b_baseline_features | 0.0500 | random_forest_classifier | random_forest_regressor | 0.7268 | 0.4093 | 0.1616 | 0.7408 |
| b86b_baseline_features | 0.0500 | random_forest_classifier | ridge | 0.7268 | 0.3950 | 0.2526 | 0.7032 |
| b86b_baseline_features | 0.1000 | hist_gradient_boosting_classifier | hist_gradient_boosting_regressor | 0.7392 | 0.3861 | 0.2007 | 0.7105 |
| b86b_baseline_features | 0.1000 | hist_gradient_boosting_classifier | random_forest_regressor | 0.7392 | 0.3895 | 0.2551 | 0.7980 |
| b86b_baseline_features | 0.1000 | hist_gradient_boosting_classifier | ridge | 0.7392 | 0.3541 | 0.2347 | 0.7373 |
| ... | 69 more rows | | | | | | |

## 7. Feature Upgrade Recommendation

- minimal_physics_interpretable/random_forest_regressor vs baseline random_forest_regressor: supporting Spearman 0.441 (+0.001), top10pct 0.245 (-0.024), MAE gain -1.4%.
- Feature representation gaps remain the first explanation to audit when spatial/typology transfer collapses.

## 8. Workflow v0.1

- See `b86c_surrogate_workflow_v0_1.md` for the input, label, feature, validation, model, diagnostic, promotion, and forbidden-output contracts.

## 9. B8.6d Recommendation

- Recommend B8.6d to formalize the two-stage neutral-boundary workflow before any AOI-wide preflight; B9 remains blocked.

## 10. Claim Boundaries

- This is not B9.
- This is not AOI-wide prediction.
- This is not local WBGT.
- This is not risk.
- This is not observed truth.
- This is not causal feature importance.
- No raster operation was run or required.
- No SOLWEIG or QGIS operation was run.
- No Tmrt-to-WBGT conversion was performed.
- No System A/B coupling output was created.

## Decision Matrix

| gate | status | evidence | next_action |
| --- | --- | --- | --- |
| compact_inputs | PASS | 289 compact feature candidates scanned. | Use compact CSV inputs only. |
| leakage_guard | PASS | safe=158; rejected/metadata/leakage/future=131. | Keep target, rank, WBGT, risk, hazard, observed, path/status, and future risk-overlay columns excluded. |
| feature_set_hardening | DIAGNOSTIC | minimal_physics_interpretable/random_forest_regressor vs baseline random_forest_regressor: supporting Spearman 0.441 (+0.001), top10pct 0.245 (-0.024), MAE gain -1.4%. | Use only if supporting holdouts improve materially. |
| failure_audit | PASS | spatial flagged 2/4 bins; typology flagged 2/5 bins. anchor underprediction rows 17; neutral confusion rows 29; unstable flagged rows 68. | Carry failure types into B8.6d design. |
| two_stage_pretest | PROMISING | full_safe_compact, threshold=0.05, random_forest_classifier+random_forest_regressor: neutral_accuracy=0.770, supporting Spearman=0.489, top10pct=0.361, anchor_MAE=0.673. | Use only if neutral/spatial/typology/anchor diagnostics remain stable. |
| aoi_b9_status | BLOCKED | B8.6c is feature hardening/failure audit only. | Recommend B8.6d to formalize the two-stage neutral-boundary workflow before any AOI-wide preflight; B9 remains blocked. |
| final_status | B86C_TWO_STAGE_PROMISING | B8.6c compact outputs and workflow specification are complete. | Recommend B8.6d to formalize the two-stage neutral-boundary workflow before any AOI-wide preflight; B9 remains blocked. |
