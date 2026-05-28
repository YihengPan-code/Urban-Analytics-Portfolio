# B87E N300 Surrogate Benchmark Report

Generated: 2026-05-28 13:19:37

Status: `B87E_SURROGATE_BENCHMARK_PASS_NO_PROMOTION`

## 1. Task Definition

This benchmark tests surrogate models as emulators of SOLWEIG-derived `delta_tmrt_p90_c` and companion delta Tmrt labels. It is not WBGT calibration and not observed truth.

## 2. N300 Label Table Summary

- Rows/cells: `3000` rows, `300` expected cells.
- Primary target: `delta_tmrt_p90_c` (`overhead_as_canopy - base`).

## 3. Feature Source Summary

Static compact cell/context features were joined from the configured B86/B87 candidate feature sources. Coordinates, label source, protocol, sample group, cell ID, run/path/status columns, and target/Tmrt columns are excluded from the main feature set.

## 4. Feature Leakage Audit

See `b87e_feature_leakage_audit.csv`. Main models do not use label source, protocol ID, sample group, direct cell ID one-hot, target columns, base/overhead Tmrt columns, delta columns, run IDs, raster paths, output dirs, or status/error fields.

## 5. Validation Split Registry

Main/supporting evidence includes GroupKFold by `cell_id`, old-to-new generalization, spatial/typology/role holdouts where available, and context holdouts. Random split is diagnostic only.

## 6. Model Registry

The headline registry follows the N150-compatible order: featureless mean, context mean, ridge, elasticnet, random forest, extra trees, and hist gradient boosting. `extra_trees` is reported as the prior N150 model-card candidate baseline.

## 7. Metrics By Split

Best GroupKFold model by MAE: `extra_trees` with MAE `0.150376`. Full metrics are in `b87e_model_metrics_by_split.csv` and summaries in `b87e_model_metrics_summary.csv`.

## 8. Old-To-New And New-To-Old

Best old-to-new MAE model: `random_forest` with MAE `0.218676`. Reverse transfer is diagnostic only.

## 9. Error By Strata

See `b87e_error_by_strata.csv` for sample group, forcing day, hour, typology/spatial/role, and available water/tree/overhead proxy strata.

## 10. Ranking / Top-K Performance

Best GroupKFold rank Spearman observed among headline models: `0.749701`. Top-k overlaps are diagnostic ranking evidence, not a hazard/risk planning claim.

## 11. Promotion Decision

Promotion decision: `B87E_EXTRA_TREES_REMAINS_CANDIDATE`. No AOI/B9 inference is authorized in this lane.

## 12. Next Lane Recommendation

Recommended next lane: `B87F_surrogate_patch_stronger_features_before_any_AOI_preflight`.

## 13. Claim Boundaries

- No AOI/B9 output.
- No WBGT conversion.
- No risk/hazard map.
- No causal feature-importance claim.
- No observed truth claim.
