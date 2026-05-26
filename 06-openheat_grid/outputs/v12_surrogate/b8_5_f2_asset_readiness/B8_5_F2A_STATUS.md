# B8.5-F2a Status

Generated: 2026-05-26 23:52:20

## Status

PARTIAL_ASSETS_MISSING

## Branch

`codex/b85-f2a-asset-readiness`

## Scope

Local asset readiness and dry-run planning gate only. QGIS/SOLWEIG was not run. No rasters were created or copied. This is not B9. This is not local WBGT. This is not risk. No AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling output was created.

## Key Results

- Ready runs: `0/480`
- Missing/manual asset classes: `cell_geometry=24; local_output_root=1; met_forcing_file=5; qgis_algorithm_manual_check=1; raster_tile=145; svf_zip=48`
- Local output root status: `NEEDS_CREATE`
- QGIS/SOLWEIG executed: `no`
- Dry-run simulation log created: `yes`

## Next Recommended Action

Resolve missing local assets before manual QGIS execution. Missing/manual classes: cell_geometry=24; local_output_root=1; met_forcing_file=5; qgis_algorithm_manual_check=1; raster_tile=145; svf_zip=48. Local output root status: NEEDS_CREATE.

Manual QGIS execution can proceed only if readiness is `READY_FOR_MANUAL_QGIS`. If readiness is `PARTIAL_ASSETS_MISSING`, resolve the missing asset classes and exact manual checks listed in `b85_f2_missing_assets.csv` and `b85_f2_manual_execution_checklist.md`, then rerun this gate.

## Files Created / Modified

- `configs/v12/systemb_b85_f2_asset_readiness.yaml`
- `scripts/v12_b85_f2_asset_readiness.py`
- `scripts/v12_b85_run_f2_asset_readiness.py`
- `docs/v12/OpenHeat_SystemB_B8_5_F2_asset_readiness_CN.md`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_asset_readiness_summary.csv`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_asset_readiness_by_asset.csv`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_asset_readiness_by_run.csv`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_missing_assets.csv`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_local_output_root_check.csv`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_dry_run_simulation_log.csv`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_manual_execution_checklist.md`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/B8_5_F2A_STATUS.md`

## Git Status Short

```text
?? configs/v12/systemb_b85_f2_asset_readiness.yaml
?? docs/v12/OpenHeat_SystemB_B8_5_F2_asset_readiness_CN.md
?? outputs/v12_surrogate/b8_5_f2_asset_readiness/
?? scripts/v12_b85_f2_asset_readiness.py
?? scripts/v12_b85_run_f2_asset_readiness.py
```
