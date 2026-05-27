# B8.6c Status

Generated: 2026-05-27 19:28:28
Status: B86C_TWO_STAGE_PROMISING
Branch: codex/b86c-feature-hardening-audit
Scope: System B surrogate feature hardening and spatial/typology failure audit using compact F5 labels only.

## Commands run

- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -m compileall scripts/v12_b86c_feature_inventory.py scripts/v12_b86c_dataset.py scripts/v12_b86c_failure_audit.py scripts/v12_b86c_feature_set_models.py scripts/v12_b86c_two_stage_pretest.py scripts/v12_b86c_workflow_spec.py scripts/v12_b86c_run_feature_hardening.py`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python scripts/v12_b86c_run_feature_hardening.py --config configs/v12/systemb_b86c_feature_hardening.yaml`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -c "...mojibake check..."`
- `git status --short -- .`
- forbidden-file check over `git status --porcelain -- .`

## Files created / modified

- `configs/v12/systemb_b86c_feature_hardening.yaml`
- `scripts/v12_b86c_feature_inventory.py`
- `scripts/v12_b86c_dataset.py`
- `scripts/v12_b86c_failure_audit.py`
- `scripts/v12_b86c_feature_set_models.py`
- `scripts/v12_b86c_two_stage_pretest.py`
- `scripts/v12_b86c_workflow_spec.py`
- `scripts/v12_b86c_run_feature_hardening.py`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_input_inventory.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_candidate_inventory.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_safe_feature_catalog.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_rejected_feature_catalog.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_group_registry.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_set_registry.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_hardened_surrogate_dataset.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_split_failure_summary.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_spatial_failure_inventory.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_typology_failure_inventory.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_anchor_failure_audit.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_neutral_boundary_audit.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_unstable_cell_audit.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_core_hour_h10_contrast.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_set_model_metrics.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_two_stage_pretest_metrics.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_two_stage_confusion_summary.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_oof_prediction_audit.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_upgrade_recommendation.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_surrogate_workflow_v0_1.md`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_b86d_recommendation.md`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_decision_matrix.csv`
- `outputs/v12_surrogate/b8_6c_feature_hardening/b86c_report.md`
- `outputs/v12_surrogate/b8_6c_feature_hardening/B8_6C_STATUS.md`
- `docs/v12/OpenHeat_SystemB_B8_6c_feature_hardening_CN.md`

## Key results

- Feature candidates scanned: 289
- Safe/rejected counts: 158/131
- Feature-set headline: minimal_physics_interpretable/random_forest_regressor vs baseline random_forest_regressor: supporting Spearman 0.441 (+0.001), top10pct 0.245 (-0.024), MAE gain -1.4%.
- Spatial/typology headline: spatial flagged 2/4 bins; typology flagged 2/5 bins.
- Anchor/neutral/unstable headline: anchor underprediction rows 17; neutral confusion rows 29; unstable flagged rows 68.
- Two-stage headline: full_safe_compact, threshold=0.05, random_forest_classifier+random_forest_regressor: neutral_accuracy=0.770, supporting Spearman=0.489, top10pct=0.361, anchor_MAE=0.673.
- B8.6d recommendation: Recommend B8.6d to formalize the two-stage neutral-boundary workflow before any AOI-wide preflight; B9 remains blocked.
- AOI-wide/B9 status: BLOCKED: no AOI-wide prediction and no B9 output created.

## Caveats

- The audit uses SOLWEIG-derived F5 compact labels, not observed truth.
- Feature interpretation is diagnostic, not causal.
- h10 remains a caveated hour and is separated from core-hour behavior.
- No QGIS, SOLWEIG, raster reading, AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling was created.

## Safe to commit

- Compact config, scripts, docs, CSV, and Markdown outputs after review.

## Not safe to commit

- Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, and AOI-wide prediction outputs.
