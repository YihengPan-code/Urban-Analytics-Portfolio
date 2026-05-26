# B3.3 Execution Completion Validation

Status: **PASS**

This validation read existing CSV outputs only. It did not rerun SOLWEIG, QGIS, qgis_process, N24 execution, aggregation, local WBGT, hazard_score, risk_score, surrogate training, or System A/B coupling.

## Summary

- base_vs_overhead_delta: PASS
- focus_tmrt_summary: PASS
- provisional_modifier: PASS
- run_log: PASS

## Schema Note

- Requested threshold delta names with `_tmrt_` are not present in the existing delta CSV.
- Equivalent threshold-area delta columns are present as `delta_pct_pixels_ge_40`, `delta_pct_pixels_ge_45`, `delta_pct_pixels_ge_50`, and `delta_pct_pixels_ge_55`.

## Checks

| Section | Check | Status | Observed | Expected | Note |
|---|---|---|---|---|---|
| run_log | rows | PASS | 240 | 240 |  |
| run_log | unique_run_id | PASS | 240 | 240 |  |
| run_log | status_counts | PASS | {'success': 239, 'skipped_completed': 1, 'failed_preprocess': 0, 'failed_solweig': 0, 'blocked': 0} | {'success': 239, 'skipped_completed': 1, 'failed_preprocess': 0, 'failed_solweig': 0, 'blocked': 0} | One skipped_completed row is expected because the first run completed before the loop fix. |
| run_log | cells | PASS | 24 | 24 |  |
| run_log | scenarios | PASS | base, overhead_as_canopy | base, overhead_as_canopy |  |
| run_log | hours | PASS | 10, 12, 13, 15, 16 | 10, 12, 13, 15, 16 |  |
| focus_tmrt_summary | rows | PASS | 240 | 240 |  |
| focus_tmrt_summary | unique_run_id | PASS | 240 | 240 |  |
| focus_tmrt_summary | cells | PASS | 24 | 24 |  |
| focus_tmrt_summary | scenarios | PASS | 2 | 2 |  |
| focus_tmrt_summary | hours | PASS | 5 | 5 |  |
| focus_tmrt_summary | n_pixels_min_max | PASS | (2500, 2500) | (2500, 2500) | Checked only because the n_pixels column exists. |
| focus_tmrt_summary | valid_pixel_count_min_max | PASS | (2500, 2500) | (2500, 2500) | Checked only because the valid_pixel_count column exists. |
| focus_tmrt_summary | required_metric_columns | PASS | present | all required columns |  |
| base_vs_overhead_delta | rows | PASS | 120 | 120 |  |
| base_vs_overhead_delta | cells | PASS | 24 | 24 |  |
| base_vs_overhead_delta | hours | PASS | 5 | 5 |  |
| base_vs_overhead_delta | paired_base_overhead_columns | PASS | present | all required columns |  |
| base_vs_overhead_delta | required_tmrt_delta_columns | PASS | present | all required columns |  |
| base_vs_overhead_delta | requested_threshold_delta_column_names | WARN | missing: delta_pct_pixels_tmrt_ge_40, delta_pct_pixels_tmrt_ge_45, delta_pct_pixels_tmrt_ge_50, delta_pct_pixels_tmrt_ge_55 | all requested column names | Current aggregation file uses delta_pct_pixels_ge_* names instead. |
| base_vs_overhead_delta | current_threshold_delta_columns | PASS | present | all required columns | These are the available threshold-area delta columns in the existing CSV. |
| provisional_modifier | file_exists | PASS | True | True | This file is provisional N24-internal reference only. |
| provisional_modifier | rows | PASS | 240 | 240 |  |
| provisional_modifier | boundary_note | PASS | N24-internal target robustness reference only | not final AOI-wide M_rad_pct, not hazard_score, not System A/B coupling | The validation script does not compute WBGT, hazard_score, risk_score, surrogates, or System A/B coupling. |
