# OpenHeat System B Surrogate Baseline Benchmark (B8.2)

This note documents the B8.2 baseline benchmark protocol. The filename keeps
the existing `_CN` convention, but the text is ASCII to avoid local Windows
encoding drift.

## Scope

B8.2 benchmarks baseline surrogate/emulator models for SOLWEIG-derived System B
targets in the existing N150 label-feature matrix. It does not create AOI-wide
prediction maps, does not create local WBGT, does not create `hazard_score` or
`risk_score`, and does not couple System A and System B.

## Targets

- Primary: `delta_tmrt_p90_c`
- Secondary: `tmrt_p90_c`
- Retained label: `m_rad_pct01` for post-prediction rank interpretation only

`m_rad_pct01` is not the headline regression target.

## Feature Contract

The benchmark uses `outputs/v12_surrogate/b8_dataset_audit/feature_schema.csv`
as the source of truth. Headline predictors are limited to rows where:

- `role == feature`
- `predictor_tier == physical_core`

The benchmark also applies a hard name-block for target-derived, SOLWEIG output,
reference/rank, metadata/provenance, exposure, vulnerability, risk, social
proxy, source, note, version, interpretation, and nearest-name columns.

Spatial coordinate predictors are not included in the headline model family.
They may be used only in future diagnostic runs with explicit labelling.

## Models

The implemented baseline family is:

- Featureless train-fold mean baseline
- Ridge
- ElasticNet
- RandomForestRegressor
- ExtraTreesRegressor
- HistGradientBoostingRegressor

LightGBM, XGBoost, and deep learning are intentionally out of scope. Tree grids
are reduced for runtime in the full split-family benchmark and documented in
the generated report.

## Validation

The benchmark consumes the existing B8.1 manifests only:

- `cell_grouped_holdout`
- `spatial_holdout`
- `feature_bin_holdout`
- `hour_holdout`
- `scenario_holdout`

Blocked or degenerate feature-bin splits are skipped. No random row split is
created or used as evidence. Cell-grouped, spatial, and valid feature-bin
families assert no train/test `cell_id` overlap. Hour and scenario holdouts may
reuse cells by design.

## Outputs

All B8.2 outputs are written under:

`outputs/v12_surrogate/b8_model_benchmark/`

The required artifacts are:

- `surrogate_model_metrics.csv`
- `surrogate_predictions_oof.csv.gz`
- `topk_overlap_by_model.csv`
- `stratified_error_by_feature_bin.csv`
- `split_family_summary.csv`
- `model_family_comparison_report.md`
- `B8_2_BENCHMARK_STATUS.md`

## Claim Boundary

These models approximate SOLWEIG-derived Tmrt targets under the current N150
single-forcing setup. They are not validated local WBGT predictors, not public
health warning models, not risk maps, and not causal feature-importance
evidence.
