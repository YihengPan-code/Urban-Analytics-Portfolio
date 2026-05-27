# B8.6e Spatial Failure and Feature-Gap Closure Package

Status: `B86E_SPATIAL_FEATURE_CLOSURE_PASS`

## 1. Why B8.6e Follows B8.6d

B8.6d kept the two-stage System B surrogate diagnostic-only because spatial holdout remained the main blocker. B8.6e therefore does not train a broader model zoo and does not create AOI-wide predictions. It diagnoses the spatial failure, audits missing feature families, tests only safe compact engineered features, and prepares a review-only targeted N300 candidate design.

Dataset rows/cells/features: 7310 joined diagnostic rows, 150 cells, 17 engineered diagnostic features.

## 2. Spatial Failure Headline

| spatial_bin | n_rows | n_cells | mean_abs_error | Spearman | top10pct_overlap | neutral_accuracy | false_promotion_rate | suspected_failure_type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| west_north | 350.000 | 35.000 | 0.154 | 0.074 | 0.250 | 0.634 | 0.240 | neutral-false-promotion|spatial-bin-out-of-domain |
| west_south | 400.000 | 40.000 | 0.218 | 0.082 | 0.000 | 0.608 | 0.115 | spatial-bin-out-of-domain |
| east_south | 380.000 | 38.000 | 0.174 | 0.244 | 0.500 | 0.726 | 0.182 | spatial-bin-out-of-domain |

## 3. Typology x Spatial Failure Headline

| typology | spatial_bin | n_cells | meaningful_cooling_support | neutral_support | median_true_delta_tmrt_p90_c | median_predicted_delta_tmrt_p90_c | false_promotion_rate | failure_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residential | west_north | 16.000 | 58.000 | 102.000 | -0.019 | 0.000 | 0.138 | feature-distribution-shift |
| residential | west_south | 15.000 | 35.000 | 115.000 | 0.000 | 0.000 | 0.167 | feature-distribution-shift|target-role-mismatch |
| civic_institutional | west_south | 10.000 | 44.000 | 56.000 | -0.002 | 0.000 | 0.100 | feature-distribution-shift|target-role-mismatch |
| transport | east_north | 11.000 | 110.000 | 0.000 | -0.464 | 0.000 |  | not-flagged |
| residential | east_north | 13.000 | 44.000 | 86.000 | -0.015 | 0.000 | 0.077 | not-flagged |

## 4. Anchor Underprediction Context

| cell_id | spatial_bin | typology | mean_true_delta_tmrt_p90_c | mean_predicted_delta_tmrt_p90_c | mean_abs_error | underprediction_rate_for_cooling | false_neutral_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0857 | east_north | hdb_canyon | -2.539 | 0.000 | 2.539 | 1.000 | 1.000 |
| TP_0433 | east_south | tree_shaded_reference | -0.807 | -0.187 | 0.620 | 1.000 | 0.600 |
| TP_0542 | east_north | river_edge_shaded_walkway | -0.495 | 0.000 | 0.495 | 1.000 | 1.000 |
| TP_0037 | west_south | other | -0.397 | 0.000 | 0.397 | 1.000 | 1.000 |
| TP_0141 | east_south | residential | -0.813 | -0.634 | 0.258 | 0.900 | 0.000 |

## 5. Neutral False-Promotion Context

| cell_id | split_family | spatial_bin | typology | known_neutral_flag | false_promotion_rate | mean_predicted_delta_tmrt_p90_c | mean_abs_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0005 | typology_holdout | west_south | residential | 0.000 | 1.000 | -1.637 | 1.637 |
| TP_0799 | typology_holdout | east_north | residential | 0.000 | 1.000 | -1.642 | 1.623 |
| TP_0379 | typology_holdout | west_south | residential | 0.000 | 1.000 | -1.624 | 1.591 |
| TP_0318 | spatial_holdout | east_south | water | 0.000 | 1.000 | -1.394 | 1.394 |
| TP_0254 | typology_holdout | east_south | residential | 0.000 | 1.000 | -1.398 | 1.372 |
| TP_0053 | typology_holdout | east_south | residential | 0.000 | 1.000 | -1.342 | 1.339 |
| TP_0237 | typology_holdout | west_south | residential | 0.000 | 1.000 | -1.331 | 1.331 |
| TP_0647 | typology_holdout | west_north | residential | 0.000 | 1.000 | -1.286 | 1.281 |

## 6. Feature Distribution Shift

| distribution_axis | group_value | feature | standardized_difference_vs_rest | missing_fraction | out_of_domain_flag |
| --- | --- | --- | --- | --- | --- |
| typology | grass_or_park_open | cu__dynamic_world_grass_fraction | 14.976 | 0.000 | 1.000 |
| typology | grass_or_park_open | cu__grass_fraction | 14.976 | 0.000 | 1.000 |
| typology | grass_or_park_open | grass_fraction | 14.976 | 0.000 | 1.000 |
| typology | river_edge_shaded_walkway | overhead_fraction_x_shade_fraction | 13.234 | 0.000 | 1.000 |
| typology | open_paved_high_svf | cu__svf_umep_p10_open_v10 | 6.376 | 0.000 | 1.000 |
| typology | water | cu__dynamic_world_water_fraction | 5.220 | 0.000 | 1.000 |
| typology | water | cu__water_fraction | 5.220 | 0.000 | 1.000 |
| typology | water | water_edge_or_water_fraction | 5.220 | 0.000 | 1.000 |

## 7. Domain Distance / OOD Diagnostics

Domain-distance rows written: 520. These distances are diagnostic only and are not production predictors.

| scope | cell_id | nearest_cell_id | feature_space_distance | distance_percentile | sparse_feature_space_flag |
| --- | --- | --- | --- | --- | --- |
| spatial_holdout_train_like_nearest | TP_0489 | TP_0133 | 212.251 | 0.927 | True |
| spatial_holdout_train_like_nearest | TP_0492 | TP_0614 | 1350.883 | 0.990 | True |
| spatial_holdout_train_like_nearest | TP_0542 | TP_0018 | 36.786 | 0.810 | False |
| spatial_holdout_train_like_nearest | TP_0543 | TP_0407 | 16.238 | 0.727 | False |
| spatial_holdout_train_like_nearest | TP_0569 | TP_0587 | 21.716 | 0.753 | False |
| spatial_holdout_train_like_nearest | TP_0575 | TP_0089 | 22.367 | 0.763 | False |
| spatial_holdout_train_like_nearest | TP_0599 | TP_0097 | 2.066 | 0.093 | False |
| spatial_holdout_train_like_nearest | TP_0600 | TP_0587 | 10.713 | 0.700 | False |

## 8. Feature Gap Register

| feature_family | currently_available | computable_from_existing_compact_tables | requires_new_data_or_processing | expected_benefit | recommended_lane |
| --- | --- | --- | --- | --- | --- |
| pedestrian-accessible shaded fraction | yes | yes | yes | high | B8.6f safe physical feature upgrade |
| connected shade corridor / shade continuity | no | no | yes | high | targeted feature acquisition / B8.6f preflight |
| overhead geometry shape descriptors | yes | yes | yes | medium-high | B8.6f safe physical feature upgrade |
| sunlit-hot-pocket area fraction | partial | yes | yes | high | external compact feature acquisition |
| local boundary / edge context | yes | yes | yes | medium | B8.6f safe physical feature upgrade |
| neighbourhood-scale context | yes | yes | yes | medium | targeted N300 design |
| tree/building shadow interaction | partial | yes | yes | high | B8.6f engineered feature probe |
| canyon orientation / height roughness | partial | yes | yes | medium-high | B8.6f feature acquisition |
| typology-specific geometry | yes | yes | yes | medium | targeted N300 typology balance |
| safe coordinate-context diagnostic | partial | yes | no | diagnostic-only | diagnostic only; not production predictor |

## 9. Safe Engineered Feature Probe

| feature_variant | MAE | Spearman | top10pct_overlap | neutral_accuracy | false_promotion_rate | anchor_MAE | Spearman_delta_vs_b86d | variant_decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b86d_selected_existing_oof | 0.224 | 0.172 | 0.312 | 0.667 | 0.238 | 0.771 | 0.000 | B86D_SELECTED_BASELINE |
| b86e_refit_full_safe_compact | 0.224 | 0.172 | 0.312 | 0.648 | 0.223 | 0.785 | 0.000 | DIAGNOSTIC_ONLY |
| coordinate_context_diagnostic | 0.263 | 0.208 | 0.125 | 0.655 | 0.235 | 0.934 | 0.036 | DIAGNOSTIC_ONLY_COORDINATE_DEPENDENT |
| safe_physical_engineered | 0.243 | 0.176 | 0.250 | 0.648 | 0.221 | 0.983 | 0.004 | DIAGNOSTIC_ONLY |
| safe_physical_plus_distance_diagnostic | 0.237 | 0.189 | 0.188 | 0.656 | 0.192 | 1.001 | 0.017 | DIAGNOSTIC_ONLY_DISTANCE_DEPENDENT |

Safe physical feature probe summary:

| split_family | Spearman_delta_vs_b86d | top10_delta_vs_b86d | variant_decision |
| --- | --- | --- | --- |
| cell_group_holdout | -0.082 | -0.133 | DIAGNOSTIC_ONLY |
| spatial_holdout | 0.004 | -0.062 | DIAGNOSTIC_ONLY |
| typology_holdout | 0.100 | -0.267 | FEATURE_UPGRADE_PROMISING |

## 10. Targeted N300 Design

150 targeted candidate-design cells selected; first roles: typology_gap_fill, typology_gap_fill, typology_gap_fill, typology_gap_fill, typology_gap_fill

This is candidate design only. It is not a SOLWEIG manifest, QGIS runner, N300 execution package, AOI-wide prediction, or B9 output.

## 11. Recommendation

- B8.6f: run a narrow improved-workflow lane only if reviewers accept the safe non-coordinate engineered features as diagnostic candidates, not as validated spatial-closure features; require the same spatial/typology/cell-group holdouts.
- Targeted N300: recommended if reviewers agree current compact features cannot close spatial failure; use the candidate design as a review list only.
- External feature acquisition: prioritize connected shade continuity, pedestrian-accessible shade, hot-pocket/open-sun fraction, and canyon orientation or roughness.
- AOI preflight: no-go until spatial holdout and neutral false-promotion are materially improved.

## 12. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not hazard_score or risk_score.
- Not observed truth.
- Not causal feature importance.
- No raster read/open/create/copy/write.
- No SOLWEIG or QGIS.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
