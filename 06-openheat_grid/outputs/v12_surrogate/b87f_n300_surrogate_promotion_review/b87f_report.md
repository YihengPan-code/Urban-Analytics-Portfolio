# B87F N300 Surrogate Promotion Review Report

Generated: 2026-05-28 14:11:59

Status: `B87F_EXTRA_TREES_REMAINS_CANDIDATE_NO_PROMOTION`

## 1. Current B87D/B87E State Recap

B87D passed as `B87D_N300_LABEL_INTEGRATION_PASS` with 3000 N300 pairwise rows and no blockers. B87E passed as `B87E_SURROGATE_BENCHMARK_PASS_NO_PROMOTION` but did not promote; `extra_trees` remained the prior candidate.

## 2. Why B87E Did Not Promote

B87E did not promote because no model superseded the prior `extra_trees` candidate across GroupKFold, transfer, and stress evidence. Old-to-new transfer favored `random_forest`, and source gaps from B8.6g3 remained explicit.

## 3. Target Distribution And Error Scale

See `b87f_target_distribution_deepdive.csv`. The target remains SOLWEIG simulated `delta_tmrt_p90_c` and companion delta Tmrt labels, not observed truth.

## 4. Feature Quality And Groups

See `b87f_feature_group_registry.csv`, `b87f_feature_quality_audit.csv`, and `b87f_feature_correlation_clusters.csv`. Coordinates, sample/design flags, label/protocol/status/path fields, target columns, base/overhead Tmrt columns, and delta columns are excluded from predictive feature sets.

## 5. Feature Set Variants

B87F compared exact B87E features, pruned low-missing/low-correlation features, physical-core variants, a context-residual two-stage variant, no-coordinate/no-design variants, and old-to-new robust pruning.

## 6. Split Stress Tests

Main evidence includes GroupKFold by `cell_id`, old-to-new transfer, spatial-bin, typology, and primary-role holdouts where available. Forcing-day and hour holdouts are supporting context stress tests; random split is diagnostic only.

## 7. Model Patch Results

Best B87F GroupKFold: `b87e_original_main / extra_trees MAE=0.150376`. Full metrics are in `b87f_patch_model_metrics_by_split.csv` and `b87f_patch_model_metrics_summary.csv`.

## 8. Old-To-New And New-To-Old Transfer

Best old-to-new result: `no_coordinates_no_design_flags / random_forest MAE=0.213904`. See `b87f_transfer_generalization_matrix.csv`.

## 9. Error Strata Deep Dive

See `b87f_error_strata_deepdive.csv` and `b87f_outlier_cell_context_register.csv` for sample group, forcing day, hour, typology, spatial bin, primary role, water/river caveat, vegetation, overhead, and shade/SVF proxy strata.

## 10. Rank And Top-K Diagnostics

Best rank Spearman: `0.769221`. Rank/top-k diagnostics are prioritisation diagnostics only, not hazard/risk claims.

## 11. Prior Extra-Trees Comparison

See `b87f_prior_candidate_comparison.csv` and `b87f_extra_trees_stability_audit.csv`. `extra_trees` remains the prior N150/B87E candidate baseline.

## 12. Promotion Review And AOI Preflight Gate

Promotion decision: `NO_AOI_PREFLIGHT`. AOI preflight gate: `BLOCKED_NO_AOI_PREFLIGHT`. No AOI/B9 inference was created.

## 13. Next Lane

Recommended next lane: `B87F2_feature_patch_and_B86g4_true_vector_source_acquisition`.

## 14. Claim Boundaries

- No AOI/B9 output.
- No WBGT conversion.
- No risk/hazard map.
- No exposure/vulnerability output.
- No causal feature-importance claim.
- No observed truth claim.
- The surrogate is a SOLWEIG emulator only.

## Files Created

- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_input_inventory.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_b87e_replay_audit.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_target_distribution_deepdive.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_error_source_hypotheses.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_feature_group_registry.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_feature_quality_audit.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_feature_correlation_clusters.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_feature_set_registry.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_split_stress_test_registry.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_model_patch_registry.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_patch_model_metrics_by_split.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_patch_model_metrics_summary.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_patch_predictions_oof.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_patch_predictions_holdout.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_transfer_generalization_matrix.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_rank_topk_matrix.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_error_strata_deepdive.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_outlier_cell_context_register.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_prior_candidate_comparison.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_extra_trees_stability_audit.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_model_promotion_review.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_model_card_patch_summary.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_aoi_preflight_gate_matrix.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_blocker_register.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_next_lane_decision_matrix.csv`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_codex_prompt_B87G_aoi_preflight_or_B87F2_feature_patch.md`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/B87F_STATUS.md`
- `outputs/v12_surrogate/b87f_n300_surrogate_promotion_review/b87f_report.md`
- `docs/v12/OpenHeat_SystemB_B87F_N300_surrogate_promotion_review_CN.md`
