# A-L1H.4 Status

Status: A_L1H4_COMPANION_PROMISING
Generated: 2026-05-27
Branch: codex/systema-l1h4-prob-exceedance-suite

## Scope

Probabilistic / exceedance companion suite for Level 1 threshold behavior around 31 C / 33 C. Companion only; deterministic WBGT_A remains primary.

## Commands Run

- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts/v11_l1h4_run_prob_exceedance_suite.py --config configs/v11/systema_l1h4_prob_exceedance_suite.yaml`

## Key Results

- Rows/stations/events: n_rows=1674; n_stations=27; n_events_ge31=204; n_events_ge33=15
- Probability: isotonic_m4_score_ge31 Brier=0.052, ECE_fixed=0.018, PR-AUC=0.610, best_F1 threshold=0.446.
- Expected exceedance: deterministic_score_gap_m4_ge31 MAE=0.100 C, positive-event MAE=0.779 C; delta MAE vs deterministic score gap=0.000 C.
- Interval: conformal_m4_residual nominal 90% coverage=0.898, mean width=2.869 C.
- Baseline comparison: isotonic_m4_score_ge31 best_F1 vs WBGT_A fixed_31: recall 0.588->0.765 (delta 0.176), precision 0.682->0.678 (delta -0.004), miss_rate 0.412->0.235.
- S142 caveat: S142: n_ge31=15, recall=0.533, miss_rate=0.467, false_alarm_ratio=0.000; S139: n_ge31=1, recall=1.000, miss_rate=0.000, false_alarm_ratio=0.889. Station diagnostics remain caveats, not station corrections.
- Output contract recommendation: Keep WBGT_A as primary; add P_ge31, expected exceedance, and interval columns as optional companion diagnostics only.

## Files Created / Modified

- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_input_inventory.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_model_input_table.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_feature_schema.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_validation_splits.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_deterministic_baseline_metrics.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_threshold_policy_metrics.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_probability_model_metrics.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_probability_calibration_bins.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_expected_exceedance_metrics.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_quantile_interval_metrics.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_oof_predictions.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_station_threshold_diagnostics.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_decision_matrix.csv`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_output_contract_draft.md`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_model_card.md`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_report.md`
- `outputs/v11_systema_l1_high_tail/prob_exceedance_suite/A_L1H4_STATUS.md`
- `docs/v11/OpenHeat_SystemA_L1H4_prob_exceedance_suite_CN.md`

## Caveats

- Retrospective station-held-out companion evidence only.
- P_ge31 is not an official warning probability.
- P_ge33 remains exploratory when low support.
- No station-adjusted WBGT, local 100 m WBGT, System B coupling output, risk_score, or hazard_score.

## Safe To Commit

- Config, scripts, docs, and compact CSV/Markdown outputs after review.

## Not Safe To Commit

- Raw archives, rasters, SOLWEIG/System B outputs, tif/tiff files, svfs.zip, patch zip packages, raw API dumps, or large forecast/live CSVs.
