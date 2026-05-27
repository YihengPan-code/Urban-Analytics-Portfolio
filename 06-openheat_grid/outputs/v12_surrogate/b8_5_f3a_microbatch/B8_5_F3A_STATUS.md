# B8.5-F3a Status

Generated: 2026-05-27 03:21:01

## Status

`MICRO_BATCH_EXECUTED_PASS`

## Branch

`codex/b85-f3a-microbatch-execution`

## Scope

Micro-batch execution package and postrun validator only. Codex/Python did not run QGIS/SOLWEIG. No rasters were created, copied, or opened by this lane. `svfs.zip` was not copied or opened. This is not B9. This is not local WBGT. This is not risk. This authorizes only a 4-run human-controlled micro-batch. Full 480 execution remains blocked until micro-batch validation passes.

## Key Results

- Selected cell_id: `TP_0037`
- Micro-batch run count: `4`
- Pre-execution ready count: `4/4`
- Postrun status: `4/4_EXECUTED_OUTPUTS_VALID`
- Local run log path expected: `C:/OpenHeat-local/solweig/b85_f3a_microbatch/run_logs/b85_f3a_microbatch_qgis_run_log.csv`
- QGIS/SOLWEIG executed by Codex: `no`
- Notes: Human run log found and validated without opening raster contents.

## Files Created / Modified

- `configs/v12/systemb_b85_f3a_microbatch_execution.yaml`
- `scripts/v12_b85_f3a_prepare_microbatch.py`
- `scripts/v12_b85_f3a_validate_microbatch.py`
- `scripts/qgis/v12_b85_f3a_microbatch_qgis_runner.py`
- `docs/v12/OpenHeat_SystemB_B8_5_F3a_microbatch_execution_CN.md`
- `outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_microbatch_manifest.csv`
- `outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_pre_execution_asset_check.csv`
- `outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_expected_run_log_schema.csv`
- `outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_manual_qgis_run_instructions.md`
- `outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_postrun_validation.csv`
- `outputs/v12_surrogate/b8_5_f3a_microbatch/B8_5_F3A_STATUS.md`

## Commands To Verify

- `python -m compileall scripts/v12_b85_f3a_prepare_microbatch.py scripts/v12_b85_f3a_validate_microbatch.py scripts/qgis/v12_b85_f3a_microbatch_qgis_runner.py`
- `python scripts/v12_b85_f3a_prepare_microbatch.py --config configs/v12/systemb_b85_f3a_microbatch_execution.yaml`
- `python scripts/v12_b85_f3a_validate_microbatch.py --config configs/v12/systemb_b85_f3a_microbatch_execution.yaml`
- `git status --short -- .`

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown control artifacts listed above after review.

## Not Safe To Commit

Rasters, `data/solweig/`, `data/rasters/`, `.tif`, `.tiff`, `svfs.zip`, raw archive dumps, patch zip packages, and large forecast CSV files.
