# B8 Lane Status

Status: PASS
Branch: codex/b8-surrogate-dataset-protocol
Scope: B8.0 surrogate-ready dataset audit + B8.1 validation split protocol only.

## Commands run

- `python -m compileall scripts/v12_b8_prepare_surrogate_dataset.py scripts/v12_b8_make_validation_splits.py scripts/v12_b8_run_audit_and_splits.py (attempted; python was not on PATH)`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -m compileall scripts/v12_b8_prepare_surrogate_dataset.py scripts/v12_b8_make_validation_splits.py scripts/v12_b8_run_audit_and_splits.py`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python scripts/v12_b8_run_audit_and_splits.py --config configs\v12\systemb_surrogate_b8_config.yaml`

## Files created / modified

- `configs/v12/systemb_surrogate_b8_config.yaml`
- `scripts/v12_b8_prepare_surrogate_dataset.py`
- `scripts/v12_b8_make_validation_splits.py`
- `scripts/v12_b8_run_audit_and_splits.py`
- `docs/v12/OpenHeat_SystemB_surrogate_dataset_protocol_CN.md`
- `outputs/v12_surrogate/B8_LANE_STATUS.md`
- `outputs/v12_surrogate/b8_dataset_audit/b8_dataset_audit_report.md`
- `outputs/v12_surrogate/b8_dataset_audit/feature_missingness.csv`
- `outputs/v12_surrogate/b8_dataset_audit/feature_schema.csv`
- `outputs/v12_surrogate/b8_dataset_audit/leakage_check_report.md`
- `outputs/v12_surrogate/b8_dataset_audit/surrogate_label_feature_matrix.csv`
- `outputs/v12_surrogate/b8_dataset_audit/target_distribution_summary.csv`
- `outputs/v12_surrogate/b8_validation_protocol/split_manifest_cell_grouped.csv`
- `outputs/v12_surrogate/b8_validation_protocol/split_manifest_feature_bin.csv`
- `outputs/v12_surrogate/b8_validation_protocol/split_manifest_hour_holdout.csv`
- `outputs/v12_surrogate/b8_validation_protocol/split_manifest_scenario_holdout.csv`
- `outputs/v12_surrogate/b8_validation_protocol/split_manifest_spatial.csv`
- `outputs/v12_surrogate/b8_validation_protocol/surrogate_validation_protocol.md`

## Key results

- B8.0 status: PASS
- B8.1 status: PASS
- Rows in surrogate label-feature matrix: 1500
- Unique cells: 150
- Scenarios: base, overhead_as_canopy
- hour_sgt values: 10, 12, 13, 15, 16
- Pre-B8.1.1 selected feature count: 195
- Selected B8.2 physical-core predictor columns: 115
- Excluded nonphysical/social columns: 16
- Excluded metadata/constant/contract columns: 92
- Leakage-like excluded columns: 7
- Cell-grouped manifest rows: 7500
- Spatial manifest rows: 6000 (PASS)
- Feature-bin manifest rows: 15002
- Valid feature-bin splits: svf_low_bin, svf_high_bin, shade_low_bin, shade_high_bin, overhead_low_bin, overhead_high_bin, road_hardscape_low_bin, road_hardscape_high_bin, building_density_low_bin, building_density_high_bin
- Blocked/degenerate feature-bin splits: water_low_bin, water_high_bin
- Hour-holdout manifest rows: 7500
- Scenario-holdout manifest rows: 3000

## Caveats

- No B8.2 model benchmark was implemented.
- No models were trained.
- No AOI-wide final outputs were created.
- No Tmrt values were converted to WBGT.
- `m_rad_pct01` is retained as a reference-domain modifier/label; B8 emphasizes `delta_tmrt_p90_c` and `tmrt_p90_c` as physical surrogate targets.
- Hygiene patch B8.1.1 tightened predictor eligibility and blocks degenerate feature-bin holdouts; B8.0/B8.1 status remains PASS.

## Safe to commit

- B8 config, scripts, protocol note, and compact CSV/Markdown outputs under `outputs/v12_surrogate/` after review.

## Not safe to commit

- `data/solweig/`, `data/rasters/`, raw archive files, `.tif`, `.tiff`, `svfs.zip`, patch zip packages, or large hourly forecast CSV outputs.

## Next recommended action

Review B8.0/B8.1 outputs and then open a separate B8.2 task for model benchmark design/implementation using these split manifests.
