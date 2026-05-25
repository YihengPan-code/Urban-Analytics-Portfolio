# Prospective Metadata Schema Smoke

- Tests passed: 6/6
- Output CSV: `outputs\v11_level1\prospective_eval\metadata_patch\prospective_metadata_schema_smoke.csv`
- API calls: none
- Archive reads/writes: none

## Results

| test                                                    | passed   | detail                                                                                                                                                                    |
|:--------------------------------------------------------|:---------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| helper creates issue_valid_pair_id                      | True     | ivp_80578384b6707897                                                                                                                                                      |
| lead_time is None when issue/model time missing         | True     | None                                                                                                                                                                      |
| lead_time computed correctly when model_run_time exists | True     | 12.0                                                                                                                                                                      |
| legacy row gets legacy/missing metadata flags           | True     | missing_model_run_time\|missing_forecast_issue_time\|missing_forecast_retrieved_at\|missing_official_retrieved_at\|missing_lead_time\|legacy_missing_prospective_metadata |
| strict prospective row passes required metadata         | True     | ok_prospective_metadata                                                                                                                                                   |
| output columns match expected schema                    | True     | all present                                                                                                                                                               |

## Expected Prospective Metadata Fields

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