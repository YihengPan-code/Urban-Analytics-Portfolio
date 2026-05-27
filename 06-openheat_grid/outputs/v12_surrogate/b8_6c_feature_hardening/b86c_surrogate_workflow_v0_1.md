# B8.6c Surrogate Workflow v0.1

Generated: 2026-05-27 19:28:28

## Inputs

- F5 compact pairwise labels only: `delta_tmrt_p90_c = overhead_as_canopy - base` plus companion delta targets.
- Compact N150 feature tables only: `n150_sampling_feature_matrix.csv` and `n150_candidate_universe.csv`.
- B8.6b compact diagnostics and B8.5-F4 anchor/neutral/unstable cell lists for audit context.

## Label Contract

- Labels are SOLWEIG-derived Tmrt deltas, not observed truth and not WBGT.
- Primary target is `delta_tmrt_p90_c`; companion targets are mean, p50, and p95 deltas.
- `cell_id`, `forcing_day_id`, ranks, and target columns are not numeric predictors.

## Feature Contract

- Safe features must be compact, non-target-derived, and pre-existing in the compact tables.
- Target, rank, WBGT, risk, hazard, score, observed, path/status, System A, and future exposure/vulnerability columns are excluded.
- Coordinates are allowed only for spatial bins or diagnostic feature sets, never causal interpretation.
- Interactions are limited to pre-registered physical pairs.

## Validation Contract

- Primary evidence remains forcing-day holdout.
- Supporting evidence includes cell-group, spatial, typology, and hour holdouts.
- Random row split is not a main evidence path for this lane.

## Model Family Contract

- Use modest ridge, elasticnet, random forest, and histogram gradient boosting baselines plus dummy mean.
- Model selection must report failure modes, not only aggregate fit.
- Feature importance, if produced later, is diagnostic and non-causal.

## Diagnostic Outputs

- Split failure summary, spatial and typology inventories, anchor/neutral/unstable audits, h10 contrast, OOF prediction audit, and two-stage pretest metrics.

## Promotion Gates

- B8.6c can pass only if hardened feature sets materially improve weak supporting holdouts without boundary violations.
- Two-stage can be called promising if neutral and supporting holdouts improve enough to justify B8.6d.
- Otherwise B8.6c remains diagnostic-only.

## Forbidden Outputs

- No B9.
- No AOI-wide prediction.
- No local WBGT, hazard_score, risk_score, or System A/B coupling.
- No Tmrt-to-WBGT conversion.
- No raster/QGIS/SOLWEIG operation.

## What B8.6d Should Do Next

- Formalize the improved surrogate workflow only after reviewing B8.6c diagnostics.
- Keep feature upgrade, targeted N300, or extra forcing days conditional on spatial/typology generalisation improving.
