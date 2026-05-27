# B8.6d Two-Stage Surrogate Workflow Formalization

Generated: 2026-05-27 20:29:14

Status: `B86D_TWO_STAGE_DIAGNOSTIC_ONLY`

## 1. Why B8.6d Follows B8.6c

B8.6c found that simple compact feature-set hardening did not materially fix the weak cell-group, spatial, and typology holdouts, while a two-stage neutral-boundary pretest was promising. B8.6d therefore formalizes and stress-tests that compact two-stage workflow before any AOI-wide dry-run preflight is considered.

## 2. Input Counts And Leakage Guard

- Dataset rows: 1500
- Unique cells: 150
- Forcing days: 2
- Hours: 5
- Predictor feature sets tested: 6
- Schema columns audited: 205
- `cell_id` remains metadata/group only; `forcing_day_id` remains split metadata.
- Target, rank, path/status, WBGT, risk, hazard, observed-truth, future exposure/vulnerability, raster, and System A columns are excluded from predictors.

## 3. Neutral Threshold Definition

Stage 1 uses `neutral = abs(delta_tmrt_p90_c) <= threshold`; meaningful cooling is `delta_tmrt_p90_c < -threshold`. Positive warming or weak positive rows are tracked but not promoted. The primary threshold remains `0.05` C.

## 4. Stage 1 Results

| split_family        |   accuracy |   balanced_accuracy |   false_promotion_rate |   false_neutral_rate |
|:--------------------|-----------:|--------------------:|-----------------------:|---------------------:|
| cell_group_holdout  |     0.7387 |              0.748  |                 0.2172 |               0.2869 |
| forcing_day_holdout |     0.8607 |              0.8546 |                 0.1056 |               0.1852 |
| hour_holdout        |     0.8667 |              0.8622 |                 0.1085 |               0.1671 |
| spatial_holdout     |     0.667  |              0.6579 |                 0.2378 |               0.4465 |
| typology_holdout    |     0.7143 |              0.711  |                 0.2553 |               0.3226 |

## 5. Stage 2 Results

| split_family        |    MAE |   RMSE |       R2 |   Spearman_observed_vs_predicted |   top10pct_overlap |   robust_anchor_MAE |
|:--------------------|-------:|-------:|---------:|---------------------------------:|-------------------:|--------------------:|
| cell_group_holdout  | 0.3021 | 0.4875 |  -0.6358 |                           0.4267 |             0.5    |              0.7321 |
| forcing_day_holdout | 0.146  | 0.21   |   0.7967 |                           0.757  |             0.7857 |              0.1076 |
| hour_holdout        | 0.1464 | 0.2147 |   0.6903 |                           0.7731 |             0.8    |              0.2342 |
| spatial_holdout     | 0.3296 | 0.4515 |  -2.2905 |                           0.436  |             0.375  |              0.7457 |
| typology_holdout    | 0.5194 | 0.6094 | -10.6321 |                           0.3932 |             0.2667 |              0.9415 |

## 6. Combined Pipeline Results

- Selected full_safe_compact / logistic_regression + ridge at threshold 0.05: MAE=0.183, Spearman=0.466, top10pct=0.645, neutral_acc=0.761.

| split_family        |    MAE |   Spearman |   top10pct_overlap |   neutral_accuracy |   false_promotion_rate |   Spearman_gain_vs_b86c_single_stage |   top10_gain_vs_b86c_single_stage |
|:--------------------|-------:|-----------:|-------------------:|-------------------:|-----------------------:|-------------------------------------:|----------------------------------:|
| cell_group_holdout  | 0.1741 |     0.4623 |             0.6    |             0.7387 |                 0.2172 |                               0.012  |                            0.1333 |
| forcing_day_holdout | 0.0864 |     0.7091 |             0.8    |             0.8607 |                 0.1056 |                              -0.1465 |                           -0.1667 |
| hour_holdout        | 0.088  |     0.7125 |             0.8267 |             0.8667 |                 0.1085 |                              -0.1945 |                           -0.12   |
| spatial_holdout     | 0.2243 |     0.172  |             0.3125 |             0.667  |                 0.2378 |                              -0.2559 |                            0      |
| typology_holdout    | 0.2937 |     0.3611 |             0.7143 |             0.7143 |                 0.2553 |                              -0.0642 |                            0.3333 |

## 7. Threshold Sweep

|   neutral_threshold_c | feature_set       | classifier                   | regressor                        |   neutral_accuracy |   false_promotion_rate |   Spearman |   top10pct_overlap |   robust_anchor_MAE |
|----------------------:|:------------------|:-----------------------------|:---------------------------------|-------------------:|-----------------------:|-----------:|-------------------:|--------------------:|
|                  0.15 | full_safe_compact | logistic_regression          | hist_gradient_boosting_regressor |             0.7869 |                 0.1329 |     0.4046 |             0.2925 |              0.6286 |
|                  0.15 | full_safe_compact | logistic_regression          | random_forest_regressor          |             0.7869 |                 0.1329 |     0.3928 |             0.3503 |              0.7264 |
|                  0.15 | full_safe_compact | logistic_regression          | ridge                            |             0.7869 |                 0.1329 |     0.3526 |             0.2849 |              0.773  |
|                  0.15 | full_safe_compact | logistic_regression          | elasticnet                       |             0.7869 |                 0.1329 |     0.3298 |             0.3087 |              0.7281 |
|                  0.15 | full_safe_compact | random_forest_classifier     | hist_gradient_boosting_regressor |             0.7766 |                 0.1384 |     0.4541 |             0.3163 |              0.6354 |
|                  0.15 | full_safe_compact | random_forest_classifier     | random_forest_regressor          |             0.7766 |                 0.1384 |     0.4421 |             0.3546 |              0.795  |
|                  0.15 | full_safe_compact | random_forest_classifier     | ridge                            |             0.7766 |                 0.1384 |     0.3821 |             0.3027 |              0.7272 |
|                  0.15 | full_safe_compact | random_forest_classifier     | elasticnet                       |             0.7766 |                 0.1384 |     0.3668 |             0.3087 |              0.7236 |
|                  0.15 | full_safe_compact | balanced_logistic_regression | hist_gradient_boosting_regressor |             0.7687 |                 0.2065 |     0.4135 |             0.2968 |              0.6174 |
|                  0.15 | full_safe_compact | balanced_logistic_regression | random_forest_regressor          |             0.7687 |                 0.2065 |     0.3791 |             0.3682 |              0.7193 |
|                  0.15 | full_safe_compact | balanced_logistic_regression | ridge                            |             0.7687 |                 0.2065 |     0.3526 |             0.2849 |              0.7977 |
|                  0.15 | full_safe_compact | balanced_logistic_regression | elasticnet                       |             0.7687 |                 0.2065 |     0.3378 |             0.3146 |              0.751  |

## 8. Seed Stability

| split_family       | metric               |   mean |   std |    min |    max |   n_seeds |
|:-------------------|:---------------------|-------:|------:|-------:|-------:|----------:|
| overall            | neutral_accuracy     | 0.7613 |     0 | 0.7613 | 0.7613 |        10 |
| overall            | false_promotion_rate | 0.1937 |     0 | 0.1937 | 0.1937 |        10 |
| overall            | Spearman             | 0.466  |     0 | 0.466  | 0.466  |        10 |
| overall            | top10pct_overlap     | 0.6455 |     0 | 0.6455 | 0.6455 |        10 |
| overall            | anchor_MAE           | 0.505  |     0 | 0.505  | 0.505  |        10 |
| cell_group_holdout | neutral_accuracy     | 0.7387 |     0 | 0.7387 | 0.7387 |        10 |
| cell_group_holdout | false_promotion_rate | 0.2172 |     0 | 0.2172 | 0.2172 |        10 |
| cell_group_holdout | Spearman             | 0.4623 |     0 | 0.4623 | 0.4623 |        10 |
| cell_group_holdout | top10pct_overlap     | 0.6    |     0 | 0.6    | 0.6    |        10 |
| cell_group_holdout | anchor_MAE           | 0.6876 |     0 | 0.6876 | 0.6876 |        10 |
| spatial_holdout    | neutral_accuracy     | 0.667  |     0 | 0.667  | 0.667  |        10 |
| spatial_holdout    | false_promotion_rate | 0.2378 |     0 | 0.2378 | 0.2378 |        10 |
| spatial_holdout    | Spearman             | 0.172  |     0 | 0.172  | 0.172  |        10 |
| spatial_holdout    | top10pct_overlap     | 0.3125 |     0 | 0.3125 | 0.3125 |        10 |
| spatial_holdout    | anchor_MAE           | 0.7713 |     0 | 0.7713 | 0.7713 |        10 |
| typology_holdout   | neutral_accuracy     | 0.7143 |     0 | 0.7143 | 0.7143 |        10 |
| typology_holdout   | false_promotion_rate | 0.2553 |     0 | 0.2553 | 0.2553 |        10 |
| typology_holdout   | Spearman             | 0.3611 |     0 | 0.3611 | 0.3611 |        10 |

## 9. Spatial / Typology / Cell-Group Holdouts

- cell_group_holdout: Spearman=0.462, top10pct=0.600, neutral_acc=0.739; spatial_holdout: Spearman=0.172, top10pct=0.312, neutral_acc=0.667; typology_holdout: Spearman=0.361, top10pct=0.714, neutral_acc=0.714

## 10. Anchor, Neutral-Boundary, And Unstable-Cell Diagnostics

- Anchor diagnostic rows: 21
- Neutral-boundary diagnostic rows: 39
- Unstable-cell diagnostic rows: 33

## 11. h10 Caveat

h10 is reported separately from core-hour behavior in stage-2 and combined metrics. It is not used alone as anchor evidence.

## 12. Target Role Decision

| target            | role                           |   mean_Spearman |   mean_top10pct_overlap | decision              | workflow_use                     |
|:------------------|:-------------------------------|----------------:|------------------------:|:----------------------|:---------------------------------|
| delta_tmrt_p90_c  | hot-pocket / upper-tail target |          0.475  |                  0.4562 | p90 remains primary   | stage1 boundary and ranking gate |
| delta_tmrt_mean_c | broad-area cooling             |          0.4312 |                  0.5094 | companion side output | sensitivity report only          |
| delta_tmrt_p50_c  | typical cell cooling           |          0.3907 |                  0.4741 | companion side output | sensitivity report only          |
| delta_tmrt_p95_c  | extreme pocket sensitivity     |          0.2921 |                  0.4585 | companion side output | sensitivity report only          |

## 13. Promotion Gate Decision

| gate                           | status     | evidence                                                                                                                                                                  | next_action                                                                           |
|:-------------------------------|:-----------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------|
| supporting_holdout_improvement | PASS       | 2/3 weak supporting split families improved vs B8.6c single-stage reference.                                                                                              | Require at least two of cell_group/spatial/typology to improve materially.            |
| neutral_accuracy               | PASS       | Average selected neutral accuracy=0.769.                                                                                                                                  | Keep two-stage neutral gate diagnostic if below threshold.                            |
| false_promotion_rate           | DIAGNOSTIC | Average selected false promotion rate=0.185.                                                                                                                              | Do not promote neutral cells as cooling candidates when false promotion remains high. |
| spatial_or_typology_top10      | PASS       | Spatial/typology top10 improvements passing threshold=1.                                                                                                                  | Require top10 support in at least one weak generalisation family.                     |
| anchor_underprediction         | DIAGNOSTIC | Mean anchor MAE delta vs B8.6c single-stage=0.236.                                                                                                                        | Do not accept if anchor underprediction worsens materially.                           |
| seed_stability                 | PASS       | Seed std neutral=0.000; Spearman=0.000.                                                                                                                                   | Downgrade if selected stochastic workflow is seed-sensitive.                          |
| claim_boundaries               | PASS       | No AOI-wide prediction, B9, local WBGT, risk, observed-truth, causal feature-importance, raster, QGIS/SOLWEIG, Tmrt-to-WBGT, or System A/B coupling outputs are produced. | Keep B9 blocked in this lane.                                                         |

## 14. Future AOI-Wide Dry-Run Preflight

B8.6d creates no AOI-wide prediction. If the gate status is `B86D_AOI_PREFLIGHT_READY_CANDIDATE`, the only allowed next step is to design a separate future AOI-wide dry-run preflight lane; B9 remains blocked here.

## 15. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not hazard_score or risk_score.
- Not observed truth.
- Not causal feature importance.
- No raster read/write/open/copy.
- No SOLWEIG or QGIS.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
