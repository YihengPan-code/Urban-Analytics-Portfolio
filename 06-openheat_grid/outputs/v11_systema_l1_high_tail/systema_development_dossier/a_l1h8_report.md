# System A A-L1H.8 Development Dossier / Frozen Handoff

Generated: 2026-05-27
Decision status: `A_L1H8_DOSSIER_PASS`
Branch: `codex/systema-development-dossier`

## 1. Current System A State

System A is frozen/waiting. A-L1H.5 froze the Level 1 hourly output contract with `wbgt_a_c` as the deterministic primary output. A-L1H.6 built the prospective evaluation harness and is waiting for a real formal snapshot. A-L1H.7 built the formal snapshot freezer and is waiting for real formal input. A-L2.1c remains an explanatory sidecar only.

## 2. Evidence Chain

| lane_id  | artifact_path                                                                                    | exists | status                                 | key_result                                                                                   |
| -------- | ------------------------------------------------------------------------------------------------ | ------ | -------------------------------------- | -------------------------------------------------------------------------------------------- |
| A-L1H.4  | docs/v11/OpenHeat_SystemA_L1H4_prob_exceedance_suite_CN.md                                       | yes    | A_L1H4_COMPANION_PROMISING             | P_ge31 companion promising; P_ge33 low support; no station correction.                       |
| A-L1H.4  | outputs/v11_systema_l1_high_tail/prob_exceedance_suite/A_L1H4_STATUS.md                          | yes    | A_L1H4_COMPANION_PROMISING             | A_L1H4_COMPANION_PROMISING; n=1674, ge31=204, ge33=15; best_F1 P_ge31 recall 0.765.          |
| A-L1H.4  | outputs/v11_systema_l1_high_tail/prob_exceedance_suite/l1h4_report.md                            | yes    | A_L1H4_COMPANION_PROMISING             | Probability, expected exceedance, and interval diagnostics are available as companions.      |
| A-L1H.5  | docs/v11/OpenHeat_SystemA_L1H5_model_card_output_contract_CN.md                                  | yes    | A_L1H5_CONTRACT_PASS                   | System A Level 1 output contract frozen.                                                     |
| A-L1H.5  | outputs/v11_systema_l1_high_tail/model_card_output_contract/A_L1H5_STATUS.md                     | yes    | A_L1H5_CONTRACT_PASS                   | A_L1H5_CONTRACT_PASS; primary output wbgt_a_c; Level 2 explanatory only.                     |
| A-L1H.5  | outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_systema_model_card.md         | yes    | A_L1H5_CONTRACT_PASS                   | Model card defines intended use, not-intended use, validation evidence, and failure modes.   |
| A-L1H.5  | outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_hourly_output_contract_v1.md  | yes    | A_L1H5_CONTRACT_PASS                   | Required, optional, and forbidden hourly columns frozen.                                     |
| A-L1H.6  | docs/v11/OpenHeat_SystemA_L1H6_prospective_eval_harness_CN.md                                    | yes    | A_L1H6_WAITING_FOR_FORMAL_SNAPSHOT     | Prospective evaluation harness documented.                                                   |
| A-L1H.6  | outputs/v11_systema_l1_high_tail/prospective_eval_harness/A_L1H6_STATUS.md                       | yes    | A_L1H6_WAITING_FOR_FORMAL_SNAPSHOT     | A_L1H6_WAITING_FOR_FORMAL_SNAPSHOT; snapshot found false.                                    |
| A-L1H.6  | outputs/v11_systema_l1_high_tail/prospective_eval_harness/a_l1h6_report.md                       | yes    | A_L1H6_WAITING_FOR_FORMAL_SNAPSHOT     | Required future schema and promotion gates are prepared.                                     |
| A-L1H.7  | docs/v11/OpenHeat_SystemA_L1H7_formal_snapshot_freezer_CN.md                                     | yes    | A_L1H7_WAITING_FOR_FORMAL_INPUT        | Formal snapshot freezer documented.                                                          |
| A-L1H.7  | outputs/v11_systema_l1_high_tail/formal_snapshot_freezer/A_L1H7_STATUS.md                        | yes    | A_L1H7_WAITING_FOR_FORMAL_INPUT        | A_L1H7_WAITING_FOR_FORMAL_INPUT; no plausible formal candidate found.                        |
| A-L1H.7  | outputs/v11_systema_l1_high_tail/formal_snapshot_freezer/a_l1h7_report.md                        | yes    | A_L1H7_WAITING_FOR_FORMAL_INPUT        | Candidate tables scanned; all current candidates are not formal snapshot schema.             |
| A-L2.1c  | docs/v11/OpenHeat_SystemA_L2_scoped_residual_preflight_CN.md                                     | yes    | A_L2_SCOPED_SIGNAL_PROMISING           | Scoped residual preflight documented.                                                        |
| A-L2.1c  | outputs/v11_systema_l2_residual/scoped_residual_preflight/A_L2_1C_STATUS.md                      | yes    | A_L2_SCOPED_SIGNAL_PROMISING           | Weak high-tail station-context signal; score residual not identifiable.                      |
| A-L2.1c  | outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_residual_preflight_report.md | yes    | A_L2_SCOPED_SIGNAL_PROMISING           | High-tail residual has weak signal; score residual remains null under n=27 constraints.      |
| A-L1H.0  | outputs/v11_systema_l1_high_tail/residual_decomposition/high_tail_bias_report.md                 | yes    | not_declared                           | Residual decomposition and high-tail miss inventory established the System A high-tail lane. |
| A-L1H.0b | outputs/v11_systema_l1_high_tail/weather_regime_merge/A_L1H_0B_STATUS.md                         | yes    | PASS                                   | Weather-regime merge supported high-tail diagnostics.                                        |
| A-L1H.0c | outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/A_L1H_0C_STATUS.md             | yes    | PASS_FULL_PERIOD                       | Full-period weather-regime merge extended diagnostic context.                                |
| A-L1H.1  | outputs/v11_systema_l1_high_tail/formula_proxy_audit/A_L1H_1_STATUS.md                           | yes    | PASS                                   | Formula/proxy audit was a companion audit, not retroactive recalibration.                    |
| A-L1H.2  | outputs/v11_systema_l1_high_tail/probability_threshold_calibration/A_L1H_2_STATUS.md             | yes    | PASS                                   | Probability/threshold calibration preceded L1H4 companion package.                           |
| A-L1H.2b | outputs/v11_systema_l1_high_tail/level1_integration/A_L1H_2B_STATUS.md                           | yes    | PASS                                   | Level 1 integration consolidated high-tail evidence and boundaries.                          |
| A-L1H.3  | docs/v11/OpenHeat_SystemA_L1H3_high_tail_challenger_CN.md                                        | yes    | not_declared                           | High-tail benchmark informed companion decisions.                                            |
| A-L1H.3  | outputs/v11_systema_l1_high_tail/high_tail_challenger/A_L1H_3_STATUS.md                          | yes    | PASS                                   | High-tail challenger benchmark completed before L1H4.                                        |
| A-L2.0   | outputs/v11_systema_l2_residual/identifiability_preflight/A_L2_0_STATUS.md                       | yes    | PASS                                   | Identifiability preflight motivated scoped station-context checks.                           |
| A-L2.1a  | outputs/v11_systema_l2_residual/station_buffer_features_s1/A_L2_1A_S1_STATUS.md                  | yes    | PASS_FEATURE_TABLE                     | Station feature source and buffer build created explanatory covariates.                      |
| A-L2.1b  | outputs/v11_systema_l2_residual/station_feature_qa/A_L2_1B_STATUS.md                             | yes    | PASS_FEATURE_QA_READY_FOR_SCOPED_MODEL | Station feature QA narrowed context feature interpretation.                                  |

## 3. Timeline

| sequence | stage                                             | lane      | decision                                                                                                |
| -------- | ------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------- |
| 1        | L1 residual decomposition / high-tail diagnostics | A-L1H.0   | High-tail residual and ge31 miss behavior justified a focused Level 1 diagnostic lane.                  |
| 2        | formula/proxy audit                               | A-L1H.1   | Formula/proxy work stayed as companion audit, not retroactive recalibration.                            |
| 3        | probability / threshold calibration               | A-L1H.2   | Probability threshold behavior was useful as diagnostic evidence.                                       |
| 4        | high-tail benchmark                               | A-L1H.3   | High-tail challenger benchmark informed but did not replace WBGT_A.                                     |
| 5        | Level 2 identifiability                           | A-L2.0    | Station-context residual explanation warranted scoped preflight only.                                   |
| 6        | station feature QA                                | A-L2.1a/b | Station-local features are explanatory covariates with QA caveats.                                      |
| 7        | scoped residual preflight                         | A-L2.1c   | Weak high-tail station-context signal; score residual not identifiable.                                 |
| 8        | L1H4 probability companion                        | A-L1H.4   | P_ge31 promising companion; P_ge33 exploratory; expected exceedance and intervals optional diagnostics. |
| 9        | L1H5 contract                                     | A-L1H.5   | Hourly output contract frozen with wbgt_a_c as primary.                                                 |
| 10       | L1H6 prospective harness                          | A-L1H.6   | Harness ready but waiting for formal snapshot.                                                          |
| 11       | L1H7 snapshot freezer                             | A-L1H.7   | Freezer waits for real formal input.                                                                    |
| 12       | current state                                     | A-L1H.8   | System A frozen/waiting; dossier and handoff package complete.                                          |

## 4. Output Contract

| column_name                       | column_group       | decision            | allowed_use                                                                          | forbidden_use                                                                |
| --------------------------------- | ------------------ | ------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| timestamp_sgt                     | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| timestamp_utc                     | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| wbgt_a_c                          | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| wbgt_a_model_id                   | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| wbgt_a_version                    | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| s_wbgt_ge31                       | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| s_wbgt_band_31_33                 | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| source_forcing                    | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| is_retrospective_or_prospective   | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| quality_flag                      | required           | REQUIRED            | Frozen A-L1H.5 System A Level 1 hourly output contract.                              | Public warning, risk score, hazard score, or local 100 m WBGT claim.         |
| p_ge31_optional                   | optional_companion | OPTIONAL_DIAGNOSTIC | Internal retrospective/prospective diagnostic when metadata and gates are satisfied. | Official warning probability.                                                |
| p_ge33_optional                   | optional_companion | OPTIONAL_DIAGNOSTIC | Internal retrospective/prospective diagnostic when metadata and gates are satisfied. | Promoted severe warning probability under low event support.                 |
| expected_exceedance_ge31_optional | optional_companion | OPTIONAL_DIAGNOSTIC | Internal retrospective/prospective diagnostic when metadata and gates are satisfied. | Corrected WBGT forecast.                                                     |
| prediction_interval_low_optional  | optional_companion | OPTIONAL_DIAGNOSTIC | Internal retrospective/prospective diagnostic when metadata and gates are satisfied. | Promoted operational claim without prospective validation.                   |
| prediction_interval_high_optional | optional_companion | OPTIONAL_DIAGNOSTIC | Internal retrospective/prospective diagnostic when metadata and gates are satisfied. | Promoted operational claim without prospective validation.                   |
| station_adjusted_wbgt_c           | forbidden          | FORBIDDEN           | None in System A Level 1 contract.                                                   | Must not appear in System A L1H8 outputs or future formal snapshot contract. |
| local_wbgt_c                      | forbidden          | FORBIDDEN           | None in System A Level 1 contract.                                                   | Must not appear in System A L1H8 outputs or future formal snapshot contract. |
| delta_wbgt_cell                   | forbidden          | FORBIDDEN           | None in System A Level 1 contract.                                                   | Must not appear in System A L1H8 outputs or future formal snapshot contract. |
| risk_score                        | forbidden          | FORBIDDEN           | None in System A Level 1 contract.                                                   | Must not appear in System A L1H8 outputs or future formal snapshot contract. |
| hazard_score                      | forbidden          | FORBIDDEN           | None in System A Level 1 contract.                                                   | Must not appear in System A L1H8 outputs or future formal snapshot contract. |

## 5. Model Evidence

| evidence_item              | current_decision              | evidence                                                                                                  | caveat                                                              |
| -------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| P_ge31 optional companion  | PROMISING_BUT_OPTIONAL        | LOSO retrospective n=1674; ge31=204; Brier=0.052; ECE=0.018; PR-AUC=0.610; best_F1 recall=0.765.          | Not an official warning probability and not prospectively promoted. |
| P_ge33                     | LOW_SUPPORT_EXPLORATORY       | A-L1H.4 reports only 15 ge33 events.                                                                      | Below promotion support threshold; station support uncertain.       |
| Expected exceedance ge31   | OPTIONAL_DIAGNOSTIC           | A-L1H.4 deterministic score-gap expected exceedance MAE=0.100 C; positive-event MAE=0.779 C.              | Magnitude diagnostic only; not corrected WBGT.                      |
| Prediction intervals       | OPTIONAL_DIAGNOSTIC           | A-L1H.4 conformal 90% empirical coverage=0.898; mean width=2.869 C.                                       | Retrospective coverage only; near-ge33 behavior weak.               |
| S142 caveat                | MONITORING_CAVEAT             | S142 ge31 support=15; recall=0.533; miss_rate=0.467 under key companion diagnostics.                      | Station diagnostic, not station correction.                         |
| S139 caveat                | LOW_SUPPORT_MONITORING_CAVEAT | S139 ge31 support=1 and false-alarm-sensitive diagnostics.                                                | Too little event support for station-specific reliability claim.    |
| Level 2 high-tail residual | WEAK_EXPLANATORY_SIGNAL       | A-L2.1c high-tail residual improvement about 6.5%; permutation p_mae about 0.053; p_spearman about 0.025. | Explanatory only; n=26/27 station constraints.                      |
| Level 2 score residual     | NOT_IDENTIFIABLE              | A-L2.1c score residual improvement about 1.7%; p_mae about 0.142; p_spearman about 0.309.                 | Does not support station correction.                                |
| Station correction         | NO_STATION_CORRECTION         | A-L1H.5 Level 2 boundary and A-L2.1c preflight both reject correction output.                             | No station-adjusted WBGT.                                           |

## 6. Level 2 Boundary

| boundary_item              | current_status     | statement                                                                          | forbidden_output                              | future_option                                                |
| -------------------------- | ------------------ | ---------------------------------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------ |
| Level 2 role               | EXPLANATORY_ONLY   | Level 2 is explanatory only.                                                       | Operational correction model.                 | Protocol review after longer archive and better metadata.    |
| station-adjusted WBGT      | FORBIDDEN          | Level 2 does not produce station-adjusted WBGT.                                    | station_adjusted_wbgt_c                       | None in current v1.1 frozen handoff.                         |
| local 100 m WBGT           | FORBIDDEN          | Level 2 does not produce local 100 m WBGT.                                         | local_wbgt_c                                  | Requires a future explicitly scoped and validated lane.      |
| System B modifier          | FORBIDDEN          | Level 2 does not produce a System B modifier.                                      | System A/B coupling output or delta_wbgt_cell | Separate future coupling protocol only if explicitly opened. |
| future explanatory options | FUTURE_OPTION_ONLY | Longer archive and better station metadata/SVF/LCZ/siting data are future options. | Current correction or causal claim.           | Use as explanatory evidence after formal scope review.       |

## 7. Formal Snapshot Explanation

| register_item                 | current_status                  | detail                                                                                                                                                                 | required_action                                                                                                                   | forbidden_action                                                |
| ----------------------------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| why_formal_snapshot_is_needed | WAITING                         | A frozen formal snapshot is required before prospective evaluation or any stronger companion claim.                                                                    | Freeze reviewed compact prospective rows before any prospective pass or P_ge31 promotion review.                                  | Do not use a live-growing archive as the formal pass.           |
| required_schema               | DEFINED_BY_A_L1H5_A_L1H6_A_L1H7 | timestamp_sgt, timestamp_utc, wbgt_a_c, wbgt_a_model_id, wbgt_a_version, s_wbgt_ge31, s_wbgt_band_31_33, source_forcing, is_retrospective_or_prospective, quality_flag | Candidate must include all required columns with unambiguous timestamp semantics and model/version metadata.                      | Do not silently bridge ambiguous timestamp or contract columns. |
| minimum_row_event_support     | DEFINED                         | minimum prospective rows=200; minimum ge31 events=30; minimum ge33 events for promotion review=30                                                                      | Report support counts before interpreting metrics.                                                                                | Do not fabricate rows or events.                                |
| candidate_paths               | CONFIGURED                      | outputs/v11_archive_formal_beta/; outputs/v11_systema_l1_high_tail/prospective_snapshot/; outputs/v11_systema_l1_high_tail/formal_snapshot/; outputs/v11_beta_formal/  | Place a real compact CSV/CSV.GZ/Parquet snapshot in one configured path.                                                          | Do not scan raw archive dumps as formal proof.                  |
| A-L1H.7 current status        | A_L1H7_WAITING_FOR_FORMAL_INPUT | Current freezer dry-run found no plausible formal candidate.                                                                                                           | Rerun freezer with real candidate; use write_snapshot only after checks pass.                                                     | Do not weaken required schema or forbidden-column checks.       |
| A-L1H.6 rerun command         | READY_AFTER_SNAPSHOT            | python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml                                                | Run after frozen snapshot is written and reviewed.                                                                                | Do not claim prospective pass before running on snapshot.       |
| write_snapshot procedure      | DOCUMENTED_NOT_EXECUTED         | python scripts/v11_l1h7_run_formal_snapshot_freezer.py --config configs/v11/systema_l1h7_formal_snapshot_freezer.yaml                                                  | Set A-L1H.7 config to write_snapshot only for a real candidate that passes schema, support, numeric, and forbidden-column checks. | Do not write fake formal snapshot rows.                         |
| live-growing archive          | NOT_FORMAL_PASS                 | Formal comparisons must use a frozen snapshot, never a live-growing archive.                                                                                           | Version and review the frozen snapshot manifest.                                                                                  | Do not interpret live archive rows as final formal evidence.    |

## 8. Future Reactivation Path

Start by checking branch and status, then use A-L1H.7 to write a reviewed frozen snapshot if needed. After the snapshot manifest and validation pass, run A-L1H.6 prospective evaluation and evaluate P_ge31 gates. Do not train new models unless gates fail and the user explicitly opens a new lane.

## 9. Allowed / Forbidden Claims

| claim                                         | decision              | allowed_wording                                                       | forbidden_upgrade                           |
| --------------------------------------------- | --------------------- | --------------------------------------------------------------------- | ------------------------------------------- |
| WBGT_A deterministic temporal baseline        | ALLOWED               | WBGT_A deterministic temporal baseline.                               | Validated local WBGT prediction.            |
| P_ge31 optional diagnostic companion          | ALLOWED_WITH_BOUNDARY | P_ge31 optional diagnostic companion.                                 | Official warning probability.               |
| retrospective LOSO evidence                   | ALLOWED               | Retrospective station-held-out LOSO evidence.                         | Final prospective pass.                     |
| prospective harness ready                     | ALLOWED               | Prospective evaluation harness ready and waiting for formal snapshot. | Prospective evaluation complete.            |
| Level 2 explanatory weak signal               | ALLOWED_WITH_BOUNDARY | Level 2 shows weak high-tail explanatory signal.                      | Station correction or causal driver proof.  |
| official warning probability                  | FORBIDDEN             | None.                                                                 | Official warning probability.               |
| station-adjusted WBGT                         | FORBIDDEN             | None.                                                                 | station_adjusted_wbgt_c.                    |
| local 100m WBGT                               | FORBIDDEN             | None.                                                                 | local_wbgt_c or validated 100 m local WBGT. |
| risk/hazard score                             | FORBIDDEN             | None.                                                                 | risk_score or hazard_score.                 |
| System A/B coupling claim                     | FORBIDDEN             | None.                                                                 | System A/B coupling output.                 |
| final prospective pass before formal snapshot | FORBIDDEN             | Waiting for formal snapshot.                                          | Final prospective pass.                     |

## 10. Codex Re-entry Prompt

See `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_codex_reentry_prompt.md`.

## 11. Architecture Diagram

See `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_systema_architecture_diagram.md`.
