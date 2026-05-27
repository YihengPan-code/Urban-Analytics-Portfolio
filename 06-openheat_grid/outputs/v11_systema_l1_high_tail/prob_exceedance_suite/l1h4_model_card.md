# A-L1H.4 Probabilistic / Exceedance Companion Model Card

Generated: 2026-05-27
Decision: `A_L1H4_COMPANION_PROMISING`

## Intended Use

Retrospective Level 1 companion diagnostics around the 31 C / 33 C WBGT thresholds. The deterministic WBGT_A baseline remains the primary System A output.

## Not Intended Use

No station-adjusted WBGT, no local 100 m WBGT, no System B coupling output, no public warning probability, and no risk or hazard score.

## Data And Validation

Primary station-held-out rows: 1674; stations: 27; ge31 events: 204; ge33 events: 15. LOSO is primary; blocked-time is secondary where source folds exist. Standardized logistic-regression hyperparameters are fixed and disclosed in prediction rows; a dependency-free solver is used because sklearn estimator fits hard-exit in this runtime.

## Headline

- Probability: isotonic_m4_score_ge31 Brier=0.052, ECE_fixed=0.018, PR-AUC=0.610, best_F1 threshold=0.446.
- Expected exceedance: deterministic_score_gap_m4_ge31 MAE=0.100 C, positive-event MAE=0.779 C; delta MAE vs deterministic score gap=0.000 C.
- Interval: conformal_m4_residual nominal 90% coverage=0.898, mean width=2.869 C.
- Baseline comparison: isotonic_m4_score_ge31 best_F1 vs WBGT_A fixed_31: recall 0.588->0.765 (delta 0.176), precision 0.682->0.678 (delta -0.004), miss_rate 0.412->0.235.

## Decision Matrix

| criterion                     | status      | detail                                                                                                                                               |
| ----------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| primary_threshold_recall_miss | PASS        | isotonic_m4_score_ge31 best_F1 vs WBGT_A fixed_31: recall 0.588->0.765 (delta 0.176), precision 0.682->0.678 (delta -0.004), miss_rate 0.412->0.235. |
| false_alarm_precision_control | PASS        | precision=0.678; false_alarm_ratio=0.322.                                                                                                            |
| probability_calibration       | PASS        | isotonic_m4_score_ge31 Brier=0.052, ECE_fixed=0.018, PR-AUC=0.610, best_F1 threshold=0.446.                                                          |
| no_s142_sensitivity           | PASS        | no-S142 recall delta vs fixed_31=0.180.                                                                                                              |
| blocked_time_secondary        | PASS        | blocked-time recall delta vs fixed_31=0.358.                                                                                                         |
| ge33_support                  | LOW_SUPPORT | P_ge33 remains exploratory and is not promoted.                                                                                                      |
| expected_exceedance_available | PASS        | Expected exceedance metrics are available for score-gap/direct/two-part companions.                                                                  |
| interval_available            | PASS        | Interval metrics are available for conformal and quantile companions where runtime support exists.                                                   |
| claim_boundary                | PASS        | Companion only; no station-adjusted WBGT, no local 100m WBGT, no System B coupling output, no risk/hazard score.                                     |

## Caveats

- S142: n_ge31=15, recall=0.533, miss_rate=0.467, false_alarm_ratio=0.000; S139: n_ge31=1, recall=1.000, miss_rate=0.000, false_alarm_ratio=0.889. Station diagnostics remain caveats, not station corrections.
- ge33 probability remains exploratory when event support is low.
- All companion outputs are retrospective station-held-out diagnostics unless separately promoted.
