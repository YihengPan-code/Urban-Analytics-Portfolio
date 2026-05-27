# System A A-L1H.4 Probabilistic / Exceedance Companion Suite

Generated: 2026-05-27
Decision status: `A_L1H4_COMPANION_PROMISING`
Branch: `codex/systema-l1h4-prob-exceedance-suite`

## 1. Why This Follows A-L2.1c

A-L2.1c found only a weak station-context high-tail residual signal and did not identify score residual correction. This suite therefore returns to Level 1 threshold behavior rather than creating station-adjusted WBGT or local WBGT.

## 2. Why Level 1 Remains The Main Improvement Path

The current evidence supports improving threshold companions around WBGT_A: P_ge31, expected exceedance, and uncertainty intervals. These are companion diagnostics, not canonical replacements for deterministic WBGT_A.

## 3. Input Inventory And Targets

| inventory_role                   | path                                                                                                     | exists | rows_total | rows_selected_loso | selected_station_count | selected_event_count_ge31 | selected_event_count_ge33 |
| -------------------------------- | -------------------------------------------------------------------------------------------------------- | ------ | ---------- | ------------------ | ---------------------- | ------------------------- | ------------------------- |
| residual_weather_merge           | outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv | 1.000  | 6696.000   | 1674.000           | 27.000                 | 204.000                   | 15.000                    |
| beta_oof_predictions             | outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv                                     | 1.000  | 30132.000  | NA                 | NA                     | NA                        | NA                        |
| probability_predictions_oof      | outputs/v11_systema_l1_high_tail/probability_threshold_calibration/probability_predictions_oof.csv.gz    | 1.000  | 33356.000  | NA                 | NA                     | NA                        | NA                        |
| high_tail_challenger_predictions | outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_oof_predictions.csv.gz                  | 1.000  | 10044.000  | NA                 | NA                     | NA                        | NA                        |
| l2_status                        | outputs/v11_systema_l2_residual/scoped_residual_preflight/A_L2_1C_STATUS.md                              | 1.000  | 0.000      | NA                 | NA                     | NA                        | NA                        |
| l2_report                        | outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_residual_preflight_report.md         | 1.000  | 0.000      | NA                 | NA                     | NA                        | NA                        |

Targets: official_wbgt_c, ge31=official_wbgt_c>=31, ge33=official_wbgt_c>=33, exceedance_ge31_c=max(0, official_wbgt_c-31), exceedance_ge33_c=max(0, official_wbgt_c-33).

## 4. Validation Split Design

| validation_method    | fold_id | is_primary | train_rows | test_rows | test_station_ids | test_events_ge31 | test_events_ge33 |
| -------------------- | ------- | ---------- | ---------- | --------- | ---------------- | ---------------- | ---------------- |
| station_grouped_loso | S124    | 1.000      | 1612.000   | 62.000    | S124             | 0.000            | 0.000            |
| station_grouped_loso | S125    | 1.000      | 1612.000   | 62.000    | S125             | 8.000            | 0.000            |
| station_grouped_loso | S126    | 1.000      | 1612.000   | 62.000    | S126             | 8.000            | 0.000            |
| station_grouped_loso | S127    | 1.000      | 1612.000   | 62.000    | S127             | 10.000           | 0.000            |
| station_grouped_loso | S128    | 1.000      | 1612.000   | 62.000    | S128             | 11.000           | 2.000            |
| station_grouped_loso | S129    | 1.000      | 1612.000   | 62.000    | S129             | 10.000           | 0.000            |
| station_grouped_loso | S130    | 1.000      | 1612.000   | 62.000    | S130             | 6.000            | 0.000            |
| station_grouped_loso | S132    | 1.000      | 1612.000   | 62.000    | S132             | 9.000            | 0.000            |
| station_grouped_loso | S135    | 1.000      | 1612.000   | 62.000    | S135             | 11.000           | 0.000            |
| station_grouped_loso | S137    | 1.000      | 1612.000   | 62.000    | S137             | 13.000           | 2.000            |
| station_grouped_loso | S139    | 1.000      | 1612.000   | 62.000    | S139             | 1.000            | 0.000            |
| station_grouped_loso | S140    | 1.000      | 1612.000   | 62.000    | S140             | 4.000            | 0.000            |
| station_grouped_loso | S141    | 1.000      | 1612.000   | 62.000    | S141             | 10.000           | 2.000            |
| station_grouped_loso | S142    | 1.000      | 1612.000   | 62.000    | S142             | 15.000           | 7.000            |
| station_grouped_loso | S143    | 1.000      | 1612.000   | 62.000    | S143             | 7.000            | 0.000            |
| station_grouped_loso | S144    | 1.000      | 1612.000   | 62.000    | S144             | 8.000            | 1.000            |

Standardized logistic-regression companions use fixed, disclosed hyperparameters (`C=1.0`, no class weighting) with the repo's dependency-free solver because sklearn estimator fits hard-exit in this runtime; LOSO remains the primary validation evidence.

## 5. Deterministic Baseline

| sensitivity_id | validation_method    | output_id          | n        | MAE   | RMSE  | high_tail_mae_obs_ge31 | fixed_ge31_recall | fixed_ge31_precision | fixed_ge31_miss_rate |
| -------------- | -------------------- | ------------------ | -------- | ----- | ----- | ---------------------- | ----------------- | -------------------- | -------------------- |
| all            | blocked_time         | m7_compact_weather | 1674.000 | 0.813 | 1.103 | 1.296                  | 0.559             | 0.585                | 0.441                |
| all            | blocked_time         | v09_proxy          | 1674.000 | 1.472 | 2.095 | 4.277                  | 0.000             | NA                   | 1.000                |
| all            | blocked_time         | wbgt_a_m4          | 1674.000 | 0.814 | 1.058 | 1.307                  | 0.363             | 0.649                | 0.637                |
| no_s142_eval   | blocked_time         | m7_compact_weather | 1612.000 | 0.808 | 1.092 | 1.229                  | 0.566             | 0.569                | 0.434                |
| no_s142_eval   | blocked_time         | v09_proxy          | 1612.000 | 1.449 | 2.051 | 4.175                  | 0.000             | NA                   | 1.000                |
| no_s142_eval   | blocked_time         | wbgt_a_m4          | 1612.000 | 0.802 | 1.034 | 1.203                  | 0.376             | 0.640                | 0.624                |
| all            | station_grouped_loso | m7_compact_weather | 1674.000 | 0.682 | 0.912 | 1.109                  | 0.574             | 0.722                | 0.426                |
| all            | station_grouped_loso | v09_proxy          | 1674.000 | 1.472 | 2.095 | 4.277                  | 0.000             | NA                   | 1.000                |
| all            | station_grouped_loso | wbgt_a_m4          | 1674.000 | 0.639 | 0.862 | 0.995                  | 0.588             | 0.682                | 0.412                |
| no_s142_eval   | station_grouped_loso | m7_compact_weather | 1612.000 | 0.673 | 0.892 | 1.016                  | 0.587             | 0.712                | 0.413                |
| no_s142_eval   | station_grouped_loso | v09_proxy          | 1612.000 | 1.449 | 2.051 | 4.175                  | 0.000             | NA                   | 1.000                |
| no_s142_eval   | station_grouped_loso | wbgt_a_m4          | 1612.000 | 0.628 | 0.840 | 0.893                  | 0.603             | 0.671                | 0.397                |

## 6. Threshold Policies

| companion_id                  | output_kind | operating_point | threshold | precision | recall | F1    | CSI   | false_alarm_ratio | miss_rate |
| ----------------------------- | ----------- | --------------- | --------- | --------- | ------ | ----- | ----- | ----------------- | --------- |
| isotonic_m4_score_ge31        | probability | best_F1         | 0.446     | 0.678     | 0.765  | 0.719 | 0.561 | 0.322             | 0.235     |
| isotonic_m4_score_ge31        | probability | precision70     | 0.654     | 0.673     | 0.363  | 0.471 | 0.308 | 0.327             | 0.637     |
| isotonic_m4_score_ge31        | probability | recall90        | 0.212     | 0.545     | 0.946  | 0.692 | 0.529 | 0.455             | 0.054     |
| logistic_P_ge31_safe_features | probability | best_F1         | 0.433     | 0.643     | 0.760  | 0.697 | 0.534 | 0.357             | 0.240     |
| logistic_P_ge31_safe_features | probability | precision70     | 0.521     | 0.696     | 0.696  | 0.696 | 0.534 | 0.304             | 0.304     |
| logistic_P_ge31_safe_features | probability | recall90        | 0.186     | 0.508     | 0.902  | 0.650 | 0.482 | 0.492             | 0.098     |
| m7_compact_weather_score      | score       | best_F1         | 30.248    | 0.618     | 0.833  | 0.710 | 0.550 | 0.382             | 0.167     |
| m7_compact_weather_score      | score       | fixed_31        | 31.000    | 0.722     | 0.574  | 0.639 | 0.470 | 0.278             | 0.426     |
| m7_compact_weather_score      | score       | precision70     | 30.870    | 0.699     | 0.593  | 0.642 | 0.473 | 0.301             | 0.407     |
| m7_compact_weather_score      | score       | recall90        | 29.250    | 0.492     | 0.917  | 0.640 | 0.471 | 0.508             | 0.083     |
| platt_m4_score_ge31           | probability | best_F1         | 0.440     | 0.665     | 0.760  | 0.709 | 0.550 | 0.335             | 0.240     |
| platt_m4_score_ge31           | probability | precision70     | 0.675     | 0.407     | 0.108  | 0.171 | 0.093 | 0.593             | 0.892     |
| platt_m4_score_ge31           | probability | recall90        | 0.290     | 0.552     | 0.907  | 0.686 | 0.523 | 0.448             | 0.093     |
| prior_l1h2_m4_isotonic        | probability | best_F1         | 0.446     | 0.678     | 0.765  | 0.719 | 0.561 | 0.322             | 0.235     |
| prior_l1h2_m4_isotonic        | probability | precision70     | 0.654     | 0.673     | 0.363  | 0.471 | 0.308 | 0.327             | 0.637     |
| prior_l1h2_m4_isotonic        | probability | recall90        | 0.212     | 0.545     | 0.946  | 0.692 | 0.529 | 0.455             | 0.054     |
| v09_proxy_score               | score       | best_F1         | 26.850    | 0.423     | 0.868  | 0.569 | 0.398 | 0.577             | 0.132     |
| v09_proxy_score               | score       | fixed_31        | 31.000    | NA        | 0.000  | NA    | 0.000 | NA                | 1.000     |
| v09_proxy_score               | score       | precision70     | 27.791    | 0.709     | 0.358  | 0.476 | 0.312 | 0.291             | 0.642     |
| v09_proxy_score               | score       | recall90        | 26.659    | 0.336     | 0.912  | 0.491 | 0.326 | 0.664             | 0.088     |
| wbgt_a_m4_score               | score       | best_F1         | 30.700    | 0.683     | 0.770  | 0.724 | 0.567 | 0.317             | 0.230     |
| wbgt_a_m4_score               | score       | fixed_31        | 31.000    | 0.682     | 0.588  | 0.632 | 0.462 | 0.318             | 0.412     |
| wbgt_a_m4_score               | score       | precision70     | 31.183    | 0.658     | 0.377  | 0.480 | 0.316 | 0.342             | 0.623     |
| wbgt_a_m4_score               | score       | recall90        | 30.006    | 0.542     | 0.917  | 0.681 | 0.517 | 0.458             | 0.083     |

## 7. P_ge31 / P_ge33 Models

| companion_id                  | status    | n        | event_count | Brier | log_loss | PR_AUC | ROC_AUC | ECE_fixed | ECE_quantile | calibration_slope |
| ----------------------------- | --------- | -------- | ----------- | ----- | -------- | ------ | ------- | --------- | ------------ | ----------------- |
| isotonic_m4_score_ge31        | evaluated | 1674.000 | 204.000     | 0.052 | 0.170    | 0.610  | 0.947   | 0.018     | 0.022        | 0.745             |
| prior_l1h2_m4_isotonic        | evaluated | 1674.000 | 204.000     | 0.052 | 0.170    | 0.610  | 0.947   | 0.018     | 0.022        | 0.745             |
| logistic_P_ge31_safe_features | evaluated | 1674.000 | 204.000     | 0.054 | 0.170    | 0.684  | 0.956   | 0.030     | 0.013        | 1.147             |
| platt_m4_score_ge31           | evaluated | 1674.000 | 204.000     | 0.057 | 0.176    | 0.652  | 0.954   | 0.026     | 0.022        | 1.411             |

P_ge33 is gated by event support and remains exploratory when below threshold.

## 8. Expected Exceedance

| companion_id                    | exceedance_MAE | positive_exceedance_MAE | bias_expected_minus_observed | p90_abs_exceedance_error |
| ------------------------------- | -------------- | ----------------------- | ---------------------------- | ------------------------ |
| deterministic_score_gap_m4_ge31 | 0.100          | 0.779                   | -0.058                       | 0.288                    |
| two_part_best_p_ridge_ge31      | 0.114          | 0.592                   | 0.009                        | 0.464                    |
| direct_ridge_ge31               | 0.130          | 0.611                   | 0.013                        | 0.369                    |

## 9. Quantile / Interval Companion

| interval_id           | nominal_coverage | empirical_coverage | mean_interval_width_c | near31_coverage | near33_coverage |
| --------------------- | ---------------- | ------------------ | --------------------- | --------------- | --------------- |
| conformal_m4_residual | 0.800            | 0.799              | 1.985                 | 0.806           | 0.067           |
| conformal_m4_residual | 0.900            | 0.898              | 2.869                 | 0.885           | 0.133           |

## 10. Station Diagnostics And S142 Caveat

| companion_id           | operating_point | station_id | event_count_ge31 | precision | recall | miss_rate | false_alarm_ratio |
| ---------------------- | --------------- | ---------- | ---------------- | --------- | ------ | --------- | ----------------- |
| isotonic_m4_score_ge31 | best_F1         | S139       | 1.000            | 0.111     | 1.000  | 0.000     | 0.889             |
| isotonic_m4_score_ge31 | best_F1         | S142       | 15.000           | 1.000     | 0.533  | 0.467     | 0.000             |
| isotonic_m4_score_ge31 | precision70     | S139       | 1.000            | 0.111     | 1.000  | 0.000     | 0.889             |
| isotonic_m4_score_ge31 | precision70     | S142       | 15.000           | 1.000     | 0.133  | 0.867     | 0.000             |
| isotonic_m4_score_ge31 | recall90        | S139       | 1.000            | 0.083     | 1.000  | 0.000     | 0.917             |
| isotonic_m4_score_ge31 | recall90        | S142       | 15.000           | 0.929     | 0.867  | 0.133     | 0.071             |
| wbgt_a_m4_score        | best_F1         | S139       | 1.000            | 0.111     | 1.000  | 0.000     | 0.889             |
| wbgt_a_m4_score        | best_F1         | S142       | 15.000           | 1.000     | 0.533  | 0.467     | 0.000             |
| wbgt_a_m4_score        | fixed_31        | S139       | 1.000            | 0.000     | 0.000  | 1.000     | 1.000             |
| wbgt_a_m4_score        | fixed_31        | S142       | 15.000           | 1.000     | 0.400  | 0.600     | 0.000             |
| wbgt_a_m4_score        | precision70     | S139       | 1.000            | 0.111     | 1.000  | 0.000     | 0.889             |
| wbgt_a_m4_score        | precision70     | S142       | 15.000           | 1.000     | 0.133  | 0.867     | 0.000             |
| wbgt_a_m4_score        | recall90        | S139       | 1.000            | 0.083     | 1.000  | 0.000     | 0.917             |
| wbgt_a_m4_score        | recall90        | S142       | 15.000           | 1.000     | 0.733  | 0.267     | 0.000             |

S142: n_ge31=15, recall=0.533, miss_rate=0.467, false_alarm_ratio=0.000; S139: n_ge31=1, recall=1.000, miss_rate=0.000, false_alarm_ratio=0.889. Station diagnostics remain caveats, not station corrections.

## 11. Decision Matrix

| criterion                     | status      | detail                                                                                                                                               |
| ----------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| primary_threshold_recall_miss | PASS        | isotonic_m4_score_ge31 best_F1 vs WBGT_A fixed_31: recall 0.588->0.765 (delta 0.176), precision 0.682->0.678 (delta -0.004), miss_rate 0.412->0.235. |
| false_alarm_precision_control | PASS        | precision=0.678; false_alarm_ratio=0.322.                                                                                                            |
| probability_calibration       | PASS        | isotonic_m4_score_ge31 Brier=0.052, ECE_fixed=0.018, PR-AUC=0.610, best_F1 threshold=0.446.                                                          |
| no_s142_sensitivity           | PASS        | no-S142 recall delta vs fixed_31=0.180.                                                                                                              |
| blocked_time_secondary        | PASS        | blocked-time recall delta vs fixed_31=0.358.                                                                                                         |
| ge33_support                  | LOW_SUPPORT | P_ge33 remains exploratory and is not promoted.                                                                                                      |
| expected_exceedance_available | PASS        | Expected exceedance metrics are available for score-gap/direct/two-part companions.                                                                  |
| interval_available            | PASS        | Interval metrics are available for conformal and quantile companions where runtime support exists.                                                   |
| claim_boundary                | PASS        | Companion only; no station-adjusted WBGT, no local 100m WBGT, no System B coupling output, no risk/hazard score.                                     |

## 12. Output Contract Draft

Keep WBGT_A as primary; add P_ge31, expected exceedance, and interval columns as optional companion diagnostics only.

## 13. Claim Boundaries

- No station-adjusted WBGT.
- No local 100 m WBGT.
- No System B coupling output.
- No risk score or hazard score.
- Companion only unless promoted by a later model card.
