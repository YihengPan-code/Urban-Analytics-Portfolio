# System A Level 1 Dynamic Feature Ablation Report

## Status
PASS

## Scope
This is a System A Level 1 dynamic feature ablation only. It uses sklearn Ridge with the canonical median-impute and standard-scale preprocessing style, LOSO by `station_id`, and fixed alpha=1.0.

No new model family was added. No Level 2, System B, SOLWEIG, v12, rasters, risk maps, hazard maps, or local WBGT outputs were touched or produced.

## Input data
- input path: `data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_hourly.csv`
- raw rows: 10476
- station count: 27
- fold count: 27
- timestamp span: 2026-05-07 02:00:00+08:00 to 2026-05-24 20:00:00+08:00
- target columns: official_wbgt_c_mean;official_wbgt_c_max

Analytic rows by target:

| dataset_label | target_col | row_count | station_count | fold_count |
| --- | --- | --- | --- | --- |
| hourly_max | official_wbgt_c_max | 10473 | 27 | 27 |
| hourly_mean | official_wbgt_c_mean | 10473 | 27 | 27 |

## Feature availability audit

| feature_block | requested_features | available_features | missing_features | non_numeric_available_excluded | final_features_used |
| --- | --- | --- | --- | --- | --- |
| proxy | wbgt_proxy_v09_c | wbgt_proxy_v09_c |  |  | wbgt_proxy_v09_c |
| weather_core | temperature_2m;relative_humidity_2m;wind_speed_10m | temperature_2m;relative_humidity_2m;wind_speed_10m |  |  | temperature_2m;relative_humidity_2m;wind_speed_10m |
| radiation_basic | shortwave_radiation | shortwave_radiation |  |  | shortwave_radiation |
| radiation_extra | cloud_cover;direct_radiation;diffuse_radiation;solar_zenith_or_proxy | cloud_cover;direct_radiation;diffuse_radiation | solar_zenith_or_proxy |  | cloud_cover;direct_radiation;diffuse_radiation |
| time | hour_sin_v09;hour_cos_v09;period_* | hour_sin_v09;hour_cos_v09;period_v09 |  | period_v09 | hour_sin_v09;hour_cos_v09 |
| inertia | shortwave_1h_lag;shortwave_2h_lag;shortwave_3h_mean;d_temperature_dt;d_temp_dt;temperature_1h_delta;shortwave_lag_1h;shortwave_lag_2h;cumulative_day_shortwave_whm2;cumulative_day_shortwave_hourly_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean | shortwave_3h_mean;shortwave_lag_1h;shortwave_lag_2h;cumulative_day_shortwave_whm2;cumulative_day_shortwave_hourly_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean | shortwave_1h_lag;shortwave_2h_lag;d_temperature_dt;d_temp_dt;temperature_1h_delta |  | shortwave_3h_mean;shortwave_lag_1h;shortwave_lag_2h;cumulative_day_shortwave_whm2;cumulative_day_shortwave_hourly_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean |
| m4_like_inertia | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_lag_1h;shortwave_lag_2h;shortwave_3h_mean;cumulative_day_shortwave_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean;diffuse_fraction;direct_fraction;cloud_cover;hour_sin_v09;hour_cos_v09 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_lag_1h;shortwave_lag_2h;shortwave_3h_mean;cumulative_day_shortwave_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean;diffuse_fraction;direct_fraction;cloud_cover;hour_sin_v09;hour_cos_v09 |  |  | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_lag_1h;shortwave_lag_2h;shortwave_3h_mean;cumulative_day_shortwave_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean;diffuse_fraction;direct_fraction;cloud_cover;hour_sin_v09;hour_cos_v09 |
| m7_like_compact_weather | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_3h_mean;hour_sin_v09;hour_cos_v09 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_3h_mean;hour_sin_v09;hour_cos_v09 |  |  | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_3h_mean;hour_sin_v09;hour_cos_v09 |

## Model matrix

| ablation_model | feature_blocks | n_features | feature_list |
| --- | --- | --- | --- |
| L1_full_dynamic | proxy;weather_core;radiation_basic;radiation_extra;time;inertia | 19 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;cloud_cover;direct_radiation;diffuse_radiation;hour_sin_v09;hour_cos_v09;shortwave_3h_mean;shortwave_lag_1h;shortwave_lag_2h;cumulative_day_shortwave_whm2;cumulative_day_shortwave_hourly_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean |
| L1_proxy_inertia | proxy;inertia | 10 | wbgt_proxy_v09_c;shortwave_3h_mean;shortwave_lag_1h;shortwave_lag_2h;cumulative_day_shortwave_whm2;cumulative_day_shortwave_hourly_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean |
| L1_proxy_only | proxy | 1 | wbgt_proxy_v09_c |
| L1_proxy_radiation | proxy;radiation_basic;radiation_extra | 5 | wbgt_proxy_v09_c;shortwave_radiation;cloud_cover;direct_radiation;diffuse_radiation |
| L1_proxy_time | proxy;time | 3 | wbgt_proxy_v09_c;hour_sin_v09;hour_cos_v09 |
| L1_proxy_weather | proxy;weather_core | 4 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m |
| L1_proxy_weather_inertia | proxy;weather_core;inertia | 13 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_3h_mean;shortwave_lag_1h;shortwave_lag_2h;cumulative_day_shortwave_whm2;cumulative_day_shortwave_hourly_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean |
| L1_proxy_weather_radiation | proxy;weather_core;radiation_basic;radiation_extra | 8 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;cloud_cover;direct_radiation;diffuse_radiation |
| L1_proxy_weather_time | proxy;weather_core;time | 6 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;hour_sin_v09;hour_cos_v09 |
| M4_like_inertia_ridge | m4_like_inertia | 18 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_lag_1h;shortwave_lag_2h;shortwave_3h_mean;cumulative_day_shortwave_whm2;temperature_lag_1h;dTair_dt_1h;proxy_lag_1h;proxy_3h_mean;diffuse_fraction;direct_fraction;cloud_cover;hour_sin_v09;hour_cos_v09 |
| M7_like_compact_weather_ridge | m7_like_compact_weather | 8 | wbgt_proxy_v09_c;temperature_2m;relative_humidity_2m;wind_speed_10m;shortwave_radiation;shortwave_3h_mean;hour_sin_v09;hour_cos_v09 |

## Metrics summary

### hourly_mean
| ablation_model | MAE | RMSE | bias | R2 | fixed_31_recall | fixed_31_F1 | MAE_official_ge_31 | worst_station_abs_bias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M4_like_inertia_ridge | 0.8776 | 1.1966 | 0.0035 | 0.6723 | 0.0979 | 0.1716 | 1.8400 | 0.6559 |
| L1_full_dynamic | 0.8887 | 1.2158 | 0.0037 | 0.6617 | 0.0963 | 0.1678 | 1.8197 | 0.6557 |
| M7_like_compact_weather_ridge | 0.8948 | 1.2291 | 0.0035 | 0.6542 | 0.0722 | 0.1304 | 1.8627 | 0.6590 |
| L1_proxy_weather_radiation | 0.9409 | 1.2826 | 0.0021 | 0.6235 | 0.0578 | 0.1048 | 1.9648 | 0.6732 |
| L1_proxy_radiation | 0.9412 | 1.2882 | 0.0001 | 0.6202 | 0.0754 | 0.1341 | 1.9516 | 0.6707 |

### hourly_max
| ablation_model | MAE | RMSE | bias | R2 | fixed_31_recall | fixed_31_F1 | MAE_official_ge_31 | worst_station_abs_bias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M4_like_inertia_ridge | 0.9365 | 1.2727 | 0.0037 | 0.6987 | 0.3018 | 0.4326 | 1.5713 | 0.7136 |
| L1_full_dynamic | 0.9496 | 1.2978 | 0.0040 | 0.6866 | 0.2968 | 0.4251 | 1.5674 | 0.7657 |
| M7_like_compact_weather_ridge | 0.9542 | 1.3130 | 0.0039 | 0.6793 | 0.2701 | 0.4022 | 1.5875 | 0.7196 |
| L1_proxy_weather_time | 1.0082 | 1.3440 | 0.0030 | 0.6639 | 0.1446 | 0.2470 | 1.7530 | 0.9343 |
| L1_proxy_weather_radiation | 1.0099 | 1.3865 | 0.0023 | 0.6423 | 0.2793 | 0.3893 | 1.7203 | 0.7175 |

## Deltas vs proxy-only

Negative deltas for MAE/RMSE/high-tail MAE/worst-station absolute bias are improvements. Positive deltas for recall/F1 are improvements.

### hourly_mean
| ablation_model | MAE_vs_proxy | RMSE_vs_proxy | fixed_31_F1_vs_proxy | fixed_31_recall_vs_proxy | MAE_official_ge_31_vs_proxy | worst_station_abs_bias_vs_proxy |
| --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | -0.2440 | -0.2283 | 0.1646 | 0.0947 | -0.8130 | 0.0484 |
| L1_proxy_inertia | -0.1836 | -0.1631 | 0.0463 | 0.0241 | -0.6015 | 0.0466 |
| L1_proxy_only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| L1_proxy_radiation | -0.1916 | -0.1559 | 0.1309 | 0.0738 | -0.6810 | 0.0635 |
| L1_proxy_time | -0.1538 | -0.1430 | 0.0126 | 0.0064 | -0.4280 | 0.0146 |
| L1_proxy_weather | -0.0685 | -0.0748 |  | -0.0016 | -0.1597 | 0.3094 |
| L1_proxy_weather_inertia | -0.1830 | -0.1628 | 0.0095 | 0.0048 | -0.5845 | 0.1123 |
| L1_proxy_weather_radiation | -0.1918 | -0.1616 | 0.1016 | 0.0562 | -0.6679 | 0.0659 |
| L1_proxy_weather_time | -0.1869 | -0.1856 | 0.0064 | 0.0032 | -0.5381 | 0.2073 |
| M4_like_inertia_ridge | -0.2552 | -0.2475 | 0.1684 | 0.0963 | -0.7927 | 0.0486 |
| M7_like_compact_weather_ridge | -0.2380 | -0.2150 | 0.1272 | 0.0706 | -0.7699 | 0.0517 |

### hourly_max
| ablation_model | MAE_vs_proxy | RMSE_vs_proxy | fixed_31_F1_vs_proxy | fixed_31_recall_vs_proxy | MAE_official_ge_31_vs_proxy | worst_station_abs_bias_vs_proxy |
| --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | -0.3144 | -0.2942 | 0.3439 | 0.2542 | -0.8138 | 0.0113 |
| L1_proxy_inertia | -0.2380 | -0.2079 | 0.2609 | 0.1839 | -0.6206 | -0.0538 |
| L1_proxy_only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| L1_proxy_radiation | -0.2538 | -0.2019 | 0.3034 | 0.2341 | -0.6633 | -0.0375 |
| L1_proxy_time | -0.2232 | -0.2082 | 0.1167 | 0.0694 | -0.5338 | -0.0910 |
| L1_proxy_weather | -0.0906 | -0.0912 | -0.0583 | -0.0309 | -0.1971 | 0.3552 |
| L1_proxy_weather_inertia | -0.2393 | -0.2085 | 0.2310 | 0.1555 | -0.6230 | 0.0717 |
| L1_proxy_weather_radiation | -0.2540 | -0.2056 | 0.3080 | 0.2366 | -0.6609 | -0.0369 |
| L1_proxy_weather_time | -0.2557 | -0.2481 | 0.1657 | 0.1020 | -0.6282 | 0.1799 |
| M4_like_inertia_ridge | -0.3274 | -0.3194 | 0.3513 | 0.2592 | -0.8100 | -0.0408 |
| M7_like_compact_weather_ridge | -0.3098 | -0.2791 | 0.3210 | 0.2274 | -0.7938 | -0.0348 |

## Deltas vs M4 / full_dynamic

### vs M4_like_inertia_ridge, hourly_mean
| ablation_model | MAE_vs_m4 | RMSE_vs_m4 | fixed_31_F1_vs_m4 | fixed_31_recall_vs_m4 | MAE_official_ge_31_vs_m4 | worst_station_abs_bias_vs_m4 |
| --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | 0.0112 | 0.0192 | -0.0038 | -0.0016 | -0.0203 | -0.0002 |
| L1_proxy_inertia | 0.0716 | 0.0844 | -0.1221 | -0.0722 | 0.1912 | -0.0020 |
| L1_proxy_only | 0.2552 | 0.2475 | -0.1684 | -0.0963 | 0.7927 | -0.0486 |
| L1_proxy_radiation | 0.0636 | 0.0916 | -0.0375 | -0.0225 | 0.1117 | 0.0149 |
| L1_proxy_time | 0.1014 | 0.1045 | -0.1557 | -0.0899 | 0.3647 | -0.0340 |
| L1_proxy_weather | 0.1868 | 0.1728 |  | -0.0979 | 0.6330 | 0.2608 |
| L1_proxy_weather_inertia | 0.0723 | 0.0847 | -0.1589 | -0.0915 | 0.2082 | 0.0637 |
| L1_proxy_weather_radiation | 0.0634 | 0.0859 | -0.0668 | -0.0401 | 0.1248 | 0.0174 |
| L1_proxy_weather_time | 0.0683 | 0.0619 | -0.1620 | -0.0931 | 0.2546 | 0.1588 |
| M4_like_inertia_ridge | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| M7_like_compact_weather_ridge | 0.0172 | 0.0325 | -0.0412 | -0.0257 | 0.0228 | 0.0031 |

### vs M4_like_inertia_ridge, hourly_max
| ablation_model | MAE_vs_m4 | RMSE_vs_m4 | fixed_31_F1_vs_m4 | fixed_31_recall_vs_m4 | MAE_official_ge_31_vs_m4 | worst_station_abs_bias_vs_m4 |
| --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | 0.0130 | 0.0252 | -0.0074 | -0.0050 | -0.0038 | 0.0521 |
| L1_proxy_inertia | 0.0895 | 0.1115 | -0.0904 | -0.0753 | 0.1893 | -0.0130 |
| L1_proxy_only | 0.3274 | 0.3194 | -0.3513 | -0.2592 | 0.8100 | 0.0408 |
| L1_proxy_radiation | 0.0736 | 0.1175 | -0.0479 | -0.0251 | 0.1467 | 0.0033 |
| L1_proxy_time | 0.1043 | 0.1112 | -0.2347 | -0.1898 | 0.2762 | -0.0502 |
| L1_proxy_weather | 0.2368 | 0.2282 | -0.4096 | -0.2901 | 0.6129 | 0.3960 |
| L1_proxy_weather_inertia | 0.0881 | 0.1109 | -0.1203 | -0.1037 | 0.1870 | 0.1125 |
| L1_proxy_weather_radiation | 0.0734 | 0.1138 | -0.0433 | -0.0226 | 0.1491 | 0.0040 |
| L1_proxy_weather_time | 0.0717 | 0.0713 | -0.1856 | -0.1572 | 0.1817 | 0.2207 |
| M4_like_inertia_ridge | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| M7_like_compact_weather_ridge | 0.0176 | 0.0403 | -0.0304 | -0.0318 | 0.0162 | 0.0061 |

### vs L1_full_dynamic, hourly_mean
| ablation_model | MAE_vs_full_dynamic | RMSE_vs_full_dynamic | fixed_31_F1_vs_full_dynamic | fixed_31_recall_vs_full_dynamic | MAE_official_ge_31_vs_full_dynamic | worst_station_abs_bias_vs_full_dynamic |
| --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| L1_proxy_inertia | 0.0604 | 0.0652 | -0.1184 | -0.0706 | 0.2115 | -0.0018 |
| L1_proxy_only | 0.2440 | 0.2283 | -0.1646 | -0.0947 | 0.8130 | -0.0484 |
| L1_proxy_radiation | 0.0524 | 0.0724 | -0.0337 | -0.0209 | 0.1319 | 0.0151 |
| L1_proxy_time | 0.0902 | 0.0853 | -0.1520 | -0.0883 | 0.3850 | -0.0338 |
| L1_proxy_weather | 0.1756 | 0.1535 |  | -0.0963 | 0.6533 | 0.2610 |
| L1_proxy_weather_inertia | 0.0611 | 0.0655 | -0.1551 | -0.0899 | 0.2285 | 0.0639 |
| L1_proxy_weather_radiation | 0.0522 | 0.0667 | -0.0630 | -0.0385 | 0.1451 | 0.0176 |
| L1_proxy_weather_time | 0.0572 | 0.0427 | -0.1582 | -0.0915 | 0.2749 | 0.1590 |
| M4_like_inertia_ridge | -0.0112 | -0.0192 | 0.0038 | 0.0016 | 0.0203 | 0.0002 |
| M7_like_compact_weather_ridge | 0.0060 | 0.0133 | -0.0374 | -0.0241 | 0.0431 | 0.0033 |

### vs L1_full_dynamic, hourly_max
| ablation_model | MAE_vs_full_dynamic | RMSE_vs_full_dynamic | fixed_31_F1_vs_full_dynamic | fixed_31_recall_vs_full_dynamic | MAE_official_ge_31_vs_full_dynamic | worst_station_abs_bias_vs_full_dynamic |
| --- | --- | --- | --- | --- | --- | --- |
| L1_full_dynamic | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| L1_proxy_inertia | 0.0764 | 0.0864 | -0.0830 | -0.0702 | 0.1932 | -0.0651 |
| L1_proxy_only | 0.3144 | 0.2942 | -0.3439 | -0.2542 | 0.8138 | -0.0113 |
| L1_proxy_radiation | 0.0606 | 0.0924 | -0.0405 | -0.0201 | 0.1505 | -0.0488 |
| L1_proxy_time | 0.0912 | 0.0861 | -0.2272 | -0.1848 | 0.2801 | -0.1023 |
| L1_proxy_weather | 0.2238 | 0.2030 | -0.4021 | -0.2851 | 0.6167 | 0.3439 |
| L1_proxy_weather_inertia | 0.0751 | 0.0857 | -0.1129 | -0.0987 | 0.1908 | 0.0604 |
| L1_proxy_weather_radiation | 0.0604 | 0.0887 | -0.0359 | -0.0176 | 0.1529 | -0.0482 |
| L1_proxy_weather_time | 0.0587 | 0.0462 | -0.1782 | -0.1522 | 0.1856 | 0.1686 |
| M4_like_inertia_ridge | -0.0130 | -0.0252 | 0.0074 | 0.0050 | 0.0038 | -0.0521 |
| M7_like_compact_weather_ridge | 0.0046 | 0.0151 | -0.0229 | -0.0268 | 0.0200 | -0.0461 |

## High-tail findings

| dataset_label | ablation_model | MAE_official_ge_31 | bias_official_ge_31 | top_decile_residual_MAE | top_decile_residual_bias | official_ge_31_count | official_ge_33_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hourly_max | L1_full_dynamic | 1.5674 | -1.5083 | 1.6022 | -1.5505 | 1196 | 119 |
| hourly_max | M4_like_inertia_ridge | 1.5713 | -1.5252 | 1.6093 | -1.5708 | 1196 | 119 |
| hourly_max | M7_like_compact_weather_ridge | 1.5875 | -1.5448 | 1.6264 | -1.5889 | 1196 | 119 |
| hourly_max | L1_proxy_radiation | 1.7179 | -1.6606 | 1.7464 | -1.6922 | 1196 | 119 |
| hourly_max | L1_proxy_weather_radiation | 1.7203 | -1.6738 | 1.7493 | -1.7063 | 1196 | 119 |
| hourly_max | L1_proxy_weather_time | 1.7530 | -1.7455 | 1.8025 | -1.7966 | 1196 | 119 |
| hourly_max | L1_proxy_weather_inertia | 1.7583 | -1.7415 | 1.8005 | -1.7869 | 1196 | 119 |
| hourly_max | L1_proxy_inertia | 1.7606 | -1.7306 | 1.8006 | -1.7747 | 1196 | 119 |
| hourly_max | L1_proxy_time | 1.8475 | -1.8394 | 1.8991 | -1.8916 | 1196 | 119 |
| hourly_max | L1_proxy_weather | 2.1841 | -2.1825 | 2.2300 | -2.2291 | 1196 | 119 |
| hourly_max | L1_proxy_only | 2.3812 | -2.3785 | 2.4275 | -2.4251 | 1196 | 119 |
| hourly_mean | L1_full_dynamic | 1.8197 | -1.8128 | 1.5815 | -1.5534 | 623 | 30 |

## Station robustness

| dataset_label | ablation_model | worst_station_MAE | worst_station_MAE_station_id | worst_station_abs_bias | worst_station_abs_bias_station_id |
| --- | --- | --- | --- | --- | --- |
| hourly_max | L1_proxy_time | 1.3548 | S142 | 0.6634 | S137 |
| hourly_max | L1_proxy_inertia | 1.3208 | S142 | 0.7006 | S137 |
| hourly_max | M4_like_inertia_ridge | 1.2351 | S142 | 0.7136 | S139 |
| hourly_max | L1_proxy_radiation | 1.3150 | S142 | 0.7169 | S137 |
| hourly_max | L1_proxy_weather_radiation | 1.3079 | S142 | 0.7175 | S137 |
| hourly_max | M7_like_compact_weather_ridge | 1.2472 | S142 | 0.7196 | S139 |
| hourly_max | L1_proxy_only | 1.6717 | S139 | 0.7544 | S139 |
| hourly_max | L1_full_dynamic | 1.2308 | S142 | 0.7657 | S139 |
| hourly_max | L1_proxy_weather_inertia | 1.3177 | S142 | 0.8261 | S139 |
| hourly_max | L1_proxy_weather_time | 1.3804 | S139 | 0.9343 | S139 |
| hourly_max | L1_proxy_weather | 1.5726 | S139 | 1.1096 | S139 |
| hourly_mean | L1_proxy_only | 1.4703 | S139 | 0.6073 | S139 |

## Interpretation

For `hourly_mean`, the strongest MAE deltas versus proxy-only are:

| ablation_model | MAE_vs_proxy | fixed_31_F1_vs_proxy | fixed_31_recall_vs_proxy | MAE_official_ge_31_vs_proxy | worst_station_abs_bias_vs_proxy | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| M4_like_inertia_ridge | -0.2552 | 0.1684 | 0.0963 | -0.7927 | 0.0486 | practically meaningful candidate |
| L1_full_dynamic | -0.2440 | 0.1646 | 0.0947 | -0.8130 | 0.0484 | practically meaningful candidate |
| M7_like_compact_weather_ridge | -0.2380 | 0.1272 | 0.0706 | -0.7699 | 0.0517 | practically meaningful candidate |

For `hourly_max`, the strongest MAE deltas versus proxy-only are:

| ablation_model | MAE_vs_proxy | fixed_31_F1_vs_proxy | fixed_31_recall_vs_proxy | MAE_official_ge_31_vs_proxy | worst_station_abs_bias_vs_proxy | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| M4_like_inertia_ridge | -0.3274 | 0.3513 | 0.2592 | -0.8100 | -0.0408 | practically meaningful candidate |
| L1_full_dynamic | -0.3144 | 0.3439 | 0.2542 | -0.8138 | 0.0113 | practically meaningful candidate |
| M7_like_compact_weather_ridge | -0.3098 | 0.3210 | 0.2274 | -0.7938 | -0.0348 | practically meaningful candidate |

Treat MAE improvements below 0.01 C as negligible/noise, 0.01-0.03 C as directional/small, and at least 0.03 C as a practically meaningful candidate subject to high-tail and station robustness. These are Ridge ablation diagnostics only; they do not establish causal mechanisms.

## Caveats

- Formal-hourly OOF-derived metrics reference available: True. It is reference context only, not a new reproduction run.
- No blocked-time secondary validation was implemented in this sprint.
- No model family comparison was run.
- No formula-v2 was used.
- No Level 2 was used.
- No local WBGT prediction or 100m-cell WBGT surface was produced.
- `period_v09` exists but is non-numeric and was excluded from final Ridge features under the fixed numeric preprocessing rule.
- OOF predictions are local artifacts and should be treated as do-not-commit if size or review policy requires.

## Next recommended action

Run blocked-time secondary validation before promoting any dynamic feature group wording. If threshold behavior remains important, follow with high-tail/event calibration diagnostics focused on fixed_31 recall/F1 and station robustness.

## Outputs

- `outputs/v11_level1/feature_ablation/feature_ablation_manifest.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_metrics.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_delta_vs_proxy.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_delta_vs_full_dynamic.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_delta_vs_m4.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_high_tail_metrics.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_per_station_metrics.csv`
- `outputs/v11_level1/feature_ablation/oof_predictions_feature_ablation.csv`

## Provenance

- registry: `configs/v11/level1_feature_ablation_registry.yaml`
- evaluator sys.executable: `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe`
