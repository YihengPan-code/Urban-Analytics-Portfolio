# B8.0 Surrogate-Ready Dataset Audit

Status: **PASS**

## Input Files

- modifier_targets (required): FOUND - `outputs\v12_solweig_n150_execution\n150_modifier_targets_b5.csv`
- focus_tmrt_summary (required): FOUND - `outputs\v12_solweig_n150_execution\n150_focus_tmrt_summary_merged.csv`
- base_vs_overhead_delta (required): FOUND - `outputs\v12_solweig_n150_execution\n150_base_vs_overhead_delta_merged.csv`
- overhead_features (required): FOUND - `data\grid\v10\toa_payoh_grid_v10_features_overhead_sensitivity.csv`
- umep_features (required): FOUND - `data\grid\v10\toa_payoh_grid_v10_features_umep_with_veg.csv`
- morphology_features (required): FOUND - `data\grid\v10\toa_payoh_grid_v10_umep_morphology_with_veg.csv`
- reference_values (optional): FOUND - `outputs\v12_solweig_n150_execution\n150_reference_values_b5.csv`
- typology_candidates (optional): FOUND - `data\grid\v12\solweig_typology_cell_candidates.csv`

## Expected N150 Structure

- Row count: 1500
- Unique cell count: 150
- Scenario values: base, overhead_as_canopy
- hour_sgt values: 10, 12, 13, 15, 16
- target_version values: systemb_target_family_v0_1_b5
- reference_domain_version values: n150_training_future

## Required Label Columns

- Missing required target / label columns: (none)
- Primary physical surrogate target: `delta_tmrt_p90_c`
- Secondary target: `tmrt_p90_c`
- Retained post-prediction modifier / label: `m_rad_pct01`

## Checks

- required_inputs_found: PASS
- row_count_is_1500: PASS
- unique_cell_count_is_150: PASS
- scenario_set_matches: PASS
- hour_sgt_set_matches: PASS
- target_version_matches: PASS
- reference_domain_version_matches: PASS
- primary_target_exists: PASS
- primary_target_complete: PASS
- secondary_target_exists: PASS
- retained_modifier_exists: PASS
- feature_matrix_exists: PASS
- selected_feature_leakage_clean: PASS
- required_label_columns_present: PASS

## Missingness Summary

- Selected B8.2 physical-core predictor count: 115
- Numeric selected feature count: 114
- Categorical selected feature count: 1
- Spatial diagnostic coordinate count excluded from headline predictors: 4
- Excluded nonphysical/social feature count: 16
- Excluded metadata/constant/contract count: 92
- All-NaN selected feature columns: (none)
- Constant selected feature columns: (none)
- High missingness >20%: (none)
- High missingness >50%: (none)
- High missingness >80%: (none)

## Leakage Summary

- Excluded leakage-like columns: 7
- Selected feature columns contain no leakage-like name tokens: PASS
- Raw merged matrix retains audit/label columns; B8.2 should consume only `feature_schema.csv` rows where `role == feature` and `predictor_tier == physical_core` for the headline physical surrogate.
- Spatial diagnostic columns are retained for optional diagnostic models only, not the headline physical surrogate.

## Caveats

- `m_rad_pct01` is retained as a reference-domain percentile/rank modifier label, not the only regression target.
- The emphasized B8.2 targets are `delta_tmrt_p90_c` and `tmrt_p90_c`; no Tmrt value is converted to WBGT.
- Hygiene patch B8.1.1 tightened predictor eligibility; exposure/vulnerability/risk/social fields, provenance strings, constants, contract fields, and spatial coordinates are excluded from headline B8.2 predictors.
- No model training or AOI-wide inference is performed in B8.0.

## Next Recommended Action

Review the audit outputs and then run B8.1 validation split manifests before any B8.2 benchmark work.
