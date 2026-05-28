# B8.7b.2 Cross-Worktree Asset Discovery

Status: `B87B2_BLOCKED_NO_ASSETS_FOUND`

## 1. Why this follows B8.7b.1

B8.7b.1 ended at `B87B1_WAITING_LOCAL_ROOTS`: the 150 new N300 candidates were known, met forcing and output roots were metadata-ready, but no cell tile folders or SVF/DSM/CDSM/DEM/landcover assets were resolved.

## 2. Main worktree vs B8 worktree

Current B8 worktree: `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid`.
Original/main worktree: `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid`.

## 3. Search roots

- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid`: yes (current_b8_worktree)
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid`: yes (main_worktree)
- `C:/OpenHeat-local`: yes (local_root)
- `C:/OpenHeat-local/solweig`: yes (local_root)
- `C:/OpenHeat-local/solweig/b85_f1_tiles`: yes (local_root)
- `C:/OpenHeat-local/solweig/b85_f5_n150`: yes (local_root)
- `C:/OpenHeat-local/solweig/b87c_n300/assets`: yes (local_root)

## 4. Discovery counts

- candidate count: `150`
- resolved complete count: `0`
- resolved minimal SVF/DSM count: `0`
- partial count: `0`
- ambiguous count: `0`
- unresolved count: `150`
- main worktree hit count: `0`
- local root hit count: `0`

## 5. SVF/DSM status

Required SVF/DSM resolution is `0/150`.

## 6. Per-cell mapping status

See `b87b2_candidate_asset_mapping.csv`, `b87b2_unresolved_cell_register.csv`, and `b87b2_ambiguous_cell_register.csv`.

## 7. Remap/materialization recommendation

No remap was performed. `b87b2_remap_plan.csv` and `b87b2_local_only_materialization_options.csv` are plan-only outputs.

## 8. Next lane

Recommended next lane: `B8.7b.4 asset generation`.

## 9. Boundaries

PASS: metadata only; no raster read/write/copy/open; no rasterio/GDAL; no QGIS/SOLWEIG; no manifest/runner; no symlink/junction. No QGIS/SOLWEIG, no run-ready manifest, no QGIS/local runner, no local execution package, no AOI/B9, no local WBGT, no hazard/risk score, and no System A/B coupling.

## Files created

- `configs/v12/systemb_b87b2_cross_worktree_asset_discovery.yaml`
- `scripts/v12_b87b2_input_inventory.py`
- `scripts/v12_b87b2_search_roots.py`
- `scripts/v12_b87b2_cell_asset_discovery.py`
- `scripts/v12_b87b2_asset_signature.py`
- `scripts/v12_b87b2_mapping_plan.py`
- `scripts/v12_b87b2_readiness_decision.py`
- `scripts/v12_b87b2_run_cross_worktree_asset_discovery.py`
- `docs/v12/OpenHeat_SystemB_B8_7b2_cross_worktree_asset_discovery_CN.md`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_input_inventory.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_search_root_inventory.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_cell_folder_candidates.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_asset_signature_by_folder.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_candidate_asset_mapping.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_unresolved_cell_register.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_ambiguous_cell_register.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_remap_plan.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_local_only_materialization_options.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_manual_mapping_template.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_manual_mapping_instructions.md`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_b87c_readiness_matrix.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_no_raster_touch_audit.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_next_lane_decision_matrix.csv`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_codex_prompt_B87B3_local_only_materialization.md`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_codex_prompt_B87C_N300_execution_package.md`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_report.md`
- `outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/B8_7B2_STATUS.md`
