#!/usr/bin/env python
"""System A A-L1H.2 probability / threshold calibration diagnostics.

Inputs:
    - configs/v11/systema_l1h_probability_threshold_calibration.yaml
    - outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv
    - outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv
    - outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv
    - outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_threshold_metrics_31_33.csv

Outputs:
    - calibration_input_inventory.csv
    - calibration_analysis_input.csv
    - probability_predictions_oof.csv.gz
    - score_bin_event_rates.csv
    - reliability_bins_fixed.csv
    - reliability_bins_quantile.csv
    - probability_calibration_metrics.csv
    - threshold_operating_points.csv
    - threshold_by_station.csv
    - threshold_by_regime.csv
    - probability_threshold_calibration_report.md
    - A_L1H_2_STATUS.md

Saved metrics:
    - Input availability, selected LOSO validation rows, event counts, and fold
      usability.
    - Score-bin empirical event rates for existing M4/M7 score columns.
    - Station-held-out P(WBGT >= 31) and exploratory P(WBGT >= 33)
      probabilities from empirical-bin, logistic score-only, isotonic
      score-only, and optional diagnostic score+hour / score+radiation-hot
      calibrators.
    - Brier score, log loss, ROC-AUC, PR-AUC, calibration intercept/slope,
      fixed-bin and quantile-bin ECE/MCE, and probability spread.
    - Train-station-selected fixed_score_31, best_F1, recall_90, precision_70,
      max_Youden, and selected candidate policy operating points.
    - Threshold metrics by station and by radiation-hot / shortwave regime.

Scope guard:
    This script consumes existing OOF scores only. It does not retrain base
    WBGT models, implement formula-v2, implement high-tail regression, start
    A-L2, touch System B or SOLWEIG outputs, modify archive collector paths,
    stage, or commit files.
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised only on lean bundled runtimes.
    yaml = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
SGT_TZ = "Asia/Singapore"
EPS = 1e-6


@dataclass(frozen=True)
class CalibrationResult:
    """Headline result for the A-L1H.2 calibration run."""

    acceptance_status: str
    decision_status: str
    best_probability_candidate: str
    brier_pr_auc_reliability_headline: str
    recommended_operating_point: str
    station_regime_caveats: str
    next_recommended_action: str
    output_paths: list[Path]


@dataclass(frozen=True)
class LogisticFit:
    """Small fitted logistic model used to avoid external runtime dependencies."""

    coef: np.ndarray
    mean: np.ndarray
    scale: np.ndarray


def rel(path: Path) -> str:
    """Return a repo-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(raw_path: str) -> Path:
    """Resolve an absolute or repo-relative path."""
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


def parse_scalar(value: str) -> Any:
    """Parse the small scalar subset used by explicit lane YAML configs."""
    if value in {"", "null", "Null", "NULL"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the narrow YAML subset used by this lane's explicit config."""
    raw_lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        raw_lines.append((indent, raw.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(raw_lines):
            return {}, index
        if raw_lines[index][1].startswith("- "):
            values: list[Any] = []
            while index < len(raw_lines):
                line_indent, stripped = raw_lines[index]
                if line_indent != indent or not stripped.startswith("- "):
                    break
                item = stripped[2:].strip()
                index += 1
                if not item:
                    nested, index = parse_block(index, raw_lines[index][0])
                    values.append(nested)
                    continue
                key, separator, value = item.partition(":")
                if separator:
                    item_dict: dict[str, Any] = {}
                    if value.strip():
                        item_dict[key.strip()] = parse_scalar(value.strip())
                    elif index < len(raw_lines) and raw_lines[index][0] > line_indent:
                        nested, index = parse_block(index, raw_lines[index][0])
                        item_dict[key.strip()] = nested
                    else:
                        item_dict[key.strip()] = {}
                    if index < len(raw_lines) and raw_lines[index][0] > line_indent:
                        extra, index = parse_block(index, raw_lines[index][0])
                        if isinstance(extra, dict):
                            item_dict.update(extra)
                    values.append(item_dict)
                else:
                    values.append(parse_scalar(item))
            return values, index

        mapping: dict[str, Any] = {}
        while index < len(raw_lines):
            line_indent, stripped = raw_lines[index]
            if line_indent != indent or stripped.startswith("- "):
                break
            key, separator, value = stripped.partition(":")
            if not separator:
                raise ValueError(f"Unexpected YAML line: {stripped}")
            index += 1
            if value.strip():
                mapping[key.strip()] = parse_scalar(value.strip())
            elif index < len(raw_lines) and raw_lines[index][0] > line_indent:
                nested, index = parse_block(index, raw_lines[index][0])
                mapping[key.strip()] = nested
            else:
                mapping[key.strip()] = {}
        return mapping, index

    parsed, _ = parse_block(0, 0)
    if not isinstance(parsed, dict):
        raise ValueError("Config root must be a mapping.")
    return parsed


def load_config(path: Path) -> dict[str, Any]:
    """Read the A-L1H.2 YAML config."""
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return parse_simple_yaml(text)


def git_branch() -> str:
    """Return the active git branch when available."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def count_csv_rows(path: Path) -> int:
    """Count CSV data rows without retaining the file in memory."""
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return max(sum(1 for _ in f) - 1, 0)


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV, including gzip-compressed CSVs by extension."""
    return pd.read_csv(path, low_memory=False)


def safe_div(num: float, den: float) -> float:
    """Divide with NaN for zero denominators."""
    return float(num / den) if den else np.nan


def clip_prob(prob: np.ndarray) -> np.ndarray:
    """Clip probabilities for log-loss and logit diagnostics."""
    return np.clip(prob.astype(float), EPS, 1.0 - EPS)


def sigmoid(values: np.ndarray) -> np.ndarray:
    """Stable logistic sigmoid."""
    clipped = np.clip(values, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def fit_logistic_model(x: np.ndarray, y: np.ndarray, standardize: bool = True, ridge: float = 1e-4) -> LogisticFit:
    """Fit a small ridge-stabilized logistic model with Newton iterations."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float)
    if standardize:
        mean = np.nanmean(x, axis=0)
        scale = np.nanstd(x, axis=0)
        scale = np.where(scale < EPS, 1.0, scale)
    else:
        mean = np.zeros(x.shape[1], dtype=float)
        scale = np.ones(x.shape[1], dtype=float)
    x_norm = np.nan_to_num((x - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    base_rate = float(np.clip(y.mean(), EPS, 1.0 - EPS))
    coef = np.zeros(design.shape[1], dtype=float)
    coef[0] = math.log(base_rate / (1.0 - base_rate))
    penalty = np.eye(design.shape[1]) * ridge
    penalty[0, 0] = 0.0
    for _ in range(100):
        prob = sigmoid(design @ coef)
        weight = np.clip(prob * (1.0 - prob), EPS, None)
        gradient = design.T @ (prob - y) + penalty @ coef
        hessian = (design.T * weight) @ design + penalty
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        coef -= step
        if float(np.linalg.norm(step)) < 1e-7:
            break
    return LogisticFit(coef=coef, mean=mean, scale=scale)


def predict_logistic(fit: LogisticFit, x: np.ndarray) -> np.ndarray:
    """Predict probabilities from a fitted small logistic model."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    x_norm = np.nan_to_num((x - fit.mean) / fit.scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    return clip_prob(sigmoid(design @ fit.coef))


def pava(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Pool-adjacent-violators algorithm for increasing isotonic fits."""
    block_values: list[float] = []
    block_weights: list[float] = []
    block_lengths: list[int] = []
    for value, weight in zip(values, weights):
        block_values.append(float(value))
        block_weights.append(float(weight))
        block_lengths.append(1)
        while len(block_values) >= 2 and block_values[-2] > block_values[-1]:
            total_weight = block_weights[-2] + block_weights[-1]
            pooled = (block_values[-2] * block_weights[-2] + block_values[-1] * block_weights[-1]) / total_weight
            block_values[-2] = pooled
            block_weights[-2] = total_weight
            block_lengths[-2] += block_lengths[-1]
            block_values.pop()
            block_weights.pop()
            block_lengths.pop()
    fitted: list[float] = []
    for value, length in zip(block_values, block_lengths):
        fitted.extend([value] * length)
    return np.asarray(fitted, dtype=float)


def isotonic_fit_predict(train_score: np.ndarray, train_y: np.ndarray, test_score: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit a dependency-free increasing isotonic calibration and predict."""
    order = np.argsort(train_score, kind="mergesort")
    sorted_score = train_score[order]
    sorted_y = train_y[order].astype(float)
    fitted_sorted = pava(sorted_y, np.ones_like(sorted_y, dtype=float))
    train_fit_sorted = fitted_sorted
    train_prob = np.empty_like(train_fit_sorted)
    train_prob[order] = train_fit_sorted
    unique_scores = pd.Series(sorted_score).drop_duplicates().to_numpy(dtype=float)
    unique_rates = (
        pd.DataFrame({"score": sorted_score, "rate": fitted_sorted})
        .groupby("score", sort=True)["rate"]
        .mean()
        .to_numpy(dtype=float)
    )
    if len(unique_scores) == 1:
        test_prob = np.full(len(test_score), unique_rates[0], dtype=float)
    else:
        test_prob = np.interp(test_score, unique_scores, unique_rates, left=unique_rates[0], right=unique_rates[-1])
    return clip_prob(train_prob), clip_prob(test_prob)


def roc_auc_binary(y_true: np.ndarray, score: np.ndarray) -> float:
    """Compute binary ROC-AUC using average ranks for ties."""
    y = y_true.astype(int)
    if len(np.unique(y)) < 2:
        return np.nan
    ranks = pd.Series(score).rank(method="average").to_numpy(dtype=float)
    n_pos = int(y.sum())
    n_neg = int(len(y) - n_pos)
    rank_sum_pos = float(ranks[y == 1].sum())
    return float((rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def average_precision_binary(y_true: np.ndarray, score: np.ndarray) -> float:
    """Compute average precision for binary labels."""
    y = y_true.astype(int)
    n_pos = int(y.sum())
    if n_pos == 0:
        return np.nan
    order = np.argsort(-score, kind="mergesort")
    sorted_y = y[order]
    tp = np.cumsum(sorted_y)
    ranks = np.arange(1, len(sorted_y) + 1)
    precision = tp / ranks
    return float(precision[sorted_y == 1].sum() / n_pos)


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


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values for compact CSV cells."""
    out: list[str] = []
    for value in values:
        text = str(value)
        if text and text != "nan" and text not in out:
            out.append(text)
    return ";".join(out)


def bool_series(series: pd.Series) -> pd.Series:
    """Convert bool-like values to boolean values."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    text = series.astype(str).str.strip().str.lower()
    return text.isin({"true", "1", "yes", "y"})


def numeric(series: pd.Series) -> pd.Series:
    """Convert a Series to numeric values."""
    return pd.to_numeric(series, errors="coerce")


def input_inventory(config: dict[str, Any], selected: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build the input inventory for required calibration sources."""
    inputs = config["inputs"]
    rows: list[dict[str, Any]] = []
    for role, raw_path in inputs.items():
        path = resolve_path(str(raw_path))
        exists = path.exists()
        columns: list[str] = []
        row_count = 0
        if exists:
            row_count = count_csv_rows(path)
            try:
                columns = pd.read_csv(path, nrows=0).columns.tolist()
            except Exception:
                columns = []
        row = {
            "inventory_role": role,
            "path": rel(path),
            "exists": exists,
            "rows_total": row_count,
            "column_count": len(columns),
            "columns_present": semicolon(columns),
            "selected_for_analysis": role == "residual_weather_merge",
            "notes": "",
        }
        if selected is not None and role == "residual_weather_merge":
            row.update(
                {
                    "rows_selected_loso": len(selected),
                    "selected_models": semicolon(selected.get("model_name", pd.Series(dtype=object)).dropna().unique()),
                    "selected_station_count": selected.get("station_id", pd.Series(dtype=object)).nunique(),
                    "selected_event_count_ge31": int(selected.get("obs_ge31", pd.Series(dtype=bool)).sum()),
                    "selected_event_count_ge33": int(selected.get("obs_ge33", pd.Series(dtype=bool)).sum()),
                    "selected_timestamp_min": selected.get("timestamp", pd.Series(dtype=object)).min(),
                    "selected_timestamp_max": selected.get("timestamp", pd.Series(dtype=object)).max(),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def validation_metadata(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Summarize whether station-held-out validation is usable."""
    schema = config["schema"]
    station_col = schema["station_col"]
    fold_col = schema["fold_col"]
    cv_col = schema["cv_scheme_col"]
    primary_cv = schema["primary_cv_scheme"]
    has_cols = all(col in df.columns for col in [station_col, fold_col, cv_col])
    if not has_cols:
        return {
            "validation_method": "apparent_only",
            "station_grouped_validation_available": False,
            "fold_identity_usable": False,
            "fold_count": 0,
            "reason": "required fold/station/cv columns missing",
        }
    primary = df[df[cv_col].astype(str).eq(str(primary_cv))].copy()
    if primary.empty:
        return {
            "validation_method": "apparent_only",
            "station_grouped_validation_available": False,
            "fold_identity_usable": False,
            "fold_count": 0,
            "reason": f"primary cv_scheme={primary_cv} not present",
        }
    fold_identity = primary[fold_col].astype(str).eq(primary[station_col].astype(str)).all()
    fold_count = primary[fold_col].nunique()
    station_count = primary[station_col].nunique()
    return {
        "validation_method": "station_grouped_loso",
        "station_grouped_validation_available": bool(fold_identity and fold_count >= 3),
        "fold_identity_usable": bool(fold_identity),
        "fold_count": int(fold_count),
        "station_count": int(station_count),
        "reason": "fold equals station_id in primary LOSO rows" if fold_identity else "fold does not equal station_id",
    }


def prepare_analysis_input(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Load and normalize the LOSO calibration analysis input."""
    schema = config["schema"]
    path = resolve_path(config["inputs"]["residual_weather_merge"])
    if not path.exists():
        raise FileNotFoundError(rel(path))

    df = read_csv(path)
    metadata = validation_metadata(df, config)
    model_col = schema["model_name_col"]
    score_col = schema["model_score_col"]
    target_col = schema["target_col"]
    station_col = schema["station_col"]
    timestamp_col = schema["timestamp_col"]
    cv_col = schema["cv_scheme_col"]
    hour_col = schema["hour_col"]
    primary_cv = schema["primary_cv_scheme"]
    score_models = set(config["models"]["score_models"])

    selected = df[df[model_col].astype(str).isin(score_models)].copy()
    selected = selected[selected[cv_col].astype(str).eq(str(primary_cv))].copy()
    selected = selected.dropna(subset=[model_col, score_col, target_col, station_col, timestamp_col])
    selected[score_col] = numeric(selected[score_col])
    selected[target_col] = numeric(selected[target_col])
    selected = selected.dropna(subset=[score_col, target_col]).copy()
    selected["timestamp_dt"] = pd.to_datetime(selected[timestamp_col], errors="coerce")
    if hour_col not in selected.columns or selected[hour_col].isna().all():
        selected[hour_col] = selected["timestamp_dt"].dt.hour
    selected[hour_col] = numeric(selected[hour_col]).astype("Int64")

    for event in config["events"].values():
        event_col = event["event_col"]
        threshold = float(event["threshold_c"])
        selected[event_col] = selected[target_col] >= threshold

    selected["radiation_hot_flag"] = (
        selected.get("combined_radiation_hot_regime", pd.Series("", index=selected.index)).astype(str)
        == str(config["analysis"]["radiation_hot_label"])
    )
    selected["shortwave_very_high_flag"] = (
        selected.get("shortwave_bin", pd.Series("", index=selected.index)).astype(str)
        == str(config["analysis"]["very_high_label"])
    )
    selected["shortwave_3h_very_high_flag"] = (
        selected.get("shortwave_3h_mean_bin", pd.Series("", index=selected.index)).astype(str)
        == str(config["analysis"]["very_high_label"])
    )
    hours = selected[hour_col].astype(float)
    selected["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
    selected["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)

    keep = [
        "source_path",
        "row_id",
        model_col,
        target_col,
        score_col,
        station_col,
        hour_col,
        timestamp_col,
        "date",
        cv_col,
        schema["fold_col"],
        "residual_c",
        "abs_error_c",
        "obs_ge31",
        "obs_ge33",
        "pred_ge31_fixed",
        "pred_ge33_fixed",
        "ge31_event_class",
        "observed_wbgt_bin",
        "predicted_score_bin",
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "shortwave_radiation",
        "shortwave_3h_mean",
        "cloud_cover",
        "precipitation",
        "direct_radiation",
        "diffuse_radiation",
        "has_weather_match",
        "shortwave_bin",
        "shortwave_3h_mean_bin",
        "humidity_bin",
        "wind_bin",
        "temperature_bin",
        "cloud_cover_bin",
        "direct_radiation_bin",
        "diffuse_radiation_bin",
        "combined_radiation_hot_regime",
        "radiation_hot_flag",
        "shortwave_very_high_flag",
        "shortwave_3h_very_high_flag",
        "hour_sin",
        "hour_cos",
    ]
    selected = selected[[col for col in keep if col in selected.columns]].copy()
    selected = selected.sort_values([model_col, station_col, timestamp_col]).reset_index(drop=True)
    inventory = input_inventory(config, selected)
    return selected, inventory, metadata


def bin_labels(edges: np.ndarray) -> list[str]:
    """Create compact labels for numeric bins."""
    labels: list[str] = []
    for idx in range(len(edges) - 1):
        left = "-inf" if np.isneginf(edges[idx]) else f"{edges[idx]:.2f}"
        right = "inf" if np.isposinf(edges[idx + 1]) else f"{edges[idx + 1]:.2f}"
        labels.append(f"[{left},{right})")
    return labels


def monotonic_status(values: pd.Series) -> str:
    """Classify event-rate monotonicity versus increasing bins."""
    rates = values.dropna().to_numpy(dtype=float)
    if len(rates) < 3:
        return "insufficient_bins"
    decreases = int((np.diff(rates) < -1e-9).sum())
    if decreases == 0:
        return "monotonic"
    if decreases <= max(1, math.floor(0.25 * (len(rates) - 1))):
        return "mostly_monotonic"
    return "not_monotonic"


def make_score_bin_event_rates(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create score-bin empirical event rates for M4/M7 scores."""
    schema = config["schema"]
    model_col = schema["model_name_col"]
    score_col = schema["model_score_col"]
    target_col = schema["target_col"]
    station_col = schema["station_col"]
    rows: list[pd.DataFrame] = []
    start = float(config["analysis"]["score_threshold_scan_start_c"])
    stop = float(config["analysis"]["score_threshold_scan_stop_c"])
    fixed_edges = np.arange(start, stop + 0.5, 0.5)
    q_count = int(config["analysis"]["quantile_bin_count"])
    for model_name, model_df in df.groupby(model_col):
        for event in config["events"].values():
            event_id = event["id"]
            event_col = event["event_col"]
            work = model_df[[score_col, target_col, station_col, event_col]].dropna().copy()
            if work.empty:
                continue
            work[event_col] = bool_series(work[event_col])
            fixed = work.copy()
            fixed["score_bin"] = pd.cut(
                fixed[score_col],
                bins=fixed_edges,
                labels=bin_labels(fixed_edges),
                include_lowest=True,
                right=False,
            ).astype(str)
            rows.append(summarize_score_bins(fixed, model_name, event_id, "fixed_score_0p5", score_col, target_col, station_col, event_col))
            if work[score_col].nunique() >= 4:
                q = min(q_count, work[score_col].nunique())
                quant = work.copy()
                quant["score_bin"] = pd.qcut(quant[score_col], q=q, duplicates="drop").astype(str)
                rows.append(summarize_score_bins(quant, model_name, event_id, "quantile_score", score_col, target_col, station_col, event_col))
    out = pd.concat([part for part in rows if not part.empty], ignore_index=True) if rows else pd.DataFrame()
    if out.empty:
        return out
    keys = ["model_name", "event_target", "bin_kind"]
    mono = (
        out.sort_values("mean_score")
        .groupby(keys, dropna=False)["event_rate"]
        .apply(monotonic_status)
        .rename("event_rate_monotonicity")
        .reset_index()
    )
    return out.merge(mono, on=keys, how="left")


def summarize_score_bins(
    frame: pd.DataFrame,
    model_name: str,
    event_id: str,
    bin_kind: str,
    score_col: str,
    target_col: str,
    station_col: str,
    event_col: str,
) -> pd.DataFrame:
    """Summarize one score-bin table."""
    grouped = frame.dropna(subset=["score_bin"]).groupby("score_bin", observed=False)
    out = grouped.agg(
        n=(event_col, "size"),
        event_count=(event_col, "sum"),
        score_min=(score_col, "min"),
        score_max=(score_col, "max"),
        mean_score=(score_col, "mean"),
        observed_wbgt_mean=(target_col, "mean"),
        station_count=(station_col, "nunique"),
    ).reset_index()
    out.insert(0, "bin_kind", bin_kind)
    out.insert(0, "event_target", event_id)
    out.insert(0, "model_name", model_name)
    out["event_rate"] = out["event_count"] / out["n"]
    out["validation_scope"] = "loso_station_grouped_source_rows"
    return out.sort_values(["model_name", "event_target", "bin_kind", "score_min"])


def event_vector(frame: pd.DataFrame, event_col: str) -> np.ndarray:
    """Return binary event values."""
    return bool_series(frame[event_col]).astype(int).to_numpy()


def confusion_counts(y_true: np.ndarray, values: np.ndarray, threshold: float) -> dict[str, Any]:
    """Compute event-detection metrics at a threshold."""
    y = y_true.astype(int)
    pred = (values >= threshold).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    f1 = safe_div(2.0 * precision * recall, precision + recall) if np.isfinite(precision) and np.isfinite(recall) else np.nan
    return {
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": precision,
        "recall": recall,
        "F1": f1,
        "CSI": safe_div(tp, tp + fp + fn),
        "false_alarm_ratio": safe_div(fp, tp + fp),
        "miss_rate": safe_div(fn, tp + fn),
        "specificity": specificity,
        "Youden": recall + specificity - 1.0 if np.isfinite(recall) and np.isfinite(specificity) else np.nan,
        "predicted_positive_count": int(pred.sum()),
        "observed_positive_count": int(y.sum()),
        "n": int(len(y)),
    }


def threshold_grid(kind: str, config: dict[str, Any]) -> np.ndarray:
    """Return the configured threshold scan grid."""
    analysis = config["analysis"]
    if kind == "score":
        start = float(analysis["score_threshold_scan_start_c"])
        stop = float(analysis["score_threshold_scan_stop_c"])
        step = float(analysis["score_threshold_scan_step_c"])
    else:
        start = float(analysis["probability_threshold_scan_start"])
        stop = float(analysis["probability_threshold_scan_stop"])
        step = float(analysis["probability_threshold_scan_step"])
    count = int(round((stop - start) / step)) + 1
    return np.round(start + np.arange(count) * step, 6)


def choose_thresholds(
    train_y: np.ndarray,
    train_values: np.ndarray,
    output_kind: str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Select operating thresholds on training-station rows only."""
    rows: list[dict[str, Any]] = []
    if output_kind == "score":
        rows.append(
            {
                "operating_point": "fixed_score_31",
                "threshold_source": "fixed",
                "achievable": True,
                "threshold": 31.0,
                **confusion_counts(train_y, train_values, 31.0),
            }
        )
    grid = threshold_grid(output_kind, config)
    scan = pd.DataFrame([{**confusion_counts(train_y, train_values, float(th)), "threshold": float(th)} for th in grid])
    best_f1 = scan.sort_values(["F1", "recall", "precision", "threshold"], ascending=[False, False, False, True]).head(1)
    if not best_f1.empty:
        rows.append({"operating_point": "best_F1", "threshold_source": "train_selected", "achievable": True, **best_f1.iloc[0].to_dict()})

    recall_target = float(config["analysis"]["recall_target"])
    recall_choice = (
        scan[scan["recall"] >= recall_target]
        .sort_values(["precision", "F1", "threshold"], ascending=[False, False, False])
        .head(1)
    )
    rows.append(
        {
            "operating_point": "recall_90",
            "threshold_source": "train_selected",
            "achievable": not recall_choice.empty,
            **(recall_choice.iloc[0].to_dict() if not recall_choice.empty else {"threshold": np.nan}),
        }
    )

    precision_target = float(config["analysis"]["precision_target"])
    precision_choice = (
        scan[scan["precision"] >= precision_target]
        .sort_values(["recall", "F1", "threshold"], ascending=[False, False, True])
        .head(1)
    )
    rows.append(
        {
            "operating_point": "precision_70",
            "threshold_source": "train_selected",
            "achievable": not precision_choice.empty,
            **(precision_choice.iloc[0].to_dict() if not precision_choice.empty else {"threshold": np.nan}),
        }
    )

    youden = scan.sort_values(["Youden", "recall", "precision"], ascending=[False, False, False]).head(1)
    if not youden.empty:
        rows.append({"operating_point": "max_Youden", "threshold_source": "train_selected", "achievable": True, **youden.iloc[0].to_dict()})
    return rows


def feature_matrix(frame: pd.DataFrame, method: dict[str, Any], score_col: str) -> np.ndarray:
    """Build a calibrator feature matrix."""
    features: list[np.ndarray] = []
    for feature in method.get("features", ["score"]):
        if feature == "score":
            features.append(numeric(frame[score_col]).to_numpy(dtype=float))
        else:
            features.append(numeric(frame[feature]).fillna(0.0).to_numpy(dtype=float))
    return np.column_stack(features)


def empirical_edges(scores: np.ndarray, n_bins: int) -> np.ndarray:
    """Create robust empirical-bin edges from training scores."""
    clean = scores[np.isfinite(scores)]
    if clean.size == 0:
        return np.array([-np.inf, np.inf])
    quantiles = np.linspace(0.0, 1.0, min(n_bins, len(np.unique(clean))) + 1)
    edges = np.unique(np.quantile(clean, quantiles))
    if len(edges) < 3:
        low = float(np.min(clean))
        high = float(np.max(clean))
        if low == high:
            high = low + EPS
        edges = np.array([low, high])
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges


def empirical_predict(scores: np.ndarray, edges: np.ndarray, rates: np.ndarray, fallback: float) -> np.ndarray:
    """Predict empirical-bin probabilities."""
    bin_ids = np.digitize(scores, edges[1:-1], right=False)
    probs = np.full(len(scores), fallback, dtype=float)
    valid = (bin_ids >= 0) & (bin_ids < len(rates))
    probs[valid] = rates[bin_ids[valid]]
    return clip_prob(probs)


def fit_predict_calibrator(
    method: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
    event_col: str,
    score_col: str,
    config: dict[str, Any],
) -> tuple[np.ndarray | None, np.ndarray | None, dict[str, Any]]:
    """Fit a station-training calibrator and return train/test probabilities."""
    train_y = event_vector(train, event_col)
    info = {
        "fit_status": "fit",
        "train_n": int(len(train)),
        "train_event_count": int(train_y.sum()),
        "train_non_event_count": int((1 - train_y).sum()),
        "train_event_rate": safe_div(int(train_y.sum()), len(train_y)),
        "low_support_bins": np.nan,
    }
    if len(train_y) < int(config["calibrators"]["min_train_rows"]) or len(np.unique(train_y)) < 2:
        info["fit_status"] = "skipped_insufficient_training_classes"
        return None, None, info

    family = method["family"]
    if family == "empirical_bin":
        scores = numeric(train[score_col]).to_numpy(dtype=float)
        test_scores = numeric(test[score_col]).to_numpy(dtype=float)
        fallback = float(train_y.mean())
        edges = empirical_edges(scores, int(config["calibrators"]["empirical_bin_count"]))
        train_bin = np.digitize(scores, edges[1:-1], right=False)
        rates: list[float] = []
        supports: list[int] = []
        for idx in range(len(edges) - 1):
            mask = train_bin == idx
            supports.append(int(mask.sum()))
            rates.append(float(train_y[mask].mean()) if mask.any() else fallback)
        info["low_support_bins"] = int(sum(support < int(config["analysis"]["low_support_n"]) for support in supports))
        rates_arr = np.array(rates, dtype=float)
        return empirical_predict(scores, edges, rates_arr, fallback), empirical_predict(test_scores, edges, rates_arr, fallback), info

    if family == "isotonic":
        if train_y.sum() < int(config["calibrators"]["min_isotonic_events"]) or (1 - train_y).sum() < int(config["calibrators"]["min_isotonic_non_events"]):
            info["fit_status"] = "skipped_insufficient_isotonic_events"
            return None, None, info
        train_score = numeric(train[score_col]).to_numpy(dtype=float)
        test_score = numeric(test[score_col]).to_numpy(dtype=float)
        return (*isotonic_fit_predict(train_score, train_y, test_score), info)

    if family == "logistic":
        x_train = feature_matrix(train, method, score_col)
        x_test = feature_matrix(test, method, score_col)
        if np.unique(x_train, axis=0).shape[0] < 2:
            info["fit_status"] = "skipped_insufficient_feature_variation"
            return None, None, info
        model = fit_logistic_model(x_train, train_y, standardize=True)
        return predict_logistic(model, x_train), predict_logistic(model, x_test), info

    raise ValueError(f"Unsupported calibrator family: {family}")


def metadata_columns(df: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    """Return compact row metadata columns to carry through outputs."""
    schema = config["schema"]
    base = [
        "row_id",
        schema["model_name_col"],
        schema["station_col"],
        schema["fold_col"],
        schema["cv_scheme_col"],
        schema["timestamp_col"],
        schema["date_col"],
        schema["hour_col"],
        schema["target_col"],
        schema["model_score_col"],
        "radiation_hot_flag",
        "shortwave_very_high_flag",
        "shortwave_3h_very_high_flag",
        "combined_radiation_hot_regime",
        "shortwave_bin",
        "shortwave_3h_mean_bin",
        "temperature_bin",
        "humidity_bin",
        "wind_bin",
        "cloud_cover_bin",
        "direct_radiation_bin",
        "diffuse_radiation_bin",
    ]
    return [col for col in base if col in df.columns]


def record_threshold_evaluation(
    test: pd.DataFrame,
    train_y: np.ndarray,
    train_values: np.ndarray,
    test_y: np.ndarray,
    test_values: np.ndarray,
    output_kind: str,
    output_id: str,
    model_name: str,
    event_id: str,
    event_col: str,
    event_threshold: float,
    fold_id: str,
    config: dict[str, Any],
    threshold_rows: list[dict[str, Any]],
    decision_parts: list[pd.DataFrame],
) -> None:
    """Select thresholds on training rows, then evaluate held-out station rows."""
    choices = choose_thresholds(train_y, train_values, output_kind, config)
    for choice in choices:
        base = {
            "model_name": model_name,
            "event_target": event_id,
            "official_event_threshold_c": event_threshold,
            "output_kind": output_kind,
            "output_id": output_id,
            "validation_method": "station_grouped_loso",
            "fold_id": fold_id,
            "operating_point": choice["operating_point"],
            "threshold_source": choice["threshold_source"],
            "achievable": bool(choice["achievable"]),
        }
        if not choice["achievable"] or not np.isfinite(float(choice.get("threshold", np.nan))):
            threshold_rows.append({**base, "status": "skipped_unachievable", "threshold": np.nan})
            continue
        threshold = float(choice["threshold"])
        metrics = confusion_counts(test_y, test_values, threshold)
        threshold_rows.append({**base, "status": "evaluated_on_heldout", "threshold": threshold, **metrics})
        decisions = test[metadata_columns(test, config)].copy()
        decisions["model_name"] = model_name
        decisions["event_target"] = event_id
        decisions["event_col"] = event_col
        decisions["official_event_threshold_c"] = event_threshold
        decisions["output_kind"] = output_kind
        decisions["output_id"] = output_id
        decisions["validation_method"] = "station_grouped_loso"
        decisions["fold_id"] = fold_id
        decisions["operating_point"] = choice["operating_point"]
        decisions["threshold_source"] = choice["threshold_source"]
        decisions["threshold"] = threshold
        decisions["output_value"] = test_values
        decisions["event_observed"] = test_y
        decisions["event_predicted"] = (test_values >= threshold).astype(int)
        decision_parts.append(decisions)


def run_score_thresholds(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate raw score thresholds with station-training threshold selection."""
    schema = config["schema"]
    model_col = schema["model_name_col"]
    score_col = schema["model_score_col"]
    station_col = schema["station_col"]
    fold_col = schema["fold_col"]
    threshold_rows: list[dict[str, Any]] = []
    decision_parts: list[pd.DataFrame] = []
    for model_name, model_df in df.groupby(model_col):
        for event in config["events"].values():
            event_id = event["id"]
            event_col = event["event_col"]
            event_threshold = float(event["threshold_c"])
            for fold_id in sorted(model_df[fold_col].dropna().astype(str).unique()):
                test_mask = model_df[fold_col].astype(str).eq(fold_id)
                train = model_df[~test_mask].copy()
                test = model_df[test_mask].copy()
                if train.empty or test.empty:
                    continue
                train_y = event_vector(train, event_col)
                test_y = event_vector(test, event_col)
                train_score = numeric(train[score_col]).to_numpy(dtype=float)
                test_score = numeric(test[score_col]).to_numpy(dtype=float)
                record_threshold_evaluation(
                    test=test,
                    train_y=train_y,
                    train_values=train_score,
                    test_y=test_y,
                    test_values=test_score,
                    output_kind="score",
                    output_id="raw_model_score",
                    model_name=str(model_name),
                    event_id=str(event_id),
                    event_col=str(event_col),
                    event_threshold=event_threshold,
                    fold_id=str(fold_id),
                    config=config,
                    threshold_rows=threshold_rows,
                    decision_parts=decision_parts,
                )
    decisions = pd.concat(decision_parts, ignore_index=True) if decision_parts else pd.DataFrame()
    return pd.DataFrame(threshold_rows), decisions


def run_probability_calibration(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run station-held-out probability calibration and threshold evaluation."""
    schema = config["schema"]
    model_col = schema["model_name_col"]
    score_col = schema["model_score_col"]
    fold_col = schema["fold_col"]
    prediction_parts: list[pd.DataFrame] = []
    threshold_rows: list[dict[str, Any]] = []
    decision_parts: list[pd.DataFrame] = []
    methods = config["calibrators"]["probability_methods"]

    for model_name, model_df in df.groupby(model_col):
        for event in config["events"].values():
            event_id = event["id"]
            event_col = event["event_col"]
            event_threshold = float(event["threshold_c"])
            for fold_id in sorted(model_df[fold_col].dropna().astype(str).unique()):
                test_mask = model_df[fold_col].astype(str).eq(fold_id)
                train = model_df[~test_mask].copy()
                test = model_df[test_mask].copy()
                if train.empty or test.empty:
                    continue
                train_y = event_vector(train, event_col)
                test_y = event_vector(test, event_col)
                for method in methods:
                    train_prob, test_prob, fit_info = fit_predict_calibrator(method, train, test, event_col, score_col, config)
                    if train_prob is None or test_prob is None:
                        threshold_rows.append(
                            {
                                "model_name": model_name,
                                "event_target": event_id,
                                "official_event_threshold_c": event_threshold,
                                "output_kind": "probability",
                                "output_id": method["id"],
                                "validation_method": "station_grouped_loso",
                                "fold_id": fold_id,
                                "operating_point": "calibrator_fit",
                                "threshold_source": "none",
                                "achievable": False,
                                "status": fit_info["fit_status"],
                                **fit_info,
                            }
                        )
                        continue

                    pred = test[metadata_columns(test, config)].copy()
                    pred["event_target"] = event_id
                    pred["event_col"] = event_col
                    pred["official_event_threshold_c"] = event_threshold
                    pred["event_observed"] = test_y
                    pred["calibrator_id"] = method["id"]
                    pred["calibrator_family"] = method["family"]
                    pred["diagnostic_only"] = bool(method.get("diagnostic_only", False))
                    pred["validation_method"] = "station_grouped_loso"
                    pred["fold_id"] = fold_id
                    pred["probability"] = test_prob
                    pred["p_ge31"] = test_prob if event_id == "ge31" else np.nan
                    pred["p_ge33"] = test_prob if event_id == "ge33" else np.nan
                    for key, value in fit_info.items():
                        pred[key] = value
                    prediction_parts.append(pred)

                    record_threshold_evaluation(
                        test=test,
                        train_y=train_y,
                        train_values=train_prob,
                        test_y=test_y,
                        test_values=test_prob,
                        output_kind="probability",
                        output_id=str(method["id"]),
                        model_name=str(model_name),
                        event_id=str(event_id),
                        event_col=str(event_col),
                        event_threshold=event_threshold,
                        fold_id=str(fold_id),
                        config=config,
                        threshold_rows=threshold_rows,
                        decision_parts=decision_parts,
                    )

    predictions = pd.concat(prediction_parts, ignore_index=True) if prediction_parts else pd.DataFrame()
    decisions = pd.concat(decision_parts, ignore_index=True) if decision_parts else pd.DataFrame()
    return predictions, pd.DataFrame(threshold_rows), decisions


def log_loss_binary(y_true: np.ndarray, prob: np.ndarray) -> float:
    """Compute binary log-loss with clipped probabilities."""
    y = y_true.astype(float)
    p = clip_prob(prob)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def calibration_intercept_slope(y_true: np.ndarray, prob: np.ndarray) -> tuple[float, float]:
    """Estimate calibration intercept and slope from held-out predictions."""
    if len(np.unique(y_true)) < 2 or np.unique(np.round(prob, 8)).size < 2:
        return np.nan, np.nan
    logits = np.log(clip_prob(prob) / (1.0 - clip_prob(prob)))
    try:
        model = fit_logistic_model(logits.reshape(-1, 1), y_true.astype(float), standardize=False, ridge=1e-6)
        return float(model.coef[0]), float(model.coef[1])
    except Exception:
        return np.nan, np.nan


def make_reliability_bins(predictions: pd.DataFrame, config: dict[str, Any], bin_kind: str) -> pd.DataFrame:
    """Build fixed or quantile probability reliability bins."""
    if predictions.empty:
        return pd.DataFrame()
    low_support = int(config["analysis"]["low_support_n"])
    keys = [
        "model_name",
        "event_target",
        "official_event_threshold_c",
        "calibrator_id",
        "calibrator_family",
        "diagnostic_only",
        "validation_method",
    ]
    rows: list[pd.DataFrame] = []
    for key, group in predictions.groupby(keys, dropna=False):
        work = group[["probability", "event_observed", "station_id", "model_score"]].dropna().copy()
        if work.empty:
            continue
        if bin_kind == "fixed":
            step = float(config["analysis"]["fixed_probability_bin_step"])
            edges = np.round(np.arange(0.0, 1.0 + step, step), 6)
            if edges[-1] < 1.0:
                edges = np.append(edges, 1.0)
            labels = bin_labels(edges)
            work["probability_bin"] = pd.cut(
                work["probability"],
                bins=edges,
                labels=labels,
                include_lowest=True,
                right=False,
            ).astype(str)
            work.loc[work["probability"] >= 1.0, "probability_bin"] = labels[-1]
        else:
            q_count = min(int(config["analysis"]["quantile_bin_count"]), work["probability"].nunique())
            if q_count < 2:
                continue
            work["probability_bin"] = pd.qcut(work["probability"], q=q_count, duplicates="drop").astype(str)
        out = work.groupby("probability_bin", observed=False).agg(
            n=("event_observed", "size"),
            event_count=("event_observed", "sum"),
            mean_predicted_probability=("probability", "mean"),
            p_min=("probability", "min"),
            p_max=("probability", "max"),
            mean_score=("model_score", "mean"),
            station_count=("station_id", "nunique"),
        ).reset_index()
        out["observed_event_rate"] = out["event_count"] / out["n"]
        out["calibration_gap"] = out["mean_predicted_probability"] - out["observed_event_rate"]
        out["abs_calibration_gap"] = out["calibration_gap"].abs()
        out["low_support"] = out["n"] < low_support
        out["bin_kind"] = bin_kind
        for col, value in zip(keys, key):
            out[col] = value
        rows.append(out)
    combined = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if combined.empty:
        return combined
    ordered = keys + [
        "bin_kind",
        "probability_bin",
        "n",
        "event_count",
        "observed_event_rate",
        "mean_predicted_probability",
        "calibration_gap",
        "abs_calibration_gap",
        "p_min",
        "p_max",
        "mean_score",
        "station_count",
        "low_support",
    ]
    return combined[[col for col in ordered if col in combined.columns]]


def reliability_errors(bins: pd.DataFrame) -> pd.DataFrame:
    """Compute ECE/MCE from reliability bins."""
    if bins.empty:
        return pd.DataFrame()
    keys = [
        "model_name",
        "event_target",
        "official_event_threshold_c",
        "calibrator_id",
        "validation_method",
        "bin_kind",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in bins.groupby(keys, dropna=False):
        n = group["n"].sum()
        rows.append(
            {
                **dict(zip(keys, key)),
                "ECE": float(((group["n"] / n) * group["abs_calibration_gap"]).sum()) if n else np.nan,
                "MCE": float(group["abs_calibration_gap"].max()) if len(group) else np.nan,
                "reliability_bin_count": int(len(group)),
                "low_support_bin_count": int(group["low_support"].sum()) if "low_support" in group else 0,
            }
        )
    return pd.DataFrame(rows)


def station_probability_summary(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute station-grouped probability performance summaries."""
    if predictions.empty:
        return pd.DataFrame()
    keys = ["model_name", "event_target", "calibrator_id", "validation_method", "station_id"]
    rows: list[dict[str, Any]] = []
    for key, group in predictions.groupby(keys, dropna=False):
        y = group["event_observed"].to_numpy(dtype=int)
        p = group["probability"].to_numpy(dtype=float)
        rows.append(
            {
                **dict(zip(keys, key)),
                "n": len(group),
                "event_count": int(y.sum()),
                "observed_event_rate": safe_div(int(y.sum()), len(y)),
                "mean_predicted_probability": float(p.mean()) if len(p) else np.nan,
                "probability_bias": float(p.mean() - y.mean()) if len(p) else np.nan,
                "Brier": float(np.mean((p - y) ** 2)) if len(p) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def make_probability_metrics(
    predictions: pd.DataFrame,
    reliability_fixed: pd.DataFrame,
    reliability_quantile: pd.DataFrame,
) -> pd.DataFrame:
    """Compute station-held-out probability calibration metrics."""
    if predictions.empty:
        return pd.DataFrame()
    keys = [
        "model_name",
        "event_target",
        "official_event_threshold_c",
        "calibrator_id",
        "calibrator_family",
        "diagnostic_only",
        "validation_method",
    ]
    fixed_errors = reliability_errors(reliability_fixed)
    quant_errors = reliability_errors(reliability_quantile)
    station_summary = station_probability_summary(predictions)
    rows: list[dict[str, Any]] = []
    for key, group in predictions.groupby(keys, dropna=False):
        y = group["event_observed"].to_numpy(dtype=int)
        p = clip_prob(group["probability"].to_numpy(dtype=float))
        both_classes = len(np.unique(y)) == 2
        intercept, slope = calibration_intercept_slope(y, p)
        row = {
            **dict(zip(keys, key)),
            "n": int(len(group)),
            "event_count": int(y.sum()),
            "event_count_ge31": int(y.sum()) if key[1] == "ge31" else np.nan,
            "event_count_ge33": int(y.sum()) if key[1] == "ge33" else np.nan,
            "event_rate": safe_div(int(y.sum()), len(y)),
            "Brier": float(np.mean((p - y) ** 2)),
            "log_loss": log_loss_binary(y, p),
            "ROC_AUC": roc_auc_binary(y, p) if both_classes else np.nan,
            "PR_AUC": average_precision_binary(y, p) if both_classes else np.nan,
            "average_precision": average_precision_binary(y, p) if both_classes else np.nan,
            "calibration_intercept": intercept,
            "calibration_slope": slope,
            "mean_predicted_probability": float(p.mean()),
            "probability_bias": float(p.mean() - y.mean()),
            "p05_predicted_probability": float(np.quantile(p, 0.05)),
            "p50_predicted_probability": float(np.quantile(p, 0.50)),
            "p95_predicted_probability": float(np.quantile(p, 0.95)),
            "p05_predicted_P_ge31": float(np.quantile(p, 0.05)) if key[1] == "ge31" else np.nan,
            "p50_predicted_P_ge31": float(np.quantile(p, 0.50)) if key[1] == "ge31" else np.nan,
            "p95_predicted_P_ge31": float(np.quantile(p, 0.95)) if key[1] == "ge31" else np.nan,
            "station_count": int(group["station_id"].nunique()),
            "fold_count": int(group["fold_id"].nunique()),
        }
        fixed_match = fixed_errors[
            fixed_errors["model_name"].eq(key[0])
            & fixed_errors["event_target"].eq(key[1])
            & fixed_errors["calibrator_id"].eq(key[3])
            & fixed_errors["validation_method"].eq(key[6])
            & fixed_errors["bin_kind"].eq("fixed")
        ]
        quant_match = quant_errors[
            quant_errors["model_name"].eq(key[0])
            & quant_errors["event_target"].eq(key[1])
            & quant_errors["calibrator_id"].eq(key[3])
            & quant_errors["validation_method"].eq(key[6])
            & quant_errors["bin_kind"].eq("quantile")
        ]
        row["ECE_fixed"] = fixed_match["ECE"].iloc[0] if not fixed_match.empty else np.nan
        row["MCE_fixed"] = fixed_match["MCE"].iloc[0] if not fixed_match.empty else np.nan
        row["ECE_quantile"] = quant_match["ECE"].iloc[0] if not quant_match.empty else np.nan
        row["MCE_quantile"] = quant_match["MCE"].iloc[0] if not quant_match.empty else np.nan
        station_match = station_summary[
            station_summary["model_name"].eq(key[0])
            & station_summary["event_target"].eq(key[1])
            & station_summary["calibrator_id"].eq(key[3])
            & station_summary["validation_method"].eq(key[6])
        ]
        row["station_Brier_mean"] = station_match["Brier"].mean() if not station_match.empty else np.nan
        row["station_Brier_max"] = station_match["Brier"].max() if not station_match.empty else np.nan
        row["station_probability_bias_abs_mean"] = station_match["probability_bias"].abs().mean() if not station_match.empty else np.nan
        row["station_event_count_max"] = station_match["event_count"].max() if not station_match.empty else np.nan
        rows.append(row)
    metrics = pd.DataFrame(rows)
    if metrics.empty:
        return metrics
    metrics["rank_score_ge31"] = np.nan
    focus = metrics[metrics["event_target"].eq("ge31") & ~metrics["diagnostic_only"].astype(bool)].copy()
    if not focus.empty:
        rank = (
            focus["Brier"].rank(method="min")
            + focus["ECE_fixed"].rank(method="min")
            + focus["log_loss"].rank(method="min")
            + focus["PR_AUC"].rank(method="min", ascending=False)
        )
        metrics.loc[focus.index, "rank_score_ge31"] = rank
    return metrics.sort_values(["event_target", "rank_score_ge31", "Brier"], na_position="last")


def aggregate_threshold_operating_points(fold_thresholds: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fold-level threshold metrics into operating-point rows."""
    if fold_thresholds.empty:
        return pd.DataFrame()
    keys = [
        "model_name",
        "event_target",
        "official_event_threshold_c",
        "output_kind",
        "output_id",
        "validation_method",
        "operating_point",
        "threshold_source",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in fold_thresholds.groupby(keys, dropna=False):
        evaluated = group[group["status"].eq("evaluated_on_heldout")].copy()
        skipped = group[~group["status"].eq("evaluated_on_heldout")].copy()
        if evaluated.empty:
            rows.append(
                {
                    **dict(zip(keys, key)),
                    "status": "skipped_unachievable",
                    "n_folds_evaluated": 0,
                    "n_folds_skipped": int(len(skipped)),
                    "threshold": np.nan,
                    "threshold_min": np.nan,
                    "threshold_max": np.nan,
                    "precision": np.nan,
                    "recall": np.nan,
                    "F1": np.nan,
                    "CSI": np.nan,
                    "false_alarm_ratio": np.nan,
                    "miss_rate": np.nan,
                    "TP": np.nan,
                    "FP": np.nan,
                    "FN": np.nan,
                    "TN": np.nan,
                    "n": np.nan,
                }
            )
            continue
        totals = evaluated[["TP", "FP", "FN", "TN", "n"]].sum()
        tp = float(totals["TP"])
        fp = float(totals["FP"])
        fn = float(totals["FN"])
        tn = float(totals["TN"])
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        rows.append(
            {
                **dict(zip(keys, key)),
                "status": "evaluated_on_heldout",
                "n_folds_evaluated": int(evaluated["fold_id"].nunique()),
                "n_folds_skipped": int(len(skipped)),
                "threshold": float(evaluated["threshold"].mean()),
                "threshold_min": float(evaluated["threshold"].min()),
                "threshold_max": float(evaluated["threshold"].max()),
                "precision": precision,
                "recall": recall,
                "F1": safe_div(2.0 * precision * recall, precision + recall) if np.isfinite(precision) and np.isfinite(recall) else np.nan,
                "CSI": safe_div(tp, tp + fp + fn),
                "false_alarm_ratio": safe_div(fp, tp + fp),
                "miss_rate": safe_div(fn, tp + fn),
                "TP": int(tp),
                "FP": int(fp),
                "FN": int(fn),
                "TN": int(tn),
                "n": int(totals["n"]),
                "fold_F1_std": evaluated["F1"].std(ddof=0),
                "fold_recall_std": evaluated["recall"].std(ddof=0),
                "fold_precision_std": evaluated["precision"].std(ddof=0),
            }
        )
    return pd.DataFrame(rows).sort_values(["event_target", "output_kind", "model_name", "output_id", "operating_point"])


def choose_best_candidate(metrics: pd.DataFrame, thresholds: pd.DataFrame) -> pd.Series | None:
    """Choose the primary non-diagnostic P_ge31 companion candidate."""
    if metrics.empty:
        return None
    focus = metrics[metrics["event_target"].eq("ge31") & ~metrics["diagnostic_only"].astype(bool)].copy()
    if focus.empty:
        return None
    best_thresholds = thresholds[
        thresholds["event_target"].eq("ge31")
        & thresholds["output_kind"].eq("probability")
        & thresholds["operating_point"].eq("best_F1")
        & thresholds["status"].eq("evaluated_on_heldout")
    ][["model_name", "output_id", "F1", "precision", "recall", "threshold"]].rename(
        columns={
            "output_id": "calibrator_id",
            "F1": "best_F1_operating_F1",
            "precision": "best_F1_operating_precision",
            "recall": "best_F1_operating_recall",
            "threshold": "best_F1_operating_threshold",
        }
    )
    focus = focus.merge(best_thresholds, on=["model_name", "calibrator_id"], how="left")
    focus["selection_rank"] = (
        focus["Brier"].rank(method="min")
        + focus["ECE_fixed"].rank(method="min")
        + focus["log_loss"].rank(method="min")
        + focus["PR_AUC"].rank(method="min", ascending=False)
        + focus["best_F1_operating_F1"].rank(method="min", ascending=False).fillna(len(focus) + 1)
    )
    return focus.sort_values(["selection_rank", "Brier", "ECE_fixed"]).iloc[0]


def append_selected_policy(
    best: pd.Series | None,
    fold_thresholds: pd.DataFrame,
    decisions: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Duplicate the configured operating point as selected_candidate_policy."""
    if best is None or fold_thresholds.empty:
        return fold_thresholds, decisions
    policy_source = str(config["analysis"]["selected_policy_operating_point"])
    mask = (
        fold_thresholds["model_name"].eq(best["model_name"])
        & fold_thresholds["event_target"].eq("ge31")
        & fold_thresholds["output_kind"].eq("probability")
        & fold_thresholds["output_id"].eq(best["calibrator_id"])
        & fold_thresholds["operating_point"].eq(policy_source)
    )
    policy_folds = fold_thresholds[mask].copy()
    if policy_folds.empty:
        return fold_thresholds, decisions
    policy_folds["operating_point"] = "selected_candidate_policy"
    policy_folds["threshold_source"] = f"selected_policy_from_{policy_source}"
    policy_folds["policy_note"] = "Balanced diagnostic threshold selected from training-station best_F1 for the chosen non-diagnostic P_ge31 companion."
    if decisions.empty:
        return pd.concat([fold_thresholds, policy_folds], ignore_index=True), decisions
    decision_mask = (
        decisions["model_name"].eq(best["model_name"])
        & decisions["event_target"].eq("ge31")
        & decisions["output_kind"].eq("probability")
        & decisions["output_id"].eq(best["calibrator_id"])
        & decisions["operating_point"].eq(policy_source)
    )
    policy_decisions = decisions[decision_mask].copy()
    if not policy_decisions.empty:
        policy_decisions["operating_point"] = "selected_candidate_policy"
        policy_decisions["threshold_source"] = f"selected_policy_from_{policy_source}"
    return (
        pd.concat([fold_thresholds, policy_folds], ignore_index=True),
        pd.concat([decisions, policy_decisions], ignore_index=True) if not policy_decisions.empty else decisions,
    )


def aggregate_threshold_by_station(decisions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Aggregate threshold metrics and probability calibration by station."""
    if decisions.empty:
        return pd.DataFrame()
    focus_stations = set(str(station) for station in config["analysis"].get("focus_stations", []))
    keys = [
        "model_name",
        "event_target",
        "output_kind",
        "output_id",
        "validation_method",
        "operating_point",
        "station_id",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in decisions.groupby(keys, dropna=False):
        y = group["event_observed"].to_numpy(dtype=int)
        pred = group["event_predicted"].to_numpy(dtype=int)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        output_kind = key[2]
        output_values = group["output_value"].to_numpy(dtype=float)
        probability_brier = float(np.mean((output_values - y) ** 2)) if output_kind == "probability" else np.nan
        rows.append(
            {
                **dict(zip(keys, key)),
                "focus_station_flag": str(key[-1]) in focus_stations,
                "threshold_mean": group["threshold"].mean(),
                "n": len(group),
                "event_count": int(y.sum()),
                "observed_event_rate": safe_div(int(y.sum()), len(y)),
                "mean_output_value": float(np.mean(output_values)) if len(output_values) else np.nan,
                "probability_bias": float(np.mean(output_values) - y.mean()) if output_kind == "probability" and len(output_values) else np.nan,
                "Brier": probability_brier,
                "TP": tp,
                "FP": fp,
                "FN": fn,
                "TN": tn,
                "precision": precision,
                "recall": recall,
                "F1": safe_div(2.0 * precision * recall, precision + recall) if np.isfinite(precision) and np.isfinite(recall) else np.nan,
                "CSI": safe_div(tp, tp + fp + fn),
                "false_alarm_ratio": safe_div(fp, tp + fp),
                "miss_rate": safe_div(fn, tp + fn),
            }
        )
    return pd.DataFrame(rows).sort_values(["event_target", "model_name", "output_kind", "output_id", "operating_point", "station_id"])


def aggregate_one_regime(decisions: pd.DataFrame, variable: str, label_col: str) -> pd.DataFrame:
    """Aggregate threshold metrics for one regime variable."""
    work = decisions.copy()
    if variable not in work.columns:
        return pd.DataFrame()
    work[label_col] = work[variable].astype(str)
    keys = [
        "model_name",
        "event_target",
        "output_kind",
        "output_id",
        "validation_method",
        "operating_point",
        label_col,
    ]
    rows: list[dict[str, Any]] = []
    for key, group in work.groupby(keys, dropna=False):
        y = group["event_observed"].to_numpy(dtype=int)
        pred = group["event_predicted"].to_numpy(dtype=int)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        output_values = group["output_value"].to_numpy(dtype=float)
        rows.append(
            {
                "regime_variable": variable,
                "regime_bin": key[-1],
                **dict(zip(keys[:-1], key[:-1])),
                "threshold_mean": group["threshold"].mean(),
                "n": len(group),
                "event_count": int(y.sum()),
                "observed_event_rate": safe_div(int(y.sum()), len(y)),
                "mean_output_value": float(np.mean(output_values)) if len(output_values) else np.nan,
                "probability_bias": float(np.mean(output_values) - y.mean()) if key[2] == "probability" and len(output_values) else np.nan,
                "TP": tp,
                "FP": fp,
                "FN": fn,
                "TN": tn,
                "precision": precision,
                "recall": recall,
                "F1": safe_div(2.0 * precision * recall, precision + recall) if np.isfinite(precision) and np.isfinite(recall) else np.nan,
                "CSI": safe_div(tp, tp + fp + fn),
                "false_alarm_ratio": safe_div(fp, tp + fp),
                "miss_rate": safe_div(fn, tp + fn),
            }
        )
    return pd.DataFrame(rows)


def aggregate_threshold_by_regime(decisions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate threshold metrics by radiation and shortwave regimes."""
    if decisions.empty:
        return pd.DataFrame()
    variables = [
        "combined_radiation_hot_regime",
        "radiation_hot_flag",
        "shortwave_bin",
        "shortwave_very_high_flag",
        "shortwave_3h_mean_bin",
        "shortwave_3h_very_high_flag",
    ]
    parts = [aggregate_one_regime(decisions, variable, "regime_bin") for variable in variables if variable in decisions.columns]
    return pd.concat([part for part in parts if not part.empty], ignore_index=True) if parts else pd.DataFrame()


def selected_score_threshold_baseline(thresholds: pd.DataFrame) -> pd.DataFrame:
    """Extract score-threshold baselines for report comparison."""
    if thresholds.empty:
        return pd.DataFrame()
    return thresholds[
        thresholds["event_target"].eq("ge31")
        & thresholds["output_kind"].eq("score")
        & thresholds["operating_point"].isin(["fixed_score_31", "best_F1", "recall_90", "precision_70", "max_Youden"])
        & thresholds["status"].eq("evaluated_on_heldout")
    ].copy()


def decide_result(
    metadata: dict[str, Any],
    metrics: pd.DataFrame,
    thresholds: pd.DataFrame,
    best: pd.Series | None,
    output_paths: list[Path],
) -> CalibrationResult:
    """Assign the A-L1H.2 diagnostic decision."""
    if not metadata.get("station_grouped_validation_available", False):
        return CalibrationResult(
            acceptance_status="BLOCKED",
            decision_status="BLOCKED",
            best_probability_candidate="None - station grouped validation was not usable.",
            brier_pr_auc_reliability_headline="No station-held-out calibration metrics promoted.",
            recommended_operating_point="None.",
            station_regime_caveats=str(metadata.get("reason", "fold structure unusable")),
            next_recommended_action="Repair fold/station metadata before interpreting P_ge31 calibration.",
            output_paths=output_paths,
        )
    if metrics.empty or best is None:
        return CalibrationResult(
            acceptance_status="BLOCKED",
            decision_status="BLOCKED",
            best_probability_candidate="None - probability predictions were not produced.",
            brier_pr_auc_reliability_headline="No probability metrics available.",
            recommended_operating_point="None.",
            station_regime_caveats="Probability calibration could not be evaluated.",
            next_recommended_action="Audit input rows and calibrator support before proceeding.",
            output_paths=output_paths,
        )

    best_key = (
        thresholds["model_name"].eq(best["model_name"])
        & thresholds["event_target"].eq("ge31")
        & thresholds["output_kind"].eq("probability")
        & thresholds["output_id"].eq(best["calibrator_id"])
        & thresholds["operating_point"].eq("selected_candidate_policy")
    )
    best_policy = thresholds[best_key].copy()
    score_fixed = thresholds[
        thresholds["event_target"].eq("ge31")
        & thresholds["output_kind"].eq("score")
        & thresholds["operating_point"].eq("fixed_score_31")
        & thresholds["status"].eq("evaluated_on_heldout")
    ].copy()
    fixed_f1 = score_fixed["F1"].max() if not score_fixed.empty else np.nan
    policy_f1 = best_policy["F1"].iloc[0] if not best_policy.empty else np.nan
    reliability_ok = bool(best.get("ECE_fixed", np.nan) <= 0.10 or best.get("ECE_quantile", np.nan) <= 0.10)
    threshold_ok = bool(np.isfinite(policy_f1) and (not np.isfinite(fixed_f1) or policy_f1 >= fixed_f1))
    spread_ok = bool(best.get("p95_predicted_probability", np.nan) - best.get("p05_predicted_probability", np.nan) >= 0.25)

    if reliability_ok and threshold_ok and spread_ok:
        decision_status = "PASS_CANDIDATE_PROBABILITY_COMPANION"
        acceptance_status = "PASS"
    elif reliability_ok or threshold_ok:
        decision_status = "PARTIAL_DIAGNOSTIC"
        acceptance_status = "PARTIAL"
    else:
        decision_status = "WEAK_OR_NEGATIVE"
        acceptance_status = "WEAK"

    best_candidate = f"{best['model_name']} + {best['calibrator_id']} ({best['validation_method']})"
    brier = fmt(best.get("Brier"))
    pr_auc = fmt(best.get("PR_AUC"))
    ece = fmt(best.get("ECE_fixed"))
    quant_ece = fmt(best.get("ECE_quantile"))
    spread = f"{fmt(best.get('p05_predicted_probability'))}/{fmt(best.get('p50_predicted_probability'))}/{fmt(best.get('p95_predicted_probability'))}"
    headline = f"Brier={brier}; PR-AUC={pr_auc}; ECE_fixed={ece}; ECE_quantile={quant_ece}; P05/P50/P95={spread}."
    if best_policy.empty:
        operating = "No selected policy threshold row was available."
    else:
        row = best_policy.iloc[0]
        operating = (
            f"selected_candidate_policy from best_F1: threshold={fmt(row['threshold'])}, "
            f"precision={fmt(row['precision'])}, recall={fmt(row['recall'])}, F1={fmt(row['F1'])}, CSI={fmt(row['CSI'])}."
        )
    caveats = (
        "S142 and S139 remain station diagnostics to review; radiation-hot and very-high shortwave rows "
        "are retrospective regime diagnostics only and do not establish a causal mechanism."
    )
    next_action = (
        "Use calibrated P_ge31 as a diagnostic companion in A-L1H evidence notes; keep deterministic WBGT_A score separate. "
        "Proceed to A-L1H.3 only if a separately scoped high-tail regression review is opened; do not start A-L2 from this lane."
    )
    return CalibrationResult(
        acceptance_status=acceptance_status,
        decision_status=decision_status,
        best_probability_candidate=best_candidate,
        brier_pr_auc_reliability_headline=headline,
        recommended_operating_point=operating,
        station_regime_caveats=caveats,
        next_recommended_action=next_action,
        output_paths=output_paths,
    )


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 12) -> str:
    """Render a compact Markdown table."""
    if df.empty:
        return "_No rows available._"
    display = df[[col for col in columns if col in df.columns]].head(limit).copy()
    for col in display.columns:
        if pd.api.types.is_numeric_dtype(display[col]):
            display[col] = display[col].map(lambda value: fmt(value))
        else:
            display[col] = display[col].fillna("NA").astype(str)
    headers = [str(col) for col in display.columns]
    body = [[str(value) for value in row] for row in display.to_numpy()]
    widths = [len(header) for header in headers]
    for row in body:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    separator = "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |"
    return "\n".join([render_row(headers), separator, *[render_row(row) for row in body]])


def write_report(
    path: Path,
    result: CalibrationResult,
    inventory: pd.DataFrame,
    metadata: dict[str, Any],
    score_bins: pd.DataFrame,
    metrics: pd.DataFrame,
    thresholds: pd.DataFrame,
    reliability_fixed: pd.DataFrame,
    reliability_quantile: pd.DataFrame,
    station: pd.DataFrame,
    regime: pd.DataFrame,
) -> None:
    """Write the A-L1H.2 Markdown report."""
    ge31_metrics = metrics[metrics["event_target"].eq("ge31")].copy() if not metrics.empty else pd.DataFrame()
    score_baseline = selected_score_threshold_baseline(thresholds)
    probability_ops = thresholds[
        thresholds["event_target"].eq("ge31")
        & thresholds["output_kind"].eq("probability")
        & thresholds["operating_point"].isin(["best_F1", "recall_90", "precision_70", "selected_candidate_policy"])
        & thresholds["status"].eq("evaluated_on_heldout")
    ].copy() if not thresholds.empty else pd.DataFrame()
    selected_station = station[
        station["event_target"].eq("ge31")
        & station["operating_point"].eq("selected_candidate_policy")
    ].copy() if not station.empty else pd.DataFrame()
    focus_station = selected_station[selected_station.get("focus_station_flag", pd.Series(False, index=selected_station.index)).astype(bool)].copy() if not selected_station.empty else pd.DataFrame()
    selected_regime = regime[
        regime["event_target"].eq("ge31")
        & regime["operating_point"].eq("selected_candidate_policy")
        & regime["regime_variable"].isin(["combined_radiation_hot_regime", "shortwave_bin", "shortwave_3h_mean_bin"])
    ].copy() if not regime.empty else pd.DataFrame()
    reliability_focus = reliability_fixed[reliability_fixed["event_target"].eq("ge31")].copy() if not reliability_fixed.empty else pd.DataFrame()
    score_bin_focus = score_bins[score_bins["event_target"].eq("ge31") & score_bins["bin_kind"].eq("fixed_score_0p5")].copy() if not score_bins.empty else pd.DataFrame()

    lines = [
        "# System A A-L1H.2 Probability / Threshold Calibration",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Acceptance status: `{result.acceptance_status}`",
        f"Decision status: `{result.decision_status}`",
        f"Branch: `{git_branch()}`",
        "",
        "## 1. Why A-L1H.2 Follows A-L1H.1",
        "",
        "A-L1H.0 found global high-tail compression plus station bias. A-L1H.0c then recovered full-period weather-regime coverage and showed that radiation-hot periods contain most observed ge31 events and misses. A-L1H.1 found the simple formula/proxy route weak or negative: raw formula/proxy candidates did not reach fixed_31 crossings, while M4/M7 scores remained more useful but their nominal score >=31 thresholds were misaligned with event detection. A-L1H.2 therefore tests whether existing M4/M7 OOF scores can be calibrated into a cautious diagnostic P_ge31 companion and station-held-out threshold operating points.",
        "",
        "## 2. Inputs And Validation Method",
        "",
        markdown_table(
            inventory,
            ["inventory_role", "path", "exists", "rows_total", "rows_selected_loso", "selected_station_count", "selected_event_count_ge31", "selected_event_count_ge33"],
            limit=10,
        ),
        "",
        f"Validation method: `{metadata.get('validation_method')}`. Fold usability: `{metadata.get('reason')}`. Fold count: `{metadata.get('fold_count')}`.",
        "",
        "All promoted probability rows are predicted for held-out stations after fitting the calibrator on other-station OOF rows. The probability models consume existing score columns only; optional score+hour and score+radiation-hot fits are marked diagnostic.",
        "",
        "## 3. M4 vs M7 Score Comparison",
        "",
        "Station-held-out score-threshold baselines:",
        "",
        markdown_table(
            score_baseline.sort_values(["model_name", "operating_point"]),
            ["model_name", "operating_point", "threshold", "precision", "recall", "F1", "CSI", "false_alarm_ratio", "miss_rate", "TP", "FP", "FN", "TN"],
            limit=16,
        ),
        "",
        "Score-bin empirical ge31 event rates:",
        "",
        markdown_table(
            score_bin_focus.sort_values(["model_name", "score_min"]),
            ["model_name", "score_bin", "n", "event_count", "event_rate", "mean_score", "observed_wbgt_mean", "event_rate_monotonicity"],
            limit=20,
        ),
        "",
        "## 4. Probability Calibration Metrics",
        "",
        markdown_table(
            ge31_metrics.sort_values(["diagnostic_only", "rank_score_ge31", "Brier"], na_position="last"),
            ["model_name", "calibrator_id", "diagnostic_only", "n", "event_count_ge31", "Brier", "log_loss", "PR_AUC", "ROC_AUC", "ECE_fixed", "MCE_fixed", "ECE_quantile", "calibration_intercept", "calibration_slope", "p05_predicted_probability", "p50_predicted_probability", "p95_predicted_probability"],
            limit=16,
        ),
        "",
        "ge33 remains exploratory and is not used to promote a probability companion.",
        "",
        "## 5. Threshold Operating Point Metrics",
        "",
        markdown_table(
            probability_ops.sort_values(["output_id", "model_name", "operating_point"]),
            ["model_name", "output_id", "operating_point", "threshold", "precision", "recall", "F1", "CSI", "false_alarm_ratio", "miss_rate", "TP", "FP", "FN", "TN"],
            limit=24,
        ),
        "",
        f"Recommended operating point: {result.recommended_operating_point}",
        "",
        "## 6. Reliability Diagnostics",
        "",
        "Fixed probability bins for ge31:",
        "",
        markdown_table(
            reliability_focus.sort_values(["model_name", "calibrator_id", "p_min"]),
            ["model_name", "calibrator_id", "probability_bin", "n", "event_count", "observed_event_rate", "mean_predicted_probability", "calibration_gap", "low_support"],
            limit=24,
        ),
        "",
        f"Reliability headline: {result.brier_pr_auc_reliability_headline}",
        "",
        f"Quantile reliability bins were also written with {len(reliability_quantile)} rows.",
        "",
        "## 7. Station / Regime Diagnostics",
        "",
        "Focus station rows for the selected candidate policy:",
        "",
        markdown_table(
            focus_station.sort_values(["station_id"]),
            ["model_name", "output_id", "station_id", "n", "event_count", "observed_event_rate", "mean_output_value", "probability_bias", "Brier", "precision", "recall", "F1", "false_alarm_ratio", "miss_rate"],
            limit=12,
        ),
        "",
        "Selected candidate policy by radiation and shortwave regimes:",
        "",
        markdown_table(
            selected_regime.sort_values(["regime_variable", "regime_bin", "model_name"]),
            ["model_name", "output_id", "regime_variable", "regime_bin", "n", "event_count", "observed_event_rate", "mean_output_value", "probability_bias", "precision", "recall", "F1", "false_alarm_ratio", "miss_rate"],
            limit=24,
        ),
        "",
        result.station_regime_caveats,
        "",
        "## 8. Recommended Calibrated Diagnostic Output",
        "",
        f"Best probability companion candidate: `{result.best_probability_candidate}`.",
        "",
        "The deterministic WBGT_A score remains separate from P_ge31. `P_ge31` is a retrospective diagnostic companion conditional on the current OOF score distribution and station-held-out calibration; it is not an official warning probability and not prospective forecast skill.",
        "",
        "## 9. Proceed / Hold Decision",
        "",
        f"Decision: `{result.decision_status}`.",
        "",
        result.next_recommended_action,
        "",
        "A-L2 station-context preflight remains out of scope for this lane. High-tail regression remains a separate A-L1H.3 review gate, not an implementation performed here.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(path: Path, config_path: Path, result: CalibrationResult) -> None:
    """Write the A-L1H.2 lane status file."""
    outputs = "\n".join(f"- `{rel(output_path)}`" for output_path in result.output_paths)
    lines = [
        "# A-L1H.2 Status",
        "",
        f"Status: {result.acceptance_status}",
        f"Decision: {result.decision_status}",
        f"Generated: {date.today().isoformat()}",
        f"Branch: {git_branch()}",
        "",
        "## Scope",
        "",
        "Probability / threshold calibration for existing System A M4/M7 OOF scores. This is score-to-event calibration only, not official warning probability and not prospective forecast skill.",
        "",
        "## Command",
        "",
        f"- `{Path(sys.executable)} scripts/v11_l1h_run_probability_threshold_calibration.py --config {rel(config_path)}`",
        "",
        "## Files Created / Modified",
        "",
        outputs,
        "",
        "## Key Results",
        "",
        f"- Best probability companion candidate: {result.best_probability_candidate}",
        f"- Reliability headline: {result.brier_pr_auc_reliability_headline}",
        f"- Recommended operating point: {result.recommended_operating_point}",
        f"- Station/regime caveats: {result.station_regime_caveats}",
        f"- Next recommended action: {result.next_recommended_action}",
        "",
        "## Caveats",
        "",
        "- Station-held-out retrospective OOF calibration only.",
        "- P_ge31 is diagnostic and not an official warning probability.",
        "- ge33 remains exploratory.",
        "- Optional score+hour and score+radiation-hot calibrators are diagnostic only.",
        "",
        "## Safe To Commit",
        "",
        "- Config, scripts, docs, and compact A-L1H.2 diagnostic outputs after review.",
        "",
        "## Not Safe To Commit",
        "",
        "- Raw archives, rasters, SOLWEIG outputs, tif/tiff files, svfs.zip, patch zip packages, or large hourly forecast CSVs.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked_outputs(config: dict[str, Any], config_path: Path, reason: str) -> CalibrationResult:
    """Write minimal BLOCKED outputs if required inputs are missing."""
    output_dir = resolve_path(config["outputs"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(config)
    inventory_path = output_dir / "calibration_input_inventory.csv"
    report_path = output_dir / "probability_threshold_calibration_report.md"
    status_path = output_dir / "A_L1H_2_STATUS.md"
    inventory.to_csv(inventory_path, index=False)
    report_path.write_text(
        "\n".join(
            [
                "# System A A-L1H.2 Probability / Threshold Calibration",
                "",
                "Acceptance status: `BLOCKED`",
                "Decision status: `BLOCKED`",
                "",
                "## Blocker",
                "",
                reason,
                "",
                "No base WBGT models were retrained and no probability claims are promoted.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    result = CalibrationResult(
        acceptance_status="BLOCKED",
        decision_status="BLOCKED",
        best_probability_candidate="None.",
        brier_pr_auc_reliability_headline="No metrics produced.",
        recommended_operating_point="None.",
        station_regime_caveats=reason,
        next_recommended_action="Repair missing inputs/folds before rerunning A-L1H.2.",
        output_paths=[inventory_path, report_path, status_path],
    )
    write_status(status_path, config_path, result)
    return result


def run_calibration(config_path: Path) -> CalibrationResult:
    """Run A-L1H.2 probability and threshold calibration diagnostics."""
    config = load_config(config_path)
    output_dir = resolve_path(config["outputs"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = [resolve_path(path) for path in config["inputs"].values() if not resolve_path(path).exists()]
    if missing:
        return write_blocked_outputs(config, config_path, "Missing required inputs: " + ", ".join(rel(path) for path in missing))

    analysis_input, inventory, metadata = prepare_analysis_input(config)
    if analysis_input.empty:
        return write_blocked_outputs(config, config_path, "No primary LOSO M4/M7 rows available after schema normalization.")

    score_bins = make_score_bin_event_rates(analysis_input, config)
    score_threshold_folds, score_decisions = run_score_thresholds(analysis_input, config)
    prob_predictions, prob_threshold_folds, prob_decisions = run_probability_calibration(analysis_input, config)
    reliability_fixed = make_reliability_bins(prob_predictions, config, "fixed")
    reliability_quantile = make_reliability_bins(prob_predictions, config, "quantile")
    metrics = make_probability_metrics(prob_predictions, reliability_fixed, reliability_quantile)
    initial_threshold_folds = pd.concat([score_threshold_folds, prob_threshold_folds], ignore_index=True)
    initial_decisions = pd.concat([score_decisions, prob_decisions], ignore_index=True) if not score_decisions.empty or not prob_decisions.empty else pd.DataFrame()
    initial_thresholds = aggregate_threshold_operating_points(initial_threshold_folds)
    best = choose_best_candidate(metrics, initial_thresholds)
    threshold_folds, threshold_decisions = append_selected_policy(best, initial_threshold_folds, initial_decisions, config)
    thresholds = aggregate_threshold_operating_points(threshold_folds)
    station = aggregate_threshold_by_station(threshold_decisions, config)
    regime = aggregate_threshold_by_regime(threshold_decisions)

    inventory_path = output_dir / "calibration_input_inventory.csv"
    analysis_path = output_dir / "calibration_analysis_input.csv"
    predictions_path = output_dir / "probability_predictions_oof.csv.gz"
    score_bins_path = output_dir / "score_bin_event_rates.csv"
    reliability_fixed_path = output_dir / "reliability_bins_fixed.csv"
    reliability_quantile_path = output_dir / "reliability_bins_quantile.csv"
    metrics_path = output_dir / "probability_calibration_metrics.csv"
    thresholds_path = output_dir / "threshold_operating_points.csv"
    station_path = output_dir / "threshold_by_station.csv"
    regime_path = output_dir / "threshold_by_regime.csv"
    report_path = output_dir / "probability_threshold_calibration_report.md"
    status_path = output_dir / "A_L1H_2_STATUS.md"

    inventory.to_csv(inventory_path, index=False)
    analysis_input.to_csv(analysis_path, index=False)
    prob_predictions.to_csv(predictions_path, index=False, compression="gzip")
    score_bins.to_csv(score_bins_path, index=False)
    reliability_fixed.to_csv(reliability_fixed_path, index=False)
    reliability_quantile.to_csv(reliability_quantile_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    thresholds.to_csv(thresholds_path, index=False)
    station.to_csv(station_path, index=False)
    regime.to_csv(regime_path, index=False)

    output_paths = [
        inventory_path,
        analysis_path,
        predictions_path,
        score_bins_path,
        reliability_fixed_path,
        reliability_quantile_path,
        metrics_path,
        thresholds_path,
        station_path,
        regime_path,
        report_path,
        status_path,
    ]
    result = decide_result(metadata, metrics, thresholds, best, output_paths)
    write_report(
        report_path,
        result,
        inventory,
        metadata,
        score_bins,
        metrics,
        thresholds,
        reliability_fixed,
        reliability_quantile,
        station,
        regime,
    )
    write_status(status_path, config_path, result)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Run A-L1H.2 station-held-out score-to-event probability and threshold calibration."
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h_probability_threshold_calibration.yaml")
    args = parser.parse_args()

    result = run_calibration(resolve_path(args.config))
    print(f"[acceptance_status] {result.acceptance_status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[best_probability_candidate] {result.best_probability_candidate}")
    print(f"[brier_pr_auc_reliability] {result.brier_pr_auc_reliability_headline}")
    print(f"[recommended_operating_point] {result.recommended_operating_point}")
    print(f"[station_regime_caveats] {result.station_regime_caveats}")
    print(f"[next_recommended_action] {result.next_recommended_action}")
    return 0 if result.acceptance_status in {"PASS", "PARTIAL", "WEAK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
