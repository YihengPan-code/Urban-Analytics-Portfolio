# Sprint B7.2 — N150 schema cleanup

## Status
PASS

## Scope
- Tiny schema cleanup only.
- No QGIS.
- No SOLWEIG rerun.
- No raw raster reads.
- No selected-cell or manifest changes.
- No local WBGT, hazard_score, risk_score, surrogate, or System A/B coupling.

## Purpose
Ensure B7/B8 downstream tables consistently expose both `hour_sgt` and `hour`, with identical values where both exist.

## Result
- Files checked: 7
- Files changed: 7
- Failed checks: 0
- Missing files: 0

## Validation table

| file                                                                      | exists   |   expected_rows |   observed_rows | had_hour   | had_hour_sgt   | changed   | status   | note                                 |
|:--------------------------------------------------------------------------|:---------|----------------:|----------------:|:-----------|:---------------|:----------|:---------|:-------------------------------------|
| outputs\v12_solweig_n150_execution\n150_new_solweig_run_log.csv           | True     |            1260 |            1260 | False      | True           | True      | PASS     | hour/hour_sgt present and consistent |
| outputs\v12_solweig_n150_execution\n150_new_focus_tmrt_summary.csv        | True     |            1260 |            1260 | False      | True           | True      | PASS     | hour/hour_sgt present and consistent |
| outputs\v12_solweig_n150_execution\n150_new_base_vs_overhead_delta.csv    | True     |             630 |             630 | False      | True           | True      | PASS     | hour/hour_sgt present and consistent |
| outputs\v12_solweig_n150_execution\n150_focus_tmrt_summary_merged.csv     | True     |            1500 |            1500 | True       | True           | True      | PASS     | hour/hour_sgt present and consistent |
| outputs\v12_solweig_n150_execution\n150_base_vs_overhead_delta_merged.csv | True     |             750 |             750 | True       | True           | True      | PASS     | hour/hour_sgt present and consistent |
| outputs\v12_solweig_n150_execution\n150_modifier_targets_b5.csv           | True     |            1500 |            1500 | True       | True           | True      | PASS     | hour/hour_sgt present and consistent |
| outputs\v12_solweig_n150_execution\n150_reference_values_b5.csv           | True     |              10 |              10 | False      | True           | True      | PASS     | hour/hour_sgt present and consistent |

## Downstream rule
B8 should prefer `hour_sgt` as the canonical hour field. The `hour` column is retained only as a compatibility alias.

Generated at: 2026-05-26T09:27:44