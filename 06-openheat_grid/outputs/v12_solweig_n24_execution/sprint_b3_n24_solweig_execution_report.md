# Sprint B3 — Full N24 SOLWEIG Execution Report

## Status

PASS

## Scope

- Full N24 SOLWEIG execution completed.
- System B SOLWEIG-derived Tmrt execution only.
- Local raw rasters are allowed as local execution outputs but are not committed.
- No System A/B coupling.
- No local WBGT.
- No hazard_score.
- No risk_score.
- No surrogate.

## B2.2 frozen input

The N24 selected cells were frozen after B2.2 human QA. Five replacements were applied before the B3 execution matrix was frozen:

- TP_0058 -> TP_0141
- TP_0828 -> TP_0301
- TP_0802 -> TP_0773
- TP_0675 -> TP_0676
- TP_0916 -> TP_0575

Frozen selected cells: 24.

Run matrix rows: 240.

Reference files:

- `outputs/v12_systemb_n24_sample_design/sprint_b2_2_n24_human_qa_freeze_report.md`
- `outputs/v12_systemb_n24_sample_design/n24_selected_cells_b2_2_human_qa_freeze.csv`
- `configs/v12/v12_solweig_n24_run_matrix.csv`

## Execution environment

Execution method: QGIS Desktop Python Console.

Direct `qgis_process` execution was blocked or unstable for this sprint and was not used for the completed N24 execution.

Resolved QGIS/SOLWEIG algorithm:

- Algorithm id: `umep:Outdoor Thermal Comfort: SOLWEIG`
- Display name: `Outdoor Thermal Comfort: SOLWEIG v2025a`

Preprocess algorithm resolution was also available:

- Wall Height and Aspect: `umep:Urban Geometry: Wall Height and Aspect`
- Sky View Factor: `umep:Urban Geometry: Sky View Factor`

Reference files:

- `outputs/v12_solweig_n24_execution/qgis_algorithm_resolution.md`
- `outputs/v12_solweig_n24_execution/qgis_preprocess_algorithm_resolution.md`

## Effective SOLWEIG parameters

Effective parameters recorded for the completed N24 execution:

- `INPUTMET_key`: `INPUTMET`
- `LEAF_START`: `1`
- `LEAF_END`: `366`
- `UTC`: `8`
- `TRANS_VEG`: `3`
- `INPUT_THEIGHT`: `25.0`
- `OUTPUT_TMRT`: `True`
- Scenario design: paired `base` vs `overhead_as_canopy` comparison; not absolute truth.
- Tmrt output filename note: SOLWEIG may write `Tmrt_average.tif`; the hour is parsed from the parent folder `solweig_outputs_hHH`.

Reference file:

- `outputs/v12_solweig_n24_execution/n24_effective_solweig_parameters.md`

## Run summary

- Expected main runs: 240
- Attempted after loop fix: 239
- Success: 239
- Skipped completed: 1
- Failed preprocess: 0
- Failed SOLWEIG: 0
- Blocked: 0
- Completed: 240 / 240

The single `skipped_completed` run was expected. The first run, `v12_n24_base_TP_0059_h10`, had already succeeded during the previous loop attempt, so the fixed QGIS Desktop Python Console runner skipped it and completed the remaining 239 runs.

Reference file:

- `outputs/v12_solweig_n24_execution/n24_solweig_run_log.csv`

## Aggregation summary

- `n24_focus_tmrt_summary.csv` rows: 240
- `n24_base_vs_overhead_delta.csv` rows: 120
- `n24_modifier_targets_provisional.csv`: present
- Focus-cell `n_pixels` min/max: 2500 / 2500
- Focus-cell `valid_pixel_count` min/max: 2500 / 2500
- Threshold-area metric columns are available in the focus summary:
  - `pct_pixels_tmrt_ge_40`
  - `pct_pixels_tmrt_ge_45`
  - `pct_pixels_tmrt_ge_50`
  - `pct_pixels_tmrt_ge_55`
- Base-vs-overhead threshold-area delta columns are available in the current aggregation as:
  - `delta_pct_pixels_ge_40`
  - `delta_pct_pixels_ge_45`
  - `delta_pct_pixels_ge_50`
  - `delta_pct_pixels_ge_55`

Reference files:

- `outputs/v12_solweig_n24_execution/n24_focus_tmrt_summary.csv`
- `outputs/v12_solweig_n24_execution/n24_base_vs_overhead_delta.csv`
- `outputs/v12_solweig_n24_execution/n24_modifier_targets_provisional.csv`
- `outputs/v12_solweig_n24_execution/b3_3_execution_completion_validation.csv`
- `outputs/v12_solweig_n24_execution/b3_3_execution_completion_validation.md`

## Preliminary sanity observations

These are light execution-completion observations only, not the B4 target robustness audit.

- TP_0565 and TP_0986 remain present as hot-anchor continuity cells in the completed focus summary.
- TP_0433 remains present as a shaded-reference continuity cell in the completed focus summary.
- TP_0141 successfully replaced near-pure-river TP_0058 and produced valid Tmrt rows.
- No failed runs were recorded.

Detailed p90, p75, p95, max, threshold-area, hour-stability, and target-robustness analysis is reserved for Sprint B4.

## Provisional modifier note

`n24_modifier_targets_provisional.csv` is for N24-internal target robustness analysis only.

It is not final AOI-wide `M_rad_pct`.

It is not `hazard_score`.

It is not System A/B coupling.

## Outputs

- Raw local output root: `data/solweig/v12_n24_tiles/`
- `outputs/v12_solweig_n24_execution/n24_solweig_run_log.csv`
- `outputs/v12_solweig_n24_execution/n24_focus_tmrt_summary.csv`
- `outputs/v12_solweig_n24_execution/n24_base_vs_overhead_delta.csv`
- `outputs/v12_solweig_n24_execution/n24_modifier_targets_provisional.csv`
- `outputs/v12_solweig_n24_execution/n24_effective_solweig_parameters.md`
- `outputs/v12_solweig_n24_execution/qgis_algorithm_resolution.md`

## Git safety

- Raw rasters and SOLWEIG outputs under `data/solweig/v12_n24_tiles/` are local-only.
- Do not stage or commit `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG outputs, `data/solweig`, or `data/rasters`.
- This report does not imply raw outputs are git-safe.

## What this proves

- The N24 SOLWEIG execution pipeline works in QGIS Desktop Python Console.
- The frozen N24 sample has complete Tmrt outputs for `base` and `overhead_as_canopy` scenarios.
- N24 summaries are ready for target robustness re-audit.

## What this does not prove

- No local WBGT.
- No risk.
- No final hazard map.
- No surrogate validation.
- No observed truth.
- No System A/B coupling.

## Next recommended action

Sprint B4 — N24 target robustness re-audit using actual N24 SOLWEIG summaries:

- p90 vs p75 / p95 / max
- p90 vs threshold-area metrics
- base vs overhead sensitivity
- hour stability
- typology / replacement-cell sanity
- whether p90 remains provisional primary or can be strengthened
