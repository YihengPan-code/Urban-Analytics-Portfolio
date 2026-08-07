\# OpenHeat v1.1-beta-formal run log — 2026-05-24



\## 0. Status



This is an execution log for the v1.1-beta-formal frozen-snapshot rerun. It is not the final formal findings report.



Current status:



```text

frozen snapshot: complete

formal baseline matrix: complete

H10 full OOF identity: pass

M4-M3 bootstrap: pass

threshold scan: complete

ablation: complete

archive diagnostics: pending

formal report: pending

1\. Snapshot



Raw snapshot:



data/calibration/v11/snapshots/v11\_pairs\_14d\_formal\_20260524\_40419.csv



v091 feature snapshot:



data/calibration/v11/snapshots/v11\_pairs\_14d\_formal\_20260524\_40419\_v091.csv



Hourly snapshot:



data/calibration/v11/snapshots/v11\_pairs\_14d\_formal\_20260524\_40419\_hourly.csv



Notes:



The original freeze script used wmic for timestamp generation. wmic was unavailable on the current Windows system, causing malformed filenames using \~0,8. Files were manually renamed to stable 20260524\_40419 names.

2\. Config patch



Formal configs were patched to use frozen inputs:



all\_stations / no\_S142:

&#x20; paired\_dataset\_csv = v11\_pairs\_14d\_formal\_20260524\_40419\_v091.csv

&#x20; model.target\_col = official\_wbgt\_c



hourly\_mean / hourly\_max:

&#x20; paired\_dataset\_csv = v11\_pairs\_14d\_formal\_20260524\_40419\_hourly.csv

&#x20; model.target\_col = official\_wbgt\_c\_mean / official\_wbgt\_c\_max



Formal output directory:



outputs/v11\_beta\_formal



CV split handling:



cv\_splits\_csv = outputs/v11\_beta\_formal/\_no\_cv\_splits\_use\_auto\_loso.csv



This sentinel path intentionally does not exist, forcing v11\_beta\_calibration\_baselines.py to use auto-generated LOSO / time-block folds from the frozen dataframe.



3\. Stale CV split issue



Initial formal 15-min OOF outputs were incomplete:



all\_stations / no\_S142:

&#x20; prediction non-null = 5,724 rows

&#x20; stations with prediction = 4

&#x20; valid stations = S124, S125, S126, S127



Root cause:



v11\_beta\_calibration\_baselines.py defaulted to data/calibration/v11/v11\_cv\_splits.csv when configs did not specify cv\_splits\_csv. That file belonged to the pre-formal 5,724-row analytic set and did not cover the formal 40,389-row snapshot.



Fix:



Set cv\_splits\_csv in all four formal configs to a deliberately non-existent sentinel path. This makes the baseline script use splits=None and fall back to auto LOSO folds.



After fix:



all\_stations:

&#x20; M3/M4 prediction non-null = 40,389

&#x20; stations with prediction = 27



no\_S142:

&#x20; M3/M4 prediction non-null = 38,893

&#x20; stations with prediction = 26



hourly\_mean / hourly\_max:

&#x20; prediction non-null = 10,473

&#x20; stations with prediction = 27

4\. H10 formal result



H10 full OOF identity check passed.



M5/M6/M7 OOF predictions are identical to 6 decimals across:

\- all\_stations

\- no\_S142

\- hourly\_mean

\- hourly\_max



Raw floating differences are around 1e-11 and disappear after 6-decimal rounding.



5\. M4-M3 bootstrap



Manual station-grouped bootstrap after stale split fix:



all\_stations:

&#x20; n\_folds = 27

&#x20; n\_obs = 40,389

&#x20; M3 = 0.933191

&#x20; M4 = 0.916754

&#x20; delta = -0.016445

&#x20; 95% CI = \[-0.020042, -0.012794]



no\_S142:

&#x20; n\_folds = 26

&#x20; n\_obs = 38,893

&#x20; M3 = 0.923450

&#x20; M4 = 0.907635

&#x20; delta = -0.015824

&#x20; 95% CI = \[-0.019659, -0.012054]



hourly\_mean:

&#x20; n\_folds = 27

&#x20; n\_obs = 10,473

&#x20; M3 = 0.891813

&#x20; M4 = 0.877568

&#x20; delta = -0.014251

&#x20; 95% CI = \[-0.018530, -0.010158]



hourly\_max:

&#x20; n\_folds = 27

&#x20; n\_obs = 10,473

&#x20; M3 = 0.944512

&#x20; M4 = 0.936526

&#x20; delta = -0.007992

&#x20; 95% CI = \[-0.012264, -0.003787]



Interpretation:



M4 thermal-inertia features retain a statistically distinguishable but practically small advantage over M3.

6\. Threshold scan



Formal hourly\_max fixed\_31:



M3 fixed\_31: P=0.771, R=0.262, F1=0.391

M4 fixed\_31: P=0.763, R=0.302, F1=0.433

M7 fixed\_31: P=0.788, R=0.270, F1=0.402



Formal 15-min fixed\_31:



M3 fixed\_31: P=0.686, R=0.049, F1=0.092

M4 fixed\_31: P=0.647, R=0.076, F1=0.136

M7 fixed\_31: P=0.640, R=0.057, F1=0.105



Interpretation:



hourly\_max remains the better operational warning target than 15-min point WBGT, but fixed\_31 performance is materially weaker than v2.2 pre-formal results.

7\. Ablation



Formal ablation row counts:



A\_all: 40,389

B\_retrospective: 40,389

C\_fresh\_v11: 35,017

D\_migrated: 5,372



LOSO MAE pivot:



M3:

&#x20; A\_all = 0.933

&#x20; B\_retrospective = 0.933

&#x20; C\_fresh\_v11 = 0.919

&#x20; D\_migrated = 0.698



M4:

&#x20; A\_all = 0.917

&#x20; B\_retrospective = 0.917

&#x20; C\_fresh\_v11 = 0.899

&#x20; D\_migrated = 0.679



M5/M6/M7:

&#x20; A\_all ≈ 0.936

&#x20; B\_retrospective ≈ 0.936

&#x20; C\_fresh\_v11 ≈ 0.935

&#x20; D\_migrated ≈ 0.728



Interpretation:



A\_all and B\_retrospective remain identical, so stale-dilution remains falsified.



Fresh v11 rows are harder than migrated rows. Formal performance degradation should not be blamed on migrated rows; it likely reflects fresh archive regime complexity, recent weather distribution, station-specific high-tail behavior, or target/proxy missingness patterns.

8\. Pending



Still pending before final formal report:



archive diagnostics

row attrition diagnostic

station-day completeness

ge31 / ge33 by day

ge31 / ge33 by station

S142 high-tail contribution share

official H10 script outputs

archive quality note

formal findings report

9\. Current claim boundary



Do not claim yet:



validated 100m local WBGT

operational real-time warning system

risk map

ML readiness

final formal report



Allowed current statement:



The v1.1-beta-formal matrix has been rerun on a frozen 17d snapshot. H10 remains confirmed, M4 retains a small but statistically distinguishable advantage over M3, stale-dilution remains falsified, and hourly\_max remains the more defensible threshold target. However, the formal snapshot substantially weakens the pre-formal \~0.6°C MAE and fixed\_31 F1 expectations, pending archive diagnostics.

