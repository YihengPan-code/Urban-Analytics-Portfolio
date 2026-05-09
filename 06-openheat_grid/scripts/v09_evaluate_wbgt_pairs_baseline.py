from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from v09_common import load_config, ensure_dir, metrics, add_wbgt_categories


def classification_metrics(df: pd.DataFrame, obs_col="heat_stress_category", pred_col="wbgt_proxy_weather_only_category"):
    out = []
    for cat in ["Moderate", "High"]:
        if cat == "Moderate":
            obs_pos = df["official_wbgt_c"] >= 31
            pred_pos = df["wbgt_proxy_physics"] >= 31
        else:
            obs_pos = df["official_wbgt_c"] >= 33
            pred_pos = df["wbgt_proxy_physics"] >= 33
        tp = int((obs_pos & pred_pos).sum())
        fp = int((~obs_pos & pred_pos).sum())
        fn = int((obs_pos & ~pred_pos).sum())
        tn = int((~obs_pos & ~pred_pos).sum())
        precision = tp / (tp + fp) if (tp + fp) else np.nan
        recall = tp / (tp + fn) if (tp + fn) else np.nan
        f1 = 2 * precision * recall / (precision + recall) if precision == precision and recall == recall and (precision + recall) else np.nan
        out.append({
            "threshold": f"WBGT>={31 if cat=='Moderate' else 33}",
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1,
        })
    return pd.DataFrame(out)


def main():
    parser = argparse.ArgumentParser(description="Evaluate v0.9-alpha WBGT paired baseline.")
    parser.add_argument("--config", default="configs/v09_alpha_config.example.json")
    parser.add_argument("--pairs", default="data/calibration/v09_wbgt_station_pairs.csv")
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = ensure_dir(cfg.get("outputs_dir", "outputs/v09_alpha_calibration"))
    pairs_fp = Path(args.pairs)
    if not pairs_fp.exists():
        raise FileNotFoundError(f"Pairs CSV not found: {pairs_fp}")
    df = pd.read_csv(pairs_fp)

    if "wbgt_proxy_physics" not in df.columns:
        raise KeyError("Pairs CSV missing wbgt_proxy_physics")

    overall = pd.DataFrame([metrics(df["official_wbgt_c"], df["wbgt_proxy_physics"])] )
    overall_fp = out_dir / "v09_baseline_overall_metrics.csv"
    overall.to_csv(overall_fp, index=False)

    by_station = []
    for (sid, sname), g in df.groupby(["station_id", "station_name"], dropna=False):
        m = metrics(g["official_wbgt_c"], g["wbgt_proxy_physics"])
        m.update({"station_id": sid, "station_name": sname, "n": len(g), "obs_max": g["official_wbgt_c"].max(), "obs_mean": g["official_wbgt_c"].mean()})
        by_station.append(m)
    by_station_df = pd.DataFrame(by_station).sort_values("mae")
    by_station_fp = out_dir / "v09_baseline_metrics_by_station.csv"
    by_station_df.to_csv(by_station_fp, index=False)

    class_df = classification_metrics(df)
    class_fp = out_dir / "v09_baseline_event_detection_metrics.csv"
    class_df.to_csv(class_fp, index=False)

    # residual by hour
    df["residual_official_minus_proxy"] = df["official_wbgt_c"] - df["wbgt_proxy_physics"]
    hour_df = df.groupby("hour_sgt", as_index=False).agg(
        n=("residual_official_minus_proxy", "count"),
        residual_mean=("residual_official_minus_proxy", "mean"),
        residual_median=("residual_official_minus_proxy", "median"),
        residual_p90_abs=("residual_official_minus_proxy", lambda x: x.abs().quantile(0.9)),
        official_wbgt_mean=("official_wbgt_c", "mean"),
        proxy_wbgt_mean=("wbgt_proxy_physics", "mean"),
    )
    hour_fp = out_dir / "v09_residual_by_hour.csv"
    hour_df.to_csv(hour_fp, index=False)

    report = []
    report.append("# OpenHeat v0.9-alpha baseline WBGT calibration diagnostics")
    report.append("")
    report.append("## Overall raw physics proxy metrics")
    report.append(overall.to_string(index=False))
    report.append("")
    report.append("## Event detection")
    report.append(class_df.to_string(index=False))
    report.append("")
    report.append("## Station metrics preview")
    report.append(by_station_df.head(12).to_string(index=False))
    report.append("")
    report.append("## Residual by hour preview")
    report.append(hour_df.head(20).to_string(index=False))
    report.append("")
    report.append("## Notes")
    report.append("- These metrics evaluate the raw screening-level physics proxy against official WBGT.")
    report.append("- This is a v0.9-alpha diagnostic, not final calibration or ML validation.")
    report.append("- Use this report to decide whether v0.9-beta linear calibration and v0.9-ML residual learning are justified.")
    report_fp = out_dir / "v09_baseline_calibration_diagnostics.md"
    report_fp.write_text("\n".join(report), encoding="utf-8")

    print("[OK] Baseline evaluation complete")
    print("overall:", overall_fp)
    print("station:", by_station_fp)
    print("event:", class_fp)
    print("hour:", hour_fp)
    print("report:", report_fp)


if __name__ == "__main__":
    main()
