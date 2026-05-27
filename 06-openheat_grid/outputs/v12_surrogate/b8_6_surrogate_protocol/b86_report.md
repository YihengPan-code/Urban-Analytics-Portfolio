# B8.6 System B Surrogate Protocol / Baseline Gate

Generated: 2026-05-27 16:44:12

Status: `B86_WEAK_BASELINE_NEEDS_N150_MULTIFORCING`

## 1. Why B8.6 Follows F4

B8.5-F4 passed the N24 decision matrix and froze the target-card interpretation for `delta_tmrt_p90_c = overhead_as_canopy - base`. B8.6 therefore uses existing compact N150 labels, when available, to test a surrogate protocol and baseline gate. N24/F4 remains stress-validation context only.

## 2. Label Source Inventory

| candidate_name        | path                                                                      | exists   |   row_count | has_delta_tmrt_p90_c   | usable_for_b86_primary   |
|:----------------------|:--------------------------------------------------------------------------|:---------|------------:|:-----------------------|:-------------------------|
| pairwise_delta        | outputs/v12_solweig_n150_execution/n150_base_vs_overhead_delta_merged.csv | True     |         750 | True                   | True                     |
| focus_tmrt_summary    | outputs/v12_solweig_n150_execution/n150_focus_tmrt_summary_merged.csv     | True     |        1500 | False                  | False                    |
| modifier_targets      | outputs/v12_solweig_n150_execution/n150_modifier_targets_b5.csv           | True     |        1500 | True                   | False                    |
| b8_surrogate_matrix   | outputs/v12_surrogate/b8_dataset_audit/surrogate_label_feature_matrix.csv | True     |        1500 | True                   | False                    |
| discovered_n150_label | outputs/v12_solweig_n150_execution/n150_new_base_vs_overhead_delta.csv    | True     |           0 | True                   | False                    |

## 3. Feature Source Inventory

| candidate_name           | path                                                                                | exists   |   row_count |   available_feature_count | usable_for_b86_features   |
|:-------------------------|:------------------------------------------------------------------------------------|:---------|------------:|--------------------------:|:--------------------------|
| sample_feature_matrix    | outputs/v12_systemb_n150_sample_design/n150_sampling_feature_matrix.csv             | True     |         981 |                        10 | True                      |
| sample_feature_schema    | outputs/v12_systemb_n150_sample_design/n150_sampling_feature_schema.csv             | True     |          12 |                         0 | False                     |
| b8_surrogate_matrix      | outputs/v12_surrogate/b8_dataset_audit/surrogate_label_feature_matrix.csv           | True     |        1500 |                         3 | False                     |
| b8_feature_schema        | outputs/v12_surrogate/b8_dataset_audit/feature_schema.csv                           | True     |         227 |                         0 | False                     |
| discovered_feature_table | outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_asset_readiness_by_run.csv     | True     |           0 |                         0 | False                     |
| discovered_feature_table | outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_run_readiness_after_remap.csv | True     |           0 |                         0 | False                     |
| discovered_feature_table | outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_run_readiness.csv            | True     |           0 |                         0 | False                     |
| discovered_feature_table | outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_pre_execution_asset_check.csv     | True     |           0 |                         0 | False                     |
| discovered_feature_table | outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_pre_execution_asset_check.csv        | True     |           0 |                         0 | False                     |
| discovered_feature_table | outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_pairwise_delta_by_cell_hour.csv          | True     |           0 |                         0 | False                     |
| discovered_feature_table | outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_pre_execution_asset_check.csv            | True     |           0 |                         0 | False                     |
| discovered_feature_table | outputs/v12_surrogate/b8_6_surrogate_protocol/b86_surrogate_dataset.csv             | True     |           0 |                         0 | False                     |

## 4. Dataset Shape And Targets

- Dataset shape: 750 rows x 42 columns.
- Unique cells: 150.
- Scenario context: `overhead_as_canopy_minus_base`.

| target_name       | role                     | available   |   non_null_count | source_definition                                   |
|:------------------|:-------------------------|:------------|-----------------:|:----------------------------------------------------|
| delta_tmrt_p90_c  | primary                  | True        |              750 | overhead_as_canopy - base pairwise SOLWEIG Tmrt p90 |
| tmrt_p90_c        | secondary_or_sensitivity | True        |              750 | compact N150 label retained for sensitivity/context |
| delta_tmrt_mean_c | secondary_or_sensitivity | True        |              750 | compact N150 label retained for sensitivity/context |
| delta_tmrt_p95_c  | secondary_or_sensitivity | True        |              750 | compact N150 label retained for sensitivity/context |
| m_rad_pct01       | secondary_or_sensitivity | True        |              750 | compact N150 label retained for sensitivity/context |

## 5. Validation Split Protocol

- Available main split families: cell_group_holdout, hour_holdout, spatial_holdout, typology_holdout.
- `random_split` is diagnostic only and is not main evidence.
- `forcing_day_holdout` is future-required because existing N150 labels are single-forcing.

## 6. Baseline Model Results

- random_forest_regressor on delta_tmrt_p90_c: mean main-holdout MAE=0.1616, R2=-0.145, Spearman=0.611, MAE improvement vs dummy=50.9%

| split_family       | model                            |       MAE |     RMSE |         R2 |   Spearman_observed_vs_predicted |   MAE_improvement_fraction_over_dummy |
|:-------------------|:---------------------------------|----------:|---------:|-----------:|---------------------------------:|--------------------------------------:|
| cell_group_holdout | random_forest_regressor          | 0.178765  | 0.473795 |  0.171605  |                         0.573895 |                              0.456296 |
| cell_group_holdout | hist_gradient_boosting_regressor | 0.178811  | 0.433332 |  0.309498  |                         0.489383 |                              0.443765 |
| cell_group_holdout | elasticnet                       | 0.235825  | 0.478777 |  0.279607  |                         0.37211  |                              0.258306 |
| cell_group_holdout | ridge                            | 0.237189  | 0.479534 |  0.276628  |                         0.366933 |                              0.254245 |
| cell_group_holdout | linear_regression                | 0.237885  | 0.479866 |  0.275466  |                         0.364905 |                              0.252347 |
| cell_group_holdout | dummy_mean                       | 0.318491  | 0.604045 | -0.143881  |                       nan        |                              0        |
| hour_holdout       | random_forest_regressor          | 0.0761076 | 0.355155 |  0.69415   |                         0.824823 |                              0.764282 |
| hour_holdout       | hist_gradient_boosting_regressor | 0.095959  | 0.371539 |  0.65379   |                         0.748523 |                              0.70266  |
| hour_holdout       | elasticnet                       | 0.219268  | 0.473806 |  0.429109  |                         0.440997 |                              0.310077 |
| hour_holdout       | ridge                            | 0.219993  | 0.473987 |  0.428461  |                         0.439946 |                              0.307725 |
| hour_holdout       | linear_regression                | 0.220243  | 0.474148 |  0.427757  |                         0.439218 |                              0.306871 |
| hour_holdout       | dummy_mean                       | 0.316509  | 0.616699 | -0.0149418 |                       nan        |                              0        |
| spatial_holdout    | random_forest_regressor          | 0.202413  | 0.533209 |  0.0634701 |                         0.551462 |                              0.377576 |
| spatial_holdout    | hist_gradient_boosting_regressor | 0.218173  | 0.513208 |  0.100619  |                         0.493322 |                              0.321284 |
| spatial_holdout    | elasticnet                       | 0.250293  | 0.507792 |  0.224007  |                         0.370109 |                              0.221367 |
| spatial_holdout    | ridge                            | 0.251482  | 0.508666 |  0.219798  |                         0.366411 |                              0.217451 |
| spatial_holdout    | linear_regression                | 0.25286   | 0.509846 |  0.214871  |                         0.364519 |                              0.212964 |
| spatial_holdout    | dummy_mean                       | 0.320148  | 0.604412 | -0.0584638 |                       nan        |                              0        |
| typology_holdout   | hist_gradient_boosting_regressor | 0.180207  | 0.314543 | -0.167012  |                         0.384745 |                              0.485712 |
| typology_holdout   | random_forest_regressor          | 0.189299  | 0.361876 | -1.50948   |                         0.49493  |                              0.437699 |
| typology_holdout   | ridge                            | 0.236176  | 0.35424  | -0.374989  |                         0.241986 |                              0.289893 |
| typology_holdout   | elasticnet                       | 0.236242  | 0.354105 | -0.364943  |                         0.241111 |                              0.290532 |
| typology_holdout   | linear_regression                | 0.240856  | 0.358888 | -0.415863  |                         0.233727 |                              0.274549 |
| typology_holdout   | dummy_mean                       | 0.311346  | 0.424353 | -1.28891   |                       nan        |                              0        |

## 7. Holdout Weaknesses

- No forcing-day holdout is available for existing N150 labels.
- Scenario holdout is not applicable to the primary pairwise delta target because scenario has already been differenced.
- h10 remains caveated from F4 and is not anchor evidence.
- Any promising baseline remains a surrogate of SOLWEIG labels, not observed local heat truth.

## 8. Target Sensitivity

| target            | available   | best_model                       |   mean_main_MAE |   mean_main_spearman | b86_target_card_verdict                     |
|:------------------|:------------|:---------------------------------|----------------:|---------------------:|:--------------------------------------------|
| delta_tmrt_p90_c  | True        | random_forest_regressor          |        0.161646 |             0.611277 | PRIMARY_REMAINS_B8_6_TARGET_CARD            |
| tmrt_p90_c        | True        | random_forest_regressor          |        2.64406  |             0.900496 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| delta_tmrt_mean_c | True        | random_forest_regressor          |        0.2595   |             0.866057 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| delta_tmrt_p95_c  | True        | random_forest_regressor          |        0.125057 |             0.501852 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| m_rad_pct01       | True        | hist_gradient_boosting_regressor |        0.150172 |             0.690169 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |

## 9. N24 Stress-Validation Bridge

| cell_id   | bridge_role            | n150_label_present   | training_role                               |
|:----------|:-----------------------|:---------------------|:--------------------------------------------|
| TP_0115   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0301   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0326   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0366   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0492   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0565   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0676   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0960   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0986   | neutral_boundary       | True                 | stress_validation_context_only_not_training |
| TP_0037   | robust_priority_anchor | True                 | stress_validation_context_only_not_training |
| TP_0141   | robust_priority_anchor | True                 | stress_validation_context_only_not_training |
| TP_0433   | robust_priority_anchor | True                 | stress_validation_context_only_not_training |
| TP_0542   | robust_priority_anchor | True                 | stress_validation_context_only_not_training |
| TP_0857   | robust_priority_anchor | True                 | stress_validation_context_only_not_training |
| TP_0059   | unstable_review        | True                 | stress_validation_context_only_not_training |
| TP_0098   | unstable_review        | True                 | stress_validation_context_only_not_training |
| TP_0154   | unstable_review        | True                 | stress_validation_context_only_not_training |
| TP_0326   | unstable_review        | True                 | stress_validation_context_only_not_training |
| TP_0409   | unstable_review        | True                 | stress_validation_context_only_not_training |
| TP_0575   | unstable_review        | True                 | stress_validation_context_only_not_training |

## 10. Surrogate Role Decision

| gate                         | status                                    | evidence                                                                                                                             | next_action                                                                                |
|:-----------------------------|:------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------|
| label_input                  | PASS                                      | Dataset rows=750, targets=delta_tmrt_p90_c,tmrt_p90_c,delta_tmrt_mean_c,delta_tmrt_p95_c,m_rad_pct01.                                | Use compact N150 pairwise labels only; do not rerun SOLWEIG.                               |
| feature_input                | PASS                                      | Baseline feature count=11.                                                                                                           | Keep features compact and non-raster; do not derive new raster features in this lane.      |
| validation_protocol          | PASS                                      | Available split families: cell_group_holdout,hour_holdout,spatial_holdout,typology_holdout.                                          | Treat random_split as diagnostic only; keep grouped/holdout evidence primary.              |
| baseline_gate                | BASELINE_PROMISING                        | random_forest_regressor on delta_tmrt_p90_c: mean main-holdout MAE=0.1616, R2=-0.145, Spearman=0.611, MAE improvement vs dummy=50.9% | Review grouped/typology/hour holdout metrics before any promotion.                         |
| forcing_day_holdout          | FUTURE_REQUIRED                           | Existing N150 labels are single-forcing; no forcing-day holdout exists.                                                              | Run a future controlled N150 multi-forcing precheck/execution lane before B9 or promotion. |
| n24_stress_validation_bridge | PASS                                      | N24 bridge rows=21; stress-validation only.                                                                                          | Use N24 anchors/neutral/unstable cells for interpretation checks, not training.            |
| b9_status                    | BLOCKED                                   | B8.6 is surrogate protocol / baseline gate only.                                                                                     | Keep B9 blocked until separately scoped after N150 multi-forcing and promotion review.     |
| final_status                 | B86_WEAK_BASELINE_NEEDS_N150_MULTIFORCING | Protocol artifacts and baseline metrics were produced from compact inputs.                                                           | N150 multi-forcing remains the next hardening recommendation unless blockers are found.    |

## 11. Claim Boundaries

- This is not B9.
- This is not local WBGT.
- This is not risk.
- This is not observed truth.
- This is not causal feature importance.
- No raster is committed.
- No Tmrt-to-WBGT conversion is performed.
