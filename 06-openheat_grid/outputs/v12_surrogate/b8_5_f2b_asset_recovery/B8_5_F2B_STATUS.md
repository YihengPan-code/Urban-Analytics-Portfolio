# B8.5-F2b Status

Generated: 2026-05-27 01:42:50

## Status

`PARTIAL_REMAP_AVAILABLE`

## Scope

Local SOLWEIG asset discovery, root remap, and readiness simulation only. QGIS/SOLWEIG was not run. No rasters were created, copied, opened for analysis, or staged. `svfs.zip` was not copied or opened. This is not B9. This is not local WBGT. This is not risk. No AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling output was created.

## Key Results

- F2a ready runs: `0/480`
- F2b ready runs strict: `0/480`
- F2b ready runs if output root created: `0/480`
- F2b ready runs if QGIS check passes: `0/480`
- F2b ready runs if output root created and QGIS check passes: `240/480`
- Recovered assets by type: `cell_geometry=24; raster_tile=145; svf_zip=48`
- Still missing assets by type: `local_output_root=1; met_forcing_file=5; qgis_algorithm_manual_check=1`
- Selected root aliases: `original_project`
- Local output root action: `human_create_parent_and_directory`
- QGIS/SOLWEIG executed: `no`

## Files Created / Modified

- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_root_candidate_inventory.csv`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_asset_recovery_by_missing_asset.csv`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_asset_remap_table.csv`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_missing_after_remap.csv`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_run_readiness_after_remap.csv`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_readiness_delta_summary.csv`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_local_output_root_plan.csv`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_met_forcing_recovery_plan.csv`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_manual_remap_checklist.md`
- `outputs/v12_surrogate/b8_5_f2b_asset_recovery/B8_5_F2B_STATUS.md`
- `docs/v12/OpenHeat_SystemB_B8_5_F2b_asset_recovery_remap_CN.md`

## Caveats

Actual manual QGIS execution requires human confirmation of the QGIS/UMEP SOLWEIG algorithm and local-only output directory. Root aliases are discovery references only; large assets must remain uncommitted.
