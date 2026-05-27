# Future Codex prompt: B8.6g2 / B8.6f2 feature-upgraded surrogate retest

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.6g2/B8.6f2 compact feature-upgraded surrogate retest.

Use these B8.6g inputs:
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_n150_feature_dataset.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_schema.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_coverage_matrix.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_quality_checks.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_failure_context_feature_join.csv
- outputs/v12_surrogate/b8_6d_two_stage_surrogate/b86d_oof_predictions.csv

Task:
Run only a compact feature-upgraded surrogate retest against the existing N150 labelled cells. Compare against B8.6d/B8.6f diagnostics using blocked spatial, typology, cell-group, forcing-day, and hour holdouts. Do not use target-derived columns as predictors. Treat proxy/status/method columns as diagnostic metadata unless explicitly registered as predictors in the B8.6g schema.

Forbidden:
No AOI-wide prediction, no B9, no QGIS, no SOLWEIG, no raster read/write/open/copy, no local WBGT, no hazard_score, no risk_score, no observed-truth claim, no causal feature-importance claim, no Tmrt-to-WBGT conversion, and no System A/B coupling.

Required outputs:
CSV metrics by split, anchor/neutral diagnostics for TP_0857/TP_0542/TP_0433/TP_0037/TP_0141 and known neutral/near-zero cells, feature inclusion audit, leakage audit, Markdown report, and next-lane decision. Keep AOI/B9 blocked unless a later reviewed lane explicitly changes that boundary.
