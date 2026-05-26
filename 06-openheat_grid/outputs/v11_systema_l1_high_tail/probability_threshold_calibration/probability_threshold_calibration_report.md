# System A A-L1H.2 Probability / Threshold Calibration

Generated: 2026-05-26
Acceptance status: `PASS`
Decision status: `PASS_CANDIDATE_PROBABILITY_COMPANION`
Branch: `codex/systema-l1h2-prob-threshold-calibration`

## 1. Why A-L1H.2 Follows A-L1H.1

A-L1H.0 found global high-tail compression plus station bias. A-L1H.0c then recovered full-period weather-regime coverage and showed that radiation-hot periods contain most observed ge31 events and misses. A-L1H.1 found the simple formula/proxy route weak or negative: raw formula/proxy candidates did not reach fixed_31 crossings, while M4/M7 scores remained more useful but their nominal score >=31 thresholds were misaligned with event detection. A-L1H.2 therefore tests whether existing M4/M7 OOF scores can be calibrated into a cautious diagnostic P_ge31 companion and station-held-out threshold operating points.

## 2. Inputs And Validation Method

| inventory_role            | path                                                                                                     | exists | rows_total | rows_selected_loso | selected_station_count | selected_event_count_ge31 | selected_event_count_ge33 |
| ------------------------- | -------------------------------------------------------------------------------------------------------- | ------ | ---------- | ------------------ | ---------------------- | ------------------------- | ------------------------- |
| residual_analysis_input   | outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv                      | 1.000  | 6696.000   | NA                 | NA                     | NA                        | NA                        |
| residual_weather_merge    | outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv | 1.000  | 6696.000   | 3348.000           | 27.000                 | 408.000                   | 30.000                    |
| oof_predictions           | outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv                                     | 1.000  | 30132.000  | NA                 | NA                     | NA                        | NA                        |
| formula_threshold_metrics | outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_threshold_metrics_31_33.csv                 | 1.000  | 66.000     | NA                 | NA                     | NA                        | NA                        |

Validation method: `station_grouped_loso`. Fold usability: `fold equals station_id in primary LOSO rows`. Fold count: `27`.

All promoted probability rows are predicted for held-out stations after fitting the calibrator on other-station OOF rows. The probability models consume existing score columns only; optional score+hour and score+radiation-hot fits are marked diagnostic.

## 3. M4 vs M7 Score Comparison

Station-held-out score-threshold baselines:

| model_name               | operating_point | threshold | precision | recall | F1    | CSI   | false_alarm_ratio | miss_rate | TP      | FP      | FN      | TN       |
| ------------------------ | --------------- | --------- | --------- | ------ | ----- | ----- | ----------------- | --------- | ------- | ------- | ------- | -------- |
| M4_inertia_ridge         | best_F1         | 30.700    | 0.683     | 0.770  | 0.724 | 0.567 | 0.317             | 0.230     | 157.000 | 73.000  | 47.000  | 1397.000 |
| M4_inertia_ridge         | fixed_score_31  | 31.000    | 0.682     | 0.588  | 0.632 | 0.462 | 0.318             | 0.412     | 120.000 | 56.000  | 84.000  | 1414.000 |
| M4_inertia_ridge         | max_Youden      | 29.900    | 0.548     | 0.956  | 0.696 | 0.534 | 0.452             | 0.044     | 195.000 | 161.000 | 9.000   | 1309.000 |
| M4_inertia_ridge         | precision_70    | 31.183    | 0.658     | 0.377  | 0.480 | 0.316 | 0.342             | 0.623     | 77.000  | 40.000  | 127.000 | 1430.000 |
| M4_inertia_ridge         | recall_90       | 30.006    | 0.542     | 0.917  | 0.681 | 0.517 | 0.458             | 0.083     | 187.000 | 158.000 | 17.000  | 1312.000 |
| M7_compact_weather_ridge | best_F1         | 30.248    | 0.618     | 0.833  | 0.710 | 0.550 | 0.382             | 0.167     | 170.000 | 105.000 | 34.000  | 1365.000 |
| M7_compact_weather_ridge | fixed_score_31  | 31.000    | 0.722     | 0.574  | 0.639 | 0.470 | 0.278             | 0.426     | 117.000 | 45.000  | 87.000  | 1425.000 |
| M7_compact_weather_ridge | max_Youden      | 29.000    | 0.453     | 0.971  | 0.618 | 0.447 | 0.547             | 0.029     | 198.000 | 239.000 | 6.000   | 1231.000 |
| M7_compact_weather_ridge | precision_70    | 30.870    | 0.699     | 0.593  | 0.642 | 0.473 | 0.301             | 0.407     | 121.000 | 52.000  | 83.000  | 1418.000 |
| M7_compact_weather_ridge | recall_90       | 29.250    | 0.492     | 0.917  | 0.640 | 0.471 | 0.508             | 0.083     | 187.000 | 193.000 | 17.000  | 1277.000 |

Score-bin empirical ge31 event rates:

| model_name               | score_bin     | n       | event_count | event_rate | mean_score | observed_wbgt_mean | event_rate_monotonicity |
| ------------------------ | ------------- | ------- | ----------- | ---------- | ---------- | ------------------ | ----------------------- |
| M4_inertia_ridge         | [24.50,25.00) | 3.000   | 0.000       | 0.000      | 24.952     | 24.800             | mostly_monotonic        |
| M4_inertia_ridge         | [25.00,25.50) | 124.000 | 0.000       | 0.000      | 25.385     | 25.190             | mostly_monotonic        |
| M4_inertia_ridge         | [25.50,26.00) | 465.000 | 0.000       | 0.000      | 25.746     | 25.811             | mostly_monotonic        |
| M4_inertia_ridge         | [26.00,26.50) | 288.000 | 0.000       | 0.000      | 26.216     | 26.252             | mostly_monotonic        |
| M4_inertia_ridge         | [26.50,27.00) | 85.000  | 0.000       | 0.000      | 26.709     | 26.709             | mostly_monotonic        |
| M4_inertia_ridge         | [27.00,27.50) | 74.000  | 0.000       | 0.000      | 27.248     | 27.065             | mostly_monotonic        |
| M4_inertia_ridge         | [27.50,28.00) | 52.000  | 0.000       | 0.000      | 27.691     | 27.525             | mostly_monotonic        |
| M4_inertia_ridge         | [28.00,28.50) | 31.000  | 0.000       | 0.000      | 28.181     | 27.652             | mostly_monotonic        |
| M4_inertia_ridge         | [28.50,29.00) | 87.000  | 5.000       | 0.057      | 28.777     | 28.985             | mostly_monotonic        |
| M4_inertia_ridge         | [29.00,29.50) | 66.000  | 4.000       | 0.061      | 29.254     | 29.297             | mostly_monotonic        |
| M4_inertia_ridge         | [29.50,30.00) | 51.000  | 4.000       | 0.078      | 29.729     | 29.486             | mostly_monotonic        |
| M4_inertia_ridge         | [30.00,30.50) | 93.000  | 30.000      | 0.323      | 30.218     | 30.343             | mostly_monotonic        |
| M4_inertia_ridge         | [30.50,31.00) | 79.000  | 41.000      | 0.519      | 30.763     | 30.997             | mostly_monotonic        |
| M4_inertia_ridge         | [31.00,31.50) | 125.000 | 85.000      | 0.680      | 31.212     | 31.312             | mostly_monotonic        |
| M4_inertia_ridge         | [31.50,32.00) | 45.000  | 29.000      | 0.644      | 31.667     | 31.029             | mostly_monotonic        |
| M4_inertia_ridge         | [32.00,32.50) | 6.000   | 6.000       | 1.000      | 32.055     | 31.600             | mostly_monotonic        |
| M7_compact_weather_ridge | [24.50,25.00) | 2.000   | 0.000       | 0.000      | 24.782     | 24.850             | mostly_monotonic        |
| M7_compact_weather_ridge | [25.00,25.50) | 193.000 | 0.000       | 0.000      | 25.341     | 25.410             | mostly_monotonic        |
| M7_compact_weather_ridge | [25.50,26.00) | 366.000 | 0.000       | 0.000      | 25.732     | 25.843             | mostly_monotonic        |
| M7_compact_weather_ridge | [26.00,26.50) | 222.000 | 0.000       | 0.000      | 26.265     | 26.129             | mostly_monotonic        |

## 4. Probability Calibration Metrics

| model_name               | calibrator_id                           | diagnostic_only | n        | event_count_ge31 | Brier | log_loss | PR_AUC | ROC_AUC | ECE_fixed | MCE_fixed | ECE_quantile | calibration_intercept | calibration_slope | p05_predicted_probability | p50_predicted_probability | p95_predicted_probability |
| ------------------------ | --------------------------------------- | --------------- | -------- | ---------------- | ----- | -------- | ------ | ------- | --------- | --------- | ------------ | --------------------- | ----------------- | ------------------------- | ------------------------- | ------------------------- |
| M4_inertia_ridge         | isotonic_score_only                     | 0.000           | 1674.000 | 204.000          | 0.052 | 0.170    | 0.610  | 0.947   | 0.018     | 0.447     | 0.022        | -0.052                | 0.754             | 0.000                     | 0.000                     | 0.702                     |
| M4_inertia_ridge         | logistic_score_only                     | 0.000           | 1674.000 | 204.000          | 0.056 | 0.168    | 0.653  | 0.954   | 0.022     | 0.216     | 0.008        | -0.012                | 0.967             | 0.000                     | 0.001                     | 0.687                     |
| M7_compact_weather_ridge | isotonic_score_only                     | 0.000           | 1674.000 | 204.000          | 0.056 | 0.176    | 0.555  | 0.941   | 0.013     | 0.800     | 0.014        | -0.063                | 0.795             | 0.000                     | 0.000                     | 0.738                     |
| M7_compact_weather_ridge | logistic_score_only                     | 0.000           | 1674.000 | 204.000          | 0.057 | 0.176    | 0.624  | 0.952   | 0.020     | 0.247     | 0.010        | -0.015                | 0.974             | 0.001                     | 0.004                     | 0.727                     |
| M7_compact_weather_ridge | empirical_score_bin                     | 0.000           | 1674.000 | 204.000          | 0.058 | 0.177    | 0.511  | 0.932   | 0.017     | 0.283     | 0.006        | -0.015                | 0.952             | 0.000                     | 0.000                     | 0.704                     |
| M4_inertia_ridge         | empirical_score_bin                     | 0.000           | 1674.000 | 204.000          | 0.058 | 0.179    | 0.500  | 0.932   | 0.019     | 0.704     | 0.004        | -0.033                | 0.870             | 0.000                     | 0.000                     | 0.673                     |
| M4_inertia_ridge         | logistic_score_radiation_hot_diagnostic | 1.000           | 1674.000 | 204.000          | 0.056 | 0.169    | 0.653  | 0.954   | 0.022     | 0.215     | 0.011        | -0.014                | 0.958             | 0.000                     | 0.001                     | 0.687                     |
| M4_inertia_ridge         | logistic_score_hour_diagnostic          | 1.000           | 1674.000 | 204.000          | 0.056 | 0.168    | 0.640  | 0.953   | 0.025     | 0.217     | 0.009        | -0.014                | 0.952             | 0.000                     | 0.000                     | 0.700                     |
| M7_compact_weather_ridge | logistic_score_hour_diagnostic          | 1.000           | 1674.000 | 204.000          | 0.057 | 0.172    | 0.590  | 0.950   | 0.018     | 0.808     | 0.009        | -0.019                | 0.954             | 0.000                     | 0.000                     | 0.715                     |
| M7_compact_weather_ridge | logistic_score_radiation_hot_diagnostic | 1.000           | 1674.000 | 204.000          | 0.057 | 0.177    | 0.622  | 0.951   | 0.019     | 0.203     | 0.007        | -0.018                | 0.966             | 0.000                     | 0.003                     | 0.723                     |

ge33 remains exploratory and is not used to promote a probability companion.

## 5. Threshold Operating Point Metrics

| model_name               | output_id                      | operating_point           | threshold | precision | recall | F1    | CSI   | false_alarm_ratio | miss_rate | TP      | FP      | FN      | TN       |
| ------------------------ | ------------------------------ | ------------------------- | --------- | --------- | ------ | ----- | ----- | ----------------- | --------- | ------- | ------- | ------- | -------- |
| M4_inertia_ridge         | empirical_score_bin            | best_F1                   | 0.107     | 0.552     | 0.907  | 0.686 | 0.523 | 0.448             | 0.093     | 185.000 | 150.000 | 19.000  | 1320.000 |
| M4_inertia_ridge         | empirical_score_bin            | precision_70              | 0.450     | 0.000     | NA     | NA    | 0.000 | 1.000             | NA        | 0.000   | 7.000   | 0.000   | 55.000   |
| M4_inertia_ridge         | empirical_score_bin            | recall_90                 | 0.429     | 0.552     | 0.907  | 0.686 | 0.523 | 0.448             | 0.093     | 185.000 | 150.000 | 19.000  | 1320.000 |
| M7_compact_weather_ridge | empirical_score_bin            | best_F1                   | 0.152     | 0.527     | 0.868  | 0.656 | 0.488 | 0.473             | 0.132     | 177.000 | 159.000 | 27.000  | 1311.000 |
| M7_compact_weather_ridge | empirical_score_bin            | precision_70              | 0.354     | 0.598     | 0.583  | 0.591 | 0.419 | 0.402             | 0.417     | 70.000  | 47.000  | 50.000  | 1011.000 |
| M7_compact_weather_ridge | empirical_score_bin            | recall_90                 | 0.142     | 0.403     | 0.990  | 0.573 | 0.402 | 0.597             | 0.010     | 202.000 | 299.000 | 2.000   | 1171.000 |
| M4_inertia_ridge         | isotonic_score_only            | best_F1                   | 0.309     | 0.678     | 0.765  | 0.719 | 0.561 | 0.322             | 0.235     | 156.000 | 74.000  | 48.000  | 1396.000 |
| M4_inertia_ridge         | isotonic_score_only            | precision_70              | 0.614     | 0.653     | 0.377  | 0.478 | 0.314 | 0.347             | 0.623     | 77.000  | 41.000  | 127.000 | 1429.000 |
| M4_inertia_ridge         | isotonic_score_only            | recall_90                 | 0.296     | 0.545     | 0.946  | 0.692 | 0.529 | 0.455             | 0.054     | 193.000 | 161.000 | 11.000  | 1309.000 |
| M4_inertia_ridge         | isotonic_score_only            | selected_candidate_policy | 0.309     | 0.678     | 0.765  | 0.719 | 0.561 | 0.322             | 0.235     | 156.000 | 74.000  | 48.000  | 1396.000 |
| M7_compact_weather_ridge | isotonic_score_only            | best_F1                   | 0.319     | 0.612     | 0.819  | 0.700 | 0.539 | 0.388             | 0.181     | 167.000 | 106.000 | 37.000  | 1364.000 |
| M7_compact_weather_ridge | isotonic_score_only            | precision_70              | 0.501     | 0.696     | 0.549  | 0.614 | 0.443 | 0.304             | 0.451     | 112.000 | 49.000  | 92.000  | 1421.000 |
| M7_compact_weather_ridge | isotonic_score_only            | recall_90                 | 0.170     | 0.448     | 0.966  | 0.612 | 0.441 | 0.552             | 0.034     | 197.000 | 243.000 | 7.000   | 1227.000 |
| M4_inertia_ridge         | logistic_score_hour_diagnostic | best_F1                   | 0.421     | 0.664     | 0.784  | 0.719 | 0.561 | 0.336             | 0.216     | 160.000 | 81.000  | 44.000  | 1389.000 |
| M4_inertia_ridge         | logistic_score_hour_diagnostic | precision_70              | 0.645     | 0.640     | 0.392  | 0.486 | 0.321 | 0.360             | 0.608     | 80.000  | 45.000  | 124.000 | 1425.000 |
| M4_inertia_ridge         | logistic_score_hour_diagnostic | recall_90                 | 0.210     | 0.542     | 0.922  | 0.682 | 0.518 | 0.458             | 0.078     | 188.000 | 159.000 | 16.000  | 1311.000 |
| M7_compact_weather_ridge | logistic_score_hour_diagnostic | best_F1                   | 0.406     | 0.647     | 0.789  | 0.711 | 0.551 | 0.353             | 0.211     | 161.000 | 88.000  | 43.000  | 1382.000 |
| M7_compact_weather_ridge | logistic_score_hour_diagnostic | precision_70              | 0.639     | 0.650     | 0.436  | 0.522 | 0.353 | 0.350             | 0.564     | 89.000  | 48.000  | 115.000 | 1422.000 |
| M7_compact_weather_ridge | logistic_score_hour_diagnostic | recall_90                 | 0.150     | 0.491     | 0.941  | 0.645 | 0.476 | 0.509             | 0.059     | 192.000 | 199.000 | 12.000  | 1271.000 |
| M4_inertia_ridge         | logistic_score_only            | best_F1                   | 0.451     | 0.678     | 0.765  | 0.719 | 0.561 | 0.322             | 0.235     | 156.000 | 74.000  | 48.000  | 1396.000 |
| M4_inertia_ridge         | logistic_score_only            | precision_70              | 0.634     | 0.635     | 0.392  | 0.485 | 0.320 | 0.365             | 0.608     | 80.000  | 46.000  | 124.000 | 1424.000 |
| M4_inertia_ridge         | logistic_score_only            | recall_90                 | 0.219     | 0.549     | 0.912  | 0.685 | 0.521 | 0.451             | 0.088     | 186.000 | 153.000 | 18.000  | 1317.000 |
| M7_compact_weather_ridge | logistic_score_only            | best_F1                   | 0.322     | 0.612     | 0.819  | 0.700 | 0.539 | 0.388             | 0.181     | 167.000 | 106.000 | 37.000  | 1364.000 |
| M7_compact_weather_ridge | logistic_score_only            | precision_70              | 0.530     | 0.698     | 0.588  | 0.638 | 0.469 | 0.302             | 0.412     | 120.000 | 52.000  | 84.000  | 1418.000 |

Recommended operating point: selected_candidate_policy from best_F1: threshold=0.309, precision=0.678, recall=0.765, F1=0.719, CSI=0.561.

## 6. Reliability Diagnostics

Fixed probability bins for ge31:

| model_name       | calibrator_id                  | probability_bin | n        | event_count | observed_event_rate | mean_predicted_probability | calibration_gap | low_support |
| ---------------- | ------------------------------ | --------------- | -------- | ----------- | ------------------- | -------------------------- | --------------- | ----------- |
| M4_inertia_ridge | empirical_score_bin            | [0.00,0.10)     | 1229.000 | 18.000      | 0.015               | 0.005                      | -0.009          | 0.000       |
| M4_inertia_ridge | empirical_score_bin            | [0.10,0.20)     | 110.000  | 1.000       | 0.009               | 0.106                      | 0.097           | 0.000       |
| M4_inertia_ridge | empirical_score_bin            | [0.40,0.50)     | 168.000  | 73.000      | 0.435               | 0.434                      | -0.001          | 0.000       |
| M4_inertia_ridge | empirical_score_bin            | [0.60,0.70)     | 160.000  | 112.000     | 0.700               | 0.673                      | -0.027          | 0.000       |
| M4_inertia_ridge | empirical_score_bin            | [0.70,0.80)     | 7.000    | 0.000       | 0.000               | 0.704                      | 0.704           | 1.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.00,0.10)     | 1318.000 | 9.000       | 0.007               | 0.007                      | 0.000           | 0.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.20,0.30)     | 42.000   | 26.000      | 0.619               | 0.286                      | -0.333          | 0.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.30,0.40)     | 84.000   | 13.000      | 0.155               | 0.308                      | 0.153           | 0.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.40,0.50)     | 1.000    | 0.000       | 0.000               | 0.440                      | 0.440           | 1.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.50,0.60)     | 1.000    | 1.000       | 1.000               | 0.553                      | -0.447          | 1.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.60,0.70)     | 129.000  | 82.000      | 0.636               | 0.641                      | 0.006           | 0.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.70,0.80)     | 87.000   | 63.000      | 0.724               | 0.716                      | -0.008          | 0.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.80,0.90)     | 5.000    | 4.000       | 0.800               | 0.830                      | 0.030           | 1.000       |
| M4_inertia_ridge | isotonic_score_only            | [0.90,1.00)     | 7.000    | 6.000       | 0.857               | 0.997                      | 0.140           | 1.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.00,0.10)     | 1283.000 | 9.000       | 0.007               | 0.008                      | 0.001           | 0.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.10,0.20)     | 36.000   | 3.000       | 0.083               | 0.155                      | 0.072           | 0.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.20,0.30)     | 65.000   | 25.000      | 0.385               | 0.244                      | -0.141          | 0.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.30,0.40)     | 42.000   | 5.000       | 0.119               | 0.337                      | 0.217           | 0.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.40,0.50)     | 26.000   | 16.000      | 0.615               | 0.454                      | -0.161          | 1.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.50,0.60)     | 67.000   | 45.000      | 0.672               | 0.552                      | -0.120          | 0.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.60,0.70)     | 70.000   | 42.000      | 0.600               | 0.646                      | 0.046           | 0.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.70,0.80)     | 68.000   | 47.000      | 0.691               | 0.745                      | 0.054           | 0.000       |
| M4_inertia_ridge | logistic_score_hour_diagnostic | [0.80,0.90)     | 17.000   | 12.000      | 0.706               | 0.821                      | 0.115           | 1.000       |
| M4_inertia_ridge | logistic_score_only            | [0.00,0.10)     | 1268.000 | 9.000       | 0.007               | 0.007                      | -0.000          | 0.000       |

Reliability headline: Brier=0.052; PR-AUC=0.610; ECE_fixed=0.018; ECE_quantile=0.022; P05/P50/P95=0.000/0.000/0.702.

Quantile reliability bins were also written with 127 rows.

## 7. Station / Regime Diagnostics

Focus station rows for the selected candidate policy:

| model_name       | output_id           | station_id | n      | event_count | observed_event_rate | mean_output_value | probability_bias | Brier | precision | recall | F1    | false_alarm_ratio | miss_rate |
| ---------------- | ------------------- | ---------- | ------ | ----------- | ------------------- | ----------------- | ---------------- | ----- | --------- | ------ | ----- | ----------------- | --------- |
| M4_inertia_ridge | isotonic_score_only | S139       | 62.000 | 1.000       | 0.016               | 0.122             | 0.106            | 0.069 | 0.111     | 1.000  | 0.200 | 0.889             | 0.000     |
| M4_inertia_ridge | isotonic_score_only | S142       | 62.000 | 15.000      | 0.242               | 0.114             | -0.128           | 0.090 | 1.000     | 0.533  | 0.696 | 0.000             | 0.467     |

Selected candidate policy by radiation and shortwave regimes:

| model_name       | output_id           | regime_variable               | regime_bin            | n       | event_count | observed_event_rate | mean_output_value | probability_bias | precision | recall | F1    | false_alarm_ratio | miss_rate |
| ---------------- | ------------------- | ----------------------------- | --------------------- | ------- | ----------- | ------------------- | ----------------- | ---------------- | --------- | ------ | ----- | ----------------- | --------- |
| M4_inertia_ridge | isotonic_score_only | combined_radiation_hot_regime | highradiation_not_hot | 155.000 | 2.000       | 0.013               | 0.008             | -0.005           | NA        | 0.000  | NA    | NA                | 1.000     |
| M4_inertia_ridge | isotonic_score_only | combined_radiation_hot_regime | hot_not_highradiation | 60.000  | 0.000       | 0.000               | 0.000             | 0.000            | NA        | NA     | NA    | NA                | NA        |
| M4_inertia_ridge | isotonic_score_only | combined_radiation_hot_regime | other                 | 706.000 | 0.000       | 0.000               | 0.000             | 0.000            | NA        | NA     | NA    | NA                | NA        |
| M4_inertia_ridge | isotonic_score_only | combined_radiation_hot_regime | radiation_hot         | 753.000 | 202.000     | 0.268               | 0.269             | 0.001            | 0.678     | 0.772  | 0.722 | 0.322             | 0.228     |
| M4_inertia_ridge | isotonic_score_only | shortwave_3h_mean_bin         | high                  | 419.000 | 53.000      | 0.126               | 0.127             | 0.000            | 0.660     | 0.660  | 0.660 | 0.340             | 0.340     |
| M4_inertia_ridge | isotonic_score_only | shortwave_3h_mean_bin         | low                   | 675.000 | 0.000       | 0.000               | 0.000             | 0.000            | NA        | NA     | NA    | NA                | NA        |
| M4_inertia_ridge | isotonic_score_only | shortwave_3h_mean_bin         | mid                   | 162.000 | 1.000       | 0.006               | 0.006             | -0.000           | NA        | 0.000  | NA    | NA                | 1.000     |
| M4_inertia_ridge | isotonic_score_only | shortwave_3h_mean_bin         | very_high             | 418.000 | 150.000     | 0.359               | 0.359             | -0.000           | 0.684     | 0.807  | 0.740 | 0.316             | 0.193     |
| M4_inertia_ridge | isotonic_score_only | shortwave_bin                 | high                  | 339.000 | 14.000      | 0.041               | 0.041             | -0.001           | 0.000     | 0.000  | NA    | 1.000             | 1.000     |
| M4_inertia_ridge | isotonic_score_only | shortwave_bin                 | low                   | 918.000 | 0.000       | 0.000               | 0.000             | 0.000            | NA        | NA     | NA    | NA                | NA        |
| M4_inertia_ridge | isotonic_score_only | shortwave_bin                 | very_high             | 417.000 | 190.000     | 0.456               | 0.456             | 0.001            | 0.681     | 0.821  | 0.745 | 0.319             | 0.179     |

S142 and S139 remain station diagnostics to review; radiation-hot and very-high shortwave rows are retrospective regime diagnostics only and do not establish a causal mechanism.

## 8. Recommended Calibrated Diagnostic Output

Best probability companion candidate: `M4_inertia_ridge + isotonic_score_only (station_grouped_loso)`.

The deterministic WBGT_A score remains separate from P_ge31. `P_ge31` is a retrospective diagnostic companion conditional on the current OOF score distribution and station-held-out calibration; it is not an official warning probability and not prospective forecast skill.

## 9. Proceed / Hold Decision

Decision: `PASS_CANDIDATE_PROBABILITY_COMPANION`.

Use calibrated P_ge31 as a diagnostic companion in A-L1H evidence notes; keep deterministic WBGT_A score separate. Proceed to A-L1H.3 only if a separately scoped high-tail regression review is opened; do not start A-L2 from this lane.

A-L2 station-context preflight remains out of scope for this lane. High-tail regression remains a separate A-L1H.3 review gate, not an implementation performed here.
