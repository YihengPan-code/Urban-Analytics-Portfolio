# Sprint 4B.3 — One-run Live Local Prospective Metadata Smoke

## Status
PASS

## Scope
- one-run local API smoke
- metadata only
- no archive write
- no collector runtime modification
- no forecast skill evaluation
- no model training
- no System B/v12/SOLWEIG/local WBGT

## API calls
- Open-Meteo call count: 3
- WBGT API call count: 1
- Status codes: [200, 200, 200, 200]
- Elapsed time seconds: [0.144, 0.145, 0.149, 0.624]
- Endpoint summary: no secrets; public endpoint and query summaries recorded in manifest.

## Forecast metadata
- Rows: 3
- Stations: 3
- Valid_time range: 2026-05-25T23:00:00Z to 2026-05-25T23:00:00Z
- Min_valid_time_minus_retrieval_hours: 0.816667
- Provider model_run_time availability: 0 rows
- Lead_time availability: 0 rows
- Quality_flag counts: {'live_smoke_not_forecast_skill': 3, 'missing_forecast_issue_time': 3, 'missing_lead_time': 3, 'missing_model_run_time': 3}

## Official WBGT metadata
- Rows: 3
- Stations: 3
- Observation time availability: 3 rows
- Official_retrieved_at availability: 3 rows
- Quality_flag counts: {'live_smoke_not_forecast_skill': 3}

## Pair candidates
- Rows: 1
- Exact pairing possible? no
- Issue_valid_pair_id count/uniqueness: 0 / False
- Quality flags: {'live_smoke_not_forecast_skill': 1, 'no_safe_pairing': 1}
- Rows eligible for skill evaluation: 0
- Expected: no skill evaluation yet.

## Validation checks
- Checks passed: 18/18
- Schema errors: none
- Smoke warnings: none

## What this proves
- local live API smoke can capture request/retrieval metadata
- output manifest and validation work with real API responses
- fail-closed behavior still works when provider model_run_time is absent

## What this does not prove
- no forecast skill
- no lead-time accuracy
- no operational warning probability
- no official forecast product validation
- no GHA/local parity
- no 24h continuity
- no local WBGT

## Next recommended action
- Evaluate Open-Meteo Previous Runs / Single Runs route if provider model_run_time is not available in Forecast API.

## Safety statements
- no forbidden files touched
- API call counts: Open-Meteo=3, WBGT=1
- no archive modification
- no collector runtime modification
- no model training
- no forecast skill evaluation
- no System B/v12 touched
- no commit/stage performed