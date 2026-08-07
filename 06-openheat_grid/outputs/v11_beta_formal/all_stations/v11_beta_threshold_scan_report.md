# v11-β.1 threshold scan report

- Config: `configs\v11\v11_beta_calibration_config_v091.json`
- Predictions: `outputs\v11_beta_formal\all_stations\v11_beta_oof_predictions.csv`
- Target column: `official_wbgt_c`
- Event threshold: ≥ 31.0°C
- CV scheme: loso
- Threshold sweep: [27.0, 34.0] step 0.05

## Operating points (4 per model)

| dataset | model | operating_point | thr (°C) | P | R | F1 | TP | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| all_stations | M3_weather_ridge | fixed_31 | 31.00 | 0.686 | 0.049 | 0.092 | 140 | 64 | 2704 |
| all_stations | M3_weather_ridge | best_F1 | 29.95 | 0.451 | 0.504 | 0.476 | 1434 | 1743 | 1410 |
| all_stations | M3_weather_ridge | recall_90 | 28.45 | 0.259 | 0.902 | 0.402 | 2566 | 7355 | 278 |
| all_stations | M3_weather_ridge | precision_70 | 31.50 | 1.000 | 0.000 | 0.001 | 1 | 0 | 2843 |
| all_stations | M4_inertia_ridge | fixed_31 | 31.00 | 0.647 | 0.076 | 0.136 | 216 | 118 | 2628 |
| all_stations | M4_inertia_ridge | best_F1 | 29.85 | 0.423 | 0.590 | 0.493 | 1679 | 2293 | 1165 |
| all_stations | M4_inertia_ridge | recall_90 | 28.45 | 0.271 | 0.901 | 0.417 | 2563 | 6892 | 281 |
| all_stations | M4_inertia_ridge | precision_70 | 31.35 | 0.740 | 0.013 | 0.026 | 37 | 13 | 2807 |
| all_stations | M5_v10_morphology_ridge | fixed_31 | 31.00 | 0.640 | 0.057 | 0.105 | 162 | 91 | 2682 |
| all_stations | M5_v10_morphology_ridge | best_F1 | 29.50 | 0.368 | 0.687 | 0.480 | 1955 | 3351 | 889 |
| all_stations | M5_v10_morphology_ridge | recall_90 | 28.40 | 0.264 | 0.901 | 0.409 | 2563 | 7141 | 281 |
| all_stations | M5_v10_morphology_ridge | precision_70 | 31.55 | 1.000 | 0.000 | 0.001 | 1 | 0 | 2843 |
| all_stations | M7_compact_weather_ridge | fixed_31 | 31.00 | 0.640 | 0.057 | 0.105 | 162 | 91 | 2682 |
| all_stations | M7_compact_weather_ridge | best_F1 | 29.50 | 0.368 | 0.687 | 0.480 | 1955 | 3351 | 889 |
| all_stations | M7_compact_weather_ridge | recall_90 | 28.40 | 0.264 | 0.901 | 0.409 | 2563 | 7141 | 281 |
| all_stations | M7_compact_weather_ridge | precision_70 | 31.55 | 1.000 | 0.000 | 0.001 | 1 | 0 | 2843 |

## Notes

- `fixed_31` is the canonical operational semantics: predicted WBGT ≥ 31.0°C → flag the hour. No threshold tuning required at deployment.
- `best_F1` is post-hoc; report it as a tuned upper bound, not the operational target.
- `recall_90` and `precision_70` answer 'how high can the other metric go if I commit to this floor'.