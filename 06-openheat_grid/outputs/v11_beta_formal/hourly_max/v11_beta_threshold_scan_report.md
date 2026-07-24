# v11-β.1 threshold scan report

- Config: `configs\v11\v11_beta_calibration_config_v091_hourly_max.json`
- Predictions: `outputs\v11_beta_formal\hourly_max\v11_beta_oof_predictions.csv`
- Target column: `official_wbgt_c_max`
- Event threshold: ≥ 31.0°C
- CV scheme: loso
- Threshold sweep: [27.0, 34.0] step 0.05

## Operating points (4 per model)

| dataset | model | operating_point | thr (°C) | P | R | F1 | TP | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| hourly_max | M3_weather_ridge | fixed_31 | 31.00 | 0.771 | 0.262 | 0.391 | 313 | 93 | 883 |
| hourly_max | M3_weather_ridge | best_F1 | 29.80 | 0.516 | 0.735 | 0.607 | 879 | 823 | 317 |
| hourly_max | M3_weather_ridge | recall_90 | 28.90 | 0.407 | 0.901 | 0.561 | 1078 | 1570 | 118 |
| hourly_max | M3_weather_ridge | precision_70 | 30.75 | 0.733 | 0.360 | 0.483 | 431 | 157 | 765 |
| hourly_max | M4_inertia_ridge | fixed_31 | 31.00 | 0.763 | 0.302 | 0.433 | 361 | 112 | 835 |
| hourly_max | M4_inertia_ridge | best_F1 | 29.35 | 0.467 | 0.829 | 0.597 | 991 | 1131 | 205 |
| hourly_max | M4_inertia_ridge | recall_90 | 28.70 | 0.400 | 0.906 | 0.555 | 1083 | 1623 | 113 |
| hourly_max | M4_inertia_ridge | precision_70 | 30.75 | 0.701 | 0.431 | 0.534 | 516 | 220 | 680 |
| hourly_max | M5_v10_morphology_ridge | fixed_31 | 31.00 | 0.788 | 0.270 | 0.402 | 323 | 87 | 873 |
| hourly_max | M5_v10_morphology_ridge | best_F1 | 29.40 | 0.471 | 0.826 | 0.600 | 988 | 1108 | 208 |
| hourly_max | M5_v10_morphology_ridge | recall_90 | 28.90 | 0.427 | 0.905 | 0.580 | 1082 | 1451 | 114 |
| hourly_max | M5_v10_morphology_ridge | precision_70 | 30.85 | 0.719 | 0.344 | 0.466 | 412 | 161 | 784 |
| hourly_max | M7_compact_weather_ridge | fixed_31 | 31.00 | 0.788 | 0.270 | 0.402 | 323 | 87 | 873 |
| hourly_max | M7_compact_weather_ridge | best_F1 | 29.40 | 0.471 | 0.826 | 0.600 | 988 | 1108 | 208 |
| hourly_max | M7_compact_weather_ridge | recall_90 | 28.90 | 0.427 | 0.905 | 0.580 | 1082 | 1451 | 114 |
| hourly_max | M7_compact_weather_ridge | precision_70 | 30.85 | 0.719 | 0.344 | 0.466 | 412 | 161 | 784 |

## Notes

- `fixed_31` is the canonical operational semantics: predicted WBGT ≥ 31.0°C → flag the hour. No threshold tuning required at deployment.
- `best_F1` is post-hoc; report it as a tuned upper bound, not the operational target.
- `recall_90` and `precision_70` answer 'how high can the other metric go if I commit to this floor'.