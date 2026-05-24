# v12 Core 8 base vs overhead_as_canopy delta report

- Base: `outputs\v12_solweig_typology_pilot\core8_base_summary\modifier_targets_long.csv`
- Overhead: `outputs\v12_solweig_typology_pilot\core8_overhead_summary\modifier_targets_long.csv`
- Rows compared: `40`

## By-cell delta summary

| cell_id   |   n |   mean_delta_mean |   min_delta_mean |   max_delta_mean |   mean_delta_p90 |   min_delta_p90 |   max_delta_p90 |   max_abs_delta_p90 |   n_large_p90_change |   n_p90_increase |   n_mean_large_p90_small |
|:----------|----:|------------------:|-----------------:|-----------------:|-----------------:|----------------:|----------------:|--------------------:|---------------------:|-----------------:|-------------------------:|
| TP_0542   |   5 |            -0.32  |           -0.539 |           -0.041 |           -2.417 |         -11.581 |           0.244 |              11.581 |                    1 |                1 |                        0 |
| TP_0059   |   5 |            -2.46  |           -3.22  |           -1.357 |           -0.183 |          -0.218 |          -0.122 |               0.218 |                    0 |                0 |                        5 |
| TP_0366   |   5 |            -0.324 |           -0.514 |           -0.122 |           -0.054 |          -0.076 |          -0.037 |               0.076 |                    0 |                0 |                        0 |
| TP_0627   |   5 |            -0     |           -0     |           -0     |           -0     |          -0.002 |           0     |               0.002 |                    0 |                0 |                        0 |
| TP_0326   |   5 |            -0.216 |           -0.262 |           -0.117 |            0     |           0     |           0     |               0     |                    0 |                0 |                        0 |
| TP_0565   |   5 |            -0.01  |           -0.012 |           -0.008 |            0     |           0     |           0     |               0     |                    0 |                0 |                        0 |
| TP_0835   |   5 |             0     |            0     |            0     |            0     |           0     |           0     |               0     |                    0 |                0 |                        0 |
| TP_0986   |   5 |             0     |            0     |            0     |            0     |           0     |           0     |               0     |                    0 |                0 |                        0 |

## Flagged rows

| cell_id   |   hour_sgt |   tmrt_mean_base |   tmrt_mean_overhead |   delta_tmrt_mean_overhead_minus_base |   tmrt_p90_base |   tmrt_p90_overhead |   delta_tmrt_p90_overhead_minus_base |   tmrt_max_base |   tmrt_max_overhead |   delta_tmrt_max_overhead_minus_base | flag_p90_large_change   | flag_p90_increase   | flag_mean_large_but_p90_small   |
|:----------|-----------:|-----------------:|---------------------:|--------------------------------------:|----------------:|--------------------:|-------------------------------------:|----------------:|--------------------:|-------------------------------------:|:------------------------|:--------------------|:--------------------------------|
| TP_0059   |         10 |           44.781 |               43.424 |                                -1.357 |          45.901 |              45.714 |                               -0.187 |          46.108 |              45.947 |                               -0.161 | False                   | False               | True                            |
| TP_0059   |         12 |           61.751 |               59.347 |                                -2.405 |          61.906 |              61.783 |                               -0.122 |          62.025 |              61.941 |                               -0.084 | False                   | False               | True                            |
| TP_0059   |         13 |           61.813 |               59.046 |                                -2.767 |          62.027 |              61.85  |                               -0.176 |          62.19  |              62.078 |                               -0.111 | False                   | False               | True                            |
| TP_0059   |         15 |           59.996 |               56.776 |                                -3.22  |          60.218 |              60.006 |                               -0.212 |          60.401 |              60.239 |                               -0.163 | False                   | False               | True                            |
| TP_0059   |         16 |           50.936 |               48.386 |                                -2.55  |          51.18  |              50.962 |                               -0.218 |          51.382 |              51.206 |                               -0.177 | False                   | False               | True                            |
| TP_0542   |         10 |           34.129 |               34.041 |                                -0.087 |          41.417 |              41.661 |                                0.244 |          46.563 |              46.563 |                                0     | False                   | True                | False                           |
| TP_0542   |         15 |           37.96  |               37.483 |                                -0.477 |          50.729 |              39.148 |                              -11.581 |          60.761 |              60.761 |                                0     | True                    | False               | False                           |

## Interpretation notes

- `flag_p90_large_change` means |overhead p90 - base p90| >= 1°C.
- `flag_p90_increase` means overhead p90 is >0.1°C warmer than base; this may be numerical/contextual and should be inspected before interpretation.
- `flag_mean_large_but_p90_small` means overhead changes the average strongly while upper-tail exposure remains stable; this supports using p90 as primary target.
- This comparison remains a mapped-overhead sensitivity diagnostic, not local WBGT and not risk.
