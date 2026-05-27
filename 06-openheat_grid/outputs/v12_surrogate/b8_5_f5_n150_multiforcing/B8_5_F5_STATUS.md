# B8.5-F5 Status

Generated: 2026-05-27 17:45:04

## Status

`N150_MULTIFORCING_STABILITY_REVIEW_READY`

## Branch

`codex/b85-f5-n150-multiforcing-precheck`

## Scope

N150 / 3000-run multi-forcing readiness and human-execution package only. Codex/Python did not run QGIS/SOLWEIG. This is not B9, not local WBGT, not risk, not observed truth, and not Tmrt-to-WBGT conversion.

## Key Results

- Manifest run count: `3000`
- Unique cell count: `150`
- Pre-execution ready count: `3000/3000`
- Postrun status: `3000/3000_EXECUTED_OUTPUTS_VALID`
- Raster QA status: `PASS`
- Label merge status: `PASS`
- Stability status: `PASS`
- Local run log path expected: `C:/OpenHeat-local/solweig/b85_f5_n150/run_logs/b85_f5_n150_qgis_run_log.csv`
- QGIS/SOLWEIG executed by Codex: `no`
- B9 status: `blocked`
- Notes: F5 stability summary created; B9 remains blocked pending separate promotion review.

## Files Created / Modified

- `configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `scripts/v12_b85_f5_prepare_n150_multiforcing.py`
- `scripts/v12_b85_f5_validate_n150_multiforcing.py`
- `scripts/v12_b85_f5_raster_qa.py`
- `scripts/v12_b85_f5_label_merge.py`
- `scripts/v12_b85_f5_stability_summary.py`
- `scripts/qgis/v12_b85_f5_n150_qgis_runner.py`
- `docs/v12/OpenHeat_SystemB_B8_5_F5_N150_multiforcing_CN.md`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_n150_manifest.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_pre_execution_asset_check.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_expected_run_log_schema.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_manual_qgis_run_instructions.md`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_postrun_validation.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_raster_inventory.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_raster_stats.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_cell_hour_summary.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_pairwise_delta_by_cell_hour.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_forcing_day_contrast_by_cell_hour.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_alignment_qa.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_sanity_checks.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_label_merge_plan.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_stability_summary.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_execution_risk_register.csv`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_report.md`
- `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/B8_5_F5_STATUS.md`

## Commands To Verify

- `python -m compileall scripts/v12_b85_f5_prepare_n150_multiforcing.py scripts/v12_b85_f5_validate_n150_multiforcing.py scripts/v12_b85_f5_raster_qa.py scripts/v12_b85_f5_label_merge.py scripts/v12_b85_f5_stability_summary.py scripts/qgis/v12_b85_f5_n150_qgis_runner.py`
- `python scripts/v12_b85_f5_prepare_n150_multiforcing.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `python scripts/v12_b85_f5_validate_n150_multiforcing.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `python scripts/v12_b85_f5_raster_qa.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `python scripts/v12_b85_f5_label_merge.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `python scripts/v12_b85_f5_stability_summary.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- Python mojibake check on `docs/v12/OpenHeat_SystemB_B8_5_F5_N150_multiforcing_CN.md`
- `git status --short -- .`
- forbidden-file check

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown control artifacts listed above after review.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and large forecast CSV files.
