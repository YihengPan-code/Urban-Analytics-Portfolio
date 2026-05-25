# Live Smoke Validation

- Status: PASS
- Checks passed: 18/18
- Forecast skill evaluation: none

| check | passed | detail |
| --- | --- | --- |
| Open-Meteo API calls within limit | True | 3 |
| WBGT API calls within limit | True | 1 |
| output path is live_smoke only | True | outputs\v11_level1\prospective_eval\live_smoke |
| no archive files modified by script | True | script writes only live_smoke outputs |
| no provider schema unexpected stop | True | none |
| no no_future_valid_times partial stop | True | none |
| forecast_requested_at_utc present | True | forecast_rows=3 |
| forecast_retrieved_at_utc present | True | forecast_rows=3 |
| selected forecast valid_time follows next-hour retrieval rule | True | min_valid_time_minus_retrieval_hours=0.816667 |
| official_retrieved_at_utc present if official API succeeded | True | official_success=True; official_rows=3 |
| source_lane equals local_live_smoke | True | ['local_live_smoke'] |
| issue_valid_pair_id present where pair candidate exists | True | pair_rows=0 |
| lead_time null when model/issue time missing | True | checked_rows=3 |
| missing flags present when model/issue time missing | True | checked_rows=3 |
| no row labelled forecast_skill_evaluated | True | none |
| no forbidden fields | True | none |
| no regression/event skill metrics written | True | none |
| quality_flag includes live_smoke_not_forecast_skill | True | checked available quality_flag columns |
