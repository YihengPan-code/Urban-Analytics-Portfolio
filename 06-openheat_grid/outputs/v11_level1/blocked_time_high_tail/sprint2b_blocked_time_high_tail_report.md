# System A Level 1 Sprint 2B - Blocked-time + High-tail Diagnostics

## Status
PASS

## Scope
- Level 1 only.
- Ridge only with sklearn `Ridge(alpha=1.0)`.
- No new model family.
- No formula-v2.
- No Level 2.
- No System B / SOLWEIG / v12.
- No local WBGT.

## Inputs
- input file path: `data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_hourly.csv`
- row count: 10476
- analytic row count per target: hourly_mean=10473;hourly_max=10473
- station count: 27
- date range: 2026-05-07 02:00:00+08:00 to 2026-05-24 20:00:00+08:00
- target columns: official_wbgt_c_mean;official_wbgt_c_max
- selected models: L1_proxy_only;L1_proxy_radiation;M7_like_compact_weather_ridge;M4_like_inertia_ridge;L1_full_dynamic;L1_proxy_weather
- high-tail prediction source: `loso_sprint2a_oof`

## Temporal split design
For `blocked_date_cv`, unique calendar dates from `timestamp_sgt` were sorted and split into contiguous date blocks. Each fold trains on all dates outside the held-out block and tests on the held-out block. This is blocked-time CV, not prospective forecasting.

| dataset_label | fold | test_date_min | test_date_max | train_rows | test_rows | train_station_count | test_station_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_mean | date_block_1 | 2026-05-07 | 2026-05-10 | 8934 | 1539 | 27 | 27 |
| hourly_mean | date_block_2 | 2026-05-11 | 2026-05-14 | 7935 | 2538 | 27 | 27 |
| hourly_mean | date_block_3 | 2026-05-15 | 2026-05-18 | 7881 | 2592 | 27 | 27 |
| hourly_mean | date_block_4 | 2026-05-19 | 2026-05-21 | 8532 | 1941 | 27 | 27 |
| hourly_mean | date_block_5 | 2026-05-22 | 2026-05-24 | 8610 | 1863 | 27 | 27 |
| hourly_max | date_block_1 | 2026-05-07 | 2026-05-10 | 8934 | 1539 | 27 | 27 |
| hourly_max | date_block_2 | 2026-05-11 | 2026-05-14 | 7935 | 2538 | 27 | 27 |
| hourly_max | date_block_3 | 2026-05-15 | 2026-05-18 | 7881 | 2592 | 27 | 27 |
| hourly_max | date_block_4 | 2026-05-19 | 2026-05-21 | 8532 | 1941 | 27 | 27 |
| hourly_max | date_block_5 | 2026-05-22 | 2026-05-24 | 8610 | 1863 | 27 | 27 |

For `future_holdout_last_block`, the final contiguous date block was held out and all earlier dates were used for training. This is a future-block holdout / prospective-like retrospective test.

| dataset_label | fold | train_date_min | train_date_max | test_date_min | test_date_max | train_rows | test_rows | warning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_mean | last_date_block | 2026-05-07 | 2026-05-20 | 2026-05-21 | 2026-05-24 | 7962 | 2511 |  |
| hourly_max | last_date_block | 2026-05-07 | 2026-05-20 | 2026-05-21 | 2026-05-24 | 7962 | 2511 |  |

## Blocked-time validation results
### hourly_mean
| ablation_model | MAE | RMSE | bias | fixed_31_recall | fixed_31_F1 | MAE_official_ge_31 |
| --- | --- | --- | --- | --- | --- | --- |
| L1_proxy_radiation | 0.9918 | 1.3794 | 0.0448 | 0.0465 | 0.0842 | 2.0397 |
| M7_like_compact_weather_ridge | 1.0126 | 1.4038 | 0.0560 | 0.0241 | 0.0444 | 1.9940 |
| M4_like_inertia_ridge | 1.0430 | 1.4617 | 0.1103 | 0.0144 | 0.0267 | 1.9688 |
| L1_full_dynamic | 1.0545 | 1.4747 | 0.0950 | 0.0482 | 0.0821 | 1.9468 |
| L1_proxy_weather | 1.1046 | 1.4303 | 0.0012 | 0.0000 |  | 2.6072 |
| L1_proxy_only | 1.1507 | 1.4697 | -0.0129 | 0.0000 |  | 2.7199 |

### hourly_max
| ablation_model | MAE | RMSE | bias | fixed_31_recall | fixed_31_F1 | MAE_official_ge_31 |
| --- | --- | --- | --- | --- | --- | --- |
| L1_proxy_radiation | 1.0719 | 1.4975 | 0.0532 | 0.2726 | 0.3696 | 1.7945 |
| M7_like_compact_weather_ridge | 1.0859 | 1.5136 | 0.0666 | 0.2517 | 0.3616 | 1.7111 |
| M4_like_inertia_ridge | 1.1162 | 1.5754 | 0.1281 | 0.2784 | 0.3817 | 1.6819 |
| L1_full_dynamic | 1.1286 | 1.5878 | 0.1082 | 0.2985 | 0.3980 | 1.6825 |
| L1_proxy_weather | 1.2167 | 1.5632 | 0.0027 | 0.0059 | 0.0116 | 2.3075 |
| L1_proxy_only | 1.2833 | 1.6176 | -0.0149 | 0.0360 | 0.0690 | 2.4598 |

Future-block holdout:

| dataset_label | ablation_model | MAE | RMSE | bias | fixed_31_recall | fixed_31_F1 | MAE_official_ge_31 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_max | M7_like_compact_weather_ridge | 0.8887 | 1.1977 | 0.2231 | 0.3653 | 0.4959 | 1.1647 |
| hourly_max | M4_like_inertia_ridge | 0.9370 | 1.2362 | 0.2639 | 0.3383 | 0.4575 | 1.2202 |
| hourly_max | L1_full_dynamic | 0.9374 | 1.2583 | 0.3200 | 0.4611 | 0.5560 | 1.0904 |
| hourly_max | L1_proxy_radiation | 0.9445 | 1.2913 | 0.1178 | 0.2844 | 0.4060 | 1.3507 |
| hourly_max | L1_proxy_weather | 1.1307 | 1.4219 | 0.1447 | 0.0210 | 0.0403 | 1.8411 |
| hourly_max | L1_proxy_only | 1.2530 | 1.5559 | 0.1551 | 0.0329 | 0.0632 | 2.0738 |
| hourly_mean | M7_like_compact_weather_ridge | 0.8501 | 1.1465 | 0.2165 | 0.0337 | 0.0642 | 1.4435 |
| hourly_mean | L1_full_dynamic | 0.8964 | 1.2101 | 0.3173 | 0.0674 | 0.1171 | 1.3208 |
| hourly_mean | M4_like_inertia_ridge | 0.8977 | 1.1902 | 0.2558 | 0.0000 |  | 1.5198 |
| hourly_mean | L1_proxy_radiation | 0.8979 | 1.2192 | 0.1104 | 0.0056 | 0.0111 | 1.6416 |
| hourly_mean | L1_proxy_weather | 1.0346 | 1.3106 | 0.1433 | 0.0000 |  | 2.1301 |
| hourly_mean | L1_proxy_only | 1.1397 | 1.4287 | 0.1433 | 0.0000 |  | 2.3430 |

Comparison to Sprint 2A LOSO reference:

| validation_scheme | dataset_label | ablation_model | delta_MAE_vs_loso | delta_RMSE_vs_loso | delta_fixed_31_recall_vs_loso | delta_fixed_31_F1_vs_loso | delta_MAE_official_ge_31_vs_loso |
| --- | --- | --- | --- | --- | --- | --- | --- |
| blocked_date_cv | hourly_max | L1_proxy_radiation | 0.0618 | 0.1073 | -0.0042 | -0.0150 | 0.0766 |
| blocked_date_cv | hourly_max | M7_like_compact_weather_ridge | 0.1318 | 0.2007 | -0.0184 | -0.0407 | 0.1236 |
| blocked_date_cv | hourly_max | M4_like_inertia_ridge | 0.1797 | 0.3027 | -0.0234 | -0.0509 | 0.1106 |
| blocked_date_cv | hourly_max | L1_full_dynamic | 0.1790 | 0.2900 | 0.0017 | -0.0272 | 0.1151 |
| blocked_date_cv | hourly_max | L1_proxy_weather | 0.0433 | 0.0624 | -0.0059 | -0.0114 | 0.1234 |
| blocked_date_cv | hourly_max | L1_proxy_only | 0.0194 | 0.0255 | -0.0067 | -0.0123 | 0.0785 |
| blocked_date_cv | hourly_mean | L1_proxy_radiation | 0.0507 | 0.0912 | -0.0289 | -0.0499 | 0.0881 |
| blocked_date_cv | hourly_mean | M7_like_compact_weather_ridge | 0.1179 | 0.1747 | -0.0482 | -0.0860 | 0.1313 |
| blocked_date_cv | hourly_mean | M4_like_inertia_ridge | 0.1654 | 0.2650 | -0.0835 | -0.1448 | 0.1288 |
| blocked_date_cv | hourly_mean | L1_full_dynamic | 0.1658 | 0.2589 | -0.0482 | -0.0858 | 0.1271 |
| blocked_date_cv | hourly_mean | L1_proxy_weather | 0.0403 | 0.0609 | 0.0000 |  | 0.1342 |
| blocked_date_cv | hourly_mean | L1_proxy_only | 0.0180 | 0.0256 | -0.0016 |  | 0.0873 |
| future_holdout_last_block | hourly_max | M7_like_compact_weather_ridge | -0.0654 | -0.1153 | 0.0952 | 0.0937 | -0.4228 |
| future_holdout_last_block | hourly_max | M4_like_inertia_ridge | 0.0005 | -0.0365 | 0.0365 | 0.0249 | -0.3511 |
| future_holdout_last_block | hourly_max | L1_full_dynamic | -0.0122 | -0.0395 | 0.1643 | 0.1308 | -0.4770 |
| future_holdout_last_block | hourly_max | L1_proxy_radiation | -0.0657 | -0.0989 | 0.0077 | 0.0213 | -0.3673 |
| future_holdout_last_block | hourly_max | L1_proxy_weather | -0.0426 | -0.0789 | 0.0093 | 0.0173 | -0.3430 |
| future_holdout_last_block | hourly_max | L1_proxy_only | -0.0110 | -0.0362 | -0.0097 | -0.0181 | -0.3074 |
| future_holdout_last_block | hourly_mean | M7_like_compact_weather_ridge | -0.0446 | -0.0826 | -0.0385 | -0.0663 | -0.4193 |
| future_holdout_last_block | hourly_mean | L1_full_dynamic | 0.0077 | -0.0057 | -0.0289 | -0.0508 | -0.4989 |
| future_holdout_last_block | hourly_mean | M4_like_inertia_ridge | 0.0201 | -0.0064 | -0.0979 |  | -0.3201 |
| future_holdout_last_block | hourly_mean | L1_proxy_radiation | -0.0433 | -0.0691 | -0.0698 | -0.1230 | -0.3100 |
| future_holdout_last_block | hourly_mean | L1_proxy_weather | -0.0298 | -0.0588 | 0.0000 |  | -0.3429 |
| future_holdout_last_block | hourly_mean | L1_proxy_only | 0.0069 | -0.0155 | -0.0016 |  | -0.2896 |

## Stability interpretation
| dataset_label | ablation_model | stability | blocked_delta_MAE_vs_loso | future_delta_MAE_vs_loso | min_delta_fixed_31_F1_vs_loso | max_delta_high_tail_MAE_vs_loso |
| --- | --- | --- | --- | --- | --- | --- |
| hourly_max | L1_full_dynamic | mixed | 0.1790 | -0.0122 | -0.0272 | 0.1151 |
| hourly_max | L1_proxy_only | stable | 0.0194 | -0.0110 | -0.0181 | 0.0785 |
| hourly_max | L1_proxy_radiation | stable | 0.0618 | -0.0657 | -0.0150 | 0.0766 |
| hourly_max | L1_proxy_weather | stable | 0.0433 | -0.0426 | -0.0114 | 0.1234 |
| hourly_max | M4_like_inertia_ridge | mixed | 0.1797 | 0.0005 | -0.0509 | 0.1106 |
| hourly_max | M7_like_compact_weather_ridge | mixed | 0.1318 | -0.0654 | -0.0407 | 0.1236 |
| hourly_mean | L1_full_dynamic | mixed | 0.1658 | 0.0077 | -0.0858 | 0.1271 |
| hourly_mean | L1_proxy_only | stable | 0.0180 | 0.0069 |  | 0.0873 |
| hourly_mean | L1_proxy_radiation | mixed | 0.0507 | -0.0433 | -0.1230 | 0.0881 |
| hourly_mean | L1_proxy_weather | stable | 0.0403 | -0.0298 |  | 0.1342 |
| hourly_mean | M4_like_inertia_ridge | mixed | 0.1654 | 0.0201 | -0.1448 | 0.1288 |
| hourly_mean | M7_like_compact_weather_ridge | stable | 0.1179 | -0.0446 | -0.0860 | 0.1313 |

M4_like remains preferred: no; blocked-time ranking is mixed, so M4_like is not promoted as the sole primary Level 1 baseline. Full_dynamic remains close but is not promoted unless its blocked-time and high-tail rows improve materially without station robustness cost. Proxy_radiation remains useful where it improves over proxy_only, while proxy_only remains insufficient for threshold/high-tail behavior.

## High-tail residual diagnostics
Residuals are `official - predicted`; positive residuals indicate underprediction.

| dataset_label | ablation_model | mean_residual_official_minus_pred |
| --- | --- | --- |
| hourly_max | L1_full_dynamic | 1.8673 |
| hourly_max | L1_proxy_only | 2.7969 |
| hourly_max | L1_proxy_radiation | 1.9862 |
| hourly_max | L1_proxy_weather | 2.6105 |
| hourly_max | M4_like_inertia_ridge | 1.8935 |
| hourly_max | M7_like_compact_weather_ridge | 1.9255 |
| hourly_mean | L1_full_dynamic | 2.3713 |
| hourly_mean | L1_proxy_only | 3.2378 |
| hourly_mean | L1_proxy_radiation | 2.4629 |
| hourly_mean | L1_proxy_weather | 3.0995 |
| hourly_mean | M4_like_inertia_ridge | 2.3993 |
| hourly_mean | M7_like_compact_weather_ridge | 2.4479 |

| dataset_label | ablation_model | threshold_name | TP | FP | TN | FN | precision | recall | F1 | predicted_positive_count | official_positive_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_max | L1_full_dynamic | fixed_31 | 355 | 119 | 9158 | 841 | 0.7489 | 0.2968 | 0.4251 | 474 | 1196 |
| hourly_max | L1_full_dynamic | fixed_33 | 0 | 0 | 10354 | 119 |  | 0.0000 |  | 0 | 119 |
| hourly_max | L1_proxy_only | fixed_31 | 51 | 8 | 9269 | 1145 | 0.8644 | 0.0426 | 0.0813 | 59 | 1196 |
| hourly_max | L1_proxy_only | fixed_33 | 0 | 0 | 10354 | 119 |  | 0.0000 |  | 0 | 119 |
| hourly_max | L1_proxy_radiation | fixed_31 | 331 | 194 | 9083 | 865 | 0.6305 | 0.2768 | 0.3847 | 525 | 1196 |
| hourly_max | L1_proxy_radiation | fixed_33 | 0 | 0 | 10354 | 119 |  | 0.0000 |  | 0 | 119 |
| hourly_max | L1_proxy_weather | fixed_31 | 14 | 7 | 9270 | 1182 | 0.6667 | 0.0117 | 0.0230 | 21 | 1196 |
| hourly_max | L1_proxy_weather | fixed_33 | 0 | 0 | 10354 | 119 |  | 0.0000 |  | 0 | 119 |
| hourly_max | M4_like_inertia_ridge | fixed_31 | 361 | 112 | 9165 | 835 | 0.7632 | 0.3018 | 0.4326 | 473 | 1196 |
| hourly_max | M4_like_inertia_ridge | fixed_33 | 0 | 0 | 10354 | 119 |  | 0.0000 |  | 0 | 119 |
| hourly_max | M7_like_compact_weather_ridge | fixed_31 | 323 | 87 | 9190 | 873 | 0.7878 | 0.2701 | 0.4022 | 410 | 1196 |
| hourly_max | M7_like_compact_weather_ridge | fixed_33 | 0 | 0 | 10354 | 119 |  | 0.0000 |  | 0 | 119 |
| hourly_mean | L1_full_dynamic | fixed_31 | 60 | 32 | 9818 | 563 | 0.6522 | 0.0963 | 0.1678 | 92 | 623 |
| hourly_mean | L1_full_dynamic | fixed_33 | 0 | 0 | 10443 | 30 |  | 0.0000 |  | 0 | 30 |
| hourly_mean | L1_proxy_only | fixed_31 | 1 | 0 | 9850 | 622 | 1.0000 | 0.0016 | 0.0032 | 1 | 623 |
| hourly_mean | L1_proxy_only | fixed_33 | 0 | 0 | 10443 | 30 |  | 0.0000 |  | 0 | 30 |
| hourly_mean | L1_proxy_radiation | fixed_31 | 47 | 31 | 9819 | 576 | 0.6026 | 0.0754 | 0.1341 | 78 | 623 |
| hourly_mean | L1_proxy_radiation | fixed_33 | 0 | 0 | 10443 | 30 |  | 0.0000 |  | 0 | 30 |
| hourly_mean | L1_proxy_weather | fixed_31 | 0 | 0 | 9850 | 623 |  | 0.0000 |  | 0 | 623 |
| hourly_mean | L1_proxy_weather | fixed_33 | 0 | 0 | 10443 | 30 |  | 0.0000 |  | 0 | 30 |
| hourly_mean | M4_like_inertia_ridge | fixed_31 | 61 | 27 | 9823 | 562 | 0.6932 | 0.0979 | 0.1716 | 88 | 623 |
| hourly_mean | M4_like_inertia_ridge | fixed_33 | 0 | 0 | 10443 | 30 |  | 0.0000 |  | 0 | 30 |
| hourly_mean | M7_like_compact_weather_ridge | fixed_31 | 45 | 22 | 9828 | 578 | 0.6716 | 0.0722 | 0.1304 | 67 | 623 |
| hourly_mean | M7_like_compact_weather_ridge | fixed_33 | 0 | 0 | 10443 | 30 |  | 0.0000 |  | 0 | 30 |

| dataset_label | ablation_model | official_event_threshold_c | official_positive_count | exploratory | best_F1_threshold | best_F1 | recall_90_threshold | precision_70_threshold | max_youden_J_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_max | L1_full_dynamic | 31.0000 | 1196 | False | 29.5000 | 0.6002 | 28.8000 | 30.9000 | 28.5000 |
| hourly_max | L1_full_dynamic | 33.0000 | 119 | False | 31.5000 | 0.1987 | 29.5000 |  | 29.5000 |
| hourly_max | L1_proxy_only | 31.0000 | 1196 | False | 29.2000 | 0.5532 | 28.4000 | 30.1000 | 28.4000 |
| hourly_max | L1_proxy_only | 33.0000 | 119 | False | 30.4000 | 0.1711 | 28.5000 |  | 28.5000 |
| hourly_max | L1_proxy_radiation | 31.0000 | 1196 | False | 29.7000 | 0.5932 | 28.4000 | 31.3000 | 28.0000 |
| hourly_max | L1_proxy_radiation | 33.0000 | 119 | False | 31.3000 | 0.1962 | 29.3000 |  | 28.9000 |
| hourly_max | L1_proxy_weather | 31.0000 | 1196 | False | 29.5000 | 0.5821 | 28.7000 | 30.1000 | 28.6000 |
| hourly_max | L1_proxy_weather | 33.0000 | 119 | False | 30.3000 | 0.1636 | 29.0000 | 31.6000 | 28.7000 |
| hourly_max | M4_like_inertia_ridge | 31.0000 | 1196 | False | 29.5000 | 0.5972 | 28.7000 | 30.8000 | 28.4000 |
| hourly_max | M4_like_inertia_ridge | 33.0000 | 119 | False | 31.4000 | 0.1947 | 29.5000 |  | 29.5000 |
| hourly_max | M7_like_compact_weather_ridge | 31.0000 | 1196 | False | 29.4000 | 0.6002 | 28.9000 | 30.9000 | 28.8000 |
| hourly_max | M7_like_compact_weather_ridge | 33.0000 | 119 | False | 31.4000 | 0.1987 | 29.5000 |  | 28.9000 |
| hourly_mean | L1_full_dynamic | 31.0000 | 623 | False | 29.9000 | 0.4668 | 28.5000 | 31.2000 | 28.1000 |
| hourly_mean | L1_full_dynamic | 33.0000 | 30 | True | 31.2000 | 0.1250 | 28.7000 |  | 28.2000 |
| hourly_mean | L1_proxy_only | 31.0000 | 623 | False | 28.9000 | 0.4155 | 28.0000 | 30.6000 | 28.0000 |
| hourly_mean | L1_proxy_only | 33.0000 | 30 | True | 30.3000 | 0.0698 | 28.0000 |  | 28.7000 |
| hourly_mean | L1_proxy_radiation | 31.0000 | 623 | False | 29.7000 | 0.4382 | 28.5000 |  | 28.4000 |
| hourly_mean | L1_proxy_radiation | 33.0000 | 30 | True | 30.9000 | 0.0752 | 29.1000 |  | 29.1000 |
| hourly_mean | L1_proxy_weather | 31.0000 | 623 | False | 29.4000 | 0.4319 | 28.4000 | 30.4000 | 28.2000 |
| hourly_mean | L1_proxy_weather | 33.0000 | 30 | True | 29.7000 | 0.0655 | 28.3000 |  | 28.1000 |
| hourly_mean | M4_like_inertia_ridge | 31.0000 | 623 | False | 29.9000 | 0.4790 | 28.5000 | 31.1000 | 28.5000 |
| hourly_mean | M4_like_inertia_ridge | 33.0000 | 30 | True | 31.0000 | 0.1017 | 28.8000 |  | 28.5000 |
| hourly_mean | M7_like_compact_weather_ridge | 31.0000 | 623 | False | 29.8000 | 0.4602 | 28.5000 |  | 28.2000 |
| hourly_mean | M7_like_compact_weather_ridge | 33.0000 | 30 | True | 31.0000 | 0.1031 | 28.6000 |  | 28.2000 |

Fixed_33 predicted-positive count across diagnostics: 0. If fixed_33 remains untriggered or sparse, >=33 modeling remains exploratory. M4_like still shows high-tail underprediction when high WBGT bins retain positive mean residuals.

## Station and S142 diagnostics
Worst station rows by MAE:

| dataset_label | ablation_model | station_id | n | MAE | bias | official_ge_31_count | official_ge_33_count | fixed_31_recall | fixed_31_F1 | residual_p90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_max | L1_proxy_only | S139 | 388 | 1.6717 | -0.7544 | 8 | 0 | 0.0000 |  | 1.8054 |
| hourly_max | L1_proxy_only | S142 | 388 | 1.5873 | 0.5522 | 84 | 32 | 0.0000 |  | 3.7952 |
| hourly_max | L1_proxy_weather | S139 | 388 | 1.5726 | -1.1096 | 8 | 0 | 0.0000 |  | 1.0134 |
| hourly_max | L1_proxy_weather | S142 | 388 | 1.4951 | 0.5397 | 84 | 32 | 0.0000 |  | 3.6006 |
| hourly_mean | L1_proxy_only | S139 | 388 | 1.4703 | -0.6073 | 0 | 0 |  |  | 1.7855 |
| hourly_max | L1_proxy_only | S147 | 388 | 1.4523 | -0.1165 | 55 | 4 | 0.0000 |  | 2.6204 |
| hourly_max | L1_proxy_only | S137 | 388 | 1.4243 | 0.6325 | 77 | 26 | 0.0000 |  | 3.4562 |
| hourly_mean | L1_proxy_weather | S139 | 388 | 1.4178 | -0.9166 | 0 | 0 |  |  | 1.1277 |

S142 sensitivity:

| dataset_label | ablation_model | station_subset | official_ge_31_count | official_ge_33_count | MAE_official_ge_31 | fixed_31_recall | fixed_31_F1 | fixed_33_recall | fixed_33_F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_max | L1_full_dynamic | all_stations | 1196 | 119 | 1.5674 | 0.2968 | 0.4251 | 0.0000 |  |
| hourly_max | L1_full_dynamic | excluding_S142 | 1112 | 87 | 1.4863 | 0.3067 | 0.4338 | 0.0000 |  |
| hourly_max | L1_proxy_only | all_stations | 1196 | 119 | 2.3812 | 0.0426 | 0.0813 | 0.0000 |  |
| hourly_max | L1_proxy_only | excluding_S142 | 1112 | 87 | 2.2944 | 0.0459 | 0.0871 | 0.0000 |  |
| hourly_max | L1_proxy_radiation | all_stations | 1196 | 119 | 1.7179 | 0.2768 | 0.3847 | 0.0000 |  |
| hourly_max | L1_proxy_radiation | excluding_S142 | 1112 | 87 | 1.6357 | 0.2851 | 0.3909 | 0.0000 |  |
| hourly_max | L1_proxy_weather | all_stations | 1196 | 119 | 2.1841 | 0.0117 | 0.0230 | 0.0000 |  |
| hourly_max | L1_proxy_weather | excluding_S142 | 1112 | 87 | 2.1013 | 0.0126 | 0.0247 | 0.0000 |  |
| hourly_max | M4_like_inertia_ridge | all_stations | 1196 | 119 | 1.5713 | 0.3018 | 0.4326 | 0.0000 |  |
| hourly_max | M4_like_inertia_ridge | excluding_S142 | 1112 | 87 | 1.4917 | 0.3121 | 0.4418 | 0.0000 |  |
| hourly_max | M7_like_compact_weather_ridge | all_stations | 1196 | 119 | 1.5875 | 0.2701 | 0.4022 | 0.0000 |  |
| hourly_max | M7_like_compact_weather_ridge | excluding_S142 | 1112 | 87 | 1.5045 | 0.2797 | 0.4119 | 0.0000 |  |
| hourly_mean | L1_full_dynamic | all_stations | 623 | 30 | 1.8197 | 0.0963 | 0.1678 | 0.0000 |  |
| hourly_mean | L1_full_dynamic | excluding_S142 | 557 | 17 | 1.7070 | 0.1059 | 0.1821 | 0.0000 |  |
| hourly_mean | L1_proxy_only | all_stations | 623 | 30 | 2.6326 | 0.0016 | 0.0032 | 0.0000 |  |
| hourly_mean | L1_proxy_only | excluding_S142 | 557 | 17 | 2.5185 | 0.0018 | 0.0036 | 0.0000 |  |
| hourly_mean | L1_proxy_radiation | all_stations | 623 | 30 | 1.9516 | 0.0754 | 0.1341 | 0.0000 |  |
| hourly_mean | L1_proxy_radiation | excluding_S142 | 557 | 17 | 1.8349 | 0.0844 | 0.1480 | 0.0000 |  |
| hourly_mean | L1_proxy_weather | all_stations | 623 | 30 | 2.4730 | 0.0000 |  | 0.0000 |  |
| hourly_mean | L1_proxy_weather | excluding_S142 | 557 | 17 | 2.3644 | 0.0000 |  | 0.0000 |  |
| hourly_mean | M4_like_inertia_ridge | all_stations | 623 | 30 | 1.8400 | 0.0979 | 0.1716 | 0.0000 |  |
| hourly_mean | M4_like_inertia_ridge | excluding_S142 | 557 | 17 | 1.7321 | 0.1077 | 0.1863 | 0.0000 |  |
| hourly_mean | M7_like_compact_weather_ridge | all_stations | 623 | 30 | 1.8627 | 0.0722 | 0.1304 | 0.0000 |  |
| hourly_mean | M7_like_compact_weather_ridge | excluding_S142 | 557 | 17 | 1.7498 | 0.0808 | 0.1442 | 0.0000 |  |

Excluding S142 is prediction-filtered sensitivity only; no model was retrained.

## Radiation / regime diagnostics
| dataset_label | ablation_model | regime_type | regime_value | n | MAE | bias | official_ge_31_count | fixed_31_recall | fixed_31_F1 | residual_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_max | L1_full_dynamic | shortwave_radiation | q4_high | 2623 | 0.9314 | 0.0307 | 307 | 0.3062 | 0.4332 | 0.0307 |
| hourly_max | L1_proxy_only | shortwave_radiation | q4_high | 2623 | 1.2426 | 0.0213 | 307 | 0.0423 | 0.0807 | 0.0213 |
| hourly_max | L1_proxy_radiation | shortwave_radiation | q4_high | 2623 | 1.0087 | 0.0205 | 307 | 0.2834 | 0.3884 | 0.0205 |
| hourly_max | L1_proxy_weather | shortwave_radiation | q4_high | 2623 | 1.1587 | 0.0463 | 307 | 0.0098 | 0.0193 | 0.0463 |
| hourly_max | M4_like_inertia_ridge | shortwave_radiation | q4_high | 2623 | 0.9201 | 0.0278 | 307 | 0.3094 | 0.4378 | 0.0278 |
| hourly_max | M7_like_compact_weather_ridge | shortwave_radiation | q4_high | 2623 | 0.9397 | 0.0323 | 307 | 0.2704 | 0.3990 | 0.0323 |
| hourly_mean | L1_full_dynamic | shortwave_radiation | q4_high | 2613 | 0.8690 | 0.0296 | 154 | 0.1039 | 0.1788 | 0.0296 |
| hourly_mean | L1_proxy_only | shortwave_radiation | q4_high | 2613 | 1.1064 | 0.0211 | 154 | 0.0000 |  | 0.0211 |
| hourly_mean | L1_proxy_radiation | shortwave_radiation | q4_high | 2613 | 0.9344 | 0.0199 | 154 | 0.0844 | 0.1494 | 0.0199 |
| hourly_mean | L1_proxy_weather | shortwave_radiation | q4_high | 2613 | 1.0462 | 0.0437 | 154 | 0.0000 |  | 0.0437 |
| hourly_mean | M4_like_inertia_ridge | shortwave_radiation | q4_high | 2613 | 0.8588 | 0.0265 | 154 | 0.1039 | 0.1778 | 0.0265 |
| hourly_mean | M7_like_compact_weather_ridge | shortwave_radiation | q4_high | 2616 | 0.8795 | 0.0315 | 154 | 0.0714 | 0.1279 | 0.0315 |

Regime diagnostics are descriptive. They support residual-pattern triage only and do not establish causal drivers.

## Interpretation
Blocked-time results provide diagnostic evidence on temporal robustness for existing Ridge dynamic feature groups. High-tail residuals continue to be the main limitation when high WBGT bins have positive residuals and fixed threshold recall remains low. Candidate next steps should focus on event/high-tail calibration or formula-v2 benchmarking before any stronger claim.

## Caveats
- Blocked-time is retrospective, not true prospective forecast evaluation.
- No hyperparameter tuning.
- No probability calibration.
- No model family comparison.
- No local WBGT.
- No System B.

## Next recommended action
Sprint 2C high-tail/event calibration.

## Guardrail closeout
- no forbidden files touched.
- no fallback used.
- no new model family added.
- no System B/v12 touched.
- no commit/stage performed.
- optional prediction CSV files are local diagnostics and should be treated as do-not-commit if size policy requires.

## Outputs
- `outputs/v11_level1/blocked_time_high_tail/sprint2b_manifest.csv`
- `outputs/v11_level1/blocked_time_high_tail/blocked_time_split_manifest.csv`
- `outputs/v11_level1/blocked_time_high_tail/blocked_time_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/future_holdout_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/blocked_vs_loso_delta.csv`
- `outputs/v11_level1/blocked_time_high_tail/residual_by_wbgt_bin.csv`
- `outputs/v11_level1/blocked_time_high_tail/threshold_fixed_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/threshold_scan_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/residual_by_hour.csv`
- `outputs/v11_level1/blocked_time_high_tail/residual_by_station.csv`
- `outputs/v11_level1/blocked_time_high_tail/s142_sensitivity_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/residual_by_regime.csv`
- `outputs/v11_level1/blocked_time_high_tail/sprint2b_blocked_time_high_tail_report.md`
