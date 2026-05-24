# TP0542 h15 base vs overhead distribution diagnostic

## Quantiles

|   quantile |   base_tmrt_c |   overhead_tmrt_c |   delta_overhead_minus_base_c |
|-----------:|--------------:|------------------:|------------------------------:|
|          0 |        34.728 |            34.728 |                         0     |
|          1 |        34.748 |            34.748 |                         0     |
|          5 |        34.841 |            34.841 |                         0     |
|         10 |        34.936 |            34.968 |                         0.032 |
|         25 |        35.364 |            35.365 |                         0.001 |
|         50 |        35.494 |            35.471 |                        -0.023 |
|         75 |        36.381 |            35.974 |                        -0.407 |
|         80 |        37.02  |            36.359 |                        -0.661 |
|         85 |        37.859 |            37.07  |                        -0.789 |
|         90 |        50.729 |            39.148 |                       -11.581 |
|         95 |        56.381 |            56.228 |                        -0.152 |
|         99 |        60.755 |            60.755 |                        -0     |
|        100 |        60.761 |            60.761 |                         0     |

## Area above thresholds

|   threshold_c |   base_pct_ge_threshold |   overhead_pct_ge_threshold |   delta_pct_point |
|--------------:|------------------------:|----------------------------:|------------------:|
|            35 |                   88.48 |                       89.2  |              0.72 |
|            40 |                   11.4  |                        9.08 |             -2.32 |
|            45 |                   10.12 |                        7.84 |             -2.28 |
|            50 |                   10.12 |                        7.84 |             -2.28 |
|            55 |                    6.76 |                        6.48 |             -0.28 |
|            60 |                    4.24 |                        4.24 |              0    |

## Interpretation note

TP0542 h15 is interpreted as a mapped pedestrian-overhead shade case. A large p90 decrease with unchanged max means overhead adds shaded/low-Tmrt pixels while a small number of hot pixels remains. This supports p90 as a mixed-cell upper-tail target.
