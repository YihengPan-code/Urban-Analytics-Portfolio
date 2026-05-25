# v12 formal-hot-day smoke vs v10-epsilon comparison

This diagnostic compares existing Core-8 output against formal-hot-day QA output.
It is a robustness check for SOLWEIG-derived Tmrt summaries.

## Coverage

- rows compared: `20`
- epsilon matches found: `20`
- cells: `5`
- scenarios: `base, overhead_as_canopy`

## Tmrt p90 difference

| cell_id   | scenario_id        |   count |   mean |   min |    max |
|:----------|:-------------------|--------:|-------:|------:|-------:|
| TP_0059   | base               |       2 |  4.092 | 1.85  |  6.334 |
| TP_0059   | overhead_as_canopy |       2 |  4.264 | 2.019 |  6.51  |
| TP_0542   | base               |       2 |  8.582 | 6.096 | 11.067 |
| TP_0542   | overhead_as_canopy |       2 |  3.95  | 1.317 |  6.582 |
| TP_0565   | base               |       2 |  4.348 | 2.632 |  6.064 |
| TP_0565   | overhead_as_canopy |       2 |  4.348 | 2.632 |  6.064 |
| TP_0835   | base               |       2 |  0.492 | 0.066 |  0.917 |
| TP_0835   | overhead_as_canopy |       2 |  0.492 | 0.066 |  0.917 |
| TP_0986   | base               |       2 |  3.851 | 1.967 |  5.736 |
| TP_0986   | overhead_as_canopy |       2 |  3.851 | 1.967 |  5.736 |

## Tmrt mean difference

| cell_id   | scenario_id        |   count |   mean |   min |   max |
|:----------|:-------------------|--------:|-------:|------:|------:|
| TP_0059   | base               |       2 |  4.204 | 1.971 | 6.437 |
| TP_0059   | overhead_as_canopy |       2 |  4.114 | 2.186 | 6.043 |
| TP_0542   | base               |       2 |  1.246 | 0.771 | 1.722 |
| TP_0542   | overhead_as_canopy |       2 |  1.07  | 0.659 | 1.482 |
| TP_0565   | base               |       2 |  4.845 | 2.771 | 6.92  |
| TP_0565   | overhead_as_canopy |       2 |  4.854 | 2.779 | 6.929 |
| TP_0835   | base               |       2 |  0.494 | 0.068 | 0.92  |
| TP_0835   | overhead_as_canopy |       2 |  0.494 | 0.068 | 0.92  |
| TP_0986   | base               |       2 |  4.817 | 2.923 | 6.711 |
| TP_0986   | overhead_as_canopy |       2 |  4.817 | 2.923 | 6.711 |

## Review notes

- Compare direction, rank stability, and expected null or sensitivity roles.
- If roles flip unexpectedly, audit forcing, masks, tile geometry, SVF, and aggregation before scaling.
- Treat this as QA evidence for pre-scale design, not as an operational product.
