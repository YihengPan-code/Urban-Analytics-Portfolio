#!/usr/bin/env python
"""System A A-L1H.3 high-tail challenger benchmark.

Inputs:
    - configs/v11/systema_l1h3_high_tail_challenger.yaml
    - outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/
      residual_weather_merge_full_period.csv
    - outputs/v11_systema_l1_high_tail/probability_threshold_calibration/
      probability_predictions_oof.csv.gz
    - outputs/v11_systema_l1_high_tail/probability_threshold_calibration/
      threshold_operating_points.csv
    - outputs/v11_systema_l1_high_tail/level1_integration/
      systema_l1h_output_contract.csv

Outputs:
    - challenger_input_inventory.csv
    - challenger_feature_schema.csv
    - challenger_oof_predictions.csv.gz
    - challenger_overall_metrics.csv
    - challenger_threshold_metrics.csv
    - challenger_reliability_metrics.csv
    - challenger_by_station.csv
    - challenger_by_regime.csv
    - challenger_pairwise_vs_current_companion.csv
    - high_tail_challenger_report.md
    - A_L1H_3_STATUS.md

Saved metrics:
    - Input inventory, selected LOSO row counts, station/fold counts, and
      current-companion reproduction checks.
    - No-leakage feature contract for each challenger and skipped HGB route.
    - Station-held-out OOF challenger probabilities/scores.
    - ge31 precision, recall, F1, CSI, false-alarm ratio, miss rate,
      TP/FP/FN/TN, ROC-AUC, PR-AUC, Brier, reliability ECE/MCE, and
      probability spread.
    - Train-station-selected best_F1, recall_90, precision_70,
      current_companion_threshold, and selected_candidate_policy operating
      points.
    - Station and weather-regime threshold diagnostics plus pairwise deltas
      against the current M4+isotonic best-F1 and recall_90 companions.

Scope guard:
    This is a constrained retrospective challenger benchmark. It does not
    stage or commit files, touch System B, touch SOLWEIG outputs, modify
    archive collector paths, use station_id as a feature, claim official
    warning probability, claim prospective forecast skill, claim local 100m
    WBGT, or start A-L2.
"""
from __future__ import annotations

import argparse
import gzip
import itertools
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import v11_l1h_probability_threshold_calibration as l1h2


ROOT = Path(__file__).resolve().parents[1]
EPS = 1e-6
VALIDATION_METHOD = "station_grouped_loso"
EXPECTED_OUTPUT_PREFIX = "outputs/v11_systema_l1_high_tail/high_tail_challenger"
PRIMARY_EVENT_ID = "ge31"
REQUIRED_OPERATING_POINTS = ["best_F1", "recall_90", "precision_70", "current_companion_threshold"]
FORBIDDEN_FEATURE_NAMES = {
    "station_id",
    "fold",
    "official_wbgt_c",
    "observed_wbgt_c",
    "obs_ge31",
    "obs_ge33",
    "residual_c",
    "abs_error_c",
    "event_class",
    "ge31_event_class",
    "target",
    "future_label",
}
FORBIDDEN_FEATURE_SUBSTRINGS = ["official", "obs_", "residual", "event_class", "future", "systemb", "solweig", "tmrt"]


@dataclass(frozen=True)
class ChallengerRunResult:
    """Headline result for the A-L1H.3 challenger benchmark."""

    acceptance_status: str
    decision_status: str
    best_challenger: str
    comparison_best_f1: str
    comparison_recall90: str
    station_regime_caveats: str
    a_l2_recommendation: str
    output_paths: list[Path]


@dataclass(frozen=True)
class WeightedLogisticFit:
    """Small fitted weighted logistic model."""

    coef: np.ndarray
    mean: np.ndarray
    scale: np.ndarray


@dataclass(frozen=True)
class RidgeFit:
    """Small fitted ridge linear model."""

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


def load_config(path: Path) -> dict[str, Any]:
    """Read the explicit A-L1H.3 YAML config."""
    return l1h2.load_config(path)


def git_branch() -> str:
    """Return the current git branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def count_csv_rows(path: Path) -> int:
    """Count CSV data rows, including gzip-compressed CSVs."""
    if not path.exists():
        return 0
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace", newline="") as f:
        return max(sum(1 for _ in f) - 1, 0)


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file with pandas."""
    return pd.read_csv(path, low_memory=False)


def fmt(value: object, digits: int = 3) -> str:
    """Format numbers for reports."""
    return l1h2.fmt(value, digits=digits)


def safe_div(num: float, den: float) -> float:
    """Divide with NaN for zero denominators."""
    return l1h2.safe_div(num, den)


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values for compact cells."""
    return l1h2.semicolon(values)


def numeric(series: pd.Series) -> pd.Series:
    """Convert a Series to numeric values."""
    return pd.to_numeric(series, errors="coerce")


def bool_series(series: pd.Series) -> pd.Series:
    """Convert bool-like values to booleans."""
    return l1h2.bool_series(series)


def params_text(params: dict[str, Any]) -> str:
    """Serialize params deterministically for CSV outputs."""
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


def markdown_cell(value: object) -> str:
    """Escape compact Markdown table cells."""
    text = fmt(value) if isinstance(value, (float, int, np.floating, np.integer)) else str(value)
    if text == "nan":
        text = "NA"
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 16) -> str:
    """Render a compact Markdown table."""
    if df.empty:
        return "_No rows available._"
    display = df[[col for col in columns if col in df.columns]].head(limit).copy()
    for col in display.columns:
        if pd.api.types.is_numeric_dtype(display[col]):
            display[col] = display[col].map(fmt)
        else:
            display[col] = display[col].fillna("NA").astype(str)
    headers = [str(col) for col in display.columns]
    body = [[markdown_cell(value) for value in row] for row in display.to_numpy()]
    widths = [len(header) for header in headers]
    for row in body:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([render(headers), separator, *[render(row) for row in body]])


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Return all expected A-L1H.3 output paths."""
    output_dir = resolve_path(str(config["outputs"]["output_dir"]))
    return {
        "dir": output_dir,
        "inventory": output_dir / "challenger_input_inventory.csv",
        "feature_schema": output_dir / "challenger_feature_schema.csv",
        "predictions": output_dir / "challenger_oof_predictions.csv.gz",
        "overall": output_dir / "challenger_overall_metrics.csv",
        "threshold": output_dir / "challenger_threshold_metrics.csv",
        "reliability": output_dir / "challenger_reliability_metrics.csv",
        "station": output_dir / "challenger_by_station.csv",
        "regime": output_dir / "challenger_by_regime.csv",
        "pairwise": output_dir / "challenger_pairwise_vs_current_companion.csv",
        "report": output_dir / "high_tail_challenger_report.md",
        "status": output_dir / "A_L1H_3_STATUS.md",
    }


def assert_output_scope(paths: dict[str, Path]) -> None:
    """Ensure outputs stay in the explicit A-L1H.3 directory."""
    output_dir = paths["dir"]
    if not rel(output_dir).startswith(EXPECTED_OUTPUT_PREFIX):
        raise ValueError(f"Refusing to write outside {EXPECTED_OUTPUT_PREFIX}: {rel(output_dir)}")


def add_derived_columns(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Normalize events, weather flags, cyclic hour, and secondary exceedance."""
    schema = config["schema"]
    out = df.copy()
    target_col = schema["target_col"]
    score_col = schema["model_score_col"]
    hour_col = schema["hour_col"]
    timestamp_col = schema["timestamp_col"]
    out[target_col] = numeric(out[target_col])
    out[score_col] = numeric(out[score_col])
    out["timestamp_dt"] = pd.to_datetime(out[timestamp_col], errors="coerce")
    if hour_col not in out.columns or out[hour_col].isna().all():
        out[hour_col] = out["timestamp_dt"].dt.hour
    out[hour_col] = numeric(out[hour_col])
    out["hour_sin"] = np.sin(2.0 * np.pi * out[hour_col].astype(float) / 24.0)
    out["hour_cos"] = np.cos(2.0 * np.pi * out[hour_col].astype(float) / 24.0)

    for event in config["events"].values():
        event_col = str(event["event_col"])
        out[event_col] = out[target_col] >= float(event["threshold_c"])
    out["expected_exceedance_above31_c"] = np.maximum(0.0, out[target_col] - 31.0)
    out["radiation_hot_flag"] = (
        out.get("combined_radiation_hot_regime", pd.Series("", index=out.index)).astype(str)
        == str(config["analysis"]["radiation_hot_label"])
    )
    out["shortwave_very_high_flag"] = (
        out.get("shortwave_bin", pd.Series("", index=out.index)).astype(str)
        == str(config["analysis"]["very_high_label"])
    )
    out["shortwave_3h_very_high_flag"] = (
        out.get("shortwave_3h_mean_bin", pd.Series("", index=out.index)).astype(str)
        == str(config["analysis"]["very_high_label"])
    )
    return out


def prepare_analysis_frame(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Load LOSO residual/weather rows and split challenger/base-model frames."""
    schema = config["schema"]
    path = resolve_path(str(config["inputs"]["residual_weather_merge"]))
    if not path.exists():
        raise FileNotFoundError(rel(path))
    df = add_derived_columns(read_csv(path), config)
    model_col = schema["model_name_col"]
    cv_col = schema["cv_scheme_col"]
    fold_col = schema["fold_col"]
    station_col = schema["station_col"]
    score_col = schema["model_score_col"]
    target_col = schema["target_col"]
    primary_cv = str(schema["primary_cv_scheme"])
    fixed_models = set(str(model) for model in config["baselines"]["fixed_score_models"])
    selected = df[df[model_col].astype(str).isin(fixed_models)].copy()
    selected = selected[selected[cv_col].astype(str).eq(primary_cv)].copy()
    selected = selected.dropna(subset=[station_col, fold_col, target_col, score_col]).copy()
    selected[station_col] = selected[station_col].astype(str)
    selected[fold_col] = selected[fold_col].astype(str)
    selected = selected.sort_values([model_col, station_col, schema["timestamp_col"]]).reset_index(drop=True)
    current_model = str(config["baselines"]["current_companion_model"])
    challenger_base = selected[selected[model_col].astype(str).eq(current_model)].copy()
    metadata = {
        "validation_method": VALIDATION_METHOD,
        "fold_identity_usable": bool(challenger_base[fold_col].eq(challenger_base[station_col]).all()),
        "fold_count": int(challenger_base[fold_col].nunique()),
        "station_count": int(challenger_base[station_col].nunique()),
        "row_count": int(len(challenger_base)),
        "event_count_ge31": int(bool_series(challenger_base[config["events"]["primary"]["event_col"]]).sum()),
        "event_count_ge33": int(bool_series(challenger_base[config["events"]["exploratory_ge33"]["event_col"]]).sum()),
        "timestamp_min": str(challenger_base[schema["timestamp_col"]].min()),
        "timestamp_max": str(challenger_base[schema["timestamp_col"]].max()),
    }
    return selected, challenger_base, metadata


def input_inventory(config: dict[str, Any], selected: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
    """Build the A-L1H.3 input inventory."""
    rows: list[dict[str, Any]] = []
    for role, raw_path in config["inputs"].items():
        path = resolve_path(str(raw_path))
        exists = path.exists()
        columns: list[str] = []
        rows_total = 0
        if exists:
            rows_total = count_csv_rows(path)
            try:
                columns = pd.read_csv(path, nrows=0).columns.tolist()
            except Exception:
                columns = []
        row = {
            "inventory_role": role,
            "path": rel(path),
            "exists": exists,
            "rows_total": rows_total,
            "column_count": len(columns),
            "columns_present": semicolon(columns),
            "selected_for_analysis": role in {"residual_weather_merge", "probability_predictions_oof", "threshold_operating_points"},
            "notes": "",
        }
        if role == "residual_weather_merge":
            row.update(
                {
                    "rows_selected_loso": len(selected),
                    "selected_models": semicolon(selected.get("model_name", pd.Series(dtype=object)).dropna().unique()),
                    "selected_station_count": metadata["station_count"],
                    "selected_fold_count": metadata["fold_count"],
                    "selected_event_count_ge31": metadata["event_count_ge31"],
                    "selected_event_count_ge33": metadata["event_count_ge33"],
                    "selected_timestamp_min": metadata["timestamp_min"],
                    "selected_timestamp_max": metadata["timestamp_max"],
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def validate_feature_name(feature: str) -> tuple[bool, str]:
    """Return whether a feature name passes the no-leakage contract."""
    lower = feature.lower()
    if lower in FORBIDDEN_FEATURE_NAMES:
        return False, "explicitly forbidden feature"
    for token in FORBIDDEN_FEATURE_SUBSTRINGS:
        if token in lower and feature not in {"radiation_hot_flag", "shortwave_very_high_flag", "shortwave_3h_very_high_flag"}:
            return False, f"contains forbidden token {token}"
    return True, "allowed weather/time/score feature"


def feature_columns(config: dict[str, Any], feature_set_id: str, df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return available and missing columns for one configured feature set."""
    raw_features = [str(feature) for feature in config["features"].get(feature_set_id, [])]
    available: list[str] = []
    missing: list[str] = []
    for feature in raw_features:
        allowed, reason = validate_feature_name(feature)
        if not allowed:
            raise ValueError(f"Forbidden feature in config: {feature} ({reason})")
        if feature in df.columns:
            available.append(feature)
        else:
            missing.append(feature)
    return available, missing


def make_feature_schema(config: dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
    """Write the no-leakage feature schema for all configured challengers."""
    rows: list[dict[str, Any]] = []
    for candidate_id, candidate in config["challengers"].items():
        feature_set_id = str(candidate.get("feature_set", ""))
        raw_features = [str(feature) for feature in config["features"].get(feature_set_id, [])]
        for feature in raw_features:
            allowed, reason = validate_feature_name(feature)
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_family": candidate.get("family"),
                    "implementation_status": candidate.get("implementation_status", "run"),
                    "diagnostic_only": bool(candidate.get("diagnostic_only", False)),
                    "feature_set": feature_set_id,
                    "feature_name": feature,
                    "feature_available": feature in df.columns,
                    "used_as_predictor": bool(allowed and feature in df.columns and candidate.get("implementation_status", "run") == "run"),
                    "source_type": "existing_score" if feature == "model_score" else "time/weather/regime",
                    "leakage_check": reason,
                    "forbidden_by_contract": not allowed,
                    "notes": "",
                }
            )
        if candidate.get("implementation_status", "run") != "run":
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_family": candidate.get("family"),
                    "implementation_status": candidate.get("implementation_status"),
                    "diagnostic_only": bool(candidate.get("diagnostic_only", False)),
                    "feature_set": feature_set_id,
                    "feature_name": "candidate_not_run",
                    "feature_available": False,
                    "used_as_predictor": False,
                    "source_type": "dependency",
                    "leakage_check": "not applicable",
                    "forbidden_by_contract": False,
                    "notes": "HistGradientBoostingClassifier was allowed but not run because sklearn is unavailable in the bundled runtime.",
                }
            )
    rows.append(
        {
            "candidate_id": "high_tail_residual_correction",
            "candidate_family": "residual_correction_isotonic",
            "implementation_status": "run",
            "diagnostic_only": False,
            "feature_set": "training_label_only",
            "feature_name": "official_wbgt_c_minus_model_score",
            "feature_available": True,
            "used_as_predictor": False,
            "source_type": "training_target_only",
            "leakage_check": "used only as supervised residual target inside training stations, never as a prediction feature",
            "forbidden_by_contract": False,
            "notes": "The residual target is computed on training rows only for the two-step correction.",
        }
    )
    return pd.DataFrame(rows)


def matrix_with_medians(
    frame: pd.DataFrame,
    columns: list[str],
    medians: dict[str, float] | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    """Build a numeric feature matrix with train-derived median imputation."""
    used_medians: dict[str, float] = {} if medians is None else dict(medians)
    arrays: list[np.ndarray] = []
    for col in columns:
        series = numeric(frame[col]) if col in frame.columns else pd.Series(np.nan, index=frame.index)
        if medians is None:
            median = float(series.median()) if series.notna().any() else 0.0
            used_medians[col] = median
        else:
            median = float(used_medians.get(col, 0.0))
        arrays.append(series.fillna(median).to_numpy(dtype=float))
    if not arrays:
        return np.zeros((len(frame), 0), dtype=float), used_medians
    return np.column_stack(arrays), used_medians


def fit_weighted_logistic(
    x: np.ndarray,
    y: np.ndarray,
    positive_weight: float,
    ridge: float,
) -> WeightedLogisticFit:
    """Fit a small weighted logistic model with Newton iterations."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float)
    mean = np.nanmean(x, axis=0) if x.size else np.array([], dtype=float)
    scale = np.nanstd(x, axis=0) if x.size else np.array([], dtype=float)
    scale = np.where(scale < EPS, 1.0, scale)
    x_norm = np.nan_to_num((x - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    sample_weight = np.where(y == 1.0, float(positive_weight), 1.0)
    sample_weight = sample_weight / max(float(np.mean(sample_weight)), EPS)
    weighted_rate = float(np.clip(np.sum(sample_weight * y) / np.sum(sample_weight), EPS, 1.0 - EPS))
    coef = np.zeros(design.shape[1], dtype=float)
    coef[0] = math.log(weighted_rate / (1.0 - weighted_rate))
    penalty = np.eye(design.shape[1]) * float(ridge)
    penalty[0, 0] = 0.0
    for _ in range(80):
        prob = l1h2.sigmoid(design @ coef)
        weight = np.clip(sample_weight * prob * (1.0 - prob), EPS, None)
        gradient = design.T @ (sample_weight * (prob - y)) + penalty @ coef
        hessian = (design.T * weight) @ design + penalty
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        coef -= step
        if float(np.linalg.norm(step)) < 1e-7:
            break
    return WeightedLogisticFit(coef=coef, mean=mean, scale=scale)


def predict_weighted_logistic(fit: WeightedLogisticFit, x: np.ndarray) -> np.ndarray:
    """Predict probabilities from a weighted logistic fit."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    x_norm = np.nan_to_num((x - fit.mean) / fit.scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    return l1h2.clip_prob(l1h2.sigmoid(design @ fit.coef))


def fit_ridge(x: np.ndarray, y: np.ndarray, ridge: float) -> RidgeFit:
    """Fit a small ridge linear model with standardized features."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float)
    mean = np.nanmean(x, axis=0) if x.size else np.array([], dtype=float)
    scale = np.nanstd(x, axis=0) if x.size else np.array([], dtype=float)
    scale = np.where(scale < EPS, 1.0, scale)
    x_norm = np.nan_to_num((x - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    penalty = np.eye(design.shape[1]) * float(ridge)
    penalty[0, 0] = 0.0
    coef = np.linalg.pinv(design.T @ design + penalty) @ design.T @ y
    return RidgeFit(coef=coef, mean=mean, scale=scale)


def predict_ridge(fit: RidgeFit, x: np.ndarray) -> np.ndarray:
    """Predict from a small ridge linear fit."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    x_norm = np.nan_to_num((x - fit.mean) / fit.scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    return design @ fit.coef


def positive_weight_value(spec: Any, y: np.ndarray) -> float:
    """Resolve an explicit or balanced positive class weight."""
    if str(spec).lower() == "balanced":
        positives = int(y.sum())
        negatives = int(len(y) - positives)
        return float(negatives / positives) if positives else 1.0
    return float(spec)


def event_y(frame: pd.DataFrame, config: dict[str, Any]) -> np.ndarray:
    """Return primary ge31 event labels."""
    event_col = str(config["events"]["primary"]["event_col"])
    return bool_series(frame[event_col]).astype(int).to_numpy()


def high_tail_support(frame: pd.DataFrame, score_threshold: float, config: dict[str, Any]) -> np.ndarray:
    """Return high-score / radiation-hot support rows for residual correction."""
    score_col = str(config["schema"]["model_score_col"])
    score_support = numeric(frame[score_col]).to_numpy(dtype=float) >= float(score_threshold)
    regime_support = bool_series(frame["radiation_hot_flag"]).to_numpy(dtype=bool)
    return score_support | regime_support


def fit_predict_weighted_logistic_candidate(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_names: list[str],
    params: dict[str, Any],
    config: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Fit and predict one weighted-logistic candidate."""
    y_train = event_y(train, config)
    if len(y_train) < int(config["validation"]["min_train_rows"]) or len(np.unique(y_train)) < 2:
        raise ValueError("insufficient weighted-logistic training rows/classes")
    x_train, medians = matrix_with_medians(train, feature_names)
    x_test, _ = matrix_with_medians(test, feature_names, medians=medians)
    if x_train.shape[1] == 0 or np.unique(x_train, axis=0).shape[0] < 2:
        raise ValueError("insufficient weighted-logistic feature variation")
    pos_weight = positive_weight_value(params["positive_weight"], y_train)
    fit = fit_weighted_logistic(x_train, y_train, positive_weight=pos_weight, ridge=float(params["ridge"]))
    train_prob = predict_weighted_logistic(fit, x_train)
    test_prob = predict_weighted_logistic(fit, x_test)
    return train_prob, test_prob, {"resolved_positive_weight": pos_weight}


def corrected_scores(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_names: list[str],
    params: dict[str, Any],
    config: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fit a high-tail residual correction and return corrected train/test scores."""
    schema = config["schema"]
    score_col = str(schema["model_score_col"])
    target_col = str(schema["target_col"])
    support_threshold = float(params["support_score_threshold"])
    train_support = high_tail_support(train, support_threshold, config)
    test_support = high_tail_support(test, support_threshold, config)
    if int(train_support.sum()) < int(config["validation"]["min_train_rows"]):
        raise ValueError("insufficient high-tail support rows for residual correction")
    x_support, medians = matrix_with_medians(train.loc[train_support], feature_names)
    residual_target = (
        numeric(train.loc[train_support, target_col]).to_numpy(dtype=float)
        - numeric(train.loc[train_support, score_col]).to_numpy(dtype=float)
    )
    fit = fit_ridge(x_support, residual_target, ridge=float(params["ridge"]))
    x_train, _ = matrix_with_medians(train, feature_names, medians=medians)
    x_test, _ = matrix_with_medians(test, feature_names, medians=medians)
    cap = float(params["correction_cap_c"])
    train_correction = np.clip(predict_ridge(fit, x_train), -cap, cap)
    test_correction = np.clip(predict_ridge(fit, x_test), -cap, cap)
    train_score = numeric(train[score_col]).to_numpy(dtype=float)
    test_score = numeric(test[score_col]).to_numpy(dtype=float)
    train_corrected = np.where(train_support, train_score + train_correction, train_score)
    test_corrected = np.where(test_support, test_score + test_correction, test_score)
    return train_corrected, test_corrected, train_correction, test_correction


def fit_predict_residual_candidate(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_names: list[str],
    params: dict[str, Any],
    config: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Fit residual correction and isotonic P_ge31 calibration."""
    y_train = event_y(train, config)
    if y_train.sum() < int(config["validation"]["min_train_events"]) or (1 - y_train).sum() < int(config["validation"]["min_train_non_events"]):
        raise ValueError("insufficient residual-correction event support")
    train_corrected, test_corrected, train_correction, test_correction = corrected_scores(train, test, feature_names, params, config)
    _, test_prob = l1h2.isotonic_fit_predict(train_corrected, y_train, test_corrected)
    train_prob, _ = l1h2.isotonic_fit_predict(train_corrected, y_train, train_corrected)
    info = {
        "mean_train_correction_c": float(np.mean(train_correction)),
        "mean_test_correction_c": float(np.mean(test_correction)),
        "p95_abs_test_correction_c": float(np.quantile(np.abs(test_correction), 0.95)) if len(test_correction) else np.nan,
    }
    return train_prob, test_prob, info


def fit_predict_candidate(
    candidate_id: str,
    candidate: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_names: list[str],
    params: dict[str, Any],
    config: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Fit one challenger candidate on training stations and predict test rows."""
    family = str(candidate["family"])
    if family == "weighted_logistic":
        return fit_predict_weighted_logistic_candidate(train, test, feature_names, params, config)
    if family == "residual_correction_isotonic":
        return fit_predict_residual_candidate(train, test, feature_names, params, config)
    raise ValueError(f"Candidate {candidate_id} family is not runnable: {family}")


def candidate_param_grid(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the fixed small grid for one challenger."""
    if candidate.get("implementation_status", "run") != "run":
        return []
    family = str(candidate["family"])
    if family == "weighted_logistic":
        return [
            {"positive_weight": weight, "ridge": ridge}
            for weight, ridge in itertools.product(candidate["positive_weight_grid"], candidate["ridge_grid"])
        ]
    if family == "residual_correction_isotonic":
        return [
            {"support_score_threshold": threshold, "ridge": ridge, "correction_cap_c": cap}
            for threshold, ridge, cap in itertools.product(
                candidate["support_score_threshold_grid"],
                candidate["ridge_grid"],
                candidate["correction_cap_c"],
            )
        ]
    return []


def prediction_metadata(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Return common metadata columns carried into prediction and decision outputs."""
    schema = config["schema"]
    keep = [
        "row_id",
        schema["station_col"],
        schema["fold_col"],
        schema["cv_scheme_col"],
        schema["timestamp_col"],
        schema["date_col"],
        schema["hour_col"],
        schema["target_col"],
        schema["model_score_col"],
        "obs_ge31",
        "obs_ge33",
        "expected_exceedance_above31_c",
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
    return frame[[col for col in keep if col in frame.columns]].copy()


def make_prediction_rows(
    test: pd.DataFrame,
    values: np.ndarray,
    candidate_id: str,
    candidate_family: str,
    output_kind: str,
    diagnostic_only: bool,
    fold_id: str,
    params: dict[str, Any],
    feature_names: list[str],
    config: dict[str, Any],
    fit_info: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Create OOF prediction rows for one held-out station."""
    event = config["events"]["primary"]
    pred = prediction_metadata(test, config)
    pred["candidate_id"] = candidate_id
    pred["candidate_family"] = candidate_family
    pred["event_target"] = event["id"]
    pred["event_col"] = event["event_col"]
    pred["official_event_threshold_c"] = float(event["threshold_c"])
    pred["event_observed"] = event_y(test, config)
    pred["output_kind"] = output_kind
    pred["diagnostic_only"] = bool(diagnostic_only)
    pred["validation_method"] = VALIDATION_METHOD
    pred["fold_id"] = fold_id
    pred["output_value"] = values
    pred["probability"] = values if output_kind == "probability" else np.nan
    pred["p_ge31"] = values if output_kind == "probability" else np.nan
    pred["selected_params"] = params_text(params)
    pred["feature_columns"] = semicolon(feature_names)
    if fit_info:
        for key, value in fit_info.items():
            pred[key] = value
    return pred


def choices_from_values(y: np.ndarray, values: np.ndarray, output_kind: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Choose only required operating points from training-station values."""
    choices = l1h2.choose_thresholds(y, values, output_kind, config)
    return [choice for choice in choices if choice["operating_point"] in {"best_F1", "recall_90", "precision_70"}]


def add_fixed_current_threshold_choice(
    choices: list[dict[str, Any]],
    threshold: float,
    y: np.ndarray,
    values: np.ndarray,
) -> list[dict[str, Any]]:
    """Append the current-companion threshold as a fixed probability comparator."""
    fixed = {
        "operating_point": "current_companion_threshold",
        "threshold_source": "fixed_current_companion_best_f1_threshold",
        "achievable": np.isfinite(threshold),
        "threshold": float(threshold),
    }
    fixed.update(l1h2.confusion_counts(y, values, float(threshold)) if np.isfinite(threshold) else {})
    return [*choices, fixed]


def append_threshold_decisions(
    prediction_rows: pd.DataFrame,
    choices: list[dict[str, Any]],
    fold_id: str,
    threshold_rows: list[dict[str, Any]],
    decision_parts: list[pd.DataFrame],
) -> None:
    """Evaluate selected thresholds on one held-out station."""
    y = prediction_rows["event_observed"].to_numpy(dtype=int)
    values = prediction_rows["output_value"].to_numpy(dtype=float)
    base = {
        "candidate_id": prediction_rows["candidate_id"].iloc[0],
        "candidate_family": prediction_rows["candidate_family"].iloc[0],
        "event_target": prediction_rows["event_target"].iloc[0],
        "official_event_threshold_c": prediction_rows["official_event_threshold_c"].iloc[0],
        "output_kind": prediction_rows["output_kind"].iloc[0],
        "diagnostic_only": bool(prediction_rows["diagnostic_only"].iloc[0]),
        "validation_method": VALIDATION_METHOD,
        "fold_id": fold_id,
        "selected_params": prediction_rows["selected_params"].iloc[0],
        "feature_columns": prediction_rows["feature_columns"].iloc[0],
    }
    for choice in choices:
        threshold = float(choice.get("threshold", np.nan))
        row_base = {
            **base,
            "operating_point": choice["operating_point"],
            "threshold_source": choice["threshold_source"],
            "achievable": bool(choice.get("achievable", True)),
        }
        if not row_base["achievable"] or not np.isfinite(threshold):
            threshold_rows.append({**row_base, "status": "skipped_unachievable", "threshold": np.nan})
            continue
        metrics = l1h2.confusion_counts(y, values, threshold)
        threshold_rows.append({**row_base, "status": "evaluated_on_heldout", "threshold": threshold, **metrics})
        decisions = prediction_rows.copy()
        decisions["operating_point"] = choice["operating_point"]
        decisions["threshold_source"] = choice["threshold_source"]
        decisions["threshold"] = threshold
        decisions["event_predicted"] = (values >= threshold).astype(int)
        decision_parts.append(decisions)


def inner_oof_predictions(
    candidate_id: str,
    candidate: dict[str, Any],
    train: pd.DataFrame,
    feature_names: list[str],
    params: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Create inner station-held-out predictions within an outer training set."""
    fold_col = str(config["schema"]["fold_col"])
    parts: list[pd.DataFrame] = []
    for inner_fold in sorted(train[fold_col].dropna().astype(str).unique()):
        val_mask = train[fold_col].astype(str).eq(inner_fold)
        inner_train = train[~val_mask].copy()
        inner_val = train[val_mask].copy()
        if inner_train.empty or inner_val.empty:
            continue
        try:
            _, val_values, info = fit_predict_candidate(candidate_id, candidate, inner_train, inner_val, feature_names, params, config)
        except Exception:
            continue
        rows = make_prediction_rows(
            test=inner_val,
            values=val_values,
            candidate_id=candidate_id,
            candidate_family=str(candidate["family"]),
            output_kind="probability",
            diagnostic_only=bool(candidate.get("diagnostic_only", False)),
            fold_id=str(inner_fold),
            params=params,
            feature_names=feature_names,
            config=config,
            fit_info=info,
        )
        parts.append(rows)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def select_inner_params(
    candidate_id: str,
    candidate: dict[str, Any],
    outer_train: pd.DataFrame,
    feature_names: list[str],
    config: dict[str, Any],
) -> tuple[dict[str, Any] | None, pd.DataFrame, pd.DataFrame]:
    """Select fixed-grid hyperparameters using inner station-grouped CV only."""
    selection_rows: list[dict[str, Any]] = []
    predictions_by_params: dict[str, pd.DataFrame] = {}
    for params in candidate_param_grid(candidate):
        pred = inner_oof_predictions(candidate_id, candidate, outer_train, feature_names, params, config)
        key = params_text(params)
        predictions_by_params[key] = pred
        if pred.empty:
            selection_rows.append(
                {
                    "candidate_id": candidate_id,
                    "selected_params": key,
                    "inner_status": "skipped_no_inner_predictions",
                    "inner_n": 0,
                    "inner_F1": np.nan,
                    "inner_CSI": np.nan,
                    "inner_precision": np.nan,
                    "inner_recall": np.nan,
                    "inner_Brier": np.nan,
                    "inner_PR_AUC": np.nan,
                }
            )
            continue
        y = pred["event_observed"].to_numpy(dtype=int)
        values = pred["output_value"].to_numpy(dtype=float)
        choices = choices_from_values(y, values, "probability", config)
        best = next((choice for choice in choices if choice["operating_point"] == "best_F1"), None)
        brier = float(np.mean((values - y) ** 2)) if len(values) else np.nan
        selection_rows.append(
            {
                "candidate_id": candidate_id,
                "selected_params": key,
                "inner_status": "evaluated",
                "inner_n": int(len(pred)),
                "inner_station_count": int(pred["station_id"].nunique()) if "station_id" in pred else np.nan,
                "inner_event_count": int(y.sum()),
                "inner_F1": best.get("F1", np.nan) if best else np.nan,
                "inner_CSI": best.get("CSI", np.nan) if best else np.nan,
                "inner_precision": best.get("precision", np.nan) if best else np.nan,
                "inner_recall": best.get("recall", np.nan) if best else np.nan,
                "inner_threshold": best.get("threshold", np.nan) if best else np.nan,
                "inner_Brier": brier,
                "inner_ROC_AUC": l1h2.roc_auc_binary(y, values) if len(np.unique(y)) == 2 else np.nan,
                "inner_PR_AUC": l1h2.average_precision_binary(y, values) if len(np.unique(y)) == 2 else np.nan,
            }
        )
    selection = pd.DataFrame(selection_rows)
    if selection.empty or selection["inner_status"].ne("evaluated").all():
        return None, pd.DataFrame(), selection
    ranked = selection[selection["inner_status"].eq("evaluated")].copy()
    ranked = ranked.sort_values(
        ["inner_F1", "inner_CSI", "inner_recall", "inner_precision", "inner_Brier", "selected_params"],
        ascending=[False, False, False, False, True, True],
        na_position="last",
    )
    selected_key = str(ranked.iloc[0]["selected_params"])
    selected_params = json.loads(selected_key)
    selected_predictions = predictions_by_params[selected_key]
    return selected_params, selected_predictions, selection


def run_challengers(
    base: pd.DataFrame,
    config: dict[str, Any],
    current_companion_threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run all configured runnable challengers under outer station-held-out CV."""
    fold_col = str(config["schema"]["fold_col"])
    prediction_parts: list[pd.DataFrame] = []
    threshold_rows: list[dict[str, Any]] = []
    decision_parts: list[pd.DataFrame] = []
    selection_parts: list[pd.DataFrame] = []

    for candidate_id, candidate in config["challengers"].items():
        if candidate.get("implementation_status", "run") != "run":
            continue
        feature_names, _ = feature_columns(config, str(candidate["feature_set"]), base)
        for fold_id in sorted(base[fold_col].dropna().astype(str).unique()):
            test_mask = base[fold_col].astype(str).eq(fold_id)
            outer_train = base[~test_mask].copy()
            outer_test = base[test_mask].copy()
            selected_params, inner_pred, selection = select_inner_params(
                candidate_id,
                candidate,
                outer_train,
                feature_names,
                config,
            )
            if not selection.empty:
                selection = selection.copy()
                selection["outer_fold_id"] = fold_id
                selection_parts.append(selection)
            if selected_params is None or inner_pred.empty:
                continue
            try:
                _, test_values, fit_info = fit_predict_candidate(
                    candidate_id,
                    candidate,
                    outer_train,
                    outer_test,
                    feature_names,
                    selected_params,
                    config,
                )
            except Exception:
                continue
            selected_row = selection[selection["selected_params"].eq(params_text(selected_params))].head(1)
            if not selected_row.empty:
                fit_info = {
                    **fit_info,
                    "inner_selected_F1": selected_row["inner_F1"].iloc[0],
                    "inner_selected_CSI": selected_row["inner_CSI"].iloc[0],
                    "inner_selected_precision": selected_row["inner_precision"].iloc[0],
                    "inner_selected_recall": selected_row["inner_recall"].iloc[0],
                    "inner_selected_threshold": selected_row["inner_threshold"].iloc[0],
                }
            pred = make_prediction_rows(
                test=outer_test,
                values=test_values,
                candidate_id=candidate_id,
                candidate_family=str(candidate["family"]),
                output_kind="probability",
                diagnostic_only=bool(candidate.get("diagnostic_only", False)),
                fold_id=str(fold_id),
                params=selected_params,
                feature_names=feature_names,
                config=config,
                fit_info=fit_info,
            )
            prediction_parts.append(pred)
            inner_y = inner_pred["event_observed"].to_numpy(dtype=int)
            inner_values = inner_pred["output_value"].to_numpy(dtype=float)
            choices = choices_from_values(inner_y, inner_values, "probability", config)
            choices = add_fixed_current_threshold_choice(choices, current_companion_threshold, inner_y, inner_values)
            append_threshold_decisions(pred, choices, str(fold_id), threshold_rows, decision_parts)

    predictions = pd.concat(prediction_parts, ignore_index=True) if prediction_parts else pd.DataFrame()
    decisions = pd.concat(decision_parts, ignore_index=True) if decision_parts else pd.DataFrame()
    selections = pd.concat(selection_parts, ignore_index=True) if selection_parts else pd.DataFrame()
    return predictions, pd.DataFrame(threshold_rows), decisions, selections


def source_current_thresholds(config: dict[str, Any]) -> dict[str, float]:
    """Read current-companion best-F1 and recall_90 aggregate thresholds."""
    threshold_path = resolve_path(str(config["inputs"]["threshold_operating_points"]))
    threshold_ops = read_csv(threshold_path)
    model = str(config["baselines"]["current_companion_model"])
    calibrator = str(config["baselines"]["current_companion_calibrator"])
    out: dict[str, float] = {}
    for op in ["best_F1", "recall_90", "selected_candidate_policy"]:
        match = threshold_ops[
            threshold_ops["model_name"].astype(str).eq(model)
            & threshold_ops["output_id"].astype(str).eq(calibrator)
            & threshold_ops["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
            & threshold_ops["operating_point"].astype(str).eq(op)
        ]
        out[op] = float(match["threshold"].iloc[0]) if not match.empty else np.nan
    return out


def current_probability_source(config: dict[str, Any]) -> pd.DataFrame:
    """Load A-L1H.2 current-companion OOF probabilities."""
    path = resolve_path(str(config["inputs"]["probability_predictions_oof"]))
    pred = read_csv(path)
    model = str(config["baselines"]["current_companion_model"])
    calibrator = str(config["baselines"]["current_companion_calibrator"])
    return pred[
        pred["model_name"].astype(str).eq(model)
        & pred["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
        & pred["calibrator_id"].astype(str).eq(calibrator)
    ].copy()


def run_current_companion_baseline(
    base: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reproduce current M4+isotonic station-held-out threshold decisions."""
    fold_col = str(config["schema"]["fold_col"])
    score_col = str(config["schema"]["model_score_col"])
    current_source = current_probability_source(config)
    source_cols = ["row_id", "station_id", "timestamp", "probability"]
    source_cols = [col for col in source_cols if col in current_source.columns]
    source = current_source[source_cols].rename(columns={"probability": "source_probability"})
    method = {
        "id": str(config["baselines"]["current_companion_calibrator"]),
        "family": "isotonic",
        "features": ["score"],
        "diagnostic_only": False,
    }
    calibration_config = {
        **config,
        "calibrators": {
            "min_train_rows": int(config["validation"]["min_train_rows"]),
            "min_isotonic_events": int(config["validation"]["min_train_events"]),
            "min_isotonic_non_events": int(config["validation"]["min_train_non_events"]),
            "empirical_bin_count": 10,
        },
    }
    prediction_parts: list[pd.DataFrame] = []
    threshold_rows: list[dict[str, Any]] = []
    decision_parts: list[pd.DataFrame] = []
    for fold_id in sorted(base[fold_col].dropna().astype(str).unique()):
        test_mask = base[fold_col].astype(str).eq(fold_id)
        train = base[~test_mask].copy()
        test = base[test_mask].copy()
        train_prob, test_prob, fit_info = l1h2.fit_predict_calibrator(method, train, test, "obs_ge31", score_col, calibration_config)
        if train_prob is None or test_prob is None:
            continue
        pred = make_prediction_rows(
            test=test,
            values=test_prob,
            candidate_id="current_companion_m4_isotonic",
            candidate_family="current_companion_probability",
            output_kind="probability",
            diagnostic_only=False,
            fold_id=str(fold_id),
            params={"source": "A-L1H.2 isotonic_score_only"},
            feature_names=["model_score"],
            config=config,
            fit_info=fit_info,
        )
        if not source.empty:
            merge_keys = [col for col in ["row_id", "station_id", "timestamp"] if col in pred.columns and col in source.columns]
            pred = pred.merge(source, on=merge_keys, how="left")
            pred["refit_probability"] = pred["probability"]
            pred["source_probability_delta_abs"] = (pred["source_probability"] - pred["refit_probability"]).abs()
            pred["probability"] = pred["source_probability"].fillna(pred["refit_probability"])
            pred["output_value"] = pred["probability"]
            pred["p_ge31"] = pred["probability"]
        prediction_parts.append(pred)
        train_y = event_y(train, config)
        choices = choices_from_values(train_y, train_prob, "probability", config)
        choices = [choice for choice in choices if choice["operating_point"] in {"best_F1", "recall_90"}]
        append_threshold_decisions(pred, choices, str(fold_id), threshold_rows, decision_parts)
    predictions = pd.concat(prediction_parts, ignore_index=True) if prediction_parts else pd.DataFrame()
    decisions = pd.concat(decision_parts, ignore_index=True) if decision_parts else pd.DataFrame()
    return predictions, pd.DataFrame(threshold_rows), decisions


def run_fixed_score_baselines(selected: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate fixed score>=31 baselines for M4 and M7."""
    schema = config["schema"]
    model_col = str(schema["model_name_col"])
    fold_col = str(schema["fold_col"])
    score_col = str(schema["model_score_col"])
    prediction_parts: list[pd.DataFrame] = []
    threshold_rows: list[dict[str, Any]] = []
    decision_parts: list[pd.DataFrame] = []
    for model_name in config["baselines"]["fixed_score_models"]:
        model_df = selected[selected[model_col].astype(str).eq(str(model_name))].copy()
        candidate_id = f"{model_name}_fixed_score_31"
        for fold_id in sorted(model_df[fold_col].dropna().astype(str).unique()):
            test = model_df[model_df[fold_col].astype(str).eq(fold_id)].copy()
            values = numeric(test[score_col]).to_numpy(dtype=float)
            pred = make_prediction_rows(
                test=test,
                values=values,
                candidate_id=candidate_id,
                candidate_family="fixed_score_baseline",
                output_kind="score",
                diagnostic_only=False,
                fold_id=str(fold_id),
                params={"threshold": 31.0},
                feature_names=["model_score"],
                config=config,
            )
            prediction_parts.append(pred)
            choice = {
                "operating_point": "fixed_score_31",
                "threshold_source": "fixed",
                "achievable": True,
                "threshold": 31.0,
            }
            append_threshold_decisions(pred, [choice], str(fold_id), threshold_rows, decision_parts)
    predictions = pd.concat(prediction_parts, ignore_index=True) if prediction_parts else pd.DataFrame()
    decisions = pd.concat(decision_parts, ignore_index=True) if decision_parts else pd.DataFrame()
    return predictions, pd.DataFrame(threshold_rows), decisions


def aggregate_threshold_metrics(fold_thresholds: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fold-level threshold rows into overall operating-point metrics."""
    if fold_thresholds.empty:
        return pd.DataFrame()
    keys = [
        "candidate_id",
        "candidate_family",
        "event_target",
        "official_event_threshold_c",
        "output_kind",
        "diagnostic_only",
        "validation_method",
        "operating_point",
        "threshold_source",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in fold_thresholds.groupby(keys, dropna=False):
        evaluated = group[group["status"].eq("evaluated_on_heldout")].copy()
        skipped = group[~group["status"].eq("evaluated_on_heldout")].copy()
        base = dict(zip(keys, key))
        if evaluated.empty:
            rows.append(
                {
                    **base,
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
                **base,
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
                "selected_params_summary": semicolon(evaluated.get("selected_params", pd.Series(dtype=object)).dropna().unique()),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["event_target", "candidate_id", "operating_point"])


def append_selected_policy(thresholds: pd.DataFrame, decisions: pd.DataFrame, best_candidate_id: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Duplicate best_F1 rows for the selected challenger candidate."""
    if not best_candidate_id or thresholds.empty:
        return thresholds, decisions
    mask = (
        thresholds["candidate_id"].eq(best_candidate_id)
        & thresholds["event_target"].eq(PRIMARY_EVENT_ID)
        & thresholds["output_kind"].eq("probability")
        & thresholds["operating_point"].eq("best_F1")
    )
    rows = thresholds[mask].copy()
    if rows.empty:
        return thresholds, decisions
    rows["operating_point"] = "selected_candidate_policy"
    rows["threshold_source"] = "selected_policy_from_best_F1"
    out_thresholds = pd.concat([thresholds, rows], ignore_index=True)
    if decisions.empty:
        return out_thresholds, decisions
    dmask = (
        decisions["candidate_id"].eq(best_candidate_id)
        & decisions["event_target"].eq(PRIMARY_EVENT_ID)
        & decisions["output_kind"].eq("probability")
        & decisions["operating_point"].eq("best_F1")
    )
    drows = decisions[dmask].copy()
    if not drows.empty:
        drows["operating_point"] = "selected_candidate_policy"
        drows["threshold_source"] = "selected_policy_from_best_F1"
        decisions = pd.concat([decisions, drows], ignore_index=True)
    return out_thresholds, decisions


def make_reliability_metrics(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build reliability bins and ECE/MCE for probability candidates."""
    if predictions.empty:
        return pd.DataFrame()
    work = predictions[predictions["output_kind"].eq("probability")].copy()
    if work.empty:
        return pd.DataFrame()
    low_support = int(config["analysis"]["low_support_n"])
    keys = ["candidate_id", "candidate_family", "event_target", "diagnostic_only", "validation_method"]
    rows: list[pd.DataFrame] = []
    for key, group in work.groupby(keys, dropna=False):
        for bin_kind in ["fixed", "quantile"]:
            g = group[["probability", "event_observed", "station_id"]].dropna().copy()
            if g.empty:
                continue
            if bin_kind == "fixed":
                step = float(config["analysis"]["fixed_probability_bin_step"])
                edges = np.round(np.arange(0.0, 1.0 + step, step), 6)
                labels = l1h2.bin_labels(edges)
                g["probability_bin"] = pd.cut(
                    g["probability"],
                    bins=edges,
                    labels=labels,
                    include_lowest=True,
                    right=False,
                ).astype(str)
                g.loc[g["probability"] >= 1.0, "probability_bin"] = labels[-1]
            else:
                q = min(int(config["analysis"]["quantile_bin_count"]), g["probability"].nunique())
                if q < 2:
                    continue
                g["probability_bin"] = pd.qcut(g["probability"], q=q, duplicates="drop").astype(str)
            out = g.groupby("probability_bin", observed=False).agg(
                n=("event_observed", "size"),
                event_count=("event_observed", "sum"),
                mean_predicted_probability=("probability", "mean"),
                p_min=("probability", "min"),
                p_max=("probability", "max"),
                station_count=("station_id", "nunique"),
            ).reset_index()
            out["observed_event_rate"] = out["event_count"] / out["n"]
            out["calibration_gap"] = out["mean_predicted_probability"] - out["observed_event_rate"]
            out["abs_calibration_gap"] = out["calibration_gap"].abs()
            total_n = float(out["n"].sum())
            out["ECE"] = float(((out["n"] / total_n) * out["abs_calibration_gap"]).sum()) if total_n else np.nan
            out["MCE"] = float(out["abs_calibration_gap"].max()) if len(out) else np.nan
            out["low_support"] = out["n"] < low_support
            out["low_support_bin_count"] = int(out["low_support"].sum())
            out["bin_kind"] = bin_kind
            for col, value in zip(keys, key):
                out[col] = value
            rows.append(out)
    reliability = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if reliability.empty:
        return reliability
    ordered = keys + [
        "bin_kind",
        "probability_bin",
        "n",
        "event_count",
        "observed_event_rate",
        "mean_predicted_probability",
        "calibration_gap",
        "abs_calibration_gap",
        "ECE",
        "MCE",
        "p_min",
        "p_max",
        "station_count",
        "low_support",
        "low_support_bin_count",
    ]
    return reliability[[col for col in ordered if col in reliability.columns]]


def reliability_summary(reliability: pd.DataFrame) -> pd.DataFrame:
    """Extract one reliability summary row per candidate."""
    if reliability.empty:
        return pd.DataFrame()
    keys = ["candidate_id", "candidate_family", "event_target", "diagnostic_only", "validation_method", "bin_kind"]
    summary = (
        reliability.groupby(keys, dropna=False)
        .agg(
            ECE=("ECE", "first"),
            MCE=("MCE", "first"),
            reliability_bin_count=("probability_bin", "nunique"),
            low_support_bin_count=("low_support_bin_count", "first"),
        )
        .reset_index()
    )
    wide = summary.pivot_table(
        index=["candidate_id", "candidate_family", "event_target", "diagnostic_only", "validation_method"],
        columns="bin_kind",
        values=["ECE", "MCE", "reliability_bin_count", "low_support_bin_count"],
        aggfunc="first",
    )
    wide.columns = [f"{metric}_{kind}" for metric, kind in wide.columns]
    return wide.reset_index()


def make_overall_metrics(predictions: pd.DataFrame, reliability: pd.DataFrame) -> pd.DataFrame:
    """Compute ge31 overall ranking and probability metrics."""
    if predictions.empty:
        return pd.DataFrame()
    rel_summary = reliability_summary(reliability)
    keys = ["candidate_id", "candidate_family", "event_target", "output_kind", "diagnostic_only", "validation_method"]
    rows: list[dict[str, Any]] = []
    for key, group in predictions.groupby(keys, dropna=False):
        y = group["event_observed"].to_numpy(dtype=int)
        values = group["output_value"].to_numpy(dtype=float)
        prob = group["probability"].to_numpy(dtype=float) if key[3] == "probability" else np.full(len(group), np.nan)
        row = {
            **dict(zip(keys, key)),
            "n": int(len(group)),
            "event_count": int(y.sum()),
            "event_rate": safe_div(int(y.sum()), len(y)),
            "station_count": int(group["station_id"].nunique()) if "station_id" in group else np.nan,
            "fold_count": int(group["fold_id"].nunique()) if "fold_id" in group else np.nan,
            "ROC_AUC": l1h2.roc_auc_binary(y, values) if len(np.unique(y)) == 2 else np.nan,
            "PR_AUC": l1h2.average_precision_binary(y, values) if len(np.unique(y)) == 2 else np.nan,
            "Brier": float(np.mean((prob - y) ** 2)) if key[3] == "probability" else np.nan,
            "mean_output_value": float(np.nanmean(values)) if len(values) else np.nan,
            "p05_output_value": float(np.nanquantile(values, 0.05)) if len(values) else np.nan,
            "p50_output_value": float(np.nanquantile(values, 0.50)) if len(values) else np.nan,
            "p95_output_value": float(np.nanquantile(values, 0.95)) if len(values) else np.nan,
            "p05_predicted_probability": float(np.nanquantile(prob, 0.05)) if key[3] == "probability" else np.nan,
            "p50_predicted_probability": float(np.nanquantile(prob, 0.50)) if key[3] == "probability" else np.nan,
            "p95_predicted_probability": float(np.nanquantile(prob, 0.95)) if key[3] == "probability" else np.nan,
            "mean_expected_exceedance_above31_c": float(group["expected_exceedance_above31_c"].mean()) if "expected_exceedance_above31_c" in group else np.nan,
            "selected_params_summary": semicolon(group.get("selected_params", pd.Series(dtype=object)).dropna().unique()),
            "feature_columns": semicolon(group.get("feature_columns", pd.Series(dtype=object)).dropna().unique()),
        }
        rows.append(row)
    metrics = pd.DataFrame(rows)
    if not rel_summary.empty:
        metrics = metrics.merge(rel_summary, on=["candidate_id", "candidate_family", "event_target", "diagnostic_only", "validation_method"], how="left")
    if "ECE_fixed" not in metrics.columns:
        metrics["ECE_fixed"] = np.nan
    if "ECE_quantile" not in metrics.columns:
        metrics["ECE_quantile"] = np.nan
    return metrics.sort_values(["event_target", "output_kind", "candidate_id"])


def aggregate_by_station(decisions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Aggregate threshold decisions by station."""
    if decisions.empty:
        return pd.DataFrame()
    focus = set(str(station) for station in config["analysis"].get("focus_stations", []))
    keys = ["candidate_id", "candidate_family", "event_target", "output_kind", "validation_method", "operating_point", "station_id"]
    rows: list[dict[str, Any]] = []
    for key, group in decisions.groupby(keys, dropna=False):
        y = group["event_observed"].to_numpy(dtype=int)
        pred = group["event_predicted"].to_numpy(dtype=int)
        values = group["output_value"].to_numpy(dtype=float)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        rows.append(
            {
                **dict(zip(keys, key)),
                "focus_station_flag": str(key[-1]) in focus,
                "threshold_mean": group["threshold"].mean(),
                "n": int(len(group)),
                "event_count": int(y.sum()),
                "observed_event_rate": safe_div(int(y.sum()), len(y)),
                "mean_output_value": float(np.nanmean(values)) if len(values) else np.nan,
                "probability_bias": float(np.nanmean(values) - y.mean()) if key[3] == "probability" and len(values) else np.nan,
                "Brier": float(np.nanmean((values - y) ** 2)) if key[3] == "probability" and len(values) else np.nan,
                "mean_expected_exceedance_above31_c": float(group["expected_exceedance_above31_c"].mean()) if "expected_exceedance_above31_c" in group else np.nan,
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
    return pd.DataFrame(rows).sort_values(["event_target", "candidate_id", "operating_point", "station_id"])


def aggregate_one_regime(decisions: pd.DataFrame, variable: str) -> pd.DataFrame:
    """Aggregate threshold decisions by one regime variable."""
    if variable not in decisions.columns:
        return pd.DataFrame()
    work = decisions.copy()
    work["regime_bin"] = work[variable].astype(str)
    keys = ["candidate_id", "candidate_family", "event_target", "output_kind", "validation_method", "operating_point", "regime_bin"]
    rows: list[dict[str, Any]] = []
    for key, group in work.groupby(keys, dropna=False):
        y = group["event_observed"].to_numpy(dtype=int)
        pred = group["event_predicted"].to_numpy(dtype=int)
        values = group["output_value"].to_numpy(dtype=float)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        rows.append(
            {
                "regime_variable": variable,
                **dict(zip(keys, key)),
                "threshold_mean": group["threshold"].mean(),
                "n": int(len(group)),
                "event_count": int(y.sum()),
                "observed_event_rate": safe_div(int(y.sum()), len(y)),
                "mean_output_value": float(np.nanmean(values)) if len(values) else np.nan,
                "probability_bias": float(np.nanmean(values) - y.mean()) if key[3] == "probability" and len(values) else np.nan,
                "mean_expected_exceedance_above31_c": float(group["expected_exceedance_above31_c"].mean()) if "expected_exceedance_above31_c" in group else np.nan,
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


def aggregate_by_regime(decisions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate threshold decisions by weather-regime diagnostics."""
    variables = [
        "combined_radiation_hot_regime",
        "radiation_hot_flag",
        "shortwave_bin",
        "shortwave_3h_mean_bin",
        "temperature_bin",
        "humidity_bin",
        "wind_bin",
        "cloud_cover_bin",
    ]
    parts = [aggregate_one_regime(decisions, variable) for variable in variables if variable in decisions.columns]
    return pd.concat([part for part in parts if not part.empty], ignore_index=True) if parts else pd.DataFrame()


def top_station_text(merged: pd.DataFrame, value_col: str, station_col: str = "station_id", positive: bool = True) -> str:
    """Return compact top-station diagnostics."""
    if merged.empty or value_col not in merged.columns:
        return ""
    work = merged.copy()
    work = work[work[value_col] > 0] if positive else work[work[value_col] < 0]
    if work.empty:
        return ""
    work = work.sort_values(value_col, ascending=not positive).head(5)
    return semicolon(f"{row[station_col]}:{fmt(row[value_col], 0)}" for _, row in work.iterrows())


def make_pairwise(
    thresholds: pd.DataFrame,
    by_station: pd.DataFrame,
    by_regime: pd.DataFrame,
) -> pd.DataFrame:
    """Compare each non-current candidate against current companion best-F1 and recall_90."""
    if thresholds.empty:
        return pd.DataFrame()
    baseline_rows = thresholds[
        thresholds["candidate_id"].eq("current_companion_m4_isotonic")
        & thresholds["event_target"].eq(PRIMARY_EVENT_ID)
        & thresholds["operating_point"].isin(["best_F1", "recall_90"])
        & thresholds["status"].eq("evaluated_on_heldout")
    ].copy()
    candidate_rows = thresholds[
        thresholds["event_target"].eq(PRIMARY_EVENT_ID)
        & thresholds["status"].eq("evaluated_on_heldout")
        & ~thresholds["candidate_id"].eq("current_companion_m4_isotonic")
    ].copy()
    rows: list[dict[str, Any]] = []
    for _, base in baseline_rows.iterrows():
        for _, cand in candidate_rows.iterrows():
            station_improve = ""
            station_worse_fp = ""
            if not by_station.empty:
                base_station = by_station[
                    by_station["candidate_id"].eq(base["candidate_id"])
                    & by_station["operating_point"].eq(base["operating_point"])
                ][["station_id", "FN", "FP"]].rename(columns={"FN": "baseline_FN", "FP": "baseline_FP"})
                cand_station = by_station[
                    by_station["candidate_id"].eq(cand["candidate_id"])
                    & by_station["operating_point"].eq(cand["operating_point"])
                ][["station_id", "FN", "FP"]].rename(columns={"FN": "candidate_FN", "FP": "candidate_FP"})
                merged = cand_station.merge(base_station, on="station_id", how="inner")
                if not merged.empty:
                    merged["misses_improved_count"] = merged["baseline_FN"] - merged["candidate_FN"]
                    merged["false_alarms_worsened_count"] = merged["candidate_FP"] - merged["baseline_FP"]
                    station_improve = top_station_text(merged, "misses_improved_count", positive=True)
                    station_worse_fp = top_station_text(merged, "false_alarms_worsened_count", positive=True)

            radiation_hot_miss_improvement = np.nan
            radiation_hot_false_alarm_delta = np.nan
            radiation_hot_recall_delta = np.nan
            if not by_regime.empty:
                base_hot = by_regime[
                    by_regime["candidate_id"].eq(base["candidate_id"])
                    & by_regime["operating_point"].eq(base["operating_point"])
                    & by_regime["regime_variable"].eq("combined_radiation_hot_regime")
                    & by_regime["regime_bin"].eq("radiation_hot")
                ]
                cand_hot = by_regime[
                    by_regime["candidate_id"].eq(cand["candidate_id"])
                    & by_regime["operating_point"].eq(cand["operating_point"])
                    & by_regime["regime_variable"].eq("combined_radiation_hot_regime")
                    & by_regime["regime_bin"].eq("radiation_hot")
                ]
                if not base_hot.empty and not cand_hot.empty:
                    radiation_hot_miss_improvement = float(base_hot["FN"].iloc[0] - cand_hot["FN"].iloc[0])
                    radiation_hot_false_alarm_delta = float(cand_hot["FP"].iloc[0] - base_hot["FP"].iloc[0])
                    radiation_hot_recall_delta = float(cand_hot["recall"].iloc[0] - base_hot["recall"].iloc[0])
            rows.append(
                {
                    "baseline_candidate_id": base["candidate_id"],
                    "baseline_operating_point": base["operating_point"],
                    "candidate_id": cand["candidate_id"],
                    "candidate_family": cand["candidate_family"],
                    "candidate_operating_point": cand["operating_point"],
                    "delta_recall": cand["recall"] - base["recall"],
                    "delta_miss_rate": cand["miss_rate"] - base["miss_rate"],
                    "delta_precision": cand["precision"] - base["precision"],
                    "delta_false_alarm_ratio": cand["false_alarm_ratio"] - base["false_alarm_ratio"],
                    "delta_F1": cand["F1"] - base["F1"],
                    "delta_CSI": cand["CSI"] - base["CSI"],
                    "candidate_precision": cand["precision"],
                    "candidate_recall": cand["recall"],
                    "candidate_F1": cand["F1"],
                    "candidate_CSI": cand["CSI"],
                    "candidate_false_alarm_ratio": cand["false_alarm_ratio"],
                    "candidate_miss_rate": cand["miss_rate"],
                    "station_where_it_improves_misses": station_improve,
                    "station_where_it_worsens_false_alarms": station_worse_fp,
                    "radiation_hot_misses_improved_count": radiation_hot_miss_improvement,
                    "radiation_hot_false_alarm_delta": radiation_hot_false_alarm_delta,
                    "radiation_hot_recall_delta": radiation_hot_recall_delta,
                }
            )
    return pd.DataFrame(rows).sort_values(["baseline_operating_point", "candidate_id", "candidate_operating_point"]) if rows else pd.DataFrame()


def source_baseline_reproduction(thresholds: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compare reproduced current-companion rows against A-L1H.2 source metrics."""
    source_path = resolve_path(str(config["inputs"]["threshold_operating_points"]))
    source = read_csv(source_path)
    model = str(config["baselines"]["current_companion_model"])
    calibrator = str(config["baselines"]["current_companion_calibrator"])
    source_focus = source[
        source["model_name"].astype(str).eq(model)
        & source["output_id"].astype(str).eq(calibrator)
        & source["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
        & source["operating_point"].astype(str).isin(["best_F1", "recall_90"])
    ][["operating_point", "precision", "recall", "F1", "CSI", "false_alarm_ratio", "miss_rate", "TP", "FP", "FN", "TN"]].copy()
    repro = thresholds[
        thresholds["candidate_id"].eq("current_companion_m4_isotonic")
        & thresholds["event_target"].eq(PRIMARY_EVENT_ID)
        & thresholds["operating_point"].isin(["best_F1", "recall_90"])
    ][["operating_point", "precision", "recall", "F1", "CSI", "false_alarm_ratio", "miss_rate", "TP", "FP", "FN", "TN"]].copy()
    merged = repro.merge(source_focus, on="operating_point", suffixes=("_reproduced", "_source"), how="outer")
    for metric in ["precision", "recall", "F1", "CSI", "false_alarm_ratio", "miss_rate", "TP", "FP", "FN", "TN"]:
        if f"{metric}_reproduced" in merged.columns and f"{metric}_source" in merged.columns:
            merged[f"{metric}_delta"] = merged[f"{metric}_reproduced"] - merged[f"{metric}_source"]
    return merged


def choose_best_challenger(thresholds: pd.DataFrame, overall: pd.DataFrame, config: dict[str, Any]) -> tuple[str | None, str, pd.DataFrame]:
    """Apply promotion rules and return the best challenger decision."""
    if thresholds.empty:
        return None, "BLOCKED", pd.DataFrame()
    current = thresholds[
        thresholds["candidate_id"].eq("current_companion_m4_isotonic")
        & thresholds["operating_point"].eq("best_F1")
        & thresholds["event_target"].eq(PRIMARY_EVENT_ID)
    ]
    if current.empty:
        return None, "BLOCKED", pd.DataFrame()
    base = current.iloc[0]
    rel = reliability_summary_from_overall(overall, "current_companion_m4_isotonic")
    base_brier = rel.get("Brier", np.nan)
    base_ece = rel.get("ECE_fixed", np.nan)
    min_precision = float(config["analysis"]["promotion_min_precision"])
    max_brier_delta = float(config["analysis"]["promotion_max_brier_delta"])
    max_ece_delta = float(config["analysis"]["promotion_max_ece_delta"])
    rows: list[dict[str, Any]] = []
    candidates = thresholds[
        thresholds["event_target"].eq(PRIMARY_EVENT_ID)
        & thresholds["output_kind"].eq("probability")
        & thresholds["status"].eq("evaluated_on_heldout")
        & thresholds["operating_point"].eq("best_F1")
        & ~thresholds["candidate_id"].eq("current_companion_m4_isotonic")
    ].copy()
    for _, cand in candidates.iterrows():
        cand_rel = reliability_summary_from_overall(overall, str(cand["candidate_id"]))
        brier_delta = cand_rel.get("Brier", np.nan) - base_brier if np.isfinite(base_brier) else np.nan
        ece_delta = cand_rel.get("ECE_fixed", np.nan) - base_ece if np.isfinite(base_ece) else np.nan
        recall_improved = bool(cand["recall"] > base["recall"] + 1e-12 or cand["miss_rate"] < base["miss_rate"] - 1e-12)
        precision_ok = bool(cand["precision"] >= min_precision)
        csi_ok = bool(cand["CSI"] >= base["CSI"] - 1e-12)
        reliability_ok = bool(
            (not np.isfinite(brier_delta) or brier_delta <= max_brier_delta)
            and (not np.isfinite(ece_delta) or ece_delta <= max_ece_delta)
        )
        no_leakage = True
        if recall_improved and precision_ok and csi_ok and reliability_ok and no_leakage:
            status = "PROMISING_CHALLENGER"
        elif recall_improved:
            status = "RECALL_FIRST_DIAGNOSTIC"
        else:
            status = "WEAK_OR_NEGATIVE"
        rows.append(
            {
                "candidate_id": cand["candidate_id"],
                "candidate_family": cand["candidate_family"],
                "operating_point": cand["operating_point"],
                "promotion_status": status,
                "recall_improved": recall_improved,
                "precision_ok": precision_ok,
                "csi_ok": csi_ok,
                "reliability_ok": reliability_ok,
                "no_leakage": no_leakage,
                "delta_recall": cand["recall"] - base["recall"],
                "delta_miss_rate": cand["miss_rate"] - base["miss_rate"],
                "delta_precision": cand["precision"] - base["precision"],
                "delta_F1": cand["F1"] - base["F1"],
                "delta_CSI": cand["CSI"] - base["CSI"],
                "Brier_delta": brier_delta,
                "ECE_fixed_delta": ece_delta,
                "precision": cand["precision"],
                "recall": cand["recall"],
                "F1": cand["F1"],
                "CSI": cand["CSI"],
            }
        )
    decisions = pd.DataFrame(rows)
    if decisions.empty:
        return None, "WEAK_OR_NEGATIVE", decisions
    ranked = decisions.copy()
    status_rank = {"PROMISING_CHALLENGER": 0, "RECALL_FIRST_DIAGNOSTIC": 1, "WEAK_OR_NEGATIVE": 2}
    ranked["status_rank"] = ranked["promotion_status"].map(status_rank).fillna(3)
    ranked = ranked.sort_values(["status_rank", "F1", "CSI", "recall", "precision"], ascending=[True, False, False, False, False])
    best = ranked.iloc[0]
    if (decisions["promotion_status"] == "PROMISING_CHALLENGER").any():
        decision_status = "PROMISING_CHALLENGER"
    elif (decisions["promotion_status"] == "RECALL_FIRST_DIAGNOSTIC").any():
        decision_status = "RECALL_FIRST_DIAGNOSTIC"
    else:
        decision_status = "WEAK_OR_NEGATIVE"
    return str(best["candidate_id"]), decision_status, decisions


def reliability_summary_from_overall(overall: pd.DataFrame, candidate_id: str) -> dict[str, float]:
    """Return probability reliability fields for one candidate."""
    if overall.empty:
        return {}
    row = overall[
        overall["candidate_id"].eq(candidate_id)
        & overall["event_target"].eq(PRIMARY_EVENT_ID)
        & overall["output_kind"].eq("probability")
    ]
    if row.empty:
        return {}
    out = row.iloc[0].to_dict()
    return {str(key): float(value) for key, value in out.items() if isinstance(value, (int, float, np.integer, np.floating))}


def comparison_text(pairwise: pd.DataFrame, candidate_id: str | None, baseline_op: str) -> str:
    """Build a compact comparison line for the selected challenger."""
    if not candidate_id or pairwise.empty:
        return "No challenger comparison available."
    rows = pairwise[
        pairwise["candidate_id"].eq(candidate_id)
        & pairwise["baseline_operating_point"].eq(baseline_op)
        & pairwise["candidate_operating_point"].eq("best_F1")
    ]
    if rows.empty:
        return "No matching pairwise row available."
    row = rows.iloc[0]
    return (
        f"{candidate_id} best_F1 vs current {baseline_op}: "
        f"delta recall={fmt(row['delta_recall'])}, delta miss_rate={fmt(row['delta_miss_rate'])}, "
        f"delta precision={fmt(row['delta_precision'])}, delta F1={fmt(row['delta_F1'])}, "
        f"delta CSI={fmt(row['delta_CSI'])}."
    )


def write_report(
    path: Path,
    result: ChallengerRunResult,
    inventory: pd.DataFrame,
    feature_schema: pd.DataFrame,
    reproduction: pd.DataFrame,
    overall: pd.DataFrame,
    thresholds: pd.DataFrame,
    reliability: pd.DataFrame,
    by_station: pd.DataFrame,
    by_regime: pd.DataFrame,
    pairwise: pd.DataFrame,
    promotion: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    """Write the A-L1H.3 Markdown report."""
    baseline_thresholds = thresholds[
        thresholds["candidate_id"].isin(["current_companion_m4_isotonic", "M4_inertia_ridge_fixed_score_31", "M7_compact_weather_ridge_fixed_score_31"])
    ].copy() if not thresholds.empty else pd.DataFrame()
    challenger_thresholds = thresholds[
        ~thresholds["candidate_id"].isin(["current_companion_m4_isotonic", "M4_inertia_ridge_fixed_score_31", "M7_compact_weather_ridge_fixed_score_31"])
        & thresholds["operating_point"].isin(["best_F1", "recall_90", "precision_70", "current_companion_threshold", "selected_candidate_policy"])
    ].copy() if not thresholds.empty else pd.DataFrame()
    reliability_summary_table = reliability_summary(reliability)
    station_focus = by_station[
        by_station["event_target"].eq(PRIMARY_EVENT_ID)
        & by_station["focus_station_flag"].astype(bool)
    ].copy() if not by_station.empty else pd.DataFrame()
    regime_focus = by_regime[
        by_regime["event_target"].eq(PRIMARY_EVENT_ID)
        & by_regime["regime_variable"].isin(["combined_radiation_hot_regime", "shortwave_bin", "shortwave_3h_mean_bin"])
        & by_regime["operating_point"].isin(["best_F1", "recall_90", "selected_candidate_policy"])
    ].copy() if not by_regime.empty else pd.DataFrame()
    hgb_note = feature_schema[
        feature_schema["candidate_id"].eq("hist_gradient_boosting_small")
        & feature_schema["feature_name"].eq("candidate_not_run")
    ]
    lines = [
        "# System A A-L1H.3 High-Tail Challenger Benchmark",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Acceptance status: `{result.acceptance_status}`",
        f"Decision status: `{result.decision_status}`",
        f"Branch: `{git_branch()}`",
        "",
        "## 1. Why A-L1H.3 Exists",
        "",
        "A-L1H.2b accepted `P_ge31` as a retrospective diagnostic companion, not as an official warning probability. The accepted companion improves ge31 capture relative to fixed score 31, but high-tail compression, S142/S139 station caveats, radiation-hot caveats, and low-support ge33 evidence remain. A-L1H.3 therefore runs a small challenger benchmark only to ask whether ge31 miss rate can be reduced without unacceptable false alarms or station/regime overfit.",
        "",
        "This benchmark is not a replacement for the current Level 1 contract.",
        "",
        "## 2. Inputs And No-Leakage Feature Contract",
        "",
        markdown_table(
            inventory,
            ["inventory_role", "path", "exists", "rows_total", "rows_selected_loso", "selected_station_count", "selected_fold_count", "selected_event_count_ge31", "selected_event_count_ge33"],
            limit=10,
        ),
        "",
        "Feature schema summary:",
        "",
        markdown_table(
            feature_schema,
            ["candidate_id", "candidate_family", "implementation_status", "diagnostic_only", "feature_name", "feature_available", "used_as_predictor", "leakage_check", "notes"],
            limit=40,
        ),
        "",
        "Forbidden features were not used: station id, fold, official WBGT, observed event bins, residual columns, event labels, future labels, System B, SOLWEIG, Tmrt, and local morphology station features.",
        "",
        "## 3. Validation Design",
        "",
        "Primary validation is `station_grouped_loso`: each outer fold trains on all other stations and predicts the held-out station. Challenger hyperparameters are selected with inner station-grouped CV on training stations only. Thresholds for challenger best_F1, recall_90, and precision_70 are selected from inner-CV predictions only, then evaluated on the outer held-out station.",
        "",
        f"Fold count: `{inventory.loc[inventory['inventory_role'].eq('residual_weather_merge'), 'selected_fold_count'].iloc[0] if 'selected_fold_count' in inventory else 'NA'}`. Station count: `{inventory.loc[inventory['inventory_role'].eq('residual_weather_merge'), 'selected_station_count'].iloc[0] if 'selected_station_count' in inventory else 'NA'}`.",
        "",
        "The HistGradientBoostingClassifier route was allowed by scope but not run because the bundled runtime does not include sklearn." if not hgb_note.empty else "",
        "",
        "## 4. Baseline Current Companion Performance",
        "",
        "Current companion reproduction check against A-L1H.2 source rows:",
        "",
        markdown_table(
            reproduction,
            ["operating_point", "precision_reproduced", "precision_source", "recall_reproduced", "recall_source", "F1_reproduced", "F1_source", "CSI_reproduced", "CSI_source", "TP_delta", "FP_delta", "FN_delta"],
            limit=8,
        ),
        "",
        "Required baselines:",
        "",
        markdown_table(
            baseline_thresholds.sort_values(["candidate_id", "operating_point"]),
            ["candidate_id", "operating_point", "threshold", "precision", "recall", "F1", "CSI", "false_alarm_ratio", "miss_rate", "TP", "FP", "FN", "TN"],
            limit=12,
        ),
        "",
        "## 5. Challenger Metrics",
        "",
        markdown_table(
            challenger_thresholds.sort_values(["candidate_id", "operating_point"]),
            ["candidate_id", "operating_point", "threshold", "precision", "recall", "F1", "CSI", "false_alarm_ratio", "miss_rate", "TP", "FP", "FN", "TN"],
            limit=32,
        ),
        "",
        "Overall probability and ranking metrics:",
        "",
        markdown_table(
            overall.sort_values(["output_kind", "candidate_id"]),
            ["candidate_id", "output_kind", "diagnostic_only", "n", "event_count", "ROC_AUC", "PR_AUC", "Brier", "ECE_fixed", "ECE_quantile", "p05_predicted_probability", "p50_predicted_probability", "p95_predicted_probability"],
            limit=20,
        ),
        "",
        "Reliability summary:",
        "",
        markdown_table(
            reliability_summary_table.sort_values(["candidate_id"]),
            ["candidate_id", "bin_kind", "ECE", "MCE", "reliability_bin_count", "low_support_bin_count"] if "bin_kind" in reliability_summary_table else ["candidate_id", "ECE_fixed", "MCE_fixed", "ECE_quantile", "MCE_quantile", "reliability_bin_count_fixed", "low_support_bin_count_fixed"],
            limit=20,
        ),
        "",
        "## 6. Pairwise Improvement / Degradation",
        "",
        markdown_table(
            pairwise.sort_values(["baseline_operating_point", "candidate_id", "candidate_operating_point"]),
            ["baseline_operating_point", "candidate_id", "candidate_operating_point", "delta_recall", "delta_miss_rate", "delta_precision", "delta_false_alarm_ratio", "delta_F1", "delta_CSI", "station_where_it_improves_misses", "station_where_it_worsens_false_alarms", "radiation_hot_misses_improved_count", "radiation_hot_false_alarm_delta"],
            limit=40,
        ),
        "",
        "Promotion-rule audit:",
        "",
        markdown_table(
            promotion,
            ["candidate_id", "promotion_status", "recall_improved", "precision_ok", "csi_ok", "reliability_ok", "delta_recall", "delta_miss_rate", "delta_precision", "delta_F1", "delta_CSI", "Brier_delta", "ECE_fixed_delta"],
            limit=12,
        ),
        "",
        "## 7. Station / Regime Diagnostics",
        "",
        "Focus station rows:",
        "",
        markdown_table(
            station_focus.sort_values(["candidate_id", "operating_point", "station_id"]),
            ["candidate_id", "operating_point", "station_id", "event_count", "TP", "FP", "FN", "precision", "recall", "F1", "false_alarm_ratio", "miss_rate", "mean_expected_exceedance_above31_c"],
            limit=36,
        ),
        "",
        "Regime rows:",
        "",
        markdown_table(
            regime_focus.sort_values(["candidate_id", "operating_point", "regime_variable", "regime_bin"]),
            ["candidate_id", "operating_point", "regime_variable", "regime_bin", "event_count", "TP", "FP", "FN", "precision", "recall", "F1", "false_alarm_ratio", "miss_rate"],
            limit=40,
        ),
        "",
        result.station_regime_caveats,
        "",
        "## 8. Promotion To Future Model Card",
        "",
        f"Decision: `{result.decision_status}`.",
        "",
        f"Best challenger: {result.best_challenger}",
        "",
        result.comparison_best_f1,
        "",
        result.comparison_recall90,
        "",
        "A challenger is marked `PROMISING_CHALLENGER` only if it improves recall or miss rate over the current best-F1 companion, keeps precision at or above 0.60 unless explicitly recall-first, improves or matches CSI, keeps Brier/reliability acceptable, survives station-grouped LOSO, and uses no leakage features.",
        "",
        "## 9. A-L2 Hold / Preflight Recommendation",
        "",
        result.a_l2_recommendation,
        "",
        "This lane does not start A-L2 and does not add station-context predictors. If station residual evidence is reviewed later, that should be an explicit A-L2.0 preflight gate rather than a hidden continuation of this benchmark.",
        "",
        "## 10. Claim Boundaries",
        "",
        "- Allowed: retrospective System A WBGT_A temporal severity diagnostics and station-held-out ge31 challenger benchmark evidence.",
        "- Allowed with qualifier: `P_ge31` as a retrospective diagnostic companion only.",
        "- Disallowed: official warning probability, public alert trigger, prospective forecast skill, local 100m WBGT, System A/B coupled risk, SOLWEIG/Tmrt-as-WBGT, and ge33 promotion.",
        "- ge33 remains exploratory only; expected exceedance above 31 C is summarized only as an observed diagnostic context.",
    ]
    path.write_text("\n".join(line for line in lines if line is not None) + "\n", encoding="utf-8")


def write_status(path: Path, config_path: Path, result: ChallengerRunResult) -> None:
    """Write the A-L1H.3 status file."""
    outputs = "\n".join(f"- `{rel(output_path)}`" for output_path in result.output_paths)
    lines = [
        "# A-L1H.3 Status",
        "",
        f"Status: {result.acceptance_status}",
        f"Decision: {result.decision_status}",
        f"Generated: {date.today().isoformat()}",
        f"Branch: {git_branch()}",
        "",
        "## Scope",
        "",
        "Constrained high-tail challenger benchmark against the accepted A-L1H.2 M4+isotonic P_ge31 diagnostic companion.",
        "",
        "## Commands Run",
        "",
        f"- `{Path(sys.executable)} scripts/v11_l1h3_run_high_tail_challenger.py --config {rel(config_path)}`",
        "",
        "## Files Created / Modified",
        "",
        outputs,
        "",
        "## Key Results",
        "",
        f"- Best challenger: {result.best_challenger}",
        f"- Decision: {result.decision_status}",
        f"- Versus current best-F1: {result.comparison_best_f1}",
        f"- Versus current recall90: {result.comparison_recall90}",
        f"- A-L2 recommendation: {result.a_l2_recommendation}",
        "",
        "## Caveats",
        "",
        f"- {result.station_regime_caveats}",
        "- Retrospective station-held-out OOF benchmark only.",
        "- P_ge31 remains diagnostic, not official warning probability.",
        "- No prospective forecast skill is claimed.",
        "- ge33 remains exploratory.",
        "",
        "## Safe To Commit",
        "",
        "- Config, scripts, Chinese documentation, and compact A-L1H.3 benchmark outputs after review.",
        "",
        "## Not Safe To Commit",
        "",
        "- System B outputs, SOLWEIG outputs, raster/raw archive data, .tif/.tiff files, svfs.zip, large hourly forecast CSVs, patch zips, or raw API dumps.",
        "",
        "## Next Recommended Action",
        "",
        result.a_l2_recommendation,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_benchmark(config_path: Path) -> ChallengerRunResult:
    """Run the full A-L1H.3 challenger benchmark."""
    config = load_config(config_path)
    paths = output_paths(config)
    assert_output_scope(paths)
    paths["dir"].mkdir(parents=True, exist_ok=True)

    selected, base, metadata = prepare_analysis_frame(config)
    if not metadata["fold_identity_usable"] or metadata["fold_count"] < 3:
        result = ChallengerRunResult(
            acceptance_status="BLOCKED",
            decision_status="BLOCKED",
            best_challenger="None - station_grouped_loso fold identity was not usable.",
            comparison_best_f1="No valid comparison.",
            comparison_recall90="No valid comparison.",
            station_regime_caveats="Fold/station metadata blocked the benchmark.",
            a_l2_recommendation="Hold A-L2; repair Level 1 validation metadata first.",
            output_paths=[],
        )
        write_status(paths["status"], config_path, result)
        return result

    inventory = input_inventory(config, selected, metadata)
    feature_schema = make_feature_schema(config, base)
    current_thresholds = source_current_thresholds(config)

    current_pred, current_fold_thresholds, current_decisions = run_current_companion_baseline(base, config)
    fixed_pred, fixed_fold_thresholds, fixed_decisions = run_fixed_score_baselines(selected, config)
    challenger_pred, challenger_fold_thresholds, challenger_decisions, selections = run_challengers(
        base,
        config,
        current_companion_threshold=current_thresholds.get("best_F1", np.nan),
    )

    predictions = pd.concat([part for part in [current_pred, fixed_pred, challenger_pred] if not part.empty], ignore_index=True)
    fold_thresholds = pd.concat(
        [part for part in [current_fold_thresholds, fixed_fold_thresholds, challenger_fold_thresholds] if not part.empty],
        ignore_index=True,
    )
    decisions = pd.concat([part for part in [current_decisions, fixed_decisions, challenger_decisions] if not part.empty], ignore_index=True)

    thresholds = aggregate_threshold_metrics(fold_thresholds)
    reliability = make_reliability_metrics(predictions, config)
    overall = make_overall_metrics(predictions, reliability)
    best_candidate_id, decision_status, promotion = choose_best_challenger(thresholds, overall, config)
    thresholds, decisions = append_selected_policy(thresholds, decisions, best_candidate_id)
    by_station = aggregate_by_station(decisions, config)
    by_regime = aggregate_by_regime(decisions)
    pairwise = make_pairwise(thresholds, by_station, by_regime)
    reproduction = source_baseline_reproduction(thresholds, config)

    output_file_paths = [
        paths["inventory"],
        paths["feature_schema"],
        paths["predictions"],
        paths["overall"],
        paths["threshold"],
        paths["reliability"],
        paths["station"],
        paths["regime"],
        paths["pairwise"],
        paths["report"],
        paths["status"],
    ]

    best_label = best_candidate_id or "None"
    if best_candidate_id and not promotion.empty:
        best_row = promotion[promotion["candidate_id"].eq(best_candidate_id)].head(1)
        if not best_row.empty:
            best_label = f"{best_candidate_id} ({best_row['promotion_status'].iloc[0]})"
    caveats = (
        "S142/S139 and radiation-hot / very-high shortwave regimes remain diagnostics; "
        "station/regime structure is not treated as causal proof or prospective skill."
    )
    a_l2 = (
        "Hold A-L2 from this lane. If reviewed station residual evidence remains compelling after Level 1 closeout, "
        "open a separate A-L2.0 preflight; do not merge it into A-L1H.3."
    )
    result = ChallengerRunResult(
        acceptance_status="PASS" if decision_status != "BLOCKED" else "BLOCKED",
        decision_status=decision_status,
        best_challenger=best_label,
        comparison_best_f1=comparison_text(pairwise, best_candidate_id, "best_F1"),
        comparison_recall90=comparison_text(pairwise, best_candidate_id, "recall_90"),
        station_regime_caveats=caveats,
        a_l2_recommendation=a_l2,
        output_paths=output_file_paths,
    )

    inventory.to_csv(paths["inventory"], index=False)
    feature_schema.to_csv(paths["feature_schema"], index=False)
    predictions.to_csv(paths["predictions"], index=False, compression="gzip")
    overall.to_csv(paths["overall"], index=False)
    thresholds.to_csv(paths["threshold"], index=False)
    reliability.to_csv(paths["reliability"], index=False)
    by_station.to_csv(paths["station"], index=False)
    by_regime.to_csv(paths["regime"], index=False)
    pairwise.to_csv(paths["pairwise"], index=False)

    if not selections.empty:
        # Keep nested-selection evidence inside the predictions file via
        # selected_params_summary, but do not add an extra artifact beyond the
        # requested contract.
        pass

    write_report(
        paths["report"],
        result,
        inventory,
        feature_schema,
        reproduction,
        overall,
        thresholds,
        reliability,
        by_station,
        by_regime,
        pairwise,
        promotion,
        config,
    )
    write_status(paths["status"], config_path, result)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.3 high-tail challenger benchmark.")
    parser.add_argument("--config", default="configs/v11/systema_l1h3_high_tail_challenger.yaml")
    args = parser.parse_args()
    result = run_benchmark(resolve_path(args.config))
    print(f"[acceptance_status] {result.acceptance_status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[best_challenger] {result.best_challenger}")
    print(f"[comparison_best_f1] {result.comparison_best_f1}")
    print(f"[comparison_recall90] {result.comparison_recall90}")
    print(f"[station_regime_caveats] {result.station_regime_caveats}")
    print(f"[a_l2_recommendation] {result.a_l2_recommendation}")
    return 0 if result.acceptance_status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
