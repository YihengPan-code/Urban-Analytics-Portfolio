#!/usr/bin/env python
"""
OpenHeat v0.9-beta extension: decision-threshold scan for WBGT events.

This script scans model-score thresholds, e.g. M4_pred >= 29.2°C,
for detecting official WBGT >= 31°C or >= 33°C events. The threshold is
NOT a replacement for official WBGT thresholds; it is a post-hoc decision
threshold for a calibrated model whose high tail may still be compressed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


def load_config(path: str | Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def period_mask(df: pd.DataFrame, period: str) -> pd.Series:
    if period == "overall":
        return pd.Series(True, index=df.index)
    if "period_beta" in df.columns:
        p = df["period_beta"].astype(str).str.lower()
        if period == "daytime":
            return p.eq("daytime")
        if period == "nighttime":
            return p.eq("nighttime")
        if period == "peak":
            # fall back to hour filter for peak
            pass
    hour_col = None
    for c in ["hour_sgt_numeric", "hour_sgt", "hour"]:
        if c in df.columns:
            hour_col = c
            break
    if hour_col is None:
        raise KeyError("No hour column found for period filtering. Need hour_sgt_numeric/hour_sgt/hour.")
    h = pd.to_numeric(df[hour_col], errors="coerce")
    if period == "daytime":
        return (h >= 9) & (h < 18)
    if period == "peak":
        return (h >= 12) & (h < 16)
    if period == "nighttime":
        return ((h >= 0) & (h < 7)) | (h >= 20)
    raise ValueError(f"Unknown period: {period}")


def event_metrics(y_true_event: np.ndarray, y_pred_event: np.ndarray) -> Dict[str, float]:
    y_true_event = np.asarray(y_true_event, dtype=bool)
    y_pred_event = np.asarray(y_pred_event, dtype=bool)
    tp = int(np.sum(y_true_event & y_pred_event))
    fp = int(np.sum(~y_true_event & y_pred_event))
    fn = int(np.sum(y_true_event & ~y_pred_event))
    tn = int(np.sum(~y_true_event & ~y_pred_event))
    precision = tp / (tp + fp) if (tp + fp) else np.nan
    recall = tp / (tp + fn) if (tp + fn) else np.nan
    f1 = 2 * precision * recall / (precision + recall) if precision == precision and recall == recall and (precision + recall) else np.nan
    specificity = tn / (tn + fp) if (tn + fp) else np.nan
    balanced_accuracy = np.nanmean([recall, specificity]) if recall == recall or specificity == specificity else np.nan
    return {
        "n": int(len(y_true_event)),
        "event_count": int(np.sum(y_true_event)),
        "non_event_count": int(np.sum(~y_true_event)),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
        "balanced_accuracy": balanced_accuracy,
    }


def threshold_grid(min_val: float, max_val: float, step: float) -> np.ndarray:
    n = int(round((max_val - min_val) / step)) + 1
    return np.round(min_val + np.arange(n) * step, 6)


def scan_thresholds(
    pred: pd.DataFrame,
    models: List[str],
    split_types: List[str],
    periods: List[str],
    official_thresholds: List[float],
    thresholds: np.ndarray,
) -> pd.DataFrame:
    required = ["model", "split_type", "y_true", "y_pred"]
    missing = [c for c in required if c not in pred.columns]
    if missing:
        raise KeyError(f"Predictions CSV missing required columns: {missing}")

    rows = []
    for split in split_types:
        split_df = pred[pred["split_type"].astype(str).eq(split)].copy()
        if split_df.empty:
            print(f"[WARN] No rows for split_type={split}")
            continue
        for model in models:
            model_df = split_df[split_df["model"].astype(str).eq(model)].copy()
            if model_df.empty:
                print(f"[WARN] No rows for model={model}, split_type={split}")
                continue
            y_true_all = pd.to_numeric(model_df["y_true"], errors="coerce")
            y_pred_all = pd.to_numeric(model_df["y_pred"], errors="coerce")
            valid_base = y_true_all.notna() & y_pred_all.notna()
            for period in periods:
                pmask = period_mask(model_df, period)
                sub = model_df[valid_base & pmask].copy()
                if sub.empty:
                    print(f"[WARN] Empty subset: split={split}, model={model}, period={period}")
                    continue
                y_true = pd.to_numeric(sub["y_true"], errors="coerce").to_numpy()
                y_pred = pd.to_numeric(sub["y_pred"], errors="coerce").to_numpy()
                for official_thr in official_thresholds:
                    true_event = y_true >= official_thr
                    for pred_thr in thresholds:
                        pred_event = y_pred >= pred_thr
                        m = event_metrics(true_event, pred_event)
                        rows.append({
                            "split_type": split,
                            "model": model,
                            "period": period,
                            "official_event_threshold": float(official_thr),
                            "model_decision_threshold": float(pred_thr),
                            **m,
                        })
    return pd.DataFrame(rows)


def make_summary(scan: pd.DataFrame, target_recall: float, target_precision: float) -> pd.DataFrame:
    rows = []
    group_cols = ["split_type", "model", "period", "official_event_threshold"]
    for key, g in scan.groupby(group_cols, dropna=False):
        g = g.copy()
        # best F1: max F1, tie highest recall then highest precision
        best_f1 = g.sort_values(["f1", "recall", "precision"], ascending=False).head(1)
        if not best_f1.empty:
            r = best_f1.iloc[0].to_dict()
            rows.append({**dict(zip(group_cols, key)), "criterion": "best_f1", **{f"selected_{k}": v for k, v in r.items() if k not in group_cols}})
        # recall target: among thresholds with recall>=target, choose max precision then max F1
        gr = g[g["recall"] >= target_recall].sort_values(["precision", "f1"], ascending=False).head(1)
        if not gr.empty:
            r = gr.iloc[0].to_dict()
            rows.append({**dict(zip(group_cols, key)), "criterion": f"recall_ge_{target_recall}", **{f"selected_{k}": v for k, v in r.items() if k not in group_cols}})
        else:
            rows.append({**dict(zip(group_cols, key)), "criterion": f"recall_ge_{target_recall}", "note": "no_threshold_met_target"})
        # precision target: among thresholds with precision>=target, choose max recall then max F1
        gp = g[g["precision"] >= target_precision].sort_values(["recall", "f1"], ascending=False).head(1)
        if not gp.empty:
            r = gp.iloc[0].to_dict()
            rows.append({**dict(zip(group_cols, key)), "criterion": f"precision_ge_{target_precision}", **{f"selected_{k}": v for k, v in r.items() if k not in group_cols}})
        else:
            rows.append({**dict(zip(group_cols, key)), "criterion": f"precision_ge_{target_precision}", "note": "no_threshold_met_target"})
    return pd.DataFrame(rows)


def make_focus_station_timeline(pred: pd.DataFrame, summary: pd.DataFrame, focus_stations: List[str], out_dir: Path) -> Optional[Path]:
    if not focus_stations:
        return None
    # choose M3/M4 best_f1 thresholds for WBGT>=31 LOSO overall if available
    sel = summary[
        (summary["split_type"].astype(str).eq("LOSO"))
        & (summary["period"].astype(str).eq("overall"))
        & (summary["official_event_threshold"].astype(float).eq(31.0))
        & (summary["criterion"].astype(str).eq("best_f1"))
    ].copy()
    if sel.empty:
        return None
    pred2 = pred[pred["split_type"].astype(str).eq("LOSO") & pred["station_id"].astype(str).isin(focus_stations)].copy()
    if pred2.empty:
        return None
    pivot = pred2.pivot_table(
        index=["timestamp_sgt", "station_id", "station_name", "official_wbgt_c", "heat_stress_category"],
        columns="model",
        values="y_pred",
        aggfunc="first",
    ).reset_index()
    for _, row in sel.iterrows():
        model = row["model"]
        thr = row.get("selected_model_decision_threshold")
        if model in pivot.columns and thr == thr:
            pivot[f"{model}_event31_bestF1_decision"] = pivot[model] >= float(thr)
            pivot[f"{model}_decision_threshold31_bestF1"] = float(thr)
    out = out_dir / "v09_beta_threshold_scan_focus_station_timeline.csv"
    pivot.to_csv(out, index=False)
    return out


def write_report(scan: pd.DataFrame, summary: pd.DataFrame, cfg: Dict, out_dir: Path) -> Path:
    lines = []
    lines.append("# OpenHeat v0.9-beta threshold scan extension")
    lines.append("")
    lines.append("This report scans **model decision thresholds** for detecting official WBGT events. These thresholds do **not** replace official WBGT thresholds; they calibrate the score scale of each model.")
    lines.append("")
    lines.append(f"Predictions CSV: `{cfg.get('predictions_csv')}`")
    lines.append(f"Rows scanned: **{len(scan)}** threshold rows")
    lines.append(f"Target recall: **{cfg.get('target_recall')}**, target precision: **{cfg.get('target_precision')}**")
    lines.append("")
    lines.append("## Best-F1 decision thresholds for official WBGT≥31, LOSO overall")
    q = summary[
        (summary["split_type"].astype(str).eq("LOSO"))
        & (summary["period"].astype(str).eq("overall"))
        & (summary["official_event_threshold"].astype(float).eq(31.0))
        & (summary["criterion"].astype(str).eq("best_f1"))
    ].copy()
    cols = [
        "model", "selected_model_decision_threshold", "selected_precision", "selected_recall", "selected_f1", "selected_tp", "selected_fp", "selected_fn", "selected_tn",
    ]
    if not q.empty:
        lines.append(q[[c for c in cols if c in q.columns]].to_markdown(index=False))
    else:
        lines.append("No matching rows found.")
    lines.append("")
    lines.append("## Recall-target decision thresholds for official WBGT≥31, LOSO overall")
    q = summary[
        (summary["split_type"].astype(str).eq("LOSO"))
        & (summary["period"].astype(str).eq("overall"))
        & (summary["official_event_threshold"].astype(float).eq(31.0))
        & (summary["criterion"].astype(str).str.startswith("recall_ge"))
    ].copy()
    if not q.empty:
        lines.append(q[[c for c in cols + ["note"] if c in q.columns]].to_markdown(index=False))
    else:
        lines.append("No matching rows found.")
    lines.append("")
    lines.append("## Interpretation notes")
    lines.append("- A lower model decision threshold is expected if a calibrated regression model still underpredicts the high-WBGT tail.")
    lines.append("- Treat these thresholds as post-hoc detection cut-offs for the current 24h pilot archive.")
    lines.append("- Do not interpret a threshold such as `M4_pred ≥ 29°C` as a new official WBGT threshold.")
    lines.append("- WBGT≥33 results are reported for diagnostics only because the current archive has very few High events.")
    out = out_dir / "v09_beta_threshold_scan_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v09_beta_threshold_config.example.json")
    parser.add_argument("--predictions-csv", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.predictions_csv:
        cfg["predictions_csv"] = args.predictions_csv
    if args.out_dir:
        cfg["out_dir"] = args.out_dir

    pred_path = Path(cfg["predictions_csv"])
    if not pred_path.exists():
        raise FileNotFoundError(f"Predictions CSV not found: {pred_path}")
    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    pred = pd.read_csv(pred_path)
    models = cfg.get("models") or sorted(pred["model"].dropna().unique().tolist())
    split_types = cfg.get("split_types") or sorted(pred["split_type"].dropna().unique().tolist())
    periods = cfg.get("periods", ["overall", "daytime", "peak", "nighttime"])
    official_thresholds = [float(x) for x in cfg.get("event_thresholds_official", [31.0, 33.0])]
    thresholds = threshold_grid(float(cfg.get("prediction_threshold_min", 27.0)), float(cfg.get("prediction_threshold_max", 33.0)), float(cfg.get("prediction_threshold_step", 0.1)))

    scan = scan_thresholds(pred, models, split_types, periods, official_thresholds, thresholds)
    scan_out = out_dir / "v09_beta_threshold_scan_metrics.csv"
    scan.to_csv(scan_out, index=False)

    summary = make_summary(scan, float(cfg.get("target_recall", 0.6)), float(cfg.get("target_precision", 0.5)))
    summary_out = out_dir / "v09_beta_threshold_scan_summary.csv"
    summary.to_csv(summary_out, index=False)

    focus_out = make_focus_station_timeline(pred, summary, cfg.get("focus_stations", []), out_dir)
    report_out = write_report(scan, summary, cfg, out_dir)

    print("[OK] threshold scan metrics:", scan_out)
    print("[OK] threshold scan summary:", summary_out)
    if focus_out:
        print("[OK] focus station timeline:", focus_out)
    print("[OK] report:", report_out)


if __name__ == "__main__":
    main()
