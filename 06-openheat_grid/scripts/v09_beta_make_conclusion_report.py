#!/usr/bin/env python
"""Generate a v0.9-beta conclusion report from calibration and threshold outputs."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def safe_read(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        print(f"[WARN] Missing file: {p}")
        return pd.DataFrame()
    return pd.read_csv(p)


def fmt(x, nd=3):
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)


def get_metric(metrics: pd.DataFrame, model: str, split="LOSO", period="overall", col="mae"):
    if metrics.empty:
        return None
    q = metrics[(metrics["model"].astype(str) == model) & (metrics["split_type"].astype(str) == split) & (metrics["period"].astype(str) == period)]
    if q.empty or col not in q.columns:
        return None
    return q.iloc[0][col]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calib-dir", default="outputs/v09_beta_calibration")
    parser.add_argument("--threshold-dir", default="outputs/v09_beta_threshold_scan")
    parser.add_argument("--out", default="outputs/v09_beta_calibration/v09_beta_conclusion_report.md")
    args = parser.parse_args()

    calib_dir = Path(args.calib_dir)
    threshold_dir = Path(args.threshold_dir)
    metrics = safe_read(calib_dir / "v09_beta_model_metrics.csv")
    events = safe_read(calib_dir / "v09_beta_event_detection_metrics.csv")
    slopes = safe_read(calib_dir / "v09_beta_linear_slope_diagnostics.csv")
    thresh_summary = safe_read(threshold_dir / "v09_beta_threshold_scan_summary.csv")

    lines = []
    lines.append("# OpenHeat v0.9-beta conclusion report")
    lines.append("")
    lines.append("## Executive conclusion")
    lines.append("")
    lines.append("v0.9-beta confirms that the raw weather-only WBGT proxy requires calibration. Ridge calibration using current weather-regime features and thermal-inertia features substantially improves LOSO-CV MAE, while direct use of the official WBGT thresholds on calibrated regression output still under-detects the high tail. Therefore, v0.9-beta should be interpreted as a strong point-prediction calibration baseline, not a finished operational alert model.")
    lines.append("")

    lines.append("## Key LOSO-CV MAE results")
    lines.append("")
    models = ["M0_raw_proxy", "M1_global_bias", "M1b_period_bias", "M2_linear_proxy", "M3_regime_current_ridge", "M4_inertia_ridge", "M5_inertia_morphology_ridge"]
    rows = []
    for m in models:
        rows.append({
            "model": m,
            "overall_mae": get_metric(metrics, m, period="overall"),
            "daytime_mae": get_metric(metrics, m, period="daytime_09_18"),
            "peak_mae": get_metric(metrics, m, period="peak_12_16"),
            "night_mae": get_metric(metrics, m, period="night_00_07_20_23"),
        })
    tab = pd.DataFrame(rows)
    if not tab.empty:
        lines.append(tab.to_markdown(index=False, floatfmt=".3f"))
    lines.append("")

    lines.append("## Event detection summary")
    lines.append("")
    if not events.empty:
        q = events[(events["split_type"].astype(str) == "LOSO") & (events["period"].astype(str) == "overall") & (events["threshold"].astype(float) == 31.0)].copy()
        cols = ["model", "tp", "fp", "fn", "tn", "precision", "recall", "f1"]
        if not q.empty:
            lines.append(q[[c for c in cols if c in q.columns]].sort_values("recall", ascending=False).to_markdown(index=False, floatfmt=".3f"))
        q33 = events[(events["split_type"].astype(str) == "LOSO") & (events["period"].astype(str) == "overall") & (events["threshold"].astype(float) == 33.0)].copy()
        if not q33.empty:
            lines.append("")
            lines.append("WBGT≥33 is reported for diagnostics only because the current archive has very few High events.")
            lines.append(q33[[c for c in cols if c in q33.columns]].sort_values("recall", ascending=False).to_markdown(index=False, floatfmt=".3f"))
    lines.append("")

    lines.append("## Linear slope diagnostic")
    lines.append("")
    if not slopes.empty:
        cols = ["split_type", "heldout_station_id", "intercept", "slope", "slope_warning"]
        lines.append(slopes[[c for c in cols if c in slopes.columns]].head(30).to_markdown(index=False, floatfmt=".3f"))
        lines.append("")
        lines.append("Large slopes indicate dynamic-range compression in the raw proxy. Linear calibration is useful diagnostically, but slope inflation makes it risky as an operational model without longer multi-day validation.")
    else:
        lines.append("Slope diagnostics not found.")
    lines.append("")

    lines.append("## Threshold-scan extension")
    lines.append("")
    if not thresh_summary.empty:
        q = thresh_summary[
            (thresh_summary["split_type"].astype(str) == "LOSO")
            & (thresh_summary["period"].astype(str) == "overall")
            & (thresh_summary["official_event_threshold"].astype(float) == 31.0)
            & (thresh_summary["criterion"].astype(str) == "best_f1")
        ]
        cols = ["model", "selected_model_decision_threshold", "selected_precision", "selected_recall", "selected_f1", "selected_tp", "selected_fp", "selected_fn"]
        if not q.empty:
            lines.append(q[[c for c in cols if c in q.columns]].to_markdown(index=False, floatfmt=".3f"))
        lines.append("")
        lines.append("These decision thresholds are calibrated cut-offs for detecting official WBGT≥31 events. They are not replacement official WBGT thresholds.")
    else:
        lines.append("Threshold scan outputs not found. Run `scripts/v09_beta_threshold_scan.py` first.")
    lines.append("")

    lines.append("## Recommended v0.9-beta model interpretation")
    lines.append("")
    lines.append("- Use **M4_inertia_ridge** as the main point-prediction calibration baseline if it performs best or near-best under LOSO-CV.")
    lines.append("- Use **M3_regime_current_ridge** as a simpler weather-regime baseline, especially if its event recall is higher.")
    lines.append("- Treat **M1_global_bias** as a demonstration of why day/night metrics are necessary; it can improve daytime errors while worsening night-time errors.")
    lines.append("- Treat **M2_linear_proxy** as a dynamic-range diagnostic, not as an operational calibration model when the slope is large.")
    lines.append("- Treat **M5_morphology** cautiously unless station morphology is representative. Toa Payoh morphology should not be interpreted as local morphology for distant all-island stations.")
    lines.append("")
    lines.append("## Next development step")
    lines.append("")
    lines.append("The next physical development step should be **v0.9-gamma SOLWEIG selected tiles**, because the current 24h archive is too small for robust tail-heavy logistic or quantile ML calibration. Threshold scan can be included as a beta extension, while logistic / quantile / conformal methods should wait until at least 14–30 days of archive data are available.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("[OK] conclusion report:", out)


if __name__ == "__main__":
    main()
