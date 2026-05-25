# Collector Metadata Patch Plan - Design Only

Status: design only. This file does not patch collector code, GitHub Actions, archive files, or historical data.

## Candidate Files To Patch Later

- `scripts/v11_archive_collect_once.py`
- `scripts/v11_archive_gha_collect_once.py`
- `configs/v11/v11_longterm_archive_config.example.json`
- `configs/v11/v11_archive_gha_config.example.json`
- `docs/v11/OpenHeat_GHA_archive_ops_note_CN.md`
- `.github/workflows/v11_archive_collector.yml`, if that workflow is restored or added in a future ops sprint

## Fields To Add

- `issue_valid_pair_id`
- `valid_time_utc`
- `valid_time_sgt`
- `forecast_issue_time_utc`
- `model_run_time_utc`
- `forecast_requested_at_utc`
- `forecast_retrieved_at_utc`
- `forecast_provider`
- `forecast_model`
- `forecast_endpoint`
- `forecast_api_product`
- `forecast_lead_time_hours`
- `forecast_age_hours`
- `openmeteo_grid_lat`
- `openmeteo_grid_lon`
- `official_observed_at_utc`
- `official_retrieved_at_utc`
- `official_wbgt_publication_delay_minutes`
- `collector_run_id`
- `archive_run_id`
- `gha_run_id`
- `scheduled_at_utc`
- `started_at_utc`
- `completed_at_utc`
- `source_lane`
- `row_added_at_utc`
- `quality_flag`

## Naming Convention

Use UTC suffixes for UTC timestamps, SGT suffixes for Singapore display timestamps, and `_hours` or `_minutes` for durations. Keep provider/product metadata explicit: `forecast_provider`, `forecast_endpoint`, `forecast_api_product`, and `forecast_model`.

## Backward Compatibility

Do not rewrite historical archive files. Future readers should accept missing metadata on historical rows and mark them `quality_flag=legacy_missing_prospective_metadata` or equivalent. Any prospective evaluator should fail closed when required metadata is absent.

## Manifest Changes

Run manifests should include collector_run_id, source_lane, scheduled_at_utc, started_at_utc, completed_at_utc, rows_fetched, rows_added, stations_seen, warnings, api_status, commit_sha, and output chunk path. Pair rows should carry a joinable collector_run_id or gha_run_id.

## Smoke Tests

- Header-only schema test for required metadata fields.
- One-run local dry smoke that writes only compact test output.
- One GHA/manual smoke that confirms scheduled/start/completed timing is recorded.
- Join test from compact pair rows to run manifest.
- Lead-time calculation test that rejects rows with missing or invalid issue/model time.
- Official observation delay test that rejects rows without official retrieval time.

## No Large Git Files Rule

Keep future prospective outputs compact. Do not commit rasters, raw JSON dumps, large all-grid forecast exports, `*.tif`, `*.tiff`, SOLWEIG folders, raw archive, or hourly grid heat-stress forecast exports. Use the configured guard threshold and stop for review if any file exceeds it.

## Avoid Modifying Historical Archive

Add new fields only to future chunks/snapshots. For old rows, keep legacy columns as read-only evidence and expose missing metadata through quality flags in derived prospective snapshots.

## Version Future Prospective Snapshots

Use names such as `system_a_level1_prospective_pairs_v0_1_YYYYMMDD_YYYYMMDD.csv.gz` and a sidecar manifest JSON/MD. Include schema version, source lane, lead bins, model score version, probability calibrator version, date range, station coverage, event counts, and required-metadata completeness.

## Validate GHA/Local Parity

Compare local_loop and gha for station coverage, valid_time completeness, forecast retrieval latency, rows_added, warnings, Open-Meteo product metadata, official observation delay, and computed lead-time bins. Do not stop local collection until parity is documented for the chosen smoke period.
