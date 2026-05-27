# B8.6g2 Feature-Upgraded Surrogate Model Card

Generated: 2026-05-27 23:03:52

## Intended role

Compact N150 retest of B8.6g feature-upgraded surrogate candidates for SOLWEIG-derived Tmrt-delta labels. This is a diagnostic validation artifact only.

## Decision

`B86G2_DIAGNOSTIC_IMPROVEMENT_ONLY`

## Selected workflow

- Feature set: `b86g_proxy_features_only`
- Stage 1 classifier: `logistic_regression`
- Stage 2 regressor: `ridge`
- Neutral threshold: `0.05` C
- Primary target: `delta_tmrt_p90_c`

## Validation headline

| split_family        |    MAE |   Spearman |   top10pct_overlap |   neutral_accuracy |   false_promotion_rate |
|:--------------------|-------:|-----------:|-------------------:|-------------------:|-----------------------:|
| cell_group_holdout  | 0.1659 |     0.5266 |             0.5333 |             0.8589 |                 0.1411 |
| forcing_day_holdout | 0.1352 |     0.676  |             0.6    |             0.8913 |                 0.1087 |
| hour_holdout        | 0.1397 |     0.6651 |             0.6    |             0.8856 |                 0.1144 |
| spatial_holdout     | 0.168  |     0.5174 |             0.5    |             0.8372 |                 0.1628 |
| typology_holdout    | 0.199  |     0.4104 |             0.5619 |             0.7907 |                 0.2093 |

## Non-claims

Not B9, not AOI-wide prediction, not local WBGT, not risk/hazard score, not observed truth, not causal feature importance, no raster/QGIS/SOLWEIG, no Tmrt-to-WBGT conversion, and no System A/B coupling.
