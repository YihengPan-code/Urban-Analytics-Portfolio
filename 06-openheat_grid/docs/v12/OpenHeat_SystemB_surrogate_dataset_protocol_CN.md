# OpenHeat System B Surrogate Dataset And Validation Protocol (B8)

This note is the B8 protocol record. The filename keeps the existing `_CN`
suffix, but the B8.1.1 hygiene patch text is written in ASCII to avoid
encoding drift in the local Windows toolchain.

## Scope

B8 covers only:

- B8.0 surrogate-ready dataset audit from B7 N150 SOLWEIG-derived labels and v10 grid features.
- B8.1 validation split manifests for later B8.2 benchmark work.
- B8.1.1 hygiene hardening for predictor eligibility and degenerate feature-bin split handling.

This stage does not train models, does not create AOI-wide final outputs, does
not perform System A/B coupling, does not convert Tmrt to WBGT, and does not
create `hazard_score` or `risk_score`.

## Targets And Retained Labels

The primary physical surrogate target is `delta_tmrt_p90_c`.

The secondary target is `tmrt_p90_c`.

`m_rad_pct01` is retained in the label matrix and metadata as a
reference-domain percentile / rank modifier. It is not the only regression
target and should not replace the physical target audit.

Companion labels include:

- `tmrt_p75_c`
- `tmrt_p95_c`
- `tmrt_mean_c`
- `tmrt_max_c`
- `pct_pixels_tmrt_ge_40`
- `pct_pixels_tmrt_ge_45`
- `pct_pixels_tmrt_ge_50`
- `pct_pixels_tmrt_ge_55`

## B8.0 Dataset Audit

Script: `scripts/v12_b8_prepare_surrogate_dataset.py`

Config: `configs/v12/systemb_surrogate_b8_config.yaml`

Output directory: `outputs/v12_surrogate/b8_dataset_audit/`

The audit:

- checks required and optional inputs;
- joins B7 N150 labels to v10 cell features on `cell_id`;
- creates `row_id = cell_id + "|" + scenario + "|" + hour_sgt`;
- checks 150 cells, 2 scenarios, 5 hours, and 1500 rows;
- checks `target_version = systemb_target_family_v0_1_b5`;
- checks `reference_domain_version = n150_training_future`;
- writes `feature_schema.csv`;
- excludes target-derived, rank-derived, reference-domain, SOLWEIG-derived, nonphysical/social, provenance, source, version, note, name, method, interpretation, constant, and target-contract columns from B8.2 headline predictors;
- writes missingness, constant-column, high-missingness, leakage, and target distribution summaries.

`surrogate_label_feature_matrix.csv` is the raw merged audit matrix and keeps
labels plus audit columns. B8.2 headline models should use only
`feature_schema.csv` rows where `role == feature` and
`predictor_tier == physical_core`.

## B8.2 Candidate Feature Tiers

`physical_core`: SVF, shade, building density, building height, open/building
fractions, tree/grass/water/built/NDVI fields, road/hardscape fields, overhead
fractions, and park/water distance fields.

`spatial_diagnostic`: `lat`, `lon`, `centroid_x_svy21`, and
`centroid_y_svy21`. These may be used only in a diagnostic model, not as the
headline physical surrogate.

`excluded_nonphysical`: exposure, vulnerability, risk, and social proxy fields.

`excluded_metadata`: source, provenance, version, note, name, method,
interpretation, target-contract, constant, all-NaN, identifier, and label
contract fields.

## B8.1 Validation Split Protocol

Script: `scripts/v12_b8_make_validation_splits.py`

Output directory: `outputs/v12_surrogate/b8_validation_protocol/`

All manifests keep these common columns:

- `split_family`
- `split_name`
- `fold_id`
- `role`
- `row_id`
- `cell_id`
- `scenario`
- `hour_sgt`
- `reason`
- `notes`

`split_manifest_feature_bin.csv` also includes `split_status`,
`train_cell_count`, and `test_cell_count` so degenerate bins are
machine-readable.

## Why Random Row Split Is Not Main Evidence

The row unit is `cell_id x hour_sgt x scenario`. A random row split would leak
static cell-level features because the same cell could appear in both train and
test rows. B8.1 therefore prioritizes cell-grouped, spatial, and valid
feature-bin holdouts for cell generalization. Hour and scenario holdouts are
transfer diagnostics.

## Split Families

`cell_grouped_holdout`: deterministic five-fold cell holdout. The same
`cell_id` must never appear in both train and test within a fold.

`spatial_holdout`: uses a usable coordinate pair, preferring
`centroid_x_svy21` / `centroid_y_svy21`. If no coordinates are available, the
split is explicitly blocked instead of faked.

`feature_bin_holdout`: creates low/high bins for available physical feature
families. A feature-bin split is valid only when both train and test have at
least 30 unique cells. Degenerate bins are marked `BLOCKED_DEGENERATE`.

`hour_holdout`: leave-one-hour-out. This tests hour transfer; the same cells
may appear in train and test across different hours by design.

`scenario_holdout`: base to overhead and overhead to base transfer diagnostics.
The same cells may appear in train and test across scenarios by design.

## B8.2 Consumption Rules

Future B8.2 benchmark work should:

- join split manifests to `surrogate_label_feature_matrix.csv` by `row_id`;
- use only `role == feature` and `predictor_tier == physical_core` for headline predictors;
- optionally use `spatial_diagnostic` only in a separately labelled diagnostic model;
- exclude `split_status == BLOCKED_DEGENERATE` feature-bin rows from validation folds;
- treat `delta_tmrt_p90_c` as the primary physical target and `tmrt_p90_c` as the secondary target;
- retain `m_rad_pct01` as a reference-domain modifier / label, not the only target;
- avoid random row split as headline evidence.
