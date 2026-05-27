# B8.6b Status

Generated: 2026-05-27 18:11:49
Status: B86B_WEAK_NEEDS_FEATURE_UPGRADE
Branch: codex/b86b-surrogate-promotion-review
Scope: System B surrogate promotion review with F5 N150 multi-forcing compact labels only.

## Commands run

- Plain `python` was unavailable on PATH in this shell; equivalent commands were run through the `openheat` conda environment.
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -m compileall scripts/v12_b86b_surrogate_inventory.py scripts/v12_b86b_surrogate_dataset.py scripts/v12_b86b_validation_splits.py scripts/v12_b86b_surrogate_models.py scripts/v12_b86b_error_audit.py scripts/v12_b86b_run_surrogate_promotion.py`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python scripts/v12_b86b_run_surrogate_promotion.py --config configs/v12/systemb_b86b_surrogate_promotion.yaml`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -c "...mojibake check..."`
- `git status --short -- .`
- forbidden-file check over `git status --porcelain -- .`

## Files created / modified

- `configs/v12/systemb_b86b_surrogate_promotion.yaml`
- `scripts/v12_b86b_surrogate_inventory.py`
- `scripts/v12_b86b_surrogate_dataset.py`
- `scripts/v12_b86b_validation_splits.py`
- `scripts/v12_b86b_surrogate_models.py`
- `scripts/v12_b86b_error_audit.py`
- `scripts/v12_b86b_run_surrogate_promotion.py`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_input_inventory.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_label_source_inventory.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_feature_source_inventory.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_surrogate_dataset.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_feature_schema.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_target_schema.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_validation_splits.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_model_metrics_by_split.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_forcing_day_holdout_metrics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_cell_group_holdout_metrics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_hour_holdout_metrics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_spatial_holdout_metrics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_typology_holdout_metrics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_target_sensitivity_metrics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_topk_overlap_metrics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_anchor_cell_diagnostics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_neutral_boundary_diagnostics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_unstable_cell_diagnostics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_worst_error_inventory.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_feature_importance_diagnostics.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_promotion_decision_matrix.csv`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_promotion_gate.md`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_model_card.md`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_report.md`
- `outputs/v12_surrogate/b8_6b_surrogate_promotion/B8_6B_STATUS.md`
- `docs/v12/OpenHeat_SystemB_B8_6b_surrogate_promotion_CN.md`

## Key results

- Best primary model: hist_gradient_boosting_regressor
- Forcing-day headline: Forcing-day holdout MAE=0.0666, R2=0.850, Spearman=0.864, top10pct=1.000, improvement=70.0%.
- Cross-holdout headline: cell_group_holdout Spearman=0.462, top10pct=0.333; spatial_holdout Spearman=0.386, top10pct=0.312; typology_holdout Spearman=0.391, top10pct=0.124; hour_holdout Spearman=0.902, top10pct=0.960
- Target sensitivity headline: Most predictable target: base_tmrt_p90_c (Spearman=0.867); primary p90 Spearman=0.864.
- Diagnostics headline: anchor MAE=0.3778, anchor rank error=2.60, neutral accuracy=0.621, unstable MAE=0.1119.
- AOI-wide preflight recommendation: AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation.
- B9 status: BLOCKED

## Caveats

- The surrogate learns SOLWEIG-derived F5 labels, not observed truth.
- Feature importance diagnostics are non-causal.
- h10 remains a caveated hour and is reported separately.
- No QGIS, SOLWEIG, raster reading, AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling was created by this lane.

## Safe to commit

- Compact config, scripts, docs, CSV, and Markdown outputs after review.

## Not safe to commit

- Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and AOI-wide prediction outputs.

## Next recommended action

- AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation.
