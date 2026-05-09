# OpenHeat v0.9-beta WBGT calibration report

v0.9-beta evaluates non-ML calibration baselines for the raw physics WBGT proxy using period-specific metrics, thermal-inertia features and leave-one-station-out validation. No random split is used as primary evidence.

## Models
| model | description |
| --- | --- |
| M0_raw_proxy | Raw physics proxy; no calibration. |
| M1_global_bias | Train-set mean residual added to proxy. |
| M1b_period_bias | Train-set residual correction by period: daytime/nighttime/shoulder. |
| M2_linear_proxy | Linear proxy calibration; diagnostic slope model. |
| M3_regime_current_ridge | Ridge calibration with current weather regime. |
| M4_inertia_ridge | Ridge calibration with lagged/cumulative shortwave and dTair/dt. |
| M5_inertia_morphology_ridge | M4 plus station-nearest morphology; diagnostic where morphology is representative. |

## Apparent / in-sample: overall metrics
| model | n | bias_pred_minus_obs | mae | rmse | p90_abs_error |
| --- | --- | --- | --- | --- | --- |
| M5_inertia_morphology_ridge | 2564 | -0.0000 | 0.5350 | 0.7366 | 1.2568 |
| M4_inertia_ridge | 2564 | -0.0000 | 0.5710 | 0.7698 | 1.2969 |
| M3_regime_current_ridge | 2564 | -0.0000 | 0.5763 | 0.7771 | 1.3081 |
| M1b_period_bias | 2564 | -0.0000 | 0.6512 | 0.9069 | 1.5973 |
| M2_linear_proxy | 2564 | 0.0000 | 0.9632 | 1.2375 | 2.0055 |
| M1_global_bias | 2564 | -0.0000 | 1.3211 | 1.5807 | 2.5020 |
| M0_raw_proxy | 2564 | -1.1404 | 1.3248 | 1.9491 | 3.5884 |

## Leave-One-Station-Out CV: overall metrics
| model | n | bias_pred_minus_obs | mae | rmse | p90_abs_error |
| --- | --- | --- | --- | --- | --- |
| M4_inertia_ridge | 2564 | 0.0076 | 0.5946 | 0.7971 | 1.3374 |
| M3_regime_current_ridge | 2564 | 0.0055 | 0.5951 | 0.7986 | 1.3403 |
| M5_inertia_morphology_ridge | 2564 | -0.0816 | 0.6566 | 0.9135 | 1.5976 |
| M1b_period_bias | 2564 | 0.0000 | 0.6608 | 0.9161 | 1.6041 |
| M2_linear_proxy | 2564 | -0.0014 | 0.9733 | 1.2495 | 2.0245 |
| M1_global_bias | 2564 | 0.0000 | 1.3218 | 1.5838 | 2.5190 |
| M0_raw_proxy | 2564 | -1.1404 | 1.3248 | 1.9491 | 3.5884 |

## LOSO-CV metrics by period
| model | period | n | bias_pred_minus_obs | mae | rmse | p90_abs_error |
| --- | --- | --- | --- | --- | --- | --- |
| M4_inertia_ridge | daytime_09_18 | 971 | -0.0285 | 0.8361 | 1.0492 | 1.7454 |
| M3_regime_current_ridge | daytime_09_18 | 971 | -0.0248 | 0.8477 | 1.0603 | 1.7458 |
| M5_inertia_morphology_ridge | daytime_09_18 | 971 | -0.1134 | 0.8883 | 1.1189 | 1.8726 |
| M1b_period_bias | daytime_09_18 | 971 | 0.0001 | 1.0465 | 1.2986 | 2.1451 |
| M2_linear_proxy | daytime_09_18 | 971 | -0.6896 | 1.1869 | 1.5133 | 2.5535 |
| M1_global_bias | daytime_09_18 | 971 | -1.6582 | 1.7646 | 2.1030 | 3.3775 |
| M0_raw_proxy | daytime_09_18 | 971 | -2.7986 | 2.8024 | 3.0809 | 4.5061 |
| M0_raw_proxy | night_00_07_20_23 | 1161 | -0.1239 | 0.3740 | 0.4643 | 0.7327 |
| M1b_period_bias | night_00_07_20_23 | 1161 | -0.0000 | 0.3741 | 0.4600 | 0.6983 |
| M3_regime_current_ridge | night_00_07_20_23 | 1161 | -0.0005 | 0.3767 | 0.4696 | 0.7169 |
| M4_inertia_ridge | night_00_07_20_23 | 1161 | 0.0046 | 0.3794 | 0.4737 | 0.7168 |
| M5_inertia_morphology_ridge | night_00_07_20_23 | 1161 | -0.0834 | 0.4539 | 0.6893 | 0.8184 |
| M2_linear_proxy | night_00_07_20_23 | 1161 | 0.2582 | 0.7228 | 0.9209 | 1.5376 |
| M1_global_bias | night_00_07_20_23 | 1161 | 1.0164 | 1.0173 | 1.1141 | 1.5402 |
| M4_inertia_ridge | overall | 2564 | 0.0076 | 0.5946 | 0.7971 | 1.3374 |
| M3_regime_current_ridge | overall | 2564 | 0.0055 | 0.5951 | 0.7986 | 1.3403 |
| M5_inertia_morphology_ridge | overall | 2564 | -0.0816 | 0.6566 | 0.9135 | 1.5976 |
| M1b_period_bias | overall | 2564 | 0.0000 | 0.6608 | 0.9161 | 1.6041 |
| M2_linear_proxy | overall | 2564 | -0.0014 | 0.9733 | 1.2495 | 2.0245 |
| M1_global_bias | overall | 2564 | 0.0000 | 1.3218 | 1.5838 | 2.5190 |
| M0_raw_proxy | overall | 2564 | -1.1404 | 1.3248 | 1.9491 | 3.5884 |
| M4_inertia_ridge | peak_12_16 | 431 | -0.0470 | 0.8729 | 1.1036 | 1.8394 |
| M3_regime_current_ridge | peak_12_16 | 431 | -0.0532 | 0.8866 | 1.1224 | 1.8610 |
| M5_inertia_morphology_ridge | peak_12_16 | 431 | -0.1491 | 0.9453 | 1.1765 | 1.9530 |
| M1b_period_bias | peak_12_16 | 431 | -0.6087 | 1.0506 | 1.3150 | 2.1535 |
| M2_linear_proxy | peak_12_16 | 431 | -1.0902 | 1.4294 | 1.7713 | 2.9263 |
| M1_global_bias | peak_12_16 | 431 | -2.2670 | 2.2834 | 2.5460 | 3.7783 |
| M0_raw_proxy | peak_12_16 | 431 | -3.4074 | 3.4074 | 3.5968 | 4.9169 |

## LOSO-CV WBGT>=31 event detection
| model | period | tp | fp | fn | tn | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M3_regime_current_ridge | daytime_09_18 | 76 | 104 | 192 | 599 | 0.4222 | 0.2836 | 0.3393 |
| M4_inertia_ridge | daytime_09_18 | 70 | 86 | 198 | 617 | 0.4487 | 0.2612 | 0.3302 |
| M5_inertia_morphology_ridge | daytime_09_18 | 56 | 80 | 212 | 623 | 0.4118 | 0.2090 | 0.2772 |
| M2_linear_proxy | daytime_09_18 | 11 | 29 | 257 | 674 | 0.2750 | 0.0410 | 0.0714 |
| M1b_period_bias | daytime_09_18 | 8 | 14 | 260 | 689 | 0.3636 | 0.0299 | 0.0552 |
| M0_raw_proxy | daytime_09_18 | 0 | 0 | 268 | 703 |  | 0.0000 |  |
| M1_global_bias | daytime_09_18 | 0 | 0 | 268 | 703 |  | 0.0000 |  |
| M0_raw_proxy | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M1_global_bias | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M1b_period_bias | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M2_linear_proxy | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M3_regime_current_ridge | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M4_inertia_ridge | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M5_inertia_morphology_ridge | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M3_regime_current_ridge | overall | 76 | 104 | 192 | 2192 | 0.4222 | 0.2836 | 0.3393 |
| M4_inertia_ridge | overall | 70 | 86 | 198 | 2210 | 0.4487 | 0.2612 | 0.3302 |
| M5_inertia_morphology_ridge | overall | 56 | 80 | 212 | 2216 | 0.4118 | 0.2090 | 0.2772 |
| M2_linear_proxy | overall | 11 | 29 | 257 | 2267 | 0.2750 | 0.0410 | 0.0714 |
| M1b_period_bias | overall | 8 | 14 | 260 | 2282 | 0.3636 | 0.0299 | 0.0552 |
| M0_raw_proxy | overall | 0 | 0 | 268 | 2296 |  | 0.0000 |  |
| M1_global_bias | overall | 0 | 0 | 268 | 2296 |  | 0.0000 |  |
| M3_regime_current_ridge | peak_12_16 | 76 | 103 | 129 | 123 | 0.4246 | 0.3707 | 0.3958 |
| M4_inertia_ridge | peak_12_16 | 70 | 85 | 135 | 141 | 0.4516 | 0.3415 | 0.3889 |
| M5_inertia_morphology_ridge | peak_12_16 | 55 | 74 | 150 | 152 | 0.4264 | 0.2683 | 0.3293 |
| M2_linear_proxy | peak_12_16 | 9 | 24 | 196 | 202 | 0.2727 | 0.0439 | 0.0756 |
| M1b_period_bias | peak_12_16 | 8 | 12 | 197 | 214 | 0.4000 | 0.0390 | 0.0711 |
| M0_raw_proxy | peak_12_16 | 0 | 0 | 205 | 226 |  | 0.0000 |  |
| M1_global_bias | peak_12_16 | 0 | 0 | 205 | 226 |  | 0.0000 |  |

## LOSO-CV WBGT>=33 event detection
| model | period | tp | fp | fn | tn | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0_raw_proxy | daytime_09_18 | 0 | 0 | 10 | 961 |  | 0.0000 |  |
| M1_global_bias | daytime_09_18 | 0 | 0 | 10 | 961 |  | 0.0000 |  |
| M1b_period_bias | daytime_09_18 | 0 | 0 | 10 | 961 |  | 0.0000 |  |
| M2_linear_proxy | daytime_09_18 | 0 | 0 | 10 | 961 |  | 0.0000 |  |
| M3_regime_current_ridge | daytime_09_18 | 0 | 0 | 10 | 961 |  | 0.0000 |  |
| M4_inertia_ridge | daytime_09_18 | 0 | 0 | 10 | 961 |  | 0.0000 |  |
| M5_inertia_morphology_ridge | daytime_09_18 | 0 | 0 | 10 | 961 |  | 0.0000 |  |
| M0_raw_proxy | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M1_global_bias | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M1b_period_bias | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M2_linear_proxy | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M3_regime_current_ridge | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M4_inertia_ridge | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M5_inertia_morphology_ridge | night_00_07_20_23 | 0 | 0 | 0 | 1161 |  |  |  |
| M0_raw_proxy | overall | 0 | 0 | 10 | 2554 |  | 0.0000 |  |
| M1_global_bias | overall | 0 | 0 | 10 | 2554 |  | 0.0000 |  |
| M1b_period_bias | overall | 0 | 0 | 10 | 2554 |  | 0.0000 |  |
| M2_linear_proxy | overall | 0 | 0 | 10 | 2554 |  | 0.0000 |  |
| M3_regime_current_ridge | overall | 0 | 0 | 10 | 2554 |  | 0.0000 |  |
| M4_inertia_ridge | overall | 0 | 0 | 10 | 2554 |  | 0.0000 |  |
| M5_inertia_morphology_ridge | overall | 0 | 0 | 10 | 2554 |  | 0.0000 |  |
| M0_raw_proxy | peak_12_16 | 0 | 0 | 10 | 421 |  | 0.0000 |  |
| M1_global_bias | peak_12_16 | 0 | 0 | 10 | 421 |  | 0.0000 |  |
| M1b_period_bias | peak_12_16 | 0 | 0 | 10 | 421 |  | 0.0000 |  |
| M2_linear_proxy | peak_12_16 | 0 | 0 | 10 | 421 |  | 0.0000 |  |
| M3_regime_current_ridge | peak_12_16 | 0 | 0 | 10 | 421 |  | 0.0000 |  |
| M4_inertia_ridge | peak_12_16 | 0 | 0 | 10 | 421 |  | 0.0000 |  |
| M5_inertia_morphology_ridge | peak_12_16 | 0 | 0 | 10 | 421 |  | 0.0000 |  |

## Linear slope diagnostics
| model | split_type | heldout_station_id | intercept | slope | n_train | n_test | slope_warning |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M2_linear_proxy | apparent | ALL | -23.6914 | 1.9463 | 2564 | 2564 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S124 | -23.8376 | 1.9531 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S125 | -25.0917 | 1.9990 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S126 | -23.3877 | 1.9344 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S127 | -23.2277 | 1.9281 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S128 | -23.2233 | 1.9280 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S129 | -23.5386 | 1.9405 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S130 | -23.5773 | 1.9415 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S132 | -24.1759 | 1.9643 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S135 | -23.4345 | 1.9364 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S137 | -23.5173 | 1.9391 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S139 | -23.9345 | 1.9569 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S140 | -23.9519 | 1.9567 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S141 | -23.5633 | 1.9412 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S142 | -23.1860 | 1.9260 | 2470 | 94 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S143 | -24.2983 | 1.9690 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S144 | -23.3828 | 1.9344 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S145 | -24.2352 | 1.9668 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S146 | -23.5366 | 1.9410 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S147 | -23.1806 | 1.9268 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S148 | -23.8974 | 1.9555 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S149 | -23.7455 | 1.9495 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S150 | -23.5272 | 1.9407 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S151 | -23.3252 | 1.9324 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S153 | -24.1165 | 1.9622 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S180 | -23.7929 | 1.9501 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S184 | -23.9126 | 1.9545 | 2469 | 95 | slope_gt_1_5_range_expansion |
| M2_linear_proxy | LOSO | S187 | -23.2562 | 1.9300 | 2469 | 95 | slope_gt_1_5_range_expansion |

## Station-level LOSO preview
| model | station_id | station_name | n | bias_pred_minus_obs | mae | rmse | p90_abs_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M0_raw_proxy | S148 | Pasir Ris Walk | 95 | -0.5891 | 0.7747 | 1.2957 | 2.4791 |
| M0_raw_proxy | S124 | Upper Changi Road North | 95 | -0.5733 | 0.8055 | 1.2061 | 2.2353 |
| M0_raw_proxy | S149 | Tampines Walk | 95 | -0.7217 | 1.0042 | 1.5694 | 3.0851 |
| M0_raw_proxy | S140 | Choa Chu Kang Stadium | 95 | -0.7009 | 1.0301 | 1.4645 | 2.5308 |
| M0_raw_proxy | S145 | MacRitchie Reservoir | 95 | -1.0000 | 1.0728 | 1.6250 | 3.1759 |
| M0_raw_proxy | S150 | Evans Road | 95 | -0.7450 | 1.0993 | 1.5650 | 2.6665 |
| M0_raw_proxy | S180 | Taman Jurong Greens | 95 | -1.0314 | 1.1932 | 1.7807 | 3.1911 |
| M0_raw_proxy | S146 | Jalan Bahar | 95 | -0.6257 | 1.1983 | 1.5593 | 2.7350 |
| M0_raw_proxy | S153 | Bukit Batok Street 22 | 95 | -1.2104 | 1.2626 | 1.7569 | 3.1744 |
| M0_raw_proxy | S184 | Sengkang East Avenue | 95 | -1.2638 | 1.2773 | 1.8208 | 3.3172 |
| M0_raw_proxy | S151 | Outward Bound Singapore(Pulau ubin) | 95 | -1.1674 | 1.2784 | 2.1251 | 4.4203 |
| M0_raw_proxy | S143 | Punggol North | 95 | -1.2559 | 1.2923 | 1.7789 | 3.1519 |
| M0_raw_proxy | S141 | Yio Chu Kang Stadium | 95 | -1.2249 | 1.3129 | 2.0517 | 3.9704 |
| M0_raw_proxy | S132 | Jurong West Street 93 | 95 | -1.3345 | 1.3345 | 1.8264 | 3.4186 |
| M0_raw_proxy | S129 | Bedok North Street 2 | 95 | -1.3943 | 1.3968 | 2.0574 | 3.5779 |
| M0_raw_proxy | S147 | Marina Barrage | 95 | -1.3019 | 1.3979 | 2.2154 | 4.3361 |
| M0_raw_proxy | S144 | Upper Pickering Street | 95 | -1.4177 | 1.4177 | 2.0337 | 3.4444 |
| M0_raw_proxy | S187 | Bukit Timah(West) | 95 | -1.0303 | 1.4270 | 2.1618 | 4.0730 |
| M0_raw_proxy | S139 | Tuas Terminal Gateway | 95 | -0.6328 | 1.4449 | 1.7709 | 2.9253 |
| M0_raw_proxy | S130 | West Coast Road | 95 | -1.4713 | 1.4740 | 1.9767 | 3.5322 |
| M0_raw_proxy | S125 | Woodlands Street 13 | 95 | -1.2210 | 1.4754 | 1.9353 | 3.5502 |
| M0_raw_proxy | S135 | Mandai Wildlife Reserve | 95 | -0.9178 | 1.4975 | 2.1223 | 3.7775 |
| M0_raw_proxy | S126 | Old Chua Chu Kang Road | 95 | -1.2651 | 1.5029 | 2.2699 | 4.2897 |
| M0_raw_proxy | S128 | Bishan Street | 95 | -1.4438 | 1.5439 | 2.4388 | 4.4742 |
| M0_raw_proxy | S127 | Stadium Road | 95 | -1.6682 | 1.6682 | 2.3459 | 4.2545 |
| M0_raw_proxy | S137 | Sakra Road | 95 | -1.6732 | 1.6754 | 2.1435 | 3.5964 |
| M0_raw_proxy | S142 | Sentosa Palawan Green | 94 | -1.9164 | 1.9178 | 2.8487 | 5.2131 |
| M1_global_bias | S132 | Jurong West Street 93 | 95 | -0.2017 | 0.9410 | 1.2630 | 2.2857 |
| M1_global_bias | S184 | Sengkang East Avenue | 95 | -0.1282 | 1.0099 | 1.3169 | 2.1816 |
| M1_global_bias | S143 | Punggol North | 95 | -0.1199 | 1.0141 | 1.2656 | 2.0159 |
| M1_global_bias | S153 | Bukit Batok Street 22 | 95 | -0.0727 | 1.0289 | 1.2756 | 2.0367 |
| M1_global_bias | S124 | Upper Changi Road North | 95 | 0.5889 | 1.0904 | 1.2136 | 1.8364 |
| M1_global_bias | S130 | West Coast Road | 95 | -0.3437 | 1.1068 | 1.3641 | 2.4046 |
| M1_global_bias | S137 | Sakra Road | 95 | -0.5533 | 1.1213 | 1.4496 | 2.4765 |
| M1_global_bias | S145 | MacRitchie Reservoir | 95 | 0.1458 | 1.1250 | 1.2892 | 2.0301 |
| M1_global_bias | S125 | Woodlands Street 13 | 95 | -0.0837 | 1.1475 | 1.5039 | 2.6266 |
| M1_global_bias | S148 | Pasir Ris Walk | 95 | 0.5725 | 1.1830 | 1.2883 | 1.6919 |
| M1_global_bias | S144 | Upper Pickering Street | 95 | -0.2880 | 1.1872 | 1.4863 | 2.3147 |
| M1_global_bias | S129 | Bedok North Street 2 | 95 | -0.2637 | 1.1875 | 1.5357 | 2.4474 |
| M1_global_bias | S140 | Choa Chu Kang Stadium | 95 | 0.4564 | 1.2648 | 1.3645 | 1.9288 |
| M1_global_bias | S180 | Taman Jurong Greens | 95 | 0.1131 | 1.2973 | 1.4560 | 2.0465 |
| M1_global_bias | S149 | Tampines Walk | 95 | 0.4347 | 1.3262 | 1.4599 | 1.9286 |
| M1_global_bias | S141 | Yio Chu Kang Stadium | 95 | -0.0878 | 1.3376 | 1.6482 | 2.8333 |
| M1_global_bias | S150 | Evans Road | 95 | 0.4105 | 1.3679 | 1.4362 | 1.8142 |
| M1_global_bias | S127 | Stadium Road | 95 | -0.5482 | 1.3765 | 1.7381 | 3.1345 |
| M1_global_bias | S146 | Jalan Bahar | 95 | 0.5345 | 1.4188 | 1.5250 | 1.9565 |
| M1_global_bias | S151 | Outward Bound Singapore(Pulau ubin) | 95 | -0.0281 | 1.5000 | 1.7760 | 3.2810 |
| M1_global_bias | S147 | Marina Barrage | 95 | -0.1678 | 1.5108 | 1.8003 | 3.2020 |
| M1_global_bias | S139 | Tuas Terminal Gateway | 95 | 0.5271 | 1.6140 | 1.7359 | 2.5211 |
| M1_global_bias | S128 | Bishan Street | 95 | -0.3151 | 1.6589 | 1.9906 | 3.3455 |
| M1_global_bias | S126 | Old Chua Chu Kang Road | 95 | -0.1295 | 1.6939 | 1.8891 | 3.1542 |
| M1_global_bias | S142 | Sentosa Palawan Green | 94 | -0.8056 | 1.7082 | 2.2565 | 4.1022 |
| M1_global_bias | S187 | Bukit Timah(West) | 95 | 0.1143 | 1.7103 | 1.9039 | 2.9284 |
| M1_global_bias | S135 | Mandai Wildlife Reserve | 95 | 0.2311 | 1.7641 | 1.9275 | 2.6286 |
| M1b_period_bias | S180 | Taman Jurong Greens | 95 | 0.1138 | 0.4881 | 0.6783 | 1.2469 |
| M1b_period_bias | S130 | West Coast Road | 95 | -0.3431 | 0.5394 | 0.6955 | 1.1064 |
| M1b_period_bias | S145 | MacRitchie Reservoir | 95 | 0.1465 | 0.5400 | 0.7811 | 1.2375 |
| M1b_period_bias | S144 | Upper Pickering Street | 95 | -0.2873 | 0.5445 | 0.7816 | 1.4284 |
| M1b_period_bias | S129 | Bedok North Street 2 | 95 | -0.2631 | 0.5661 | 0.8650 | 1.3744 |
| M1b_period_bias | S150 | Evans Road | 95 | 0.4112 | 0.5782 | 0.7435 | 1.1144 |
| ... |  |  |  |  |  |  |  |

## Interpretation notes
- M1 global bias correction must be interpreted with day/night metrics because it may improve daytime underprediction while worsening night-time overprediction.
- M2 linear proxy calibration is diagnostic; large slopes indicate proxy dynamic-range compression and can be unsafe for external operation.
- M4/M5 include lagged/cumulative shortwave features to represent thermal inertia and afternoon residual peaks.
- LOSO-CV is the primary validation because random splits leak station/time structure and are not appropriate for deployment to unobserved grid cells.
- This remains a 24h pilot archive, not final ML/calibration validation.