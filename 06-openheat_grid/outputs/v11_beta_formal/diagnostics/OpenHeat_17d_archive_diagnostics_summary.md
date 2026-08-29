# OpenHeat v1.1-beta-formal archive diagnostics summary

## Archive health

```json
{
  "rows": 40419,
  "wbgt_rows": 40389,
  "unique_stations": 27,
  "unique_timestamps": 1497,
  "first_obs": "2026-05-06 18:00:00+00:00",
  "last_obs": "2026-05-24 12:40:03+00:00",
  "span_days": 17.778,
  "nat_rows": 0
}
```

## Row attrition diagnostic

```text
                 diagnostic  rows
                 total_rows 40419
retrospective_eligible_rows 40419
   official_wbgt_c_non_null 40389
    official_wbgt_c_missing    30
  wbgt_proxy_v09_c_non_null 40419
   wbgt_proxy_v09_c_missing     0
  target_and_proxy_non_null 40389
```

## Top heat-event days by ≥31°C rows

```text
  date_sgt  rows  stations  max_wbgt  ge31  ge33
2026-05-20  2481        27      34.3   439    32
2026-05-19  2496        27      34.1   399    40
2026-05-07  2321        27      34.0   268    10
2026-05-14  2538        27      33.8   244    22
2026-05-22  2483        27      33.5   229     9
2026-05-21  2511        27      33.3   223     9
2026-05-11  2538        27      34.4   211    23
```

## S142 contribution

```text
station_id  rows  timestamps  max_wbgt  ge31  ge33
      S142  1496        1496      34.4   257    76
```

## Interpretation notes

- This diagnostic is for frozen-snapshot formal closeout, not live archive comparison.
- Row attrition must be interpreted before comparing calibration metrics.
- ≥33°C event modeling should remain exploratory if high-tail events are station-concentrated.
- GHA cadence, once enabled, must be described as best-effort scheduled cadence, not strict sensor-grade 15-minute cadence.
