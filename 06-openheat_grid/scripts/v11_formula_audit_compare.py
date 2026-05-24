#!/usr/bin/env python
"""System A WBGT formula sensitivity audit for OpenHeat v1.1-beta-formal.

Purpose
-------
This script compares the currently deployed v0.9 WBGT proxy against a small
family of transparent screening/sensitivity variants. It is a companion audit,
not a retroactive replacement of the frozen formal calibration result.

The script intentionally avoids changing the archive or calibration outputs.
It writes small summary CSV/Markdown files and, optionally, a compressed
row-level comparison table for local inspection.

Core checks
-----------
- formula bias / MAE / RMSE against official_wbgt_c
- formula score distributions
- threshold confusion matrices at >=31C and >=33C
- threshold-sweep operating points for fixed, best-F1, high-recall,
  and high-precision settings
- bias-corrected threshold confusion matrices
- additive shifts required to reach fixed thresholds or observed event counts
- threshold crossing flips versus the deployed v09 proxy
- by-station and by-day bias summaries
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_table(df: pd.DataFrame) -> str:
    """Render a small dataframe as a GitHub-style Markdown table."""
    if df.empty:
        return "_No rows._"

    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{x:.6f}")
        else:
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else str(x))

    headers = [str(c) for c in display.columns]
    rows = display.values.tolist()
    widths = [
        max(len(headers[i]), *(len(str(row[i])) for row in rows))
        for i in range(len(headers))
    ]

    header_row = "| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |"
    sep_row = "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |"
    body_rows = [
        "| " + " | ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))) + " |"
        for row in rows
    ]
    return "\n".join([header_row, sep_row, *body_rows])


def stull_wet_bulb_c(t_c: pd.Series, rh_pct: pd.Series) -> pd.Series:
    """Stull (2011) wet-bulb approximation.

    Inputs:
      t_c: air temperature in degrees Celsius
      rh_pct: relative humidity in percent, expected 0..100

    Returns:
      approximate psychrometric wet-bulb temperature in degrees Celsius.
    """
    rh = rh_pct.clip(lower=0, upper=100)
    t = t_c
    return (
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * np.power(rh, 1.5) * np.arctan(0.023101 * rh)
        - 4.686035
    )


def safe_r2(y: pd.Series, pred: pd.Series) -> float:
    mask = y.notna() & pred.notna()
    if mask.sum() < 2:
        return float("nan")
    yy = y[mask].astype(float)
    pp = pred[mask].astype(float)
    denom = float(((yy - yy.mean()) ** 2).sum())
    if denom == 0:
        return float("nan")
    return 1.0 - float(((yy - pp) ** 2).sum()) / denom


def binary_metrics(y_event: pd.Series, score_event: pd.Series) -> dict[str, Any]:
    """Return binary classification counts and rates for already-valid rows."""
    y = y_event.astype(bool)
    p = score_event.astype(bool)

    tp = int((y & p).sum())
    fp = int((~y & p).sum())
    fn = int((y & ~p).sum())
    tn = int((~y & ~p).sum())

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if precision == precision and recall == recall and (precision + recall) else float("nan")

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def threshold_metrics(y: pd.Series, score: pd.Series, event_threshold: float, score_threshold: float) -> dict[str, Any]:
    """Return threshold confusion metrics using only rows with y and score."""
    valid = y.notna() & score.notna()
    y_valid = y[valid].astype(float)
    score_valid = score[valid].astype(float)
    y_event = y_valid >= event_threshold
    score_event = score_valid >= score_threshold
    return {
        "n_obs": int(valid.sum()),
        "n_event_obs": int(y_event.sum()),
        **binary_metrics(y_event, score_event),
    }


def build_variants(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    cols = cfg["columns"]
    variants: dict[str, pd.Series] = {}

    temp_col = cols["temperature_col"]
    rh_col = cols["rh_col"]
    wind_col = cols["wind_col"]
    sw_col = cols["shortwave_col"]

    missing_core = [c for c in [temp_col, rh_col, wind_col, sw_col] if c not in df.columns]
    if missing_core:
        raise KeyError(f"Missing core weather columns required for formula variants: {missing_core}")

    t = pd.to_numeric(df[temp_col], errors="coerce")
    rh = pd.to_numeric(df[rh_col], errors="coerce")
    wind = pd.to_numeric(df[wind_col], errors="coerce")
    sw = pd.to_numeric(df[sw_col], errors="coerce")

    wetbulb_col = cols.get("stull_wetbulb_col", "wetbulb_stull_c_v09")
    if wetbulb_col in df.columns:
        twb = pd.to_numeric(df[wetbulb_col], errors="coerce")
    else:
        twb = stull_wet_bulb_c(t, rh)

    existing_col = cols.get("existing_proxy_col", "wbgt_proxy_v09_c")
    if existing_col in df.columns:
        variants["existing_v09_proxy"] = pd.to_numeric(df[existing_col], errors="coerce")

    globe_col = cols.get("globe_proxy_col", "globe_temp_proxy_v09_c")
    if globe_col in df.columns:
        tg_existing = pd.to_numeric(df[globe_col], errors="coerce")
        variants["reconstructed_from_v09_components"] = 0.7 * twb + 0.2 * tg_existing + 0.1 * t

    formula_cfg = cfg.get("formula_variants", {})
    wind_offset = float(formula_cfg.get("wind_offset", 0.25))
    min_wind = float(formula_cfg.get("min_wind_for_sqrt", 0.0))
    wind_term = np.sqrt(wind.clip(lower=min_wind) + wind_offset)

    for k in formula_cfg.get("globe_k_values", [0.0045]):
        k_float = float(k)
        tg = t + k_float * sw / wind_term
        name = f"stull_simple_globe_k{str(k_float).replace('.', 'p')}"
        variants[name] = 0.7 * twb + 0.2 * tg + 0.1 * t

    # This is not a direct-sun outdoor WBGT replacement. It is a deliberately
    # labelled no-radiation sensitivity baseline.
    variants["no_radiation_sensitivity_tg_eq_tair"] = 0.7 * twb + 0.3 * t

    out = pd.DataFrame(variants)
    return out


def formula_metrics(df: pd.DataFrame, variants: pd.DataFrame, target_col: str) -> pd.DataFrame:
    y = pd.to_numeric(df[target_col], errors="coerce")
    rows = []

    for name in variants.columns:
        p = pd.to_numeric(variants[name], errors="coerce")
        mask = y.notna() & p.notna()
        err = p[mask] - y[mask]
        rows.append({
            "formula": name,
            "n": int(mask.sum()),
            "bias_pred_minus_obs": float(err.mean()) if len(err) else float("nan"),
            "mae": float(err.abs().mean()) if len(err) else float("nan"),
            "rmse": float(np.sqrt((err ** 2).mean())) if len(err) else float("nan"),
            "r2": safe_r2(y, p),
            "pred_mean": float(p[mask].mean()) if int(mask.sum()) else float("nan"),
            "obs_mean": float(y[mask].mean()) if int(mask.sum()) else float("nan"),
        })

    return pd.DataFrame(rows).sort_values(["mae", "rmse"], na_position="last")


def distribution_summary(variants: pd.DataFrame) -> pd.DataFrame:
    """Summarise raw formula score distributions."""
    quantiles = {
        "p01": 0.01,
        "p05": 0.05,
        "p25": 0.25,
        "p50": 0.50,
        "p75": 0.75,
        "p90": 0.90,
        "p95": 0.95,
        "p99": 0.99,
    }
    rows = []
    for formula in variants.columns:
        score = pd.to_numeric(variants[formula], errors="coerce").dropna()
        row: dict[str, Any] = {"formula": formula, "n": int(len(score))}
        if score.empty:
            row.update({k: float("nan") for k in ["min", *quantiles.keys(), "max", "mean"]})
        else:
            row["min"] = float(score.min())
            for name, q in quantiles.items():
                row[name] = float(score.quantile(q))
            row["max"] = float(score.max())
            row["mean"] = float(score.mean())
        rows.append(row)

    return pd.DataFrame(rows)


def threshold_tables(df: pd.DataFrame, variants: pd.DataFrame, target_col: str, thresholds: list[float]) -> tuple[pd.DataFrame, pd.DataFrame]:
    y = pd.to_numeric(df[target_col], errors="coerce")
    rows_conf = []
    rows_flip = []

    ref = variants["existing_v09_proxy"] if "existing_v09_proxy" in variants.columns else None

    for formula in variants.columns:
        score = pd.to_numeric(variants[formula], errors="coerce")
        for thr in thresholds:
            m = threshold_metrics(y, score, thr, thr)
            rows_conf.append({
                "formula": formula,
                "event_threshold_c": thr,
                "score_threshold_c": thr,
                **m,
            })

            if ref is not None and formula != "existing_v09_proxy":
                y_event = y >= thr
                s_event = score >= thr
                ref_event = ref >= thr
                both_valid = score.notna() & ref.notna() & y.notna()
                rows_flip.append({
                    "formula": formula,
                    "reference_formula": "existing_v09_proxy",
                    "threshold_c": thr,
                    "n_valid": int(both_valid.sum()),
                    "formula_ge_ref_lt": int((both_valid & s_event & ~ref_event).sum()),
                    "formula_lt_ref_ge": int((both_valid & ~s_event & ref_event).sum()),
                    "same_classification": int((both_valid & (s_event == ref_event)).sum()),
                })

    return pd.DataFrame(rows_conf), pd.DataFrame(rows_flip)


def threshold_scan_values(start: float = 27.0, stop: float = 34.0, step: float = 0.05) -> list[float]:
    """Build inclusive score thresholds without floating point drift."""
    scale = 100
    return [x / scale for x in range(int(round(start * scale)), int(round(stop * scale)) + 1, int(round(step * scale)))]


def choose_scan_row(scan: pd.DataFrame, operating_point: str, event_threshold: float) -> dict[str, Any]:
    """Pick one operating threshold row for the named criterion."""
    missing_choice = {"threshold_c": float("nan"), "precision": float("nan"), "recall": float("nan"), "f1": float("nan"), "tp": float("nan"), "fp": float("nan"), "fn": float("nan")}
    if operating_point == f"fixed_{int(event_threshold)}":
        chosen = scan.loc[scan["threshold_c"].sub(event_threshold).abs().idxmin()]
    elif operating_point == "best_F1":
        valid = scan.dropna(subset=["f1"])
        if valid.empty:
            return missing_choice
        chosen = valid.sort_values(["f1", "recall", "precision", "threshold_c"], ascending=[False, False, False, True]).iloc[0]
    elif operating_point == "recall_90":
        valid = scan[scan["recall"] >= 0.90].dropna(subset=["recall"])
        if valid.empty:
            return missing_choice
        chosen = valid.sort_values(["precision", "f1", "threshold_c"], ascending=[False, False, False]).iloc[0]
    elif operating_point == "precision_70":
        valid = scan[scan["precision"] >= 0.70].dropna(subset=["precision"])
        if valid.empty:
            return missing_choice
        chosen = valid.sort_values(["recall", "f1", "threshold_c"], ascending=[False, False, True]).iloc[0]
    else:
        raise ValueError(f"Unknown operating point: {operating_point}")

    return {
        "threshold_c": float(chosen["threshold_c"]),
        "precision": float(chosen["precision"]) if pd.notna(chosen["precision"]) else float("nan"),
        "recall": float(chosen["recall"]) if pd.notna(chosen["recall"]) else float("nan"),
        "f1": float(chosen["f1"]) if pd.notna(chosen["f1"]) else float("nan"),
        "tp": int(chosen["tp"]),
        "fp": int(chosen["fp"]),
        "fn": int(chosen["fn"]),
    }


def threshold_operating_points(df: pd.DataFrame, variants: pd.DataFrame, target_col: str, thresholds: list[float]) -> pd.DataFrame:
    """Scan score thresholds and report selected operating points."""
    y = pd.to_numeric(df[target_col], errors="coerce")
    score_thresholds = threshold_scan_values()
    rows = []

    for formula in variants.columns:
        score = pd.to_numeric(variants[formula], errors="coerce")
        for event_threshold in thresholds:
            scan_rows = []
            for score_threshold in score_thresholds:
                m = threshold_metrics(y, score, event_threshold, score_threshold)
                scan_rows.append({
                    "threshold_c": score_threshold,
                    "precision": m["precision"],
                    "recall": m["recall"],
                    "f1": m["f1"],
                    "tp": m["tp"],
                    "fp": m["fp"],
                    "fn": m["fn"],
                })
            scan = pd.DataFrame(scan_rows)
            for operating_point in [f"fixed_{int(event_threshold)}", "best_F1", "recall_90", "precision_70"]:
                chosen = choose_scan_row(scan, operating_point, event_threshold)
                rows.append({
                    "formula": formula,
                    "event_threshold_c": event_threshold,
                    "operating_point": operating_point,
                    **chosen,
                })

    out = pd.DataFrame(rows)
    for col in ["tp", "fp", "fn"]:
        out[col] = out[col].astype("Int64")
    return out


def bias_corrected_confusion(metrics: pd.DataFrame, df: pd.DataFrame, variants: pd.DataFrame, target_col: str, thresholds: list[float]) -> pd.DataFrame:
    """Compute fixed-threshold confusion after subtracting formula bias."""
    y = pd.to_numeric(df[target_col], errors="coerce")
    bias_by_formula = metrics.set_index("formula")["bias_pred_minus_obs"].to_dict()
    rows = []

    for formula in variants.columns:
        bias = float(bias_by_formula.get(formula, float("nan")))
        score = pd.to_numeric(variants[formula], errors="coerce") - bias
        for thr in thresholds:
            rows.append({
                "formula": formula,
                "score_variant": "formula_bias_corrected",
                "bias_pred_minus_obs": bias,
                "bias_correction_added_c": -bias,
                "event_threshold_c": thr,
                "score_threshold_c": thr,
                **threshold_metrics(y, score, thr, thr),
            })

    return pd.DataFrame(rows)


def required_shift_summary(df: pd.DataFrame, variants: pd.DataFrame, target_col: str, thresholds: list[float]) -> pd.DataFrame:
    """Summarise additive shifts needed to cross fixed WBGT thresholds."""
    y = pd.to_numeric(df[target_col], errors="coerce")
    rows = []

    for formula in variants.columns:
        score_all = pd.to_numeric(variants[formula], errors="coerce")
        score = score_all.dropna()
        row: dict[str, Any] = {"formula": formula, "n": int(len(score))}
        max_score = float(score.max()) if len(score) else float("nan")
        p99_score = float(score.quantile(0.99)) if len(score) else float("nan")
        for thr in thresholds:
            suffix = str(int(thr))
            row[f"shift_to_make_max_reach_{suffix}"] = float(thr - max_score) if len(score) else float("nan")
            row[f"shift_to_make_p99_reach_{suffix}"] = float(thr - p99_score) if len(score) else float("nan")

            valid = y.notna() & score_all.notna()
            event_count = int((y[valid] >= thr).sum())
            row[f"observed_event_count_{suffix}"] = event_count
            if event_count <= 0:
                row[f"shift_to_match_observed_event_count_{suffix}"] = float("nan")
            else:
                ranked = score_all[valid].astype(float).sort_values(ascending=False)
                if event_count > len(ranked):
                    row[f"shift_to_match_observed_event_count_{suffix}"] = float("nan")
                else:
                    kth_score = float(ranked.iloc[event_count - 1])
                    row[f"shift_to_match_observed_event_count_{suffix}"] = float(thr - kth_score)
        rows.append(row)

    out = pd.DataFrame(rows)
    ordered_cols = ["formula", "n"]
    for thr in thresholds:
        suffix = str(int(thr))
        ordered_cols.extend([
            f"shift_to_make_max_reach_{suffix}",
            f"shift_to_match_observed_event_count_{suffix}",
            f"shift_to_make_p99_reach_{suffix}",
            f"observed_event_count_{suffix}",
        ])
    return out[[c for c in ordered_cols if c in out.columns]]


def grouped_bias(df: pd.DataFrame, variants: pd.DataFrame, target_col: str, group_col: str, out_name: str) -> pd.DataFrame:
    if group_col not in df.columns:
        return pd.DataFrame()

    y = pd.to_numeric(df[target_col], errors="coerce")
    work = pd.DataFrame({group_col: df[group_col]})
    for formula in variants.columns:
        work[f"{formula}_err"] = pd.to_numeric(variants[formula], errors="coerce") - y

    rows = []
    for key, g in work.groupby(group_col, dropna=False):
        row = {group_col: key, "rows": int(len(g))}
        for formula in variants.columns:
            err = g[f"{formula}_err"].dropna()
            row[f"{formula}_bias"] = float(err.mean()) if len(err) else float("nan")
            row[f"{formula}_mae"] = float(err.abs().mean()) if len(err) else float("nan")
        rows.append(row)

    return pd.DataFrame(rows)


def write_report(
    out_dir: Path,
    cfg: dict[str, Any],
    metrics: pd.DataFrame,
    dist: pd.DataFrame,
    conf: pd.DataFrame,
    op_points: pd.DataFrame,
    corrected_conf: pd.DataFrame,
    shifts: pd.DataFrame,
    flips: pd.DataFrame,
) -> None:
    lines = []
    lines.append("# System A WBGT formula sensitivity audit\n\n")
    lines.append("## Scope\n\n")
    lines.append("This is a companion sensitivity audit for System A. It does not retroactively recalibrate the v1.1-beta-formal results.\n\n")
    lines.append("## Inputs\n\n")
    lines.append(f"- Snapshot: `{cfg['inputs']['snapshot_v091_csv']}`\n")
    lines.append(f"- Target: `{cfg['inputs']['target_col']}`\n\n")
    lines.append("## Formula metrics\n\n")
    lines.append(markdown_table(metrics.round(6)))
    lines.append("\n\n## Raw formula distribution summary\n\n")
    lines.append(markdown_table(dist.round(6)))
    lines.append("\n\n## Threshold confusion matrix\n\n")
    lines.append("The fixed_31/fixed_33 raw confusion rows are all-zero on predicted positives because every raw formula variant remains below the 31C and 33C score thresholds in this snapshot.\n\n")
    lines.append(markdown_table(conf.round(6)))
    lines.append("\n\n## Threshold-sweep operating points\n\n")
    lines.append("Score thresholds are scanned from 27.0C to 34.0C in 0.05C increments. The recall_90 row selects the highest-precision threshold with recall >= 0.90 when available; precision_70 selects the highest-recall threshold with precision >= 0.70 when available.\n\n")
    lines.append(markdown_table(op_points.round(6)))
    lines.append("\n\n## Bias-corrected threshold results\n\n")
    lines.append("For this screening diagnostic, each formula is shifted by subtracting its mean prediction bias against observed WBGT, then evaluated at the same fixed 31C and 33C thresholds.\n\n")
    lines.append(markdown_table(corrected_conf.round(6)))
    lines.append("\n\n## Required additive shift summary\n\n")
    lines.append(markdown_table(shifts.round(6)))
    lines.append("\n\n## Crossing flips vs existing v09 proxy\n\n")
    if flips.empty:
        lines.append("_No existing_v09_proxy reference available._\n")
    else:
        lines.append(markdown_table(flips))
    lines.append("\n\n## Interpretation guardrails\n\n")
    lines.append("- The current variants are transparent screening/sensitivity formulas, not a validated replacement for NEA WBGT.\n")
    lines.append("- Bias correction and threshold sweeps are screening sensitivity diagnostics only; they do not validate a replacement formula or alter the frozen v1.1-beta-formal calibration outputs.\n")
    lines.append("- A Liljegren/PyWBGT route should be treated as a separate implementation-validation task before any formula replacement claim.\n")
    lines.append("- If formula choice shifts many rows around 31C or 33C, open a formula-v2 cycle rather than rewriting the v1.1-beta-formal report silently.\n")

    (out_dir / "System_A_WBGT_formula_audit_report.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="System A WBGT formula sensitivity audit.")
    parser.add_argument("--config", default="configs/v11/v11_formula_audit_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    in_path = Path(cfg["inputs"]["snapshot_v091_csv"])
    out_dir = Path(cfg["outputs"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[load] {in_path}")
    df = pd.read_csv(in_path, low_memory=False)
    print(f"       {len(df):,} rows x {len(df.columns):,} cols")

    target_col = cfg["inputs"]["target_col"]
    if target_col not in df.columns:
        raise KeyError(f"Missing target column: {target_col}")

    timestamp_col = cfg["inputs"].get("timestamp_col")
    if timestamp_col and timestamp_col in df.columns:
        df = df.copy()
        ts = pd.to_datetime(df[timestamp_col], errors="coerce")
        df["date_sgt_for_formula_audit"] = ts.dt.date.astype(str)

    variants = build_variants(df, cfg)
    metrics = formula_metrics(df, variants, target_col)
    dist = distribution_summary(variants)
    thresholds = [float(x) for x in cfg.get("thresholds_c", [31.0, 33.0])]
    conf, flips = threshold_tables(df, variants, target_col, thresholds)
    op_points = threshold_operating_points(df, variants, target_col, thresholds)
    corrected_conf = bias_corrected_confusion(metrics, df, variants, target_col, thresholds)
    shifts = required_shift_summary(df, variants, target_col, thresholds)

    metrics.to_csv(out_dir / "formula_bias_mae_rmse_table.csv", index=False)
    dist.to_csv(out_dir / "formula_distribution_summary.csv", index=False)
    conf.to_csv(out_dir / "formula_event_confusion_matrix.csv", index=False)
    conf.to_csv(out_dir / "threshold_crossing_diff_31_33.csv", index=False)
    op_points.to_csv(out_dir / "formula_threshold_operating_points.csv", index=False)
    corrected_conf.to_csv(out_dir / "formula_bias_corrected_confusion_matrix.csv", index=False)
    shifts.to_csv(out_dir / "formula_required_shift_summary.csv", index=False)
    flips.to_csv(out_dir / "formula_flip_summary_vs_v09.csv", index=False)

    station_col = cfg["inputs"].get("station_col", "station_id")
    station_bias = grouped_bias(df, variants, target_col, station_col, "station")
    if not station_bias.empty:
        station_bias.to_csv(out_dir / "formula_bias_by_station.csv", index=False)

    if "date_sgt_for_formula_audit" in df.columns:
        day_bias = grouped_bias(df, variants, target_col, "date_sgt_for_formula_audit", "day")
        day_bias.to_csv(out_dir / "formula_bias_by_day.csv", index=False)

    if cfg.get("outputs", {}).get("write_row_level_comparison_gzip", True):
        row = pd.DataFrame({
            "station_id": df.get(station_col),
            "timestamp": df.get(timestamp_col) if timestamp_col in df.columns else pd.NA,
            target_col: df[target_col],
        })
        for formula in variants.columns:
            row[formula] = variants[formula]
            row[f"{formula}_err_pred_minus_obs"] = variants[formula] - pd.to_numeric(df[target_col], errors="coerce")
        row.to_csv(out_dir / "formula_comparison_by_row.csv.gz", index=False, compression="gzip")

    write_report(out_dir, cfg, metrics, dist, conf, op_points, corrected_conf, shifts, flips)

    print("[write]", out_dir / "formula_bias_mae_rmse_table.csv")
    print("[write]", out_dir / "formula_distribution_summary.csv")
    print("[write]", out_dir / "formula_event_confusion_matrix.csv")
    print("[write]", out_dir / "formula_threshold_operating_points.csv")
    print("[write]", out_dir / "formula_bias_corrected_confusion_matrix.csv")
    print("[write]", out_dir / "formula_required_shift_summary.csv")
    print("[write]", out_dir / "formula_flip_summary_vs_v09.csv")
    print("[write]", out_dir / "System_A_WBGT_formula_audit_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
