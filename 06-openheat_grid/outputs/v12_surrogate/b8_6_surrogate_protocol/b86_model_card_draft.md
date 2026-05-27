# B8.6 System B Surrogate Model Card Draft

Generated: 2026-05-27 16:44:12

## Intended Role

Protocol and baseline benchmarking for a surrogate/emulator of SOLWEIG-derived System B radiative labels in Toa Payoh.

## Current Decision

`B86_WEAK_BASELINE_NEEDS_N150_MULTIFORCING`

## Dataset

- Rows: 750
- Cells: 150
- Hours: 10, 12, 13, 15, 16
- Primary target: `delta_tmrt_p90_c = overhead_as_canopy - base`.
- Baseline predictors: 11 compact physical/hour-aware columns.

## Validation Families

- Main: `cell_group_holdout`, `spatial_holdout`, `typology_holdout`, `hour_holdout`.
- Diagnostic only: `random_split`.
- Future required: `forcing_day_holdout`, `scenario_holdout` for non-pairwise scenario-labelled targets.

## Baseline Headline

- random_forest_regressor on delta_tmrt_p90_c: mean main-holdout MAE=0.1616, R2=-0.145, Spearman=0.611, MAE improvement vs dummy=50.9%

## N24 Stress-Validation Bridge

- Bridge rows: 21.
- N24 validates stress interpretation only; it is not training evidence here.

## Explicit Non-Claims

- Not B9.
- Not local WBGT.
- Not risk.
- Not observed truth.
- Not causal feature importance.
- No raster committed.
- No Tmrt-to-WBGT conversion.
