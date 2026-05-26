# B8.5-F1 Execution Package README

Generated: 2026-05-26 23:14:38

## Status

This package prepares execution only. QGIS was not run. SOLWEIG was not run. No rasters were created or copied. No local WBGT, risk map, `hazard_score`, `risk_score`, AOI-wide prediction, or System A/B coupling output was created. This package does not approve B9 AOI-wide inference.

## Manifest

- Source manifest: `outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv`
- Planned rows: `480`
- Expected cells: `24`
- Expected forcing days: `2`
- Expected hours SGT: `10,12,13,15,16`
- Expected scenarios: `base`, `overhead_as_canopy`
- Required source flag: `solweig_execute_now=no`

## Package Artifacts

- Manifest validation: `outputs/v12_surrogate/b8_5_execution_package/b85_f1_manifest_validation.csv`
- Required asset inventory: `outputs/v12_surrogate/b8_5_execution_package/b85_f1_required_asset_inventory.csv`
- QGIS parameter contract: `outputs/v12_surrogate/b8_5_execution_package/b85_f1_qgis_parameter_contract.csv`
- Expected run-log schema: `outputs/v12_surrogate/b8_5_execution_package/b85_f1_expected_run_log_schema.csv`
- Expected aggregation contract: `outputs/v12_surrogate/b8_5_execution_package/b85_f1_expected_aggregation_contract.csv`
- QGIS skeleton: `scripts/qgis/v12_b85_qgis_solweig_execution_SKELETON.py`

## Asset Readiness

Asset readiness is `PARTIAL`. Missing or untracked raster/SVF paths do not fail this package; they are documented for human checking before QGIS execution. Met forcing files are inventoried for each `forcing_day_id x hour_sgt`.

## Local-Only Output Root

`C:/OpenHeat-local/solweig/b85_f1_tiles` is a local-only placeholder for future manual QGIS execution outside the Git worktree. It is not a blind execution command, and no raster or `svfs.zip` output from that path should be staged or committed.

## Human Execution Rule

The next step is human-reviewed QGIS execution using the skeleton and contracts in this package. Do not interpret SOLWEIG Tmrt as WBGT and do not create local WBGT, risk, `hazard_score`, `risk_score`, AOI-wide prediction, or System A/B coupling outputs in this lane.
