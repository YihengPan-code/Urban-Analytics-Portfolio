# B8.7b N300 Execution Precheck

Status: `B87B_PRECHECK_NEEDS_LOCAL_ASSET_REMAP`

## 1. Why B8.7b follows B8.6g3

B8.6g3 closed the N300 v4 source-review caveats, kept the candidate design at 150 rows, confirmed zero overlap with the labelled N150 set, and kept AOI/B9 blocked because true-vector gaps remain. B8.7b therefore checks whether a future N300 SOLWEIG execution package can be prepared, without preparing that package.

## 2. N300 v4 design validation

- New candidate count: `150`
- Duplicate new candidate cells: `0`
- N150 overlap: `0`
- Caveat cells carried: `TP_0103`, `TP_0104`, `TP_0464`, `TP_0159`, `TP_0519`
- Excluded water cells remain absent: `TP_0830`, `TP_0858`, `TP_0943`

## 3. N300 total sample index

Existing labelled N150 cells plus new N150 candidates produce `300` unique cells. Existing rows are treated as labelled context, not new execution rows.

## 4. Expected run count

`2 forcing days x 5 hours x 2 scenarios = 3000 additional preview runs`. Expected additional run count: `3000`.

## 5. Forcing design

The F5 design supplies the base versus overhead_as_canopy pair across two forcing days and five SGT hours. B8.7b reports the design and does not force a different one.

## 6. Asset readiness

150 new candidate cells audited; 150 have no prior local cell-asset mapping and require future local asset remap; no raster contents opened.

## 7. Path remap

10 path/remap rows; 4 unresolved or placeholder-only local-audit rows.

## 8. Pre-manifest schema preview

`b87b_pre_manifest_schema_preview.csv` is schema-only. `b87b_run_plan_preview.csv` is explicitly marked `precheck_only_not_execution_manifest=true`, `not_run_ready=true`, and `no_qgis_solweig_execution=true`.

## 9. Batch / resume / failure strategy

The preview recommends smoke, pilot, production chunk, and full-new-N150 grouping, plus append-only local logging, resume by run ID plus output metadata, and failure isolation by cell/day/hour/scenario. No runner is created.

## 10. Runtime/storage estimate

Runtime remains unknown because prior local logs are not reliable enough. Tmrt-only storage estimate 259.37 MB. Runtime remains caveated when local logs look like cached/subsecond local-copy timing.

## 11. Git hygiene

The guard table checks forbidden raster-like files, `svfs.zip`, raw roots, forecast CSVs, AOI/B9/WBGT/risk/hazard outputs, execution manifests, and QGIS/local runners. No staging or commit was performed.

## 12. Readiness decision

Final decision: `B87B_PRECHECK_NEEDS_LOCAL_ASSET_REMAP`.

## 13. What B8.7c may do next

B8.7c N300 execution package only after explicit authorization, starting with local asset remap; B8.6g4 external-vector acquisition remains required before AOI/B9. B8.7c may create a real execution package only after explicit user authorization and after local asset remap is resolved.

## 14. Claim boundaries

Not B9; not AOI-wide prediction; not local WBGT; not risk/hazard score; not observed truth; not causal feature importance; no raster read/write/copy; no QGIS/SOLWEIG execution; no run-ready N300 manifest; no QGIS runner; no Tmrt-to-WBGT conversion; no System A/B coupling.

## Files created

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
