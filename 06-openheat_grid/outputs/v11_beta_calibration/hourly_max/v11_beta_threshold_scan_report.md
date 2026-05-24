# v11-β.1 threshold scan report

- Config: `configs\v11\v11_beta_calibration_config_v091_hourly_max.json`
- Predictions: `outputs\v11_beta_calibration\hourly_max\v11_beta_oof_predictions.csv`
- Target column: `official_wbgt_c_max`
- Event threshold: ≥ 31.0°C
- CV scheme: loso
- Threshold sweep: [27.0, 34.0] step 0.05

## Operating points (4 per model)

| dataset | model | operating_point | thr (°C) | P | R | F1 | TP | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| hourly_max | M3_weather_ridge | fixed_31 | 31.00 | 0.673 | 0.515 | 0.583 | 105 | 51 | 99 |
| hourly_max | M3_weather_ridge | best_F1 | 30.20 | 0.603 | 0.917 | 0.728 | 187 | 123 | 17 |
| hourly_max | M3_weather_ridge | recall_90 | 30.20 | 0.603 | 0.917 | 0.728 | 187 | 123 | 17 |
| hourly_max | M3_weather_ridge | precision_70 | 31.20 | 0.701 | 0.299 | 0.419 | 61 | 26 | 143 |
| hourly_max | M4_inertia_ridge | fixed_31 | 31.00 | 0.682 | 0.588 | 0.632 | 120 | 56 | 84 |
| hourly_max | M4_inertia_ridge | best_F1 | 30.70 | 0.683 | 0.770 | 0.724 | 157 | 73 | 47 |
| hourly_max | M4_inertia_ridge | recall_90 | 30.00 | 0.549 | 0.936 | 0.692 | 191 | 157 | 13 |
| hourly_max | M4_inertia_ridge | precision_70 | 31.20 | 0.703 | 0.382 | 0.495 | 78 | 33 | 126 |
| hourly_max | M5_v10_morphology_ridge | fixed_31 | 31.00 | 0.722 | 0.574 | 0.639 | 117 | 45 | 87 |
| hourly_max | M5_v10_morphology_ridge | best_F1 | 30.25 | 0.620 | 0.833 | 0.711 | 170 | 104 | 34 |
| hourly_max | M5_v10_morphology_ridge | recall_90 | 29.25 | 0.492 | 0.917 | 0.640 | 187 | 193 | 17 |
| hourly_max | M5_v10_morphology_ridge | precision_70 | 30.90 | 0.713 | 0.583 | 0.642 | 119 | 48 | 85 |
| hourly_max | M7_compact_weather_ridge | fixed_31 | 31.00 | 0.722 | 0.574 | 0.639 | 117 | 45 | 87 |
| hourly_max | M7_compact_weather_ridge | best_F1 | 30.25 | 0.620 | 0.833 | 0.711 | 170 | 104 | 34 |
| hourly_max | M7_compact_weather_ridge | recall_90 | 29.25 | 0.492 | 0.917 | 0.640 | 187 | 193 | 17 |
| hourly_max | M7_compact_weather_ridge | precision_70 | 30.90 | 0.713 | 0.583 | 0.642 | 119 | 48 | 85 |

## Notes

- `fixed_31` is the canonical operational semantics: predicted WBGT ≥ 31.0°C → flag the hour. No threshold tuning required at deployment.
- `best_F1` is post-hoc; report it as a tuned upper bound, not the operational target.
- `recall_90` and `precision_70` answer 'how high can the other metric go if I commit to this floor'.