# B8.5-F0 QGIS Execution README

Generated: 2026-05-26

## Status

B8.5-F0 is preflight only. QGIS was not run. SOLWEIG was not run. No raster files were created.

## Manifest

- Planned run matrix: `outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv`
- Planned rows: `480`
- Cells: `24`, from `original_retained_n24_cells`
- Forcing days: `FD01_high_shortwave_hot_20260507`, `FD02_humid_hot_cloudy_or_diffuse_20260508`
- Scenarios: `base`, `overhead_as_canopy`
- Hours: `10,12,13,15,16`

## Forcing-Day Interpretation

FD01 is the GE31-rich high-shortwave/hot forcing day. FD02 is a contrast day for humidity/cloud/diffuse/radiation diversity; GE31 observations are unavailable in the local paired station file for FD02, so it is not treated as GE31-rich.

## Later Execution Rules

1. Use `b85_f0_solweig_run_matrix.csv` as the controlling manifest.
2. Execute only the listed N24 cells, selected forcing days, five hours, and two scenarios.
3. Keep outputs grouped by `expected_output_group` so aggregation can trace every result back to one manifest row.
4. Do not expand this preflight into AOI-wide prediction.
5. Do not create local WBGT, `hazard_score`, `risk_score`, or System A/B coupling outputs.
6. Do not interpret SOLWEIG Tmrt as WBGT.

## Expected Completion Evidence

- A later run log with one status per `run_id`.
- Aggregated Tmrt summary CSV keyed by `run_id`.
- Delta / modifier target CSV computed within the forcing-day reference domain.
- Stability metrics CSV and Markdown report following `b85_f0_stability_metrics_protocol.md`.

This README is intentionally not an execution command. It is a handoff contract for a future approved QGIS/SOLWEIG lane.
