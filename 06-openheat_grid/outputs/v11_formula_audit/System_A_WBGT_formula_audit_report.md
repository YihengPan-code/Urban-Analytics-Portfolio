# System A WBGT formula sensitivity audit

## Scope

This is a companion sensitivity audit for System A. It does not retroactively recalibrate the v1.1-beta-formal results.

## Inputs

- Snapshot: `data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv`
- Target: `official_wbgt_c`

## Formula metrics

| formula                             | n     | bias_pred_minus_obs | mae      | rmse     | r2       | pred_mean | obs_mean  |
| ----------------------------------- | ----- | ------------------- | -------- | -------- | -------- | --------- | --------- |
| stull_simple_globe_k0p0065          | 40389 | -0.821547           | 1.253325 | 1.726936 | 0.346560 | 26.174726 | 26.996274 |
| stull_simple_globe_k0p0055          | 40389 | -0.839113           | 1.263170 | 1.743590 | 0.333897 | 26.157161 | 26.996274 |
| existing_v09_proxy                  | 40389 | -0.856679           | 1.273195 | 1.760567 | 0.320862 | 26.139595 | 26.996274 |
| reconstructed_from_v09_components   | 40389 | -0.856679           | 1.273195 | 1.760567 | 0.320862 | 26.139595 | 26.996274 |
| stull_simple_globe_k0p0045          | 40389 | -0.856679           | 1.273195 | 1.760567 | 0.320862 | 26.139595 | 26.996274 |
| stull_simple_globe_k0p0035          | 40389 | -0.874245           | 1.283368 | 1.777860 | 0.307455 | 26.122029 | 26.996274 |
| stull_simple_globe_k0p0025          | 40389 | -0.891810           | 1.293698 | 1.795459 | 0.293676 | 26.104463 | 26.996274 |
| no_radiation_sensitivity_tg_eq_tair | 40389 | -0.935725           | 1.320454 | 1.840738 | 0.257601 | 26.060549 | 26.996274 |

## Raw formula distribution summary

| formula                             | n     | min       | p01       | p05       | p25       | p50       | p75       | p90       | p95       | p99       | max       | mean      |
| ----------------------------------- | ----- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- |
| existing_v09_proxy                  | 40419 | 23.021999 | 23.725465 | 24.227941 | 25.268714 | 26.155584 | 27.043803 | 27.668711 | 27.967162 | 28.534765 | 29.235366 | 26.140359 |
| reconstructed_from_v09_components   | 40419 | 23.021999 | 23.725465 | 24.227941 | 25.268714 | 26.155584 | 27.043803 | 27.668711 | 27.967162 | 28.534765 | 29.235366 | 26.140359 |
| stull_simple_globe_k0p0025          | 40419 | 23.021999 | 23.725465 | 24.227941 | 25.265593 | 26.137095 | 26.981505 | 27.570086 | 27.851110 | 28.406362 | 29.053975 | 26.105177 |
| stull_simple_globe_k0p0035          | 40419 | 23.021999 | 23.725465 | 24.227941 | 25.268714 | 26.148513 | 27.016121 | 27.627819 | 27.908167 | 28.470564 | 29.144670 | 26.122768 |
| stull_simple_globe_k0p0045          | 40419 | 23.021999 | 23.725465 | 24.227941 | 25.268714 | 26.155584 | 27.043803 | 27.668711 | 27.967162 | 28.534765 | 29.235366 | 26.140359 |
| stull_simple_globe_k0p0055          | 40419 | 23.021999 | 23.725465 | 24.227941 | 25.268714 | 26.160480 | 27.070349 | 27.717624 | 28.020619 | 28.604639 | 29.326061 | 26.157949 |
| stull_simple_globe_k0p0065          | 40419 | 23.021999 | 23.725465 | 24.227941 | 25.268714 | 26.163728 | 27.106161 | 27.769598 | 28.067507 | 28.678506 | 29.434284 | 26.175540 |
| no_radiation_sensitivity_tg_eq_tair | 40419 | 23.021999 | 23.725465 | 24.227941 | 25.265593 | 26.065764 | 26.899413 | 27.437619 | 27.719988 | 28.245859 | 28.827236 | 26.061201 |

## Threshold confusion matrix

The fixed_31/fixed_33 raw confusion rows are all-zero on predicted positives because every raw formula variant remains below the 31C and 33C score thresholds in this snapshot.

| formula                             | event_threshold_c | score_threshold_c | n_obs | n_event_obs | tp | fp | fn   | tn    | precision | recall   | f1 |
| ----------------------------------- | ----------------- | ----------------- | ----- | ----------- | -- | -- | ---- | ----- | --------- | -------- | -- |
| existing_v09_proxy                  | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| existing_v09_proxy                  | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| reconstructed_from_v09_components   | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| reconstructed_from_v09_components   | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0025          | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0025          | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0035          | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0035          | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0045          | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0045          | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0055          | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0055          | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0065          | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0065          | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| no_radiation_sensitivity_tg_eq_tair | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| no_radiation_sensitivity_tg_eq_tair | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |

## Threshold-sweep operating points

Score thresholds are scanned from 27.0C to 34.0C in 0.05C increments. The recall_90 row selects the highest-precision threshold with recall >= 0.90 when available; precision_70 selects the highest-recall threshold with precision >= 0.70 when available.

| formula                             | event_threshold_c | operating_point | threshold_c | precision | recall   | f1       | tp     | fp      | fn     |
| ----------------------------------- | ----------------- | --------------- | ----------- | --------- | -------- | -------- | ------ | ------- | ------ |
| existing_v09_proxy                  | 31.000000         | fixed_31        | 31.000000   |           | 0.000000 |          | 0.0    | 0.0     | 2844.0 |
| existing_v09_proxy                  | 31.000000         | best_F1         | 27.550000   | 0.342289  | 0.604782 | 0.437158 | 1720.0 | 3305.0  | 1124.0 |
| existing_v09_proxy                  | 31.000000         | recall_90       |             |           |          |          |        |         |        |
| existing_v09_proxy                  | 31.000000         | precision_70    | 29.150000   | 0.750000  | 0.003165 | 0.006303 | 9.0    | 3.0     | 2835.0 |
| existing_v09_proxy                  | 33.000000         | fixed_33        | 33.000000   |           | 0.000000 |          | 0.0    | 0.0     | 212.0  |
| existing_v09_proxy                  | 33.000000         | best_F1         | 28.250000   | 0.050829  | 0.216981 | 0.082363 | 46.0   | 859.0   | 166.0  |
| existing_v09_proxy                  | 33.000000         | recall_90       | 27.000000   | 0.018166  | 0.905660 | 0.035618 | 192.0  | 10377.0 | 20.0   |
| existing_v09_proxy                  | 33.000000         | precision_70    |             |           |          |          |        |         |        |
| reconstructed_from_v09_components   | 31.000000         | fixed_31        | 31.000000   |           | 0.000000 |          | 0.0    | 0.0     | 2844.0 |
| reconstructed_from_v09_components   | 31.000000         | best_F1         | 27.550000   | 0.342289  | 0.604782 | 0.437158 | 1720.0 | 3305.0  | 1124.0 |
| reconstructed_from_v09_components   | 31.000000         | recall_90       |             |           |          |          |        |         |        |
| reconstructed_from_v09_components   | 31.000000         | precision_70    | 29.150000   | 0.750000  | 0.003165 | 0.006303 | 9.0    | 3.0     | 2835.0 |
| reconstructed_from_v09_components   | 33.000000         | fixed_33        | 33.000000   |           | 0.000000 |          | 0.0    | 0.0     | 212.0  |
| reconstructed_from_v09_components   | 33.000000         | best_F1         | 28.250000   | 0.050829  | 0.216981 | 0.082363 | 46.0   | 859.0   | 166.0  |
| reconstructed_from_v09_components   | 33.000000         | recall_90       | 27.000000   | 0.018166  | 0.905660 | 0.035618 | 192.0  | 10377.0 | 20.0   |
| reconstructed_from_v09_components   | 33.000000         | precision_70    |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0025          | 31.000000         | fixed_31        | 31.000000   |           | 0.000000 |          | 0.0    | 0.0     | 2844.0 |
| stull_simple_globe_k0p0025          | 31.000000         | best_F1         | 27.450000   | 0.334690  | 0.607243 | 0.431534 | 1727.0 | 3433.0  | 1117.0 |
| stull_simple_globe_k0p0025          | 31.000000         | recall_90       |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0025          | 31.000000         | precision_70    | 29.000000   | 1.000000  | 0.001406 | 0.002809 | 4.0    | 0.0     | 2840.0 |
| stull_simple_globe_k0p0025          | 33.000000         | fixed_33        | 33.000000   |           | 0.000000 |          | 0.0    | 0.0     | 212.0  |
| stull_simple_globe_k0p0025          | 33.000000         | best_F1         | 28.150000   | 0.053179  | 0.216981 | 0.085422 | 46.0   | 819.0   | 166.0  |
| stull_simple_globe_k0p0025          | 33.000000         | recall_90       |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0025          | 33.000000         | precision_70    |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0035          | 31.000000         | fixed_31        | 31.000000   |           | 0.000000 |          | 0.0    | 0.0     | 2844.0 |
| stull_simple_globe_k0p0035          | 31.000000         | best_F1         | 27.450000   | 0.328425  | 0.643108 | 0.434803 | 1829.0 | 3740.0  | 1015.0 |
| stull_simple_globe_k0p0035          | 31.000000         | recall_90       |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0035          | 31.000000         | precision_70    | 29.050000   | 0.812500  | 0.004571 | 0.009091 | 13.0   | 3.0     | 2831.0 |
| stull_simple_globe_k0p0035          | 33.000000         | fixed_33        | 33.000000   |           | 0.000000 |          | 0.0    | 0.0     | 212.0  |
| stull_simple_globe_k0p0035          | 33.000000         | best_F1         | 28.200000   | 0.051744  | 0.216981 | 0.083560 | 46.0   | 843.0   | 166.0  |
| stull_simple_globe_k0p0035          | 33.000000         | recall_90       |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0035          | 33.000000         | precision_70    |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0045          | 31.000000         | fixed_31        | 31.000000   |           | 0.000000 |          | 0.0    | 0.0     | 2844.0 |
| stull_simple_globe_k0p0045          | 31.000000         | best_F1         | 27.550000   | 0.342289  | 0.604782 | 0.437158 | 1720.0 | 3305.0  | 1124.0 |
| stull_simple_globe_k0p0045          | 31.000000         | recall_90       |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0045          | 31.000000         | precision_70    | 29.150000   | 0.750000  | 0.003165 | 0.006303 | 9.0    | 3.0     | 2835.0 |
| stull_simple_globe_k0p0045          | 33.000000         | fixed_33        | 33.000000   |           | 0.000000 |          | 0.0    | 0.0     | 212.0  |
| stull_simple_globe_k0p0045          | 33.000000         | best_F1         | 28.250000   | 0.050829  | 0.216981 | 0.082363 | 46.0   | 859.0   | 166.0  |
| stull_simple_globe_k0p0045          | 33.000000         | recall_90       | 27.000000   | 0.018166  | 0.905660 | 0.035618 | 192.0  | 10377.0 | 20.0   |
| stull_simple_globe_k0p0045          | 33.000000         | precision_70    |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0055          | 31.000000         | fixed_31        | 31.000000   |           | 0.000000 |          | 0.0    | 0.0     | 2844.0 |
| stull_simple_globe_k0p0055          | 31.000000         | best_F1         | 27.600000   | 0.345229  | 0.605485 | 0.439734 | 1722.0 | 3266.0  | 1122.0 |
| stull_simple_globe_k0p0055          | 31.000000         | recall_90       |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0055          | 31.000000         | precision_70    |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0055          | 33.000000         | fixed_33        | 33.000000   |           | 0.000000 |          | 0.0    | 0.0     | 212.0  |
| stull_simple_globe_k0p0055          | 33.000000         | best_F1         | 28.350000   | 0.053118  | 0.216981 | 0.085343 | 46.0   | 820.0   | 166.0  |
| stull_simple_globe_k0p0055          | 33.000000         | recall_90       | 27.000000   | 0.018472  | 0.943396 | 0.036235 | 200.0  | 10627.0 | 12.0   |
| stull_simple_globe_k0p0055          | 33.000000         | precision_70    |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0065          | 31.000000         | fixed_31        | 31.000000   |           | 0.000000 |          | 0.0    | 0.0     | 2844.0 |
| stull_simple_globe_k0p0065          | 31.000000         | best_F1         | 27.650000   | 0.347286  | 0.609705 | 0.442516 | 1734.0 | 3259.0  | 1110.0 |
| stull_simple_globe_k0p0065          | 31.000000         | recall_90       | 27.000000   | 0.232783  | 0.912799 | 0.370963 | 2596.0 | 8556.0  | 248.0  |
| stull_simple_globe_k0p0065          | 31.000000         | precision_70    |             |           |          |          |        |         |        |
| stull_simple_globe_k0p0065          | 33.000000         | fixed_33        | 33.000000   |           | 0.000000 |          | 0.0    | 0.0     | 212.0  |
| stull_simple_globe_k0p0065          | 33.000000         | best_F1         | 28.400000   | 0.050998  | 0.216981 | 0.082585 | 46.0   | 856.0   | 166.0  |
| stull_simple_globe_k0p0065          | 33.000000         | recall_90       | 27.050000   | 0.018627  | 0.933962 | 0.036525 | 198.0  | 10432.0 | 14.0   |
| stull_simple_globe_k0p0065          | 33.000000         | precision_70    |             |           |          |          |        |         |        |
| no_radiation_sensitivity_tg_eq_tair | 31.000000         | fixed_31        | 31.000000   |           | 0.000000 |          | 0.0    | 0.0     | 2844.0 |
| no_radiation_sensitivity_tg_eq_tair | 31.000000         | best_F1         | 27.400000   | 0.348758  | 0.537975 | 0.423178 | 1530.0 | 2857.0  | 1314.0 |
| no_radiation_sensitivity_tg_eq_tair | 31.000000         | recall_90       |             |           |          |          |        |         |        |
| no_radiation_sensitivity_tg_eq_tair | 31.000000         | precision_70    | 28.750000   | 0.708333  | 0.005977 | 0.011855 | 17.0   | 7.0     | 2827.0 |
| no_radiation_sensitivity_tg_eq_tair | 33.000000         | fixed_33        | 33.000000   |           | 0.000000 |          | 0.0    | 0.0     | 212.0  |
| no_radiation_sensitivity_tg_eq_tair | 33.000000         | best_F1         | 28.000000   | 0.051402  | 0.207547 | 0.082397 | 44.0   | 812.0   | 168.0  |
| no_radiation_sensitivity_tg_eq_tair | 33.000000         | recall_90       |             |           |          |          |        |         |        |
| no_radiation_sensitivity_tg_eq_tair | 33.000000         | precision_70    |             |           |          |          |        |         |        |

## Bias-corrected threshold results

For this screening diagnostic, each formula is shifted by subtracting its mean prediction bias against observed WBGT, then evaluated at the same fixed 31C and 33C thresholds.

| formula                             | score_variant          | bias_pred_minus_obs | bias_correction_added_c | event_threshold_c | score_threshold_c | n_obs | n_event_obs | tp | fp | fn   | tn    | precision | recall   | f1 |
| ----------------------------------- | ---------------------- | ------------------- | ----------------------- | ----------------- | ----------------- | ----- | ----------- | -- | -- | ---- | ----- | --------- | -------- | -- |
| existing_v09_proxy                  | formula_bias_corrected | -0.856679           | 0.856679                | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| existing_v09_proxy                  | formula_bias_corrected | -0.856679           | 0.856679                | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| reconstructed_from_v09_components   | formula_bias_corrected | -0.856679           | 0.856679                | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| reconstructed_from_v09_components   | formula_bias_corrected | -0.856679           | 0.856679                | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0025          | formula_bias_corrected | -0.891810           | 0.891810                | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0025          | formula_bias_corrected | -0.891810           | 0.891810                | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0035          | formula_bias_corrected | -0.874245           | 0.874245                | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0035          | formula_bias_corrected | -0.874245           | 0.874245                | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0045          | formula_bias_corrected | -0.856679           | 0.856679                | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0045          | formula_bias_corrected | -0.856679           | 0.856679                | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0055          | formula_bias_corrected | -0.839113           | 0.839113                | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0055          | formula_bias_corrected | -0.839113           | 0.839113                | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| stull_simple_globe_k0p0065          | formula_bias_corrected | -0.821547           | 0.821547                | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| stull_simple_globe_k0p0065          | formula_bias_corrected | -0.821547           | 0.821547                | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |
| no_radiation_sensitivity_tg_eq_tair | formula_bias_corrected | -0.935725           | 0.935725                | 31.000000         | 31.000000         | 40389 | 2844        | 0  | 0  | 2844 | 37545 |           | 0.000000 |    |
| no_radiation_sensitivity_tg_eq_tair | formula_bias_corrected | -0.935725           | 0.935725                | 33.000000         | 33.000000         | 40389 | 212         | 0  | 0  | 212  | 40177 |           | 0.000000 |    |

## Required additive shift summary

| formula                             | n     | shift_to_make_max_reach_31 | shift_to_match_observed_event_count_31 | shift_to_make_p99_reach_31 | observed_event_count_31 | shift_to_make_max_reach_33 | shift_to_match_observed_event_count_33 | shift_to_make_p99_reach_33 | observed_event_count_33 |
| ----------------------------------- | ----- | -------------------------- | -------------------------------------- | -------------------------- | ----------------------- | -------------------------- | -------------------------------------- | -------------------------- | ----------------------- |
| existing_v09_proxy                  | 40419 | 1.764634                   | 3.168593                               | 2.465235                   | 2844                    | 3.764634                   | 4.207519                               | 4.465235                   | 212                     |
| reconstructed_from_v09_components   | 40419 | 1.764634                   | 3.168593                               | 2.465235                   | 2844                    | 3.764634                   | 4.207519                               | 4.465235                   | 212                     |
| stull_simple_globe_k0p0025          | 40419 | 1.946025                   | 3.280307                               | 2.593638                   | 2844                    | 3.946025                   | 4.372082                               | 4.593638                   | 212                     |
| stull_simple_globe_k0p0035          | 40419 | 1.855330                   | 3.224760                               | 2.529436                   | 2844                    | 3.855330                   | 4.289801                               | 4.529436                   | 212                     |
| stull_simple_globe_k0p0045          | 40419 | 1.764634                   | 3.168593                               | 2.465235                   | 2844                    | 3.764634                   | 4.207519                               | 4.465235                   | 212                     |
| stull_simple_globe_k0p0055          | 40419 | 1.673939                   | 3.115705                               | 2.395361                   | 2844                    | 3.673939                   | 4.125237                               | 4.395361                   | 212                     |
| stull_simple_globe_k0p0065          | 40419 | 1.565716                   | 3.061915                               | 2.321494                   | 2844                    | 3.565716                   | 4.042956                               | 4.321494                   | 212                     |
| no_radiation_sensitivity_tg_eq_tair | 40419 | 2.172764                   | 3.416580                               | 2.754141                   | 2844                    | 4.172764                   | 4.565945                               | 4.754141                   | 212                     |

## Crossing flips vs existing v09 proxy

| formula                             | reference_formula  | threshold_c | n_valid | formula_ge_ref_lt | formula_lt_ref_ge | same_classification |
| ----------------------------------- | ------------------ | ----------- | ------- | ----------------- | ----------------- | ------------------- |
| reconstructed_from_v09_components   | existing_v09_proxy | 31.000000   | 40389   | 0                 | 0                 | 40389               |
| reconstructed_from_v09_components   | existing_v09_proxy | 33.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0025          | existing_v09_proxy | 31.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0025          | existing_v09_proxy | 33.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0035          | existing_v09_proxy | 31.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0035          | existing_v09_proxy | 33.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0045          | existing_v09_proxy | 31.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0045          | existing_v09_proxy | 33.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0055          | existing_v09_proxy | 31.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0055          | existing_v09_proxy | 33.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0065          | existing_v09_proxy | 31.000000   | 40389   | 0                 | 0                 | 40389               |
| stull_simple_globe_k0p0065          | existing_v09_proxy | 33.000000   | 40389   | 0                 | 0                 | 40389               |
| no_radiation_sensitivity_tg_eq_tair | existing_v09_proxy | 31.000000   | 40389   | 0                 | 0                 | 40389               |
| no_radiation_sensitivity_tg_eq_tair | existing_v09_proxy | 33.000000   | 40389   | 0                 | 0                 | 40389               |

## Interpretation guardrails

- The current variants are transparent screening/sensitivity formulas, not a validated replacement for NEA WBGT.
- Bias correction and threshold sweeps are screening sensitivity diagnostics only; they do not validate a replacement formula or alter the frozen v1.1-beta-formal calibration outputs.
- A Liljegren/PyWBGT route should be treated as a separate implementation-validation task before any formula replacement claim.
- If formula choice shifts many rows around 31C or 33C, open a formula-v2 cycle rather than rewriting the v1.1-beta-formal report silently.
