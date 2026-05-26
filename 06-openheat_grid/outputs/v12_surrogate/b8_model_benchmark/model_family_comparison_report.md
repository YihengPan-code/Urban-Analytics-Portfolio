# B8.2 System B Baseline Surrogate Benchmark

Generated: 2026-05-26 21:29:28

## 1. Input Files And Feature Contract

- Matrix: `outputs/v12_surrogate/b8_dataset_audit/surrogate_label_feature_matrix.csv`
- Feature schema: `outputs/v12_surrogate/b8_dataset_audit/feature_schema.csv`
- Split manifests: existing B8.1 cell-grouped, spatial, feature-bin, hour, and scenario holdouts.
- Headline feature set: `role == feature` and `predictor_tier == physical_core`.
- Feature count used: 115 (114 numeric, 1 categorical).
- Dropped all-NaN features: 0.
- Dropped constant/non-usable features: 0.
- Hard-blocked by name contract: 0.

## 2. Target Definitions And Claim Boundary

- Primary target: `delta_tmrt_p90_c`.
- Secondary target: `tmrt_p90_c`.
- Retained label: `m_rad_pct01` for post-prediction rank interpretation only.
- Labels are SOLWEIG-derived Tmrt targets. This is not observed WBGT calibration, not local WBGT prediction, and not a risk map.

## 3. Models Benchmarked

- `featureless_mean`
- `ridge`
- `elasticnet`
- `random_forest`
- `extra_trees`
- `hist_gradient_boosting`

Tree ensembles used a reduced fixed grid (`n_estimators=80`, two depth settings, one leaf setting, single-thread fits) to keep the full multi-split benchmark reasonable on the B8.2 lane.

## 4. Validation Split Families Consumed

- `cell_grouped_holdout`
- `feature_bin_holdout`
- `hour_holdout`
- `scenario_holdout`
- `spatial_holdout`

Group-safe split families assert no cell_id overlap between train and test. Hour and scenario holdouts may reuse cells by design.

## 5. Splits Skipped

- `feature_bin_holdout` / `water_high_bin` fold `8`: blocked_or_below_min_cell_threshold
- `feature_bin_holdout` / `water_low_bin` fold `7`: blocked_or_below_min_cell_threshold

## 6. Primary Target Results

- Best non-featureless cell-grouped model by MAE: extra_trees (MAE=0.9401).
- Best non-featureless spatial model by MAE: extra_trees (MAE=0.9892).

| split_family         | model                  |   n_folds |      MAE |     RMSE |             R2 |   spearman |   improvement_over_featureless_MAE |
|:---------------------|:-----------------------|----------:|---------:|---------:|---------------:|-----------:|-----------------------------------:|
| cell_grouped_holdout | extra_trees            |         5 | 0.940126 |  1.79015 |    0.807381    |   0.723394 |                           1.90761  |
| cell_grouped_holdout | random_forest          |         5 | 0.960504 |  1.88834 |    0.745022    |   0.704327 |                           1.88723  |
| cell_grouped_holdout | hist_gradient_boosting |         5 | 1.1096   |  2.36306 |    0.620736    |   0.711971 |                           1.73813  |
| cell_grouped_holdout | elasticnet             |         5 | 1.6088   |  2.49161 |    0.643769    |   0.513285 |                           1.23894  |
| cell_grouped_holdout | ridge                  |         5 | 1.68969  |  2.59487 |    0.478255    |   0.539188 |                           1.15805  |
| cell_grouped_holdout | featureless_mean       |         5 | 2.84773  |  5.12311 |   -0.113276    | nan        |                           0        |
| feature_bin_holdout  | extra_trees            |        10 | 2.22978  |  3.55601 |    0.378739    |   0.66344  |                           1.86196  |
| feature_bin_holdout  | random_forest          |        10 | 2.26101  |  3.57928 |    0.396497    |   0.645682 |                           1.83074  |
| feature_bin_holdout  | hist_gradient_boosting |        10 | 2.32295  |  3.78956 |    0.38471     |   0.636581 |                           1.76879  |
| feature_bin_holdout  | elasticnet             |        10 | 3.63829  |  5.71492 |  -15.7815      |   0.563749 |                           0.453458 |
| feature_bin_holdout  | featureless_mean       |        10 | 4.09175  |  6.4949  |   -2.33726     | nan        |                           0        |
| feature_bin_holdout  | ridge                  |        10 | 8.99701  | 22.8465  | -199.873       |   0.499238 |                          -4.90527  |
| hour_holdout         | random_forest          |         5 | 0.7563   |  1.83377 |    0.801283    |   0.963969 |                           2.06989  |
| hour_holdout         | extra_trees            |         5 | 0.759383 |  1.83461 |    0.800891    |   0.963438 |                           2.0668   |
| hour_holdout         | hist_gradient_boosting |         5 | 0.786624 |  1.93678 |    0.791405    |   0.964098 |                           2.03956  |
| hour_holdout         | ridge                  |         5 | 1.35441  |  2.22722 |    0.768804    |   0.665445 |                           1.47177  |
| hour_holdout         | elasticnet             |         5 | 1.48847  |  2.37281 |    0.74445     |   0.57587  |                           1.33771  |
| hour_holdout         | featureless_mean       |         5 | 2.82619  |  5.1662  |   -0.0144309   | nan        |                           0        |
| scenario_holdout     | random_forest          |         2 | 0.734166 |  1.58487 |    0.909817    |   0.894939 |                           2.09038  |
| scenario_holdout     | hist_gradient_boosting |         2 | 0.734571 |  1.58207 |    0.910144    |   0.894939 |                           2.08997  |
| scenario_holdout     | extra_trees            |         2 | 0.735921 |  1.58272 |    0.910073    |   0.89452  |                           2.08862  |
| scenario_holdout     | ridge                  |         2 | 1.36681  |  2.14802 |    0.834399    |   0.61279  |                           1.45773  |
| scenario_holdout     | elasticnet             |         2 | 1.41036  |  2.16078 |    0.832424    |   0.575784 |                           1.41418  |
| scenario_holdout     | featureless_mean       |         2 | 2.82454  |  5.27863 |   -8.66083e-07 | nan        |                           0        |
| spatial_holdout      | extra_trees            |         4 | 0.989158 |  1.75913 |    0.87621     |   0.72795  |                           1.85767  |
| spatial_holdout      | random_forest          |         4 | 1.08735  |  1.91274 |    0.85629     |   0.678624 |                           1.75948  |
| spatial_holdout      | hist_gradient_boosting |         4 | 1.10882  |  1.99516 |    0.844163    |   0.672443 |                           1.73801  |
| spatial_holdout      | ridge                  |         4 | 1.64615  |  2.55934 |    0.729098    |   0.564802 |                           1.20068  |
| spatial_holdout      | elasticnet             |         4 | 1.81531  |  3.00838 |    0.6465      |   0.520691 |                           1.03152  |
| spatial_holdout      | featureless_mean       |         4 | 2.84682  |  5.151   |   -0.0418704   | nan        |                           0        |

## 7. Secondary Target Results

| split_family         | model                  |   n_folds |      MAE |     RMSE |            R2 |   spearman |   improvement_over_featureless_MAE |
|:---------------------|:-----------------------|----------:|---------:|---------:|--------------:|-----------:|-----------------------------------:|
| cell_grouped_holdout | random_forest          |         5 |  5.99004 |  6.5469  |   0.329955    |   0.356298 |                            1.31136 |
| cell_grouped_holdout | extra_trees            |         5 |  5.99429 |  6.53337 |   0.333176    |   0.374984 |                            1.30711 |
| cell_grouped_holdout | ridge                  |         5 |  6.099   |  6.79262 |   0.276045    |   0.287748 |                            1.2024  |
| cell_grouped_holdout | elasticnet             |         5 |  6.10415 |  6.73193 |   0.28819     |   0.312952 |                            1.19725 |
| cell_grouped_holdout | hist_gradient_boosting |         5 |  6.11458 |  6.72968 |   0.288791    |   0.365186 |                            1.18682 |
| cell_grouped_holdout | featureless_mean       |         5 |  7.3014  |  8.19719 |  -0.0154014   | nan        |                            0       |
| feature_bin_holdout  | extra_trees            |        10 |  6.77924 |  7.57968 |   0.174207    |   0.37425  |                            1.29048 |
| feature_bin_holdout  | random_forest          |        10 |  6.83809 |  7.63974 |   0.161223    |   0.336048 |                            1.23163 |
| feature_bin_holdout  | hist_gradient_boosting |        10 |  6.89576 |  7.70207 |   0.153089    |   0.358937 |                            1.17396 |
| feature_bin_holdout  | featureless_mean       |        10 |  8.06972 |  9.27812 |  -0.164008    | nan        |                            0       |
| feature_bin_holdout  | elasticnet             |        10 | 12.051   | 20.4152  | -24.5047      |   0.282556 |                           -3.98127 |
| feature_bin_holdout  | ridge                  |        10 | 12.3432  | 21.5162  | -30.9743      |   0.297442 |                           -4.27349 |
| hour_holdout         | extra_trees            |         5 |  7.45652 |  7.64862 |  -3.08751     |   0.963504 |                            1.22734 |
| hour_holdout         | hist_gradient_boosting |         5 |  7.45653 |  7.65723 |  -3.09082     |   0.964035 |                            1.22734 |
| hour_holdout         | elasticnet             |         5 |  7.46077 |  7.68405 |  -3.10166     |   0.751821 |                            1.2231  |
| hour_holdout         | ridge                  |         5 |  7.46421 |  7.69316 |  -3.10449     |   0.757462 |                            1.21966 |
| hour_holdout         | random_forest          |         5 |  7.46649 |  7.66316 |  -3.09212     |   0.923644 |                            1.21738 |
| hour_holdout         | featureless_mean       |         5 |  8.68387 |  9.28473 |  -3.90258     | nan        |                            0       |
| scenario_holdout     | hist_gradient_boosting |         2 |  5.96859 |  6.47885 |   0.376221    |   0.429127 |                            1.32608 |
| scenario_holdout     | extra_trees            |         2 |  5.9686  |  6.47896 |   0.376199    |   0.429063 |                            1.32607 |
| scenario_holdout     | random_forest          |         2 |  5.97095 |  6.4891  |   0.374247    |   0.410273 |                            1.32372 |
| scenario_holdout     | elasticnet             |         2 |  5.977   |  6.52431 |   0.367436    |   0.36693  |                            1.31767 |
| scenario_holdout     | ridge                  |         2 |  5.98881 |  6.5377  |   0.364837    |   0.367223 |                            1.30586 |
| scenario_holdout     | featureless_mean       |         2 |  7.29467 |  8.20582 |  -0.000641651 | nan        |                            0       |
| spatial_holdout      | extra_trees            |         4 |  6.01863 |  6.54289 |   0.338465    |   0.373191 |                            1.28268 |
| spatial_holdout      | random_forest          |         4 |  6.03508 |  6.57091 |   0.333798    |   0.367159 |                            1.26622 |
| spatial_holdout      | hist_gradient_boosting |         4 |  6.07331 |  6.62212 |   0.324512    |   0.355825 |                            1.22799 |
| spatial_holdout      | elasticnet             |         4 |  6.14217 |  6.80267 |   0.286189    |   0.324218 |                            1.15913 |
| spatial_holdout      | ridge                  |         4 |  6.16968 |  6.87758 |   0.270366    |   0.317288 |                            1.13163 |
| spatial_holdout      | featureless_mean       |         4 |  7.3013  |  8.19595 |  -0.0146491   | nan        |                            0       |

## 8. Top-k / Spearman Interpretation

- extra_trees: mean cell/spatial Spearman=0.725; mean cell-level top-10% overlap=0.444.
- Top-k overlap is diagnostic for prioritisation ranking, not evidence of risk prediction.

## 9. Stratified Error Summary

| target           | stratification_family   | model                  |     MAE |
|:-----------------|:------------------------|:-----------------------|--------:|
| delta_tmrt_p90_c | SVF                     | extra_trees            | 1.11016 |
| delta_tmrt_p90_c | SVF                     | random_forest          | 1.14287 |
| delta_tmrt_p90_c | SVF                     | hist_gradient_boosting | 1.21213 |
| delta_tmrt_p90_c | SVF                     | elasticnet             | 1.94378 |
| delta_tmrt_p90_c | SVF                     | featureless_mean       | 3.06075 |
| delta_tmrt_p90_c | SVF                     | ridge                  | 3.80862 |
| delta_tmrt_p90_c | building_density        | extra_trees            | 1.31877 |
| delta_tmrt_p90_c | building_density        | random_forest          | 1.34959 |
| delta_tmrt_p90_c | building_density        | hist_gradient_boosting | 1.40467 |
| delta_tmrt_p90_c | building_density        | elasticnet             | 2.26335 |
| delta_tmrt_p90_c | building_density        | featureless_mean       | 3.22849 |
| delta_tmrt_p90_c | building_density        | ridge                  | 4.22311 |
| delta_tmrt_p90_c | overhead                | extra_trees            | 1.39877 |
| delta_tmrt_p90_c | overhead                | random_forest          | 1.42798 |
| delta_tmrt_p90_c | overhead                | hist_gradient_boosting | 1.48615 |
| delta_tmrt_p90_c | overhead                | elasticnet             | 2.38545 |
| delta_tmrt_p90_c | overhead                | ridge                  | 3.15123 |
| delta_tmrt_p90_c | overhead                | featureless_mean       | 3.3494  |
| delta_tmrt_p90_c | road_hardscape          | extra_trees            | 1.28044 |
| delta_tmrt_p90_c | road_hardscape          | random_forest          | 1.31376 |
| delta_tmrt_p90_c | road_hardscape          | hist_gradient_boosting | 1.38188 |
| delta_tmrt_p90_c | road_hardscape          | elasticnet             | 2.23919 |
| delta_tmrt_p90_c | road_hardscape          | featureless_mean       | 3.16768 |
| delta_tmrt_p90_c | road_hardscape          | ridge                  | 5.40214 |
| delta_tmrt_p90_c | shade                   | extra_trees            | 1.10012 |
| delta_tmrt_p90_c | shade                   | random_forest          | 1.13159 |
| delta_tmrt_p90_c | shade                   | hist_gradient_boosting | 1.20447 |
| delta_tmrt_p90_c | shade                   | elasticnet             | 1.92048 |
| delta_tmrt_p90_c | shade                   | featureless_mean       | 3.05092 |
| delta_tmrt_p90_c | shade                   | ridge                  | 3.71413 |
| delta_tmrt_p90_c | water                   | extra_trees            | 1.39323 |
| delta_tmrt_p90_c | water                   | random_forest          | 1.42353 |
| delta_tmrt_p90_c | water                   | hist_gradient_boosting | 1.4852  |
| delta_tmrt_p90_c | water                   | elasticnet             | 2.38274 |
| delta_tmrt_p90_c | water                   | featureless_mean       | 3.32013 |
| delta_tmrt_p90_c | water                   | ridge                  | 4.40419 |
| tmrt_p90_c       | SVF                     | extra_trees            | 6.38982 |
| tmrt_p90_c       | SVF                     | random_forest          | 6.40933 |
| tmrt_p90_c       | SVF                     | hist_gradient_boosting | 6.47272 |
| tmrt_p90_c       | SVF                     | featureless_mean       | 7.73615 |
| tmrt_p90_c       | SVF                     | elasticnet             | 8.13513 |
| tmrt_p90_c       | SVF                     | ridge                  | 8.32567 |
| tmrt_p90_c       | building_density        | extra_trees            | 6.56819 |
| tmrt_p90_c       | building_density        | random_forest          | 6.58754 |
| tmrt_p90_c       | building_density        | hist_gradient_boosting | 6.63831 |
| tmrt_p90_c       | building_density        | featureless_mean       | 7.81436 |
| tmrt_p90_c       | building_density        | elasticnet             | 8.52647 |
| tmrt_p90_c       | building_density        | ridge                  | 8.62519 |
| tmrt_p90_c       | overhead                | extra_trees            | 6.59257 |
| tmrt_p90_c       | overhead                | random_forest          | 6.61871 |
| tmrt_p90_c       | overhead                | hist_gradient_boosting | 6.66292 |
| tmrt_p90_c       | overhead                | ridge                  | 7.56187 |
| tmrt_p90_c       | overhead                | elasticnet             | 7.56276 |
| tmrt_p90_c       | overhead                | featureless_mean       | 7.88692 |
| tmrt_p90_c       | road_hardscape          | extra_trees            | 6.53775 |
| tmrt_p90_c       | road_hardscape          | random_forest          | 6.56369 |
| tmrt_p90_c       | road_hardscape          | hist_gradient_boosting | 6.60999 |
| tmrt_p90_c       | road_hardscape          | featureless_mean       | 7.73478 |
| tmrt_p90_c       | road_hardscape          | elasticnet             | 9.19885 |
| tmrt_p90_c       | road_hardscape          | ridge                  | 9.3719  |
| tmrt_p90_c       | shade                   | extra_trees            | 6.39892 |
| tmrt_p90_c       | shade                   | random_forest          | 6.41703 |
| tmrt_p90_c       | shade                   | hist_gradient_boosting | 6.48228 |
| tmrt_p90_c       | shade                   | featureless_mean       | 7.7304  |
| tmrt_p90_c       | shade                   | elasticnet             | 8.11271 |
| tmrt_p90_c       | shade                   | ridge                  | 8.30199 |
| tmrt_p90_c       | water                   | extra_trees            | 6.57916 |
| tmrt_p90_c       | water                   | random_forest          | 6.60561 |
| tmrt_p90_c       | water                   | hist_gradient_boosting | 6.65552 |
| tmrt_p90_c       | water                   | featureless_mean       | 7.86223 |
| tmrt_p90_c       | water                   | elasticnet             | 8.64835 |
| tmrt_p90_c       | water                   | ridge                  | 8.76556 |

## 10. B8.3 Model-card Promotion Readiness

- No. Results are baseline evidence for B8.3 model-card review only; no final AOI-wide surrogate is promoted here.

## 11. Caveats

- N150 only.
- Single forcing setup.
- SOLWEIG-derived labels only.
- No local WBGT.
- No risk map.
- No causal feature importance.
- No final AOI-wide prediction map was created.
