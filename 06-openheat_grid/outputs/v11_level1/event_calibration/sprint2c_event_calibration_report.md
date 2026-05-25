# System A Level 1 Sprint 2C - High-tail / Event Calibration Diagnostics

## Status
PASS

## Scope
- Level 1 only.
- Existing prediction scores only.
- No new regression model.
- No new model family.
- No formula-v2.
- No Level 2.
- No System B / SOLWEIG / v12.
- No local WBGT.

## Inputs
- `outputs/v11_level1/feature_ablation/oof_predictions_feature_ablation.csv`: used
- `outputs/v11_level1/blocked_time_high_tail/oof_predictions_blocked_time.csv`: used
- `outputs/v11_level1/blocked_time_high_tail/predictions_future_holdout.csv`: used

Context files:
- `outputs/v11_level1/feature_ablation/feature_ablation_report.md`: present
- `outputs/v11_level1/blocked_time_high_tail/sprint2b_blocked_time_high_tail_report.md`: present
- `outputs/v11_level1/blocked_time_high_tail/blocked_time_metrics.csv`: present
- `outputs/v11_level1/blocked_time_high_tail/future_holdout_metrics.csv`: present
- `outputs/v11_level1/blocked_time_high_tail/threshold_scan_metrics.csv`: present

Loaded manifest rows: 30 across 27 stations. Candidate models: M4_like_inertia_ridge, M7_like_compact_weather_ridge, L1_full_dynamic, L1_proxy_radiation, L1_proxy_only.

## Why Sprint 2C was needed
Sprint 2B showed severe high-tail underprediction, nominal fixed_33 threshold crossings were absent or ineffective for the Ridge scores, and ge31 best-F1 thresholds fell below the official 31 C event boundary. Sprint 2C therefore treats existing Ridge outputs as diagnostic scores and audits threshold behavior without creating a new WBGT value.

## Operating Point Results
Hourly_max ge31 LOSO reference:
| model | operating_point | achievable | score_threshold_c | precision | recall | F1 | false_alarm_ratio | miss_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | best_F1 | 1 | 29.500 | 0.481 | 0.798 | 0.600 | 0.519 | 0.202 |
| L1_full_dynamic | fixed_nominal | 1 | 31.000 | 0.749 | 0.297 | 0.425 | 0.251 | 0.703 |
| L1_full_dynamic | precision_70 | 1 | 30.900 | 0.722 | 0.344 | 0.466 | 0.278 | 0.656 |
| L1_full_dynamic | recall_90 | 1 | 28.800 | 0.426 | 0.902 | 0.579 | 0.574 | 0.098 |
| L1_proxy_only | best_F1 | 1 | 29.200 | 0.478 | 0.656 | 0.553 | 0.522 | 0.344 |
| L1_proxy_only | fixed_nominal | 1 | 31.000 | 0.864 | 0.043 | 0.081 | 0.136 | 0.957 |
| L1_proxy_only | precision_70 | 1 | 30.100 | 0.703 | 0.229 | 0.346 | 0.297 | 0.771 |
| L1_proxy_only | recall_90 | 1 | 28.400 | 0.356 | 0.908 | 0.511 | 0.644 | 0.092 |
| L1_proxy_radiation | best_F1 | 1 | 29.700 | 0.509 | 0.712 | 0.593 | 0.491 | 0.288 |
| L1_proxy_radiation | fixed_nominal | 1 | 31.000 | 0.630 | 0.277 | 0.385 | 0.370 | 0.723 |
| L1_proxy_radiation | precision_70 | 1 | 31.300 | 0.736 | 0.184 | 0.294 | 0.264 | 0.816 |
| L1_proxy_radiation | recall_90 | 1 | 28.400 | 0.381 | 0.910 | 0.537 | 0.619 | 0.090 |
| M4_like_inertia_ridge | best_F1 | 1 | 29.500 | 0.479 | 0.793 | 0.597 | 0.521 | 0.207 |
| M4_like_inertia_ridge | fixed_nominal | 1 | 31.000 | 0.763 | 0.302 | 0.433 | 0.237 | 0.698 |
| M4_like_inertia_ridge | precision_70 | 1 | 30.800 | 0.712 | 0.406 | 0.517 | 0.288 | 0.594 |
| M4_like_inertia_ridge | recall_90 | 1 | 28.700 | 0.400 | 0.906 | 0.555 | 0.600 | 0.094 |
| M7_like_compact_weather_ridge | best_F1 | 1 | 29.400 | 0.471 | 0.826 | 0.600 | 0.529 | 0.174 |
| M7_like_compact_weather_ridge | fixed_nominal | 1 | 31.000 | 0.788 | 0.270 | 0.402 | 0.212 | 0.730 |
| M7_like_compact_weather_ridge | precision_70 | 1 | 30.900 | 0.733 | 0.319 | 0.445 | 0.267 | 0.681 |
| M7_like_compact_weather_ridge | recall_90 | 1 | 28.900 | 0.427 | 0.905 | 0.580 | 0.573 | 0.095 |

Hourly_mean ge31 LOSO reference:
| model | operating_point | score_threshold_c | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | best_F1 | 29.900 | 0.387 | 0.587 | 0.467 |
| L1_full_dynamic | fixed_nominal | 31.000 | 0.652 | 0.096 | 0.168 |
| L1_proxy_only | best_F1 | 28.900 | 0.317 | 0.602 | 0.416 |
| L1_proxy_only | fixed_nominal | 31.000 | 1.000 | 0.002 | 0.003 |
| L1_proxy_radiation | best_F1 | 29.700 | 0.346 | 0.597 | 0.438 |
| L1_proxy_radiation | fixed_nominal | 31.000 | 0.603 | 0.075 | 0.134 |
| M4_like_inertia_ridge | best_F1 | 29.900 | 0.397 | 0.604 | 0.479 |
| M4_like_inertia_ridge | fixed_nominal | 31.000 | 0.693 | 0.098 | 0.172 |
| M7_like_compact_weather_ridge | best_F1 | 29.800 | 0.372 | 0.604 | 0.460 |
| M7_like_compact_weather_ridge | fixed_nominal | 31.000 | 0.672 | 0.072 | 0.130 |

Hourly_max ge33 remains exploratory:
| model | operating_point | score_threshold_c | official_positive_count | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | best_F1 | 31.500 | 119.000 | 0.161 | 0.261 | 0.199 |
| L1_full_dynamic | fixed_nominal | 33.000 | 119.000 | NA | 0.000 | 0.000 |
| L1_proxy_only | best_F1 | 30.400 | 119.000 | 0.132 | 0.244 | 0.171 |
| L1_proxy_only | fixed_nominal | 33.000 | 119.000 | NA | 0.000 | 0.000 |
| L1_proxy_radiation | best_F1 | 31.300 | 119.000 | 0.137 | 0.345 | 0.196 |
| L1_proxy_radiation | fixed_nominal | 33.000 | 119.000 | NA | 0.000 | 0.000 |
| M4_like_inertia_ridge | best_F1 | 31.400 | 119.000 | 0.150 | 0.277 | 0.195 |
| M4_like_inertia_ridge | fixed_nominal | 33.000 | 119.000 | NA | 0.000 | 0.000 |
| M7_like_compact_weather_ridge | best_F1 | 31.400 | 119.000 | 0.161 | 0.261 | 0.199 |
| M7_like_compact_weather_ridge | fixed_nominal | 33.000 | 119.000 | NA | 0.000 | 0.000 |

## Threshold Stability
| model | event_target | best_F1_threshold_LOSO | best_F1_threshold_blocked | best_F1_threshold_future | threshold_range | best_F1_range | stability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | ge31 | 29.500 | 30.200 | 30.200 | 0.700 | 0.151 | mixed |
| L1_proxy_only | ge31 | 29.200 | 29.100 | 29.400 | 0.300 | 0.059 | stable |
| L1_proxy_radiation | ge31 | 29.700 | 29.300 | 30.200 | 0.900 | 0.112 | unstable |
| M4_like_inertia_ridge | ge31 | 29.500 | 30.200 | 30.000 | 0.700 | 0.131 | mixed |
| M7_like_compact_weather_ridge | ge31 | 29.400 | 30.000 | 30.300 | 0.900 | 0.141 | unstable |

## Score-bin Event Rates
L1_full_dynamic: mostly monotonic; L1_proxy_only: mostly monotonic; L1_proxy_radiation: mostly monotonic; M4_like_inertia_ridge: mostly monotonic; M7_like_compact_weather_ridge: mostly monotonic.
These are empirical score calibration tables only, not a trained probability model.

## Advisory Mapping Candidates
The advisory table uses cautious language: candidate screening threshold and diagnostic advisory mapping. It is not a final official warning threshold.
| model | mapping_type | achievable | threshold | expected_precision | expected_recall | expected_F1 |
| --- | --- | --- | --- | --- | --- | --- |
| M4_like_inertia_ridge | high_recall_screening | 1 | 28.700 | 0.400 | 0.906 | 0.555 |
| M4_like_inertia_ridge | best_F1_screening | 1 | 29.500 | 0.479 | 0.793 | 0.597 |
| M4_like_inertia_ridge | high_precision_screening | 1 | 30.800 | 0.712 | 0.406 | 0.517 |
| M7_like_compact_weather_ridge | high_recall_screening | 1 | 28.900 | 0.427 | 0.905 | 0.580 |
| M7_like_compact_weather_ridge | best_F1_screening | 1 | 29.400 | 0.471 | 0.826 | 0.600 |
| M7_like_compact_weather_ridge | high_precision_screening | 1 | 30.900 | 0.733 | 0.319 | 0.445 |
| L1_full_dynamic | high_recall_screening | 1 | 28.800 | 0.426 | 0.902 | 0.579 |
| L1_full_dynamic | best_F1_screening | 1 | 29.500 | 0.481 | 0.798 | 0.600 |
| L1_full_dynamic | high_precision_screening | 1 | 30.900 | 0.722 | 0.344 | 0.466 |
| L1_proxy_radiation | high_recall_screening | 1 | 28.400 | 0.381 | 0.910 | 0.537 |
| L1_proxy_radiation | best_F1_screening | 1 | 29.700 | 0.509 | 0.712 | 0.593 |
| L1_proxy_radiation | high_precision_screening | 1 | 31.300 | 0.736 | 0.184 | 0.294 |
| L1_proxy_only | high_recall_screening | 1 | 28.400 | 0.356 | 0.908 | 0.511 |
| L1_proxy_only | best_F1_screening | 1 | 29.200 | 0.478 | 0.656 | 0.553 |
| L1_proxy_only | high_precision_screening | 1 | 30.100 | 0.703 | 0.229 | 0.346 |

## Expected Exceedance
Expected exceedance diagnostics were written for nominal 31 C, mapped ge31, and nominal 33 C score exceedance proxies. Because mapped thresholds are diagnostic score cutoffs, score exceedance should not be interpreted as official WBGT exceedance.
| model | score_excess_proxy | MAE_exceedance | bias_exceedance | correlation_exceedance | zero_excess_false_negative_count |
| --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | score_excess31_nominal | 0.094 | -0.078 | 0.386 | 775 |
| L1_full_dynamic | score_excess31_mapped | 0.175 | 0.102 | 0.504 | 214 |
| L1_full_dynamic | score_excess33_nominal | 0.004 | -0.004 | NA | 100 |
| L1_proxy_only | score_excess31_nominal | 0.099 | -0.098 | 0.148 | 1062 |
| L1_proxy_only | score_excess31_mapped | 0.122 | -0.002 | 0.424 | 375 |
| L1_proxy_only | score_excess33_nominal | 0.004 | -0.004 | NA | 100 |
| L1_proxy_radiation | score_excess31_nominal | 0.097 | -0.078 | 0.333 | 798 |
| L1_proxy_radiation | score_excess31_mapped | 0.152 | 0.059 | 0.466 | 307 |
| L1_proxy_radiation | score_excess33_nominal | 0.004 | -0.004 | NA | 100 |
| M4_like_inertia_ridge | score_excess31_nominal | 0.094 | -0.081 | 0.376 | 770 |
| M4_like_inertia_ridge | score_excess31_mapped | 0.174 | 0.100 | 0.505 | 220 |
| M4_like_inertia_ridge | score_excess33_nominal | 0.004 | -0.004 | NA | 100 |
| M7_like_compact_weather_ridge | score_excess31_nominal | 0.094 | -0.083 | 0.364 | 802 |
| M7_like_compact_weather_ridge | score_excess31_mapped | 0.182 | 0.111 | 0.499 | 187 |
| M7_like_compact_weather_ridge | score_excess33_nominal | 0.004 | -0.004 | NA | 100 |

## Station/regime Findings
Focus stations S142, S137, S135, and S139 are flagged in `event_calibration_by_station.csv` when present.
| model | station_id | event_count | fixed_nominal_recall | mapped_threshold_recall | residual_bias_high_tail_official_minus_score |
| --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | S135 | 69 | 0.275 | 0.681 | 2.049 |
| L1_full_dynamic | S137 | 77 | 0.169 | 0.701 | 2.492 |
| L1_full_dynamic | S139 | 8 | 0.250 | 0.875 | 0.841 |
| L1_full_dynamic | S142 | 84 | 0.167 | 0.762 | 2.642 |
| L1_proxy_only | S135 | 69 | 0.029 | 0.696 | 2.703 |
| L1_proxy_only | S137 | 77 | 0.000 | 0.597 | 3.211 |
| L1_proxy_only | S139 | 8 | 0.000 | 0.125 | 2.419 |
| L1_proxy_only | S142 | 84 | 0.000 | 0.548 | 3.531 |
| L1_proxy_radiation | S135 | 69 | 0.232 | 0.594 | 2.281 |
| L1_proxy_radiation | S137 | 77 | 0.156 | 0.662 | 2.540 |
| L1_proxy_radiation | S139 | 8 | 0.000 | 0.625 | 1.332 |
| L1_proxy_radiation | S142 | 84 | 0.167 | 0.643 | 2.807 |
| M4_like_inertia_ridge | S135 | 69 | 0.246 | 0.696 | 2.084 |
| M4_like_inertia_ridge | S137 | 77 | 0.195 | 0.714 | 2.481 |
| M4_like_inertia_ridge | S139 | 8 | 0.375 | 0.750 | 0.565 |
| M4_like_inertia_ridge | S142 | 84 | 0.167 | 0.738 | 2.625 |
Radiation-regime calibration was skipped because shortwave radiation was not present in the prediction output schema.

## Interpretation
1. Best ge31 event screening score under LOSO hourly_max: M7_like_compact_weather_ridge at threshold 29.400 with F1 0.600.
2. Best overall Level 1 WBGT_A regression under LOSO hourly_max MAE among selected scores: M4_like_inertia_ridge with MAE 0.937.
3. ge33 remains exploratory; the best LOSO hourly_max ge33 F1 among selected scores is 0.199 with event count 119.000.
4. Score compression remains present: ge31 best-F1 thresholds below 31 C were observed from 29.200 to 29.700.
5. Sprint 2C supports a diagnostic event score layer when thresholds are stable enough, but it is not enough to claim calibrated WBGT. Formula-v2/probability-calibration work remains a separate companion step.

## Caveats
- Event calibration is diagnostic, not an official warning system.
- Thresholds are derived from retrospective data.
- This is not a prospective forecast evaluation.
- Scores are not probability calibrated unless explicitly modeled.
- No formula-v2 was run.
- No local WBGT was produced.

## Next Recommended Action
- Build a formula-v2 proxy benchmark and a probability-calibration / P_ge31 companion before considering any high-tail-specific model family comparison.
- Prepare a Level 1 model card that separates regression WBGT_A behavior from diagnostic event-score mapping.

## Run Hygiene
- No forbidden files touched by the Sprint 2C script.
- No fallback used.
- No new model family added.
- No System B/v12 touched.
- No commit/stage performed.
