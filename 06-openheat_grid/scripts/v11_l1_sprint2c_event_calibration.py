#!/usr/bin/env python
"""Run System A Level 1 Sprint 2C high-tail/event calibration diagnostics.

Inputs:
    - outputs/v11_level1/feature_ablation/oof_predictions_feature_ablation.csv
    - Optional raw validation predictions:
      outputs/v11_level1/blocked_time_high_tail/oof_predictions_blocked_time.csv
      outputs/v11_level1/blocked_time_high_tail/predictions_future_holdout.csv
    - Context-only Sprint 2A/2B reports and aggregate metric files, when present:
      outputs/v11_level1/feature_ablation/feature_ablation_report.md
      outputs/v11_level1/blocked_time_high_tail/sprint2b_blocked_time_high_tail_report.md
      outputs/v11_level1/blocked_time_high_tail/threshold_scan_metrics.csv
      outputs/v11_level1/blocked_time_high_tail/blocked_time_metrics.csv
      outputs/v11_level1/blocked_time_high_tail/future_holdout_metrics.csv

Outputs:
    - outputs/v11_level1/event_calibration/event_calibration_manifest.csv
    - outputs/v11_level1/event_calibration/threshold_scan_full.csv
    - outputs/v11_level1/event_calibration/operating_point_summary.csv
    - outputs/v11_level1/event_calibration/threshold_stability_summary.csv
    - outputs/v11_level1/event_calibration/score_bin_event_rates.csv
    - outputs/v11_level1/event_calibration/score_quantile_event_rates.csv
    - outputs/v11_level1/event_calibration/advisory_mapping_candidates.csv
    - outputs/v11_level1/event_calibration/exceedance_diagnostics.csv
    - outputs/v11_level1/event_calibration/event_calibration_by_station.csv
    - outputs/v11_level1/event_calibration/event_calibration_by_hour.csv
    - outputs/v11_level1/event_calibration/event_calibration_by_regime.csv
    - outputs/v11_level1/event_calibration/sprint2c_event_calibration_report.md

Saved metrics:
    - Candidate score inventory by validation source, target, and model.
    - Threshold scans for ge31, ge32 sensitivity, and ge33 events from 27.0 C
      through 34.5 C in 0.1 C steps.
    - Fixed nominal, best-F1, recall_90, precision_70, balanced-J, and low
      false-alarm operating points.
    - Cross-scheme threshold stability diagnostics.
    - Empirical score-bin and quantile-bin event-rate calibration diagnostics.
    - Diagnostic advisory mapping candidates for hourly_max ge31/ge33.
    - Expected exceedance diagnostics, plus station/hour/regime breakdowns.

This script only consumes existing Ridge prediction scores. It does not train
regression models, add model families, use fallback solvers, touch Level 2,
System B, SOLWEIG, v12, rasters, risk maps, hazard maps, archive collection, or
produce local WBGT.
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "outputs/v11_level1/event_calibration"

SELECTED_MODELS = [
    "M4_like_inertia_ridge",
    "M7_like_compact_weather_ridge",
    "L1_full_dynamic",
    "L1_proxy_radiation",
    "L1_proxy_only",
]
BASELINE_MODELS = {"L1_proxy_only"}
TARGETS = {
    "hourly_mean": "official_wbgt_c_mean",
    "hourly_max": "official_wbgt_c_max",
}
EVENTS = {
    "ge31": 31.0,
    "ge32": 32.0,
    "ge33": 33.0,
}
SOURCE_SPECS = [
    (
        "loso_oof",
        "loso_oof",
        ROOT / "outputs/v11_level1/feature_ablation/oof_predictions_feature_ablation.csv",
        True,
    ),
    (
        "blocked_time",
        "blocked_date_cv",
        ROOT / "outputs/v11_level1/blocked_time_high_tail/oof_predictions_blocked_time.csv",
        False,
    ),
    (
        "future_holdout",
        "future_holdout",
        ROOT / "outputs/v11_level1/blocked_time_high_tail/predictions_future_holdout.csv",
        False,
    ),
]
CONTEXT_FILES = {
    "feature_ablation_report": ROOT / "outputs/v11_level1/feature_ablation/feature_ablation_report.md",
    "sprint2b_report": ROOT / "outputs/v11_level1/blocked_time_high_tail/sprint2b_blocked_time_high_tail_report.md",
    "blocked_time_metrics": ROOT / "outputs/v11_level1/blocked_time_high_tail/blocked_time_metrics.csv",
    "future_holdout_metrics": ROOT / "outputs/v11_level1/blocked_time_high_tail/future_holdout_metrics.csv",
    "threshold_scan_metrics": ROOT / "outputs/v11_level1/blocked_time_high_tail/threshold_scan_metrics.csv",
}
FOCUS_STATIONS = {"S142", "S137", "S135", "S139"}


@dataclass(frozen=True)
class SourceFrame:
    source: str
    validation_scheme: str
    path: Path
    frame: pd.DataFrame


def rel(path: Path) -> str:
    """Return a repository-relative path for reports."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_div(num: float, den: float) -> float:
    """Divide with NaN for a zero denominator."""
    return float(num / den) if den else np.nan


def boolish(series: pd.Series) -> pd.Series:
    """Parse bool-like columns consistently."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def semicolon(values: Iterable[object]) -> str:
    """Join non-empty unique values for compact manifest fields."""
    seen: list[str] = []
    for value in values:
        text = str(value)
        if text and text != "nan" and text not in seen:
            seen.append(text)
    return ";".join(seen)


def finite_corr(left: pd.Series, right: pd.Series) -> float:
    """Compute a correlation only when both vectors vary meaningfully."""
    data = pd.DataFrame({"left": left, "right": right}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 3 or data["left"].std(ddof=0) == 0 or data["right"].std(ddof=0) == 0:
        return np.nan
    return float(data["left"].corr(data["right"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute Sprint 2C high-tail/event calibration diagnostics from "
            "existing System A Level 1 Ridge prediction scores."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT, help="Repository root. Defaults to this script parent.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for Sprint 2C CSV and Markdown artifacts.",
    )
    return parser.parse_args()


def write_blocker(out_dir: Path, reason: str, missing_paths: list[Path]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"status": "BLOCKED", "reason": reason, "missing_path": rel(path)} for path in missing_paths]
    pd.DataFrame(rows).to_csv(out_dir / "event_calibration_manifest.csv", index=False)
    report = [
        "# System A Level 1 Sprint 2C - High-tail / Event Calibration Diagnostics",
        "",
        "## Status",
        "BLOCKED",
        "",
        "## Blocker",
        reason,
        "",
        "Missing required prediction files:",
    ]
    report.extend(f"- `{rel(path)}`" for path in missing_paths)
    report.extend(
        [
            "",
            "No fallback backend was used. No new model family was added. No System B/v12 work was touched. No commit/stage was performed.",
        ]
    )
    (out_dir / "sprint2c_event_calibration_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def load_prediction_source(source: str, validation_scheme: str, path: Path) -> SourceFrame | None:
    if not path.exists():
        return None
    raw = pd.read_csv(path)
    required = {"dataset_label", "target_col", "prediction_wbgt_c"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise SystemExit(f"[ERROR] {rel(path)} missing required columns: {', '.join(missing)}")
    model_col = "ablation_model" if "ablation_model" in raw.columns else "model"
    if model_col not in raw.columns:
        raise SystemExit(f"[ERROR] {rel(path)} missing model/ablation_model column")
    if "observed_wbgt_c" not in raw.columns:
        raise SystemExit(f"[ERROR] {rel(path)} missing observed_wbgt_c column")

    df = raw.copy()
    df["model"] = df[model_col].astype(str)
    df = df[df["model"].isin(SELECTED_MODELS)].copy()
    df = df[df["dataset_label"].isin(TARGETS)].copy()
    df = df[df["target_col"].isin(TARGETS.values())].copy()
    df["prediction_source"] = source
    df["validation_scheme"] = validation_scheme
    df["source_file"] = rel(path)
    df["prediction_col"] = "prediction_wbgt_c"
    df["official_target_col"] = df["target_col"].astype(str)
    df["score"] = pd.to_numeric(df["prediction_wbgt_c"], errors="coerce")
    df["official"] = pd.to_numeric(df["observed_wbgt_c"], errors="coerce")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    elif "timestamp_sgt" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp_sgt"], errors="coerce")
    else:
        df["timestamp"] = pd.NaT
    if "hour" in df.columns:
        df["hour_numeric"] = pd.to_numeric(df["hour"], errors="coerce")
    else:
        df["hour_numeric"] = df["timestamp"].dt.hour
    if "station_id" not in df.columns:
        df["station_id"] = ""
    df["station_id"] = df["station_id"].astype(str)
    df = df[df["score"].notna() & df["official"].notna()].copy()

    if "fallback_used" in df.columns and boolish(df["fallback_used"]).any():
        bad = sorted(df.loc[boolish(df["fallback_used"]), "model"].dropna().astype(str).unique())
        raise SystemExit(f"[ERROR] fallback_used=True found in {rel(path)} for: {', '.join(bad)}")
    return SourceFrame(source=source, validation_scheme=validation_scheme, path=path, frame=df)


def make_manifest(sources: list[SourceFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for source in sources:
        for keys, group in source.frame.groupby(["dataset_label", "target_col", "model"], dropna=False):
            dataset_label, target_col, model = keys
            timestamps = group["timestamp"].dropna()
            rows.append(
                {
                    "prediction_source": source.source,
                    "dataset_label": dataset_label,
                    "target_col": target_col,
                    "model": model,
                    "n": int(len(group)),
                    "station_count": int(group["station_id"].nunique(dropna=True)),
                    "timestamp_min": timestamps.min().isoformat() if not timestamps.empty else "",
                    "timestamp_max": timestamps.max().isoformat() if not timestamps.empty else "",
                    "validation_scheme": source.validation_scheme,
                    "prediction_column_name": "prediction_wbgt_c",
                    "official_target_column_name": str(target_col),
                    "source_file": rel(source.path),
                    "ridge_backend": semicolon(group.get("ridge_backend", pd.Series(dtype=object)).dropna().unique()),
                    "fallback_used_any": bool(boolish(group["fallback_used"]).any()) if "fallback_used" in group.columns else False,
                    "is_baseline_only": model in BASELINE_MODELS,
                }
            )
    return pd.DataFrame(rows)


def confusion_metrics(official: pd.Series, score: pd.Series, event_threshold: float, score_threshold: float) -> dict[str, object]:
    obs = pd.to_numeric(official, errors="coerce") >= event_threshold
    pred = pd.to_numeric(score, errors="coerce") >= score_threshold
    valid = official.notna() & score.notna()
    obs = obs[valid].to_numpy(bool)
    pred = pred[valid].to_numpy(bool)
    tp = int(np.sum(obs & pred))
    fp = int(np.sum(~obs & pred))
    tn = int(np.sum(~obs & ~pred))
    fn = int(np.sum(obs & ~pred))
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    f1 = 2 * precision * recall / (precision + recall) if pd.notna(precision) and pd.notna(recall) and (precision + recall) else 0.0
    return {
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": precision,
        "recall": recall,
        "F1": float(f1),
        "specificity": specificity,
        "false_alarm_ratio": safe_div(fp, tp + fp),
        "miss_rate": safe_div(fn, tp + fn),
        "critical_success_index": safe_div(tp, tp + fp + fn),
        "predicted_positive_count": int(tp + fp),
        "official_positive_count": int(tp + fn),
        "youden_J": recall + specificity - 1 if pd.notna(recall) and pd.notna(specificity) else np.nan,
    }


def threshold_scan(sources: list[SourceFrame]) -> pd.DataFrame:
    thresholds = np.round(np.arange(27.0, 34.5 + 0.0001, 0.1), 1)
    rows: list[dict[str, object]] = []
    for source in sources:
        group_cols = ["prediction_source", "validation_scheme", "dataset_label", "target_col", "model"]
        for keys, group in source.frame.groupby(group_cols, dropna=False):
            base = dict(zip(group_cols, keys))
            for event_label, event_threshold in EVENTS.items():
                for threshold in thresholds:
                    row = {
                        **base,
                        "event_target": event_label,
                        "official_event_threshold_c": event_threshold,
                        "score_threshold_c": float(threshold),
                    }
                    row.update(confusion_metrics(group["official"], group["score"], event_threshold, float(threshold)))
                    rows.append(row)
    return pd.DataFrame(rows)


def pick_operating_rows(scan: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    group_cols = ["prediction_source", "validation_scheme", "dataset_label", "target_col", "model", "event_target"]
    for keys, group in scan.groupby(group_cols, dropna=False):
        base = dict(zip(group_cols, keys))
        event_threshold = float(group["official_event_threshold_c"].iloc[0])

        def add_row(name: str, chosen: pd.Series | None, achievable: bool) -> None:
            row = {
                **base,
                "operating_point": name,
                "achievable": bool(achievable),
                "official_event_threshold_c": event_threshold,
            }
            if chosen is None:
                for col in [
                    "score_threshold_c",
                    "TP",
                    "FP",
                    "TN",
                    "FN",
                    "precision",
                    "recall",
                    "F1",
                    "specificity",
                    "false_alarm_ratio",
                    "miss_rate",
                    "critical_success_index",
                    "predicted_positive_count",
                    "official_positive_count",
                    "youden_J",
                ]:
                    row[col] = np.nan
            else:
                for col in [
                    "score_threshold_c",
                    "TP",
                    "FP",
                    "TN",
                    "FN",
                    "precision",
                    "recall",
                    "F1",
                    "specificity",
                    "false_alarm_ratio",
                    "miss_rate",
                    "critical_success_index",
                    "predicted_positive_count",
                    "official_positive_count",
                    "youden_J",
                ]:
                    row[col] = chosen[col]
            rows.append(row)

        fixed = group[np.isclose(group["score_threshold_c"], event_threshold)]
        add_row("fixed_nominal", fixed.iloc[0] if not fixed.empty else None, not fixed.empty)

        best = group.sort_values(["F1", "recall", "score_threshold_c"], ascending=[False, False, False]).iloc[0]
        add_row("best_F1", best, True)

        recall_90 = group[group["recall"] >= 0.90].sort_values("score_threshold_c", ascending=False)
        add_row("recall_90", recall_90.iloc[0] if not recall_90.empty else None, not recall_90.empty)

        precision_70 = group[group["precision"] >= 0.70].sort_values("score_threshold_c", ascending=True)
        add_row("precision_70", precision_70.iloc[0] if not precision_70.empty else None, not precision_70.empty)

        balanced = group.sort_values(["youden_J", "F1", "score_threshold_c"], ascending=[False, False, False]).iloc[0]
        add_row("balanced_J", balanced, True)

        low_false_alarm = group[group["precision"] >= 0.70].sort_values(["recall", "score_threshold_c"], ascending=[False, False])
        add_row("low_false_alarm_candidate", low_false_alarm.iloc[0] if not low_false_alarm.empty else None, not low_false_alarm.empty)
    return pd.DataFrame(rows)


def make_stability_summary(ops: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    group_cols = ["dataset_label", "target_col", "model", "event_target"]
    source_labels = {
        "loso_oof": "LOSO",
        "blocked_time": "blocked",
        "future_holdout": "future",
    }
    for keys, group in ops.groupby(group_cols, dropna=False):
        dataset_label, target_col, model, event_target = keys
        best = group[group["operating_point"] == "best_F1"].copy()
        recall90 = group[group["operating_point"] == "recall_90"].copy()
        precision70 = group[group["operating_point"] == "precision_70"].copy()
        thresholds = best["score_threshold_c"].dropna()
        f1_values = best["F1"].dropna()
        recalls = best["recall"].dropna()
        threshold_range = float(thresholds.max() - thresholds.min()) if len(thresholds) else np.nan
        f1_range = float(f1_values.max() - f1_values.min()) if len(f1_values) else np.nan
        recall_range = float(recalls.max() - recalls.min()) if len(recalls) else np.nan
        achievable = precision70.set_index("prediction_source")["achievable"].to_dict()
        ach_values = [bool(v) for v in achievable.values()]
        if not ach_values:
            precision_stability = "unavailable"
        elif all(ach_values):
            precision_stability = "all_available_sources"
        elif not any(ach_values):
            precision_stability = "none"
        else:
            precision_stability = "mixed"

        if len(thresholds) == 0:
            stability = "unavailable"
        elif threshold_range > 0.8 or (pd.notna(f1_range) and f1_range > 0.20) or (len(f1_values) and f1_values.min() < 0.05):
            stability = "unstable"
        elif threshold_range <= 0.3 and (pd.isna(f1_range) or f1_range <= 0.08) and (pd.isna(recall_range) or recall_range <= 0.12):
            stability = "stable"
        else:
            stability = "mixed"

        row = {
            "dataset_label": dataset_label,
            "target_col": target_col,
            "model": model,
            "event_target": event_target,
            "threshold_range": threshold_range,
            "best_F1_range": f1_range,
            "best_F1_recall_range": recall_range,
            "recall_90_threshold_stability": "stable" if recall90["score_threshold_c"].dropna().max() - recall90["score_threshold_c"].dropna().min() <= 0.3 else "mixed_or_unavailable",
            "precision_70_achievability_stability": precision_stability,
            "stability": stability,
        }
        for source, label in source_labels.items():
            best_source = best[best["prediction_source"] == source]
            row[f"best_F1_threshold_{label}"] = best_source["score_threshold_c"].iloc[0] if not best_source.empty else np.nan
            row[f"best_F1_{label}"] = best_source["F1"].iloc[0] if not best_source.empty else np.nan
            row[f"best_F1_recall_{label}"] = best_source["recall"].iloc[0] if not best_source.empty else np.nan
            row[f"best_F1_precision_{label}"] = best_source["precision"].iloc[0] if not best_source.empty else np.nan
            recall_source = recall90[recall90["prediction_source"] == source]
            row[f"recall_90_threshold_{label}"] = recall_source["score_threshold_c"].iloc[0] if not recall_source.empty and bool(recall_source["achievable"].iloc[0]) else np.nan
            precision_source = precision70[precision70["prediction_source"] == source]
            row[f"precision_70_achievable_{label}"] = bool(precision_source["achievable"].iloc[0]) if not precision_source.empty else False
        rows.append(row)
    return pd.DataFrame(rows)


def bin_metrics(group: pd.DataFrame, event_label: str, event_threshold: float) -> dict[str, object]:
    residual = group["official"] - group["score"]
    event = group["official"] >= event_threshold
    return {
        "n": int(len(group)),
        "mean_prediction_score": float(group["score"].mean()) if len(group) else np.nan,
        "mean_official_wbgt": float(group["official"].mean()) if len(group) else np.nan,
        f"event_rate_{event_label}": float(event.mean()) if len(group) else np.nan,
        "official_mean_exceedance_above31": float(np.maximum(group["official"] - 31.0, 0).mean()) if len(group) else np.nan,
        "official_mean_exceedance_above33": float(np.maximum(group["official"] - 33.0, 0).mean()) if len(group) else np.nan,
        "mean_residual": float(residual.mean()) if len(group) else np.nan,
        "residual_MAE": float(residual.abs().mean()) if len(group) else np.nan,
        "residual_bias": float(residual.mean()) if len(group) else np.nan,
        "residual_p90": float(residual.quantile(0.90)) if len(group) else np.nan,
        "station_count": int(group["station_id"].nunique(dropna=True)),
        "event_count": int(event.sum()),
        "low_support": bool(len(group) < 30),
    }


def make_score_bin_tables(sources: list[SourceFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    fixed_rows: list[dict[str, object]] = []
    quantile_rows: list[dict[str, object]] = []
    fixed_edges = np.round(np.arange(27.0, 34.5 + 0.0001, 0.5), 1)
    group_cols = ["prediction_source", "validation_scheme", "dataset_label", "target_col", "model"]
    all_df = pd.concat([source.frame for source in sources], ignore_index=True)
    for keys, group in all_df.groupby(group_cols, dropna=False):
        base = dict(zip(group_cols, keys))
        for event_label in ["ge31", "ge33"]:
            event_threshold = EVENTS[event_label]
            in_range = group[group["score"].between(fixed_edges[0], fixed_edges[-1], inclusive="both")].copy()
            in_range["_score_bin"] = pd.cut(in_range["score"], bins=fixed_edges, include_lowest=True, right=False)
            for interval, bin_group in in_range.groupby("_score_bin", observed=True):
                fixed_rows.append(
                    {
                        **base,
                        "event_target": event_label,
                        "official_event_threshold_c": event_threshold,
                        "bin_type": "fixed_0p5c",
                        "bin_lower": float(interval.left),
                        "bin_upper": float(interval.right),
                        **bin_metrics(bin_group, event_label, event_threshold),
                    }
                )
            unique_scores = int(group["score"].nunique(dropna=True))
            if len(group) >= 100 and unique_scores >= 10:
                q_group = group.copy()
                q_group["_score_bin"] = pd.qcut(q_group["score"], q=10, duplicates="drop")
                for q_index, (interval, bin_group) in enumerate(q_group.groupby("_score_bin", observed=True), start=1):
                    quantile_rows.append(
                        {
                            **base,
                            "event_target": event_label,
                            "official_event_threshold_c": event_threshold,
                            "bin_type": "decile",
                            "quantile_bin": q_index,
                            "bin_lower": float(interval.left),
                            "bin_upper": float(interval.right),
                            **bin_metrics(bin_group, event_label, event_threshold),
                        }
                    )
    return pd.DataFrame(fixed_rows), pd.DataFrame(quantile_rows)


def best_op_lookup(ops: pd.DataFrame) -> dict[tuple[str, str, str, str], pd.Series]:
    lookup: dict[tuple[str, str, str, str], pd.Series] = {}
    best = ops[(ops["operating_point"] == "best_F1") & (ops["achievable"])]
    for _, row in best.iterrows():
        lookup[(row["prediction_source"], row["dataset_label"], row["model"], row["event_target"])] = row
    return lookup


def op_row(
    ops: pd.DataFrame,
    source: str,
    dataset_label: str,
    model: str,
    event_target: str,
    operating_point: str,
) -> pd.Series | None:
    rows = ops[
        (ops["prediction_source"] == source)
        & (ops["dataset_label"] == dataset_label)
        & (ops["model"] == model)
        & (ops["event_target"] == event_target)
        & (ops["operating_point"] == operating_point)
    ]
    if rows.empty or not bool(rows["achievable"].iloc[0]):
        return None
    return rows.iloc[0]


def make_advisory_mapping(ops: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    source = "loso_oof"
    dataset_label = "hourly_max"
    for model in SELECTED_MODELS:
        for event_target, candidates in [
            ("ge31", [("high_recall_screening", "recall_90"), ("best_F1_screening", "best_F1"), ("high_precision_screening", "precision_70")]),
            ("ge33", [("best_F1_exploratory", "best_F1")]),
        ]:
            for mapping_type, operating_point in candidates:
                selected = op_row(ops, source, dataset_label, model, event_target, operating_point)
                if selected is None:
                    rows.append(
                        {
                            "prediction_source": source,
                            "dataset_label": dataset_label,
                            "model": model,
                            "event_target": event_target,
                            "mapping_type": mapping_type,
                            "operating_point": operating_point,
                            "achievable": False,
                            "threshold": np.nan,
                            "expected_precision": np.nan,
                            "expected_recall": np.nan,
                            "expected_F1": np.nan,
                            "expected_false_alarm_ratio": np.nan,
                            "expected_miss_rate": np.nan,
                            "official_positive_count": np.nan,
                            "caveat": "Not achievable under LOSO OOF retrospective diagnostics.",
                        }
                    )
                    continue
                threshold = float(selected["score_threshold_c"])
                caveats: list[str] = []
                if event_target == "ge31":
                    caveats.append("Diagnostic candidate screening threshold only; not an official warning threshold.")
                    if 29.4 <= threshold <= 29.7:
                        caveats.append("Threshold near 29.4-29.7 C indicates score compression relative to official >=31 C.")
                    elif threshold < 31.0:
                        caveats.append("Threshold below 31 C indicates under-calibrated threshold crossing / score compression.")
                else:
                    caveats.append("Exploratory ge33 diagnostic only; do not recommend operational 33 C mapping from this evidence.")
                rows.append(
                    {
                        "prediction_source": source,
                        "dataset_label": dataset_label,
                        "model": model,
                        "event_target": event_target,
                        "mapping_type": mapping_type,
                        "operating_point": operating_point,
                        "achievable": True,
                        "threshold": threshold,
                        "expected_precision": selected["precision"],
                        "expected_recall": selected["recall"],
                        "expected_F1": selected["F1"],
                        "expected_false_alarm_ratio": selected["false_alarm_ratio"],
                        "expected_miss_rate": selected["miss_rate"],
                        "official_positive_count": selected["official_positive_count"],
                        "caveat": " ".join(caveats),
                    }
                )
    return pd.DataFrame(rows)


def exceedance_metric_rows(
    frame: pd.DataFrame,
    base: dict[str, object],
    station_level: bool,
    best_lookup: dict[tuple[str, str, str, str], pd.Series],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    source = str(base["prediction_source"])
    dataset_label = str(base["dataset_label"])
    model = str(base["model"])
    mapped = best_lookup.get((source, dataset_label, model, "ge31"))
    mapped_threshold = float(mapped["score_threshold_c"]) if mapped is not None and pd.notna(mapped["score_threshold_c"]) else np.nan
    specs = [
        ("official_excess31", "score_excess31_nominal", 31.0, 31.0),
        ("official_excess31", "score_excess31_mapped", 31.0, mapped_threshold),
        ("official_excess33", "score_excess33_nominal", 33.0, 33.0),
    ]
    for official_name, score_name, official_threshold, score_threshold in specs:
        if pd.isna(score_threshold):
            rows.append({**base, "summary_level": "station" if station_level else "overall", "official_excess": official_name, "score_excess_proxy": score_name, "score_threshold_c": np.nan})
            continue
        official_excess = np.maximum(frame["official"] - official_threshold, 0.0)
        score_excess = np.maximum(frame["score"] - score_threshold, 0.0)
        diff = score_excess - official_excess
        row = {
            **base,
            "summary_level": "station" if station_level else "overall",
            "official_excess": official_name,
            "score_excess_proxy": score_name,
            "official_threshold_c": official_threshold,
            "score_threshold_c": score_threshold,
            "n": int(len(frame)),
            "official_positive_excess_count": int((official_excess > 0).sum()),
            "score_positive_excess_count": int((score_excess > 0).sum()),
            "MAE_exceedance": float(np.mean(np.abs(diff))) if len(frame) else np.nan,
            "bias_exceedance": float(np.mean(diff)) if len(frame) else np.nan,
            "correlation_exceedance": finite_corr(pd.Series(official_excess), pd.Series(score_excess)),
            "zero_excess_false_negative_count": int(((official_excess > 0) & (score_excess <= 0)).sum()),
            "station_level_exceedance_bias": float(np.mean(diff)) if station_level and len(frame) else np.nan,
        }
        rows.append(row)
    return rows


def make_exceedance_diagnostics(sources: list[SourceFrame], ops: pd.DataFrame) -> pd.DataFrame:
    all_df = pd.concat([source.frame for source in sources], ignore_index=True)
    best_lookup = best_op_lookup(ops)
    rows: list[dict[str, object]] = []
    group_cols = ["prediction_source", "validation_scheme", "dataset_label", "target_col", "model"]
    for keys, group in all_df.groupby(group_cols, dropna=False):
        base = dict(zip(group_cols, keys))
        rows.extend(exceedance_metric_rows(group, base, False, best_lookup))
        for station_id, station_group in group.groupby("station_id", dropna=False):
            rows.extend(exceedance_metric_rows(station_group, {**base, "station_id": station_id}, True, best_lookup))
    return pd.DataFrame(rows)


def subgroup_event_rows(
    group: pd.DataFrame,
    base: dict[str, object],
    subgroup_label: str,
    subgroup_value: object,
    event_label: str,
    event_threshold: float,
    mapped_threshold: float,
) -> dict[str, object]:
    event_count = int((group["official"] >= event_threshold).sum())
    fixed = confusion_metrics(group["official"], group["score"], event_threshold, event_threshold)
    mapped = confusion_metrics(group["official"], group["score"], event_threshold, mapped_threshold) if pd.notna(mapped_threshold) else {}
    best_threshold = np.nan
    best_f1 = np.nan
    enough_events = event_count >= 5 and len(group) >= 30
    if enough_events:
        scans = []
        for threshold in np.round(np.arange(27.0, 34.5 + 0.0001, 0.1), 1):
            metrics = confusion_metrics(group["official"], group["score"], event_threshold, float(threshold))
            scans.append({"score_threshold_c": float(threshold), **metrics})
        best = pd.DataFrame(scans).sort_values(["F1", "recall", "score_threshold_c"], ascending=[False, False, False]).iloc[0]
        best_threshold = best["score_threshold_c"]
        best_f1 = best["F1"]
    high_tail = group[group["official"] >= event_threshold]
    residual = high_tail["official"] - high_tail["score"]
    row = {
        **base,
        subgroup_label: subgroup_value,
        "event_target": event_label,
        "official_event_threshold_c": event_threshold,
        "n": int(len(group)),
        "event_count": event_count,
        "best_F1_threshold_if_enough_events": best_threshold,
        "best_F1_if_enough_events": best_f1,
        "fixed_nominal_threshold": event_threshold,
        "fixed_nominal_recall": fixed["recall"],
        "fixed_nominal_F1": fixed["F1"],
        "mapped_threshold": mapped_threshold,
        "mapped_threshold_recall": mapped.get("recall", np.nan),
        "mapped_threshold_F1": mapped.get("F1", np.nan),
        "residual_bias_high_tail_official_minus_score": float(residual.mean()) if len(residual) else np.nan,
        "low_support": bool(not enough_events),
    }
    if subgroup_label == "station_id":
        row["focus_station"] = str(subgroup_value) in FOCUS_STATIONS
    return row


def make_station_hour_regime(sources: list[SourceFrame], ops: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    all_df = pd.concat([source.frame for source in sources], ignore_index=True)
    best_lookup = best_op_lookup(ops)
    station_rows: list[dict[str, object]] = []
    hour_rows: list[dict[str, object]] = []
    regime_rows: list[dict[str, object]] = []
    group_cols = ["prediction_source", "validation_scheme", "dataset_label", "target_col", "model"]
    for keys, group in all_df.groupby(group_cols, dropna=False):
        base = dict(zip(group_cols, keys))
        for event_label in ["ge31", "ge33"]:
            event_threshold = EVENTS[event_label]
            mapped = best_lookup.get((str(base["prediction_source"]), str(base["dataset_label"]), str(base["model"]), event_label))
            mapped_threshold = float(mapped["score_threshold_c"]) if mapped is not None and pd.notna(mapped["score_threshold_c"]) else np.nan
            for station_id, station_group in group.groupby("station_id", dropna=False):
                station_rows.append(subgroup_event_rows(station_group, base, "station_id", station_id, event_label, event_threshold, mapped_threshold))
            hour_values = group.assign(hour_int=np.floor(group["hour_numeric"]).astype("Int64"))
            for hour, hour_group in hour_values.groupby("hour_int", dropna=False):
                hour_rows.append(subgroup_event_rows(hour_group, base, "hour", hour, event_label, event_threshold, mapped_threshold))

            shortwave_col = next((col for col in ["shortwave_radiation", "shortwave_w_m2"] if col in group.columns), "")
            if shortwave_col:
                regime_group = group.copy()
                regime_group["_shortwave"] = pd.to_numeric(regime_group[shortwave_col], errors="coerce")
                valid = regime_group[regime_group["_shortwave"].notna()].copy()
                if valid["_shortwave"].nunique() >= 3:
                    valid["radiation_regime"] = pd.qcut(valid["_shortwave"], q=3, labels=["low", "medium", "high"], duplicates="drop")
                    for regime, sub in valid.groupby("radiation_regime", observed=True):
                        regime_rows.append(subgroup_event_rows(sub, {**base, "regime_variable": shortwave_col}, "radiation_regime", regime, event_label, event_threshold, mapped_threshold))
            else:
                regime_rows.append(
                    {
                        **base,
                        "event_target": event_label,
                        "status": "skipped_missing_shortwave_radiation_in_prediction_outputs",
                        "regime_variable": "",
                        "radiation_regime": "",
                    }
                )
    return pd.DataFrame(station_rows), pd.DataFrame(hour_rows), pd.DataFrame(regime_rows)


def regression_summary(sources: list[SourceFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    all_df = pd.concat([source.frame for source in sources], ignore_index=True)
    for keys, group in all_df.groupby(["prediction_source", "dataset_label", "target_col", "model"], dropna=False):
        source, dataset_label, target_col, model = keys
        residual = group["score"] - group["official"]
        ss_res = float(np.sum((group["official"] - group["score"]) ** 2))
        ss_tot = float(np.sum((group["official"] - group["official"].mean()) ** 2))
        rows.append(
            {
                "prediction_source": source,
                "dataset_label": dataset_label,
                "target_col": target_col,
                "model": model,
                "n": int(len(group)),
                "MAE": float(residual.abs().mean()),
                "RMSE": float(np.sqrt(np.mean(residual**2))),
                "bias_pred_minus_obs": float(residual.mean()),
                "R2": float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def fmt(value: object, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return "NA"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}"
    return str(value)


def report_table(rows: pd.DataFrame, columns: list[str], max_rows: int = 8) -> list[str]:
    if rows.empty:
        return ["No rows available."]
    data = rows.loc[:, columns].head(max_rows).copy()
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in data.iterrows():
        lines.append("| " + " | ".join(fmt(row[col]) for col in columns) + " |")
    return lines


def build_report(
    out_dir: Path,
    sources: list[SourceFrame],
    manifest: pd.DataFrame,
    ops: pd.DataFrame,
    stability: pd.DataFrame,
    fixed_bins: pd.DataFrame,
    advisory: pd.DataFrame,
    exceedance: pd.DataFrame,
    station_rows: pd.DataFrame,
    hour_rows: pd.DataFrame,
    regime_rows: pd.DataFrame,
    reg: pd.DataFrame,
) -> str:
    raw_available = {source.source for source in sources}
    status = "PASS" if {"loso_oof", "blocked_time", "future_holdout"}.issubset(raw_available) else "PARTIAL"
    input_lines = []
    for _, _, path, required in SOURCE_SPECS:
        state = "used" if path.exists() else ("missing_required" if required else "not_available")
        input_lines.append(f"- `{rel(path)}`: {state}")
    context_lines = [f"- `{rel(path)}`: {'present' if path.exists() else 'not present'}" for path in CONTEXT_FILES.values()]

    loso_ge31_max = ops[
        (ops["prediction_source"] == "loso_oof")
        & (ops["dataset_label"] == "hourly_max")
        & (ops["event_target"] == "ge31")
        & (ops["operating_point"].isin(["fixed_nominal", "best_F1", "recall_90", "precision_70"]))
    ].copy()
    loso_ge33_max = ops[
        (ops["prediction_source"] == "loso_oof")
        & (ops["dataset_label"] == "hourly_max")
        & (ops["event_target"] == "ge33")
        & (ops["operating_point"].isin(["fixed_nominal", "best_F1"]))
    ].copy()
    mean_ge31 = ops[
        (ops["prediction_source"] == "loso_oof")
        & (ops["dataset_label"] == "hourly_mean")
        & (ops["event_target"] == "ge31")
        & (ops["operating_point"].isin(["fixed_nominal", "best_F1"]))
    ].copy()
    best_event = loso_ge31_max[loso_ge31_max["operating_point"] == "best_F1"].sort_values("F1", ascending=False).head(1)
    best_reg = reg[(reg["prediction_source"] == "loso_oof") & (reg["dataset_label"] == "hourly_max")].sort_values("MAE").head(1)
    ge33_best = loso_ge33_max[loso_ge33_max["operating_point"] == "best_F1"].sort_values("F1", ascending=False).head(1)
    compression_thresholds = loso_ge31_max[(loso_ge31_max["operating_point"] == "best_F1") & (loso_ge31_max["score_threshold_c"] < 31.0)]["score_threshold_c"]
    mapped_stable = stability[(stability["dataset_label"] == "hourly_max") & (stability["event_target"] == "ge31")]

    monotonic_note = "Score-bin rows were written for fixed 0.5 C bins and deciles. Inspect bins with low_support=False first."
    if not fixed_bins.empty:
        ge31_bins = fixed_bins[(fixed_bins["prediction_source"] == "loso_oof") & (fixed_bins["dataset_label"] == "hourly_max") & (fixed_bins["event_target"] == "ge31")]
        if not ge31_bins.empty:
            model_monotonic = []
            for model, group in ge31_bins.groupby("model"):
                rate_col = "event_rate_ge31"
                ordered = group.sort_values("bin_lower")
                rates = ordered[ordered["low_support"] == False][rate_col].dropna().to_numpy()  # noqa: E712
                if len(rates) >= 3:
                    model_monotonic.append(f"{model}: {'mostly monotonic' if np.all(np.diff(rates) >= -0.05) else 'not strictly monotonic'}")
            if model_monotonic:
                monotonic_note = "; ".join(model_monotonic) + "."

    station_focus = station_rows[(station_rows.get("focus_station", False) == True) & (station_rows["prediction_source"] == "loso_oof")] if not station_rows.empty else pd.DataFrame()  # noqa: E712
    regime_status = "shortwave radiation regimes computed."
    if not regime_rows.empty and "status" in regime_rows.columns and regime_rows["status"].astype(str).str.contains("skipped_missing").any():
        regime_status = "Radiation-regime calibration was skipped because shortwave radiation was not present in the prediction output schema."

    lines = [
        "# System A Level 1 Sprint 2C - High-tail / Event Calibration Diagnostics",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- Level 1 only.",
        "- Existing prediction scores only.",
        "- No new regression model.",
        "- No new model family.",
        "- No formula-v2.",
        "- No Level 2.",
        "- No System B / SOLWEIG / v12.",
        "- No local WBGT.",
        "",
        "## Inputs",
        *input_lines,
        "",
        "Context files:",
        *context_lines,
        "",
        f"Loaded manifest rows: {len(manifest)} across {manifest['station_count'].max() if not manifest.empty else 0} stations. Candidate models: {', '.join(SELECTED_MODELS)}.",
        "",
        "## Why Sprint 2C was needed",
        "Sprint 2B showed severe high-tail underprediction, nominal fixed_33 threshold crossings were absent or ineffective for the Ridge scores, and ge31 best-F1 thresholds fell below the official 31 C event boundary. Sprint 2C therefore treats existing Ridge outputs as diagnostic scores and audits threshold behavior without creating a new WBGT value.",
        "",
        "## Operating Point Results",
        "Hourly_max ge31 LOSO reference:",
        *report_table(
            loso_ge31_max.sort_values(["model", "operating_point"]),
            ["model", "operating_point", "achievable", "score_threshold_c", "precision", "recall", "F1", "false_alarm_ratio", "miss_rate"],
            max_rows=20,
        ),
        "",
        "Hourly_mean ge31 LOSO reference:",
        *report_table(
            mean_ge31.sort_values(["model", "operating_point"]),
            ["model", "operating_point", "score_threshold_c", "precision", "recall", "F1"],
            max_rows=12,
        ),
        "",
        "Hourly_max ge33 remains exploratory:",
        *report_table(
            loso_ge33_max.sort_values(["model", "operating_point"]),
            ["model", "operating_point", "score_threshold_c", "official_positive_count", "precision", "recall", "F1"],
            max_rows=12,
        ),
        "",
        "## Threshold Stability",
        *report_table(
            mapped_stable.sort_values(["event_target", "model"]),
            ["model", "event_target", "best_F1_threshold_LOSO", "best_F1_threshold_blocked", "best_F1_threshold_future", "threshold_range", "best_F1_range", "stability"],
            max_rows=15,
        ),
        "",
        "## Score-bin Event Rates",
        monotonic_note,
        "These are empirical score calibration tables only, not a trained probability model.",
        "",
        "## Advisory Mapping Candidates",
        "The advisory table uses cautious language: candidate screening threshold and diagnostic advisory mapping. It is not a final official warning threshold.",
        *report_table(
            advisory[(advisory["dataset_label"] == "hourly_max") & (advisory["event_target"] == "ge31")],
            ["model", "mapping_type", "achievable", "threshold", "expected_precision", "expected_recall", "expected_F1"],
            max_rows=18,
        ),
        "",
        "## Expected Exceedance",
        "Expected exceedance diagnostics were written for nominal 31 C, mapped ge31, and nominal 33 C score exceedance proxies. Because mapped thresholds are diagnostic score cutoffs, score exceedance should not be interpreted as official WBGT exceedance.",
        *report_table(
            exceedance[(exceedance["summary_level"] == "overall") & (exceedance["prediction_source"] == "loso_oof") & (exceedance["dataset_label"] == "hourly_max")],
            ["model", "score_excess_proxy", "MAE_exceedance", "bias_exceedance", "correlation_exceedance", "zero_excess_false_negative_count"],
            max_rows=15,
        ),
        "",
        "## Station/regime Findings",
        "Focus stations S142, S137, S135, and S139 are flagged in `event_calibration_by_station.csv` when present.",
        *report_table(
            station_focus[(station_focus["dataset_label"] == "hourly_max") & (station_focus["event_target"] == "ge31")].sort_values(["model", "station_id"]),
            ["model", "station_id", "event_count", "fixed_nominal_recall", "mapped_threshold_recall", "residual_bias_high_tail_official_minus_score"],
            max_rows=16,
        ),
        regime_status,
        "",
        "## Interpretation",
        f"1. Best ge31 event screening score under LOSO hourly_max: {best_event['model'].iloc[0] if not best_event.empty else 'NA'} at threshold {fmt(best_event['score_threshold_c'].iloc[0] if not best_event.empty else np.nan)} with F1 {fmt(best_event['F1'].iloc[0] if not best_event.empty else np.nan)}.",
        f"2. Best overall Level 1 WBGT_A regression under LOSO hourly_max MAE among selected scores: {best_reg['model'].iloc[0] if not best_reg.empty else 'NA'} with MAE {fmt(best_reg['MAE'].iloc[0] if not best_reg.empty else np.nan)}.",
        f"3. ge33 remains exploratory; the best LOSO hourly_max ge33 F1 among selected scores is {fmt(ge33_best['F1'].iloc[0] if not ge33_best.empty else np.nan)} with event count {fmt(ge33_best['official_positive_count'].iloc[0] if not ge33_best.empty else np.nan)}.",
        f"4. Score compression remains present: ge31 best-F1 thresholds below 31 C were observed from {fmt(compression_thresholds.min() if not compression_thresholds.empty else np.nan)} to {fmt(compression_thresholds.max() if not compression_thresholds.empty else np.nan)}.",
        "5. Sprint 2C supports a diagnostic event score layer when thresholds are stable enough, but it is not enough to claim calibrated WBGT. Formula-v2/probability-calibration work remains a separate companion step.",
        "",
        "## Caveats",
        "- Event calibration is diagnostic, not an official warning system.",
        "- Thresholds are derived from retrospective data.",
        "- This is not a prospective forecast evaluation.",
        "- Scores are not probability calibrated unless explicitly modeled.",
        "- No formula-v2 was run.",
        "- No local WBGT was produced.",
        "",
        "## Next Recommended Action",
        "- Build a formula-v2 proxy benchmark and a probability-calibration / P_ge31 companion before considering any high-tail-specific model family comparison.",
        "- Prepare a Level 1 model card that separates regression WBGT_A behavior from diagnostic event-score mapping.",
        "",
        "## Run Hygiene",
        "- No forbidden files touched by the Sprint 2C script.",
        "- No fallback used.",
        "- No new model family added.",
        "- No System B/v12 touched.",
        "- No commit/stage performed.",
    ]
    report = "\n".join(lines) + "\n"
    (out_dir / "sprint2c_event_calibration_report.md").write_text(report, encoding="utf-8")
    return status


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    missing_required = [path for _, _, path, required in SOURCE_SPECS if required and not path.exists()]
    if missing_required:
        write_blocker(out_dir, "Required LOSO OOF prediction file is missing; Sprint 2C stopped without recalculating models.", missing_required)
        return 2

    sources: list[SourceFrame] = []
    for source, validation_scheme, path, _required in SOURCE_SPECS:
        loaded = load_prediction_source(source, validation_scheme, path)
        if loaded is not None:
            sources.append(loaded)
    if not sources:
        write_blocker(out_dir, "No prediction sources were available; Sprint 2C stopped without recalculating models.", [])
        return 2

    available_models = set(pd.concat([source.frame["model"] for source in sources], ignore_index=True).unique())
    missing_models = sorted(set(SELECTED_MODELS) - available_models)
    if missing_models:
        write_blocker(out_dir, "Required selected candidate scores are missing from available prediction files: " + ", ".join(missing_models), [])
        return 2

    manifest = make_manifest(sources)
    scan = threshold_scan(sources)
    ops = pick_operating_rows(scan)
    stability = make_stability_summary(ops)
    fixed_bins, quantile_bins = make_score_bin_tables(sources)
    advisory = make_advisory_mapping(ops)
    exceedance = make_exceedance_diagnostics(sources, ops)
    station_rows, hour_rows, regime_rows = make_station_hour_regime(sources, ops)
    reg = regression_summary(sources)

    manifest.to_csv(out_dir / "event_calibration_manifest.csv", index=False)
    scan.to_csv(out_dir / "threshold_scan_full.csv", index=False)
    ops.to_csv(out_dir / "operating_point_summary.csv", index=False)
    stability.to_csv(out_dir / "threshold_stability_summary.csv", index=False)
    fixed_bins.to_csv(out_dir / "score_bin_event_rates.csv", index=False)
    quantile_bins.to_csv(out_dir / "score_quantile_event_rates.csv", index=False)
    advisory.to_csv(out_dir / "advisory_mapping_candidates.csv", index=False)
    exceedance.to_csv(out_dir / "exceedance_diagnostics.csv", index=False)
    station_rows.to_csv(out_dir / "event_calibration_by_station.csv", index=False)
    hour_rows.to_csv(out_dir / "event_calibration_by_hour.csv", index=False)
    regime_rows.to_csv(out_dir / "event_calibration_by_regime.csv", index=False)

    status = build_report(out_dir, sources, manifest, ops, stability, fixed_bins, advisory, exceedance, station_rows, hour_rows, regime_rows, reg)
    print(f"[OK] Sprint 2C event calibration diagnostics complete: {status}")
    print(f"[OK] Outputs written to {rel(out_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
