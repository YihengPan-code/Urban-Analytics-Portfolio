# B8.5-F3c Status

Generated: 2026-05-27 05:08:25

## Status

`N24_STABILITY_REVIEW_READY`

## Branch

`codex/b85-f3c-n24-full-execution`

## Scope

N24 / 480-run controlled execution package, postrun validator, raster QA, and first-pass multi-forcing stability summaries. Codex/Python did not run QGIS/SOLWEIG. Preparation did not create, copy, move, or open rasters, and did not copy/open `svfs.zip`. Raster QA reads local raster contents only after human execution and postrun validation. This is not B9, not local WBGT, not risk, not N150, not full AOI, and not Tmrt-to-WBGT conversion.

## Key Results

- Manifest run count: `480`
- Unique cell count: `24`
- Pre-execution ready count: `480/480`
- Postrun status: `480/480_EXECUTED_OUTPUTS_VALID`
- Raster QA status: `PASS`
- Stability summary status: `PASS`
- Local run log path expected: `C:/OpenHeat-local/solweig/b85_f3c_n24/run_logs/b85_f3c_n24_qgis_run_log.csv`
- QGIS/SOLWEIG executed by Codex: `no`
- N150 / B9 status: `blocked_until_N24_execution_and_stability_review_pass`
- Notes: Human review of N24 stability evidence; N150 / B9 remains blocked until review passes.

## Files Created / Modified

- `configs/v12/systemb_b85_f3c_n24_full_execution.yaml`
- `scripts/v12_b85_f3c_prepare_n24.py`
- `scripts/v12_b85_f3c_validate_n24.py`
- `scripts/v12_b85_f3c_raster_qa.py`
- `scripts/v12_b85_f3c_stability_summary.py`
- `scripts/qgis/v12_b85_f3c_n24_qgis_runner.py`
- `docs/v12/OpenHeat_SystemB_B8_5_F3c_N24_full_execution_CN.md`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_n24_manifest.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_pre_execution_asset_check.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_expected_run_log_schema.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_manual_qgis_run_instructions.md`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_postrun_validation.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_raster_inventory.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_raster_stats.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_cell_hour_summary.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_pairwise_delta_by_cell_hour.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_forcing_day_contrast_by_cell_hour.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_alignment_qa.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_sanity_checks.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_stability_summary.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_unstable_cell_inventory.csv`
- `outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_n24_report.md`
- `outputs/v12_surrogate/b8_5_f3c_n24/B8_5_F3C_STATUS.md`

## Commands To Verify

- `python -m compileall scripts/v12_b85_f3c_prepare_n24.py scripts/v12_b85_f3c_validate_n24.py scripts/v12_b85_f3c_raster_qa.py scripts/v12_b85_f3c_stability_summary.py scripts/qgis/v12_b85_f3c_n24_qgis_runner.py`
- `python scripts/v12_b85_f3c_prepare_n24.py --config configs/v12/systemb_b85_f3c_n24_full_execution.yaml`
- `python scripts/v12_b85_f3c_validate_n24.py --config configs/v12/systemb_b85_f3c_n24_full_execution.yaml`
- `python scripts/v12_b85_f3c_raster_qa.py --config configs/v12/systemb_b85_f3c_n24_full_execution.yaml`
- `python scripts/v12_b85_f3c_stability_summary.py --config configs/v12/systemb_b85_f3c_n24_full_execution.yaml`
- Python mojibake check on `docs/v12/OpenHeat_SystemB_B8_5_F3c_N24_full_execution_CN.md`
- `git status --short -- .`
- forbidden-file check

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown control artifacts listed above after review.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and large forecast CSV files.
