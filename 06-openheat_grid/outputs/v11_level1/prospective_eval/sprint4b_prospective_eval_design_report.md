# System A Level 1 Sprint 4B - Prospective Forecast Evaluation Design

## Status

PARTIAL

The sprint passes as a design and metadata audit. Current artifacts support retrospective valid-time calibration, but they do not yet support true live prospective forecast evaluation.

## Scope

- design/audit only
- no model training
- no collector modification
- no archive modification
- no System B
- no local WBGT

## Inputs Inspected

The audit inspected System A model-card and output-contract artifacts, v11 archive/GHA operation notes, v11 calibration pair tables and snapshots, compact GHA live chunks, GHA run manifests and health summaries, v11 archive collector scripts, v11 GHA wrapper scripts, archive configs, and workflow presence. The full artifact inventory is in `outputs/v11_level1/prospective_eval/prospective_eval_artifact_inventory.csv`.

## Key Finding

Can current data support true prospective evaluation now? No. It preserves valid-time aligned station/weather pairs and some collector timing, but it does not preserve enough verified issue/model/retrieval metadata to make a true prospective forecast-skill claim.

Can it support hindcast reconstruction later? Partially. Open-Meteo Historical Forecast / Previous Runs / Single Runs could be used in a separate future route if the ingestion records provider product, issue/model run time, valid time, endpoint, and a deterministic issue-valid pair id.

What is missing? The blocking gaps are `model_run_time_utc`, unambiguous `forecast_issue_time_utc`, `forecast_requested_at_utc`, normalized `forecast_retrieved_at_utc`, `forecast_lead_time_hours`, `forecast_age_hours`, `forecast_model`, `forecast_api_product`, explicit official observation retrieval time and publication delay, `source_lane`, row ingestion time, and `issue_valid_pair_id`.

Direct metadata answers:

- Current data partially preserves `forecast_issue_time_utc`, but it is collector/fetch-run lineage for Open-Meteo rows rather than verified provider model issue time.
- Current data does not preserve `model_run_time_utc`.
- Current data partially preserves retrieval time through fields such as `fetch_timestamp_utc` / `fetch_timestamp_utc_om`, but not as a normalized prospective evaluation field.
- Current artifacts do distinguish some valid-time fields from issue-like fields, but the issue-time semantics are not strong enough for prospective lead-time evaluation.
- The current Open-Meteo archive stores forecast snapshot rows keyed by collector-run issue-like time, location, and `valid_time_sgt`; paired outputs are then valid-time aligned for retrospective calibration.
- True `lead_time_hours` cannot be reconstructed today. A nominal value could be derived from existing issue-like and valid-time fields, but it would not be a defensible provider lead-time field.
- The exact missing fields are listed in `prospective_metadata_gap_audit.csv`.
- Open-Meteo Previous Runs / Historical Forecast / Single Runs remain a possible future Mode B route, not current evidence.
- Current System A can claim retrospective WBGT-like score and P_ge31 diagnostic analysis only.
- Prospective skill, official warning probability, 100m local WBGT, and risk forecast remain forbidden until prospective evidence exists.

## Current Claim Boundary

Allowed today: retrospective WBGT-like background score analysis, retrospective P_ge31 diagnostic companion, station-network / AOI background temporal severity diagnostics, and System B temporal severity input with output contract caveats.

Forbidden today: prospective forecast skill, lead-time-specific forecast accuracy, operational warning probability, official warning system, 100m local WBGT, risk forecast, and System B cell severity from station rows.

## Metadata Gap Summary

Blockers: no verified provider model run time, no reliable lead-time field, no normalized forecast retrieval time, no official WBGT retrieval delay, no issue-valid pair key, and GHA/local latency not carried into row-level prospective records.

Non-blockers for retrospective Mode A: existing `timestamp_sgt`, `timestamp_utc`, `valid_time_sgt`, `official_wbgt_c`, station metadata, Open-Meteo forcing columns, and retrospective calibration flags are sufficient for the current retrospective System A Level 1 evidence.

## Prospective Evaluation Design

The proposed schema stores explicit issue, model run, retrieval, valid, official observation, source-lane, and quality fields. Lead-time bins are nowcast_like_0h, 1h, 3h, 6h, 12h, and 24h, but only after forecast issue/model time is present. Metrics cover regression, high-tail, ge31 event detection, probability calibration, and operations health.

## Minimal Next Implementation

Primary recommendation: Sprint 4B.1 collector metadata patch design/implementation. Keep it small and additive: add future-row metadata fields, row-level quality flags, and manifest join keys without rewriting historical archive files.

Optional recommendation: Sprint 4C P_ge31 export hardening can proceed in parallel only if it preserves the retrospective/prospective boundary and does not imply operational warning probability.

## Risks

- retrospective data mistaken as forecast
- missing issue time
- Open-Meteo stitched latest forecasts not equivalent to archived issue-time forecast
- GHA schedule latency
- official WBGT retrieval delay
- station coverage
- event sparsity

## Next Recommended Action

Primary: implement a small collector metadata patch for future prospective capture, then run a 24h smoke followed by a 7-day prospective archive smoke.

Optional: design a separate hindcast reconstruction experiment using Open-Meteo Previous Runs / Historical Forecast / Single Runs, with strict product and issue-time metadata.

## Compliance Notes

- no forbidden files touched
- no model training
- no archive modification
- no collector code modification
- no GitHub Actions workflow modification
- no System B/v12 touched
- no commit/stage performed
