# B8.6 Status

Status: B86_WEAK_BASELINE_NEEDS_N150_MULTIFORCING
Branch: codex/b86-surrogate-protocol-baseline
Scope: System B surrogate protocol / baseline gate only.

## Commands run

- `python --version` (plain `python` was not on PATH in this shell)
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -m compileall scripts/v12_b86_surrogate_inventory.py scripts/v12_b86_surrogate_dataset.py scripts/v12_b86_surrogate_baseline.py scripts/v12_b86_run_surrogate_protocol.py`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python scripts/v12_b86_run_surrogate_protocol.py --config configs/v12/systemb_b86_surrogate_protocol.yaml`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -c "...mojibake check..."`
- `git status --short -- .`
- PowerShell forbidden-file check over `git status --porcelain -- .`

## Files created / modified

- `configs/v12/systemb_b86_surrogate_protocol.yaml`
- `scripts/v12_b86_surrogate_inventory.py`
- `scripts/v12_b86_surrogate_dataset.py`
- `scripts/v12_b86_surrogate_baseline.py`
- `scripts/v12_b86_run_surrogate_protocol.py`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_input_inventory.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_label_source_inventory.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_feature_source_inventory.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_surrogate_dataset.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_feature_schema.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_target_schema.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_validation_splits.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_baseline_model_metrics.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_holdout_metrics.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_target_sensitivity_metrics.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_n24_stress_validation_bridge.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_surrogate_decision_matrix.csv`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_promotion_gate.md`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_model_card_draft.md`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/b86_report.md`
- `outputs/v12_surrogate/b8_6_surrogate_protocol/B8_6_STATUS.md`
- `docs/v12/OpenHeat_SystemB_B8_6_surrogate_protocol_CN.md`

## Key results

- N150 label source found: yes
- Dataset shape: 750 x 42
- Primary target availability: True
- Main validation splits available: cell_group_holdout, hour_holdout, spatial_holdout, typology_holdout
- Best baseline headline: random_forest_regressor on delta_tmrt_p90_c: mean main-holdout MAE=0.1616, R2=-0.145, Spearman=0.611, MAE improvement vs dummy=50.9%
- N24 stress-validation bridge headline: 21 bridge rows; robust anchors/neutral-boundary/unstable cells are stress-validation only.
- N150 multi-forcing recommendation: N150 multi-forcing precheck and controlled execution are required before promotion/B9.
- B9 status: BLOCKED

## Caveats

- Existing N150 labels are single-forcing.
- N24 is stress-validation context only.
- No QGIS/SOLWEIG/raster operation was run by this lane.
- No local WBGT, hazard_score, risk_score, or System A/B coupling output was created.
- No Tmrt-to-WBGT conversion was performed.

## Safe to commit

- Compact B8.6 config, scripts, docs, CSV, and Markdown outputs after review.

## Not safe to commit

- Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and AOI-wide prediction outputs.

## Next recommended action

- N150 multi-forcing precheck and controlled execution/hardening before surrogate promotion or B9.
