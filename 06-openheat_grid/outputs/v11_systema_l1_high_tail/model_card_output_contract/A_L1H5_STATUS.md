# A-L1H.5 Status

Status: A_L1H5_CONTRACT_PASS
Generated: 2026-05-27
Branch: codex/systema-l1h5-model-card-contract

## Scope

System A Level 1 model card and hourly output contract finalization only. No model training, no System B/SOLWEIG outputs, no archive collector changes, no station-adjusted WBGT, no local 100 m WBGT, no risk_score, and no hazard_score.

## Commands Run

- `python scripts/v11_l1h5_run_model_card_output_contract.py --config configs/v11/systema_l1h5_model_card_output_contract.yaml`

## Key Results

- Primary output decision: `wbgt_a_c` is PRIMARY.
- P_ge31 decision: OPTIONAL_COMPANION, not official warning probability.
- P_ge33 decision: EXPLORATORY_ONLY / LOW_SUPPORT.
- Expected exceedance decision: OPTIONAL_COMPANION.
- Interval decision: OPTIONAL_COMPANION.
- Level 2 boundary decision: EXPLANATORY_ONLY; no station correction layer.
- Prospective next action: future frozen formal archive snapshot with prospective rows separated from retrospective rows.

## Files Created / Modified

- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_evidence_inventory.csv`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_companion_decision_matrix.csv`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_output_schema.csv`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_threshold_policy_register.csv`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_station_caveat_register.csv`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_level2_boundary_register.csv`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_prospective_evaluation_plan.md`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_systema_model_card.md`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_hourly_output_contract_v1.md`
- `outputs/v11_systema_l1_high_tail/model_card_output_contract/a_l1h5_report.md`
- `docs/v11/OpenHeat_SystemA_L1H5_model_card_output_contract_CN.md`

## Missing Required Sources

- none

## Caveats

- Current evidence is retrospective station-held-out evidence.
- Threshold policies are diagnostic operating points, not public warning thresholds.
- S142/S139 remain station caveats, not station correction rules.
- ge33 probability remains exploratory until event support is sufficient.

## Safe To Commit

Controlled config, scripts, docs, and compact CSV/Markdown outputs from this lane after review.

## Not Safe To Commit

Raw archives, rasters, SOLWEIG/System B outputs, tif/tiff files, svfs.zip, patch zip packages, raw API dumps, or large forecast/live CSVs.
