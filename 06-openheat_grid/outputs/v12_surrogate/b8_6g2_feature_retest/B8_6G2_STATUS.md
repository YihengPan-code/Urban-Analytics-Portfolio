# B8.6g2 Status

Generated: 2026-05-27 23:03:52
Status: B86G2_DIAGNOSTIC_IMPROVEMENT_ONLY
Branch: codex/b86g2-feature-upgraded-surrogate-retest
Scope: System B feature-upgraded compact surrogate retest using B8.6g N150 features and F5 labels.

## Commands run by suite

- `python scripts/v12_b86g2_run_feature_retest.py --config configs/v12/systemb_b86g2_feature_retest.yaml`

## Key results

- Modeling rows / unique cells: 1500/150
- Selected two-stage workflow: b86g_proxy_features_only + logistic_regression / ridge
- Validation headline: spatial_holdout: Spearman=0.517, top10pct=0.500, false_promotion=0.163; cell_group_holdout: Spearman=0.527, top10pct=0.533, false_promotion=0.141; typology_holdout: Spearman=0.410, top10pct=0.562, false_promotion=0.209; forcing_day_holdout: Spearman=0.676, top10pct=0.600, false_promotion=0.109; hour_holdout: Spearman=0.665, top10pct=0.600, false_promotion=0.114
- Ablation headline: spatial_help=neighbourhood_context; neutral_false_promotion_help=canyon_roughness, edge_context, neighbourhood_context, overhead_geometry, pedestrian_shade, tree_building_interaction, typology_geometry; anchor_help=canyon_roughness, edge_context, neighbourhood_context, overhead_geometry, tree_building_interaction, typology_geometry
- AOI/B9 status: AOI_PREFLIGHT_BLOCKED / B9_BLOCKED
- Recommended next lane: B8.7-N300-PRE plus B8.6g3 true vector source acquisition

## Files created / modified

- `outputs\v12_surrogate\b8_6g2_feature_retest`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_input_inventory.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_dataset_schema.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_feature_leakage_audit.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_feature_set_registry.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_modeling_dataset.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_validation_splits.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_single_stage_metrics.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_two_stage_metrics.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_combined_pipeline_metrics.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_metrics_by_split.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_metrics_by_spatial_bin.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_metrics_by_typology.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_metrics_by_hour.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_feature_ablation_metrics.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_proxy_vs_vector_feature_comparison.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_anchor_cell_diagnostics.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_neutral_boundary_diagnostics.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_unstable_cell_diagnostics.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_worst_error_inventory.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_oof_predictions.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_baseline_comparison.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_promotion_gate.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_aoi_preflight_readiness_matrix.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_next_lane_decision_matrix.csv`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_model_card.md`
- `outputs\v12_surrogate\b8_6g2_feature_retest\b86g2_report.md`
- `outputs\v12_surrogate\b8_6g2_feature_retest\B8_6G2_STATUS.md`
- `docs\v12\OpenHeat_SystemB_B8_6g2_feature_retest_CN.md`

## Caveats

- Labels are SOLWEIG-derived compact Tmrt deltas, not observed truth.
- Feature effects are diagnostic and non-causal.
- This lane creates no AOI-wide prediction, B9 output, WBGT, hazard_score, risk_score, raster, QGIS/SOLWEIG run, Tmrt-to-WBGT conversion, or System A/B coupling output.

## Safe to commit after review

Compact B8.6g2 config, scripts, docs, CSV, and Markdown outputs.

## Not safe to commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide predictions, B9 outputs, WBGT, hazard_score, risk_score, and System A/B coupling outputs.
