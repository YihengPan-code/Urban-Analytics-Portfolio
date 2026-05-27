# System A A-L1H.5 Model Card / Output Contract Finalization

Generated: 2026-05-27
Decision status: `A_L1H5_CONTRACT_PASS`

## 1. Why A-L1H.5 Follows A-L1H.4 And A-L2.1c

A-L1H.4 concluded `A_L1H4_COMPANION_PROMISING`: `wbgt_a_c` remains primary, `p_ge31_optional` improves ge31 threshold behavior as a companion, `p_ge33_optional` remains low-support exploratory, and expected exceedance / intervals are optional diagnostics. A-L2.1c found weak station-context high-tail residual signal and score residual was not identifiable, so this lane finalizes a Level 1 contract without a station correction layer.

## 2. System A Primary Output

The primary output is `wbgt_a_c`: a calibrated hourly WBGT_A temporal baseline. Deterministic ge31 severity fields are derived from it and are not risk scores.

## 3. Optional Companions

| item                                      | decision           | allowed_column_name                                                         | caveat                                                                          |
| ----------------------------------------- | ------------------ | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| wbgt_a_c deterministic baseline           | PRIMARY            | wbgt_a_c                                                                    | Calibrated hourly WBGT_A temporal baseline, not local 100 m WBGT.               |
| s_wbgt_ge31 deterministic severity / band | PRIMARY            | s_wbgt_ge31; s_wbgt_band_31_33                                              | Severity band is deterministic WBGT_A context, not a probability or risk score. |
| p_ge31_optional                           | OPTIONAL_COMPANION | p_ge31_optional; p_ge31_model_id_optional; p_ge31_threshold_policy_optional | Station-held-out retrospective diagnostic only.                                 |
| p_ge33_optional                           | EXPLORATORY_ONLY   | p_ge33_optional                                                             | ge33 event support is below promotion threshold.                                |
| expected_exceedance_ge31_optional         | OPTIONAL_COMPANION | expected_exceedance_ge31_optional                                           | Magnitude diagnostic above 31 C; not a corrected WBGT forecast.                 |
| prediction_interval_low/high_optional     | OPTIONAL_COMPANION | prediction_interval_low_optional; prediction_interval_high_optional         | Retrospective conformal interval diagnostic; near-ge33 coverage remains weak.   |

## 4. Threshold Policy Register

| policy_id   | policy_role                      | threshold | recall | precision | miss_rate | not_allowed_use                                                           |
| ----------- | -------------------------------- | --------- | ------ | --------- | --------- | ------------------------------------------------------------------------- |
| fixed_31    | baseline_reference               | 31.000    | 0.588  | 0.682     | 0.412     | Official public warning threshold or replacement for optional companions. |
| best_F1     | retrospective_operating_point    | 0.446     | 0.765  | 0.678     | 0.235     | Official public warning threshold or prospective deployment gate.         |
| recall90    | screening_high_tail_sensitive    | 0.212     | 0.946  | 0.545     | 0.054     | Public alert threshold without false-alarm governance.                    |
| precision70 | precision_sensitive_if_supported | 0.654     | 0.363  | 0.673     | 0.637     | Claimed precision guarantee or public threshold.                          |

## 5. Station Caveats

| station_id | event_support           | recall | miss_rate | false_alarm_ratio | interpretation                                                                            |
| ---------- | ----------------------- | ------ | --------- | ----------------- | ----------------------------------------------------------------------------------------- |
| S139       | n=62.000; n_ge31=1.000  | 1.000  | 0.000     | 0.889             | Focus caveat: very low event support and high false-alarm sensitivity.                    |
| S142       | n=62.000; n_ge31=15.000 | 0.533  | 0.467     | 0.000             | Focus caveat: high-tail misses remain material; do not treat this as solved or corrected. |
| S124       | n=62.000; n_ge31=0.000  | NA     | NA        | 1.000             | No held-out ge31 events; recall is not interpretable for this station.                    |
| S125       | n=62.000; n_ge31=8.000  | 0.750  | 0.250     | 0.333             | No station correction; retain routine caveat monitoring.                                  |
| S126       | n=62.000; n_ge31=8.000  | 0.750  | 0.250     | 0.250             | No station correction; retain routine caveat monitoring.                                  |
| S127       | n=62.000; n_ge31=10.000 | 0.900  | 0.100     | 0.000             | No station correction; retain routine caveat monitoring.                                  |
| S128       | n=62.000; n_ge31=11.000 | 0.727  | 0.273     | 0.111             | No station correction; retain routine caveat monitoring.                                  |
| S129       | n=62.000; n_ge31=10.000 | 0.700  | 0.300     | 0.125             | No station correction; retain routine caveat monitoring.                                  |
| S130       | n=62.000; n_ge31=6.000  | 0.833  | 0.167     | 0.375             | No station correction; retain routine caveat monitoring.                                  |
| S132       | n=62.000; n_ge31=9.000  | 0.778  | 0.222     | 0.125             | No station correction; retain routine caveat monitoring.                                  |
| S135       | n=62.000; n_ge31=11.000 | 0.636  | 0.364     | 0.125             | No station correction; retain routine caveat monitoring.                                  |
| S137       | n=62.000; n_ge31=13.000 | 0.462  | 0.538     | 0.250             | High miss-rate caveat under best_F1 diagnostic policy.                                    |

S142/S139 remain focus caveats. All station rows remain monitoring diagnostics, not station corrections.

## 6. Level 2 Boundary

| boundary_item             | decision                               | forbidden_use                                          |
| ------------------------- | -------------------------------------- | ------------------------------------------------------ |
| level2_role               | EXPLANATORY_ONLY                       | Hourly correction layer or operational forecast model. |
| high_tail_residual_signal | WEAK_EXPLANATORY_SIGNAL_NOT_CORRECTION | Correct wbgt_a_c or create station-adjusted WBGT.      |
| score_residual            | NOT_IDENTIFIABLE                       | Claim station context fixes Level 1 score residual.    |
| station_adjusted_wbgt     | FORBIDDEN                              | station_adjusted_wbgt_c output.                        |
| local_cell_level_modifier | FORBIDDEN                              | local 100 m WBGT or System A/B coupling output.        |

## 7. System B / Coupling Boundary

No System B, SOLWEIG, Tmrt, morphology, cell_id, local WBGT, or radiative modifier feature is part of this System A hourly contract. Coupling is future-scoped only and produces no output here.

## 8. Prospective Evaluation Plan

A future formal archive snapshot must separate prospective rows from retrospective rows. LOSO remains retrospective evidence; prospective time validation is required with recall_ge31, precision_ge31, miss_rate_ge31, Brier, ECE, high-tail MAE, and station caveat refresh before any stronger companion claim.

## 9. Final Allowed / Forbidden Claims

Allowed: calibrated hourly WBGT_A temporal baseline; optional retrospective P_ge31 diagnostic companion; optional expected exceedance and interval diagnostics; station caveat monitoring.

Forbidden: validated local WBGT prediction, official warning probability, station-adjusted WBGT, local 100 m WBGT, System A/B coupling output, risk_score, hazard_score, and promoted ge33 probability.

## 10. Next Recommended Lane

Freeze and review this A-L1H.5 contract package. The next recommended action is a future prospective evaluation protocol using a frozen archive snapshot; do not create a station correction layer or System A/B coupling inside this lane.
