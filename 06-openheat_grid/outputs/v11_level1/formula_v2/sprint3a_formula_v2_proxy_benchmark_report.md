# System A Level 1 Sprint 3A - Formula-v2 Proxy Benchmark

## Status
PASS

## Scope
- Level 1 only.
- Proxy formula benchmark only.
- No new model family.
- No final formula replacement.
- No formula retroactive rewrite.
- No Level 2.
- No System B / SOLWEIG / v12.
- No local WBGT.

## Why Sprint 3A was needed
Sprint 2B found high-tail underprediction, and Sprint 2C found ge31 best-F1 score thresholds below 31 C plus ge33 nominal threshold failure. Therefore the v09 proxy scale and high-tail compression needed a direct formula/proxy audit.

## Existing formula audit discovery
Reused `scripts/v11_formula_audit_compare.py` for the Stull wet-bulb and simplified globe k-sweep lineage. Existing audit outputs under `outputs/v11_formula_audit/` were read only for discovery/context and were not overwritten.

## Input availability
- Input file: `data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv`
- Input mode: station-time input
- Rows: 40,419
- Columns: 495
- Stations: 27
- Station-hours written: 10,476

## Candidate Registry
Available raw candidates were `existing_v09_proxy`, `reconstructed_v09_proxy`, and the v09 k-sweep (`k0.0035`, `k0.0045`, `k0.0055`, `k0.0065`, `k0.0080`). Advanced physics candidates were feasibility-only because no validated in-repo implementation was found.

## Raw Formula Results
| candidate_id            | dataset_label | target_col          | score_col     | diagnostic_role | n     | MAE      | RMSE     | bias      | R2       | p50_abs_error | p90_abs_error | p95_abs_error |
| ----------------------- | ------------- | ------------------- | ------------- | --------------- | ----- | -------- | -------- | --------- | -------- | ------------- | ------------- | ------------- |
| k0.0080                 | hourly_max    | official_wbgt_c_max | candidate_max | main            | 10473 | 1.435070 | 1.968414 | -1.099365 | 0.279134 | 0.935543      | 3.584944      | 4.193439      |
| k0.0065                 | hourly_max    | official_wbgt_c_max | candidate_max | main            | 10473 | 1.452723 | 1.997205 | -1.125687 | 0.257892 | 0.937603      | 3.641062      | 4.264855      |
| k0.0055                 | hourly_max    | official_wbgt_c_max | candidate_max | main            | 10473 | 1.464705 | 2.016687 | -1.143229 | 0.243343 | 0.937831      | 3.686622      | 4.305218      |
| existing_v09_proxy      | hourly_max    | official_wbgt_c_max | candidate_max | main            | 10473 | 1.476785 | 2.036398 | -1.160767 | 0.228479 | 0.935863      | 3.727979      | 4.342323      |
| reconstructed_v09_proxy | hourly_max    | official_wbgt_c_max | candidate_max | main            | 10473 | 1.476785 | 2.036398 | -1.160767 | 0.228479 | 0.935863      | 3.727979      | 4.342323      |

Raw fixed_31/fixed_33 threshold behavior remains compressed. The best raw ge31 rows were:

| candidate_id            | dataset_label | target_col          | score_col     | diagnostic_role | event_target | official_event_threshold_c | fixed_score_threshold_c | n     | official_positive_count | predicted_positive_count | TP | FP | TN   | FN   | precision | recall   | F1 | best_F1_threshold | best_F1_precision | best_F1_recall | best_F1  | threshold_offset_ge31 | threshold_offset_ge33 |
| ----------------------- | ------------- | ------------------- | ------------- | --------------- | ------------ | -------------------------- | ----------------------- | ----- | ----------------------- | ------------------------ | -- | -- | ---- | ---- | --------- | -------- | -- | ----------------- | ----------------- | -------------- | -------- | --------------------- | --------------------- |
| k0.0080                 | hourly_max    | official_wbgt_c_max | candidate_max | main            | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 0                        | 0  | 0  | 9277 | 1196 |           | 0.000000 |    | 27.600000         | 0.495950          | 0.665552       | 0.568368 | -3.400000             |                       |
| k0.0065                 | hourly_max    | official_wbgt_c_max | candidate_max | main            | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 0                        | 0  | 0  | 9277 | 1196 |           | 0.000000 |    | 27.500000         | 0.481850          | 0.688127       | 0.566804 | -3.500000             |                       |
| existing_v09_proxy      | hourly_max    | official_wbgt_c_max | candidate_max | main            | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 0                        | 0  | 0  | 9277 | 1196 |           | 0.000000 |    | 27.400000         | 0.475970          | 0.687291       | 0.562436 | -3.600000             |                       |
| reconstructed_v09_proxy | hourly_max    | official_wbgt_c_max | candidate_max | main            | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 0                        | 0  | 0  | 9277 | 1196 |           | 0.000000 |    | 27.400000         | 0.475970          | 0.687291       | 0.562436 | -3.600000             |                       |
| k0.0045                 | hourly_max    | official_wbgt_c_max | candidate_max | main            | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 0                        | 0  | 0  | 9277 | 1196 |           | 0.000000 |    | 27.400000         | 0.475970          | 0.687291       | 0.562436 | -3.600000             |                       |
| k0.0055                 | hourly_max    | official_wbgt_c_max | candidate_max | main            | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 0                        | 0  | 0  | 9277 | 1196 |           | 0.000000 |    | 27.500000         | 0.490590          | 0.653846       | 0.560573 | -3.500000             |                       |
| k0.0035                 | hourly_max    | official_wbgt_c_max | candidate_max | main            | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 0                        | 0  | 0  | 9277 | 1196 |           | 0.000000 |    | 27.400000         | 0.480687          | 0.655518       | 0.554652 | -3.600000             |                       |

## Calibrated Formula Diagnostics
Train-only bias and affine diagnostics were run under LOSO and a final-date future block. These are one-score formula-calibration diagnostics, not final formula-v2 candidates.

| candidate_id            | dataset_label | target_col          | raw_score_col | validation_scheme | calibration_method | event_target | official_event_threshold_c | fixed_score_threshold_c | n     | official_positive_count | predicted_positive_count | TP | FP | TN   | FN   | precision | recall   | F1       | best_F1_threshold | best_F1_precision | best_F1_recall | best_F1  | threshold_offset_ge31 | threshold_offset_ge33 |
| ----------------------- | ------------- | ------------------- | ------------- | ----------------- | ------------------ | ------------ | -------------------------- | ----------------------- | ----- | ----------------------- | ------------------------ | -- | -- | ---- | ---- | --------- | -------- | -------- | ----------------- | ----------------- | -------------- | -------- | --------------------- | --------------------- |
| k0.0080                 | hourly_max    | official_wbgt_c_max | candidate_max | LOSO              | loso_affine        | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 106                      | 92 | 14 | 9263 | 1104 | 0.867925  | 0.076923 | 0.141321 | 29.200000         | 0.474044          | 0.694816       | 0.563581 | -1.800000             |                       |
| k0.0065                 | hourly_max    | official_wbgt_c_max | candidate_max | LOSO              | loso_affine        | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 95                       | 82 | 13 | 9264 | 1114 | 0.863158  | 0.068562 | 0.127033 | 29.200000         | 0.480213          | 0.679766       | 0.562825 | -1.800000             |                       |
| k0.0055                 | hourly_max    | official_wbgt_c_max | candidate_max | LOSO              | loso_affine        | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 86                       | 73 | 13 | 9264 | 1123 | 0.848837  | 0.061037 | 0.113885 | 29.200000         | 0.479665          | 0.670569       | 0.559275 | -1.800000             |                       |
| existing_v09_proxy      | hourly_max    | official_wbgt_c_max | candidate_max | LOSO              | loso_affine        | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 77                       | 65 | 12 | 9265 | 1131 | 0.844156  | 0.054348 | 0.102121 | 29.100000         | 0.460361          | 0.704013       | 0.556694 | -1.900000             |                       |
| k0.0045                 | hourly_max    | official_wbgt_c_max | candidate_max | LOSO              | loso_affine        | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 77                       | 65 | 12 | 9265 | 1131 | 0.844156  | 0.054348 | 0.102121 | 29.100000         | 0.460361          | 0.704013       | 0.556694 | -1.900000             |                       |
| reconstructed_v09_proxy | hourly_max    | official_wbgt_c_max | candidate_max | LOSO              | loso_affine        | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 77                       | 65 | 12 | 9265 | 1131 | 0.844156  | 0.054348 | 0.102121 | 29.100000         | 0.460361          | 0.704013       | 0.556694 | -1.900000             |                       |
| k0.0035                 | hourly_max    | official_wbgt_c_max | candidate_max | LOSO              | loso_affine        | ge31         | 31.000000                  | 31.000000               | 10473 | 1196                    | 73                       | 61 | 12 | 9265 | 1135 | 0.835616  | 0.051003 | 0.096139 | 29.100000         | 0.460167          | 0.690635       | 0.552324 | -1.900000             |                       |

## Formula vs Sprint 2C Event-score Comparison
| source_type                          | candidate_or_model            | fixed_31_recall | fixed_31_F1 | best_F1_threshold_ge31 | threshold_offset_ge31 | fixed_33_predicted_count | best_F1_ge33 | high_tail_bias |
| ------------------------------------ | ----------------------------- | --------------- | ----------- | ---------------------- | --------------------- | ------------------------ | ------------ | -------------- |
| best_raw_formula_candidate           | k0.0080                       | 0.000000        |             | 27.600000              | -3.400000             | 0.000000                 | 0.175342     | -4.022445      |
| best_simple_affine_formula_candidate | k0.0080                       | 0.076923        | 0.141321    | 29.200000              | -1.800000             | 0.000000                 | 0.170213     | -2.253449      |
| Sprint_2C_event_score                | M4_like_inertia_ridge         | 0.301839        | 0.432594    | 29.500000              | -1.500000             | 0.000000                 | 0.194690     | -1.525169      |
| Sprint_2C_event_score                | M7_like_compact_weather_ridge | 0.270067        | 0.402242    | 29.400000              | -1.600000             | 0.000000                 | 0.198718     | -1.544840      |
| Sprint_2C_event_score                | L1_full_dynamic               | 0.296823        | 0.425150    | 29.500000              | -1.500000             | 0.000000                 | 0.198718     | -1.508331      |

## Advanced Formula Feasibility
| candidate_id     | required_inputs                                                                                                 | available_in_current_snapshot                                                                                            | missing_inputs                                                                 | existing_validated_implementation_in_repo | external_package_available_in_environment | implementation_risk | recommendation                  |
| ---------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ----------------------------------------- | ----------------------------------------- | ------------------- | ------------------------------- |
| liljegren_style  | air temperature; humidity; wind; radiation; pressure; solar geometry; validated iterative implementation        | temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;surface_pressure;timestamp_sgt;latitude;longitude | validated in-repo implementation                                               | False                                     |                                           | high                | implement in separate Sprint 3B |
| kong_huber_style | published formula inputs; weather/radiation inputs; documented coefficients; validated implementation reference | temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;cloud_cover                                       | validated in-repo implementation;documented project-approved formula reference | False                                     |                                           | high                | blocked until inputs available  |
| brimicombe_style | published formula inputs; weather/radiation inputs; documented coefficients; validated implementation reference | temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;cloud_cover                                       | validated in-repo implementation;documented project-approved formula reference | False                                     |                                           | high                | blocked until inputs available  |

## Interpretation
1. The current v09 proxy is a major high-tail bottleneck on the raw score scale: station-hour maxima remain below fixed WBGT event thresholds for the raw k-sweep.
2. No simple raw formula candidate materially removes high-tail compression.
3. The k-sweep helps only marginally; larger k values nudge the upper tail but do not restore fixed_31/fixed_33 crossings.
4. Simple affine calibration reduces scale offset as a diagnostic layer, but it is not enough to promote a replacement formula without follow-up validation and model-card work.
5. Next recommended action: P_ge31 probability calibration companion, while treating advanced physics implementation as a separate Sprint 3B validation track if the project wants a formula replacement route.

## Caveats
- Formula candidates are proxies, not observed WBGT.
- Calibrated formula diagnostics are not final forecast models.
- Future-block is retrospective-like, not true prospective.
- No formula candidate is promoted without model card and follow-up validation.

## Next Recommended Action
P_ge31 probability calibration companion.

## Run Guardrails
- No forbidden files touched.
- No fallback solver used.
- No new model family added.
- No System B/v12 touched.
- No commit/stage performed.
- `formula_candidate_hourly_predictions.csv` is a generated row-level diagnostic and should be treated as do-not-commit unless explicitly reviewed.
