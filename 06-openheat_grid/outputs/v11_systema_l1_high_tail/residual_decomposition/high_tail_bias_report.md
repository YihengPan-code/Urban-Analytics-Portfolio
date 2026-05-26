# System A A-L1H.0 High-Tail Residual Decomposition

Generated: 2026-05-26

## Input Source Selected

- File path: `outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv`
- Model(s): `M4_inertia_ridge, M7_compact_weather_ridge`
- Target: `official_wbgt_c_max` normalized to `official_wbgt_c`
- Model score: `prediction_wbgt_c` normalized to `model_score`
- Row count: 6696 selected model rows
- Station count: 27
- Timestamp span: 2026-05-07 02:00:00+08:00 to 2026-05-11 04:00:00+08:00

## Residual Sign Convention

`residual_c = official_wbgt_c - model_score`. Positive residuals mean System A underprediction against the official WBGT target in this diagnostic input.

## ge31 Fixed-Threshold Summary

- Observed ge31 count: 408
- Predicted ge31 count: 290
- Hits / misses / false alarms: 194 / 214 / 96
- Fixed_31 precision / recall / F1: 0.669 / 0.475 / 0.556

These are fixed-threshold OOF diagnostics only; `P_ge31` is not treated as an official warning probability here.

## High-Tail Compression Diagnostics

Residual by observed bin, primary model:

| model_name       | observed_wbgt_bin   |    n |   n_obs_ge31 |   n_pred_ge31 |   n_ge31_hit |   n_ge31_miss |   n_ge31_false_alarm |   mean_official_wbgt_c |   mean_model_score |   mean_residual_c |   median_residual_c |   p75_residual_c |   p90_residual_c |   mean_abs_error_c |   p90_abs_error_c |   max_abs_error_c |
|:-----------------|:--------------------|-----:|-------------:|--------------:|-------------:|--------------:|---------------------:|-----------------------:|-------------------:|------------------:|--------------------:|-----------------:|-----------------:|-------------------:|------------------:|------------------:|
| M4_inertia_ridge | 28-29               |  188 |            0 |             5 |            0 |             0 |                    5 |                28.4979 |            28.9381 |         -0.44021  |         -0.406722   |         0.31856  |         1.07483  |           0.97776  |           1.91481 |           3.46088 |
| M4_inertia_ridge | 29-30               |  226 |            0 |            26 |            0 |             0 |                   26 |                29.5142 |            29.5328 |         -0.01861  |         -0.00576803 |         0.648868 |         1.16987  |           0.825305 |           1.72506 |           3.72901 |
| M4_inertia_ridge | 30-31               |  280 |            0 |            65 |            0 |             0 |                   65 |                30.4486 |            30.0951 |          0.353463 |          0.14111    |         1.17516  |         1.76995  |           0.845886 |           1.76995 |           3.84701 |
| M4_inertia_ridge | 31-32               |  268 |          268 |           135 |          135 |           133 |                    0 |                31.3679 |            30.7462 |          0.621746 |          0.416469   |         1.188    |         1.81402  |           0.809238 |           1.81402 |           3.53275 |
| M4_inertia_ridge | 32-33               |  110 |          110 |            46 |           46 |            64 |                    0 |                32.3582 |            30.7373 |          1.6209   |          1.6072     |         2.02377  |         2.51755  |           1.6209   |           2.51755 |           3.60534 |
| M4_inertia_ridge | <28                 | 2246 |            0 |             0 |            0 |             0 |                    0 |                26.0836 |            26.1231 |         -0.039469 |         -0.00445821 |         0.482193 |         0.863928 |           0.603284 |           1.26822 |           3.82484 |
| M4_inertia_ridge | >=33                |   30 |           30 |            13 |           13 |            17 |                    0 |                33.34   |            30.8571 |          2.48287  |          2.34849    |         3.16759  |         3.33545  |           2.48287  |           3.33545 |           3.9508  |

Residual by predicted bin, primary model:

| model_name       | predicted_score_bin   |    n |   n_obs_ge31 |   n_pred_ge31 |   n_ge31_hit |   n_ge31_miss |   n_ge31_false_alarm |   mean_official_wbgt_c |   mean_model_score |   mean_residual_c |   median_residual_c |   p75_residual_c |   p90_residual_c |   mean_abs_error_c |   p90_abs_error_c |   max_abs_error_c |
|:-----------------|:----------------------|-----:|-------------:|--------------:|-------------:|--------------:|---------------------:|-----------------------:|-------------------:|------------------:|--------------------:|-----------------:|-----------------:|-------------------:|------------------:|------------------:|
| M4_inertia_ridge | 28-29                 |  264 |           13 |             0 |            0 |            13 |                    0 |                28.7383 |            28.5669 |         0.171363  |           0.0501475 |        1.19742   |         1.87452  |           1.12939  |           2.12025 |           3.53275 |
| M4_inertia_ridge | 29-30                 |  262 |           44 |             0 |            0 |            44 |                    0 |                29.7359 |            29.4789 |         0.256984  |           0.213619  |        1.01866   |         1.94854  |           1.00402  |           2.11101 |           3.75404 |
| M4_inertia_ridge | 30-30.5               |  172 |           70 |             0 |            0 |            70 |                    0 |                30.6087 |            30.2349 |         0.373805  |           0.385447  |        1.50311   |         2.12715  |           1.18448  |           2.26693 |           3.9508  |
| M4_inertia_ridge | 30.5-31               |  165 |           87 |             0 |            0 |            87 |                    0 |                31.0012 |            30.7516 |         0.249637  |           0.237687  |        1.07377   |         1.67063  |           0.976043 |           2.07819 |           3.46743 |
| M4_inertia_ridge | 31-32                 |  284 |          188 |           284 |          188 |             0 |                   96 |                31.188  |            31.332  |        -0.144004  |          -0.171555  |        0.477399  |         1.18933  |           0.785896 |           1.68938 |           3.46088 |
| M4_inertia_ridge | 32-33                 |    6 |            6 |             6 |            6 |             0 |                    0 |                31.6    |            32.0552 |        -0.455173  |          -0.563054  |        0.0165562 |         0.22653  |           0.606193 |           1.029   |           1.07372 |
| M4_inertia_ridge | <28                   | 2195 |            0 |             0 |            0 |             0 |                    0 |                26.1042 |            26.0275 |         0.0766944 |           0.0678004 |        0.547687  |         0.987179 |           0.582689 |           1.22482 |           3.84701 |

Observed ge31 rows by predicted score bin, primary model:

| predicted_score_bin   |   observed_ge31_rows |
|:----------------------|---------------------:|
| 31-32                 |                  188 |
| 30.5-31               |                   87 |
| 30-30.5               |                   70 |
| 29-30                 |                   44 |
| 28-29                 |                   13 |
| 32-33                 |                    6 |

For M4_inertia_ridge, 49.3% of observed ge31 rows fall in predicted 29-31 bins; station mean-residual range is 1.17 C; weather regimes are limited by absent weather columns.

## Station Diagnostics

Top positive residual stations, primary model:

| station_id   |   n |   n_obs_ge31 |   n_ge31_miss |   mean_residual_c |   high_tail_obs_ge31_mean_residual_c |
|:-------------|----:|-------------:|--------------:|------------------:|-------------------------------------:|
| S142         | 124 |           30 |            21 |          0.859364 |                             2.45348  |
| S137         | 124 |           26 |            18 |          0.858892 |                             1.64677  |
| S129         | 124 |           20 |            11 |          0.499745 |                             1.04313  |
| S141         | 124 |           20 |            12 |          0.461225 |                             1.67792  |
| S127         | 124 |           20 |             9 |          0.441096 |                             0.712466 |

Top negative residual stations, primary model:

| station_id   |   n |   n_obs_ge31 |   n_ge31_miss |   mean_residual_c |   high_tail_obs_ge31_mean_residual_c |
|:-------------|----:|-------------:|--------------:|------------------:|-------------------------------------:|
| S146         | 124 |            6 |             3 |         -0.309086 |                            0.281668  |
| S139         | 124 |            2 |             2 |         -0.278285 |                            0.829803  |
| S150         | 124 |            6 |             4 |         -0.273722 |                            0.656435  |
| S149         | 124 |           10 |             5 |         -0.236832 |                            0.491877  |
| S140         | 124 |            8 |             2 |         -0.229286 |                           -0.0294034 |

S142 / S139 notes:

| station_id   |   n |   n_obs_ge31 |   n_ge31_miss |   mean_residual_c |   high_tail_obs_ge31_mean_residual_c |
|:-------------|----:|-------------:|--------------:|------------------:|-------------------------------------:|
| S142         | 124 |           30 |            21 |          0.859364 |                             2.45348  |
| S139         | 124 |            2 |             2 |         -0.278285 |                             0.829803 |

## Weather-Regime Diagnostics

No configured weather-regime source columns were present in the selected OOF file, so weather-regime decomposition is limited for A-L1H.0.

| model_name       | regime_variable   | regime_bin             |    n |   n_obs_ge31 |   n_pred_ge31 |   n_ge31_hit |   n_ge31_miss |   n_ge31_false_alarm |   mean_official_wbgt_c |   mean_model_score |   mean_residual_c |   median_residual_c |   p75_residual_c |   p90_residual_c |   mean_abs_error_c |   p90_abs_error_c |   max_abs_error_c |
|:-----------------|:------------------|:-----------------------|-----:|-------------:|--------------:|-------------:|--------------:|---------------------:|-----------------------:|-------------------:|------------------:|--------------------:|-----------------:|-----------------:|-------------------:|------------------:|------------------:|
| M4_inertia_ridge | no_weather_regime | weather_columns_absent | 3348 |          408 |           290 |          194 |           214 |                   96 |                  27.51 |            27.4076 |          0.102381 |           0.0642255 |         0.642091 |          1.30203 |           0.726351 |           1.58829 |            3.9508 |

## Preliminary Classification

mixed: global Level 1 score compression with station-specific residual bias

This is a diagnostic classification from existing OOF scores, not final proof of mechanism and not prospective forecast skill.

## Next Recommended Action

Recommend a staged review: first confirm score-compression evidence, then decide between A-L1H.1 formula-v2, A-L1H.2 probability calibration, A-L1H.3 high-tail regression review gate, and A-L2 station-context preflight. Do not launch one large model change.

## Claim Boundaries

- This remains a retrospective OOF diagnostic for WBGT_A temporal heat-stress scoring.
- It is not validated local 100m WBGT prediction and not an operational prospective forecast skill claim.
- ge33 rows are exploratory only.
