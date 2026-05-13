#!/usr/bin/env python
"""OpenHeat v1.1-β.1 fourth audit (4.4): threshold scan with 4 operating points.

Resolves friend-audit point 4.4 from the fourth audit: the v2.1 hourly_max
M7 LOSO ≥31 F1 = 0.639 number is a fixed-threshold result (predicted hourly
WBGT ≥ 31°C → predicted positive). For dissertation operational chapter
claims, we should additionally report:
  (a) fixed_31:    pred ≥ 31°C → flag       (current canonical)
  (b) best_F1:     scan threshold, pick θ that maximizes F1
  (c) recall_90:   threshold giving recall ≥ 0.90 with maximum precision
  (d) precision_70: threshold giving precision ≥ 0.70 with maximum recall

These four points let downstream readers / dissertation reviewers make
their own precision-recall trade-off rather than accept whatever F1-maximising
operating point happens to look best.

USAGE:
    python scripts/v11_beta_threshold_scan.py
        [--config configs/v11/v11_beta_calibration_config_v091_hourly_max.json]
        [--target-event-c 31]
        [--scan-min 27.0] [--scan-max 34.0] [--scan-step 0.05]
        [--models M5_v10_morphology_ridge,M7_compact_weather_ridge,M4_inertia_ridge]

OUTPUTS (under output_dir):
    v11_beta_threshold_scan_full.csv      — all (model, threshold) rows
    v11_beta_threshold_operating_points.csv  — 4 operating points per model
    v11_beta_threshold_scan_report.md     — markdown summary

Reads OOF predictions from the config's output_dir / output_dir_suffix /
v11_beta_oof_predictions.csv. Defaults to the hourly_max config (the
operational primary target after v2.1 §4.4).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_y_col(preds: pd.DataFrame, hint: str | None = None) -> str:
    if hint and hint in preds.columns:
        return hint
    for c in ["official_wbgt_c_max", "official_wbgt_c_p90",
              "official_wbgt_c_mean", "official_wbgt_c"]:
        if c in preds.columns:
            return c
    for c in preds.columns:
        if c.startswith("official_wbgt"):
            return c
    raise SystemExit("[ERROR] cannot identify target column")


def confusion(y_true_event: np.ndarray, y_pred_event: np.ndarray) -> dict:
    """Binary classification metrics for two boolean arrays of equal length."""
    tp = int(np.sum(y_true_event & y_pred_event))
    fp = int(np.sum(~y_true_event & y_pred_event))
    fn = int(np.sum(y_true_event & ~y_pred_event))
    tn = int(np.sum(~y_true_event & ~y_pred_event))
    p = tp + fp
    n_pos = tp + fn
    precision = tp / p if p > 0 else float("nan")
    recall = tp / n_pos if n_pos > 0 else float("nan")
    if not np.isnan(precision) and not np.isnan(recall) and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = float("nan")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1,
            "n_pos": n_pos, "n_pred_pos": p}


def scan_thresholds(y_true: np.ndarray, y_pred: np.ndarray,
                    event_c: float, scan_min: float, scan_max: float,
                    scan_step: float) -> pd.DataFrame:
    """Sweep predicted-WBGT threshold; classify y_true at fixed event_c."""
    y_true_event = y_true >= event_c
    rows = []
    thresholds = np.arange(scan_min, scan_max + 1e-9, scan_step)
    for thr in thresholds:
        y_pred_event = y_pred >= thr
        m = confusion(y_true_event, y_pred_event)
        rows.append({
            "threshold_c": float(round(thr, 4)),
            **m,
        })
    return pd.DataFrame(rows)


def pick_operating_points(scan: pd.DataFrame, event_c: float) -> dict:
    """4 operating points from the scan."""
    out = {}

    # (a) fixed_31 (or whatever event_c is) — predicted threshold = event threshold
    fixed_row = scan.iloc[(scan["threshold_c"] - event_c).abs().argsort()].iloc[0]
    out[f"fixed_{int(event_c)}"] = fixed_row.to_dict()

    # (b) best F1
    valid = scan[scan["f1"].notna()]
    if len(valid) > 0:
        best_f1 = valid.iloc[valid["f1"].argmax()]
        out["best_F1"] = best_f1.to_dict()
    else:
        out["best_F1"] = None

    # (c) recall ≥ 0.90 with maximum precision
    rec90 = scan[(scan["recall"].notna()) & (scan["recall"] >= 0.90)]
    if len(rec90) > 0:
        rec90 = rec90[rec90["precision"].notna()]
        if len(rec90) > 0:
            out["recall_90"] = rec90.iloc[rec90["precision"].argmax()].to_dict()
        else:
            out["recall_90"] = None
    else:
        out["recall_90"] = None

    # (d) precision ≥ 0.70 with maximum recall
    pre70 = scan[(scan["precision"].notna()) & (scan["precision"] >= 0.70)]
    if len(pre70) > 0:
        pre70 = pre70[pre70["recall"].notna()]
        if len(pre70) > 0:
            out["precision_70"] = pre70.iloc[pre70["recall"].argmax()].to_dict()
        else:
            out["precision_70"] = None
    else:
        out["precision_70"] = None

    return out


def operating_points_to_rows(points: dict, model: str, dataset: str) -> list[dict]:
    rows = []
    for op_name, row in points.items():
        if row is None:
            rows.append({"dataset": dataset, "model": model,
                         "operating_point": op_name, "available": False,
                         "threshold_c": None, "precision": None, "recall": None,
                         "f1": None, "tp": None, "fp": None, "fn": None})
        else:
            rows.append({
                "dataset": dataset, "model": model,
                "operating_point": op_name, "available": True,
                "threshold_c": row["threshold_c"],
                "precision": row["precision"], "recall": row["recall"], "f1": row["f1"],
                "tp": row["tp"], "fp": row["fp"], "fn": row["fn"],
            })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Threshold scan with 4 operating points (fourth audit, 4.4)")
    ap.add_argument("--config",
                    default="configs/v11/v11_beta_calibration_config_v091_hourly_max.json")
    ap.add_argument("--target-event-c", type=float, default=31.0,
                    help="WBGT threshold defining the binary event (default 31°C)")
    ap.add_argument("--scan-min", type=float, default=27.0)
    ap.add_argument("--scan-max", type=float, default=34.0)
    ap.add_argument("--scan-step", type=float, default=0.05)
    ap.add_argument("--models", default="M3_weather_ridge,M4_inertia_ridge,"
                                        "M5_v10_morphology_ridge,M7_compact_weather_ridge",
                    help="comma-separated models to scan")
    ap.add_argument("--cv-scheme", default="loso",
                    help="restrict to one CV scheme (default loso)")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"[ERROR] config not found: {cfg_path}", file=sys.stderr)
        return 2
    cfg = read_json(cfg_path)

    out_dir = Path(cfg["paths"]["output_dir"])
    suffix = cfg.get("data_filters", {}).get("output_dir_suffix", "")
    if suffix:
        out_dir = out_dir / suffix
    preds_path = out_dir / "v11_beta_oof_predictions.csv"
    if not preds_path.exists():
        print(f"[ERROR] OOF predictions not found: {preds_path}", file=sys.stderr)
        print("        Run v11_beta_calibration_baselines.py with this config first.")
        return 2

    print(f"[load] {preds_path}")
    preds = pd.read_csv(preds_path)
    if "cv_scheme" in preds.columns:
        preds = preds[preds["cv_scheme"] == args.cv_scheme].copy()
    target_hint = cfg.get("model", {}).get("target_col")
    y_col = find_y_col(preds, hint=target_hint)

    requested_models = [m.strip() for m in args.models.split(",") if m.strip()]
    available_models = preds["model"].unique().tolist()
    models = [m for m in requested_models if m in available_models]
    if not models:
        print(f"[ERROR] none of {requested_models} present in OOF "
              f"(have: {available_models})", file=sys.stderr)
        return 3

    dataset_label = suffix or "all"
    print(f"[scan]  dataset={dataset_label}  target={y_col}  event≥{args.target_event_c}°C")
    print(f"        models: {models}")
    print(f"        threshold sweep: [{args.scan_min}, {args.scan_max}] step {args.scan_step}")
    print()

    full_rows = []
    operating_rows = []

    for model in models:
        sub = preds[preds["model"] == model].copy()
        sub = sub[sub["prediction_wbgt_c"].notna() & sub[y_col].notna()]
        if len(sub) == 0:
            print(f"  [{model}] no usable rows; skipping")
            continue
        y_true = pd.to_numeric(sub[y_col], errors="coerce").to_numpy()
        y_pred = pd.to_numeric(sub["prediction_wbgt_c"], errors="coerce").to_numpy()

        scan = scan_thresholds(y_true, y_pred,
                               event_c=args.target_event_c,
                               scan_min=args.scan_min,
                               scan_max=args.scan_max,
                               scan_step=args.scan_step)
        scan["model"] = model
        scan["dataset"] = dataset_label
        scan["event_threshold_c"] = args.target_event_c
        full_rows.append(scan)

        n_pos = int(scan.iloc[0]["n_pos"])
        points = pick_operating_points(scan, event_c=args.target_event_c)
        operating_rows.extend(operating_points_to_rows(points, model, dataset_label))

        print(f"  [{model}] n={len(sub)}, n_pos(≥{args.target_event_c})={n_pos}")
        for op_name, row in points.items():
            if row is None:
                print(f"     {op_name:>14s}: not achievable in scan range")
            else:
                print(f"     {op_name:>14s}: thr={row['threshold_c']:>6.2f}°C  "
                      f"P={row['precision']:.3f}  R={row['recall']:.3f}  "
                      f"F1={row['f1']:.3f}  (TP={row['tp']}, FP={row['fp']}, FN={row['fn']})")

    if not full_rows:
        print("[ERROR] no models produced output", file=sys.stderr)
        return 4

    full_df = pd.concat(full_rows, ignore_index=True)
    op_df = pd.DataFrame(operating_rows)

    full_path = out_dir / "v11_beta_threshold_scan_full.csv"
    op_path = out_dir / "v11_beta_threshold_operating_points.csv"
    md_path = out_dir / "v11_beta_threshold_scan_report.md"

    cols_order = ["dataset", "model", "event_threshold_c", "threshold_c",
                  "precision", "recall", "f1", "tp", "fp", "fn", "tn",
                  "n_pos", "n_pred_pos"]
    full_df = full_df[[c for c in cols_order if c in full_df.columns]]

    full_df.to_csv(full_path, index=False)
    op_df.to_csv(op_path, index=False)

    # markdown report
    lines = [
        f"# v11-β.1 threshold scan report",
        f"",
        f"- Config: `{cfg_path}`",
        f"- Predictions: `{preds_path}`",
        f"- Target column: `{y_col}`",
        f"- Event threshold: ≥ {args.target_event_c}°C",
        f"- CV scheme: {args.cv_scheme}",
        f"- Threshold sweep: [{args.scan_min}, {args.scan_max}] step {args.scan_step}",
        f"",
        f"## Operating points (4 per model)",
        f"",
        f"| dataset | model | operating_point | thr (°C) | P | R | F1 | TP | FP | FN |",
        f"|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in op_df.iterrows():
        if r["available"]:
            lines.append(
                f"| {r['dataset']} | {r['model']} | {r['operating_point']} | "
                f"{r['threshold_c']:.2f} | "
                f"{r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} | "
                f"{int(r['tp'])} | {int(r['fp'])} | {int(r['fn'])} |"
            )
        else:
            lines.append(
                f"| {r['dataset']} | {r['model']} | {r['operating_point']} | "
                f"— | — | — | — | — | — | — |"
            )
    lines.append("")
    lines.append(f"## Notes")
    lines.append(f"")
    lines.append(f"- `fixed_{int(args.target_event_c)}` is the canonical operational "
                 f"semantics: predicted WBGT ≥ {args.target_event_c}°C "
                 f"→ flag the hour. No threshold tuning required at deployment.")
    lines.append(f"- `best_F1` is post-hoc; report it as a tuned upper bound, "
                 f"not the operational target.")
    lines.append(f"- `recall_90` and `precision_70` answer 'how high can the other "
                 f"metric go if I commit to this floor'.")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print()
    print(f"[write] {full_path}  ({len(full_df)} rows)")
    print(f"[write] {op_path}  ({len(op_df)} rows)")
    print(f"[write] {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
