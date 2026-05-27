# B8.5-F3b Manual QGIS One-Cell Full-Slice Instructions

Generated: 2026-05-27 03:54:04

## Decision

`READY_FOR_HUMAN_ONECELL_SLICE`

## Authorized Slice

- Cell: `TP_0037`
- Forcing days: `FD01_high_shortwave_hot_20260507, FD02_humid_hot_cloudy_or_diffuse_20260508`
- Hours SGT: `10, 12, 13, 15, 16`
- Scenarios: `base, overhead_as_canopy`
- Expected run count: `20`
- Pre-execution ready count: `20/20`

## Human Gate

Codex/Python did not run QGIS or SOLWEIG. This package authorizes only a 20-run one-cell human-controlled slice. It is not B9, not local WBGT, not risk, not System A/B coupling, and not permission for the full 480.

## Required Manual Steps

1. Review the manifest: `outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_onecell_manifest.csv`.
2. Review the repo-tracked runner without changing it: `scripts/qgis/v12_b85_f3b_onecell_qgis_runner.py`.
3. Copy the runner to a local-only path under `C:/OpenHeat-local/solweig/b85_f3b_onecell`.
4. In the local-only copy only, manually change `DRY_RUN = False`.
5. Run exactly the 20 manifest rows. DO NOT RUN FULL 480.
6. Keep the run log at `C:/OpenHeat-local/solweig/b85_f3b_onecell/run_logs/b85_f3b_onecell_qgis_run_log.csv`.
7. Keep SOLWEIG outputs under `C:/OpenHeat-local/solweig/b85_f1_tiles` only.
8. Do not commit rasters, `.tif`, `.tiff`, `svfs.zip`, local met forcing files, or local-only outputs.

## After Manual Execution

Run:

```powershell
python scripts/v12_b85_f3b_validate_onecell_fullslice.py --config configs/v12/systemb_b85_f3b_onecell_fullslice.yaml
python scripts/v12_b85_f3b_raster_qa.py --config configs/v12/systemb_b85_f3b_onecell_fullslice.yaml
```

Full 480 remains blocked until this one-cell full slice passes postrun validation and raster-content QA.
