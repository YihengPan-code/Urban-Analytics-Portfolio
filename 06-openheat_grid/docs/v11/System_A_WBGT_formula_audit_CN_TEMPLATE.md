# System A WBGT formula audit — CN template

> Status: draft template. This companion audit does not retroactively replace the v1.1-beta-formal result.

## 1. Purpose

Audit whether the current System A v09 WBGT proxy formula contributes to:
- structural M0 under-prediction;
- weak fixed_31 recall;
- threshold crossing shifts around 31°C / 33°C.

## 2. Inputs

```text
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv
```

## 3. Formula variants

- existing_v09_proxy
- reconstructed_from_v09_components, if component columns exist
- Stull wet-bulb + simple-globe sensitivity variants across multiple globe coefficients
- no_radiation_sensitivity_tg_eq_tair as a labelled sensitivity baseline, not outdoor replacement

## 4. Required outputs

```text
outputs/v11_formula_audit/formula_bias_mae_rmse_table.csv
outputs/v11_formula_audit/formula_event_confusion_matrix.csv
outputs/v11_formula_audit/threshold_crossing_diff_31_33.csv
outputs/v11_formula_audit/formula_flip_summary_vs_v09.csv
outputs/v11_formula_audit/formula_bias_by_station.csv
outputs/v11_formula_audit/formula_bias_by_day.csv
outputs/v11_formula_audit/System_A_WBGT_formula_audit_report.md
```

## 5. Interpretation rules

- Do not rewrite v1.1-beta-formal silently.
- If formula sensitivity is material near 31°C / 33°C, open a formula-v2 cycle.
- Treat Liljegren/PyWBGT implementation as a separately validated path.
- Do not convert this into local 100m WBGT mapping.

## 6. Final summary placeholder

TBD after running the audit.
