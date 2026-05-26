# B8.5-F2a Manual Execution Checklist

Generated: 2026-05-26 23:52:20

## Gate Status

- Decision: `PARTIAL_ASSETS_MISSING`
- Ready runs: `0/480`
- Local output root status: `NEEDS_CREATE`
- QGIS/SOLWEIG executed: `no`
- Rasters created or copied: `no`
- This is not B9, not local WBGT, and not risk.

## Required Before Manual QGIS

- Confirm the QGIS skeleton still has `DRY_RUN = True` until a human reviewer intentionally changes it inside QGIS.
- Confirm the UMEP Processing algorithm id manually inside QGIS.
- Confirm every required N24 focus-cell geometry, DSM/DEM/wall/vegetation raster input, SVF zip, and met forcing text file exists locally.
- Confirm the raw SOLWEIG output root is outside Git before execution.
- Do not commit rasters, `svfs.zip`, raw archive files, large forecast CSVs, or local SOLWEIG outputs.

## Missing Or Manual Checks

- `cell_geometry`: 24 required rows need manual confirmation.
- `TP_0037_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0037/focus_cell.geojson
- `TP_0059_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0059/focus_cell.geojson
- `TP_0088_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0088/focus_cell.geojson
- `TP_0098_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0098/focus_cell.geojson
- `TP_0115_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0115/focus_cell.geojson
- `TP_0141_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0141/focus_cell.geojson
- `TP_0154_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0154/focus_cell.geojson
- `TP_0254_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0254/focus_cell.geojson
- `TP_0301_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0301/focus_cell.geojson
- `TP_0326_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0326/focus_cell.geojson
- `TP_0366_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0366/focus_cell.geojson
- `TP_0409_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0409/focus_cell.geojson
- `TP_0433_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0433/focus_cell.geojson
- `TP_0492_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0492/focus_cell.geojson
- `TP_0542_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0542/focus_cell.geojson
- `TP_0565_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0565/focus_cell.geojson
- `TP_0575_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0575/focus_cell.geojson
- `TP_0627_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0627/focus_cell.geojson
- `TP_0676_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0676/focus_cell.geojson
- `TP_0773_focus_cell`: Regenerate or locate the focus-cell geometry/vector reference locally: data/solweig/v12_n24_tiles/TP_0773/focus_cell.geojson
- `cell_geometry`: 4 additional rows are listed in the missing-assets CSV.
- `local_output_root`: 1 required rows need manual confirmation.
- `manual_local_raw_output_root`: Create or confirm this local-only output root outside Git before manual QGIS execution: C:/OpenHeat-local/solweig/b85_f1_tiles
- `met_forcing_file`: 5 required rows need manual confirmation.
- `FD02_humid_hot_cloudy_or_diffuse_20260508_h10`: Create or locate the SOLWEIG met forcing text file, then update the package path if needed: data/solweig/v09_met_forcing_2026_05_08_S128_h10.txt
- `FD02_humid_hot_cloudy_or_diffuse_20260508_h12`: Create or locate the SOLWEIG met forcing text file, then update the package path if needed: data/solweig/v09_met_forcing_2026_05_08_S128_h12.txt
- `FD02_humid_hot_cloudy_or_diffuse_20260508_h13`: Create or locate the SOLWEIG met forcing text file, then update the package path if needed: data/solweig/v09_met_forcing_2026_05_08_S128_h13.txt
- `FD02_humid_hot_cloudy_or_diffuse_20260508_h15`: Create or locate the SOLWEIG met forcing text file, then update the package path if needed: data/solweig/v09_met_forcing_2026_05_08_S128_h15.txt
- `FD02_humid_hot_cloudy_or_diffuse_20260508_h16`: Create or locate the SOLWEIG met forcing text file, then update the package path if needed: data/solweig/v09_met_forcing_2026_05_08_S128_h16.txt
- `qgis_algorithm_manual_check`: 1 required rows need manual confirmation.
- `solweig_algorithm_id_hint`: Open QGIS/UMEP manually and confirm the algorithm id is available: umep:Outdoor Thermal Comfort: SOLWEIG
- `raster_tile`: 145 required rows need manual confirmation.
- `building_dsm_path`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif
- `TP_0037_dsm_buildings`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0037/dsm_buildings_tile.tif
- `TP_0037_dem`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0037/dsm_dem_flat_tile.tif
- `TP_0037_vegetation_base`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0037/dsm_vegetation_tile_base.tif
- `TP_0037_vegetation_overhead`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0037/dsm_vegetation_tile_overhead_as_canopy.tif
- `TP_0037_wall_height`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0037/wall_height.tif
- `TP_0037_wall_aspect`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0037/wall_aspect.tif
- `TP_0059_dsm_buildings`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0059/dsm_buildings_tile.tif
- `TP_0059_dem`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0059/dsm_dem_flat_tile.tif
- `TP_0059_vegetation_base`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0059/dsm_vegetation_tile_base.tif
- `TP_0059_vegetation_overhead`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0059/dsm_vegetation_tile_overhead_as_canopy.tif
- `TP_0059_wall_height`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0059/wall_height.tif
- `TP_0059_wall_aspect`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0059/wall_aspect.tif
- `TP_0088_dsm_buildings`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0088/dsm_buildings_tile.tif
- `TP_0088_dem`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0088/dsm_dem_flat_tile.tif
- `TP_0088_vegetation_base`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0088/dsm_vegetation_tile_base.tif
- `TP_0088_vegetation_overhead`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0088/dsm_vegetation_tile_overhead_as_canopy.tif
- `TP_0088_wall_height`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0088/wall_height.tif
- `TP_0088_wall_aspect`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0088/wall_aspect.tif
- `TP_0098_dsm_buildings`: Regenerate or locate the required raster input locally; do not copy or commit raster files: data/solweig/v12_n24_tiles/TP_0098/dsm_buildings_tile.tif
- `raster_tile`: 125 additional rows are listed in the missing-assets CSV.
- `svf_zip`: 48 required rows need manual confirmation.
- `TP_0037_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0037/svf_base/svfs.zip
- `TP_0037_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0037/svf_overhead_as_canopy/svfs.zip
- `TP_0059_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0059/svf_base/svfs.zip
- `TP_0059_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0059/svf_overhead_as_canopy/svfs.zip
- `TP_0088_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0088/svf_base/svfs.zip
- `TP_0088_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0088/svf_overhead_as_canopy/svfs.zip
- `TP_0098_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0098/svf_base/svfs.zip
- `TP_0098_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0098/svf_overhead_as_canopy/svfs.zip
- `TP_0115_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0115/svf_base/svfs.zip
- `TP_0115_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0115/svf_overhead_as_canopy/svfs.zip
- `TP_0141_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0141/svf_base/svfs.zip
- `TP_0141_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0141/svf_overhead_as_canopy/svfs.zip
- `TP_0154_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0154/svf_base/svfs.zip
- `TP_0154_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0154/svf_overhead_as_canopy/svfs.zip
- `TP_0254_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0254/svf_base/svfs.zip
- `TP_0254_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0254/svf_overhead_as_canopy/svfs.zip
- `TP_0301_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0301/svf_base/svfs.zip
- `TP_0301_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0301/svf_overhead_as_canopy/svfs.zip
- `TP_0326_svf_base`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0326/svf_base/svfs.zip
- `TP_0326_svf_overhead`: Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: data/solweig/v12_n24_tiles/TP_0326/svf_overhead_as_canopy/svfs.zip
- `svf_zip`: 28 additional rows are listed in the missing-assets CSV.

## Local Output Root

- Configured root: `C:/OpenHeat-local/solweig/b85_f1_tiles`
- Resolved root: `C:/OpenHeat-local/solweig/b85_f1_tiles`
- Inside Git worktree: `no`
- Exists now: `no`
- Human create/check status: `NEEDS_CREATE`

## Next Action

Manual QGIS execution can proceed only if the decision is `READY_FOR_MANUAL_QGIS`. If the decision is `PARTIAL_ASSETS_MISSING`, resolve the missing assets listed above and in `b85_f2_missing_assets.csv`, then rerun this readiness gate.
