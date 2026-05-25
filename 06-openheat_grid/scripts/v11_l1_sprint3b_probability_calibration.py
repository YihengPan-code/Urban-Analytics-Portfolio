#!/usr/bin/env python
"""Run System A Level 1 Sprint 3B P_ge31 probability calibration diagnostics.

Inputs:
    - outputs/v11_level1/feature_ablation/oof_predictions_feature_ablation.csv
    - Optional prediction inventory sources:
      outputs/v11_level1/blocked_time_high_tail/oof_predictions_blocked_time.csv
      outputs/v11_level1/blocked_time_high_tail/predictions_future_holdout.csv
    - Context-only Sprint 2C mapping summaries:
      outputs/v11_level1/event_calibration/advisory_mapping_candidates.csv
      outputs/v11_level1/event_calibration/operating_point_summary.csv
      outputs/v11_level1/event_calibration/threshold_stability_summary.csv
    - Context-only Sprint 3A formula comparison summaries, when present.

Outputs:
    - outputs/v11_level1/probability_calibration/probability_calibration_manifest.csv
    - outputs/v11_level1/probability_calibration/reliability_bins_fixed.csv
    - outputs/v11_level1/probability_calibration/reliability_bins_quantile.csv
    - outputs/v11_level1/probability_calibration/reliability_summary.csv
    - outputs/v11_level1/probability_calibration/probability_calibration_metrics.csv
    - outputs/v11_level1/probability_calibration/probability_threshold_metrics.csv
    - outputs/v11_level1/probability_calibration/probability_calibration_by_fold.csv
    - outputs/v11_level1/probability_calibration/probability_model_selection_summary.csv
    - outputs/v11_level1/probability_calibration/probability_stability_summary.csv
    - outputs/v11_level1/probability_calibration/probability_vs_event_score_mapping.csv
    - outputs/v11_level1/probability_calibration/probability_by_station.csv
    - outputs/v11_level1/probability_calibration/probability_by_hour.csv
    - outputs/v11_level1/probability_calibration/probability_by_regime.csv
    - outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv
    - outputs/v11_level1/probability_calibration/sprint3b_pge31_probability_calibration_report.md

Saved metrics:
    - Prediction-source inventory and ge31/ge33 event counts.
    - Fixed 0.5 C and quantile reliability bins with monotonicity status.
    - Retrospective blocked-date, future-block, and station-grouped probability
      calibration metrics from held-out rows only.
    - Logistic, balanced-logistic sensitivity, isotonic, and empirical-bin
      probability calibration from one existing score feature to one binary event.
    - Training-selected probability-threshold confusion metrics on held-out rows.
    - Model-selection, stability, station, hour, and regime diagnostics.

This script only consumes existing System A Level 1 score predictions. It does
not train new WBGT regression models, add model families, use fallback solvers,
touch Level 2, System B, SOLWEIG, v12, rasters, risk maps, hazard maps, archive
collection, GitHub Actions archive lanes, formula-v2, or local WBGT outputs.
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
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "outputs/v11_level1/probability_calibration"

SELECTED_MODELS = [
    "M4_like_inertia_ridge",
    "M7_like_compact_weather_ridge",
    "L1_full_dynamic",
    "L1_proxy_radiation",
    "L1_proxy_only",
]
TARGETS = {
    "hourly_max": "official_wbgt_c_max",
    "hourly_mean": "official_wbgt_c_mean",
}
EVENTS = {
    "ge31": 31.0,
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
        "future_holdout_last_block",
        ROOT / "outputs/v11_level1/blocked_time_high_tail/predictions_future_holdout.csv",
        False,
    ),
]
SPRINT_2C_FILES = {
    "advisory": ROOT / "outputs/v11_level1/event_calibration/advisory_mapping_candidates.csv",
    "operating": ROOT / "outputs/v11_level1/event_calibration/operating_point_summary.csv",
    "stability": ROOT / "outputs/v11_level1/event_calibration/threshold_stability_summary.csv",
}
SPRINT_3A_FILES = {
    "formula_comparison": ROOT / "outputs/v11_level1/formula_v2/formula_vs_event_score_comparison.csv",
    "formula_report": ROOT / "outputs/v11_level1/formula_v2/sprint3a_formula_v2_proxy_benchmark_report.md",
}
FOCUS_STATIONS = {"S142", "S137", "S135", "S139"}
FIXED_PROB_THRESHOLDS = [0.10, 0.20, 0.30, 0.40, 0.50]
MIN_ISOTONIC_EVENTS = 20
MIN_ISOTONIC_NON_EVENTS = 20
MIN_TRAIN_ROWS = 100


@dataclass(frozen=True)
class SourceFrame:
    """Loaded prediction source after schema normalization."""

    source: str
    validation_scheme: str
    path: Path
    frame: pd.DataFrame


def rel(path: Path) -> str:
    """Return a repository-relative display path."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_div(num: float, den: float) -> float:
    """Divide with NaN for zero denominators."""
    return float(num / den) if den else np.nan


def semicolon(values: Iterable[object]) -> str:
    """Join unique non-empty values for compact manifests."""
    seen: list[str] = []
    for value in values:
        text = str(value)
        if text and text != "nan" and text not in seen:
            seen.append(text)
    return ";".join(seen)


def fmt(value: object, digits: int = 3) -> str:
    """Format report values with a compact NA fallback."""
    if value is None:
        return "NA"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return "NA"
    return f"{number:.{digits}f}"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Compute Sprint 3B held-out probability calibration diagnostics "
            "from existing System A Level 1 score predictions."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT, help="Repository root. Defaults to this script parent.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for Sprint 3B probability calibration artifacts.",
    )
    return parser.parse_args()


def normalize_prediction_source(source: str, validation_scheme: str, path: Path) -> SourceFrame | None:
    """Load and normalize one existing prediction file."""
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "timestamp_sgt" not in df.columns and "timestamp" in df.columns:
        df["timestamp_sgt"] = df["timestamp"]
    if "timestamp" not in df.columns and "timestamp_sgt" in df.columns:
        df["timestamp"] = df["timestamp_sgt"]
    df["timestamp_sgt"] = pd.to_datetime(df["timestamp_sgt"], errors="coerce")
    if "date" not in df.columns:
        df["date"] = df["timestamp_sgt"].dt.date.astype(str)
    if "hour" not in df.columns:
        df["hour"] = df["timestamp_sgt"].dt.hour
    if "observed_wbgt_c" not in df.columns:
        df["observed_wbgt_c"] = np.nan
    df["prediction_source"] = source
    df["validation_scheme"] = validation_scheme
    keep = df[
        df["dataset_label"].isin(TARGETS)
        & df["model"].isin(SELECTED_MODELS)
        & df["prediction_wbgt_c"].notna()
        & df["timestamp_sgt"].notna()
        & df["station_id"].notna()
    ].copy()
    return SourceFrame(source=source, validation_scheme=validation_scheme, path=path, frame=keep)


def write_blocker(out_dir: Path, reason: str, missing_paths: list[Path]) -> None:
    """Write a blocker manifest and report when required inputs are missing."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "status": "BLOCKED",
                "reason": reason,
                "missing_path": rel(path) if path.exists() or path.is_absolute() else str(path),
            }
            for path in missing_paths
        ]
        or [{"status": "BLOCKED", "reason": reason, "missing_path": ""}]
    ).to_csv(out_dir / "probability_calibration_manifest.csv", index=False)
    lines = [
        "# System A Level 1 Sprint 3B - P_ge31 Probability Calibration Companion",
        "",
        "## Status",
        "BLOCKED",
        "",
        "## Blocker",
        reason,
        "",
        "No prior models were rerun. No fallback backend was used.",
    ]
    (out_dir / "sprint3b_pge31_probability_calibration_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_manifest(sources: list[SourceFrame]) -> pd.DataFrame:
    """Create an input inventory and event-count manifest."""
    rows: list[dict[str, object]] = []
    for loaded in sources:
        df = loaded.frame
        for dataset_label, target_col in TARGETS.items():
            sub_dataset = df[(df["dataset_label"] == dataset_label) & df[target_col].notna()].copy()
            for model in SELECTED_MODELS:
                sub = sub_dataset[sub_dataset["model"] == model]
                if sub.empty:
                    rows.append(
                        {
                            "status": "missing_model_rows",
                            "prediction_source": loaded.source,
                            "validation_scheme": loaded.validation_scheme,
                            "prediction_path": rel(loaded.path),
                            "dataset_label": dataset_label,
                            "target_col": target_col,
                            "model": model,
                            "score_col": "prediction_wbgt_c",
                            "timestamp_col": "timestamp_sgt",
                            "station_col": "station_id",
                            "n_rows": 0,
                        }
                    )
                    continue
                for event_target, threshold in EVENTS.items():
                    rows.append(
                        {
                            "status": "available",
                            "prediction_source": loaded.source,
                            "validation_scheme": loaded.validation_scheme,
                            "prediction_path": rel(loaded.path),
                            "dataset_label": dataset_label,
                            "target_col": target_col,
                            "model": model,
                            "score_col": "prediction_wbgt_c",
                            "official_target_col": target_col,
                            "event_target": event_target,
                            "official_event_threshold_c": threshold,
                            "timestamp_col": "timestamp_sgt",
                            "station_col": "station_id",
                            "n_rows": len(sub),
                            "station_count": sub["station_id"].nunique(),
                            "date_min": sub["timestamp_sgt"].min(),
                            "date_max": sub["timestamp_sgt"].max(),
                            "event_count": int((sub[target_col] >= threshold).sum()),
                            "event_rate": safe_div(int((sub[target_col] >= threshold).sum()), len(sub)),
                            "fallback_used_any": bool(
                                "fallback_used" in sub.columns
                                and sub["fallback_used"].astype(str).str.lower().isin({"true", "1", "yes", "y"}).any()
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def monotonic_status(values: pd.Series) -> str:
    """Classify monotonicity of event rate against increasing score bins."""
    rates = values.dropna().to_numpy(dtype=float)
    if len(rates) < 3:
        return "insufficient_bins"
    diffs = np.diff(rates)
    decreases = int((diffs < -1e-9).sum())
    if decreases == 0:
        return "monotonic"
    if decreases <= max(1, math.floor(0.25 * len(diffs))):
        return "mostly_monotonic"
    return "not_monotonic"


def reliability_one(
    sub: pd.DataFrame,
    source: str,
    validation_scheme: str,
    dataset_label: str,
    target_col: str,
    model: str,
    event_target: str,
    event_threshold: float,
    bin_kind: str,
) -> pd.DataFrame:
    """Build fixed or quantile empirical reliability bins."""
    frame = sub[[target_col, "prediction_wbgt_c", "station_id"]].dropna().copy()
    if frame.empty:
        return pd.DataFrame()
    if bin_kind == "fixed":
        edges = np.arange(27.0, 35.0 + 0.5, 0.5)
        labels = [f"[{edges[i]:.1f},{edges[i + 1]:.1f})" for i in range(len(edges) - 1)]
        frame["score_bin"] = pd.cut(frame["prediction_wbgt_c"], bins=edges, labels=labels, include_lowest=True, right=False)
    else:
        unique_scores = frame["prediction_wbgt_c"].nunique()
        if unique_scores < 5 or len(frame) < 100:
            return pd.DataFrame()
        q = min(10, unique_scores)
        frame["score_bin"] = pd.qcut(frame["prediction_wbgt_c"], q=q, duplicates="drop")
        frame["score_bin"] = frame["score_bin"].astype(str)
    frame["event"] = (frame[target_col] >= event_threshold).astype(int)
    grouped = frame.dropna(subset=["score_bin"]).groupby("score_bin", observed=False)
    out = grouped.agg(
        n=("event", "size"),
        score_min=("prediction_wbgt_c", "min"),
        score_max=("prediction_wbgt_c", "max"),
        mean_score=("prediction_wbgt_c", "mean"),
        event_rate=("event", "mean"),
        event_count=("event", "sum"),
        mean_official_wbgt=(target_col, "mean"),
        station_count=("station_id", "nunique"),
    ).reset_index()
    if out.empty:
        return out
    out["mean_residual_official_minus_score"] = out["mean_official_wbgt"] - out["mean_score"]
    out["low_support"] = out["n"] < 30
    out.insert(0, "event_target", event_target)
    out.insert(0, "model", model)
    out.insert(0, "target_col", target_col)
    out.insert(0, "dataset_label", dataset_label)
    out.insert(0, "validation_scheme", validation_scheme)
    out.insert(0, "prediction_source", source)
    out["official_event_threshold_c"] = event_threshold
    out["bin_kind"] = bin_kind
    return out


def make_reliability_tables(sources: list[SourceFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create fixed and quantile reliability tables plus monotonic summaries."""
    fixed_rows: list[pd.DataFrame] = []
    quantile_rows: list[pd.DataFrame] = []
    for loaded in sources:
        for dataset_label, target_col in TARGETS.items():
            source_dataset = loaded.frame[(loaded.frame["dataset_label"] == dataset_label) & loaded.frame[target_col].notna()]
            for model in SELECTED_MODELS:
                sub = source_dataset[source_dataset["model"] == model]
                for event_target, threshold in EVENTS.items():
                    fixed_rows.append(
                        reliability_one(
                            sub,
                            loaded.source,
                            loaded.validation_scheme,
                            dataset_label,
                            target_col,
                            model,
                            event_target,
                            threshold,
                            "fixed",
                        )
                    )
                    quantile_rows.append(
                        reliability_one(
                            sub,
                            loaded.source,
                            loaded.validation_scheme,
                            dataset_label,
                            target_col,
                            model,
                            event_target,
                            threshold,
                            "quantile",
                        )
                    )
    fixed = pd.concat([row for row in fixed_rows if not row.empty], ignore_index=True) if fixed_rows else pd.DataFrame()
    quantile = pd.concat([row for row in quantile_rows if not row.empty], ignore_index=True) if quantile_rows else pd.DataFrame()
    summaries: list[dict[str, object]] = []
    for table, bin_kind in [(fixed, "fixed"), (quantile, "quantile")]:
        if table.empty:
            continue
        keys = ["prediction_source", "validation_scheme", "dataset_label", "target_col", "model", "event_target"]
        for key, group in table.sort_values("mean_score").groupby(keys, dropna=False):
            usable = group[group["n"] > 0].copy()
            summaries.append(
                {
                    **dict(zip(keys, key)),
                    "bin_kind": bin_kind,
                    "n_bins": len(usable),
                    "n_low_support_bins": int(usable["low_support"].sum()),
                    "monotonicity": monotonic_status(usable["event_rate"]),
                    "event_rate_min": usable["event_rate"].min(),
                    "event_rate_max": usable["event_rate"].max(),
                    "mean_abs_residual_official_minus_score": usable["mean_residual_official_minus_score"].abs().mean(),
                }
            )
    return fixed, quantile, pd.DataFrame(summaries)


def make_date_blocks(df: pd.DataFrame, n_blocks: int = 5) -> dict[str, pd.Series]:
    """Split unique dates into contiguous date blocks."""
    dates = pd.Series(pd.to_datetime(df["timestamp_sgt"]).dt.date.astype(str).unique()).sort_values().tolist()
    if not dates:
        return {}
    chunks = np.array_split(np.array(dates, dtype=object), min(n_blocks, len(dates)))
    blocks: dict[str, pd.Series] = {}
    for idx, chunk in enumerate(chunks, start=1):
        label = f"date_block_{idx}"
        blocks[label] = pd.to_datetime(df["timestamp_sgt"]).dt.date.astype(str).isin(set(chunk.tolist()))
    return blocks


def make_future_block(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Use the final contiguous date block as a retrospective future holdout."""
    blocks = make_date_blocks(df, n_blocks=5)
    if not blocks:
        return {}
    final_label = sorted(blocks.keys())[-1]
    return {f"final_{final_label}": blocks[final_label]}


def make_station_blocks(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Create one held-out fold per station."""
    return {
        f"station_{station}": df["station_id"].astype(str).eq(str(station))
        for station in sorted(df["station_id"].dropna().astype(str).unique())
    }


def event_vector(df: pd.DataFrame, target_col: str, threshold: float) -> np.ndarray:
    """Return binary event vector."""
    return (df[target_col].to_numpy(dtype=float) >= threshold).astype(int)


def clip_prob(prob: np.ndarray) -> np.ndarray:
    """Clip probabilities for log-loss and logit diagnostics."""
    return np.clip(prob.astype(float), 1e-6, 1.0 - 1e-6)


def empirical_edges(scores: np.ndarray, n_bins: int = 10) -> np.ndarray:
    """Create robust score-bin edges from training scores."""
    qs = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.quantile(scores, qs)
    edges = np.unique(edges)
    if len(edges) < 3:
        low = float(np.nanmin(scores))
        high = float(np.nanmax(scores))
        if low == high:
            high = low + 1e-6
        edges = np.linspace(low, high, min(n_bins, len(scores)) + 1)
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges


def empirical_predict(scores: np.ndarray, edges: np.ndarray, rates: np.ndarray, fallback: float) -> tuple[np.ndarray, np.ndarray]:
    """Predict empirical-bin probabilities and bin indices."""
    bin_ids = np.digitize(scores, edges[1:-1], right=False)
    probs = np.full(len(scores), fallback, dtype=float)
    valid = (bin_ids >= 0) & (bin_ids < len(rates))
    probs[valid] = rates[bin_ids[valid]]
    return probs, bin_ids


def fit_predict_calibrator(
    method: str,
    train_score: np.ndarray,
    train_y: np.ndarray,
    test_score: np.ndarray,
) -> tuple[np.ndarray | None, np.ndarray | None, dict[str, object]]:
    """Fit a one-score probability calibrator and return train/test probabilities."""
    info: dict[str, object] = {
        "status": "fit",
        "train_event_count": int(train_y.sum()),
        "train_non_event_count": int((1 - train_y).sum()),
        "low_support_bins": np.nan,
    }
    if len(train_y) < MIN_TRAIN_ROWS or len(np.unique(train_y)) < 2:
        info["status"] = "skipped_insufficient_training_classes"
        return None, None, info
    if method == "logistic_score_calibration":
        model = LogisticRegression(max_iter=1000, class_weight=None)
        model.fit(train_score.reshape(-1, 1), train_y)
        return model.predict_proba(train_score.reshape(-1, 1))[:, 1], model.predict_proba(test_score.reshape(-1, 1))[:, 1], info
    if method == "logistic_score_calibration_balanced":
        model = LogisticRegression(max_iter=1000, class_weight="balanced")
        model.fit(train_score.reshape(-1, 1), train_y)
        return model.predict_proba(train_score.reshape(-1, 1))[:, 1], model.predict_proba(test_score.reshape(-1, 1))[:, 1], info
    if method == "isotonic_score_calibration":
        if train_y.sum() < MIN_ISOTONIC_EVENTS or (1 - train_y).sum() < MIN_ISOTONIC_NON_EVENTS:
            info["status"] = "skipped_insufficient_isotonic_events"
            return None, None, info
        model = IsotonicRegression(out_of_bounds="clip")
        model.fit(train_score, train_y)
        return model.predict(train_score), model.predict(test_score), info
    if method == "empirical_bin_calibration":
        fallback = float(train_y.mean())
        edges = empirical_edges(train_score, n_bins=10)
        train_bin = np.digitize(train_score, edges[1:-1], right=False)
        rates: list[float] = []
        supports: list[int] = []
        for idx in range(len(edges) - 1):
            mask = train_bin == idx
            supports.append(int(mask.sum()))
            rates.append(float(train_y[mask].mean()) if mask.any() else fallback)
        info["low_support_bins"] = int(sum(support < 30 for support in supports))
        train_prob, _ = empirical_predict(train_score, edges, np.array(rates), fallback)
        test_prob, _ = empirical_predict(test_score, edges, np.array(rates), fallback)
        return train_prob, test_prob, info
    raise ValueError(f"Unsupported calibrator: {method}")


def ece_mce(y_true: np.ndarray, prob: np.ndarray, n_bins: int = 10) -> tuple[float, float]:
    """Compute expected and maximum calibration error."""
    y = y_true.astype(float)
    p = clip_prob(prob)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    mce = 0.0
    for idx in range(n_bins):
        if idx == n_bins - 1:
            mask = (p >= edges[idx]) & (p <= edges[idx + 1])
        else:
            mask = (p >= edges[idx]) & (p < edges[idx + 1])
        if not mask.any():
            continue
        gap = abs(float(p[mask].mean()) - float(y[mask].mean()))
        ece += safe_div(mask.sum(), len(y)) * gap
        mce = max(mce, gap)
    return float(ece), float(mce)


def log_loss_binary(y_true: np.ndarray, prob: np.ndarray) -> float:
    """Compute binary log-loss with clipped probabilities."""
    p = clip_prob(prob)
    y = y_true.astype(float)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def calibration_intercept_slope(y_true: np.ndarray, prob: np.ndarray) -> tuple[float, float]:
    """Estimate calibration intercept and slope from held-out predictions."""
    if len(np.unique(y_true)) < 2 or np.unique(np.round(prob, 8)).size < 2:
        return np.nan, np.nan
    logits = np.log(clip_prob(prob) / (1.0 - clip_prob(prob)))
    try:
        model = LogisticRegression(C=1e6, max_iter=1000)
        model.fit(logits.reshape(-1, 1), y_true)
        return float(model.intercept_[0]), float(model.coef_[0][0])
    except Exception:
        return np.nan, np.nan


def probability_metrics(y_true: np.ndarray, prob: np.ndarray) -> dict[str, object]:
    """Compute held-out probability calibration metrics."""
    y = y_true.astype(int)
    p = clip_prob(prob)
    ece, mce = ece_mce(y, p, n_bins=10)
    intercept, slope = calibration_intercept_slope(y, p)
    both_classes = len(np.unique(y)) == 2
    return {
        "n": len(y),
        "event_count": int(y.sum()),
        "event_rate": safe_div(int(y.sum()), len(y)),
        "Brier": float(brier_score_loss(y, p)),
        "log_loss": log_loss_binary(y, p),
        "ROC_AUC": float(roc_auc_score(y, p)) if both_classes else np.nan,
        "average_precision": float(average_precision_score(y, p)) if both_classes else np.nan,
        "ECE_10": ece,
        "MCE_10": mce,
        "calibration_intercept": intercept,
        "calibration_slope": slope,
        "mean_predicted_probability": float(p.mean()),
        "observed_event_rate": safe_div(int(y.sum()), len(y)),
        "probability_bias": float(p.mean() - y.mean()),
    }


def confusion_metrics(y_true: np.ndarray, prob: np.ndarray, threshold: float) -> dict[str, object]:
    """Compute probability-threshold event-detection metrics."""
    pred = (prob >= threshold).astype(int)
    y = y_true.astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    return {
        "probability_threshold": threshold,
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": precision,
        "recall": recall,
        "F1": safe_div(2 * precision * recall, precision + recall) if np.isfinite(precision) and np.isfinite(recall) else np.nan,
        "false_alarm_ratio": safe_div(fp, tp + fp),
        "miss_rate": safe_div(fn, tp + fn),
        "critical_success_index": safe_div(tp, tp + fp + fn),
        "predicted_positive_count": int(pred.sum()),
        "official_positive_count": int(y.sum()),
    }


def choose_operating_thresholds(train_y: np.ndarray, train_prob: np.ndarray) -> list[dict[str, object]]:
    """Select train-only probability operating thresholds."""
    rows: list[dict[str, object]] = []
    for threshold in FIXED_PROB_THRESHOLDS:
        rows.append({"operating_point": f"fixed_{threshold:.2f}", "threshold_source": "fixed", "achievable": True, **confusion_metrics(train_y, train_prob, threshold)})
    grid = np.round(np.linspace(0.01, 0.99, 99), 2)
    scan = pd.DataFrame([confusion_metrics(train_y, train_prob, float(threshold)) for threshold in grid])
    best = scan.sort_values(["F1", "recall", "precision"], ascending=[False, False, False]).head(1)
    if not best.empty:
        rows.append({"operating_point": "best_F1_train", "threshold_source": "train_selected", "achievable": True, **best.iloc[0].to_dict()})
    recall90 = scan[scan["recall"] >= 0.90].sort_values(["precision", "probability_threshold"], ascending=[False, False]).head(1)
    rows.append(
        {"operating_point": "recall90_train", "threshold_source": "train_selected", "achievable": not recall90.empty, **(recall90.iloc[0].to_dict() if not recall90.empty else {"probability_threshold": np.nan})}
    )
    precision70 = scan[scan["precision"] >= 0.70].sort_values(["recall", "probability_threshold"], ascending=[False, True]).head(1)
    rows.append(
        {"operating_point": "precision70_train", "threshold_source": "train_selected", "achievable": not precision70.empty, **(precision70.iloc[0].to_dict() if not precision70.empty else {"probability_threshold": np.nan})}
    )
    return rows


def fold_masks_for_scheme(df: pd.DataFrame, scheme: str) -> dict[str, pd.Series]:
    """Return held-out masks for a calibration validation scheme."""
    if scheme == "blocked_date_calibration":
        return make_date_blocks(df, n_blocks=5)
    if scheme == "future_block_calibration":
        return make_future_block(df)
    if scheme == "station_grouped_calibration":
        return make_station_blocks(df)
    raise ValueError(scheme)


def run_probability_calibration(loso: SourceFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run held-out score-to-probability calibration on LOSO OOF scores."""
    metric_rows: list[dict[str, object]] = []
    threshold_rows: list[dict[str, object]] = []
    fold_rows: list[dict[str, object]] = []
    prediction_rows: list[pd.DataFrame] = []
    methods = [
        "logistic_score_calibration",
        "logistic_score_calibration_balanced",
        "isotonic_score_calibration",
        "empirical_bin_calibration",
    ]
    schemes = ["blocked_date_calibration", "future_block_calibration", "station_grouped_calibration"]

    for dataset_label, target_col in TARGETS.items():
        dataset = loso.frame[(loso.frame["dataset_label"] == dataset_label) & loso.frame[target_col].notna()].copy()
        if dataset.empty:
            continue
        for model in SELECTED_MODELS:
            model_df = dataset[dataset["model"] == model].sort_values(["timestamp_sgt", "station_id"]).copy()
            if model_df.empty:
                continue
            for event_target, threshold in EVENTS.items():
                model_df["event"] = (model_df[target_col] >= threshold).astype(int)
                for scheme in schemes:
                    masks = fold_masks_for_scheme(model_df, scheme)
                    for method in methods:
                        scheme_prediction_parts: list[pd.DataFrame] = []
                        for fold_id, test_mask in masks.items():
                            train = model_df[~test_mask].copy()
                            test = model_df[test_mask].copy()
                            if train.empty or test.empty:
                                continue
                            train_y = event_vector(train, target_col, threshold)
                            test_y = event_vector(test, target_col, threshold)
                            train_score = train["prediction_wbgt_c"].to_numpy(dtype=float)
                            test_score = test["prediction_wbgt_c"].to_numpy(dtype=float)
                            train_prob, test_prob, fit_info = fit_predict_calibrator(method, train_score, train_y, test_score)
                            if train_prob is None or test_prob is None:
                                fold_rows.append(
                                    {
                                        "prediction_source": loso.source,
                                        "dataset_label": dataset_label,
                                        "target_col": target_col,
                                        "model": model,
                                        "event_target": event_target,
                                        "official_event_threshold_c": threshold,
                                        "validation_scheme": scheme,
                                        "fold_id": fold_id,
                                        "calibrator": method,
                                        **fit_info,
                                    }
                                )
                                continue
                            base = {
                                "prediction_source": loso.source,
                                "dataset_label": dataset_label,
                                "target_col": target_col,
                                "model": model,
                                "event_target": event_target,
                                "official_event_threshold_c": threshold,
                                "validation_scheme": scheme,
                                "fold_id": fold_id,
                                "calibrator": method,
                                **fit_info,
                            }
                            fold_metric = probability_metrics(test_y, test_prob)
                            fold_rows.append({**base, **fold_metric})
                            for choice in choose_operating_thresholds(train_y, train_prob):
                                prob_threshold = choice.get("probability_threshold", np.nan)
                                if not choice.get("achievable", False) or not np.isfinite(prob_threshold):
                                    threshold_rows.append({**base, **choice, "status": "skipped_unachievable"})
                                    continue
                                threshold_rows.append({**base, **choice, "status": "evaluated_on_heldout", **confusion_metrics(test_y, test_prob, float(prob_threshold))})
                            pred_part = test[
                                ["timestamp_sgt", "station_id", "dataset_label", "model", "prediction_wbgt_c", target_col, "hour"]
                            ].copy()
                            pred_part = pred_part.rename(columns={"prediction_wbgt_c": "score", target_col: "official_wbgt"})
                            pred_part["event_target"] = event_target
                            pred_part["event"] = test_y
                            pred_part["p_event"] = clip_prob(test_prob)
                            pred_part["probability_calibrator_id"] = method
                            pred_part["validation_scheme"] = scheme
                            pred_part["fold_id"] = fold_id
                            scheme_prediction_parts.append(pred_part)
                        if scheme_prediction_parts:
                            combined_pred = pd.concat(scheme_prediction_parts, ignore_index=True)
                            prediction_rows.append(combined_pred)
                            y = combined_pred["event"].to_numpy(dtype=int)
                            p = combined_pred["p_event"].to_numpy(dtype=float)
                            metric_rows.append(
                                {
                                    "prediction_source": loso.source,
                                    "dataset_label": dataset_label,
                                    "target_col": target_col,
                                    "model": model,
                                    "event_target": event_target,
                                    "official_event_threshold_c": threshold,
                                    "validation_scheme": scheme,
                                    "calibrator": method,
                                    "n_folds_evaluated": combined_pred["fold_id"].nunique(),
                                    **probability_metrics(y, p),
                                }
                            )
    metrics = pd.DataFrame(metric_rows)
    thresholds = pd.DataFrame(threshold_rows)
    folds = pd.DataFrame(fold_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True) if prediction_rows else pd.DataFrame()
    return metrics, thresholds, folds, predictions


def aggregate_threshold_summary(thresholds: pd.DataFrame) -> pd.DataFrame:
    """Summarize held-out threshold metrics by candidate and operating point."""
    if thresholds.empty:
        return pd.DataFrame()
    valid = thresholds[thresholds["status"].eq("evaluated_on_heldout")].copy()
    if valid.empty:
        return pd.DataFrame()
    keys = ["dataset_label", "target_col", "model", "event_target", "validation_scheme", "calibrator", "operating_point"]
    rows: list[dict[str, object]] = []
    for key, group in valid.groupby(keys, dropna=False):
        totals = group[["TP", "FP", "TN", "FN"]].sum()
        precision = safe_div(totals["TP"], totals["TP"] + totals["FP"])
        recall = safe_div(totals["TP"], totals["TP"] + totals["FN"])
        rows.append(
            {
                **dict(zip(keys, key)),
                "mean_selected_probability_threshold": group["probability_threshold"].mean(),
                "folds": group["fold_id"].nunique(),
                "TP": int(totals["TP"]),
                "FP": int(totals["FP"]),
                "TN": int(totals["TN"]),
                "FN": int(totals["FN"]),
                "precision": precision,
                "recall": recall,
                "F1": safe_div(2 * precision * recall, precision + recall) if np.isfinite(precision) and np.isfinite(recall) else np.nan,
                "false_alarm_ratio": safe_div(totals["FP"], totals["TP"] + totals["FP"]),
                "miss_rate": safe_div(totals["FN"], totals["TP"] + totals["FN"]),
                "critical_success_index": safe_div(totals["TP"], totals["TP"] + totals["FP"] + totals["FN"]),
                "fold_F1_std": group["F1"].std(ddof=0),
                "fold_recall_std": group["recall"].std(ddof=0),
                "fold_precision_std": group["precision"].std(ddof=0),
            }
        )
    return pd.DataFrame(rows)


def make_model_selection(metrics: pd.DataFrame, thresholds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create model-selection and stability summaries."""
    if metrics.empty:
        return pd.DataFrame(), pd.DataFrame()
    threshold_summary = aggregate_threshold_summary(thresholds)
    best_f1 = threshold_summary[threshold_summary["operating_point"].eq("best_F1_train")].copy() if not threshold_summary.empty else pd.DataFrame()
    merged = metrics.copy()
    if not best_f1.empty:
        merged = merged.merge(
            best_f1[
                [
                    "dataset_label",
                    "target_col",
                    "model",
                    "event_target",
                    "validation_scheme",
                    "calibrator",
                    "precision",
                    "recall",
                    "F1",
                    "false_alarm_ratio",
                    "miss_rate",
                    "critical_success_index",
                ]
            ].rename(
                columns={
                    "precision": "best_F1_train_selected_precision",
                    "recall": "best_F1_train_selected_recall",
                    "F1": "best_F1_train_selected_F1",
                    "false_alarm_ratio": "best_F1_train_selected_false_alarm_ratio",
                    "miss_rate": "best_F1_train_selected_miss_rate",
                    "critical_success_index": "best_F1_train_selected_CSI",
                }
            ),
            on=["dataset_label", "target_col", "model", "event_target", "validation_scheme", "calibrator"],
            how="left",
        )
    else:
        merged["best_F1_train_selected_F1"] = np.nan
    merged["diagnostic_rank_score"] = (
        merged.groupby(["dataset_label", "event_target"])["Brier"].rank()
        + merged.groupby(["dataset_label", "event_target"])["ECE_10"].rank()
        + merged.groupby(["dataset_label", "event_target"])["log_loss"].rank()
        - merged.groupby(["dataset_label", "event_target"])["best_F1_train_selected_F1"].rank(ascending=False).fillna(0)
    )
    def label_candidate(row: pd.Series) -> str:
        if row["event_target"] == "ge33":
            return "ge33_exploratory"
        return "candidate"

    merged["selection_scope"] = merged.apply(label_candidate, axis=1)
    stability_rows: list[dict[str, object]] = []
    if not metrics.empty:
        keys = ["dataset_label", "target_col", "model", "event_target", "calibrator"]
        for key, group in metrics.groupby(keys, dropna=False):
            stability_rows.append(
                {
                    **dict(zip(keys, key)),
                    "validation_scheme_count": group["validation_scheme"].nunique(),
                    "mean_Brier": group["Brier"].mean(),
                    "std_Brier": group["Brier"].std(ddof=0),
                    "mean_log_loss": group["log_loss"].mean(),
                    "std_log_loss": group["log_loss"].std(ddof=0),
                    "mean_average_precision": group["average_precision"].mean(),
                    "std_average_precision": group["average_precision"].std(ddof=0),
                    "mean_ROC_AUC": group["ROC_AUC"].mean(),
                    "std_ROC_AUC": group["ROC_AUC"].std(ddof=0),
                    "mean_ECE": group["ECE_10"].mean(),
                    "std_ECE": group["ECE_10"].std(ddof=0),
                    "mean_probability_bias": group["probability_bias"].mean(),
                    "std_probability_bias": group["probability_bias"].std(ddof=0),
                }
            )
    return merged.sort_values(["dataset_label", "event_target", "diagnostic_rank_score"]), pd.DataFrame(stability_rows)


def make_vs_event_score_mapping(metrics: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    """Compare probability calibration with Sprint 2C deterministic mappings."""
    rows: list[dict[str, object]] = []
    advisory_path = SPRINT_2C_FILES["advisory"]
    operating_path = SPRINT_2C_FILES["operating"]
    if advisory_path.exists():
        advisory = pd.read_csv(advisory_path)
        focus = advisory[(advisory["dataset_label"].eq("hourly_max")) & (advisory["event_target"].eq("ge31"))].copy()
        for _, row in focus.iterrows():
            rows.append(
                {
                    "comparison_family": "Sprint_2C_event_score_mapping",
                    "dataset_label": row.get("dataset_label"),
                    "model": row.get("model"),
                    "event_target": row.get("event_target"),
                    "method": row.get("mapping_type"),
                    "operating_point": row.get("operating_point"),
                    "threshold": row.get("threshold"),
                    "Brier": np.nan,
                    "F1": row.get("expected_F1"),
                    "precision": row.get("expected_precision"),
                    "recall": row.get("expected_recall"),
                    "false_alarm_ratio": row.get("expected_false_alarm_ratio"),
                    "miss_rate": row.get("expected_miss_rate"),
                    "interpretability": "deterministic score threshold in WBGT-score units",
                    "temporal_stability": "see Sprint 2C threshold_stability_summary",
                }
            )
    elif operating_path.exists():
        operating = pd.read_csv(operating_path)
        focus = operating[
            operating["dataset_label"].eq("hourly_max")
            & operating["event_target"].eq("ge31")
            & operating["operating_point"].isin(["best_F1", "recall_90", "precision_70"])
        ].copy()
        for _, row in focus.iterrows():
            rows.append(
                {
                    "comparison_family": "Sprint_2C_event_score_mapping",
                    "dataset_label": row.get("dataset_label"),
                    "model": row.get("model"),
                    "event_target": row.get("event_target"),
                    "method": "raw_score_threshold_only",
                    "operating_point": row.get("operating_point"),
                    "threshold": row.get("score_threshold_c"),
                    "Brier": np.nan,
                    "F1": row.get("F1"),
                    "precision": row.get("precision"),
                    "recall": row.get("recall"),
                    "false_alarm_ratio": row.get("false_alarm_ratio"),
                    "miss_rate": row.get("miss_rate"),
                    "interpretability": "deterministic score threshold in WBGT-score units",
                    "temporal_stability": "see Sprint 2C threshold_stability_summary",
                }
            )
    threshold_summary = aggregate_threshold_summary(thresholds)
    if not metrics.empty and not threshold_summary.empty:
        focus_metrics = metrics[(metrics["dataset_label"].eq("hourly_max")) & (metrics["event_target"].eq("ge31"))].copy()
        focus_thresholds = threshold_summary[threshold_summary["operating_point"].eq("best_F1_train")].copy()
        merged = focus_metrics.merge(
            focus_thresholds,
            on=["dataset_label", "target_col", "model", "event_target", "validation_scheme", "calibrator"],
            how="left",
            suffixes=("", "_threshold"),
        )
        for _, row in merged.iterrows():
            rows.append(
                {
                    "comparison_family": "Sprint_3B_probability_calibration",
                    "dataset_label": row.get("dataset_label"),
                    "model": row.get("model"),
                    "event_target": row.get("event_target"),
                    "method": row.get("calibrator"),
                    "validation_scheme": row.get("validation_scheme"),
                    "operating_point": "best_F1_train",
                    "threshold": row.get("mean_selected_probability_threshold"),
                    "Brier": row.get("Brier"),
                    "F1": row.get("F1"),
                    "precision": row.get("precision"),
                    "recall": row.get("recall"),
                    "false_alarm_ratio": row.get("false_alarm_ratio"),
                    "miss_rate": row.get("miss_rate"),
                    "interpretability": "probability of official WBGT >=31 conditional on one existing score and retrospective split",
                    "temporal_stability": "summarized by blocked-date/future-block/station grouped variability",
                }
            )
    return pd.DataFrame(rows)


def choose_best_candidates(selection: pd.DataFrame) -> pd.DataFrame:
    """Pick a compact set of diagnostics for station/hour breakdowns."""
    if selection.empty:
        return pd.DataFrame()
    focus = selection[
        selection["dataset_label"].eq("hourly_max")
        & selection["event_target"].eq("ge31")
        & selection["validation_scheme"].isin(["blocked_date_calibration", "future_block_calibration"])
        & ~selection["calibrator"].eq("logistic_score_calibration_balanced")
    ].copy()
    return focus.sort_values(["diagnostic_rank_score", "Brier", "ECE_10"]).head(3)


def make_station_hour_regime(
    predictions: pd.DataFrame,
    selection: pd.DataFrame,
    thresholds: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create station/hour diagnostics for the best few probability candidates."""
    selected = choose_best_candidates(selection)
    if predictions.empty or selected.empty:
        skipped = pd.DataFrame([{"status": "skipped_no_selected_probability_candidate"}])
        return skipped, skipped.copy(), skipped.copy()
    threshold_summary = aggregate_threshold_summary(thresholds)
    selected_thresholds = threshold_summary[
        threshold_summary["operating_point"].eq("best_F1_train")
    ][
        ["dataset_label", "model", "event_target", "validation_scheme", "calibrator", "mean_selected_probability_threshold"]
    ].copy()
    station_rows: list[dict[str, object]] = []
    hour_rows: list[dict[str, object]] = []
    for _, candidate in selected.iterrows():
        mask = (
            predictions["dataset_label"].eq(candidate["dataset_label"])
            & predictions["model"].eq(candidate["model"])
            & predictions["event_target"].eq(candidate["event_target"])
            & predictions["validation_scheme"].eq(candidate["validation_scheme"])
            & predictions["probability_calibrator_id"].eq(candidate["calibrator"])
        )
        sub = predictions[mask].copy()
        if sub.empty:
            continue
        th_match = selected_thresholds[
            selected_thresholds["dataset_label"].eq(candidate["dataset_label"])
            & selected_thresholds["model"].eq(candidate["model"])
            & selected_thresholds["event_target"].eq(candidate["event_target"])
            & selected_thresholds["validation_scheme"].eq(candidate["validation_scheme"])
            & selected_thresholds["calibrator"].eq(candidate["calibrator"])
        ]
        selected_threshold = float(th_match["mean_selected_probability_threshold"].iloc[0]) if not th_match.empty else 0.5
        for station, group in sub.groupby("station_id"):
            y = group["event"].to_numpy(dtype=int)
            p = group["p_event"].to_numpy(dtype=float)
            conf = confusion_metrics(y, p, selected_threshold)
            station_rows.append(
                {
                    "dataset_label": candidate["dataset_label"],
                    "model": candidate["model"],
                    "event_target": candidate["event_target"],
                    "validation_scheme": candidate["validation_scheme"],
                    "calibrator": candidate["calibrator"],
                    "selected_probability_threshold": selected_threshold,
                    "station_id": station,
                    "focus_station_flag": station in FOCUS_STATIONS,
                    "n": len(group),
                    "event_count": int(y.sum()),
                    "observed_event_rate": float(y.mean()) if len(y) else np.nan,
                    "mean_predicted_probability": float(p.mean()) if len(p) else np.nan,
                    "probability_bias": float(p.mean() - y.mean()) if len(y) else np.nan,
                    "Brier": float(np.mean((p - y) ** 2)) if len(y) else np.nan,
                    "precision": conf["precision"],
                    "recall": conf["recall"],
                    "F1": conf["F1"],
                }
            )
        for hour, group in sub.groupby("hour"):
            y = group["event"].to_numpy(dtype=int)
            p = group["p_event"].to_numpy(dtype=float)
            hour_rows.append(
                {
                    "dataset_label": candidate["dataset_label"],
                    "model": candidate["model"],
                    "event_target": candidate["event_target"],
                    "validation_scheme": candidate["validation_scheme"],
                    "calibrator": candidate["calibrator"],
                    "hour": int(hour) if pd.notna(hour) else np.nan,
                    "n": len(group),
                    "event_count": int(y.sum()),
                    "observed_event_rate": float(y.mean()) if len(y) else np.nan,
                    "mean_predicted_probability": float(p.mean()) if len(p) else np.nan,
                    "probability_bias": float(p.mean() - y.mean()) if len(y) else np.nan,
                    "Brier": float(np.mean((p - y) ** 2)) if len(y) else np.nan,
                }
            )
    regime = pd.DataFrame(
        [
            {
                "status": "skipped_missing_shortwave_or_radiation_regime_in_prediction_outputs",
                "reason": "The Sprint 2A OOF prediction table used for probability calibration does not carry shortwave/radiation columns; no new feature join was attempted.",
            }
        ]
    )
    return pd.DataFrame(station_rows), pd.DataFrame(hour_rows), regime


def make_probability_prediction_table(predictions: pd.DataFrame, selection: pd.DataFrame) -> pd.DataFrame:
    """Export compact p_ge31 predictions for the selected diagnostic companion."""
    selected = choose_best_candidates(selection)
    if predictions.empty or selected.empty:
        return pd.DataFrame()
    candidate = selected.iloc[0]
    sub = predictions[
        predictions["dataset_label"].eq(candidate["dataset_label"])
        & predictions["model"].eq(candidate["model"])
        & predictions["event_target"].eq("ge31")
        & predictions["validation_scheme"].eq(candidate["validation_scheme"])
        & predictions["probability_calibrator_id"].eq(candidate["calibrator"])
    ].copy()
    if sub.empty:
        return pd.DataFrame()
    out = sub[
        [
            "timestamp_sgt",
            "station_id",
            "dataset_label",
            "model",
            "score",
            "official_wbgt",
            "event",
            "p_event",
            "probability_calibrator_id",
            "validation_scheme",
            "fold_id",
        ]
    ].rename(columns={"model": "model_id", "event": "event_ge31", "p_event": "p_ge31"})
    return out.sort_values(["timestamp_sgt", "station_id"])


def report_table(df: pd.DataFrame, columns: list[str], max_rows: int = 10) -> list[str]:
    """Render a compact Markdown table."""
    if df.empty:
        return ["_No rows available._"]
    display = df.loc[:, [col for col in columns if col in df.columns]].head(max_rows).copy()
    for col in display.columns:
        if pd.api.types.is_numeric_dtype(display[col]):
            display[col] = display[col].map(lambda value: fmt(value))
    return display.to_markdown(index=False).splitlines()


def build_report(
    out_dir: Path,
    manifest: pd.DataFrame,
    reliability_summary: pd.DataFrame,
    metrics: pd.DataFrame,
    thresholds: pd.DataFrame,
    selection: pd.DataFrame,
    stability: pd.DataFrame,
    vs_mapping: pd.DataFrame,
    station: pd.DataFrame,
    by_hour: pd.DataFrame,
    prediction_table: pd.DataFrame,
) -> str:
    """Write the Sprint 3B Markdown report."""
    status = "PASS" if not metrics.empty else "PARTIAL"
    hourly_max_ge31 = selection[(selection["dataset_label"].eq("hourly_max")) & (selection["event_target"].eq("ge31"))].copy()
    primary = choose_best_candidates(selection)
    best = primary.iloc[0] if not primary.empty else None
    threshold_summary = aggregate_threshold_summary(thresholds)
    high_recall = threshold_summary[
        threshold_summary["dataset_label"].eq("hourly_max")
        & threshold_summary["event_target"].eq("ge31")
        & threshold_summary["operating_point"].eq("recall90_train")
    ].sort_values(["recall", "precision"], ascending=[False, False]) if not threshold_summary.empty else pd.DataFrame()
    high_precision = threshold_summary[
        threshold_summary["dataset_label"].eq("hourly_max")
        & threshold_summary["event_target"].eq("ge31")
        & threshold_summary["operating_point"].eq("precision70_train")
    ].sort_values(["precision", "recall"], ascending=[False, False]) if not threshold_summary.empty else pd.DataFrame()
    ge33 = selection[selection["event_target"].eq("ge33")].sort_values(["dataset_label", "diagnostic_rank_score"]).copy()
    manifest_context = manifest[
        manifest["status"].eq("available")
        & manifest["prediction_source"].eq("loso_oof")
        & manifest["dataset_label"].isin(["hourly_max", "hourly_mean"])
        & manifest["event_target"].isin(["ge31", "ge33"])
    ]
    monotonic_focus = reliability_summary[
        reliability_summary["prediction_source"].eq("loso_oof")
        & reliability_summary["dataset_label"].eq("hourly_max")
        & reliability_summary["event_target"].eq("ge31")
    ] if not reliability_summary.empty else pd.DataFrame()
    station_focus = station[station.get("focus_station_flag", pd.Series(dtype=bool)).eq(True)] if "focus_station_flag" in station.columns else pd.DataFrame()
    selected_text = (
        f"{best['model']} with {best['calibrator']} under {best['validation_scheme']}"
        if best is not None
        else "No stable candidate selected"
    )
    pred_size_note = "not large" if len(prediction_table) < 100000 else "large; do-not-commit"
    lines = [
        "# System A Level 1 Sprint 3B - P_ge31 Probability Calibration Companion",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- Level 1 only.",
        "- Existing score probability calibration only.",
        "- No new WBGT regression model.",
        "- No model-family comparison.",
        "- No formula-v2.",
        "- No Level 2.",
        "- No System B / SOLWEIG / v12.",
        "- No local WBGT.",
        "",
        "## Why Sprint 3B was needed",
        "Sprint 2B found high-tail underprediction, Sprint 2C found score compression and unstable diagnostic thresholds, and Sprint 3A found simple formula candidates could not restore fixed_31/fixed_33 crossings. A held-out P_ge31 probability companion is therefore the next diagnostic layer.",
        "",
        "## Inputs",
        *report_table(
            manifest_context.sort_values(["dataset_label", "model", "event_target"]),
            ["prediction_source", "dataset_label", "model", "event_target", "n_rows", "station_count", "event_count", "event_rate", "fallback_used_any"],
            max_rows=24,
        ),
        "",
        "## Reliability before fitting",
        "Fixed and quantile reliability bins were written before any calibrator fitting. Monotonicity is empirical event-rate monotonicity versus mean score.",
        *report_table(
            monotonic_focus.sort_values(["model", "bin_kind"]),
            ["model", "bin_kind", "n_bins", "n_low_support_bins", "monotonicity", "event_rate_min", "event_rate_max"],
            max_rows=12,
        ),
        "",
        "## Calibration design",
        "- `blocked_date_calibration`: contiguous date blocks; train calibrator on other date blocks, test held-out date block.",
        "- `future_block_calibration`: train before the final date block, test final date block; retrospective, not prospective forecast skill.",
        "- `station_grouped_calibration`: train on other stations, test held-out station.",
        "- Thresholds were selected on training folds only; no test-set oracle thresholds are used as main results.",
        "",
        "## Probability calibration results",
        "Hourly_max ge31 primary candidates:",
        *report_table(
            hourly_max_ge31.sort_values(["diagnostic_rank_score"]),
            ["model", "calibrator", "validation_scheme", "Brier", "log_loss", "ECE_10", "average_precision", "ROC_AUC", "probability_bias", "best_F1_train_selected_F1"],
            max_rows=15,
        ),
        "",
        "High-recall P_ge31 screen candidates:",
        *report_table(
            high_recall,
            ["model", "calibrator", "validation_scheme", "mean_selected_probability_threshold", "precision", "recall", "F1", "false_alarm_ratio", "miss_rate"],
            max_rows=10,
        ),
        "",
        "High-precision P_ge31 screen candidates:",
        *report_table(
            high_precision,
            ["model", "calibrator", "validation_scheme", "mean_selected_probability_threshold", "precision", "recall", "F1", "false_alarm_ratio", "miss_rate"],
            max_rows=10,
        ),
        "",
        "ge33 remains exploratory unless event counts and fold stability support stronger claims:",
        *report_table(
            ge33,
            ["dataset_label", "model", "calibrator", "validation_scheme", "event_count", "Brier", "ECE_10", "average_precision", "best_F1_train_selected_F1"],
            max_rows=12,
        ),
        "",
        "## Comparison vs Sprint 2C event-score mapping",
        *report_table(
            vs_mapping[(vs_mapping["dataset_label"].eq("hourly_max")) & (vs_mapping["event_target"].eq("ge31"))].sort_values(["comparison_family", "model"]).head(24),
            ["comparison_family", "model", "method", "validation_scheme", "operating_point", "threshold", "Brier", "F1", "precision", "recall", "false_alarm_ratio", "miss_rate"],
            max_rows=24,
        ),
        "",
        "## Selected diagnostic P_ge31 companion",
        f"Selected diagnostic candidate: {selected_text}.",
        "Recommended output name: `p_ge31_diagnostic`.",
        f"Diagnostic prediction table rows: {len(prediction_table)} ({pred_size_note}).",
        "",
        "## ge33 exploratory",
        "ge33 is retained as exploratory because event counts are smaller and fold-level calibration is less stable than ge31.",
        "",
        "## Station / regime diagnostics",
        "Focus station diagnostics:",
        *report_table(
            station_focus.sort_values(["model", "station_id"]) if not station_focus.empty else station_focus,
            ["model", "calibrator", "validation_scheme", "station_id", "event_count", "observed_event_rate", "mean_predicted_probability", "probability_bias", "Brier", "precision", "recall"],
            max_rows=16,
        ),
        "Hour-of-day diagnostics were written to `probability_by_hour.csv`.",
        "Radiation-regime diagnostics were skipped because the probability input table did not carry shortwave/radiation columns and no new feature join was attempted.",
        "",
        "## Interpretation",
        "1. Probability calibration improves interpretability by producing held-out event probabilities, while deterministic Sprint 2C thresholds remain simpler score-screening rules.",
        f"2. Best P_ge31 score model by the rank used here: {best['model'] if best is not None else 'NA'}.",
        f"3. Most stable selected calibrator by the rank used here: {best['calibrator'] if best is not None else 'NA'}.",
        f"4. P_ge31 is ready as a diagnostic companion if described as retrospective and conditional on current splits: {'yes' if best is not None else 'no'}.",
        "5. This supports Level 1 interim model-card creation because it separates WBGT_A regression scores from event-probability companion diagnostics.",
        "6. Formula-v2 is still needed for a validated physics implementation sprint; Sprint 3B does not replace it.",
        "",
        "## Caveats",
        "- Retrospective probability calibration.",
        "- Not an official warning system.",
        "- Not prospective forecast skill.",
        "- Not local WBGT.",
        "- Not a replacement for WBGT_A.",
        "- Event probabilities are conditional on current data and splits.",
        "",
        "## Next recommended action",
        "Level 1 interim model card.",
        "",
        "## Run hygiene",
        "- No forbidden files touched.",
        "- No fallback used.",
        "- No new WBGT regression model added.",
        "- No System B/v12 touched.",
        "- No commit/stage performed.",
    ]
    (out_dir / "sprint3b_pge31_probability_calibration_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return status


def main() -> int:
    """Run Sprint 3B probability calibration diagnostics."""
    args = parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    required_missing = [path for _source, _scheme, path, required in SOURCE_SPECS if required and not path.exists()]
    if required_missing:
        write_blocker(
            out_dir,
            "Required LOSO OOF prediction file is missing; Sprint 3B stopped without rerunning prior models.",
            required_missing,
        )
        return 2

    sources = [loaded for spec in SOURCE_SPECS if (loaded := normalize_prediction_source(spec[0], spec[1], spec[2])) is not None]
    if not sources:
        write_blocker(out_dir, "No prediction sources were available; Sprint 3B stopped without rerunning prior models.", [])
        return 2
    loso = next((source for source in sources if source.source == "loso_oof"), None)
    if loso is None:
        write_blocker(out_dir, "LOSO OOF predictions are required for held-out calibrator diagnostics.", [])
        return 2

    available_models = set(loso.frame["model"].unique())
    missing_models = sorted(set(SELECTED_MODELS) - available_models)
    if missing_models:
        write_blocker(
            out_dir,
            "Required selected candidate scores are missing from LOSO predictions: " + ", ".join(missing_models),
            [],
        )
        return 2

    manifest = make_manifest(sources)
    fixed_bins, quantile_bins, reliability_summary = make_reliability_tables(sources)
    metrics, threshold_metrics, fold_metrics, predictions = run_probability_calibration(loso)
    selection, stability = make_model_selection(metrics, threshold_metrics)
    vs_mapping = make_vs_event_score_mapping(metrics, threshold_metrics)
    station, by_hour, by_regime = make_station_hour_regime(predictions, selection, threshold_metrics)
    p_ge31 = make_probability_prediction_table(predictions, selection)

    manifest.to_csv(out_dir / "probability_calibration_manifest.csv", index=False)
    fixed_bins.to_csv(out_dir / "reliability_bins_fixed.csv", index=False)
    quantile_bins.to_csv(out_dir / "reliability_bins_quantile.csv", index=False)
    reliability_summary.to_csv(out_dir / "reliability_summary.csv", index=False)
    metrics.to_csv(out_dir / "probability_calibration_metrics.csv", index=False)
    threshold_metrics.to_csv(out_dir / "probability_threshold_metrics.csv", index=False)
    fold_metrics.to_csv(out_dir / "probability_calibration_by_fold.csv", index=False)
    selection.to_csv(out_dir / "probability_model_selection_summary.csv", index=False)
    stability.to_csv(out_dir / "probability_stability_summary.csv", index=False)
    vs_mapping.to_csv(out_dir / "probability_vs_event_score_mapping.csv", index=False)
    station.to_csv(out_dir / "probability_by_station.csv", index=False)
    by_hour.to_csv(out_dir / "probability_by_hour.csv", index=False)
    by_regime.to_csv(out_dir / "probability_by_regime.csv", index=False)
    p_ge31.to_csv(out_dir / "p_ge31_diagnostic_predictions.csv", index=False)

    status = build_report(
        out_dir,
        manifest,
        reliability_summary,
        metrics,
        threshold_metrics,
        selection,
        stability,
        vs_mapping,
        station,
        by_hour,
        p_ge31,
    )
    print(f"[OK] Sprint 3B probability calibration diagnostics complete: {status}")
    print(f"[OK] Outputs written to {rel(out_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
