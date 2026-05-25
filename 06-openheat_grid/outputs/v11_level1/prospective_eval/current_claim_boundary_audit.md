# System A Level 1 Sprint 4B Claim Boundary Audit

Status: retrospective metadata audit only. No model training, no collector modification, no archive modification, and no System B or local-WBGT work was performed.

## Allowed Today

- Retrospective WBGT-like background score analysis.
- Retrospective P_ge31 diagnostic companion.
- Station-network / AOI background temporal severity diagnostics.
- System B temporal severity input, with output contract caveats.

## Forbidden Today

- Prospective forecast skill claim.
- Lead-time-specific forecast accuracy.
- Operational warning probability.
- Official warning system.
- 100m local WBGT.
- Risk forecast.
- System B cell severity from station rows.

## Why The Forbidden Claims Are Not Supported

Prospective forecast skill is not supported because current Level 1 evidence aligns weather forcing and official WBGT by valid time after the fact. That is Mode A retrospective valid-time calibration, not a record of what was knowable at a past issue time.

Lead-time-specific forecast accuracy is not supported because current rows do not store a verified provider `model_run_time_utc`, a normalized `forecast_retrieved_at_utc`, or a trustworthy `forecast_lead_time_hours`. Existing `issue_age_hours` is useful audit metadata, but it must not be relabeled as validated lead time.

Operational warning probability is not supported because `p_ge31_diagnostic` is calibrated retrospectively against official WBGT >=31 deg C. It has no prospective validation, no official threshold policy, and no warning issuance protocol.

An official warning system is not supported because the project has not implemented governance, reliability, public-health validation, uptime guarantees, or official observation publication-delay handling.

100m local WBGT is not supported because System A Level 1 is station-network / AOI temporal background context. It does not validate local cell WBGT and must not export `local_wbgt_c`, `wbgt_cell_c`, or equivalent fields.

Risk forecast is not supported because exposure, vulnerability, and operational forecast skill are not explicit, prospectively validated components in this sprint.

System B cell severity from station rows is not supported because station diagnostic rows are not cell-level severity. System B may consume only documented AOI temporal severity or explicitly aggregated temporal inputs with contract caveats.

## Mode Separation

Mode A - retrospective_valid_time_calibration: supported today for retrospective analysis only.

Mode B - hindcast_forecast_reconstruction: possible future route if archived forecast products preserve issue/model run metadata for past issue times.

Mode C - live_prospective_collection: future route requiring collector metadata before any prospective forecast evaluation claim.
