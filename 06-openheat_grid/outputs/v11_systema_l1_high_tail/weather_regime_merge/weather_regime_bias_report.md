# System A A-L1H.0b Weather-Regime Residual Merge

Generated: 2026-05-26
Status: PASS
Branch: codex/systema-l1h-residual-decomposition

## 1. Weather Source Selected

- Selected source: `data/calibration/v09_wbgt_station_pairs.csv`
- Selection note: usable; selected_highest_retention_usable_source
- This source is used only for station/hour weather covariates; target values in weather-pair files are not used for matching.

## 2. Merge Keys Used

- Merge keys: `station_id+timestamp->SGT_hour; weather=station_id+timestamp_sgt->SGT_hour`
- Preferred logic: exact `station_id` plus SGT hourly timestamp. Timestamps are normalized to SGT hour buckets before merging.
- Target WBGT values are not part of the merge key.

## 3. Row Retention

- Residual rows: 6696
- Rows with matched weather: 2700
- Retention rate: 40.3%
- Unmatched residual rows are retained in `residual_weather_merge_input.csv` with `has_weather_match = False`, but regime summaries use matched rows only.

## 4. Missing Weather Columns

- Recovered columns: temperature_2m, relative_humidity_2m, wind_speed_10m, shortwave_radiation, shortwave_3h_mean, cloud_cover, direct_radiation, diffuse_radiation
- Missing configured columns: precipitation

## 5. Residual by Weather Regime

| regime_variable | regime_bin | n | n_obs_ge31 | mean_residual_c | p90_residual_c | ge31_miss_rate_among_observed |
| --- | --- | --- | --- | --- | --- | --- |
| diffuse_radiation_bin | very_high | 337 | 212 | 0.350 | 1.988 | 0.458 |
| shortwave_3h_mean_bin | very_high | 337 | 206 | 0.297 | 1.884 | 0.442 |
| shortwave_bin | very_high | 337 | 188 | 0.134 | 1.694 | 0.388 |
| humidity_bin | low | 340 | 178 | 0.114 | 1.667 | 0.354 |
| temperature_bin | very_high | 334 | 178 | 0.090 | 1.663 | 0.354 |
| direct_radiation_bin | very_high | 337 | 176 | 0.037 | 1.593 | 0.347 |
| wind_bin | very_high | 337 | 158 | 0.024 | 1.634 | 0.386 |
| cloud_cover_bin | high | 413 | 81 | -0.082 | 1.413 | 0.481 |

## 6. ge31 Miss Concentration by Regime

| regime_variable | regime_bin | n_obs_ge31 | n_ge31_miss | ge31_miss_rate_among_observed | share_of_model_ge31_misses | mean_residual_c |
| --- | --- | --- | --- | --- | --- | --- |
| combined_hot_humid_lowwind_highsw | other | 216 | 101 | 0.468 | 1.000 | -0.201 |
| diffuse_radiation_bin | very_high | 212 | 97 | 0.458 | 0.960 | 0.350 |
| shortwave_3h_mean_bin | very_high | 206 | 91 | 0.442 | 0.901 | 0.297 |
| shortwave_bin | very_high | 188 | 73 | 0.388 | 0.723 | 0.134 |
| humidity_bin | low | 178 | 63 | 0.354 | 0.624 | 0.114 |
| temperature_bin | very_high | 178 | 63 | 0.354 | 0.624 | 0.090 |
| wind_bin | very_high | 158 | 61 | 0.386 | 0.604 | 0.024 |
| direct_radiation_bin | very_high | 176 | 61 | 0.347 | 0.604 | 0.037 |

## 7. Plausibility Interpretation

- Weather-regime interaction classification: `plausible_but_partial`
- Interpretation: Largest residual-bin range is 0.93 C and largest ge31 miss-rate range is 0.65; interpret as partial-period diagnostic evidence only.
- This is a retrospective OOF diagnostic on matched rows only. It supports prioritisation, not a validated local WBGT prediction or operational warning claim.

## 8. Next Recommended Action

mixed staged follow-up: first secure a full-period weather feature table, then revisit formula-v2 / physical proxy and threshold-calibration gates.

## Candidate Inventory

| path | exists | readable | recovered_weather_columns | matched_residual_rows | retention_rate | selected_for_merge | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| data/calibration/v09_historical_forecast_by_station_hourly.csv | yes | yes | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|direct_radiation\|diffuse_radiation | 2700 | 0.403 | no | usable |
| data/calibration/v09_wbgt_station_pairs.csv | yes | yes | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|direct_radiation\|diffuse_radiation | 2700 | 0.403 | yes | usable; selected_highest_retention_usable_source |
| data/calibration/v11/live_chunks/wbgt_pairs_2026-05-24.csv.gz | yes | yes | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | 0 | 0.000 | no | usable |
| data/calibration/v11/v11_station_weather_pairs_hourly.csv | no | no |  | 0 | 0.000 | no | missing |
| data/calibration/v11/v11_station_weather_pairs_v091.csv | no | no |  | 0 | 0.000 | no | missing |
| outputs/v11_level1/feature_ablation/feature_matrix_hourly_max.csv | no | no |  | 0 | 0.000 | no | missing |
| outputs/v11_level1/reproduction/feature_matrix_hourly_max.csv | no | no |  | 0 | 0.000 | no | missing |

## Claim Boundaries

- This remains a WBGT-gated, SOLWEIG-informed, surrogate-assisted local heat hazard ranking diagnostic lane.
- Do not describe this as validated local WBGT prediction, real-time heat risk forecasting, probability calibration, or high-tail regression.
