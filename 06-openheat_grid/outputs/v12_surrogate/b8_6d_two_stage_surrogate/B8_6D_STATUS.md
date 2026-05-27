# B8.6d Status

Generated: 2026-05-27 20:29:14
Status: B86D_TWO_STAGE_DIAGNOSTIC_ONLY
Branch: codex/b86d-two-stage-surrogate-workflow
Scope: System B compact two-stage surrogate workflow formalization and long-run validation.

## Commands run

- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -m compileall scripts/v12_b86d_*.py`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python scripts/v12_b86d_run_two_stage_surrogate.py --config configs/v12/systemb_b86d_two_stage_surrogate.yaml`
- Python UTF-8/mojibake check for the Chinese doc
- `git status --short -- .`
- forbidden-file check over `git status --porcelain -- .`

## Key results

- Rows/cells/forcing days/hours: 1500/150/2/5
- Best threshold/classifier/regressor: 0.05 / logistic_regression / ridge
- Supporting headline: cell_group_holdout: Spearman=0.462, top10pct=0.600, neutral_acc=0.739; spatial_holdout: Spearman=0.172, top10pct=0.312, neutral_acc=0.667; typology_holdout: Spearman=0.361, top10pct=0.714, neutral_acc=0.714
- AOI-wide preflight recommendation: see promotion gate; no AOI-wide output is created here.
- B9 status: B9_BLOCKED

## Files created / modified

- `outputs\v12_surrogate\b8_6d_two_stage_surrogate`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_input_inventory.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_dataset_schema.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_two_stage_dataset.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_feature_set_registry.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_validation_splits.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_threshold_sweep_metrics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_stage1_classifier_metrics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_stage2_regressor_metrics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_combined_pipeline_metrics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_metrics_by_split.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_metrics_by_target.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_metrics_by_hour.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_metrics_by_typology.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_metrics_by_spatial_bin.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_seed_stability_metrics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_anchor_cell_diagnostics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_neutral_boundary_diagnostics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_unstable_cell_diagnostics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_worst_error_inventory.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_oof_predictions.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_feature_importance_diagnostics.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_target_role_decision.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_promotion_gate.csv`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_model_card.md`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_surrogate_workflow_v0_2.md`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\b86d_report.md`
- `outputs\v12_surrogate\b8_6d_two_stage_surrogate\B8_6D_STATUS.md`
- `docs\v12\OpenHeat_SystemB_B8_6d_two_stage_surrogate_CN.md`

## Caveats

- The labels are SOLWEIG-derived Tmrt deltas, not observed truth.
- Feature importance is diagnostic only and non-causal.
- h10 remains caveated and is separated from core-hour behavior.
- No raster, QGIS, SOLWEIG, AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling output was created.

## Safe to commit

Compact B8.6d config, scripts, docs, CSV, and Markdown outputs after review.

## Not safe to commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide predictions, and B9 outputs.
