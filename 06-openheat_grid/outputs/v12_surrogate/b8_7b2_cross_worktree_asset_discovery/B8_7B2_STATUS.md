# B8.7b.2 Status

Status: B87B2_BLOCKED_NO_ASSETS_FOUND
Branch: codex/b87b2-cross-worktree-asset-discovery
Scope: cross-worktree local asset discovery and remap planning only.

## Key results

- search roots checked: `7`
- candidate count: `150`
- resolved complete count: `0`
- resolved minimal SVF/DSM count: `0`
- partial count: `0`
- ambiguous count: `0`
- unresolved count: `150`
- main worktree hit count: `0`
- local root hit count: `0`
- no-raster-touch audit headline: `PASS: metadata only; no raster read/write/copy/open; no rasterio/GDAL; no QGIS/SOLWEIG; no manifest/runner; no symlink/junction`
- next lane recommendation: `B8.7b.4 asset generation`

## Files created / modified

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
