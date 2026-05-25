# System A Level 1 Prospective Forecast Evaluation Design

## 0. Metadata

- date: 2026-05-25
- repo: Urban-Analytics-Portfolio/06-openheat_grid
- status: design / metadata audit / no model training
- scope: System A Level 1 only; no collector patch, no archive modification, no System B, no Level 2, no SOLWEIG, no v12, no local WBGT.

## 1. Why this is needed

All current Level 1 evidence is retrospective. Weather forcing and official WBGT are aligned by valid time after the fact, then evaluated with LOSO, blocked-date, future-block, event, and probability diagnostics. That is useful for calibration, but it is not the same as prospective forecast skill.

Prospective forecast evaluation asks a stricter question: given only the forecast information available at a past issue or retrieval time, how well did the later valid-time outcome match official observations once those observations became available?

## 2. Definitions

- valid_time: the time the forecast or observation describes.
- forecast_issue_time: the time a forecast product is issued or made available for use.
- model_run_time: the provider model cycle time that generated the forecast product.
- retrieval_time: the time the collector requested or received the forecast or official observation.
- forecast_age: retrieval_time minus model_run_time, when model_run_time is available.
- lead_time: valid_time minus forecast_issue_time or model_run_time, depending on the evaluated product definition.
- nowcast-like: a zero-hour or near-zero-hour product evaluated at valid times close to collection time.
- hindcast reconstruction: later reconstruction of what forecast would have been available at a past issue time, using archived forecast products such as Previous Runs, Historical Forecast, or Single Runs.
- live prospective evaluation: evaluation of forecasts collected live before the target valid time and compared later with official observations.
- evaluation_available_time: the time when both forecast and official observation are available for scoring.
- official observation retrieval delay: official_observation_retrieved_at minus official_observed_at or valid_time.

## 3. Current state

Current artifacts support Mode A retrospective valid-time calibration. Pair tables preserve station ids, official WBGT, valid timestamps, Open-Meteo forcing, and some collector-run lineage such as `archive_run_id`, `forecast_issue_time_utc`, `fetch_timestamp_utc_om`, and `issue_age_hours`.

They do not yet support true Mode C prospective forecast evaluation. The missing pieces are verified provider issue/model run time, normalized request/retrieval timing, source product metadata, official observation retrieval delay, lead-time fields, source lane, and a deterministic issue-valid pair key.

Current artifacts partially support a future Mode B design because Open-Meteo products may allow historical issue-time reconstruction, but that route has not been implemented or validated here.

## 4. Three Evaluation Modes

### 4.1 Retrospective Valid-Time Calibration

Existing. Weather and official WBGT are aligned by valid_time after the fact. It supports retrospective WBGT-like score calibration, blocked-time diagnostics, high-tail analysis, and retrospective P_ge31 diagnostics. It does not support forecast skill claims.

### 4.2 Hindcast Forecast Reconstruction

Possible future route. The project may use Open-Meteo Historical Forecast, Previous Runs, or Single Runs to reconstruct what would have been available at a past issue time. This can support lead-time skill analysis only if the source product exposes or permits reliable reconstruction of issue/model run time, valid time, endpoint/product identity, and retrieval assumptions.

### 4.3 Live Prospective Collection

Future route. The collector must store forecast_issue_time, forecast_retrieved_at, valid_time, lead_time_hours, model/run metadata, and official observation retrieval time. After enough future data accumulates, this supports true prospective forecast evaluation.

## 5. Proposed Data Schema

- issue_valid_pair_id
- station_id
- valid_time_utc
- valid_time_sgt
- forecast_issue_time_utc
- model_run_time_utc
- forecast_retrieved_at_utc
- lead_time_hours
- forecast_age_hours
- openmeteo_endpoint
- openmeteo_model
- openmeteo_product
- temperature_2m
- relative_humidity_2m
- wind_speed_10m
- shortwave_radiation
- wbgt_proxy_v09_c
- wbgt_a_score_c
- p_ge31_diagnostic
- official_wbgt_c
- official_observed_at_utc
- official_retrieved_at_utc
- evaluation_available_at_utc
- collector_run_id
- archive_run_id
- source_lane
- quality_flag

## 6. Lead-Time Bins

Proposed bins:

- nowcast_like_0h
- 1h
- 3h
- 6h
- 12h
- 24h

These bins are valid only if forecast_issue_time or model_run_time exists and is semantically correct for the forecast product being evaluated.

## 7. Metrics

Regression: MAE, RMSE, bias, R2.

High-tail: MAE official >=31, bias official >=31.

Event: precision / recall / F1 ge31, PR-AUC.

Probability: Brier, ECE, reliability bins.

Operations: forecast availability rate, station coverage, retrieval latency, missingness, lead-time completeness.

## 8. Minimum Viable Prospective Smoke

Before starting, require these fields: valid_time_utc, forecast_issue_time_utc or model_run_time_utc, forecast_retrieved_at_utc, lead_time_hours, forecast_provider, forecast_endpoint or product, station_id, official_observed_at_utc, official_retrieved_at_utc, collector_run_id, source_lane, quality_flag, and issue_valid_pair_id.

Use a 7-day smoke minimum to test collection completeness and schema stability. Use a 14-day first formal prospective snapshot only after the smoke passes. Prefer a 30-day prospective evaluation for initial skill reporting. Apply an event-count caveat: ge31 and especially ge33 conclusions remain weak if event counts are sparse or dominated by one station.

## 9. Stop Conditions

- no forecast_issue_time
- no valid issue/valid separation
- Open-Meteo data fetched after valid_time but labelled forecast
- official WBGT retrieval time unavailable
- lead_time cannot be reconstructed
- GHA/local collector latency not recorded

## 10. Recommended Implementation Sequence

1. metadata patch design review
2. collector metadata patch, small
3. 24h smoke
4. 7d prospective archive smoke
5. 14d prospective snapshot
6. prospective model-score evaluation
7. prospective P_ge31 evaluation

## 11. Claim Boundary

Before prospective evaluation, System A Level 1 may claim retrospective WBGT-like background score analysis, retrospective P_ge31 diagnostic companion, station-network / AOI background temporal severity diagnostics, and System B temporal severity input with output contract caveats.

Before prospective evaluation, System A Level 1 must not claim prospective forecast skill, lead-time-specific forecast accuracy, operational warning probability, official warning status, 100m local WBGT, risk forecast, or System B cell severity from station rows.

After a valid prospective evaluation exists, the project may claim lead-time-specific retrospective-to-prospective skill only for the evaluated product, station/AOI scope, period, lead bins, event counts, and quality filters. It still must not claim official warnings, 100m local WBGT, or risk forecast unless those are separately implemented and validated.
