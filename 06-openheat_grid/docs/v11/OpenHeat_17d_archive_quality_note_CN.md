# OpenHeat v1.1-beta-formal 17.78d Archive Quality Note

**Document date:** 2026-05-24  
**Project:** OpenHeat-ToaPayoh  
**Repo path:** `Urban-Analytics-Portfolio/06-openheat_grid`  
**Status:** v1.1-beta-formal archive quality note  
**Scope:** frozen archive quality / completeness / event distribution / run-log appendix  
**Not scope:** model replacement, ML, SOLWEIG, local 100m WBGT, risk map

---

## 0. Executive summary

This note records the quality of the frozen v1.1-beta-formal archive used for the 17.78-day formal closeout.

Main conclusion:

```text
The frozen archive is healthy enough for formal System A calibration closeout.
It contains 40,419 rows, 27 stations, 1,497 timestamps, zero NaT rows,
and only 30 missing official WBGT targets.
```

The archive quality result is mostly positive:

```text
- 27 / 27 stations are represented.
- Target/proxy analytic attrition is very small: 30 rows / 40,419 = 0.074%.
- v0.9 proxy exists for all 40,419 rows.
- target + proxy analytic rows = 40,389.
- >=31C event rows = 2,844.
- >=33C event rows = 212.
- S142 contributes 257 / 2,844 >=31C rows = 9.0%.
- S142 contributes 76 / 212 >=33C rows = 35.8%.
```

Therefore, the weaker v1.1-beta-formal calibration performance is **not explained by target/proxy missingness or gross archive corruption**. It is more likely related to regime complexity, fresh-v11 distribution, station-specific high-tail behavior, formula/forcing limitations, or threshold calibration limits.

---

## 1. Snapshot identity

The formal snapshot was frozen from the live v11 station-weather paired archive.

### 1.1 Snapshot files

Raw / paired frozen snapshot:

```text
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419.csv
```

v091 feature snapshot:

```text
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv
```

Hourly aggregated snapshot:

```text
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_hourly.csv
```

### 1.2 File sizes observed locally

```text
v11_pairs_14d_formal_20260524_40419.csv        60,656,549 bytes
v11_pairs_14d_formal_20260524_40419_v091.csv   72,000,241 bytes
v11_pairs_14d_formal_20260524_40419_hourly.csv  6,037,454 bytes
```

### 1.3 Naming note

The original freeze helper used `wmic` to generate a timestamp. On this Windows system, `wmic` was unavailable, causing malformed filenames containing `~0,8`. The files were manually renamed to stable `20260524_40419` names.

This is a naming / batch-script portability bug. It does **not** invalidate the frozen data content.

Recommended follow-up patch:

```bat
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
```

---

## 2. Archive health summary

The diagnostics summary reports:

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

Interpreted in Singapore time, this corresponds approximately to:

```text
first_obs_sgt ~= 2026-05-07 02:00:00+08:00
last_obs_sgt  ~= 2026-05-24 20:40:03+08:00
```

Key interpretation:

```text
- The snapshot exceeds the originally planned 14-day minimum.
- It should be described as a 17.78-day formal snapshot.
- Timestamp parsing succeeded: NaT rows = 0.
- All 27 stations are represented.
```

---

## 3. Row attrition diagnostic

The row attrition diagnostic is:

| Diagnostic | Rows |
|---|---:|
| total_rows | 40,419 |
| retrospective_eligible_rows | 40,419 |
| official_wbgt_c_non_null | 40,389 |
| official_wbgt_c_missing | 30 |
| wbgt_proxy_v09_c_non_null | 40,419 |
| wbgt_proxy_v09_c_missing | 0 |
| target_and_proxy_non_null | 40,389 |

Derived missingness:

```text
official_wbgt_c missing share = 30 / 40,419 = 0.074%
wbgt_proxy_v09_c missing share = 0 / 40,419 = 0.000%
analytic target+proxy rows = 40,389
```

Interpretation:

```text
Row attrition is very small.
The formal MAE degradation is not caused by target/proxy missingness.
```

This satisfies the v2.2 formal-pass requirement to explicitly document target/proxy attrition before interpreting formal metrics.

---

## 4. Event counts by day

Daily event counts from the frozen snapshot:

| date_sgt | rows | stations | max_wbgt | ge31 | ge33 |
|---|---:|---:|---:|---:|---:|
| 2026-05-07 | 2,321 | 27 | 34.0 | 268 | 10 |
| 2026-05-08 | 243 | 27 | 27.2 | 0 | 0 |
| 2026-05-09 | 783 | 27 | 31.9 | 6 | 0 |
| 2026-05-10 | 2,484 | 27 | 34.1 | 198 | 19 |
| 2026-05-11 | 2,538 | 27 | 34.4 | 211 | 23 |
| 2026-05-12 | 2,535 | 27 | 34.2 | 187 | 25 |
| 2026-05-13 | 2,266 | 27 | 32.4 | 11 | 0 |
| 2026-05-14 | 2,538 | 27 | 33.8 | 244 | 22 |
| 2026-05-15 | 2,537 | 27 | 29.0 | 0 | 0 |
| 2026-05-16 | 2,510 | 27 | 26.4 | 0 | 0 |
| 2026-05-17 | 2,511 | 27 | 32.5 | 57 | 0 |
| 2026-05-18 | 2,511 | 27 | 33.9 | 35 | 5 |
| 2026-05-19 | 2,496 | 27 | 34.1 | 399 | 40 |
| 2026-05-20 | 2,481 | 27 | 34.3 | 439 | 32 |
| 2026-05-21 | 2,511 | 27 | 33.3 | 223 | 9 |
| 2026-05-22 | 2,483 | 27 | 33.5 | 229 | 9 |
| 2026-05-23 | 2,511 | 27 | 34.3 | 135 | 7 |
| 2026-05-24 | 2,130 | 27 | 33.7 | 202 | 11 |

Top heat-event days by `>=31C` rows:

```text
2026-05-20: ge31=439, ge33=32
2026-05-19: ge31=399, ge33=40
2026-05-07: ge31=268, ge33=10
2026-05-14: ge31=244, ge33=22
2026-05-22: ge31=229, ge33=9
2026-05-21: ge31=223, ge33=9
2026-05-11: ge31=211, ge33=23
```

Interpretation:

```text
The formal snapshot contains multiple hot days and mixed regimes, especially the 2026-05-19 to 2026-05-22 hot period.
This supports the interpretation that the formal snapshot is harder than the 4-day pre-formal subset.
```

---

## 5. Event counts by station

Station event counts from the frozen snapshot:

| station_id | rows | timestamps | max_wbgt | ge31 | ge33 |
|---|---:|---:|---:|---:|---:|
| S124 | 1497 | 1497 | 32.0 | 18 | 0 |
| S125 | 1497 | 1497 | 33.9 | 144 | 3 |
| S126 | 1497 | 1497 | 33.0 | 103 | 1 |
| S127 | 1497 | 1497 | 33.1 | 125 | 3 |
| S128 | 1497 | 1497 | 34.2 | 121 | 13 |
| S129 | 1482 | 1482 | 32.7 | 115 | 0 |
| S130 | 1497 | 1497 | 32.1 | 66 | 0 |
| S132 | 1491 | 1491 | 33.0 | 117 | 2 |
| S135 | 1496 | 1496 | 34.3 | 187 | 21 |
| S137 | 1495 | 1495 | 34.2 | 209 | 46 |
| S139 | 1494 | 1494 | 31.7 | 10 | 0 |
| S140 | 1497 | 1497 | 32.6 | 54 | 0 |
| S141 | 1497 | 1497 | 33.7 | 126 | 11 |
| S142 | 1496 | 1496 | 34.4 | 257 | 76 |
| S143 | 1497 | 1497 | 33.3 | 127 | 7 |
| S144 | 1497 | 1497 | 33.7 | 95 | 7 |
| S145 | 1496 | 1496 | 33.3 | 111 | 4 |
| S146 | 1497 | 1497 | 32.7 | 60 | 0 |
| S147 | 1497 | 1497 | 33.7 | 151 | 10 |
| S148 | 1497 | 1497 | 31.9 | 32 | 0 |
| S149 | 1497 | 1497 | 32.3 | 54 | 0 |
| S150 | 1497 | 1497 | 33.0 | 65 | 1 |
| S151 | 1497 | 1497 | 33.2 | 142 | 3 |
| S153 | 1497 | 1497 | 32.6 | 80 | 0 |
| S180 | 1497 | 1497 | 33.6 | 86 | 1 |
| S184 | 1496 | 1496 | 33.4 | 72 | 2 |
| S187 | 1497 | 1497 | 33.0 | 117 | 1 |

Derived totals:

```text
total ge31 = 2,844
total ge33 = 212
```

---

## 6. S142 high-tail contribution

S142 event counts:

```text
rows = 1,496
max_wbgt = 34.4C
ge31 = 257
ge33 = 76
```

S142 contribution shares:

```text
S142 ge31 share = 257 / 2,844 = 9.0%
S142 ge33 share = 76 / 212 = 35.8%
```

Interpretation:

```text
S142 remains the largest single high-tail contributor, especially for >=33C events.
However, S142 no longer dominates the >=33C high tail above the earlier 55% concern threshold.
```

Formal hypothesis implication:

```text
H5 PASS: S142 share of >=33C events decreased below the 55% threshold.
>=33C modeling should still be caveated because high-tail events remain station-concentrated, but the extreme S142 dominance observed in the pre-formal archive is materially reduced.
```

---

## 7. Cadence and completeness notes

The formal snapshot has:

```text
unique_timestamps = 1,497
unique_stations = 27
rows = 40,419
```

The ideal fully complete 27-station table would be:

```text
1,497 timestamps × 27 stations = 40,419 rows
```

This matches the snapshot row count exactly.

The missing official WBGT values are target values, not missing station-time rows:

```text
station-time rows present = 40,419 / 40,419
official_wbgt_c missing = 30
```

Therefore:

```text
station-time coverage is effectively complete;
target WBGT missingness is tiny.
```

---

## 8. Archive quality verdict

Formal archive quality verdict:

```text
GREEN for formal closeout use.
```

Reasons:

```text
- 27 / 27 stations represented.
- 1,497 timestamps represented.
- Complete station-time grid: 40,419 rows = 1,497 × 27.
- NaT rows = 0.
- Target/proxy analytic rows = 40,389.
- Official WBGT missingness = 0.074%.
- >=31C event count sufficient for threshold diagnostics.
- >=33C event count improved relative to pre-formal state, although still high-tail caveated.
```

Caveats:

```text
- This is a frozen retrospective snapshot, not a live operational archive quality assessment.
- GHA, once used for ongoing collection, must be described as best-effort scheduled archive continuity, not strict sensor-grade 15-minute cadence.
- This note does not validate local 100m WBGT prediction.
- This note does not validate a risk map.
```

---

## 9. Storage and Git hygiene

The snapshot CSVs are large local formal inputs and should not be committed to Git by default:

```text
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419.csv
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_hourly.csv
```

Do not commit:

```text
*.tif
*.tiff
data/solweig/
data/rasters/
data/archive/
raw archive dumps
large forecast CSV
large OOF prediction CSV
h10_inputs/*.csv
diagnostics_inputs/*.csv
```

Small evidence artifacts may be committed after review:

```text
outputs/v11_beta_formal/diagnostics/*.md
outputs/v11_beta_formal/diagnostics/*.json
outputs/v11_beta_formal/diagnostics/row_attrition_diagnostic.csv
outputs/v11_beta_formal/diagnostics/event_counts_by_day.csv
outputs/v11_beta_formal/diagnostics/event_counts_by_station.csv
outputs/v11_beta_formal/h10/h10_formal_combined_evidence.md
outputs/v11_beta_formal/h10/h10_formal_combined_evidence.json
bootstrap / threshold summary CSVs if size-controlled
```

---

## Appendix A. Execution log and bugs encountered

### A1. `wmic` filename bug

The freeze batch used `wmic` for timestamp creation. `wmic` was unavailable on the current Windows setup, causing malformed filenames containing `~0,8`.

Impact:

```text
Data content was not affected.
Filenames were unstable and required manual rename.
```

Mitigation:

```text
Files were renamed to stable 20260524_40419 names.
```

Recommended patch:

```text
Replace wmic timestamp logic with PowerShell Get-Date.
```

### A2. Windows CMD rename issue

The malformed filenames contained `~` and `,`, causing `ren` command syntax issues.

Mitigation:

```text
Use quoted move / PowerShell Rename-Item -LiteralPath for future unusual filenames.
```

### A3. Diagnostics schema issue

`v11_formal_archive_diagnostics.py` initially failed with:

```text
Could not infer timestamp/station columns
```

The snapshot used:

```text
station_id
timestamp_sgt
timestamp_utc
```

The diagnostics script did not infer `timestamp_sgt`.

Mitigation:

```text
Created diagnostics-only input aliases with station/timestamp/valid_timestamp fields.
Original snapshots were not modified.
```

Recommended patch:

```text
Add timestamp_sgt and station_id support directly to normalize().
```

### A4. Stale CV split issue

The baseline script defaulted to:

```text
data/calibration/v11/v11_cv_splits.csv
```

when `cv_splits_csv` was absent from config. This file belonged to the older 5,724-row pre-formal analytic set.

Initial symptom:

```text
all_stations / no_S142 15-min OOF predictions:
  prediction non-null = 5,724
  stations with prediction = 4
  valid stations = S124, S125, S126, S127
```

Root cause:

```text
Old row_id-based CV split only covered the pre-formal analytic subset.
```

Mitigation:

```text
Set cv_splits_csv in formal configs to a deliberately non-existent sentinel path:
outputs/v11_beta_formal/_no_cv_splits_use_auto_loso.csv
```

This forced `splits=None` and made the baseline script auto-generate LOSO folds from the frozen dataframe.

After fix:

```text
all_stations prediction non-null = 40,389 / 40,389, 27 stations
no_S142 prediction non-null = 38,893 / 38,893, 26 stations
hourly_mean / hourly_max prediction non-null = 10,473 / 10,473, 27 stations
```

### A5. Official H10 script schema issue

`v11_formal_h10_identity_check.py` initially failed to find the OOF prediction column because the actual column was:

```text
prediction_wbgt_c
```

It then compared predictions successfully after aliasing but failed metrics grouping with:

```text
n_metric_groups_checked = 0
```

Mitigation:

```text
Generated a schema-robust combined H10 evidence file directly from current metrics and OOF schema.
```

Formal H10 evidence result:

```text
Status: PASS
M5/M6/M7 metrics and full-length LOSO OOF predictions are identical to 6 decimal places across all formal framings.
```

Recommended patch:

```text
Update v11_formal_h10_identity_check.py to support prediction_wbgt_c and full model names:
M5_v10_morphology_ridge
M6_v10_overhead_ridge
M7_compact_weather_ridge
```

---

## Appendix B. Current evidence artifacts

Diagnostics outputs:

```text
outputs/v11_beta_formal/diagnostics/archive_health_summary.json
outputs/v11_beta_formal/diagnostics/event_counts_by_day.csv
outputs/v11_beta_formal/diagnostics/event_counts_by_station.csv
outputs/v11_beta_formal/diagnostics/station_day_completeness.csv
outputs/v11_beta_formal/diagnostics/row_attrition_diagnostic.csv
outputs/v11_beta_formal/diagnostics/timestamp_cadence_diagnostic.csv
outputs/v11_beta_formal/diagnostics/OpenHeat_17d_archive_diagnostics_summary.md
```

H10 evidence:

```text
outputs/v11_beta_formal/h10/h10_formal_combined_evidence.md
outputs/v11_beta_formal/h10/h10_formal_combined_evidence.json
```
