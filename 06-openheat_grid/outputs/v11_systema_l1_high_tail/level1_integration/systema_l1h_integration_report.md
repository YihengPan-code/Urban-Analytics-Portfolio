# System A A-L1H.2b Level 1 High-Tail Integration Report

Generated: 2026-05-26
Status: `PASS`
Decision: `ACCEPT_DIAGNOSTIC_COMPANION_HOLD_OPERATIONAL_CLAIMS`
Branch: `codex/systema-l1h2b-level1-integration`
Missing configured source reports: `none`

## 1. What changed after A-L1H.0 to A-L1H.2

A-L1H.0 established the main failure mode: deterministic System A WBGT_A scores remain useful for retrospective temporal severity, but the high tail is compressed around the ge31 threshold and station bias is visible. A-L1H.0b added partial weather-regime evidence, then A-L1H.0c replaced that partial coverage with full-period regime diagnostics. A-L1H.1 found that raw formula/proxy candidates were weak or negative and should not replace WBGT_A. A-L1H.2 then selected a score-to-event probability companion without retraining the base WBGT models.

| evidence_id | status                               | key_result                                                                                                                                                                                             | safe_claim                                                                                           | forbidden_claim                                                                                             |
| ----------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| A-L1H.0     | PASS_DIAGNOSTIC                      | M4 fixed_31 precision 0.669, recall 0.475, F1 0.556; observed ge31 rows were compressed below score 31 and station bias was visible, especially S142.                                                  | System A has retrospective WBGT_A temporal severity evidence with high-tail compression diagnostics. | Do not claim validated local WBGT prediction, official warning probability, or prospective forecast skill.  |
| A-L1H.0b    | PASS_PARTIAL                         | Weather merge retained 2700 of 6696 rows (40.3%); regime interaction was plausible_but_partial, with very-high radiation bins concentrating many ge31 misses.                                          | Partial retrospective regime evidence suggested radiation-linked high-tail miss structure.           | Do not use A-L1H.0b alone as full-period regime proof or causal mechanism proof.                            |
| A-L1H.0c    | PASS_FULL_PERIOD                     | Recovered 6696 of 6696 rows (100.0%) across 27 stations; radiation_hot contained nearly all observed ge31 events and misses, while conditional enrichment remained mixed.                              | Full-period weather-regime residual diagnostics support internal high-tail evidence review.          | Do not claim weather regimes validate local WBGT, explain causality, or complete risk mapping.              |
| A-L1H.1     | WEAK_OR_NEGATIVE                     | Raw Stull/simple-globe formula and proxy candidates did not produce fixed_31 crossings; best raw proxies stayed below 31 C and had worse high-tail residual behavior.                                  | Formula/proxy audit did not justify replacing current WBGT_A score in Level 1.                       | Do not claim formula-v2 is implemented, validated, or retroactively recalibrates System A.                  |
| A-L1H.2     | PASS_CANDIDATE_PROBABILITY_COMPANION | Best companion is M4_inertia_ridge + isotonic_score_only under station_grouped_loso: Brier about 0.052, PR-AUC about 0.610, threshold about 0.309, precision 0.678, recall 0.765, F1 0.719, CSI 0.561. | P_ge31 is a candidate diagnostic companion for internal retrospective ge31 review.                   | Do not claim P_ge31 is an official warning probability, policy threshold, or prospective operational model. |

## 2. Current companion

`P_ge31` is defined as: Retrospective station-held-out diagnostic companion for observed WBGT >= 31 C, generated from the existing M4_inertia_ridge score with isotonic_score_only calibration.

Current companion definition: P_ge31 = M4_inertia_ridge model_score calibrated with isotonic_score_only under station_grouped_loso; selected diagnostic threshold about 0.309.

Headline metrics: Brier about 0.052, PR-AUC about 0.61, selected threshold about 0.309, precision 0.678, recall 0.765, F1 0.719, CSI 0.561.

The deterministic WBGT_A score remains the primary temporal severity diagnostic. P_ge31 is a retrospective diagnostic companion, not an official warning probability.

## 3. What is reliable

Reliable enough for internal retrospective diagnostic use as a companion to WBGT_A; not reliable enough for official warning probability or prospective forecast claims.

Reliable wording is limited to internal retrospective diagnostics: calibrated hourly WBGT_A temporal severity, station-held-out P_ge31 companion diagnostics, and evidence that ge31 capture improves relative to fixed score 31 behavior.

## 4. What remains not solved

ge31 capture is materially improved versus the fixed score 31 threshold, but high-tail compression and station/regime caveats remain; ge31 is not fully solved and ge33 remains exploratory.

S142, S139, radiation-hot periods, very-high shortwave / shortwave_3h, low-support bins, and ge33 all remain caveats. These caveats are diagnostic review items, not causal corrections.

## 5. Why A-L2 is deferred

HOLD A-L2 until Level 1 high-tail evidence is closed and station-context residual work is explicitly opened.

A-L2 would be station-context residual work. A-L1H.2b only records the current Level 1 contract and does not implement station-context correction.

## 6. Whether to try other models now

OPTIONAL separate A-L1H.3 review gate only if further high-tail improvement is requested; not implemented in A-L1H.2b.

No broad model search is recommended inside this lane. A-L1H.3 high-tail regression can be opened later as a separate review gate if the user wants further high-tail improvement.

## 7. Output contract

| output_name                        | current_role                         | allowed_use                                                                                           | forbidden_use                                                                                                      | contract_decision                |
| ---------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------- |
| WBGT_A_score or model_score        | primary temporal severity diagnostic | Background retrospective temporal severity diagnostic and anchor for companion P_ge31 interpretation. | Not local 100m WBGT, not official warning, not public alert, and not prospective forecast skill.                   | KEEP_PRIMARY_RETROSPECTIVE_SCORE |
| P_ge31                             | retrospective diagnostic companion   | Internal retrospective ge31 high-tail review and companion flagging with threshold about 0.309.       | Not official warning probability, not policy probability, not public alert probability, and not prospective skill. | ACCEPT_DIAGNOSTIC_COMPANION      |
| Optional threshold operating point | diagnostic operating point           | Optional internal retrospective diagnostic flag, with precision about 0.678 and recall about 0.765.   | Not final policy threshold, not operational warning trigger, and not a public-facing alert threshold.              | ACCEPT_OPTIONAL_DIAGNOSTIC_ONLY  |

## 8. Claim boundaries

| claim                                             | status                 | allowed_wording                                                   | forbidden_wording                                                 | next_gate                                                                   |
| ------------------------------------------------- | ---------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------- |
| retrospective diagnostic WBGT_A temporal severity | ALLOWED                | calibrated hourly WBGT_A temporal severity diagnostic             | validated local WBGT prediction                                   | Maintain in Level 1 contract; no new training in A-L1H.2b.                  |
| P_ge31 diagnostic companion                       | ALLOWED_WITH_QUALIFIER | retrospective diagnostic companion for observed WBGT >= 31 C      | official warning probability                                      | Use as current companion; require prospective evaluation before operations. |
| official warning probability                      | FORBIDDEN              | none                                                              | P_ge31 is an official warning probability                         | Prospective metadata and lead-time evaluation.                              |
| prospective forecast skill                        | FORBIDDEN_NOW          | not yet evaluated prospectively                                   | real-time heat risk forecast or proven prospective skill          | Prospective forecast evaluation with explicit lead times.                   |
| local 100m WBGT                                   | FORBIDDEN              | not a local 100m WBGT product                                     | validated 100m-cell local WBGT prediction                         | Separate validated local WBGT study would be required.                      |
| station-context causal correction                 | DEFERRED               | station diagnostics remain to review                              | station context causally corrects WBGT                            | A-L2 only after explicit review gate.                                       |
| System A/B coupled risk                           | FORBIDDEN_NOW          | future risk overlay after exposure and vulnerability are explicit | hazard map equals risk map or System A/B coupled risk is complete | Separate System A/B coupling and risk design after current v1.1 gates.      |
| ge33 event probability                            | EXPLORATORY_ONLY       | ge33 remains exploratory                                          | validated ge33 event probability                                  | More event support and separate review.                                     |
| public-facing alert                               | FORBIDDEN              | none                                                              | public alert or warning trigger                                   | Operational governance plus prospective validation.                         |

## 9. Decision matrix

| question                                                              | answer                         | decision                                                               | caveat                                                             |
| --------------------------------------------------------------------- | ------------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Is Level 1 reliable enough for internal retrospective diagnostic use? | YES_WITH_BOUNDARIES            | Accept System A Level 1 current contract.                              | Use only as internal retrospective diagnostic, not public warning. |
| Is ge31 high-tail capture materially improved?                        | True                           | Accept P_ge31 as diagnostic companion.                                 | Improvement is station-held-out retrospective OOF only.            |
| Is ge31 fully solved?                                                 | False                          | Do not promote to official warning probability.                        | Misses and calibration gaps still exist.                           |
| Should A-L2 start now?                                                | False                          | HOLD_A_L2                                                              | A-L2 may be reconsidered after explicit gate review.               |
| Should A-L1H.3 start now?                                             | OPTIONAL_ONLY_BY_SEPARATE_GATE | Do not start in A-L1H.2b.                                              | Only if user wants further high-tail improvement.                  |
| Should prospective evaluation be required before operational claims?  | True                           | Require prospective metadata / lead-time evaluation before operations. | No prospective lead-time skill is established.                     |

## 10. Station and regime caveats

| topic                              | interpretation                                                                      | safe_claim                                                 | forbidden_claim                                                    |
| ---------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ |
| S142                               | S142 remains a high-tail miss / underprediction caveat.                             | S142 needs station-level diagnostic review.                | S142 is causally corrected or fully solved.                        |
| S139                               | S139 is low-support and unstable for station-specific conclusions.                  | S139 evidence is a caveat, not a basis for broad claims.   | S139 proves calibration reliability or station causality.          |
| radiation-hot regime               | Radiation-hot regimes are important diagnostic contexts.                            | Radiation-hot periods concentrate ge31 review burden.      | Radiation-hot is a proven causal mechanism or operational trigger. |
| very high shortwave / shortwave_3h | Shortwave bins help explain where review is needed, not why events happen causally. | Very-high shortwave regimes are retrospective diagnostics. | Shortwave feature proves real-world causal heat-risk drivers.      |
| low-support station/event caveats  | Some metrics are unstable outside common ge31-support regimes.                      | Low-support bins require caution.                          | All stations and regimes have uniform reliability.                 |
| ge33 exploratory caveat            | ge33 is insufficient for current promoted claims.                                   | ge33 remains exploratory.                                  | Validated ge33 event probability.                                  |

## 11. Recommended next gates

| recommendation                                                                                      | decision | rationale                                                                                                                                 |
| --------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| ACCEPT A-L1H.2 P_ge31 as diagnostic companion.                                                      | ACCEPT   | Best candidate M4 + isotonic_score_only has usable station-held-out retrospective reliability and improved ge31 operating-point behavior. |
| HOLD A-L2.                                                                                          | HOLD     | Station context remains diagnostic; A-L2 was explicitly out of scope and should not start from this integration task.                     |
| OPTIONAL A-L1H.3 high-tail regression review gate only if further high-tail improvement is desired. | OPTIONAL | P_ge31 companion materially improves ge31 capture but does not fully solve high tail.                                                     |
| REQUIRE prospective metadata / lead-time evaluation before operational forecast claims.             | REQUIRE  | Current evidence is retrospective OOF; no prospective forecast skill has been evaluated.                                                  |
| Use this integration report as the System A Level 1 current contract.                               | ACCEPT   | It defines WBGT_A score as primary and P_ge31 as diagnostic companion with explicit boundaries.                                           |
| Do not try other models now unless a separate A-L1H.3 review gate is opened.                        | HOLD     | This lane is integration / model-card / output-contract work, and A-L1H.2 already selected a diagnostic companion.                        |

## Claim boundary reminder

This package does not claim validated local 100m WBGT, official warning probability, prospective forecast skill, public-facing alerts, completed risk maps, or System A/B coupled risk.
