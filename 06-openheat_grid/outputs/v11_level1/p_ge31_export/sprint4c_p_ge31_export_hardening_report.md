# Sprint 4C - P_ge31 Diagnostic Export / Reliability Hardening

## Status

PASS

## Scope

- retrospective diagnostic export only
- no model training
- no prospective claim
- no local WBGT
- no System B/v12/SOLWEIG

## Inputs

| file | exists | row_count |
| --- | --- | --- |
| docs/v11/SystemA_Level1_Interim_Model_Card_CN.md | True | NA |
| configs/v11/system_a_level1_output_contract.yaml | True | NA |
| outputs/v11_level1/model_card/system_a_level1_output_contract.md | True | NA |
| outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv | True | 10473 |
| outputs/v11_level1/probability_calibration/sprint3b_pge31_probability_calibration_report.md | True | NA |
| outputs/v11_level1/probability_calibration/probability_model_selection_summary.csv | True | 240 |
| outputs/v11_level1/probability_calibration/reliability_summary.csv | True | 120 |
| outputs/v11_level1/probability_calibration/probability_by_station.csv | True | 81 |
| outputs/v11_level1/probability_calibration/probability_by_hour.csv | True | 72 |

## Export outputs

- `outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic.csv`
- `outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic_sample.csv`
- `outputs/v11_level1/p_ge31_export/p_ge31_aoi_temporal_schema.csv`
- `outputs/v11_level1/p_ge31_export/p_ge31_export_validation_report.md`
- `outputs/v11_level1/p_ge31_export/p_ge31_reliability_hardening_report.md`
- `outputs/v11_level1/p_ge31_export/p_ge31_reliability_summary.csv`
- `outputs/v11_level1/p_ge31_export/p_ge31_contract_compliance.csv`
- `outputs/v11_level1/p_ge31_export/p_ge31_aoi_temporal_design_note.md`

## Contract compliance

- Failed checks: 0
- Overall compliance status: PASS

## Reliability summary

- Selected model/calibrator: `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration`
- Brier: 0.064
- ECE_10: 0.013
- Average precision: 0.601
- ROC_AUC: 0.931
- Station bias warning count: 4
- Low-support station count: 1

## AOI temporal boundary

station_diagnostic export is not System B cell severity.

AOI temporal aggregation is deferred.

## Caveats

- retrospective
- not operational
- no lead-time skill
- no local WBGT
- ge33 exploratory
- station bias remains

## Next action

- after 4B.1 metadata patch, run 24h prospective metadata smoke;
- later choose AOI temporal aggregation method;
- do not integrate with System B until AOI temporal contract is selected.
