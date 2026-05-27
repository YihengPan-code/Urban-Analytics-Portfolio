# B8.6b System B Surrogate Promotion Review

Generated: 2026-05-27 18:11:49

Status: `B86B_WEAK_NEEDS_FEATURE_UPGRADE`

## 1. Why B8.6b Follows F5

B8.6 found a weak single-forcing N150 surrogate baseline and kept forcing-day holdout as future-required. B8.5-F5 then completed the N150 multi-forcing compact label run. B8.6b therefore re-runs the surrogate promotion review using only F5 compact multi-forcing labels.

## 2. F5 Label Source And Row Counts

| candidate_name | path | exists | row_count | unique_cells | forcing_day_count | hour_count | usable_for_b86b_primary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| f5_pairwise_delta | outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_pairwise_delta_by_cell_hour.csv | True | 1500 | 150 | 2 | 5 | True |
| f5_cell_hour_summary | outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_cell_hour_summary.csv | True | 3000 | 150 | 2 | 5 | False |
| f5_forcing_day_contrast | outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_forcing_day_contrast_by_cell_hour.csv | True | 750 | 150 | 0 | 5 | False |
| f5_stability_summary | outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_stability_summary.csv | True | 42 | 3 | 0 | 5 | False |
| legacy_single_forcing_pairwise | outputs/v12_solweig_n150_execution/n150_base_vs_overhead_delta_merged.csv | True | 750 | 150 | 0 | 5 | False |

- B8.6b training labels: 1500 rows, 150 cells.
- Legacy single-forcing labels are metadata only and are not mixed into the training target.

## 3. Feature Source And Leakage Guard

| candidate_name | path | exists | row_count | label_cell_coverage | available_predictor_count | usable_for_b86b_features |
| --- | --- | --- | --- | --- | --- | --- |
| n150_sampling_feature_matrix | outputs/v12_systemb_n150_sample_design/n150_sampling_feature_matrix.csv | True | 981 | 150 | 10 | True |
| n150_candidate_universe | outputs/v12_systemb_n150_sample_design/n150_candidate_universe.csv | True | 986 | 150 | 3 | False |

- `cell_id` is group metadata only.
- `forcing_day_id` is excluded from primary predictors.
- Tmrt, delta, rank, WBGT, hazard, risk, vulnerability, exposure, raster, and output-path columns are excluded.

## 4. Target Definitions And Sensitivity

| target_name | role | available | non_null_count | source_definition |
| --- | --- | --- | --- | --- |
| delta_tmrt_p90_c | primary | True | 1500 | Primary: overhead_as_canopy minus base Tmrt p90 from F5 pairwise compact labels. |
| delta_tmrt_mean_c | secondary_or_sensitivity | True | 1500 | Sensitivity: overhead_as_canopy minus base Tmrt mean from F5 pairwise compact labels. |
| delta_tmrt_p50_c | secondary_or_sensitivity | True | 1500 | Sensitivity: overhead_as_canopy minus base Tmrt p50 from F5 pairwise compact labels. |
| delta_tmrt_p95_c | secondary_or_sensitivity | True | 1500 | Sensitivity: overhead_as_canopy minus base Tmrt p95 from F5 pairwise compact labels. |
| base_tmrt_p90_c | secondary_or_sensitivity | True | 1500 | Secondary absolute base-scenario Tmrt p90 from F5 labels. |
| overhead_tmrt_p90_c | secondary_or_sensitivity | True | 1500 | Secondary absolute overhead_as_canopy Tmrt p90 from F5 labels. |

| target | forcing_day_MAE | forcing_day_R2 | forcing_day_spearman | forcing_day_top10pct_overlap | target_card_verdict |
| --- | --- | --- | --- | --- | --- |
| delta_tmrt_p90_c | 0.0666 | 0.8496 | 0.8641 | 1.0000 | PRIMARY_REMAINS_TARGET_CARD_VARIABLE |
| delta_tmrt_mean_c | 0.2605 | 0.6907 | 0.8640 | 0.9000 | COMPANION_TARGET_RECOMMENDED_FOR_MEAN_MEDIAN_SENSITIVITY |
| delta_tmrt_p50_c | 0.7776 | 0.4976 | 0.7822 | 0.9000 | COMPANION_TARGET_RECOMMENDED_FOR_MEAN_MEDIAN_SENSITIVITY |
| delta_tmrt_p95_c | 0.0353 | 0.9030 | 0.7757 | 0.8667 | SECONDARY_SENSITIVITY_NOT_PRIMARY_REPLACEMENT |
| base_tmrt_p90_c | 10.1135 | -1.1715 | 0.8669 | 0.8000 | SECONDARY_SENSITIVITY_NOT_PRIMARY_REPLACEMENT |
| overhead_tmrt_p90_c | 10.1093 | -1.1571 | 0.8605 | 0.7667 | SECONDARY_SENSITIVITY_NOT_PRIMARY_REPLACEMENT |

## 5. Validation Split Design

- Primary: train FD01/test FD02 and train FD02/test FD01.
- Main supporting: grouped cell holdout, leave-one-hour-out, coordinate-bin spatial holdout, and typology holdout.
- Diagnostic only: random row split.

## 6. Model Family Comparison

| split_family | model | MAE | RMSE | R2 | Spearman_observed_vs_predicted | top10pct_overlap | MAE_improvement_fraction_over_dummy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cell_group_holdout | hist_gradient_boosting_regressor | 0.1605 | 0.2639 | 0.3524 | 0.5592 | 0.6667 | 0.2966 |
| cell_group_holdout | hist_gradient_boosting_regressor | 0.1868 | 0.2871 | -0.5482 | 0.3573 | 0.0000 | 0.0328 |
| cell_group_holdout | hist_gradient_boosting_regressor | 0.2023 | 0.5077 | -0.0052 | 0.5550 | 0.3333 | 0.1754 |
| cell_group_holdout | hist_gradient_boosting_regressor | 0.2035 | 0.2857 | -0.3372 | 0.4721 | 0.3333 | -0.1123 |
| cell_group_holdout | hist_gradient_boosting_regressor | 0.2261 | 0.4279 | 0.0126 | 0.3664 | 0.3333 | 0.1376 |
| forcing_day_holdout | hist_gradient_boosting_regressor | 0.0665 | 0.1477 | 0.8373 | 0.8625 | 1.0000 | 0.7034 |
| forcing_day_holdout | hist_gradient_boosting_regressor | 0.0667 | 0.1355 | 0.8618 | 0.8656 | 1.0000 | 0.6970 |
| hour_holdout | hist_gradient_boosting_regressor | 0.0343 | 0.0987 | 0.9401 | 0.9248 | 0.9333 | 0.8560 |
| hour_holdout | hist_gradient_boosting_regressor | 0.0353 | 0.0888 | 0.9513 | 0.9239 | 0.9333 | 0.8524 |
| hour_holdout | hist_gradient_boosting_regressor | 0.0451 | 0.1185 | 0.9104 | 0.9349 | 1.0000 | 0.8054 |
| hour_holdout | hist_gradient_boosting_regressor | 0.0540 | 0.1138 | 0.8912 | 0.9252 | 1.0000 | 0.7460 |
| hour_holdout | hist_gradient_boosting_regressor | 0.0737 | 0.1975 | 0.3641 | 0.8034 | 0.9333 | 0.6182 |
| random_split | hist_gradient_boosting_regressor | 0.0505 | 0.1079 | 0.8965 | 0.8889 | 0.7857 | 0.7716 |
| spatial_holdout | hist_gradient_boosting_regressor | 0.1351 | 0.2173 | 0.3211 | 0.3819 | 0.7500 | 0.3769 |
| spatial_holdout | hist_gradient_boosting_regressor | 0.1852 | 0.3080 | -1.6647 | 0.2690 | 0.2500 | 0.0979 |
| spatial_holdout | hist_gradient_boosting_regressor | 0.2059 | 0.3115 | -2.8195 | 0.4162 | 0.2500 | -0.2852 |
| spatial_holdout | hist_gradient_boosting_regressor | 0.3274 | 0.6127 | -0.0944 | 0.4778 | 0.0000 | 0.1033 |
| typology_holdout | hist_gradient_boosting_regressor | 0.1415 | 0.1614 | -0.1151 | 0.8944 | 0.0000 | 0.0278 |
| typology_holdout | hist_gradient_boosting_regressor | 0.1532 | 0.2321 | -0.0112 | 0.3140 | 0.2857 | 0.3192 |
| typology_holdout | hist_gradient_boosting_regressor | 0.1882 | 0.2845 | -6.2909 | 0.2351 | 0.0000 | -0.1253 |
| typology_holdout | hist_gradient_boosting_regressor | 0.2814 | 0.4601 | -0.0243 | 0.4073 | 0.3333 | 0.0667 |
| typology_holdout | hist_gradient_boosting_regressor | 0.2963 | 0.4363 | -1.4536 | 0.1047 | 0.0000 | -0.2328 |

## 7. Forcing-Day Holdout Results

- Forcing-day holdout MAE=0.0666, R2=0.850, Spearman=0.864, top10pct=1.000, improvement=70.0%.

## 8. Anchor / Neutral / Unstable Diagnostics

- anchor MAE=0.3778, anchor rank error=2.60, neutral accuracy=0.621, unstable MAE=0.1119.

| cell_id | split_family | MAE | abs_rank_error | mean_true_delta_tmrt_p90_c | mean_pred_delta_tmrt_p90_c |
| --- | --- | --- | --- | --- | --- |
| TP_0037 | cell_group_holdout | 0.3881 | 4.0000 | -0.3974 | -0.7855 |
| TP_0141 | cell_group_holdout | 0.5833 | 4.0000 | -0.8132 | -0.2472 |
| TP_0433 | cell_group_holdout | 0.2052 | 1.0000 | -0.8073 | -0.7677 |
| TP_0542 | cell_group_holdout | 0.4778 | 19.0000 | -0.4946 | -0.0168 |
| TP_0857 | cell_group_holdout | 2.4657 | 16.0000 | -2.5392 | -0.0735 |
| TP_0037 | forcing_day_holdout | 0.1678 | 3.0000 | -0.3769 | -0.4905 |
| TP_0037 | forcing_day_holdout | 0.0974 | 1.0000 | -0.4179 | -0.4515 |
| TP_0141 | forcing_day_holdout | 0.1895 | 2.0000 | -0.8599 | -0.7661 |
| TP_0141 | forcing_day_holdout | 0.2213 | 0.0000 | -0.7665 | -0.8429 |
| TP_0433 | forcing_day_holdout | 0.2593 | 1.0000 | -0.8298 | -0.8187 |
| TP_0433 | forcing_day_holdout | 0.2443 | 1.0000 | -0.7848 | -0.8742 |
| TP_0542 | forcing_day_holdout | 0.1381 | 0.0000 | -0.4825 | -0.5128 |
| TP_0542 | forcing_day_holdout | 0.1162 | 1.0000 | -0.5067 | -0.4906 |
| TP_0857 | forcing_day_holdout | 0.7584 | 0.0000 | -2.6888 | -1.9304 |
| TP_0857 | forcing_day_holdout | 0.9142 | 0.0000 | -2.3895 | -2.1370 |
| TP_0037 | hour_holdout | 0.2213 | 5.0000 | -0.2817 | -0.5030 |
| TP_0037 | hour_holdout | 0.1914 | 6.0000 | -0.3396 | -0.5087 |
| TP_0037 | hour_holdout | 0.0770 | 5.0000 | -0.4302 | -0.4703 |
| TP_0037 | hour_holdout | 0.0166 | 0.0000 | -0.4699 | -0.4533 |
| TP_0037 | hour_holdout | 0.0200 | 0.0000 | -0.4658 | -0.4858 |

## 9. h10 Caveat

- h10 metrics are stored separately in `b86b_model_metrics_by_split.csv` as `h10_MAE`, `h10_Spearman`, and `h10_top10pct_overlap`.
- h10 is retained as caveated context and is not anchor evidence by itself.

## 10. Promotion Gate Decision

| gate | status | evidence | next_action |
| --- | --- | --- | --- |
| label_input | PASS | F5 pairwise labels are used as the only training target source; expected 1500 rows. | Keep old single-forcing labels as metadata only. |
| feature_input | PASS | Compact N150 sample-design physical features plus hour_sgt; cell_id and forcing_day_id excluded from predictors. | Upgrade compact features only if generalisation remains weak. |
| forcing_day_holdout | PASS | hist_gradient_boosting_regressor: Spearman=0.864, top10pct=1.000, MAE=0.0666, R2=0.850, improvement=70.0% | Use this as primary promotion evidence; random split remains diagnostic only. |
| cell_spatial_typology_hour_holdouts | WARN | cell_group_holdout: Spearman=0.462, top10pct=0.333, improvement=10.6% | hour_holdout: Spearman=0.902, top10pct=0.960, improvement=77.6% | spatial_holdout: Spearman=0.386, top10pct=0.312, improvement=7.3% | typology_holdo | Treat any collapsing split as a feature/target hardening signal. |
| target_sensitivity | PASS | Most predictable target: base_tmrt_p90_c (Spearman=0.867); primary p90 Spearman=0.864. | Keep p90 primary by role; report mean/p50 as companion targets when they are more predictable or larger in magnitude. |
| anchor_neutral_unstable_audit | WARN | anchor MAE=0.3778, anchor rank error=2.60, neutral accuracy=0.621, unstable MAE=0.1119. | Keep h10 caveat separated and do not promote neutral-boundary cells from model artefacts. |
| h10_caveat | PASS | h10 metrics are reported separately in model metric outputs. | Do not use h10 alone as anchor evidence. |
| aoi_preflight | B86B_WEAK_NEEDS_FEATURE_UPGRADE | AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation. | AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation. |
| b9_status | BLOCKED | This lane is surrogate-promotion review only. | B9 remains separately scoped and blocked. |
| final_status | B86B_WEAK_NEEDS_FEATURE_UPGRADE | Best primary model: hist_gradient_boosting_regressor. Forcing-day holdout MAE=0.0666, R2=0.850, Spearman=0.864, top10pct=1.000, improvement=70.0%. | AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation. |

## 11. AOI-Wide Preflight

- AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation.
- This lane does not create AOI-wide prediction.

## 12. Feature Importance Diagnostic

| feature | importance | normalized_abs_importance | method | diagnostic_boundary |
| --- | --- | --- | --- | --- |
| overhead_fraction | 0.0808 | 0.1989 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| building_density | 0.0785 | 0.1931 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| shade_fraction | 0.0552 | 0.1358 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| road_or_hardscape_fraction | 0.0438 | 0.1077 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| svf_or_open_sky | 0.0432 | 0.1064 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| tree_or_gvi_fraction | 0.0328 | 0.0806 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| building_height_or_canyon_proxy | 0.0313 | 0.0771 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| impervious_or_built_fraction | 0.0177 | 0.0436 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| hour_sgt | 0.0154 | 0.0378 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| grass_fraction | 0.0052 | 0.0128 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |
| water_edge_or_water_fraction | 0.0024 | 0.0060 | permutation_importance_neg_mae | Non-causal model diagnostic only; does not prove real-world heat-risk drivers. |

## 13. Claim Boundaries

- This is not B9.
- This is not local WBGT.
- This is not risk.
- This is not observed truth.
- This is not causal feature importance.
- No raster is committed.
- No Tmrt-to-WBGT conversion is performed.
- No System A/B coupling output is created.
