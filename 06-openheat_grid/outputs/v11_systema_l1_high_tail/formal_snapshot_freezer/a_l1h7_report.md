# System A A-L1H.7 Formal Snapshot Freezer

Generated: 2026-05-27
Decision status: `A_L1H7_WAITING_FOR_FORMAL_INPUT`
Branch: `codex/systema-l1h7-formal-snapshot-freezer`

## 1. Why A-L1H.7 Follows A-L1H.6

A-L1H.5 froze the System A Level 1 output contract, and A-L1H.6 built the
prospective evaluation harness that is currently waiting for a formal snapshot.
A-L1H.7 sits between them: it searches only compact formal/prospective outputs,
bridges columns only when safe, and prepares a freeze-ready package or a
WAITING/BLOCKED report without fabricating rows or metrics.

## 2. Candidate Search Results

Candidate tables scanned: `6`

Best candidate path: `none`

| path                                                                                     | file_type | bytes | row_count | likely_schema_role             | detection_status           |
| ---------------------------------------------------------------------------------------- | --------- | ----- | --------- | ------------------------------ | -------------------------- |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv                | .csv      | 3442  | 7         | inventory_or_validation_output | NOT_FORMAL_SNAPSHOT_SCHEMA |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv                 | .csv      | 1179  | 18        | inventory_or_validation_output | NOT_FORMAL_SNAPSHOT_SCHEMA |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv       | .csv      | 698   | 11        | inventory_or_validation_output | NOT_FORMAL_SNAPSHOT_SCHEMA |
| outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv | .csv      | 551   | 6         | inventory_or_validation_output | NOT_FORMAL_SNAPSHOT_SCHEMA |
| outputs/v11_level1/prospective_eval/prospective_eval_artifact_inventory.csv              | .csv      | 10318 | 65        | inventory_or_validation_output | NOT_FORMAL_SNAPSHOT_SCHEMA |
| outputs/v11_level1/prospective_eval/prospective_metadata_gap_audit.csv                   | .csv      | 18193 | 33        | inventory_or_validation_output | NOT_FORMAL_SNAPSHOT_SCHEMA |

## 3. Column Mapping Results

| candidate_path                                                            | target_column                     | required_or_optional | source_column | mapping_status | reason                         |
| ------------------------------------------------------------------------- | --------------------------------- | -------------------- | ------------- | -------------- | ------------------------------ |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | timestamp_sgt                     | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | timestamp_utc                     | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | station_id                        | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | official_wbgt_c                   | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | wbgt_a_c                          | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | wbgt_a_model_id                   | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | wbgt_a_version                    | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | is_retrospective_or_prospective   | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | quality_flag                      | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | p_ge31_optional                   | optional             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | p_ge31_model_id_optional          | optional             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | p_ge31_threshold_policy_optional  | optional             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | p_ge33_optional                   | optional             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | expected_exceedance_ge31_optional | optional             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | prediction_interval_low_optional  | optional             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | prediction_interval_high_optional | optional             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | lead_time_hours_optional          | optional             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | timestamp_sgt                     | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | timestamp_utc                     | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | station_id                        | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | official_wbgt_c                   | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | wbgt_a_c                          | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | wbgt_a_model_id                   | required             |               | MISSING        | No exact column or safe alias. |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | wbgt_a_version                    | required             |               | MISSING        | No exact column or safe alias. |

Safe aliases are accepted only when timezone or contract-source semantics are
clear. Ambiguous aliases are recorded as `AMBIGUOUS_MAPPING` and are not silently
used.

## 4. Schema And Forbidden-Column Checks

Required schema check:

| candidate_path                                                            | target_column                     | required_or_optional | source_column | mapping_status | check_status    |
| ------------------------------------------------------------------------- | --------------------------------- | -------------------- | ------------- | -------------- | --------------- |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | timestamp_sgt                     | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | timestamp_utc                     | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | station_id                        | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | official_wbgt_c                   | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | wbgt_a_c                          | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | wbgt_a_model_id                   | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | wbgt_a_version                    | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | is_retrospective_or_prospective   | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | quality_flag                      | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | p_ge31_optional                   | optional             |               | MISSING        | OPTIONAL_ABSENT |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | p_ge31_model_id_optional          | optional             |               | MISSING        | OPTIONAL_ABSENT |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | p_ge31_threshold_policy_optional  | optional             |               | MISSING        | OPTIONAL_ABSENT |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | p_ge33_optional                   | optional             |               | MISSING        | OPTIONAL_ABSENT |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | expected_exceedance_ge31_optional | optional             |               | MISSING        | OPTIONAL_ABSENT |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | prediction_interval_low_optional  | optional             |               | MISSING        | OPTIONAL_ABSENT |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | prediction_interval_high_optional | optional             |               | MISSING        | OPTIONAL_ABSENT |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv | lead_time_hours_optional          | optional             |               | MISSING        | OPTIONAL_ABSENT |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | timestamp_sgt                     | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | timestamp_utc                     | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | station_id                        | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | official_wbgt_c                   | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | wbgt_a_c                          | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | wbgt_a_model_id                   | required             |               | MISSING        | FAIL            |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv  | wbgt_a_version                    | required             |               | MISSING        | FAIL            |

Forbidden-column check:

| candidate_path                                                                           | forbidden_column        | present | check_status | reason |
| ---------------------------------------------------------------------------------------- | ----------------------- | ------- | ------------ | ------ |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv                | cell_id                 | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv                | local_wbgt_c            | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv                | delta_wbgt_cell         | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv                | station_adjusted_wbgt_c | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv                | risk_score              | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv                | hazard_score            | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv                 | cell_id                 | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv                 | local_wbgt_c            | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv                 | delta_wbgt_cell         | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv                 | station_adjusted_wbgt_c | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv                 | risk_score              | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv                 | hazard_score            | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv       | cell_id                 | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv       | local_wbgt_c            | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv       | delta_wbgt_cell         | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv       | station_adjusted_wbgt_c | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv       | risk_score              | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv       | hazard_score            | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv | cell_id                 | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv | local_wbgt_c            | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv | delta_wbgt_cell         | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv | station_adjusted_wbgt_c | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv | risk_score              | no      | PASS         | absent |
| outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv | hazard_score            | no      | PASS         | absent |

## 5. Freeze Readiness Decision

Freeze mode: `dry_run`

Written frozen table: `none`

| candidate_path                                                                     | check_id                                  | check_group | check_status             | detail                                                                                                                                                              |
| ---------------------------------------------------------------------------------- | ----------------------------------------- | ----------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | required_columns_present_or_safely_mapped | schema      | FAIL                     | missing=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; ambiguous=none |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | forbidden_columns_absent                  | safety      | PASS                     | none                                                                                                                                                                |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | minimum_prospective_rows                  | support     | FAIL                     | n_prospective_rows=0; minimum=200                                                                                                                                   |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | minimum_ge31_events                       | support     | FAIL                     | n_ge31=0; minimum=30                                                                                                                                                |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | ge33_event_support_reported               | support     | INFO                     | n_ge33=0; promotion_minimum=30                                                                                                                                      |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | official_wbgt_c_numeric                   | schema      | FAIL                     | official_wbgt_c missing                                                                                                                                             |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | wbgt_a_c_numeric                          | schema      | FAIL                     | wbgt_a_c missing                                                                                                                                                    |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | model_version_metadata_present            | metadata    | FAIL                     | wbgt_a_model_id and wbgt_a_version non-null for prospective rows                                                                                                    |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | quality_flag_present                      | metadata    | FAIL                     | quality_flag non-null for prospective rows                                                                                                                          |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | retrospective_prospective_label_present   | metadata    | FAIL                     | label_column=missing; n_prospective_rows=0                                                                                                                          |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv          | freeze_readiness_decision                 | decision    | WAITING_FOR_FORMAL_INPUT | missing_required=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag        |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | required_columns_present_or_safely_mapped | schema      | FAIL                     | missing=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; ambiguous=none |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | forbidden_columns_absent                  | safety      | PASS                     | none                                                                                                                                                                |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | minimum_prospective_rows                  | support     | FAIL                     | n_prospective_rows=0; minimum=200                                                                                                                                   |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | minimum_ge31_events                       | support     | FAIL                     | n_ge31=0; minimum=30                                                                                                                                                |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | ge33_event_support_reported               | support     | INFO                     | n_ge33=0; promotion_minimum=30                                                                                                                                      |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | official_wbgt_c_numeric                   | schema      | FAIL                     | official_wbgt_c missing                                                                                                                                             |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | wbgt_a_c_numeric                          | schema      | FAIL                     | wbgt_a_c missing                                                                                                                                                    |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | model_version_metadata_present            | metadata    | FAIL                     | wbgt_a_model_id and wbgt_a_version non-null for prospective rows                                                                                                    |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | quality_flag_present                      | metadata    | FAIL                     | quality_flag non-null for prospective rows                                                                                                                          |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | retrospective_prospective_label_present   | metadata    | FAIL                     | label_column=missing; n_prospective_rows=0                                                                                                                          |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv           | freeze_readiness_decision                 | decision    | WAITING_FOR_FORMAL_INPUT | missing_required=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag        |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv | required_columns_present_or_safely_mapped | schema      | FAIL                     | missing=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; ambiguous=none |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv | forbidden_columns_absent                  | safety      | PASS                     | none                                                                                                                                                                |

READY_TO_FREEZE requires all required columns present or safely mapped, no
forbidden columns, at least the configured prospective rows and ge31 events,
numeric `official_wbgt_c` and `wbgt_a_c`, model/version metadata, `quality_flag`,
and a retrospective/prospective label.

## 6. Dry-Run Vs Write-Snapshot Behavior

In `dry_run`, this lane does not write a formal snapshot data table. It writes
only inventories, checks, manifests, validation rows, command templates, reports,
and status files. In `write_snapshot`, it writes a compact CSV.GZ under
`outputs/v11_systema_l1_high_tail/formal_snapshot/` only if a real candidate is
freeze-ready.

## 7. Downstream A-L1H.6 Rerun Instructions

After a reviewed frozen snapshot exists, rerun:

`python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml`

A-L1H.7 does not run A-L1H.6 automatically and does not modify A-L1H.6 promotion
gates.

## 8. Claim Boundaries

- No model training.
- No archive collector changes.
- No station-adjusted WBGT.
- No local 100 m WBGT.
- No official warning probability.
- No risk_score or hazard_score.
- No System B coupling.
- No System B, SOLWEIG, or Tmrt features.
- No fake metrics or fake rows.
