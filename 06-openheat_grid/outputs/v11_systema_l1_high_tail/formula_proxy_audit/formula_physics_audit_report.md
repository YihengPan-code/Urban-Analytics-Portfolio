# System A A-L1H.1 Formula / Physical Proxy Audit

Generated: 2026-05-26
Acceptance status: `PASS`
Diagnostic decision: `WEAK_OR_NEGATIVE`
Branch: `codex/systema-l1h-formula-proxy-audit`

## 1. Inputs and Candidate Registry

This audit uses the A-L1H.0c full-period residual/weather merge as diagnostic evidence. It does not treat A-L1H.0c as proof that the v09 formula caused high-tail compression.

| inventory_role | input_label | path | exists | rows_sampled_or_total | weather_columns_present | proxy_columns_present | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| primary | residual_weather_merge | outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv | True | 6696.000000 | temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_3h_mean;direct_radiation;diffuse_radiation;cloud_cover;precipitation |  |  |
| primary | residual_analysis_input | outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv | True | 6696.000000 |  |  |  |
| primary | oof_predictions | outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv | True | 30132.000000 |  | wbgt_proxy_v09_c |  |
| optional_discovery | formula_candidate_registry | outputs/v11_level1/formula_v2/formula_candidate_registry.csv | True |  |  |  |  |
| optional_discovery | raw_formula_metrics | outputs/v11_level1/formula_v2/raw_formula_metrics.csv | True |  |  |  |  |
| optional_discovery | raw_formula_threshold_metrics | outputs/v11_level1/formula_v2/raw_formula_threshold_metrics.csv | True |  |  |  |  |
| optional_discovery | sprint3a_formula_v2_proxy_benchmark_report | outputs/v11_level1/formula_v2/sprint3a_formula_v2_proxy_benchmark_report.md | True |  |  |  | markdown_context_file |
| optional_discovery | formula_bias_mae_rmse_table | outputs/v11_formula_audit/formula_bias_mae_rmse_table.csv | True |  |  |  |  |
| optional_discovery | formula_threshold_operating_points | outputs/v11_formula_audit/formula_threshold_operating_points.csv | True |  |  |  |  |
| optional_discovery | System_A_WBGT_formula_audit_report | outputs/v11_formula_audit/System_A_WBGT_formula_audit_report.md | True |  |  |  | markdown_context_file |
| optional_discovery | wbgt_pairs_2026-05-24.csv | data/calibration/v11/live_chunks/wbgt_pairs_2026-05-24.csv.gz | True |  | temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_3h_mean;direct_radiation;diffuse_radiation;cloud_cover;precipitation |  |  |
| optional_discovery | v11_pairs_14d_formal_20260524_40419_v091_diag | outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv | False |  |  |  |  |

Candidate registry summary:

| candidate_id | candidate_role | candidate_family | implementation_status | row_unit | missing_columns | source |
| --- | --- | --- | --- | --- | --- | --- |
| M4_inertia_ridge | score_comparator | current_oof_score | available | residual_model_row |  | outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv |
| M7_compact_weather_ridge | score_comparator | current_oof_score | available | residual_model_row |  | outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv |
| wbgt_proxy_v09_c | raw_proxy | existing_v09_proxy | available | unique_station_hour |  | found_in_oof_predictions |
| stull_globe_shortwave_radiation_k0p002_wf0p25 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p003_wf0p25 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p0045_wf0p25 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p006_wf0p25 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p008_wf0p25 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p01_wf0p25 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p012_wf0p25 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p002_wf0p5 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p003_wf0p5 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p0045_wf0p5 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p006_wf0p5 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p008_wf0p5 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p01_wf0p5 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p012_wf0p5 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p002_wf1p0 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p003_wf1p0 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |
| stull_globe_shortwave_radiation_k0p0045_wf1p0 | raw_formula_proxy | stull_wetbulb_simple_globe_k_sweep | available | unique_station_hour |  | computed_from_residual_weather_merge_full_period |

## 2. Formula Definitions and Assumptions

- `M4_inertia_ridge` and `M7_compact_weather_ridge` are current OOF score comparators from residual rows; they are not raw physical formulas.
- `wbgt_proxy_v09_c` is the existing v09 proxy when present in OOF rows; if absent, the audit reconstructs only a labelled v09-style diagnostic.
- Stull simple-globe candidates use `wetbulb=Stull(T,RH)`, `globe_simple=T + k*radiation/sqrt(wind_speed_10m + wind_floor)`, and `WBGT_proxy=0.7*wetbulb + 0.2*globe_simple + 0.1*T`.
- k values, wind floors, and radiation inputs are config-driven. These are screening proxies, not canonical WBGT_A replacements.
- Formula candidates are computed on deduplicated unique station-hour targets; M4/M7 comparators retain residual-row OOF scores including LOSO and blocked-time rows.

## 3. Advanced Formula Packages

| candidate_id | implementation_status | source | missing_columns | assumptions |
| --- | --- | --- | --- | --- |
| advanced_package_pythermalcomfort | unavailable_not_installed | pythermalcomfort | pythermalcomfort | No pip install performed; advanced route needs separate validation before use. |
| advanced_package_psychrolib | unavailable_not_installed | psychrolib | psychrolib | No pip install performed; advanced route needs separate validation before use. |
| advanced_package_pywbgt | unavailable_not_installed | pywbgt | pywbgt | No pip install performed; advanced route needs separate validation before use. |
| local_liljegren_style_implementation | unavailable_no_local_implementation | none | validated local Liljegren-style implementation | Advanced formula route remains blocked/partial until separately validated. |

No Liljegren-style formula is faked. Advanced physics routes require a separate implementation and validation task before any System A reporting use.

## 4. Overall Metrics

Comparator scores:

| candidate_id | n | bias | MAE | RMSE | R2 | max_predicted_wbgt | p99_predicted_wbgt | mean_residual_observed_ge31 | compression_ratio_p99_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M4_inertia_ridge | 3348 | -0.102381 | 0.726351 | 0.964654 | 0.818023 | 32.084270 | 31.648120 | 1.027975 | 0.836875 |
| M7_compact_weather_ridge | 3348 | 0.026312 | 0.747887 | 1.011925 | 0.799750 | 33.357712 | 32.239108 | 0.873214 | 0.884684 |

Best raw formula/proxy candidates by observed-ge31 residual:

| candidate_id | n | bias | MAE | RMSE | R2 | max_predicted_wbgt | p99_predicted_wbgt | mean_residual_observed_ge31 | compression_ratio_p99_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stull_globe_shortwave_radiation_k0p012_wf0p25 | 1674 | -1.220146 | 1.359283 | 1.925132 | 0.275238 | 29.776542 | 28.886094 | 3.854142 | 0.418411 |
| stull_globe_direct_plus_diffuse_k0p012_wf0p25 | 1674 | -1.220146 | 1.359283 | 1.925132 | 0.275238 | 29.776542 | 28.886094 | 3.854142 | 0.418411 |
| stull_globe_shortwave_radiation_k0p012_wf0p5 | 1674 | -1.226853 | 1.364644 | 1.933093 | 0.269231 | 29.745261 | 28.873638 | 3.877573 | 0.416939 |
| stull_globe_direct_plus_diffuse_k0p012_wf0p5 | 1674 | -1.226853 | 1.364644 | 1.933093 | 0.269231 | 29.745261 | 28.873638 | 3.877573 | 0.416939 |
| stull_globe_shortwave_radiation_k0p012_wf1p0 | 1674 | -1.237395 | 1.373130 | 1.946049 | 0.259403 | 29.690198 | 28.799903 | 3.913623 | 0.405921 |
| stull_globe_direct_plus_diffuse_k0p012_wf1p0 | 1674 | -1.237395 | 1.373130 | 1.946049 | 0.259403 | 29.690198 | 28.799903 | 3.913623 | 0.405921 |
| stull_globe_shortwave_radiation_k0p01_wf0p25 | 1674 | -1.254147 | 1.388094 | 1.969236 | 0.241650 | 29.599843 | 28.755936 | 3.966980 | 0.402247 |
| stull_globe_direct_plus_diffuse_k0p01_wf0p25 | 1674 | -1.254147 | 1.388094 | 1.969236 | 0.241650 | 29.599843 | 28.755936 | 3.966980 | 0.402247 |
| stull_globe_shortwave_3h_mean_k0p012_wf0p25 | 1674 | -1.200614 | 1.384965 | 1.968185 | 0.242459 | 29.540761 | 28.727229 | 3.977099 | 0.391430 |
| stull_globe_shortwave_radiation_k0p01_wf0p5 | 1674 | -1.259735 | 1.392602 | 1.976074 | 0.236373 | 29.573775 | 28.745556 | 3.986506 | 0.401086 |

## 5. Fixed_31 / Best-F1 Threshold Metrics

| candidate_id | candidate_role | observed_ge31_count | predicted_ge31_fixed_count | hits_ge31 | misses_ge31 | false_alarms_ge31 | precision_ge31 | recall_ge31 | f1_ge31 | best_f1_threshold_ge31 | best_f1_ge31 | threshold_gap_to_31 | observed_ge33_count | predicted_ge33_fixed_count | recall_ge33 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stull_globe_shortwave_radiation_k0p012_wf0p25 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.050000 | 0.598039 | -3.950000 | 15 | 0 | 0.000000 |
| stull_globe_direct_plus_diffuse_k0p012_wf0p25 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.050000 | 0.598039 | -3.950000 | 15 | 0 | 0.000000 |
| stull_globe_shortwave_radiation_k0p012_wf1p0 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.150000 | 0.593220 | -3.850000 | 15 | 0 | 0.000000 |
| stull_globe_direct_plus_diffuse_k0p012_wf1p0 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.150000 | 0.593220 | -3.850000 | 15 | 0 | 0.000000 |
| stull_globe_shortwave_radiation_k0p012_wf0p5 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.200000 | 0.592083 | -3.800000 | 15 | 0 | 0.000000 |
| stull_globe_direct_plus_diffuse_k0p012_wf0p5 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.200000 | 0.592083 | -3.800000 | 15 | 0 | 0.000000 |
| stull_globe_shortwave_radiation_k0p01_wf1p0 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.100000 | 0.591837 | -3.900000 | 15 | 0 | 0.000000 |
| stull_globe_direct_plus_diffuse_k0p01_wf1p0 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.100000 | 0.591837 | -3.900000 | 15 | 0 | 0.000000 |
| stull_globe_shortwave_radiation_k0p01_wf0p25 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.100000 | 0.589226 | -3.900000 | 15 | 0 | 0.000000 |
| stull_globe_shortwave_radiation_k0p01_wf0p5 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.100000 | 0.589226 | -3.900000 | 15 | 0 | 0.000000 |
| stull_globe_direct_plus_diffuse_k0p01_wf0p25 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.100000 | 0.589226 | -3.900000 | 15 | 0 | 0.000000 |
| stull_globe_direct_plus_diffuse_k0p01_wf0p5 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.100000 | 0.589226 | -3.900000 | 15 | 0 | 0.000000 |
| stull_globe_shortwave_radiation_k0p008_wf0p25 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.050000 | 0.583618 | -3.950000 | 15 | 0 | 0.000000 |
| stull_globe_direct_plus_diffuse_k0p008_wf0p25 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.050000 | 0.583618 | -3.950000 | 15 | 0 | 0.000000 |
| stull_globe_shortwave_3h_mean_k0p012_wf0p25 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.200000 | 0.582759 | -3.800000 | 15 | 0 | 0.000000 |
| stull_globe_shortwave_radiation_k0p008_wf0p5 | raw_formula_proxy | 204 | 0 | 0 | 204 | 0 |  | 0.000000 | 0.000000 | 27.050000 | 0.582192 | -3.950000 | 15 | 0 | 0.000000 |

ge33 metrics are exploratory only and are not used to promote a formula candidate.

## 6. High-Tail Compression Diagnostics

stull_globe_shortwave_radiation_k0p012_wf0p25 mean observed-ge31 residual=3.854 C versus M7_compact_weather_ridge=0.873 C (positive means official minus prediction; improvement=-2.981 C).

| candidate_id | regime_bin | n | n_obs_ge31 | n_pred_ge31 | n_ge31_miss | mean_residual_official_minus_pred_c | mean_abs_error_c |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M4_inertia_ridge | 31-32 | 268 | 268 | 135 | 133 | 0.621746 | 0.809238 |
| M4_inertia_ridge | 32-33 | 110 | 110 | 46 | 64 | 1.620904 | 1.620904 |
| M4_inertia_ridge | >=33 | 30 | 30 | 13 | 17 | 2.482873 | 2.482873 |
| M7_compact_weather_ridge | 31-32 | 268 | 268 | 156 | 112 | 0.438034 | 0.931557 |
| M7_compact_weather_ridge | 32-33 | 110 | 110 | 54 | 56 | 1.596456 | 1.616277 |
| M7_compact_weather_ridge | >=33 | 30 | 30 | 21 | 9 | 2.108925 | 2.108925 |
| stull_globe_direct_plus_diffuse_k0p002_wf0p25 | 31-32 | 134 | 134 | 0 | 134 | 3.982287 | 3.982287 |
| stull_globe_direct_plus_diffuse_k0p002_wf0p25 | 32-33 | 55 | 55 | 0 | 55 | 5.058748 | 5.058748 |
| stull_globe_direct_plus_diffuse_k0p002_wf0p25 | >=33 | 15 | 15 | 0 | 15 | 5.965470 | 5.965470 |
| stull_globe_direct_plus_diffuse_k0p002_wf0p5 | 31-32 | 134 | 134 | 0 | 134 | 3.986531 | 3.986531 |
| stull_globe_direct_plus_diffuse_k0p002_wf0p5 | 32-33 | 55 | 55 | 0 | 55 | 5.062238 | 5.062238 |
| stull_globe_direct_plus_diffuse_k0p002_wf0p5 | >=33 | 15 | 15 | 0 | 15 | 5.967876 | 5.967876 |
| stull_globe_direct_plus_diffuse_k0p002_wf1p0 | 31-32 | 134 | 134 | 0 | 134 | 3.992916 | 3.992916 |
| stull_globe_direct_plus_diffuse_k0p002_wf1p0 | 32-33 | 55 | 55 | 0 | 55 | 5.067799 | 5.067799 |
| stull_globe_direct_plus_diffuse_k0p002_wf1p0 | >=33 | 15 | 15 | 0 | 15 | 5.972154 | 5.972154 |
| stull_globe_direct_plus_diffuse_k0p003_wf0p25 | 31-32 | 134 | 134 | 0 | 134 | 3.925216 | 3.925216 |
| stull_globe_direct_plus_diffuse_k0p003_wf0p25 | 32-33 | 55 | 55 | 0 | 55 | 5.003868 | 5.003868 |
| stull_globe_direct_plus_diffuse_k0p003_wf0p25 | >=33 | 15 | 15 | 0 | 15 | 5.909235 | 5.909235 |
| stull_globe_direct_plus_diffuse_k0p003_wf0p5 | 31-32 | 134 | 134 | 0 | 134 | 3.931581 | 3.931581 |
| stull_globe_direct_plus_diffuse_k0p003_wf0p5 | 32-33 | 55 | 55 | 0 | 55 | 5.009104 | 5.009104 |

Component diagnostics:

| candidate_id | radiation_input | k_value | wind_floor | wetbulb_min_c | wetbulb_max_c | globe_simple_min_c | globe_simple_max_c | formula_dynamic_range_c | compression_ratio | corr_prediction_shortwave_radiation | corr_residual_shortwave_radiation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stull_globe_shortwave_radiation_k0p012_wf0p25 | shortwave_radiation | 0.012000 | 0.250000 | 23.534964 | 27.102533 | 23.500000 | 38.898416 | 6.252067 | 0.418411 | 0.845440 | 0.627910 |
| stull_globe_direct_plus_diffuse_k0p012_wf0p25 | direct_plus_diffuse | 0.012000 | 0.250000 | 23.534964 | 27.102533 | 23.500000 | 38.898416 | 6.252067 | 0.418411 | 0.845440 | 0.627910 |
| stull_globe_shortwave_radiation_k0p012_wf0p5 | shortwave_radiation | 0.012000 | 0.500000 | 23.534964 | 27.102533 | 23.500000 | 37.644566 | 6.220786 | 0.416939 | 0.845441 | 0.630665 |
| stull_globe_direct_plus_diffuse_k0p012_wf0p5 | direct_plus_diffuse | 0.012000 | 0.500000 | 23.534964 | 27.102533 | 23.500000 | 37.644566 | 6.220786 | 0.416939 | 0.845441 | 0.630665 |
| stull_globe_shortwave_radiation_k0p012_wf1p0 | shortwave_radiation | 0.012000 | 1.000000 | 23.534964 | 27.102533 | 23.500000 | 37.369254 | 6.165723 | 0.405921 | 0.844605 | 0.635050 |
| stull_globe_direct_plus_diffuse_k0p012_wf1p0 | direct_plus_diffuse | 0.012000 | 1.000000 | 23.534964 | 27.102533 | 23.500000 | 37.369254 | 6.165723 | 0.405921 | 0.844605 | 0.635050 |
| stull_globe_shortwave_radiation_k0p01_wf0p25 | shortwave_radiation | 0.010000 | 0.250000 | 23.534964 | 27.102533 | 23.500000 | 37.365347 | 6.075368 | 0.402247 | 0.836512 | 0.645400 |
| stull_globe_direct_plus_diffuse_k0p01_wf0p25 | direct_plus_diffuse | 0.010000 | 0.250000 | 23.534964 | 27.102533 | 23.500000 | 37.365347 | 6.075368 | 0.402247 | 0.836512 | 0.645400 |
| stull_globe_shortwave_radiation_k0p01_wf0p5 | shortwave_radiation | 0.010000 | 0.500000 | 23.534964 | 27.102533 | 23.500000 | 36.787139 | 6.049300 | 0.401086 | 0.836312 | 0.647498 |
| stull_globe_direct_plus_diffuse_k0p01_wf0p5 | direct_plus_diffuse | 0.010000 | 0.500000 | 23.534964 | 27.102533 | 23.500000 | 36.787139 | 6.049300 | 0.401086 | 0.836312 | 0.647498 |
| stull_globe_shortwave_3h_mean_k0p012_wf0p25 | shortwave_3h_mean | 0.012000 | 0.250000 | 23.534964 | 27.102533 | 23.500000 | 40.944255 | 6.016286 | 0.391430 | 0.813470 | 0.630620 |
| stull_globe_shortwave_3h_mean_k0p012_wf0p5 | shortwave_3h_mean | 0.012000 | 0.500000 | 23.534964 | 27.102533 | 23.500000 | 39.874534 | 5.991962 | 0.389855 | 0.814839 | 0.633474 |
| stull_globe_shortwave_radiation_k0p01_wf1p0 | shortwave_radiation | 0.010000 | 1.000000 | 23.534964 | 27.102533 | 23.500000 | 36.557711 | 6.003415 | 0.389457 | 0.835345 | 0.650885 |
| stull_globe_direct_plus_diffuse_k0p01_wf1p0 | direct_plus_diffuse | 0.010000 | 1.000000 | 23.534964 | 27.102533 | 23.500000 | 36.557711 | 6.003415 | 0.389457 | 0.835345 | 0.650885 |

## 7. Radiation-Hot Regime Diagnostics

stull_globe_shortwave_radiation_k0p012_wf0p25 radiation-hot ge31 miss rate=1.000; M7_compact_weather_ridge radiation-hot ge31 miss rate=0.428.

| candidate_id | regime_variable | regime_bin | n_obs_ge31 | n_ge31_miss | ge31_miss_rate_among_observed | share_of_candidate_ge31_misses_in_regime_variable | mean_residual_official_minus_pred_c |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M4_inertia_ridge | combined_radiation_hot_regime | highradiation_not_hot | 4 | 4 | 1.000000 | 0.018692 | 0.323766 |
| M4_inertia_ridge | combined_radiation_hot_regime | hot_not_highradiation | 0 | 0 |  | 0.000000 | 0.012403 |
| M4_inertia_ridge | combined_radiation_hot_regime | other | 0 | 0 |  | 0.000000 | 0.008602 |
| M4_inertia_ridge | combined_radiation_hot_regime | radiation_hot | 404 | 210 | 0.519802 | 0.981308 | 0.153213 |
| M4_inertia_ridge | shortwave_3h_mean_bin | high | 105 | 64 | 0.609524 | 0.299065 | 0.121997 |
| M4_inertia_ridge | shortwave_3h_mean_bin | low | 0 | 0 |  | 0.000000 | -0.002401 |
| M4_inertia_ridge | shortwave_3h_mean_bin | mid | 2 | 2 | 1.000000 | 0.009346 | 0.109927 |
| M4_inertia_ridge | shortwave_3h_mean_bin | very_high | 301 | 148 | 0.491694 | 0.691589 | 0.201741 |
| M4_inertia_ridge | shortwave_bin | high | 28 | 28 | 1.000000 | 0.130841 | 0.078846 |
| M4_inertia_ridge | shortwave_bin | low | 0 | 0 |  | 0.000000 | -0.001178 |
| M4_inertia_ridge | shortwave_bin | mid | 0 | 0 |  | 0.000000 | 0.105480 |
| M4_inertia_ridge | shortwave_bin | very_high | 380 | 186 | 0.489474 | 0.869159 | 0.231724 |
| M7_compact_weather_ridge | combined_radiation_hot_regime | highradiation_not_hot | 4 | 4 | 1.000000 | 0.022599 | -0.000389 |
| M7_compact_weather_ridge | combined_radiation_hot_regime | hot_not_highradiation | 0 | 0 |  | 0.000000 | 0.112973 |
| M7_compact_weather_ridge | combined_radiation_hot_regime | other | 0 | 0 |  | 0.000000 | 0.002035 |
| M7_compact_weather_ridge | combined_radiation_hot_regime | radiation_hot | 404 | 173 | 0.428218 | 0.977401 | -0.068032 |
| M7_compact_weather_ridge | shortwave_3h_mean_bin | high | 105 | 59 | 0.561905 | 0.333333 | -0.028867 |
| M7_compact_weather_ridge | shortwave_3h_mean_bin | low | 0 | 0 |  | 0.000000 | -0.008998 |
| M7_compact_weather_ridge | shortwave_3h_mean_bin | mid | 2 | 2 | 1.000000 | 0.011299 | 0.070367 |
| M7_compact_weather_ridge | shortwave_3h_mean_bin | very_high | 301 | 116 | 0.385382 | 0.655367 | -0.153113 |
| M7_compact_weather_ridge | shortwave_bin | high | 28 | 28 | 1.000000 | 0.158192 | 0.010579 |
| M7_compact_weather_ridge | shortwave_bin | low | 0 | 0 |  | 0.000000 | -0.031988 |
| M7_compact_weather_ridge | shortwave_bin | mid | 0 | 0 |  | 0.000000 | 0.002330 |
| M7_compact_weather_ridge | shortwave_bin | very_high | 380 | 149 | 0.392105 | 0.841808 | -0.090968 |

## 8. Formula Improvement Versus M4/M7

Least-compressed raw formula/proxy by observed-ge31 residual was stull_globe_shortwave_radiation_k0p012_wf0p25; MAE=1.359 C, max_pred=29.777 C, best-F1 ge31 threshold=27.05 C.

Decision: `WEAK_OR_NEGATIVE`. The audit checks whether any formula materially reduces observed-ge31 residuals and moves the best-F1 threshold closer to 31 C without severe false alarms or large overall MAE degradation.

## 9. Fixed_31 Crossing Review

No raw formula/proxy candidate produced fixed_31 crossings.

A formula candidate is not promoted as canonical WBGT_A from this diagnostic, even when threshold behavior improves.

## 10. Route Assessment

Formula route assessment: `WEAK_OR_NEGATIVE`.

Allowed interpretation: diagnostic evidence for formula/proxy review in retrospective System A L1H. Disallowed interpretation: validated local WBGT prediction, real-time heat risk forecast, or proof that v09 caused the high-tail compression.

## 11. Next Recommended Action

A-L1H.2 probability / threshold calibration review is the more direct next action; keep deeper formula-v2 and high-tail regression behind review gates, and start A-L2 only after Level 1 high-tail / regime control.
