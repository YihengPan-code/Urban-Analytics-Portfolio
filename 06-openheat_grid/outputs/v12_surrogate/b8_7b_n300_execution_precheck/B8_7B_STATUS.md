# B8.7b Status

Status: B87B_PRECHECK_NEEDS_LOCAL_ASSET_REMAP
Branch: codex/b87b-n300-execution-precheck
Scope: N300 execution precheck only; no QGIS/SOLWEIG execution and no run-ready manifest.

## Commands run by suite

- `python scripts/v12_b87b_run_execution_precheck.py --config configs/v12/systemb_b87b_n300_execution_precheck.yaml`

## Key results

- N300 v4 candidate count: `150`
- Existing N150 count: `150`
- Total unique cell count: `300`
- Expected additional run count: `3000`
- Forcing design: `2 forcing days x 5 hours x 2 scenarios = 3000 additional preview runs`
- Asset readiness: `150 new candidate cells audited; 150 have no prior local cell-asset mapping and require future local asset remap; no raster contents opened.`
- Path remap: `10 path/remap rows; 4 unresolved or placeholder-only local-audit rows.`
- AOI/B9: `AOI_PREFLIGHT_BLOCKED / B9_BLOCKED`
- Recommended next lane: `B8.7c N300 execution package only after explicit authorization, starting with local asset remap; B8.6g4 external-vector acquisition remains required before AOI/B9`

## Files created / modified

- `configs/v12/systemb_b87b_n300_execution_precheck.yaml`
- `scripts/v12_b87b_input_inventory.py`
- `scripts/v12_b87b_design_validation.py`
- `scripts/v12_b87b_sample_index.py`
- `scripts/v12_b87b_forcing_plan.py`
- `scripts/v12_b87b_asset_readiness.py`
- `scripts/v12_b87b_path_remap_audit.py`
- `scripts/v12_b87b_run_plan_preview.py`
- `scripts/v12_b87b_runtime_storage_estimate.py`
- `scripts/v12_b87b_git_hygiene.py`
- `scripts/v12_b87b_precheck_decision.py`
- `scripts/v12_b87b_run_execution_precheck.py`
- `docs/v12/OpenHeat_SystemB_B8_7b_N300_execution_precheck_CN.md`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_input_inventory.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_n300_v4_design_validation.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_n300_total_sample_index.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_new_candidate_sample_index.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_existing_n150_label_inventory.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_forcing_design_audit.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_expected_run_count.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_asset_source_inventory.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_cell_asset_readiness.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_local_path_remap_audit.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_pre_manifest_schema_preview.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_run_plan_preview.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_batch_grouping_plan.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_resume_failure_strategy.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_runtime_storage_estimate.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_no_raster_commit_guard.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_local_execution_boundary_checklist.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_qgis_console_safety_notes.md`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_execution_precheck_readiness_matrix.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_blocker_register.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_aoi_b9_boundary_matrix.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_next_lane_decision_matrix.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_codex_prompt_B87C_N300_execution_package.md`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_codex_prompt_B86G4_external_vector_acquisition.md`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_report.md`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/B8_7B_STATUS.md`

## Caveats

B8.7b is precheck only. It creates no QGIS runner, local runner, run-ready execution manifest, raster, AOI prediction, B9 output, local WBGT, hazard/risk/exposure/vulnerability score, Tmrt-to-WBGT conversion, or System A/B coupling.

## Safe to commit after review

Compact config, scripts, docs, CSV, and Markdown outputs listed above.

## Not safe to commit

Rasters, `.tif`, `.tiff`, `.vrt`, `.asc`, `.img`, `.nc`, `.grib`, `svfs.zip`, raw SOLWEIG/archive files, local-only run logs, patch zip packages, AOI-wide predictions, B9 outputs, WBGT, hazard_score, risk_score, and System A/B coupling outputs.
