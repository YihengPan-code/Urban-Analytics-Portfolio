# OpenHeat v1.1-beta Formal Findings Report — 17.78d Frozen Snapshot

**Document date:** 2026-05-24  
**Project:** OpenHeat-ToaPayoh  
**Repo path:** `Urban-Analytics-Portfolio/06-openheat_grid`  
**Status:** v1.1-beta-formal findings report draft  
**Scope:** System A formal calibration closeout on a frozen 17.78-day archive  
**Not scope:** ML residual learning, SOLWEIG, local 100m WBGT prediction, risk map, formula replacement

---

## 0. Executive summary

The v1.1-beta-formal run closes out the current System A archive-calibration lane on a frozen 17.78-day station-weather archive.

The formal result is mixed and scientifically useful:

```text
Confirmed:
- H10 remains confirmed: M5/M6/M7 are identical to 6 decimals in both metrics and full-length LOSO OOF predictions.
- M4 keeps a small but statistically distinguishable MAE advantage over M3 across all formal framings.
- A_all and B_retrospective remain identical, so stale-dilution remains falsified.
- S142 high-tail dominance is materially reduced; S142 contributes 35.8% of >=33C events, below the earlier 55% concern threshold.
- hourly_max remains a more defensible operational threshold target than 15-min point WBGT.

Weakened / falsified:
- The pre-formal ~0.6C calibration-floor expectation does not hold on the 17.78d snapshot.
- Formal M3/M4 MAE is closer to ~0.88-0.94C than ~0.60C.
- M7 fixed_31 F1 and recall hypotheses fail under formal evaluation.
- fixed_31 threshold performance is much weaker than the v2.2 pre-formal 4-day result.
```

Formal headline:

> v1.1-beta-formal confirms H10 and M4's small advantage, falsifies stale-dilution again, and reduces S142 high-tail dominance; however, it weakens the v2.2 pre-formal expectations around ~0.6C MAE and fixed_31 operational F1.

This is a formal evidence result, not a failure of the project. It prevents overclaiming and clarifies that System A should remain a calibrated temporal WBGT severity baseline, not a validated local 100m WBGT model.

---

## 1. Scope and non-goals

### 1.1 This report covers

```text
- Frozen 17.78-day v1.1-beta-formal snapshot.
- M0-M7 calibration ladder on all_stations, no_S142, hourly_mean, hourly_max.
- A/B/C/D ablation.
- M4-M3 station-grouped bootstrap.
- Threshold scan at fixed_31, best_F1, recall_90, precision_70.
- H10 strict identity check.
- Archive quality, row attrition, event distribution, S142 contribution.
```

### 1.2 This report does not cover

```text
- New WBGT formula replacement.
- PyWBGT / Liljegren formula audit.
- ML residual learning.
- SOLWEIG / ΔTmrt / surrogate modeling.
- WBGT-gated local radiative hazard score.
- Exposure / vulnerability / risk map.
- Validated local 100m WBGT prediction.
```

---

## 2. Formal snapshot and archive diagnostics

### 2.1 Snapshot files

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

### 2.2 Archive health

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

### 2.3 Row attrition

| Diagnostic | Rows |
|---|---:|
| total_rows | 40,419 |
| retrospective_eligible_rows | 40,419 |
| official_wbgt_c_non_null | 40,389 |
| official_wbgt_c_missing | 30 |
| wbgt_proxy_v09_c_non_null | 40,419 |
| wbgt_proxy_v09_c_missing | 0 |
| target_and_proxy_non_null | 40,389 |

Interpretation:

```text
Row attrition is negligible: only 30 official WBGT values are missing.
Formal MAE degradation is not explained by target/proxy missingness.
```

### 2.4 Event totals

```text
>=31C rows = 2,844
>=33C rows = 212
```

### 2.5 S142 contribution

```text
S142 rows = 1,496
S142 max_wbgt = 34.4C
S142 ge31 = 257
S142 ge33 = 76
```

Shares:

```text
S142 >=31C share = 257 / 2,844 = 9.0%
S142 >=33C share = 76 / 212 = 35.8%
```

Interpretation:

```text
S142 remains the largest single high-tail station, but no longer dominates >=33C events above the earlier 55% concern threshold.
```

---

## 3. Formal run matrix

The final formal matrix used:

| Framing | Input | Target | Rows used |
|---|---|---|---:|
| all_stations | frozen v091 15-min | official_wbgt_c | 40,389 analytic rows |
| no_S142 | frozen v091 15-min | official_wbgt_c | 38,893 analytic rows |
| hourly_mean | frozen hourly | official_wbgt_c_mean | 10,473 rows |
| hourly_max | frozen hourly | official_wbgt_c_max | 10,473 rows |
| ablation_A_all | frozen v091 15-min | official_wbgt_c | 40,389 rows |
| ablation_B_retrospective | frozen v091 15-min | official_wbgt_c | 40,389 rows |
| ablation_C_fresh_v11 | frozen v091 15-min | official_wbgt_c | 35,017 rows |
| ablation_D_migrated | frozen v091 15-min | official_wbgt_c | 5,372 rows |

All formal outputs were isolated under:

```text
outputs/v11_beta_formal/
```

---

## 4. Baseline M0-M7 results

### 4.1 Key LOSO MAE table

| Framing | M0 | M1 | M1b | M3 | M4 | M5/M6/M7 | Best MAE |
|---|---:|---:|---:|---:|---:|---:|---|
| all_stations | 1.273 | 1.191 | 1.010 | 0.933 | 0.917 | 0.936 | M4 |
| no_S142 | n/a | n/a | n/a | 0.923 | 0.908 | 0.927 | M4 |
| hourly_mean | 1.255 | 1.164 | 0.973 | 0.892 | 0.878 | 0.895 | M4 |
| hourly_max | 1.490 | 1.348 | 1.025 | 0.945 | 0.937 | 0.954 | M4 |

Notes:

```text
- M4 is the best regression model in all four formal framings.
- M4's improvement over M3 is small, not transformative.
- Formal MAE is materially worse than v2.2 pre-formal results.
```

### 4.2 Practical calibration-floor hypothesis

The v2.2 pre-formal report expected hourly M3/M4 MAE near ~0.6C. The formal result does not reproduce this:

```text
hourly_mean:
  M3 = 0.891813
  M4 = 0.877568

hourly_max:
  M3 = 0.944512
  M4 = 0.936526
```

Interpretation:

```text
The formal 17.78-day snapshot weakens or falsifies the ~0.6C calibration-floor expectation under the current System A setup.
```

This should not be framed as model collapse. Instead:

```text
The longer formal snapshot appears to include more complex fresh-v11 regimes than the pre-formal 4-day archive, and the current ridge calibration does not maintain ~0.6C MAE across that broader regime mix.
```

---

## 5. H10 strict identity result

H10 formal combined evidence:

```text
Status: PASS
Decimal criterion: 6
```

The check covered:

```text
all_stations:
  M5/M6/M7 OOF rows per model = 40,389

no_S142:
  M5/M6/M7 OOF rows per model = 38,893

hourly_mean:
  M5/M6/M7 OOF rows per model = 10,473

hourly_max:
  M5/M6/M7 OOF rows per model = 10,473
```

All checked metrics match to 6 decimal places:

```text
mae, rmse, bias, r2
```

All full-length LOSO OOF predictions match to 6 decimal places:

```text
nonzero_after_round6 = 0 for all M5/M6/M7 pairwise comparisons
```

Interpretation:

```text
H10 remains confirmed under the 17.78-day formal snapshot.
Morphology / overhead calibration remains structurally unidentifiable under the current NEA station network and station-level ridge/imputer pipeline.
```

Boundary:

```text
This does not mean urban morphology has no physical effect.
It means current station-level System A calibration cannot identify morphology / overhead effects.
```

---

## 6. M4-M3 bootstrap result

Manual station-grouped bootstrap, 5,000 iterations, after stale CV split fix:

| Dataset | n_folds | n_obs | M3 MAE | M4 MAE | M4-M3 delta | 95% CI | Excludes 0 |
|---|---:|---:|---:|---:|---:|---|---|
| all_stations | 27 | 40,389 | 0.933191 | 0.916754 | -0.016445 | [-0.020042, -0.012794] | True |
| no_S142 | 26 | 38,893 | 0.923450 | 0.907635 | -0.015824 | [-0.019659, -0.012054] | True |
| hourly_mean | 27 | 10,473 | 0.891813 | 0.877568 | -0.014251 | [-0.018530, -0.010158] | True |
| hourly_max | 27 | 10,473 | 0.944512 | 0.936526 | -0.007992 | [-0.012264, -0.003787] | True |

Interpretation:

```text
M4 thermal-inertia features retain a statistically distinguishable advantage over M3 across all four formal framings.
```

Practical caveat:

```text
The effect size is small: roughly 0.008-0.016C MAE improvement.
M4 should be retained as the physics-first primary baseline, but not oversold as a major breakthrough.
```

When reporting p-values, do not write `p = 0`. Because bootstrap resolution is finite, write:

```text
p < 0.001 under 5,000-iteration bootstrap resolution.
```

---

## 7. Threshold scan result

### 7.1 15-min all_stations threshold scan

Fixed 31C threshold:

| Model | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| M3 | 0.686 | 0.049 | 0.092 | 140 | 64 | 2704 |
| M4 | 0.647 | 0.076 | 0.136 | 216 | 118 | 2628 |
| M7 | 0.640 | 0.057 | 0.105 | 162 | 91 | 2682 |

Interpretation:

```text
15-min fixed_31 evaluation has extremely low recall and is not suitable as the operational warning primary.
```

Best-F1 thresholds:

```text
M3 best_F1: threshold=29.95C, F1=0.476
M4 best_F1: threshold=29.85C, F1=0.493
M7 best_F1: threshold=29.50C, F1=0.480
```

### 7.2 Hourly-max threshold scan

Fixed 31C threshold:

| Model | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| M3 | 0.771 | 0.262 | 0.391 | 313 | 93 | 883 |
| M4 | 0.763 | 0.302 | 0.433 | 361 | 112 | 835 |
| M7 | 0.788 | 0.270 | 0.402 | 323 | 87 | 873 |

Interpretation:

```text
hourly_max remains much more defensible than 15-min point WBGT for operational threshold evaluation.
However, fixed_31 recall is limited under the formal snapshot.
```

Best-F1 thresholds:

```text
M3 best_F1: threshold=29.80C, F1=0.607
M4 best_F1: threshold=29.35C, F1=0.597
M7 best_F1: threshold=29.40C, F1=0.600
```

Precision-70 operating point:

```text
M4 precision_70: threshold=30.75C, P=0.701, R=0.431, F1=0.534
```

Interpretation:

```text
Retrospective tuned thresholds can recover F1 around 0.60, but require decision thresholds around 29.3-29.8C. These should be reported as retrospective operating-point diagnostics, not deployment thresholds.
```

### 7.3 Operational implication

The v2.2 pre-formal claim that hourly_max + fixed_31 could achieve F1 around ~0.63 does not hold in the 17.78-day formal snapshot.

Updated wording:

```text
M4 + hourly_max + fixed_31 remains the most defensible physics-first operational baseline, but its recall is limited under the formal snapshot. M7 remains a precision-oriented compact alternative, not a superior all-around warning model.
```

---

## 8. Ablation result

Formal ablation row counts:

```text
A_all: 40,389
B_retrospective: 40,389
C_fresh_v11: 35,017
D_migrated: 5,372
```

LOSO MAE pivot:

| Model | A_all | B_retrospective | C_fresh_v11 | D_migrated |
|---|---:|---:|---:|---:|
| M0_raw_proxy | 1.273 | 1.273 | 1.262 | 1.349 |
| M1_global_bias | 1.191 | 1.191 | 1.183 | 1.238 |
| M1b_period_bias | 1.010 | 1.010 | 1.025 | 0.864 |
| M3_weather_ridge | 0.933 | 0.933 | 0.919 | 0.698 |
| M4_inertia_ridge | 0.917 | 0.917 | 0.899 | 0.679 |
| M5_v10_morphology_ridge | 0.936 | 0.936 | 0.935 | 0.728 |

### 8.1 Stale-dilution remains falsified

A_all and B_retrospective are identical:

```text
A_all M3 = 0.933
B_retrospective M3 = 0.933

A_all M4 = 0.917
B_retrospective M4 = 0.917
```

Interpretation:

```text
Stale-dilution remains falsified in the formal snapshot.
The collector's original pair_used_for_calibration / issue-freshness distinction is not the source of MAE degradation.
```

### 8.2 Fresh-v11 rows are harder than migrated rows

```text
C_fresh_v11 M4 = 0.899
D_migrated M4 = 0.679
```

Interpretation:

```text
Formal performance degradation is not caused by migrated old rows.
The fresh-v11 subset is substantially harder, suggesting regime complexity / recent weather distribution / station-specific high-tail behavior as more plausible sources.
```

---

## 9. Formal hypotheses status

| ID | Hypothesis | Formal result | Status |
|---|---|---|---|
| H0 | stale-dilution hypothesis is false | A_all == B_retrospective | PASS |
| H1 | M0 bias remains in previous structural underprediction range | formal bias varies by framing; all/fresh weaker than prior expectation | MIXED / WEAKENED |
| H2 | M3 LOSO MAE remains in [0.55, 0.70]C | M3 ~= 0.89-0.94 for core formal framings | FAIL |
| H3 | M4-M3 statistically distinguishable but practical-small | all four CIs exclude 0; effect 0.008-0.016C | PASS |
| H4 | M1b vs M3 gap >= 0.20C | formal gap is much smaller | FAIL |
| H5 | S142 >=33 share <=55% or confirmed outlier | S142 share = 35.8% | PASS |
| H6 / H10 | M5/M6/M7 identity persists | metrics + full OOF identical to 6 decimals | PASS |
| H7 | hourly_max M7 fixed_31 F1 >=0.55 | observed M7 F1=0.402 | FAIL |
| H8 | hourly_mean M3 near v0.9 by <=0.05C | hourly_mean M3=0.892 | FAIL |
| H9 | M7 hourly_max fixed_31 precision >=0.65 and recall >=0.50 | precision=0.788 pass; recall=0.270 fail | FAIL |
| H11 | M4 hourly_max recall_90 threshold remains around previous band | threshold=28.7C | WEAKENED / BELOW PRIOR BAND |

---

## 10. Interpretation and claim boundary

### 10.1 What is confirmed

```text
- The archive is healthy enough for formal closeout.
- H10 remains confirmed.
- M4 has a small but statistically distinguishable advantage over M3.
- hourly_max remains better than 15-min for threshold evaluation.
- stale-dilution remains falsified.
- S142 high-tail dominance is materially reduced.
```

### 10.2 What is weakened

```text
- The ~0.6C practical calibration-floor expectation does not hold on the formal snapshot.
- fixed_31 operational F1 is weaker than v2.2 pre-formal.
- M7 does not meet the formal fixed_31 recall/F1 hypotheses.
- M1b's advantage over simple bias correction is weaker than expected.
```

### 10.3 What should not be claimed

Do not claim:

```text
validated 100m local WBGT prediction
real-time operational warning system
risk map
ML readiness
morphology has no physical effect
formal pass confirms all v2.2 expectations
```

Allowed claim:

```text
The v1.1-beta-formal snapshot provides a reproducible System A evidence packet. It confirms the station-network limitation for morphology/overhead calibration and preserves a small M4 inertia advantage, while falsifying the more optimistic pre-formal MAE and fixed-threshold performance expectations.
```

---

## 11. Impact on next development path

### 11.1 Do not start ML yet

The formal result weakens the pre-formal MAE and threshold-performance assumptions. ML residual learning should remain deferred until:

```text
- formal diagnostics are fully documented;
- formula audit is complete;
- 30-day archive gates are reassessed;
- target / validation design is explicit.
```

### 11.2 Keep System A as temporal WBGT severity baseline

System A remains useful, but its claim boundary should be narrower:

```text
System A = calibrated temporal WBGT severity baseline.
Not a validated local 100m WBGT model.
```

### 11.3 v1.2 architecture remains correct

Because morphology/overhead remains unidentifiable in station-level WBGT calibration, v1.2 should not try to force morphology into local WBGT calibration.

Correct path:

```text
SOLWEIG-derived ΔTmrt_p90 / M_rad
→ surrogate emulator
→ WBGT-gated local radiative hazard score
```

Not:

```text
cell_wbgt = System A + morphology coefficient
```

### 11.4 Formula audit becomes more important

The v09 proxy / System A formula audit should be prioritized as a companion, not as retroactive recalibration.

Reason:

```text
formal MAE and fixed-threshold weakness may partly reflect simplified WBGT proxy / globe-temperature assumptions.
```

---

## 12. Reproducibility and key artifacts

### 12.1 Inputs

```text
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419.csv
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_hourly.csv
```

### 12.2 Outputs

```text
outputs/v11_beta_formal/all_stations/
outputs/v11_beta_formal/no_S142/
outputs/v11_beta_formal/hourly_mean/
outputs/v11_beta_formal/hourly_max/
outputs/v11_beta_formal/diagnostics/
outputs/v11_beta_formal/h10/
outputs/v11_beta_formal/bootstrap_M4_minus_M3_manual_station_grouped.csv
outputs/v11_beta_formal/v11_beta_ablation_loso_mae_pivot.csv
outputs/v11_beta_formal/v11_beta_ablation_summary.csv
```

### 12.3 Important config choices

Formal configs were patched to include:

```text
output_dir = outputs/v11_beta_formal
cv_splits_csv = outputs/v11_beta_formal/_no_cv_splits_use_auto_loso.csv
```

The `cv_splits_csv` path is intentionally non-existent, forcing the baseline script to use auto-generated LOSO / time-block folds from the frozen dataframe rather than stale pre-formal `row_id` splits.

---

## Appendix A. Execution log and bug record

### A1. Freeze filename bug

Problem:

```text
wmic was unavailable on the current Windows system.
The freeze script produced malformed names containing ~0,8.
```

Fix:

```text
Manual rename to stable 20260524_40419 snapshot names.
```

Recommended patch:

```text
Replace wmic timestamp logic with PowerShell Get-Date.
```

### A2. CMD rename issue

Problem:

```text
The malformed filenames contained ~ and comma, causing Windows ren syntax issues.
```

Fix:

```text
Use quoted move / PowerShell Rename-Item -LiteralPath for future unusual filenames.
```

### A3. Config target_col location

Problem:

```text
Initial target_col checks returned None because v11_beta_calibration_baselines.py reads cfg["model"]["target_col"].
```

Fix:

```text
Set model.target_col explicitly:
  all/no_S142 -> official_wbgt_c
  hourly_mean -> official_wbgt_c_mean
  hourly_max -> official_wbgt_c_max
```

### A4. Output hygiene

Problem:

```text
Early formal runs wrote into outputs/v11_beta_calibration, mixing pre-formal and formal artifacts.
```

Fix:

```text
Set formal config output_dir = outputs/v11_beta_formal and rerun clean outputs.
```

### A5. Stale CV split bug

Problem:

```text
v11_beta_calibration_baselines.py defaulted to data/calibration/v11/v11_cv_splits.csv when cv_splits_csv was absent.
That split file belonged to a 5,724-row pre-formal analytic set.
```

Symptom:

```text
15-min all/no_S142 OOF predictions initially covered only 5,724 rows and 4 stations: S124-S127.
```

Fix:

```text
Set cv_splits_csv to a deliberately non-existent sentinel path:
outputs/v11_beta_formal/_no_cv_splits_use_auto_loso.csv
```

Result:

```text
all_stations OOF coverage restored to 40,389 rows / 27 stations.
no_S142 OOF coverage restored to 38,893 rows / 26 stations.
```

### A6. Diagnostics schema issue

Problem:

```text
v11_formal_archive_diagnostics.py did not infer timestamp_sgt / station_id schema.
```

Fix:

```text
Created diagnostics-only aliases with timestamp / valid_timestamp / station fields.
```

Recommended patch:

```text
Update normalize() to recognize timestamp_sgt and station_id directly.
```

### A7. Official H10 script schema issue

Problem:

```text
v11_formal_h10_identity_check.py did not recognize prediction_wbgt_c and current full M5/M6/M7 model names.
```

Fix:

```text
Generated schema-robust combined H10 evidence from actual formal metrics and OOF schema.
```

Result:

```text
H10 combined evidence PASS.
```

Recommended patch:

```text
Update v11_formal_h10_identity_check.py to support:
  prediction_wbgt_c
  M5_v10_morphology_ridge
  M6_v10_overhead_ridge
  M7_compact_weather_ridge
```

### A8. Ablation description stale text

Problem:

```text
v11_beta_ablation_summary.csv description still says "All 5,723 rows" even when n_rows=40,389.
```

Impact:

```text
Numeric results are correct; description string is stale.
```

Recommended patch:

```text
Make ablation descriptions generic or dynamically include n_rows.
```

---

## Appendix B. Files not to commit

Do not commit:

```text
data/calibration/v11/snapshots/*.csv
outputs/v11_beta_formal/**/v11_beta_oof_predictions.csv
outputs/v11_beta_formal/h10_inputs/*.csv
outputs/v11_beta_formal/diagnostics_inputs/*.csv
*.tif
*.tiff
data/solweig/
data/rasters/
raw archive dumps
large forecast CSV
```

Potentially commit after review:

```text
docs/v11/OpenHeat_v11_beta_formal_run_log_20260524_CN.md
docs/v11/OpenHeat_17d_archive_quality_note_CN.md
docs/v11/OpenHeat_v11_beta_formal_findings_report_CN.md
outputs/v11_beta_formal/diagnostics/*.md
outputs/v11_beta_formal/diagnostics/*.json
outputs/v11_beta_formal/diagnostics/row_attrition_diagnostic.csv
outputs/v11_beta_formal/diagnostics/event_counts_by_day.csv
outputs/v11_beta_formal/diagnostics/event_counts_by_station.csv
outputs/v11_beta_formal/h10/h10_formal_combined_evidence.md
outputs/v11_beta_formal/h10/h10_formal_combined_evidence.json
outputs/v11_beta_formal/bootstrap_M4_minus_M3_manual_station_grouped.csv
outputs/v11_beta_formal/*threshold_operating_points.csv
outputs/v11_beta_formal/v11_beta_ablation_loso_mae_pivot.csv
```
