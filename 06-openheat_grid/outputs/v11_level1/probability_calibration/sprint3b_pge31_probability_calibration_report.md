# System A Level 1 Sprint 3B - P_ge31 Probability Calibration Companion

## Status
PASS

## Scope
- Level 1 only.
- Existing score probability calibration only.
- No new WBGT regression model.
- No model-family comparison.
- No formula-v2.
- No Level 2.
- No System B / SOLWEIG / v12.
- No local WBGT.

## Why Sprint 3B was needed
Sprint 2B found high-tail underprediction, Sprint 2C found score compression and unstable diagnostic thresholds, and Sprint 3A found simple formula candidates could not restore fixed_31/fixed_33 crossings. A held-out P_ge31 probability companion is therefore the next diagnostic layer.

## Inputs
| prediction_source   | dataset_label   | model                         | event_target   |   n_rows |   station_count |   event_count |   event_rate |   fallback_used_any |
|:--------------------|:----------------|:------------------------------|:---------------|---------:|----------------:|--------------:|-------------:|--------------------:|
| loso_oof            | hourly_max      | L1_full_dynamic               | ge31           |    10473 |              27 |          1196 |        0.114 |                   0 |
| loso_oof            | hourly_max      | L1_full_dynamic               | ge33           |    10473 |              27 |           119 |        0.011 |                   0 |
| loso_oof            | hourly_max      | L1_proxy_only                 | ge31           |    10473 |              27 |          1196 |        0.114 |                   0 |
| loso_oof            | hourly_max      | L1_proxy_only                 | ge33           |    10473 |              27 |           119 |        0.011 |                   0 |
| loso_oof            | hourly_max      | L1_proxy_radiation            | ge31           |    10473 |              27 |          1196 |        0.114 |                   0 |
| loso_oof            | hourly_max      | L1_proxy_radiation            | ge33           |    10473 |              27 |           119 |        0.011 |                   0 |
| loso_oof            | hourly_max      | M4_like_inertia_ridge         | ge31           |    10473 |              27 |          1196 |        0.114 |                   0 |
| loso_oof            | hourly_max      | M4_like_inertia_ridge         | ge33           |    10473 |              27 |           119 |        0.011 |                   0 |
| loso_oof            | hourly_max      | M7_like_compact_weather_ridge | ge31           |    10473 |              27 |          1196 |        0.114 |                   0 |
| loso_oof            | hourly_max      | M7_like_compact_weather_ridge | ge33           |    10473 |              27 |           119 |        0.011 |                   0 |
| loso_oof            | hourly_mean     | L1_full_dynamic               | ge31           |    10473 |              27 |           623 |        0.059 |                   0 |
| loso_oof            | hourly_mean     | L1_full_dynamic               | ge33           |    10473 |              27 |            30 |        0.003 |                   0 |
| loso_oof            | hourly_mean     | L1_proxy_only                 | ge31           |    10473 |              27 |           623 |        0.059 |                   0 |
| loso_oof            | hourly_mean     | L1_proxy_only                 | ge33           |    10473 |              27 |            30 |        0.003 |                   0 |
| loso_oof            | hourly_mean     | L1_proxy_radiation            | ge31           |    10473 |              27 |           623 |        0.059 |                   0 |
| loso_oof            | hourly_mean     | L1_proxy_radiation            | ge33           |    10473 |              27 |            30 |        0.003 |                   0 |
| loso_oof            | hourly_mean     | M4_like_inertia_ridge         | ge31           |    10473 |              27 |           623 |        0.059 |                   0 |
| loso_oof            | hourly_mean     | M4_like_inertia_ridge         | ge33           |    10473 |              27 |            30 |        0.003 |                   0 |
| loso_oof            | hourly_mean     | M7_like_compact_weather_ridge | ge31           |    10473 |              27 |           623 |        0.059 |                   0 |
| loso_oof            | hourly_mean     | M7_like_compact_weather_ridge | ge33           |    10473 |              27 |            30 |        0.003 |                   0 |

## Reliability before fitting
Fixed and quantile reliability bins were written before any calibrator fitting. Monotonicity is empirical event-rate monotonicity versus mean score.
| model                         | bin_kind   |   n_bins |   n_low_support_bins | monotonicity     |   event_rate_min |   event_rate_max |
|:------------------------------|:-----------|---------:|---------------------:|:-----------------|-----------------:|-----------------:|
| L1_full_dynamic               | fixed      |       12 |                    1 | mostly_monotonic |            0     |            0.881 |
| L1_full_dynamic               | quantile   |       10 |                    0 | monotonic        |            0     |            0.619 |
| L1_proxy_only                 | fixed      |       10 |                    1 | mostly_monotonic |            0.015 |            0.872 |
| L1_proxy_only                 | quantile   |       10 |                    0 | mostly_monotonic |            0     |            0.551 |
| L1_proxy_radiation            | fixed      |       12 |                    1 | mostly_monotonic |            0     |            0.848 |
| L1_proxy_radiation            | quantile   |       10 |                    0 | mostly_monotonic |            0     |            0.567 |
| M4_like_inertia_ridge         | fixed      |       11 |                    1 | mostly_monotonic |            0.023 |            0.88  |
| M4_like_inertia_ridge         | quantile   |       10 |                    0 | monotonic        |            0     |            0.633 |
| M7_like_compact_weather_ridge | fixed      |       11 |                    1 | mostly_monotonic |            0.007 |            0.848 |
| M7_like_compact_weather_ridge | quantile   |       10 |                    0 | monotonic        |            0     |            0.606 |

## Calibration design
- `blocked_date_calibration`: contiguous date blocks; train calibrator on other date blocks, test held-out date block.
- `future_block_calibration`: train before the final date block, test final date block; retrospective, not prospective forecast skill.
- `station_grouped_calibration`: train on other stations, test held-out station.
- Thresholds were selected on training folds only; no test-set oracle thresholds are used as main results.

## Probability calibration results
Hourly_max ge31 primary candidates:
| model                         | calibrator                 | validation_scheme           |   Brier |   log_loss |   ECE_10 |   average_precision |   ROC_AUC |   probability_bias |   best_F1_train_selected_F1 |
|:------------------------------|:---------------------------|:----------------------------|--------:|-----------:|---------:|--------------------:|----------:|-------------------:|----------------------------:|
| M7_like_compact_weather_ridge | isotonic_score_calibration | station_grouped_calibration |   0.061 |      0.189 |    0.008 |               0.603 |     0.931 |              0     |                       0.578 |
| M4_like_inertia_ridge         | isotonic_score_calibration | station_grouped_calibration |   0.061 |      0.192 |    0.015 |               0.598 |     0.928 |              0     |                       0.563 |
| L1_full_dynamic               | isotonic_score_calibration | station_grouped_calibration |   0.062 |      0.191 |    0.011 |               0.61  |     0.933 |              0     |                       0.576 |
| M4_like_inertia_ridge         | empirical_bin_calibration  | station_grouped_calibration |   0.063 |      0.195 |    0.01  |               0.479 |     0.918 |              0     |                       0.576 |
| M4_like_inertia_ridge         | logistic_score_calibration | station_grouped_calibration |   0.062 |      0.196 |    0.013 |               0.624 |     0.934 |              0     |                       0.567 |
| M4_like_inertia_ridge         | logistic_score_calibration | blocked_date_calibration    |   0.064 |      0.201 |    0.013 |               0.601 |     0.931 |             -0.001 |                       0.559 |
| L1_full_dynamic               | logistic_score_calibration | station_grouped_calibration |   0.062 |      0.194 |    0.016 |               0.625 |     0.936 |              0     |                       0.576 |
| L1_full_dynamic               | empirical_bin_calibration  | station_grouped_calibration |   0.064 |      0.195 |    0     |               0.471 |     0.918 |              0     |                       0.597 |
| M7_like_compact_weather_ridge | logistic_score_calibration | blocked_date_calibration    |   0.064 |      0.2   |    0.015 |               0.594 |     0.931 |             -0.001 |                       0.558 |
| M7_like_compact_weather_ridge | logistic_score_calibration | station_grouped_calibration |   0.062 |      0.193 |    0.016 |               0.623 |     0.936 |              0     |                       0.576 |
| L1_full_dynamic               | logistic_score_calibration | blocked_date_calibration    |   0.064 |      0.199 |    0.016 |               0.601 |     0.932 |             -0.001 |                       0.562 |
| M4_like_inertia_ridge         | isotonic_score_calibration | blocked_date_calibration    |   0.064 |      0.202 |    0.018 |               0.576 |     0.927 |             -0.002 |                       0.559 |
| M7_like_compact_weather_ridge | isotonic_score_calibration | blocked_date_calibration    |   0.064 |      0.2   |    0.021 |               0.588 |     0.928 |             -0.001 |                       0.557 |
| M7_like_compact_weather_ridge | empirical_bin_calibration  | station_grouped_calibration |   0.064 |      0.197 |    0.007 |               0.468 |     0.917 |             -0     |                       0.6   |
| L1_proxy_only                 | isotonic_score_calibration | station_grouped_calibration |   0.068 |      0.219 |    0.005 |               0.537 |     0.905 |              0     |                       0.545 |

High-recall P_ge31 screen candidates:
| model                         | calibrator                          | validation_scheme        |   mean_selected_probability_threshold |   precision |   recall |    F1 |   false_alarm_ratio |   miss_rate |
|:------------------------------|:------------------------------------|:-------------------------|--------------------------------------:|------------:|---------:|------:|--------------------:|------------:|
| M7_like_compact_weather_ridge | logistic_score_calibration          | future_block_calibration |                                  0.12 |       0.418 |    0.988 | 0.588 |               0.582 |       0.012 |
| M7_like_compact_weather_ridge | isotonic_score_calibration          | future_block_calibration |                                  0.21 |       0.417 |    0.988 | 0.586 |               0.583 |       0.012 |
| M7_like_compact_weather_ridge | logistic_score_calibration_balanced | future_block_calibration |                                  0.51 |       0.417 |    0.988 | 0.586 |               0.583 |       0.012 |
| M4_like_inertia_ridge         | isotonic_score_calibration          | future_block_calibration |                                  0.14 |       0.376 |    0.988 | 0.545 |               0.624 |       0.012 |
| M7_like_compact_weather_ridge | empirical_bin_calibration           | future_block_calibration |                                  0.15 |       0.345 |    0.988 | 0.511 |               0.655 |       0.012 |
| L1_full_dynamic               | empirical_bin_calibration           | future_block_calibration |                                  0.16 |       0.344 |    0.988 | 0.511 |               0.656 |       0.012 |
| L1_proxy_radiation            | empirical_bin_calibration           | future_block_calibration |                                  0.15 |       0.338 |    0.988 | 0.504 |               0.662 |       0.012 |
| M4_like_inertia_ridge         | empirical_bin_calibration           | future_block_calibration |                                  0.14 |       0.335 |    0.988 | 0.5   |               0.665 |       0.012 |
| M4_like_inertia_ridge         | logistic_score_calibration_balanced | future_block_calibration |                                  0.45 |       0.388 |    0.984 | 0.556 |               0.612 |       0.016 |
| M4_like_inertia_ridge         | logistic_score_calibration          | future_block_calibration |                                  0.09 |       0.385 |    0.984 | 0.553 |               0.615 |       0.016 |

High-precision P_ge31 screen candidates:
| model                         | calibrator                          | validation_scheme           |   mean_selected_probability_threshold |   precision |   recall |    F1 |   false_alarm_ratio |   miss_rate |
|:------------------------------|:------------------------------------|:----------------------------|--------------------------------------:|------------:|---------:|------:|--------------------:|------------:|
| L1_proxy_radiation            | logistic_score_calibration_balanced | future_block_calibration    |                                 0.97  |       0.8   |    0.099 | 0.176 |               0.2   |       0.901 |
| L1_proxy_radiation            | isotonic_score_calibration          | future_block_calibration    |                                 0.49  |       0.782 |    0.177 | 0.289 |               0.218 |       0.823 |
| L1_proxy_radiation            | logistic_score_calibration          | future_block_calibration    |                                 0.67  |       0.77  |    0.193 | 0.309 |               0.23  |       0.807 |
| L1_proxy_only                 | isotonic_score_calibration          | station_grouped_calibration |                                 0.553 |       0.764 |    0.2   | 0.317 |               0.236 |       0.8   |
| M7_like_compact_weather_ridge | logistic_score_calibration_balanced | future_block_calibration    |                                 0.95  |       0.762 |    0.473 | 0.584 |               0.238 |       0.527 |
| L1_proxy_only                 | isotonic_score_calibration          | blocked_date_calibration    |                                 0.574 |       0.757 |    0.175 | 0.284 |               0.243 |       0.825 |
| M7_like_compact_weather_ridge | logistic_score_calibration_balanced | station_grouped_calibration |                                 0.94  |       0.744 |    0.313 | 0.44  |               0.256 |       0.687 |
| L1_proxy_radiation            | logistic_score_calibration_balanced | station_grouped_calibration |                                 0.96  |       0.728 |    0.184 | 0.294 |               0.272 |       0.816 |
| M7_like_compact_weather_ridge | logistic_score_calibration          | future_block_calibration    |                                 0.61  |       0.718 |    0.514 | 0.6   |               0.282 |       0.486 |
| M7_like_compact_weather_ridge | isotonic_score_calibration          | station_grouped_calibration |                                 0.479 |       0.717 |    0.331 | 0.453 |               0.283 |       0.669 |

ge33 remains exploratory unless event counts and fold stability support stronger claims:
| dataset_label   | model                         | calibrator                 | validation_scheme        |   event_count |   Brier |   ECE_10 |   average_precision |   best_F1_train_selected_F1 |
|:----------------|:------------------------------|:---------------------------|:-------------------------|--------------:|--------:|---------:|--------------------:|----------------------------:|
| hourly_max      | L1_proxy_radiation            | logistic_score_calibration | future_block_calibration |            18 |   0.009 |    0.005 |               0.055 |                       0.059 |
| hourly_max      | L1_proxy_radiation            | empirical_bin_calibration  | future_block_calibration |            18 |   0.009 |    0.006 |               0.053 |                       0.107 |
| hourly_max      | L1_proxy_radiation            | isotonic_score_calibration | future_block_calibration |            18 |   0.01  |    0.005 |               0.055 |                       0.062 |
| hourly_max      | M7_like_compact_weather_ridge | empirical_bin_calibration  | future_block_calibration |            18 |   0.009 |    0.007 |               0.058 |                       0.11  |
| hourly_max      | L1_full_dynamic               | isotonic_score_calibration | future_block_calibration |            18 |   0.01  |    0.007 |               0.06  |                       0.036 |
| hourly_max      | L1_full_dynamic               | logistic_score_calibration | future_block_calibration |            18 |   0.01  |    0.008 |               0.06  |                       0.037 |
| hourly_max      | L1_proxy_only                 | empirical_bin_calibration  | future_block_calibration |            18 |   0.009 |    0.006 |               0.046 |                       0.094 |
| hourly_max      | M4_like_inertia_ridge         | isotonic_score_calibration | future_block_calibration |            18 |   0.01  |    0.007 |               0.05  |                       0.03  |
| hourly_max      | M4_like_inertia_ridge         | logistic_score_calibration | future_block_calibration |            18 |   0.01  |    0.008 |               0.054 |                       0.03  |
| hourly_max      | L1_full_dynamic               | empirical_bin_calibration  | future_block_calibration |            18 |   0.009 |    0.008 |               0.053 |                       0.101 |
| hourly_max      | M4_like_inertia_ridge         | empirical_bin_calibration  | future_block_calibration |            18 |   0.009 |    0.009 |               0.052 |                       0.1   |
| hourly_max      | M7_like_compact_weather_ridge | logistic_score_calibration | future_block_calibration |            18 |   0.01  |    0.009 |               0.066 |                       0.105 |

## Comparison vs Sprint 2C event-score mapping
| comparison_family                 | model                         | method                              | validation_scheme           | operating_point   |   threshold | Brier   |    F1 |   precision |   recall |   false_alarm_ratio |   miss_rate |
|:----------------------------------|:------------------------------|:------------------------------------|:----------------------------|:------------------|------------:|:--------|------:|------------:|---------:|--------------------:|------------:|
| Sprint_2C_event_score_mapping     | L1_full_dynamic               | high_recall_screening               | nan                         | recall_90         |      28.8   | NA      | 0.579 |       0.426 |    0.902 |               0.574 |       0.098 |
| Sprint_2C_event_score_mapping     | L1_full_dynamic               | best_F1_screening                   | nan                         | best_F1           |      29.5   | NA      | 0.6   |       0.481 |    0.798 |               0.519 |       0.202 |
| Sprint_2C_event_score_mapping     | L1_full_dynamic               | high_precision_screening            | nan                         | precision_70      |      30.9   | NA      | 0.466 |       0.722 |    0.344 |               0.278 |       0.656 |
| Sprint_2C_event_score_mapping     | L1_proxy_only                 | high_recall_screening               | nan                         | recall_90         |      28.4   | NA      | 0.511 |       0.356 |    0.908 |               0.644 |       0.092 |
| Sprint_2C_event_score_mapping     | L1_proxy_only                 | best_F1_screening                   | nan                         | best_F1           |      29.2   | NA      | 0.553 |       0.478 |    0.656 |               0.522 |       0.344 |
| Sprint_2C_event_score_mapping     | L1_proxy_only                 | high_precision_screening            | nan                         | precision_70      |      30.1   | NA      | 0.346 |       0.703 |    0.229 |               0.297 |       0.771 |
| Sprint_2C_event_score_mapping     | L1_proxy_radiation            | high_recall_screening               | nan                         | recall_90         |      28.4   | NA      | 0.537 |       0.381 |    0.91  |               0.619 |       0.09  |
| Sprint_2C_event_score_mapping     | L1_proxy_radiation            | best_F1_screening                   | nan                         | best_F1           |      29.7   | NA      | 0.593 |       0.509 |    0.712 |               0.491 |       0.288 |
| Sprint_2C_event_score_mapping     | L1_proxy_radiation            | high_precision_screening            | nan                         | precision_70      |      31.3   | NA      | 0.294 |       0.736 |    0.184 |               0.264 |       0.816 |
| Sprint_2C_event_score_mapping     | M4_like_inertia_ridge         | high_recall_screening               | nan                         | recall_90         |      28.7   | NA      | 0.555 |       0.4   |    0.906 |               0.6   |       0.094 |
| Sprint_2C_event_score_mapping     | M4_like_inertia_ridge         | best_F1_screening                   | nan                         | best_F1           |      29.5   | NA      | 0.597 |       0.479 |    0.793 |               0.521 |       0.207 |
| Sprint_2C_event_score_mapping     | M4_like_inertia_ridge         | high_precision_screening            | nan                         | precision_70      |      30.8   | NA      | 0.517 |       0.712 |    0.406 |               0.288 |       0.594 |
| Sprint_2C_event_score_mapping     | M7_like_compact_weather_ridge | high_recall_screening               | nan                         | recall_90         |      28.9   | NA      | 0.58  |       0.427 |    0.905 |               0.573 |       0.095 |
| Sprint_2C_event_score_mapping     | M7_like_compact_weather_ridge | best_F1_screening                   | nan                         | best_F1           |      29.4   | NA      | 0.6   |       0.471 |    0.826 |               0.529 |       0.174 |
| Sprint_2C_event_score_mapping     | M7_like_compact_weather_ridge | high_precision_screening            | nan                         | precision_70      |      30.9   | NA      | 0.445 |       0.733 |    0.319 |               0.267 |       0.681 |
| Sprint_3B_probability_calibration | L1_full_dynamic               | logistic_score_calibration          | blocked_date_calibration    | best_F1_train     |       0.312 | 0.064   | 0.562 |       0.496 |    0.649 |               0.504 |       0.351 |
| Sprint_3B_probability_calibration | L1_full_dynamic               | logistic_score_calibration_balanced | blocked_date_calibration    | best_F1_train     |       0.784 | 0.108   | 0.562 |       0.496 |    0.648 |               0.504 |       0.352 |
| Sprint_3B_probability_calibration | L1_full_dynamic               | isotonic_score_calibration          | blocked_date_calibration    | best_F1_train     |       0.286 | 0.065   | 0.562 |       0.497 |    0.647 |               0.503 |       0.353 |
| Sprint_3B_probability_calibration | L1_full_dynamic               | empirical_bin_calibration           | blocked_date_calibration    | best_F1_train     |       0.204 | 0.067   | 0.583 |       0.477 |    0.751 |               0.523 |       0.249 |
| Sprint_3B_probability_calibration | L1_full_dynamic               | logistic_score_calibration          | future_block_calibration    | best_F1_train     |       0.23  | 0.061   | 0.651 |       0.502 |    0.926 |               0.498 |       0.074 |
| Sprint_3B_probability_calibration | L1_full_dynamic               | logistic_score_calibration_balanced | future_block_calibration    | best_F1_train     |       0.72  | 0.135   | 0.652 |       0.502 |    0.93  |               0.498 |       0.07  |
| Sprint_3B_probability_calibration | L1_full_dynamic               | isotonic_score_calibration          | future_block_calibration    | best_F1_train     |       0.27  | 0.064   | 0.651 |       0.503 |    0.922 |               0.497 |       0.078 |
| Sprint_3B_probability_calibration | L1_full_dynamic               | empirical_bin_calibration           | future_block_calibration    | best_F1_train     |       0.17  | 0.066   | 0.625 |       0.466 |    0.951 |               0.534 |       0.049 |
| Sprint_3B_probability_calibration | L1_full_dynamic               | logistic_score_calibration          | station_grouped_calibration | best_F1_train     |       0.276 | 0.062   | 0.576 |       0.482 |    0.713 |               0.518 |       0.287 |

## Selected diagnostic P_ge31 companion
Selected diagnostic candidate: M4_like_inertia_ridge with logistic_score_calibration under blocked_date_calibration.
Recommended output name: `p_ge31_diagnostic`.
Diagnostic prediction table rows: 10473 (not large).

## ge33 exploratory
ge33 is retained as exploratory because event counts are smaller and fold-level calibration is less stable than ge31.

## Station / regime diagnostics
Focus station diagnostics:
| model                         | calibrator                 | validation_scheme        | station_id   |   event_count |   observed_event_rate |   mean_predicted_probability |   probability_bias |   Brier |   precision |   recall |
|:------------------------------|:---------------------------|:-------------------------|:-------------|--------------:|----------------------:|-----------------------------:|-------------------:|--------:|------------:|---------:|
| L1_full_dynamic               | logistic_score_calibration | blocked_date_calibration | S135         |            69 |                 0.178 |                        0.115 |             -0.063 |   0.088 |       0.695 |    0.594 |
| L1_full_dynamic               | logistic_score_calibration | blocked_date_calibration | S137         |            77 |                 0.198 |                        0.11  |             -0.088 |   0.104 |       0.702 |    0.519 |
| L1_full_dynamic               | logistic_score_calibration | blocked_date_calibration | S139         |             8 |                 0.021 |                        0.101 |              0.08  |   0.033 |       0.128 |    0.625 |
| L1_full_dynamic               | logistic_score_calibration | blocked_date_calibration | S142         |            84 |                 0.216 |                        0.107 |             -0.109 |   0.098 |       0.875 |    0.583 |
| M4_like_inertia_ridge         | logistic_score_calibration | blocked_date_calibration | S135         |            69 |                 0.178 |                        0.113 |             -0.065 |   0.088 |       0.672 |    0.594 |
| M4_like_inertia_ridge         | logistic_score_calibration | blocked_date_calibration | S137         |            77 |                 0.198 |                        0.111 |             -0.087 |   0.104 |       0.705 |    0.558 |
| M4_like_inertia_ridge         | logistic_score_calibration | blocked_date_calibration | S139         |             8 |                 0.021 |                        0.106 |              0.086 |   0.036 |       0.122 |    0.75  |
| M4_like_inertia_ridge         | logistic_score_calibration | blocked_date_calibration | S142         |            84 |                 0.216 |                        0.108 |             -0.108 |   0.096 |       0.911 |    0.607 |
| M7_like_compact_weather_ridge | logistic_score_calibration | blocked_date_calibration | S135         |            69 |                 0.178 |                        0.119 |             -0.059 |   0.086 |       0.672 |    0.623 |
| M7_like_compact_weather_ridge | logistic_score_calibration | blocked_date_calibration | S137         |            77 |                 0.198 |                        0.109 |             -0.09  |   0.106 |       0.696 |    0.506 |
| M7_like_compact_weather_ridge | logistic_score_calibration | blocked_date_calibration | S139         |             8 |                 0.021 |                        0.087 |              0.067 |   0.028 |       0.152 |    0.625 |
| M7_like_compact_weather_ridge | logistic_score_calibration | blocked_date_calibration | S142         |            84 |                 0.216 |                        0.106 |             -0.111 |   0.1   |       0.873 |    0.571 |
Hour-of-day diagnostics were written to `probability_by_hour.csv`.
Radiation-regime diagnostics were skipped because the probability input table did not carry shortwave/radiation columns and no new feature join was attempted.

## Interpretation
1. Probability calibration improves interpretability by producing held-out event probabilities, while deterministic Sprint 2C thresholds remain simpler score-screening rules.
2. Best P_ge31 score model by the rank used here: M4_like_inertia_ridge.
3. Most stable selected calibrator by the rank used here: logistic_score_calibration.
4. P_ge31 is ready as a diagnostic companion if described as retrospective and conditional on current splits: yes.
5. This supports Level 1 interim model-card creation because it separates WBGT_A regression scores from event-probability companion diagnostics.
6. Formula-v2 is still needed for a validated physics implementation sprint; Sprint 3B does not replace it.

## Caveats
- Retrospective probability calibration.
- Not an official warning system.
- Not prospective forecast skill.
- Not local WBGT.
- Not a replacement for WBGT_A.
- Event probabilities are conditional on current data and splits.

## Next recommended action
Level 1 interim model card.

## Run hygiene
- No forbidden files touched.
- No fallback used.
- No new WBGT regression model added.
- No System B/v12 touched.
- No commit/stage performed.
