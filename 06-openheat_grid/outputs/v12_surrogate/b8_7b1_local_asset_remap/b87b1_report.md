# B8.7b.1 Local Asset Remap Readiness

Status: `B87B1_WAITING_LOCAL_ROOTS`

## 1. Why B8.7b.1 follows B8.7b

B8.7b ended at `B87B_PRECHECK_NEEDS_LOCAL_ASSET_REMAP`: the N300 v4 design and run preview were coherent, but the 150 new candidates had no resolved local cell-asset mapping. B8.7b.1 therefore resolves or classifies only the local asset/path gap.

## 2. What B8.7b already passed

B8.7b passed the 150 new-candidate count, 150 existing labelled N150 count, 300 unique-cell index, and 3000-row preview. The preview remains non-executable and not run-ready.

## 3. Local root discovery

Manual local roots found: `no`. Roots resolved by metadata: `10`. Required root gaps: `2`.

## 4. Manual local root template status

`b87b1_manual_local_root_template.csv` and `b87b1_manual_local_root_instructions.md` were written. If roots cannot be inspected from this environment, fill the manual CSV at `outputs/v12_surrogate/b8_7b1_local_asset_remap/manual_inputs/b87b1_manual_local_roots.csv` and rerun.

## 5. Asset pattern registry

`b87b1_asset_pattern_registry.csv` declares cell tile folder, SVF, DSM, CDSM, DEM, landcover, met forcing, QGIS manual check, and output-root patterns. It creates no files.

## 6. Cell asset metadata audit

Audited `150` new candidates by metadata only. Cell tile folder resolved count: `0`.

## 7. Resolved readiness for all 150 new candidates

Ready cells: `0/150`. SVF/DSM/CDSM/DEM/landcover ready counts: `0/0/0/0/0`.

## 8. Missing / ambiguous asset register

waiting=1050; missing=0; ambiguous=0

## 9. B8.7c prerequisite checklist

`b87b1_b87c_prerequisite_checklist.csv` keeps B8.7c manifest/runner creation blocked unless local asset mapping is resolved and the user explicitly authorizes the future lane.

## 10. Readiness decision

Final decision: `B87B1_WAITING_LOCAL_ROOTS`. Recommended next lane: `B8.7b.2_local_asset_fix`.

## 11. What user must do if WAITING_LOCAL_ROOTS

Fill the manual local-root CSV with verified `use`, `missing`, `unknown`, or `not_applicable` statuses. Do not copy assets into Git; only provide compact metadata/path mappings, then rerun this lane.

## 12. Claim boundaries

Not B9; not AOI-wide prediction; not local WBGT; not risk/hazard score; not observed truth; not causal feature importance; no raster read/write/copy/open; no QGIS/SOLWEIG execution; no run-ready N300 manifest; no QGIS runner; no local runner; no Tmrt-to-WBGT conversion; no System A/B coupling.

## Files created

- `configs/v12/systemb_b87b1_local_asset_remap.yaml`
- `scripts/v12_b87b1_input_inventory.py`
- `scripts/v12_b87b1_local_root_inventory.py`
- `scripts/v12_b87b1_manual_root_template.py`
- `scripts/v12_b87b1_asset_path_patterns.py`
- `scripts/v12_b87b1_cell_asset_resolver.py`
- `scripts/v12_b87b1_asset_metadata_audit.py`
- `scripts/v12_b87b1_readiness_decision.py`
- `scripts/v12_b87b1_run_local_asset_remap.py`
- `docs/v12/OpenHeat_SystemB_B8_7b1_local_asset_remap_CN.md`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_input_inventory.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_prior_local_root_inventory.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_manual_local_root_template.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_manual_local_root_instructions.md`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_asset_pattern_registry.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_expected_paths.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_metadata_audit.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_readiness_resolved.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_missing_asset_register.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_local_root_gap_register.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_b87c_prerequisite_checklist.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_b87c_blocker_register.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_no_raster_touch_audit.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_next_lane_decision_matrix.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_codex_prompt_B87C_N300_execution_package.md`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_codex_prompt_B87B2_local_asset_fix.md`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_report.md`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/B8_7B1_STATUS.md`
