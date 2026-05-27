# System A A-L1H.6 Prospective Evaluation Harness

Generated: 2026-05-27
Decision status: `A_L1H6_WAITING_FOR_FORMAL_SNAPSHOT`
Branch: `codex/systema-l1h6-prospective-eval-harness`

## 1. Why A-L1H.6 Follows A-L1H.5

A-L1H.5 froze the System A Level 1 model card and hourly output contract. A-L1H.6 prepares the prospective evaluation harness requested by that contract: it waits for a future frozen formal snapshot, separates prospective rows from retrospective rows, and evaluates only after real prospective rows exist.

## 2. Frozen Contract Dependency

The harness depends on the frozen A-L1H.5 status, hourly output contract, output schema, threshold-policy register, and station-caveat register. It does not modify A-L1H.5 decisions. `wbgt_a_c` remains primary; `p_ge31_optional` remains an optional diagnostic companion; `p_ge33_optional` remains exploratory.

## 3. Snapshot Detection Results

Detection reason: `WAITING_FOR_FORMAL_SNAPSHOT`

Snapshot found: `no`

Candidate path: `none`

| path                                                                                     | candidate_table | detection_status                  | n_prospective_rows | n_ge31 | n_ge33 | reason                                                                                                                                                                               |
| ---------------------------------------------------------------------------------------- | --------------- | --------------------------------- | ------------------ | ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| outputs/v11_archive_formal_beta                                                          | directory       | MISSING_CONFIGURED_CANDIDATE_PATH |                    |        |        | Configured formal snapshot path does not exist yet.                                                                                                                                  |
| outputs/v11_systema_l1_high_tail/prospective_snapshot                                    | directory       | MISSING_CONFIGURED_CANDIDATE_PATH |                    |        |        | Configured formal snapshot path does not exist yet.                                                                                                                                  |
| outputs/v11_systema_l1_high_tail/formal_snapshot                                         | directory       | MISSING_CONFIGURED_CANDIDATE_PATH |                    |        |        | Configured formal snapshot path does not exist yet.                                                                                                                                  |
| outputs/v11_beta_formal                                                                  | directory       | MISSING_CONFIGURED_CANDIDATE_PATH |                    |        |        | Configured formal snapshot path does not exist yet.                                                                                                                                  |
| outputs/v11_level1/prospective_eval/current_capability_classification.csv                | inventory_only  | SCHEMA_INVALID                    | 0                  | 0      | 0      | missing_required=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; forbidden_present=none |
| outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv                 | inventory_only  | SCHEMA_INVALID                    | 0                  | 0      | 0      | missing_required=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; forbidden_present=none |
| outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv       | inventory_only  | SCHEMA_INVALID                    | 0                  | 0      | 0      | missing_required=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; forbidden_present=none |
| outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv | inventory_only  | SCHEMA_INVALID                    | 0                  | 0      | 0      | missing_required=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; forbidden_present=none |
| outputs/v11_level1/prospective_eval/prospective_eval_artifact_inventory.csv              | inventory_only  | SCHEMA_INVALID                    | 0                  | 0      | 0      | missing_required=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; forbidden_present=none |
| outputs/v11_level1/prospective_eval/prospective_metadata_gap_audit.csv                   | inventory_only  | SCHEMA_INVALID                    | 0                  | 0      | 0      | missing_required=timestamp_sgt;timestamp_utc;station_id;official_wbgt_c;wbgt_a_c;wbgt_a_model_id;wbgt_a_version;is_retrospective_or_prospective;quality_flag; forbidden_present=none |

## 4. Required Future Input Schema

The required future table must include `timestamp_sgt`, `timestamp_utc`, `station_id`, `official_wbgt_c`, `wbgt_a_c`, `wbgt_a_model_id`, `wbgt_a_version`, `is_retrospective_or_prospective`, and `quality_flag`. Optional companions may include `p_ge31_optional`, `p_ge31_model_id_optional`, `p_ge31_threshold_policy_optional`, `p_ge33_optional`, expected exceedance, interval, and lead-time fields.

Forbidden columns remain forbidden: `cell_id`, `local_wbgt_c`, `delta_wbgt_cell`, `station_adjusted_wbgt_c`, `risk_score`, and `hazard_score`.

## 5. Evaluation Metrics

_No prospective metrics were computed because no valid formal snapshot exists._

## 6. Promotion Gate Logic

| gate_id         | status                          | support_status              | evidence_summary                                | next_action                                                                     |
| --------------- | ------------------------------- | --------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------- |
| p_ge31_optional | P_GE31_REMAINS_OPTIONAL_WAITING | WAITING_FOR_FORMAL_SNAPSHOT | No valid formal prospective snapshot evaluated. | Freeze a formal prospective snapshot with required schema and prospective rows. |
| p_ge33_optional | P_GE33_REMAINS_EXPLORATORY      | WAITING_FOR_FORMAL_SNAPSHOT | No valid formal prospective snapshot evaluated. | Keep p_ge33 exploratory.                                                        |

## 7. Station Caveat Refresh

| station_id | n_rows | n_ge31 | n_ge33 | caveat_status               | headline                                                                  |
| ---------- | ------ | ------ | ------ | --------------------------- | ------------------------------------------------------------------------- |
| ALL        |        |        |        | WAITING_FOR_FORMAL_SNAPSHOT | No station metrics computed because no valid prospective snapshot exists. |
| S142       |        |        |        | WAITING_FOR_FORMAL_SNAPSHOT | No station metrics computed because no valid prospective snapshot exists. |
| S139       |        |        |        | WAITING_FOR_FORMAL_SNAPSHOT | No station metrics computed because no valid prospective snapshot exists. |

Station rows are monitoring diagnostics only; they are not station corrections.

## 8. Claim Boundaries

- No new model training.
- No station-adjusted WBGT.
- No local 100 m WBGT.
- No official warning probability.
- No risk_score or hazard_score.
- No System A/B coupling.
- No System B, SOLWEIG, or Tmrt features.

## 9. Next Recommended Action

Freeze a formal prospective System A snapshot with the required schema, place it under a configured candidate path, and rerun:

`python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml`
