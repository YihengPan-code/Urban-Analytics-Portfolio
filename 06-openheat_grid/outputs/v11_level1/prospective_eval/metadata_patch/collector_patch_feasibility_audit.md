# Sprint 4B.1 Collector Patch Feasibility Audit

Status: additive metadata patch audit only. No collector runtime integration was applied in this sprint.

## Files Inspected

| File | Exists | Role |
|---|---:|---|
| `outputs/v11_level1/prospective_eval/collector_metadata_patch_plan.md` | yes | Prior design-only patch plan. |
| `outputs/v11_level1/prospective_eval/prospective_metadata_gap_audit.csv` | yes | Field gap audit from Sprint 4B. |
| `docs/v11/SystemA_Level1_prospective_eval_design_CN.md` | yes | Prospective evaluation design and claim boundary. |
| `configs/v11/system_a_prospective_eval_config.example.yaml` | yes | Prospective evaluation config example. |
| `configs/v11/v11_longterm_archive_config.example.json` | yes | Local long-term collector config. |
| `configs/v11/v11_archive_gha_config.example.json` | yes | GHA compact archive wrapper config. |
| `scripts/v11_archive_collect_once.py` | yes | Main local collector, normalizer, Open-Meteo fetcher, pair builder, QA/state writer. |
| `scripts/v11_archive_gha_collect_once.py` | yes | GHA wrapper that runs the main collector in a temporary archive and writes compact live chunks/manifests. |
| `scripts/archive_nea_observations.py` | yes | Legacy NEA archive script; not the active v11 prospective metadata integration target. |
| `scripts/v09_fetch_historical_forecast_for_archive.py` | yes | Historical Open-Meteo fetcher; relevant to future Hindcast Mode B, not live v11 collector patch. |
| `scripts/v11_archive_rebuild_normalized.py` | yes | Rebuilds normalized archive tables; must not be patched for prospective metadata in this sprint. |
| `scripts/v11_archive_migrate_legacy.py` | yes | Legacy migration script; must not rewrite historical metadata. |
| `scripts/v11_archive_force_openmeteo_backfill.py` | yes | Backfill control helper; out of scope for Sprint 4B.1. |
| `scripts/v11_archive_health_check.py` | yes | Read-only health diagnostics. |
| `scripts/v11_archive_health_summary.py` | yes | Read-only compact health diagnostics. |
| `scripts/v11_archive_preflight.py` | yes | Config preflight. |
| `scripts/v11_alpha_archive_qa.py` | yes | Retrospective archive QA; not a live prospective collector. |
| `scripts/v11_alpha_archive_inventory.py` | yes | Archive inventory only. |

## Assembly Points Found

### NEA / Official Rows

- `scripts/v11_archive_collect_once.py:347`: official/data.gov.sg long rows are assembled in `parse_data_gov_realtime(...)`.
- `scripts/v11_archive_collect_once.py:369`: each official row currently stores `fetch_timestamp_utc`.
- `scripts/v11_archive_collect_once.py:384`: `normalize_nea_tables(...)` builds normalized WBGT and station-weather tables from the cumulative NEA long table.
- `scripts/v11_archive_collect_once.py:856`: cumulative NEA long CSV is written through `append_csv_dedup(...)`.
- `scripts/v11_archive_collect_once.py:860`: cumulative normalized WBGT CSV is written.
- `scripts/v11_archive_collect_once.py:861`: cumulative normalized station-weather CSV is written.

Prospective metadata implication: official retrieval timing can be sourced from the per-row `fetch_timestamp_utc`, but adding `official_retrieved_at_utc` inside the current cumulative normalizer would add new columns when rewriting cumulative normalized tables. That is safe only after explicit historical-row handling is reviewed.

### Open-Meteo Forecast Rows

- `scripts/v11_archive_collect_once.py:468`: Open-Meteo request/row assembly lives in `fetch_openmeteo_location(...)`.
- `scripts/v11_archive_collect_once.py:494`: `forecast_issue_time_utc` is currently set to the collector `run_dt`, not a verified provider model cycle.
- `scripts/v11_archive_collect_once.py:495`: `fetch_timestamp_utc` is currently set per row after the request.
- `scripts/v11_archive_collect_once.py:502`: forecast valid time is stored as `valid_time_sgt`.
- `scripts/v11_archive_collect_once.py:883`: cumulative Open-Meteo snapshots are written through `append_csv_dedup(...)`.

Prospective metadata implication: `forecast_requested_at_utc` and `forecast_retrieved_at_utc` can be captured around `request_json(...)`. However, `model_run_time_utc` is not currently available from the configured `/v1/forecast` response path, and `forecast_issue_time_utc` must not be treated as provider model run time.

### Pair Rows

- `scripts/v11_archive_collect_once.py:612`: pair rows are assembled in `build_pairs(...)`.
- `scripts/v11_archive_collect_once.py:621-623`: official WBGT valid time is rounded to an hourly SGT valid time.
- `scripts/v11_archive_collect_once.py:626-627`: Open-Meteo valid time and current `forecast_issue_time_utc` are parsed for pairing.
- `scripts/v11_archive_collect_once.py:667-668`: `issue_age_hours` is computed as observation time minus collector-assigned forecast issue time.
- `scripts/v11_archive_collect_once.py:887`: operational pair table is written through `append_csv_dedup(...)`.
- `scripts/v11_archive_collect_once.py:889`: latest pair table is rewritten with `pairs_all.to_csv(...)`.
- `scripts/v11_archive_gha_collect_once.py:99`: GHA live chunks are appended/deduplicated in `append_live_chunk(...)`.
- `scripts/v11_archive_gha_collect_once.py:115`: GHA compact chunk CSV.GZ is written.

Prospective metadata implication: pair rows are the right place for `issue_valid_pair_id`, `forecast_lead_time_hours`, `official_retrieved_at_utc`, `collector_run_id`, `source_lane`, and `quality_flag`. The current builder consumes cumulative normalized tables, so patching it now would populate or blank-fill metadata across historical rows on the next collector run.

### Run Manifests

- `scripts/v11_archive_collect_once.py:901-923`: local collector writes a QA report and JSON state, but not a row-level run manifest table.
- `scripts/v11_archive_gha_collect_once.py:47-62`: `GhaManifest` defines GHA run manifest fields.
- `scripts/v11_archive_gha_collect_once.py:160-164`: GHA manifest JSON/latest/CSV outputs are written.
- `scripts/v11_archive_gha_collect_once.py:211-225`: GHA run metadata is assembled, including scheduled/start/completed timing, source, row counts, warnings, API status, commit SHA, and chunk path.

Prospective metadata implication: GHA run metadata is already strong enough to join to rows if `gha_run_id` or `collector_run_id` is propagated into future compact chunks. Local loop needs a small manifest sidecar in a later reviewed patch.

## Safety Decision

Runtime collector patching is deferred.

Reason: the active v11 collector writes cumulative archive and pair CSVs by reading old rows, concatenating new rows, de-duplicating, and rewriting the combined table. Adding prospective metadata columns directly to `parse_data_gov_realtime(...)`, `fetch_openmeteo_location(...)`, `normalize_nea_tables(...)`, or `build_pairs(...)` would be additive in schema but would still cause the next collector run to rewrite cumulative files with metadata columns across historical rows. That is too close to the "do not rewrite historical archive files" boundary for Sprint 4B.1.

This sprint instead adds:

- a standalone helper module;
- a metadata config example;
- synthetic smoke tests;
- schema documentation;
- exact integration recommendations for a later reviewed collector patch.

## Recommended Runtime Integration Patch

Apply only in a future patch review or 24h smoke branch.

1. `scripts/v11_archive_collect_once.py:468`
   - Capture `forecast_requested_at_utc = utc_now_iso()` immediately before `request_json(...)`.
   - Capture `forecast_retrieved_at_utc = utc_now_iso()` immediately after it returns.
   - Add row fields only to `openmeteo_new` rows, not by rewriting historic Open-Meteo snapshots.

2. `scripts/v11_archive_collect_once.py:347`
   - Add `official_retrieved_at_utc` from the existing `fetch_timestamp_utc` semantics for new official rows.
   - Keep `official_observed_at_utc` derived from the official observation timestamp, not the retrieval timestamp.

3. `scripts/v11_archive_collect_once.py:612`
   - Attach prospective metadata only to rows produced from the current run's new WBGT/Open-Meteo rows, or write a separate future prospective chunk.
   - Use `scripts/v11_prospective_metadata_helpers.py`.
   - Do not compute `forecast_lead_time_hours` from retrieval time.
   - Keep `model_run_time_utc` blank until provider model cycle metadata is verified.
   - Set `quality_flag` to include `missing_model_run_time` and `missing_lead_time` when no reliable issue/model time exists.

4. `scripts/v11_archive_collect_once.py:901`
   - Add a local manifest JSON/CSV sidecar under a controlled output path.
   - Include `collector_run_id`, `source_lane`, scheduled/start/completed timing if known, rows fetched, rows added, warnings, API status, and output chunk path.

5. `scripts/v11_archive_gha_collect_once.py:99`
   - Propagate `gha_run_id`, `scheduled_at_utc`, `started_at_utc`, `completed_at_utc`, and `source_lane=gha` into future live chunks.
   - Prefer writing a new prospective chunk or new future-date rows only; do not backfill existing chunk rows.

## Feasibility Summary

| Code path | Safe to patch now? | Decision |
|---|---:|---|
| Helper/schema/config/docs | yes | Completed additively. |
| Open-Meteo request timing capture | partly | Defer until future-run-only write path is isolated. |
| Official retrieval timing capture | partly | Defer until future-run-only write path is isolated. |
| Pair row prospective metadata | no | Defer because current pair builder rewrites cumulative historical rows. |
| GHA manifest enhancement | partly | Defer because compact chunks may contain already-written historical rows. |
| Historical archive/snapshot rewrite | no | Not allowed. |
