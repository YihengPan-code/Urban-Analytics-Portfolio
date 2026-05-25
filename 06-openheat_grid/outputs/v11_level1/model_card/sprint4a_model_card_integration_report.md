# Sprint 4A Model Card Integration Report

## Files created

- `docs/v11/SystemA_Level1_Interim_Model_Card_CN.md`
- `configs/v11/system_a_level1_output_contract.yaml`
- `outputs/v11_level1/model_card/system_a_level1_output_contract.md`
- `outputs/v11_level1/model_card/system_a_level1_evidence_ledger.csv`
- `outputs/v11_level1/model_card/system_a_level1_claim_boundary_matrix.csv`
- `outputs/v11_level1/model_card/system_a_level1_current_recommendations.md`
- `outputs/v11_level1/model_card/system_a_level1_current_outputs_sample.csv`
- `outputs/v11_level1/model_card/sprint4a_model_card_integration_report.md`
- `scripts/v11_l1_export_system_a_output_sample.py`

## Evidence sources found

Found 37 evidence artifacts.

- `outputs/v11_level1/m2_recovery/m2_recovery_report.md`
- `outputs/v11_level1/pairing_audit/station_openmeteo_pairing_report.md`
- `outputs/v11_level1/reproduction/reproduction_report.md`
- `outputs/v11_level1/reproduction/metrics_reproduction_table.csv`
- `outputs/v11_level1/formal_hourly_reproduction/formal_hourly_reproduction_report.md`
- `outputs/v11_level1/formal_hourly_reproduction/formal_hourly_oof_derived_metrics_report.md`
- `outputs/v11_level1/formal_hourly_reproduction/formal_hourly_oof_derived_metrics.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_report.md`
- `outputs/v11_level1/feature_ablation/feature_ablation_metrics.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_delta_vs_proxy.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_high_tail_metrics.csv`
- `outputs/v11_level1/feature_ablation/feature_ablation_per_station_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/sprint2b_blocked_time_high_tail_report.md`
- `outputs/v11_level1/blocked_time_high_tail/blocked_time_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/future_holdout_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/threshold_scan_metrics.csv`
- `outputs/v11_level1/blocked_time_high_tail/residual_by_station.csv`
- `outputs/v11_level1/blocked_time_high_tail/s142_sensitivity_metrics.csv`
- `outputs/v11_level1/event_calibration/sprint2c_event_calibration_report.md`
- `outputs/v11_level1/event_calibration/operating_point_summary.csv`
- `outputs/v11_level1/event_calibration/advisory_mapping_candidates.csv`
- `outputs/v11_level1/event_calibration/threshold_stability_summary.csv`
- `outputs/v11_level1/event_calibration/score_bin_event_rates.csv`
- `outputs/v11_level1/event_calibration/event_calibration_by_station.csv`
- `outputs/v11_level1/formula_v2/sprint3a_formula_v2_proxy_benchmark_report.md`
- `outputs/v11_level1/formula_v2/formula_candidate_registry.csv`
- `outputs/v11_level1/formula_v2/formula_vs_event_score_comparison.csv`
- `outputs/v11_level1/formula_v2/advanced_formula_feasibility.csv`
- `outputs/v11_level1/probability_calibration/sprint3b_pge31_probability_calibration_report.md`
- `outputs/v11_level1/probability_calibration/probability_model_selection_summary.csv`
- `outputs/v11_level1/probability_calibration/probability_calibration_metrics.csv`
- `outputs/v11_level1/probability_calibration/probability_threshold_metrics.csv`
- `outputs/v11_level1/probability_calibration/probability_vs_event_score_mapping.csv`
- `outputs/v11_level1/probability_calibration/reliability_summary.csv`
- `outputs/v11_level1/probability_calibration/probability_by_station.csv`
- `outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv`
- `docs/handoff/OpenHeat_v1_1_v1_2_canonical_development_handoff_2026-05-24.md`

## Evidence sources missing / gaps

- Missing: `docs/v11/SystemA_Level1_Level2_architecture_discussion_record_CN.md`
- Missing: `docs/v11/OpenHeat_SystemA_next_development_plan_GPT_Codex_CN.md`

## Primary paths

- Model card: `docs/v11/SystemA_Level1_Interim_Model_Card_CN.md`
- Output contract YAML: `configs/v11/system_a_level1_output_contract.yaml`
- Output contract markdown: `outputs/v11_level1/model_card/system_a_level1_output_contract.md`
- Evidence ledger: `outputs/v11_level1/model_card/system_a_level1_evidence_ledger.csv`
- Claim boundary matrix: `outputs/v11_level1/model_card/system_a_level1_claim_boundary_matrix.csv`
- Sample output: `outputs/v11_level1/model_card/system_a_level1_current_outputs_sample.csv`

## Sample output

Sampled 200 rows from outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv.

Rows written: 200. Full prediction export was not created.

## Current model package definition

- Regression score: `M4_like_inertia_ridge` -> `wbgt_a_score_c`。
- Probability companion: `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration` -> `p_ge31_diagnostic`。
- ge33: exploratory only。
- Sensitivity candidates only: `M7_like_compact_weather_ridge`, `L1_full_dynamic`, `L1_proxy_radiation`。

## Compliance notes

- No forbidden files touched by Sprint 4A outputs: True。
- Forbidden-created path check: none。
- No fallback used。
- No new model training。
- No M3/M4/M7 rerun, feature ablation rerun, formula benchmark rerun, or probability calibration rerun。
- No formula-v2 implementation。
- No System B/v12/SOLWEIG/QGIS/rasters/archive collector/GitHub Actions archive lane touched。
- No full prediction export; sample is capped at 200 rows。
- No commit/stage performed by this script。

## Sprint 4A.1 patch note

Sprint 4A.1 patch added threshold wording correction and clarified station_diagnostic vs aoi_temporal output modes.

## Next recommended action

Proceed to Sprint 4B prospective forecast evaluation design, then Sprint 4C `p_ge31_diagnostic` export/reliability hardening.
