# Sprint 4B.1 Metadata Patch Report

Status: PASS as a minimal additive metadata preparation patch. Runtime collector integration is deferred for review.

## Scope

This sprint covered System A Level 1 archive metadata only. It prepares future collector rows for prospective evaluation metadata capture. It does not evaluate forecast skill, train models, modify historical archive data, or touch System B, Level 2, v12, SOLWEIG, QGIS, rasters, or GitHub Actions workflow files.

## Files Inspected

- `outputs/v11_level1/prospective_eval/collector_metadata_patch_plan.md`
- `outputs/v11_level1/prospective_eval/prospective_metadata_gap_audit.csv`
- `docs/v11/SystemA_Level1_prospective_eval_design_CN.md`
- `configs/v11/system_a_prospective_eval_config.example.yaml`
- `configs/v11/v11_longterm_archive_config.example.json`
- `configs/v11/v11_archive_gha_config.example.json`
- `scripts/v11_archive_collect_once.py`
- `scripts/v11_archive_gha_collect_once.py`
- `scripts/archive_nea_observations.py`
- `scripts/v09_fetch_historical_forecast_for_archive.py`
- `scripts/v11_archive_rebuild_normalized.py`
- `scripts/v11_archive_migrate_legacy.py`
- `scripts/v11_archive_force_openmeteo_backfill.py`
- `scripts/v11_archive_health_check.py`
- `scripts/v11_archive_health_summary.py`
- `scripts/v11_archive_preflight.py`
- `scripts/v11_alpha_archive_qa.py`
- `scripts/v11_alpha_archive_inventory.py`

## Files Created

- `scripts/v11_prospective_metadata_helpers.py`
- `scripts/v11_test_prospective_metadata_schema.py`
- `configs/v11/system_a_prospective_metadata_config.example.yaml`
- `docs/v11/SystemA_prospective_metadata_schema_CN.md`
- `outputs/v11_level1/prospective_eval/metadata_patch/collector_patch_feasibility_audit.md`
- `outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv`
- `outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.md`
- `outputs/v11_level1/prospective_eval/metadata_patch/sprint4b1_metadata_patch_report.md`

## Files Modified

No existing tracked collector/config/archive files were modified. The only code/config/doc changes are new additive files plus the generated smoke outputs listed above.

## Runtime Collector Decision

Runtime collector integration was deferred.

Reason: `scripts/v11_archive_collect_once.py` currently builds normalized and pair tables from cumulative archive tables, then writes combined de-duplicated CSV outputs. Adding metadata columns directly into the collector now would cause the next collector run to rewrite cumulative archive/pair files with new blank or recalculated columns across historical rows. That is too risky for a sprint whose hard rule is not to rewrite historical archive files or change existing-row semantics.

The feasibility audit gives exact future integration points:

- Open-Meteo rows: `fetch_openmeteo_location(...)` around `request_json(...)`.
- Official rows: `parse_data_gov_realtime(...)` and `normalize_nea_tables(...)`.
- Pair rows: `build_pairs(...)`, preferably via a future-run-only prospective chunk.
- GHA compact chunks/manifests: `append_live_chunk(...)` and `GhaManifest`.

## Schema Fields Added in Helper/Config

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

Quality flags implemented:

- `ok_prospective_metadata`
- `missing_model_run_time`
- `missing_forecast_issue_time`
- `missing_forecast_retrieved_at`
- `missing_official_retrieved_at`
- `missing_lead_time`
- `legacy_missing_prospective_metadata`

## Smoke Test

Command run:

```powershell
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v11_test_prospective_metadata_schema.py
```

Result: PASS, 6/6 synthetic tests.

Smoke outputs:

- `outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv`
- `outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.md`

Assertions covered:

- helper creates `issue_valid_pair_id`;
- lead time is `None` when issue/model time is missing;
- lead time is computed correctly from `model_run_time_utc`;
- legacy row gets legacy/missing metadata flags;
- strict prospective row passes required metadata;
- output columns match expected schema.

## Risks

- Current Open-Meteo `/v1/forecast` collector path does not expose a verified provider `model_run_time_utc`; lead-time skill must remain fail-closed until that metadata is available or a reliable product-specific issue time is established.
- Existing `forecast_issue_time_utc` in the collector is collector run time, not confirmed provider issue/model time.
- Local collector and GHA wrapper currently write cumulative or daily compact outputs; future runtime integration should isolate future-run-only prospective chunks before adding row metadata.
- GHA/local parity remains untested for prospective metadata until a live smoke is intentionally run.

## Commands Run

```powershell
Get-Location
rg --files
git status --short
Get-Content -Raw outputs\v11_level1\prospective_eval\collector_metadata_patch_plan.md
Get-Content -Raw docs\v11\SystemA_Level1_prospective_eval_design_CN.md
Get-Content -Raw configs\v11\system_a_prospective_eval_config.example.yaml
Get-Content -Raw configs\v11\v11_longterm_archive_config.example.json
Get-Content -Raw scripts\v11_archive_collect_once.py
Get-Content -Raw scripts\v11_archive_gha_collect_once.py
Get-Content -Raw configs\v11\v11_archive_gha_config.example.json
Get-Content -Raw outputs\v11_level1\prospective_eval\prospective_metadata_gap_audit.csv
rg -n "def fetch_openmeteo_location|rows.append|forecast_issue_time_utc|fetch_timestamp_utc|valid_time_sgt|openmeteo_source|manifest|to_csv|append_csv_dedup|def build_pairs|def collect_once" scripts\v11_archive_collect_once.py
rg -n "def |rows.append|forecast_issue|fetch_timestamp|manifest|to_csv|append_live_chunk|collect_once|GhaManifest" scripts\v11_archive_gha_collect_once.py
Get-Content scripts\v11_archive_collect_once.py | Select-Object -Skip 330 -First 190
Get-Content scripts\v11_archive_collect_once.py | Select-Object -Skip 600 -First 130
Get-Content scripts\v11_archive_collect_once.py | Select-Object -Skip 790 -First 130
Get-ChildItem scripts -Filter *archive*.py | Select-Object -ExpandProperty FullName
Select-String -Path scripts\archive_nea_observations.py,scripts\v09_fetch_historical_forecast_for_archive.py,scripts\v11_archive_rebuild_normalized.py,scripts\v11_archive_migrate_legacy.py,scripts\v11_archive_force_openmeteo_backfill.py -Pattern "rows.append|to_csv|forecast_issue|fetch_timestamp|manifest|openmeteo|data.gov|WBGT|wbgt"
Select-String -Path scripts\v11_archive_health_check.py,scripts\v11_archive_health_summary.py,scripts\v11_archive_preflight.py,scripts\v11_alpha_archive_qa.py,scripts\v11_alpha_archive_inventory.py -Pattern "to_csv|manifest|forecast_issue|fetch_timestamp|openmeteo|wbgt|pair|archive"
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v11_test_prospective_metadata_schema.py
git diff --name-only
```

## Safety Statements

- No historical archive rewritten.
- No existing snapshots modified.
- No live APIs fetched.
- No model training run.
- No previous model pipelines run.
- No System B touched.
- No Level 2 touched.
- No v12 touched.
- No SOLWEIG touched.
- No QGIS touched.
- No rasters or `.tif` files touched.
- No raw archive data touched.
- No GitHub Actions workflow modified.
- No branch created or switched.
- No commit performed.
- No staging performed.

## Next Action

1. 24h smoke: create a reviewed future-run-only prospective metadata chunk path and run a tiny intentional collector smoke.
2. 7d prospective archive smoke: confirm schema stability, GHA/local parity, station coverage, retrieval timing, and missingness.
3. Patch review: only after the above, integrate helper calls into collector runtime without rewriting historical archive semantics.
