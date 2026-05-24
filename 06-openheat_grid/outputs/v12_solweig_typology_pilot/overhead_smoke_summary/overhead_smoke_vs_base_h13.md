# v12 overhead smoke vs base h13

- Base: `outputs\v12_solweig_typology_pilot\core8_base_summary\modifier_targets_long.csv`
- Overhead: `outputs\v12_solweig_typology_pilot\overhead_smoke_summary\modifier_targets_long.csv`

| cell_id   |   tmrt_mean_c_base |   tmrt_p90_c_base |   tmrt_max_c_base |   tmrt_mean_c_overhead |   tmrt_p90_c_overhead |   tmrt_max_c_overhead |   delta_tmrt_mean_c_overhead_minus_base |   delta_tmrt_p90_c_overhead_minus_base |   delta_tmrt_max_c_overhead_minus_base |
|:----------|-------------------:|------------------:|------------------:|-----------------------:|----------------------:|----------------------:|----------------------------------------:|---------------------------------------:|---------------------------------------:|
| TP_0565   |             60.055 |            62.353 |            62.466 |                 60.046 |                62.353 |                62.449 |                                  -0.01  |                                  0     |                                 -0.018 |
| TP_0986   |             60.673 |            62.464 |            62.528 |                 60.673 |                62.464 |                62.528 |                                   0     |                                  0     |                                  0     |
| TP_0059   |             61.813 |            62.027 |            62.19  |                 59.046 |                61.85  |                62.078 |                                  -2.767 |                                 -0.176 |                                 -0.111 |

## Interpretation checklist

- TP_0986 is the null-control; p90 delta should be near zero or clearly explainable.
- TP_0059 is parking-lot hardscape; large delta requires mapped-overhead/context audit.
- TP_0565 is asphalt road-edge hot anchor; large delta requires mapped-overhead/context audit.
