# v11-β.1 threshold scan report

- Config: `configs\v11\v11_beta_calibration_config_v091.json`
- Predictions: `outputs\v11_beta_calibration\all_stations\v11_beta_oof_predictions.csv`
- Target column: `official_wbgt_c`
- Event threshold: ≥ 31.0°C
- CV scheme: loso
- Threshold sweep: [27.0, 34.0] step 0.05

## Operating points (4 per model)

| dataset | model | operating_point | thr (°C) | P | R | F1 | TP | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| all_stations | M3_weather_ridge | fixed_31 | 31.00 | 0.426 | 0.059 | 0.104 | 26 | 35 | 411 |
| all_stations | M3_weather_ridge | best_F1 | 30.00 | 0.419 | 0.828 | 0.557 | 362 | 501 | 75 |
| all_stations | M3_weather_ridge | recall_90 | 29.60 | 0.367 | 0.911 | 0.523 | 398 | 687 | 39 |
| all_stations | M3_weather_ridge | precision_70 | — | — | — | — | — | — | — |
| all_stations | M4_inertia_ridge | fixed_31 | 31.00 | 0.421 | 0.158 | 0.230 | 69 | 95 | 368 |
| all_stations | M4_inertia_ridge | best_F1 | 30.00 | 0.422 | 0.822 | 0.558 | 359 | 491 | 78 |
| all_stations | M4_inertia_ridge | recall_90 | 29.60 | 0.380 | 0.920 | 0.537 | 402 | 657 | 35 |
| all_stations | M4_inertia_ridge | precision_70 | — | — | — | — | — | — | — |
| all_stations | M5_v10_morphology_ridge | fixed_31 | 31.00 | 0.341 | 0.140 | 0.198 | 61 | 118 | 376 |
| all_stations | M5_v10_morphology_ridge | best_F1 | 29.85 | 0.405 | 0.838 | 0.546 | 366 | 537 | 71 |
| all_stations | M5_v10_morphology_ridge | recall_90 | 29.15 | 0.333 | 0.911 | 0.487 | 398 | 798 | 39 |
| all_stations | M5_v10_morphology_ridge | precision_70 | — | — | — | — | — | — | — |
| all_stations | M7_compact_weather_ridge | fixed_31 | 31.00 | 0.341 | 0.140 | 0.198 | 61 | 118 | 376 |
| all_stations | M7_compact_weather_ridge | best_F1 | 29.85 | 0.405 | 0.838 | 0.546 | 366 | 537 | 71 |
| all_stations | M7_compact_weather_ridge | recall_90 | 29.15 | 0.333 | 0.911 | 0.487 | 398 | 798 | 39 |
| all_stations | M7_compact_weather_ridge | precision_70 | — | — | — | — | — | — | — |

## Notes

- `fixed_31` is the canonical operational semantics: predicted WBGT ≥ 31.0°C → flag the hour. No threshold tuning required at deployment.
- `best_F1` is post-hoc; report it as a tuned upper bound, not the operational target.
- `recall_90` and `precision_70` answer 'how high can the other metric go if I commit to this floor'.