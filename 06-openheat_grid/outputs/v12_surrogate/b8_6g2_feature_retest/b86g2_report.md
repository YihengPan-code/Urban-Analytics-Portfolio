# B8.6g2 Feature-Upgraded Surrogate Retest

Generated: 2026-05-27 23:03:52

Status: `B86G2_DIAGNOSTIC_IMPROVEMENT_ONLY`

## 1. Why B8.6g2 follows B8.6g

B8.6g produced compact/vector-derived feature tables but did not train or promote a final surrogate. B8.6g2 therefore retests those B8.6g features against the same blocked validation families used in B8.6d/B8.6f, without creating AOI-wide or B9 outputs.

## 2. Input rows and cell counts

- Modeling rows: 1500
- Unique cells: 150
- Expected rows/cells: 1500/150
- B8.6g features are joined to F5 labels by `cell_id`; `cell_id` is metadata/group only.

## 3. Feature leakage audit

- Leakage audit rows: 81
- Registered feature sets: 7
- Target-derived columns, status/method/source fields, output paths, raster/QGIS/SOLWEIG/WBGT/risk/hazard/observed columns, and `cell_id` are excluded as predictors.

## 4. Feature-set definitions

| feature_set                      |   feature_count |   proxy_feature_count |   vector_or_vector_compact_feature_count | uses_hour_sgt   | status    |
|:---------------------------------|----------------:|----------------------:|-----------------------------------------:|:----------------|:----------|
| b86d_baseline_without_b86g       |              11 |                     0 |                                        0 | True            | AVAILABLE |
| b86g_proxy_features_only         |              17 |                    16 |                                        2 | True            | AVAILABLE |
| b86g_vector_derived_compact_only |               4 |                     0 |                                        3 | True            | AVAILABLE |
| b86g_proxy_plus_vector_compact   |              20 |                    16 |                                        5 | True            | AVAILABLE |
| b86g_no_status_columns           |              21 |                    17 |                                        5 | True            | AVAILABLE |
| b86g_high_priority_only          |              12 |                     8 |                                        5 | True            | AVAILABLE |
| b86g_all_safe_numeric            |              20 |                    16 |                                        5 | True            | AVAILABLE |

## 5. Single-stage results

- Best single-stage headline: b86g_all_safe_numeric + elasticnet: weak-split Spearman=0.570, top10pct=0.526, MAE=0.199

| feature_set                | model                            |   n_folds |    MAE |   Spearman |   top10pct_overlap |   anchor_MAE |
|:---------------------------|:---------------------------------|----------:|-------:|-----------:|-------------------:|-------------:|
| b86d_baseline_without_b86g | elasticnet                       |        21 | 0.2005 |     0.3889 |             0.2363 |       0.6773 |
| b86d_baseline_without_b86g | hist_gradient_boosting_regressor |        21 | 0.1563 |     0.5745 |             0.4668 |       0.5262 |
| b86d_baseline_without_b86g | random_forest_regressor          |        21 | 0.1484 |     0.5746 |             0.518  |       0.4754 |
| b86d_baseline_without_b86g | ridge                            |        21 | 0.2017 |     0.3877 |             0.2363 |       0.6753 |
| b86g_all_safe_numeric      | elasticnet                       |        21 | 0.185  |     0.599  |             0.5509 |       0.5431 |
| b86g_all_safe_numeric      | hist_gradient_boosting_regressor |        21 | 0.1423 |     0.6807 |             0.5224 |       0.4485 |
| b86g_all_safe_numeric      | random_forest_regressor          |        21 | 0.1425 |     0.6756 |             0.4926 |       0.4451 |
| b86g_all_safe_numeric      | ridge                            |        21 | 0.1863 |     0.5963 |             0.5509 |       0.5317 |
| b86g_high_priority_only    | elasticnet                       |        21 | 0.2079 |     0.2649 |             0.3037 |       0.7896 |
| b86g_high_priority_only    | hist_gradient_boosting_regressor |        21 | 0.1641 |     0.4548 |             0.4204 |       0.4707 |
| b86g_high_priority_only    | random_forest_regressor          |        21 | 0.1678 |     0.4335 |             0.458  |       0.4795 |
| b86g_high_priority_only    | ridge                            |        21 | 0.2089 |     0.2608 |             0.3037 |       0.7912 |

## 6. Two-stage results

- Selected workflow: `b86g_proxy_features_only` + `logistic_regression` / `ridge` at neutral threshold 0.05 C.

| feature_set                    | classifier                        | regressor                        | split_family        |    MAE |   Spearman |   top10pct_overlap |   false_promotion_rate |   anchor_MAE |
|:-------------------------------|:----------------------------------|:---------------------------------|:--------------------|-------:|-----------:|-------------------:|-----------------------:|-------------:|
| b86g_proxy_features_only       | hist_gradient_boosting_classifier | hist_gradient_boosting_regressor | hour_holdout        | 0.0527 |     0.8939 |             0.9467 |                 0.0396 |       0.2816 |
| b86g_proxy_features_only       | hist_gradient_boosting_classifier | random_forest_regressor          | hour_holdout        | 0.0518 |     0.8933 |             0.9333 |                 0.0396 |       0.1851 |
| b86g_proxy_features_only       | random_forest_classifier          | hist_gradient_boosting_regressor | hour_holdout        | 0.0527 |     0.893  |             0.9467 |                 0.036  |       0.2816 |
| b86g_proxy_features_only       | random_forest_classifier          | random_forest_regressor          | hour_holdout        | 0.0517 |     0.8927 |             0.9333 |                 0.036  |       0.1851 |
| b86g_no_status_columns         | hist_gradient_boosting_classifier | hist_gradient_boosting_regressor | hour_holdout        | 0.0523 |     0.8919 |             0.9467 |                 0.035  |       0.2784 |
| b86g_all_safe_numeric          | hist_gradient_boosting_classifier | hist_gradient_boosting_regressor | hour_holdout        | 0.0524 |     0.8901 |             0.9467 |                 0.035  |       0.2779 |
| b86g_proxy_plus_vector_compact | hist_gradient_boosting_classifier | hist_gradient_boosting_regressor | hour_holdout        | 0.0524 |     0.8901 |             0.9467 |                 0.035  |       0.2779 |
| b86g_all_safe_numeric          | hist_gradient_boosting_classifier | random_forest_regressor          | hour_holdout        | 0.051  |     0.89   |             0.8933 |                 0.035  |       0.178  |
| b86g_proxy_plus_vector_compact | hist_gradient_boosting_classifier | random_forest_regressor          | hour_holdout        | 0.0509 |     0.89   |             0.8933 |                 0.035  |       0.1779 |
| b86g_proxy_plus_vector_compact | random_forest_classifier          | hist_gradient_boosting_regressor | hour_holdout        | 0.0525 |     0.8897 |             0.9467 |                 0.0349 |       0.2779 |
| b86g_proxy_plus_vector_compact | random_forest_classifier          | random_forest_regressor          | hour_holdout        | 0.0511 |     0.8896 |             0.8933 |                 0.0349 |       0.1779 |
| b86g_high_priority_only        | hist_gradient_boosting_classifier | random_forest_regressor          | hour_holdout        | 0.0582 |     0.8881 |             0.8133 |                 0.0362 |       0.2015 |
| b86g_proxy_features_only       | random_forest_classifier          | random_forest_regressor          | forcing_day_holdout | 0.0589 |     0.8879 |             0.9333 |                 0.0388 |       0.0907 |
| b86d_baseline_without_b86g     | hist_gradient_boosting_classifier | hist_gradient_boosting_regressor | hour_holdout        | 0.0572 |     0.8872 |             0.8933 |                 0.036  |       0.3313 |
| b86g_no_status_columns         | hist_gradient_boosting_classifier | random_forest_regressor          | hour_holdout        | 0.0649 |     0.8868 |             0.8933 |                 0.035  |       0.2053 |
| b86g_all_safe_numeric          | random_forest_classifier          | hist_gradient_boosting_regressor | hour_holdout        | 0.0527 |     0.8858 |             0.9467 |                 0.0328 |       0.2779 |

## 7. Baseline comparison vs B8.6d/B8.6f

| split_family        |   b86g2_Spearman |   b86d_Spearman |   Spearman_delta_vs_b86d |   b86g2_top10pct_overlap |   b86d_top10pct_overlap |   top10_delta_vs_b86d | b86f_context_status   |
|:--------------------|-----------------:|----------------:|-------------------------:|-------------------------:|------------------------:|----------------------:|:----------------------|
| cell_group_holdout  |           0.5266 |          0.4623 |                   0.0643 |                   0.5333 |                  0.6    |               -0.0667 | BLOCKED               |
| forcing_day_holdout |           0.676  |          0.7091 |                  -0.0331 |                   0.6    |                  0.8    |               -0.2    | not_mapped            |
| hour_holdout        |           0.6651 |          0.7125 |                  -0.0474 |                   0.6    |                  0.8267 |               -0.2267 | not_mapped            |
| spatial_holdout     |           0.5174 |          0.172  |                   0.3453 |                   0.5    |                  0.3125 |                0.1875 | BLOCKED               |
| typology_holdout    |           0.4104 |          0.3611 |                   0.0493 |                   0.5619 |                  0.7143 |               -0.1524 | DIAGNOSTIC_ONLY       |

## 8. Blocked validation-family results

- spatial_holdout: Spearman=0.517, top10pct=0.500, false_promotion=0.163; cell_group_holdout: Spearman=0.527, top10pct=0.533, false_promotion=0.141; typology_holdout: Spearman=0.410, top10pct=0.562, false_promotion=0.209; forcing_day_holdout: Spearman=0.676, top10pct=0.600, false_promotion=0.109; hour_holdout: Spearman=0.665, top10pct=0.600, false_promotion=0.114

## 9. Feature ablation

- spatial_help=neighbourhood_context; neutral_false_promotion_help=canyon_roughness, edge_context, neighbourhood_context, overhead_geometry, pedestrian_shade, tree_building_interaction, typology_geometry; anchor_help=canyon_roughness, edge_context, neighbourhood_context, overhead_geometry, tree_building_interaction, typology_geometry

| ablation_variant           | split_family        |   Spearman_delta_full_minus_variant |   top10_delta_full_minus_variant |   false_promotion_delta_variant_minus_full |   anchor_MAE_delta_variant_minus_full |
|:---------------------------|:--------------------|------------------------------------:|---------------------------------:|-------------------------------------------:|--------------------------------------:|
| full_b86g_all_safe_numeric | cell_group_holdout  |                              0      |                           0      |                                     0      |                                0      |
| full_b86g_all_safe_numeric | forcing_day_holdout |                              0      |                           0      |                                     0      |                                0      |
| full_b86g_all_safe_numeric | hour_holdout        |                              0      |                           0      |                                     0      |                                0      |
| full_b86g_all_safe_numeric | spatial_holdout     |                              0      |                           0      |                                     0      |                                0      |
| full_b86g_all_safe_numeric | typology_holdout    |                              0      |                           0      |                                     0      |                                0      |
| drop_pedestrian_shade      | cell_group_holdout  |                             -0.0684 |                           0.1333 |                                    -0.0041 |                               -0.0181 |
| drop_pedestrian_shade      | forcing_day_holdout |                             -0.0146 |                           0.0667 |                                     0.0125 |                                0.0091 |
| drop_pedestrian_shade      | hour_holdout        |                             -0.0164 |                           0.04   |                                     0.0077 |                                0.0113 |
| drop_pedestrian_shade      | spatial_holdout     |                             -0.0577 |                          -0.125  |                                    -0.004  |                               -0.0317 |
| drop_pedestrian_shade      | typology_holdout    |                              0.0273 |                           0.0286 |                                     0.0135 |                                0.0171 |
| drop_overhead_geometry     | cell_group_holdout  |                             -0.0315 |                           0.0667 |                                     0.0168 |                                0.0232 |
| drop_overhead_geometry     | forcing_day_holdout |                              0.0042 |                           0.0667 |                                     0.0308 |                                0.0226 |
| drop_overhead_geometry     | hour_holdout        |                              0.0182 |                           0.04   |                                     0.0279 |                                0.0186 |
| drop_overhead_geometry     | spatial_holdout     |                             -0.0791 |                          -0.125  |                                     0.0446 |                               -0.1543 |

## 10. Anchor / neutral / unstable diagnostics

- Anchor diagnostic rows: 21
- Neutral and near-zero diagnostic rows: 68
- Unstable-cell diagnostic rows: 33

## 11. Whether B8.6g features help

The promotion gate status is `B86G2_DIAGNOSTIC_IMPROVEMENT_ONLY`. Improvements are treated as diagnostic unless spatial Spearman, spatial top-k, neutral false-promotion, anchor behavior, and at least one supporting weak holdout all pass together.

## 12. AOI preflight readiness

| readiness_item   | status                | evidence                                                     | allowed_future_lane                               |
|:-----------------|:----------------------|:-------------------------------------------------------------|:--------------------------------------------------|
| spatial_holdout  | BLOCKED               | Spearman=0.517; top10pct=0.500; delta_vs_b86d=(0.345, 0.188) | B8.6h_scope_limited_dry_run_preflight_review_only |
| aoi_preflight    | AOI_PREFLIGHT_BLOCKED | B8.6g2 creates no AOI-wide prediction.                       | B8.6h_scope_limited_dry_run                       |
| b9               | B9_BLOCKED            | B8.6g2 is not B9 and produces no B9 output.                  | none_in_this_lane                                 |

## 13. Next lane recommendation

Recommended next lane: `B8.7-N300-PRE plus B8.6g3 true vector source acquisition`.

| future_lane                           | recommended_priority   | decision    | why                                                                                                    |
|:--------------------------------------|:-----------------------|:------------|:-------------------------------------------------------------------------------------------------------|
| B8.7-N300-PRE                         | high                   | recommended | Add targeted sample support because B8.6g2 remains compact N150 validation only.                       |
| B8.6g3 true vector source acquisition | high                   | recommended | Connected shade corridor remains unavailable; proxy families need true vector sources.                 |
| B8.6h scope-limited dry-run           | conditional            | not_now     | Only appropriate after reviewed compact evidence; B8.6g2 itself creates no AOI-wide output.            |
| no-go / wait                          | fallback               | fallback    | Use if reviewers reject N300/vector acquisition. Ablation spatial-help signals: neighbourhood_context. |

## 14. Claim boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not risk score or hazard score.
- Not observed truth.
- Not causal feature importance.
- No raster read/open/copy/create/write.
- No QGIS or SOLWEIG.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
