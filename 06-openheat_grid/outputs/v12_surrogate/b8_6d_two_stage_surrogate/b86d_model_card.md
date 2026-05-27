# B8.6d Two-Stage Surrogate Model Card

Generated: 2026-05-27 20:29:14

## Intended Role

Compact N150 review of a two-stage surrogate for SOLWEIG-derived Tmrt-delta labels. The workflow ranks local radiative cooling deltas; it is not WBGT, risk, observed truth, B9, or AOI-wide prediction.

## Decision

`B86D_TWO_STAGE_DIAGNOSTIC_ONLY`

## Selected Workflow

- Feature set: `full_safe_compact`
- Stage 1 classifier: `logistic_regression`
- Stage 2 regressor: `ridge`
- Neutral threshold: `0.05` C
- Primary target: `delta_tmrt_p90_c`

## Validation

| split_family        |    MAE |   Spearman |   top10pct_overlap |   neutral_accuracy |   false_promotion_rate |
|:--------------------|-------:|-----------:|-------------------:|-------------------:|-----------------------:|
| cell_group_holdout  | 0.1741 |     0.4623 |             0.6    |             0.7387 |                 0.2172 |
| forcing_day_holdout | 0.0864 |     0.7091 |             0.8    |             0.8607 |                 0.1056 |
| hour_holdout        | 0.088  |     0.7125 |             0.8267 |             0.8667 |                 0.1085 |
| spatial_holdout     | 0.2243 |     0.172  |             0.3125 |             0.667  |                 0.2378 |
| typology_holdout    | 0.2937 |     0.3611 |             0.7143 |             0.7143 |                 0.2553 |

## Explicit Non-Claims

Not B9, not AOI-wide, not local WBGT, not risk, not observed truth, not causal feature importance, no raster/QGIS/SOLWEIG, no Tmrt-to-WBGT conversion, and no System A/B coupling.
