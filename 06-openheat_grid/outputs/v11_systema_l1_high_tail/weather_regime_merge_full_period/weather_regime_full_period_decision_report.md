# System A A-L1H.0c Full-Period Weather-Regime Decision Report

Generated: 2026-05-26
Status: PASS_FULL_PERIOD
Branch: codex/systema-l1h-residual-decomposition

## 1. Sources Tried

| inventory_role | evaluation_mode | path | matched_residual_rows | retention_rate | recovered_weather_columns | selected_for_merge | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| preferred_compact_recovered_source | evaluated_current_run | outputs/v11_systema_l1_high_tail/weather_regime_merge_inputs/best_weather_feature_source.csv.gz | 6696 | 1.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | True | usable |
| configured_fallback | evaluated_current_run | data/calibration/v09_historical_forecast_by_station_hourly.csv | 2700 | 0.403 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|direct_radiation\|diffuse_radiation | False | usable |
| configured_fallback | evaluated_current_run | data/calibration/v09_wbgt_station_pairs.csv | 2700 | 0.403 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|direct_radiation\|diffuse_radiation | False | usable |
| configured_fallback | evaluated_current_run | data/calibration/v11/live_chunks/wbgt_pairs_2026-05-24.csv.gz | 0 | 0.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | usable |
| preflight_reference | preflight_reference_not_loaded | outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv | 6696 | 1.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_diag.csv | 6696 | 1.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | outputs/v11_level1/feature_ablation/feature_matrix_hourly_max.csv | 6696 | 1.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | outputs/v11_level1/reproduction/feature_matrix_hourly_max.csv | 6696 | 1.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | data/calibration/v11/v11_station_weather_pairs_hourly.csv | 6696 | 1.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | data/calibration/v11/v11_station_weather_pairs_v091.csv | 6696 | 1.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | data/calibration/v09_historical_forecast_by_station_hourly.csv | 2700 | 0.403 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|cloud_cover\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | data/calibration/v09_historical_forecast_by_station_hourly.csv | 2700 | 0.403 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|cloud_cover\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | data/calibration/v09_wbgt_station_pairs.csv | 2700 | 0.403 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|cloud_cover\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | data/calibration/v09_wbgt_station_pairs.csv | 2700 | 0.403 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|cloud_cover\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | data/calibration/v11/live_chunks/wbgt_pairs_2026-05-24.csv.gz | 0 | 0.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |
| preflight_reference | preflight_reference_not_loaded | data/calibration/v11/live_chunks/wbgt_pairs_2026-05-24.csv.gz | 0 | 0.000 | temperature_2m\|relative_humidity_2m\|wind_speed_10m\|shortwave_radiation\|shortwave_3h_mean\|cloud_cover\|precipitation\|direct_radiation\|diffuse_radiation | False | preflight provenance reference |

## 2. Source Selected

- Selected weather source: `outputs/v11_systema_l1_high_tail/weather_regime_merge_inputs/best_weather_feature_source.csv.gz`
- Selected source base: `orig`
- Original provenance: `outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv`
- The original diagnostics input is not copied or required for this run; the compact recovered source is used for weather covariates.

## 3. Improvement Over A-L1H.0b

- A-L1H.0b matched rows: 2700 / 6696 (40.3%)
- A-L1H.0c matched rows: 6696 / 6696 (100.0%)
- Improvement: 3996 rows and 59.7 percentage points.

## 4. Merge Keys

- Merge keys: `station_id+timestamp->SGT_hour; weather=station_id+merge_hour->SGT_hour`
- Matching uses exact `station_id` plus SGT hourly timestamp only.
- Target WBGT values are not used as merge keys.
- Unmatched residual rows remain in the merged output with `has_weather_match = False`.

## 5. Row Retention And Station Coverage

- Total residual rows: 6696
- Matched rows: 6696
- Unmatched rows: 0
- Retention rate: 100.0%
- Matched observed ge31 rows: 816 / 816
- Matched unique observed ge31 station-hour events: 204 / 204
- Matched ge31 miss rows: 391
- Matched observed ge31 rows for `M4_inertia_ridge`: 408
- Matched ge31 miss rows for `M4_inertia_ridge`: 214
- Station coverage: 27 / 27

## 6. Weather Columns Recovered

- Recovered columns: temperature_2m, relative_humidity_2m, wind_speed_10m, shortwave_radiation, shortwave_3h_mean, cloud_cover, precipitation, direct_radiation, diffuse_radiation
- Missing configured columns: none

## 7. Residual / ge31 Miss By Weather Regime

Residual by weather regime, primary model:

| regime_variable | regime_bin | n | n_obs_ge31 | n_ge31_miss | mean_residual_c | p90_residual_c | ge31_miss_rate_among_observed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| combined_radiation_hot_regime | highradiation_not_hot | 298 | 4 | 4 | 0.324 | 1.674 | 1.000 |
| cloud_cover_bin | low | 850 | 190 | 111 | 0.294 | 1.699 | 0.584 |
| humidity_bin | mid | 838 | 106 | 75 | 0.238 | 1.582 | 0.708 |
| shortwave_bin | very_high | 836 | 380 | 186 | 0.232 | 1.733 | 0.489 |
| direct_radiation_bin | very_high | 836 | 354 | 160 | 0.214 | 1.679 | 0.452 |
| temperature_bin | mid | 839 | 4 | 4 | 0.207 | 1.145 | 1.000 |
| shortwave_3h_mean_bin | very_high | 837 | 301 | 148 | 0.202 | 1.695 | 0.492 |
| wind_bin | very_high | 833 | 206 | 91 | 0.191 | 1.623 | 0.442 |
| diffuse_radiation_bin | high | 678 | 48 | 25 | 0.182 | 1.648 | 0.521 |
| humidity_bin | high | 862 | 6 | 6 | 0.182 | 1.060 | 1.000 |

ge31 miss concentration by weather regime, primary model:

| regime_variable | regime_bin | n_obs_ge31 | n_ge31_miss | ge31_miss_rate_among_observed | share_of_model_ge31_misses | mean_residual_c |
| --- | --- | --- | --- | --- | --- | --- |
| combined_radiation_hot_regime | radiation_hot | 404 | 210 | 0.520 | 0.981 | 0.153 |
| diffuse_radiation_bin | very_high | 360 | 189 | 0.525 | 0.883 | 0.148 |
| shortwave_bin | very_high | 380 | 186 | 0.489 | 0.869 | 0.232 |
| direct_radiation_bin | very_high | 354 | 160 | 0.452 | 0.748 | 0.214 |
| shortwave_3h_mean_bin | very_high | 301 | 148 | 0.492 | 0.692 | 0.202 |
| temperature_bin | very_high | 323 | 143 | 0.443 | 0.668 | 0.150 |
| humidity_bin | low | 296 | 133 | 0.449 | 0.621 | 0.113 |
| cloud_cover_bin | low | 190 | 111 | 0.584 | 0.519 | 0.294 |
| wind_bin | very_high | 206 | 91 | 0.442 | 0.425 | 0.191 |
| humidity_bin | mid | 106 | 75 | 0.708 | 0.350 | 0.238 |

Combined-regime notes:

- combined_radiation_hot_regime included from temperature and radiation quantile bins.
- combined_hot_humid_lowwind_highsw_regime not included because it was not meaningful under configured thresholds (9 rows, 0 observed ge31 rows).

## 8. Weather-Regime Interaction Classification

- Classification: `supported_full_period`
- Evidence note: Largest primary-model residual-bin range is 0.40 C; largest ge31 miss-rate range is 0.56.
- Interpretation: Weather-regime diagnostic coverage: PASS_FULL_PERIOD. Radiation-hot regimes contain nearly all observed ge31 events and misses, but conditional miss-rate enrichment beyond the observed-ge31 base rate is mixed. This supports full-period weather-regime diagnostic evidence, not causal proof. The dominant issue remains global high-tail score compression, with station-specific bias and weather-regime structure as interacting diagnostics.
- This is full-period retrospective System A WBGT_A residual diagnostic evidence only when status is `PASS_FULL_PERIOD`; it is not validated local WBGT prediction and not an operational warning probability.

## 9. Recommended Next Action

- Recommended next action: close A-L1H.0c as full-period weather-regime residual diagnostic evidence; use it only to inform separately scoped formula-audit review, with probability calibration, high-tail regression, and A-L2 behind explicit review gates.
- Do not start A-L2 unless station bias remains after weather/regime control.
- Do not implement formula-v2, probability calibration, or high-tail regression inside this merge task.

## Claim Boundaries

- Allowed: retrospective System A WBGT_A temporal severity diagnostics; full-period weather-regime residual diagnostics; evidence to inform later WBGT-gated radiative priority only after System B coupling.
- Disallowed: validated local WBGT prediction, real-time heat risk forecast, standalone local hazard prioritisation from System A alone, official warning probability claims, SOLWEIG Tmrt equals WBGT, probability calibration, or high-tail regression claims.
