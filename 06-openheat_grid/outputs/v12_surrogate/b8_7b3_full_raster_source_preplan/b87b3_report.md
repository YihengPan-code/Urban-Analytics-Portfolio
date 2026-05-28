# B8.7b.3 Full-Raster Source Preplan

Status: `B87B3_SOURCE_LOCK_READY_FOR_MATERIALIZATION`

## 1. Why B8.7b.3 follows B8.7b.2

B8.7b.2 searched for per-cell `TP_xxxx` assets and found none. The recovered context shows that the real inputs are full-AOI raster/vector sources, so B8.7b.3 locks those sources and plans future local materialization instead of treating missing per-cell folders as missing source data.

## 2. Cross-validation of locator results

Manual CSV, v12 typology config, v10 gamma config, and the source-of-truth recovery note all converge on the same canonical DSM/CDSM/grid/base SVF family. The overhead locator recovered `data/features_3d/v10/overhead/overhead_structures_v10.geojson` and cross-checked it against the expected path.

## 3. DSM final version justification

DSM status: `LOCKED (qa_corrected_final)`. The locked DSM is `dsm_buildings_2m_augmented_reviewed_heightqa.tif`, the QA-corrected final DSM after manual QA and height/geometry QA. Older v08 and intermediate v10 DSMs are rejected in `b87b3_rejected_deprecated_source_register.csv`.

## 4. DEM flat convention correction

`DEM=NOT_APPLICABLE_GENERATE_FLAT_TILE (flat_dem_convention); landcover=NOT_APPLICABLE_NOT_USED (not_used_by_solweig_source_of_truth)`. DEM is not a missing full-raster blocker; future materialization should generate flat DEM tiles locally.

## 5. Landcover not-used correction

Landcover is not required by the SOLWEIG source-of-truth for this lane because `INPUT_LC=None` and `USE_LC_BUILD=false`.

## 6. Base vs overhead SVF scenario model

Base geometry is building DSM + existing vegetation DSM. Overhead geometry is building DSM + max(existing vegetation DSM, overhead canopy). The two scenarios are separate in `b87b3_svf_scenario_model.csv`.

## 7. SVF full-AOI vs per-tile svfs.zip caveat

Base SVF status: `LOCKED_FULL_AOI_SOURCE_ONLY (likely_final_building_plus_existing_vegetation)`. The locked v10 `SkyViewFactor.tif` is a full-AOI base source, not a per-tile SOLWEIG `svfs.zip`. Overhead SVF status: `REQUIRES_SCENARIO_SPECIFIC_MATERIALIZATION (scenario_specific_materialization_required)`; it must be materialized scenario-specifically and must not reuse the base SVF.

## 8. Overhead source status

Overhead source status: `LOCKED_CANONICAL_V10_OVERHEAD_LAYER`. The recovered vector supports the overhead_as_canopy preplan if the current lock is accepted.

## 9. Header/grid metadata status

Header metadata status: `HEADER_OK=3/3`. Grid status: `LOCKED (likely_final_geometry_source)`. Grid coverage is recorded in `b87b3_grid_source_audit.csv`.

## 10. Extraction/materialization feasibility

Feasibility headline: `base=FEASIBLE_FOR_B87B4_PREMATERIALIZATION; overhead=FEASIBLE_FOR_B87B4_PREMATERIALIZATION`. B8.7b.3 performs no extraction; `b87b3_local_only_materialization_preplan.csv` only defines future target patterns and caveats.

## 11. Next lane recommendation

Recommended next lane: `B8.7b.4 local-only materialization/pre-extraction package`. Do not proceed directly to B8.7c.

## 12. Claim boundaries

PASS: no raster pixel read; no raster write/copy/move/symlink; no svfs.zip open; no QGIS/SOLWEIG; no manifest/runner; no AOI/B9/WBGT/risk/coupling.

## Git and workspace context

- pwd: `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid`
- git root: `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8`
- branch: `codex/b87b3-source-lock-svf-scenario-preplan`
- git status -sb -uno: `## codex/b87b3-source-lock-svf-scenario-preplan`
- git status --short -- .:

```text
?? configs/v12/systemb_b87b2_cross_worktree_asset_resolver.yaml
?? configs/v12/systemb_b87b3_full_raster_source_preplan.yaml
?? docs/v12/OpenHeat_SystemB_B8_7b2_cross_worktree_asset_resolver_CN.md
?? docs/v12/OpenHeat_SystemB_B8_7b3_full_raster_source_preplan_CN.md
?? outputs/v12_surrogate/b8_7b2_cross_worktree_asset_resolver/
?? outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/
?? scripts/v12_b87b2_asset_mapping_builder.py
?? scripts/v12_b87b2_cell_folder_discovery.py
?? scripts/v12_b87b2_run_cross_worktree_asset_resolver.py
?? scripts/v12_b87b3_extraction_feasibility.py
?? scripts/v12_b87b3_full_raster_locator.py
?? scripts/v12_b87b3_grid_source_audit.py
?? scripts/v12_b87b3_grid_source_locator.py
?? scripts/v12_b87b3_header_metadata.py
?? scripts/v12_b87b3_input_inventory.py
?? scripts/v12_b87b3_manual_source_ingest.py
?? scripts/v12_b87b3_materialization_preplan.py
?? scripts/v12_b87b3_overhead_source_locator.py
?? scripts/v12_b87b3_raster_header_audit.py
?? scripts/v12_b87b3_readiness_decision.py
?? scripts/v12_b87b3_run_full_raster_source_preplan.py
?? scripts/v12_b87b3_svf_scenario_model.py
?? scripts/v12_b87b3_version_audit.py
?? scripts/v12_b87b3_version_lock.py
```

## Files created

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
