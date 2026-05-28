# B8.7b.1 Status

Status: B87B1_WAITING_LOCAL_ROOTS
Branch: codex/b87b1-local-asset-remap-readiness
Scope: local asset readiness and path remap only; no QGIS/SOLWEIG and no run-ready manifest.

## Key results

- manual local roots found: `yes`
- roots resolved count: `12`
- new candidate count: `150`
- cell_tile_folder resolved count: `0`
- SVF/DSM/CDSM/DEM/landcover ready counts: `0/0/0/0/0`
- met forcing readiness: `150/150`
- output root status: `150/150`
- missing / ambiguous asset headline: `waiting=900; missing=0; ambiguous=0`
- no-raster-touch audit headline: `PASS: no raster read/write/copy/open; no QGIS/SOLWEIG; no manifest/runner`
- AOI/B9 status: `AOI_PREFLIGHT_BLOCKED / B9_BLOCKED`
- recommended next lane: `B8.7b.2_local_asset_fix`

## Commands

- `python scripts/v12_b87b1_run_local_asset_remap.py --config configs/v12/systemb_b87b1_local_asset_remap.yaml`

## Files created / modified

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

## Caveats

B8.7b.1 is metadata-only. It creates no local runner, QGIS runner, run-ready N300 manifest, local execution package, AOI-wide prediction, B9 output, local WBGT, hazard/risk score, exposure/vulnerability score, Tmrt-to-WBGT conversion, observed-truth claim, causal feature-importance claim, or System A/B coupling.
