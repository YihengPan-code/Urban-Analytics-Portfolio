# B8.6b System B Surrogate Model Card

Generated: 2026-05-27 18:11:49

## Intended Role

Surrogate-promotion review for SOLWEIG-derived F5 N150 multi-forcing Tmrt labels. The primary use is local radiative ranking review, not public-health warning or risk scoring.

## Decision

`B86B_WEAK_NEEDS_FEATURE_UPGRADE`

## Dataset

- Rows: 1500
- Cells: 150
- Forcing days: 2
- Hours: 10, 12, 13, 15, 16
- Primary target: `delta_tmrt_p90_c = overhead_as_canopy - base`.
- Predictor count: 11; `cell_id` and `forcing_day_id` are excluded.

## Validation

- Primary: forcing-day holdout.
- Main supporting: cell-group, hour, spatial, and typology holdouts.
- Diagnostic only: random split.

## Headline

- Forcing-day holdout MAE=0.0666, R2=0.850, Spearman=0.864, top10pct=1.000, improvement=70.0%.
- Most predictable target: base_tmrt_p90_c (Spearman=0.867); primary p90 Spearman=0.864.

## Explicit Non-Claims

- Not B9.
- Not local WBGT.
- Not risk.
- Not observed truth.
- Not causal feature importance.
- No raster committed.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
