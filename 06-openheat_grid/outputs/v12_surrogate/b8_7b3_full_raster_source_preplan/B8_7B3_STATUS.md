# B8.7b.3 Status

Status: B87B3_SOURCE_LOCK_READY_FOR_MATERIALIZATION
Branch: codex/b87b3-source-lock-svf-scenario-preplan
Scope: manual source ingestion, SVF scenario model, source version lock, and extraction/materialization preplan only.

## Key results

- DSM canonical status: `LOCKED (qa_corrected_final)`
- CDSM canonical status: `LOCKED (likely_final_base_vegetation_dsm)`
- grid status: `LOCKED (likely_final_geometry_source)`
- DEM/landcover not-applicable status: `DEM=NOT_APPLICABLE_GENERATE_FLAT_TILE (flat_dem_convention); landcover=NOT_APPLICABLE_NOT_USED (not_used_by_solweig_source_of_truth)`
- base SVF status: `LOCKED_FULL_AOI_SOURCE_ONLY (likely_final_building_plus_existing_vegetation)`
- overhead SVF status: `REQUIRES_SCENARIO_SPECIFIC_MATERIALIZATION (scenario_specific_materialization_required)`
- overhead source status: `LOCKED_CANONICAL_V10_OVERHEAD_LAYER`
- header metadata status: `HEADER_OK=3/3`
- extraction/materialization feasibility: `base=FEASIBLE_FOR_B87B4_PREMATERIALIZATION; overhead=FEASIBLE_FOR_B87B4_PREMATERIALIZATION`
- no-raster-write/no-pixel-read audit: `PASS: no raster pixel read; no raster write/copy/move/symlink; no svfs.zip open; no QGIS/SOLWEIG; no manifest/runner; no AOI/B9/WBGT/risk/coupling`
- next lane recommendation: `B8.7b.4 local-only materialization/pre-extraction package`

## Files created / modified

- `configs/v12/systemb_b87b3_full_raster_source_preplan.yaml`
- `scripts/v12_b87b3_input_inventory.py`
- `scripts/v12_b87b3_manual_source_ingest.py`
- `scripts/v12_b87b3_version_lock.py`
- `scripts/v12_b87b3_svf_scenario_model.py`
- `scripts/v12_b87b3_overhead_source_locator.py`
- `scripts/v12_b87b3_header_metadata.py`
- `scripts/v12_b87b3_grid_source_audit.py`
- `scripts/v12_b87b3_extraction_feasibility.py`
- `scripts/v12_b87b3_materialization_preplan.py`
- `scripts/v12_b87b3_readiness_decision.py`
- `scripts/v12_b87b3_run_full_raster_source_preplan.py`
- `docs/v12/OpenHeat_SystemB_B8_7b3_full_raster_source_preplan_CN.md`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_input_inventory.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_manual_source_ingest.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_version_lock_decision.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_svf_scenario_model.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_svf_candidate_version_audit.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_overhead_source_inventory.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_canonical_source_set.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_not_applicable_source_register.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_rejected_deprecated_source_register.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_header_metadata.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_grid_source_audit.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_extraction_feasibility_matrix.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_local_only_materialization_preplan.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_b87c_asset_readiness_projection.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_b87c_blocker_register.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_no_raster_write_audit.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_next_lane_decision_matrix.csv`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_codex_prompt_B87B4_local_only_materialization.md`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_codex_prompt_B87B3_source_review_patch.md`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/b87b3_report.md`
- `outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/B8_7B3_STATUS.md`
