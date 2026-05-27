# B8.5-F3a Manual QGIS Micro-Batch Instructions

Generated: 2026-05-27 03:04:59

## Decision

`READY_FOR_HUMAN_MICROBATCH`

## Micro-Batch

- Cell: `TP_0037`
- Forcing days: `FD01_high_shortwave_hot_20260507, FD02_humid_hot_cloudy_or_diffuse_20260508`
- Hour SGT: `13`
- Scenarios: `base, overhead_as_canopy`
- Expected run count: `4`
- Pre-execution ready count: `4/4`

## Human Gate

Codex/Python did not run QGIS or SOLWEIG. This package authorizes only a 4-run human-controlled smoke test after review. It is not B9, not local WBGT, not risk, and not permission for a full 480-run execution.

## Required Manual Steps

1. Review the manifest: `outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_microbatch_manifest.csv`.
2. Review the repo-tracked runner without changing it: `scripts/qgis/v12_b85_f3a_microbatch_qgis_runner.py`.
3. Copy the runner to a local-only path under `C:/OpenHeat-local/solweig/b85_f3a_microbatch`.
4. In the local-only copy only, manually change `DRY_RUN = False` after confirming QGIS/UMEP and all assets.
5. Run only the four manifest rows. DO NOT RUN FULL 480.
6. Keep the run log at `C:/OpenHeat-local/solweig/b85_f3a_microbatch/run_logs/b85_f3a_microbatch_qgis_run_log.csv`.
7. Keep SOLWEIG outputs under `C:/OpenHeat-local/solweig/b85_f1_tiles` only.
8. Do not commit rasters, `svfs.zip`, or any local-only output.

## After Manual Execution

Run `python scripts/v12_b85_f3a_validate_microbatch.py --config configs/v12/systemb_b85_f3a_microbatch_execution.yaml`.
Full 480 execution remains blocked until this micro-batch validation passes.
