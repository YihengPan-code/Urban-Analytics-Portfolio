# System A Hourly Output Contract v1.0

Generated: 2026-05-27
Decision status: `A_L1H5_CONTRACT_PASS`

## Contract Identity

System A Level 1 produces hourly WBGT_A rows. The primary field is `wbgt_a_c`. Optional companions remain diagnostics unless a future frozen prospective evaluation promotes them.

## Required Columns

| column_name                     | type             | description                                                             | forbidden_use                             |
| ------------------------------- | ---------------- | ----------------------------------------------------------------------- | ----------------------------------------- |
| timestamp_sgt                   | datetime_iso8601 | SGT timestamp for the hourly row.                                       | missing or ambiguous timezone             |
| timestamp_utc                   | datetime_iso8601 | UTC timestamp matching timestamp_sgt.                                   | timezone-free time key                    |
| wbgt_a_c                        | float_celsius    | Primary deterministic System A WBGT_A value.                            | local 100 m WBGT or official warning      |
| wbgt_a_model_id                 | string           | Identifier for the deterministic WBGT_A model.                          | hidden model substitution                 |
| wbgt_a_version                  | string           | Version string for the System A Level 1 contract/model artifact.        | unversioned production use                |
| s_wbgt_ge31                     | float_or_integer | Deterministic severity above the 31 C reference, derived from wbgt_a_c. | probability or risk score                 |
| s_wbgt_band_31_33               | categorical      | Band below_31, ge31_lt33, or ge33_plus derived from wbgt_a_c.           | public warning class                      |
| source_forcing                  | string           | Forcing/source family used to create the row.                           | undocumented live/archive mixing          |
| is_retrospective_or_prospective | categorical      | Whether the row is retrospective or prospective.                        | mixing retrospective and prospective rows |
| quality_flag                    | string           | Compact quality/provenance flag.                                        | silent quality failures                   |

## Optional Companion Columns

| column_name                       | type             | description                                                        | forbidden_use                              |
| --------------------------------- | ---------------- | ------------------------------------------------------------------ | ------------------------------------------ |
| p_ge31_optional                   | float_0_1        | Optional retrospective diagnostic P(WBGT >= 31 C).                 | official warning probability               |
| p_ge31_model_id_optional          | string           | Model id for p_ge31_optional.                                      | unversioned probability                    |
| p_ge31_threshold_policy_optional  | string           | Optional policy id used to interpret p_ge31_optional.              | official public warning threshold          |
| p_ge33_optional                   | float_0_1        | Exploratory optional P(WBGT >= 33 C).                              | promoted severe warning probability        |
| expected_exceedance_ge31_optional | float_celsius    | Optional expected exceedance above 31 C.                           | corrected WBGT value                       |
| prediction_interval_low_optional  | float_celsius    | Optional lower interval bound for wbgt_a_c diagnostic uncertainty. | guaranteed operational interval            |
| prediction_interval_high_optional | float_celsius    | Optional upper interval bound for wbgt_a_c diagnostic uncertainty. | guaranteed operational interval            |
| lead_time_hours_optional          | integer_or_float | Optional lead time for prospective rows when available.            | claim of forecast skill without validation |

## Forbidden Columns

| column_name             | description                                                    | forbidden_use                           |
| ----------------------- | -------------------------------------------------------------- | --------------------------------------- |
| cell_id                 | Cell-level identifier is forbidden in System A Level 1 output. | local 100 m WBGT or System A/B coupling |
| local_wbgt_c            | Local cell WBGT is forbidden.                                  | validated local WBGT prediction         |
| delta_wbgt_cell         | Cell-level WBGT delta is forbidden.                            | SOLWEIG/Tmrt-as-WBGT conversion         |
| station_adjusted_wbgt_c | Station-adjusted WBGT is forbidden.                            | station correction layer                |
| risk_score              | Risk score is forbidden.                                       | completed risk model                    |
| hazard_score            | Hazard score is forbidden.                                     | completed hazard map                    |

## Threshold Policy

| policy_id   | policy_role                      | threshold | recall | precision | miss_rate | caveats                                                                                                      |
| ----------- | -------------------------------- | --------- | ------ | --------- | --------- | ------------------------------------------------------------------------------------------------------------ |
| fixed_31    | baseline_reference               | 31.000    | 0.588  | 0.682     | 0.412     | Baseline only; A-L1H.4 showed lower recall and higher miss rate than optional P_ge31 best_F1.                |
| best_F1     | retrospective_operating_point    | 0.446     | 0.765  | 0.678     | 0.235     | Selected on training folds and evaluated held-out; requires prospective validation.                          |
| recall90    | screening_high_tail_sensitive    | 0.212     | 0.946  | 0.545     | 0.054     | Improves recall but raises false alarms; use only as diagnostic screen.                                      |
| precision70 | precision_sensitive_if_supported | 0.654     | 0.363  | 0.673     | 0.637     | A-L1H.4 isotonic row is evaluated but does not strictly reach 0.70 precision; retain as recorded diagnostic. |

No policy in this contract is an official public warning threshold.

## Row Rules

- `wbgt_a_c` is required and remains the deterministic primary output.
- `s_wbgt_ge31` and `s_wbgt_band_31_33` are deterministic summaries derived from `wbgt_a_c`.
- Optional companion columns may be absent, null, or populated only when their model id / policy metadata is present.
- Prospective rows must be distinguishable from retrospective rows.
- The contract forbids station-adjusted WBGT, local 100 m WBGT, System A/B coupling fields, risk_score, and hazard_score.
