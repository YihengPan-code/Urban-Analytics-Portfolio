#!/usr/bin/env python
"""System A A-L2.0 station-context residual identifiability preflight.

Inputs:
    - configs/v11/systema_l2_identifiability_preflight.yaml
    - outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/
      residual_weather_merge_full_period.csv
    - outputs/v11_systema_l1_high_tail/probability_threshold_calibration/
      probability_predictions_oof.csv.gz
    - outputs/v11_systema_l1_high_tail/probability_threshold_calibration/
      threshold_by_station.csv
    - outputs/v11_systema_l1_high_tail/level1_integration/
      systema_l1h_station_regime_caveats.csv
    - outputs/v11_systema_l1_high_tail/high_tail_challenger/
      challenger_oof_predictions.csv.gz and station/threshold comparison CSVs
    - Optional station-context feature sources declared in the config.

Outputs:
    - station_context_input_inventory.csv
    - station_level_residual_summary.csv
    - station_level_probability_error_summary.csv
    - station_residual_stability_bootstrap.csv
    - station_context_feature_schema.csv
    - station_context_identifiability_matrix.csv
    - station_context_preflight_report.md
    - A_L2_0_STATUS.md

Saved metrics:
    - Required and optional input availability, row counts, column coverage,
      and station/cell key availability.
    - Station-level Level 1 score residuals, high-tail residuals, ge31/ge33
      event support, radiation-hot support, and shortwave support.
    - Station-level probability error, Brier, miss-rate, and false-alarm
      diagnostics for the current canonical P_ge31 companion, the A-L1H.3
      recall-first challenger, and the current companion recall90 point.
    - Bootstrap confidence intervals over station date/hour rows for residual,
      high-tail residual, probability error, and miss-rate signals.
    - Station-context feature availability/schema and descriptive low-n rank
      association checks where station coverage is sufficient.

Scope guard:
    This is an identifiability preflight only. It does not fit a final
    station-context residual ML model, use station_id as a predictive feature,
    create local 100 m WBGT, touch System B or SOLWEIG outputs, modify archive
    collector paths, stage, or commit files.
"""
from __future__ import annotations

import argparse
import gzip
import math
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import v11_l1h_probability_threshold_calibration as l1h2


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_OUTPUT_PREFIX = "outputs/v11_systema_l2_residual/identifiability_preflight"
PRIMARY_EVENT_ID = "ge31"
CURRENT_CASE_ID = "current_companion_best_f1"
CURRENT_RECALL90_CASE_ID = "current_companion_recall90"
CHALLENGER_CASE_ID = "recall_first_challenger_selected_policy"
STABLE_LABELS = {"stable_positive_bias", "stable_negative_bias"}


@dataclass(frozen=True)
class PreflightResult:
    """Headline result for the A-L2.0 identifiability preflight."""

    acceptance_status: str
    decision_status: str
    stable_residual_summary: str
    s142_s139_summary: str
    station_feature_availability: str
    a_l2_1_recommendation: str
    output_paths: list[Path]


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
    """Read the explicit A-L2.0 YAML config."""
    return l1h2.load_config(path)


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
    """Count CSV data rows, including gzip-compressed CSVs."""
    if not path.exists() or path.is_dir():
        return 0
    opener = gzip.open if path.suffix == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8", errors="replace", newline="") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except UnicodeDecodeError:
        return 0


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV using pandas with the lane's default low-memory policy."""
    return pd.read_csv(path, low_memory=False, **kwargs)


def fmt(value: object, digits: int = 3) -> str:
    """Format numbers for compact reports."""
    return l1h2.fmt(value, digits=digits)


def safe_div(num: float, den: float) -> float:
    """Divide with NaN for zero denominators."""
    return l1h2.safe_div(num, den)


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values for compact CSV cells."""
    return l1h2.semicolon(values)


def numeric(series: pd.Series) -> pd.Series:
    """Convert a Series to numeric values."""
    return pd.to_numeric(series, errors="coerce")


def bool_series(series: pd.Series) -> pd.Series:
    """Convert bool-like values to boolean values."""
    return l1h2.bool_series(series)


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 12) -> str:
    """Render a compact Markdown table."""
    return l1h2.markdown_table(df, columns, limit=limit)


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Return all expected A-L2.0 output paths."""
    output_dir = resolve_path(str(config["outputs"]["output_dir"]))
    return {
        "dir": output_dir,
        "inventory": output_dir / "station_context_input_inventory.csv",
        "residual_summary": output_dir / "station_level_residual_summary.csv",
        "probability_summary": output_dir / "station_level_probability_error_summary.csv",
        "bootstrap": output_dir / "station_residual_stability_bootstrap.csv",
        "feature_schema": output_dir / "station_context_feature_schema.csv",
        "identifiability": output_dir / "station_context_identifiability_matrix.csv",
        "report": output_dir / "station_context_preflight_report.md",
        "status": output_dir / "A_L2_0_STATUS.md",
    }


def assert_output_scope(paths: dict[str, Path]) -> None:
    """Ensure outputs stay in the explicit A-L2.0 directory."""
    output_dir = paths["dir"]
    if not rel(output_dir).startswith(EXPECTED_OUTPUT_PREFIX):
        raise ValueError(f"Refusing to write outside {EXPECTED_OUTPUT_PREFIX}: {rel(output_dir)}")


def sample_columns(path: Path, max_columns: int = 60) -> list[str]:
    """Read a CSV header and return a bounded column sample."""
    if not path.exists() or path.is_dir():
        return []
    try:
        columns = read_csv(path, nrows=0).columns.tolist()
    except Exception:
        return []
    if len(columns) <= max_columns:
        return [str(col) for col in columns]
    head = [str(col) for col in columns[:max_columns]]
    return [*head, f"...{len(columns) - max_columns}_more_columns"]


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Build required and optional station-context input inventory."""
    rows: list[dict[str, Any]] = []
    forbidden_tokens = [str(token).lower() for token in config["analysis"].get("forbidden_feature_tokens", [])]
    selected_roles = {
        "residual_weather_merge",
        "probability_predictions_oof",
        "threshold_operating_points",
        "threshold_by_station",
        "challenger_oof_predictions",
        "challenger_threshold_metrics",
        "challenger_by_station",
        "station_grid_mapping",
        "v09_station_pairs",
        "grid_v10_basic_morphology",
        "grid_v10_umep_features",
    }
    for role, raw_path in config["inputs"].items():
        path = resolve_path(str(raw_path))
        exists = path.exists()
        is_dir = path.is_dir()
        columns = sample_columns(path)
        lower_columns = [col.lower() for col in columns]
        forbidden_like = [
            col
            for col, lower in zip(columns, lower_columns)
            if any(token in lower for token in forbidden_tokens)
        ]
        rows.append(
            {
                "inventory_role": role,
                "path": rel(path),
                "exists": exists,
                "is_directory": is_dir,
                "file_size_bytes": path.stat().st_size if exists and not is_dir else np.nan,
                "rows_total": count_csv_rows(path),
                "column_count_sampled": 0 if is_dir else len(columns),
                "columns_present_sample": semicolon(columns),
                "has_station_id": "station_id" in columns,
                "has_cell_id": "cell_id" in columns,
                "has_timestamp_key": any(col in columns for col in ["timestamp", "timestamp_sgt", "time_sgt", "valid_time_sgt"]),
                "forbidden_like_column_sample_count": len(forbidden_like),
                "forbidden_like_column_sample": semicolon(forbidden_like[:20]),
                "selected_for_analysis": role in selected_roles,
                "source_class": source_class_for_role(role),
                "notes": inventory_notes(role, exists, columns),
            }
        )
    return pd.DataFrame(rows)


def source_class_for_role(role: str) -> str:
    """Classify an inventory role for the feature inventory."""
    if role in {"station_grid_mapping", "v09_station_pairs", "v09_station_weather", "v11_live_chunk"}:
        return "station_metadata_or_pairing"
    if role.startswith("grid_v10"):
        return "morphology_proxy"
    if role == "data_stations_dir":
        return "unavailable_station_metadata_directory"
    return "diagnostic_input"


def inventory_notes(role: str, exists: bool, columns: list[str]) -> str:
    """Return compact source-specific inventory notes."""
    if role == "data_stations_dir" and not exists:
        return "No dedicated station metadata directory found."
    if role.startswith("grid_v10"):
        return "Grid morphology proxy; may be considered only through explicit station-to-cell mapping."
    if role == "v11_live_chunk":
        return "Compact live chunk source; inventoried but not used as a modelling input."
    if not exists:
        return "Missing configured source."
    if "station_id" in columns:
        return "Station key available."
    if "cell_id" in columns:
        return "Cell key available."
    return ""


def add_context_columns(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Normalize timestamp, hour, event, and regime support columns."""
    schema = config["schema"]
    out = df.copy()
    station_col = str(schema["station_col"])
    timestamp_col = str(schema["timestamp_col"])
    date_col = str(schema["date_col"])
    hour_col = str(schema["hour_col"])
    target_col = str(schema["target_col"])
    score_col = str(schema["model_score_col"])
    out[station_col] = out[station_col].astype(str)
    out[target_col] = numeric(out[target_col])
    out[score_col] = numeric(out[score_col])
    out["timestamp_dt"] = pd.to_datetime(out[timestamp_col], errors="coerce")
    if date_col not in out.columns:
        out[date_col] = out["timestamp_dt"].dt.date.astype(str)
    if hour_col not in out.columns or out[hour_col].isna().all():
        out[hour_col] = out["timestamp_dt"].dt.hour
    out[hour_col] = numeric(out[hour_col])
    out["date_hour_key"] = out["timestamp_dt"].dt.strftime("%Y-%m-%d %H:00")
    out["date_hour_key"] = out["date_hour_key"].fillna(out[date_col].astype(str) + "_" + out[hour_col].astype(str))
    out[str(schema["event_ge31_col"])] = out[target_col] >= float(config["analysis"]["event_threshold_c"])
    out[str(schema["event_ge33_col"])] = out[target_col] >= float(config["analysis"]["exploratory_event_threshold_c"])
    out[str(schema["residual_col"])] = out[target_col] - out[score_col]
    radiation_label = str(config["analysis"]["radiation_hot_label"])
    very_high_label = str(config["analysis"]["very_high_label"])
    out["radiation_hot_flag"] = (
        out.get("combined_radiation_hot_regime", pd.Series("", index=out.index)).astype(str) == radiation_label
    )
    out["shortwave_very_high_flag"] = (
        out.get("shortwave_bin", pd.Series("", index=out.index)).astype(str) == very_high_label
    )
    out["shortwave_3h_very_high_flag"] = (
        out.get("shortwave_3h_mean_bin", pd.Series("", index=out.index)).astype(str) == very_high_label
    )
    return add_context_adjustment(out, str(schema["residual_col"]), "context_adjusted_score_residual_c", config)


def context_keys(frame: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    """Return configured context columns present in a frame."""
    keys = [str(col) for col in config["analysis"].get("context_columns", []) if col in frame.columns]
    if not keys:
        return []
    return keys


def add_context_adjustment(df: pd.DataFrame, value_col: str, output_col: str, config: dict[str, Any]) -> pd.DataFrame:
    """Subtract all-station means within weather-regime/hour context bins."""
    out = df.copy()
    keys = context_keys(out, config)
    if not keys or value_col not in out.columns:
        out[output_col] = np.nan
        return out
    work_keys: list[str] = []
    for key in keys:
        helper = f"__ctx_{key}"
        out[helper] = out[key].astype(str).fillna("__missing__")
        work_keys.append(helper)
    context_mean = out.groupby(work_keys, dropna=False)[value_col].transform("mean")
    out[output_col] = numeric(out[value_col]) - context_mean
    return out.drop(columns=work_keys)


def prepare_residual_frame(config: dict[str, Any]) -> pd.DataFrame:
    """Load and normalize current Level 1 residual/weather rows."""
    schema = config["schema"]
    path = resolve_path(str(config["inputs"]["residual_weather_merge"]))
    if not path.exists():
        raise FileNotFoundError(rel(path))
    df = read_csv(path)
    model_col = str(schema["model_name_col"])
    cv_col = str(schema["cv_scheme_col"])
    current_model = str(config["baselines"]["current_companion"]["model_name"])
    primary_cv = str(schema["primary_cv_scheme"])
    selected = df[
        df[model_col].astype(str).eq(current_model)
        & df[cv_col].astype(str).eq(primary_cv)
    ].copy()
    required = [
        str(schema["station_col"]),
        str(schema["timestamp_col"]),
        str(schema["target_col"]),
        str(schema["model_score_col"]),
    ]
    selected = selected.dropna(subset=[col for col in required if col in selected.columns])
    selected = add_context_columns(selected, config)
    return selected.sort_values([str(schema["station_col"]), str(schema["timestamp_col"])]).reset_index(drop=True)


def threshold_from_operating_points(
    config: dict[str, Any],
    operating_point: str,
    source_kind: str,
) -> float:
    """Read an aggregate probability threshold for a current or challenger case."""
    if source_kind == "current":
        path = resolve_path(str(config["inputs"]["threshold_operating_points"]))
        if not path.exists():
            return float(config["baselines"]["current_companion"]["fallback_best_f1_threshold"])
        df = read_csv(path)
        current = config["baselines"]["current_companion"]
        match = df[
            df["model_name"].astype(str).eq(str(current["model_name"]))
            & df["output_id"].astype(str).eq(str(current["calibrator_id"]))
            & df["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
            & df["operating_point"].astype(str).eq(operating_point)
        ]
    else:
        path = resolve_path(str(config["inputs"]["challenger_threshold_metrics"]))
        if not path.exists():
            return np.nan
        df = read_csv(path)
        challenger = config["baselines"]["recall_first_challenger"]
        match = df[
            df["candidate_id"].astype(str).eq(str(challenger["candidate_id"]))
            & df["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
            & df["operating_point"].astype(str).eq(operating_point)
        ]
    if match.empty and operating_point == "selected_candidate_policy":
        return threshold_from_operating_points(config, "best_F1", source_kind)
    if match.empty:
        return np.nan
    return float(numeric(match["threshold"]).dropna().iloc[0]) if numeric(match["threshold"]).notna().any() else np.nan


def load_current_probability_source(config: dict[str, Any]) -> pd.DataFrame:
    """Load the A-L1H.2 current companion P_ge31 OOF probabilities."""
    path = resolve_path(str(config["inputs"]["probability_predictions_oof"]))
    if not path.exists():
        return pd.DataFrame()
    df = read_csv(path)
    current = config["baselines"]["current_companion"]
    return df[
        df["model_name"].astype(str).eq(str(current["model_name"]))
        & df["calibrator_id"].astype(str).eq(str(current["calibrator_id"]))
        & df["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
    ].copy()


def load_challenger_probability_source(config: dict[str, Any]) -> pd.DataFrame:
    """Load the A-L1H.3 recall-first challenger OOF probabilities."""
    path = resolve_path(str(config["inputs"]["challenger_oof_predictions"]))
    if not path.exists():
        return pd.DataFrame()
    df = read_csv(path)
    challenger = config["baselines"]["recall_first_challenger"]
    return df[
        df["candidate_id"].astype(str).eq(str(challenger["candidate_id"]))
        & df["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
        & df["output_kind"].astype(str).eq("probability")
    ].copy()


def normalize_probability_case(
    df: pd.DataFrame,
    config: dict[str, Any],
    case_id: str,
    case_label: str,
    source_kind: str,
    operating_point: str,
    threshold: float,
) -> pd.DataFrame:
    """Normalize one probability case for station-level error summaries."""
    if df.empty:
        return pd.DataFrame()
    schema = config["schema"]
    out = df.copy()
    station_col = str(schema["station_col"])
    timestamp_col = str(schema["timestamp_col"])
    date_col = str(schema["date_col"])
    hour_col = str(schema["hour_col"])
    target_col = str(schema["target_col"])
    score_col = str(schema["model_score_col"])
    out[station_col] = out[station_col].astype(str)
    out[target_col] = numeric(out[target_col])
    out[score_col] = numeric(out[score_col])
    out["probability"] = numeric(out["probability"])
    out["event_observed"] = bool_series(out["event_observed"]).astype(int)
    if "obs_ge33" in out.columns:
        out["obs_ge33"] = bool_series(out["obs_ge33"])
    else:
        out["obs_ge33"] = out[target_col] >= float(config["analysis"]["exploratory_event_threshold_c"])
    out["timestamp_dt"] = pd.to_datetime(out[timestamp_col], errors="coerce")
    if date_col not in out.columns:
        out[date_col] = out["timestamp_dt"].dt.date.astype(str)
    if hour_col not in out.columns or out[hour_col].isna().all():
        out[hour_col] = out["timestamp_dt"].dt.hour
    out[hour_col] = numeric(out[hour_col])
    out["date_hour_key"] = out["timestamp_dt"].dt.strftime("%Y-%m-%d %H:00")
    out["date_hour_key"] = out["date_hour_key"].fillna(out[date_col].astype(str) + "_" + out[hour_col].astype(str))
    if "radiation_hot_flag" not in out.columns:
        out["radiation_hot_flag"] = (
            out.get("combined_radiation_hot_regime", pd.Series("", index=out.index)).astype(str)
            == str(config["analysis"]["radiation_hot_label"])
        )
    else:
        out["radiation_hot_flag"] = bool_series(out["radiation_hot_flag"])
    if "shortwave_very_high_flag" not in out.columns:
        out["shortwave_very_high_flag"] = (
            out.get("shortwave_bin", pd.Series("", index=out.index)).astype(str)
            == str(config["analysis"]["very_high_label"])
        )
    else:
        out["shortwave_very_high_flag"] = bool_series(out["shortwave_very_high_flag"])
    if "shortwave_3h_very_high_flag" not in out.columns:
        out["shortwave_3h_very_high_flag"] = (
            out.get("shortwave_3h_mean_bin", pd.Series("", index=out.index)).astype(str)
            == str(config["analysis"]["very_high_label"])
        )
    else:
        out["shortwave_3h_very_high_flag"] = bool_series(out["shortwave_3h_very_high_flag"])
    out["probability_case_id"] = case_id
    out["probability_case_label"] = case_label
    out["probability_source_kind"] = source_kind
    out["policy_operating_point"] = operating_point
    out["policy_threshold"] = threshold
    out["probability_error_obs_minus_p"] = out["event_observed"].astype(float) - out["probability"]
    out["probability_bias_pred_minus_obs"] = -out["probability_error_obs_minus_p"]
    out["brier_component"] = (out["probability"] - out["event_observed"].astype(float)) ** 2
    out["event_predicted"] = out["probability"] >= threshold if np.isfinite(threshold) else False
    out = add_context_adjustment(
        out,
        "probability_error_obs_minus_p",
        "context_adjusted_probability_error_obs_minus_p",
        config,
    )
    keep = [
        "probability_case_id",
        "probability_case_label",
        "probability_source_kind",
        "policy_operating_point",
        "policy_threshold",
        "row_id",
        station_col,
        timestamp_col,
        date_col,
        hour_col,
        target_col,
        score_col,
        "event_observed",
        "obs_ge33",
        "probability",
        "probability_error_obs_minus_p",
        "probability_bias_pred_minus_obs",
        "context_adjusted_probability_error_obs_minus_p",
        "brier_component",
        "event_predicted",
        "radiation_hot_flag",
        "shortwave_very_high_flag",
        "shortwave_3h_very_high_flag",
        "combined_radiation_hot_regime",
        "shortwave_bin",
        "shortwave_3h_mean_bin",
        "date_hour_key",
    ]
    return out[[col for col in keep if col in out.columns]].copy()


def prepare_probability_cases(config: dict[str, Any]) -> pd.DataFrame:
    """Build all requested current/challenger probability comparison cases."""
    current_source = load_current_probability_source(config)
    challenger_source = load_challenger_probability_source(config)
    cases: list[pd.DataFrame] = []
    current_best_op = str(config["baselines"]["current_companion"]["selected_operating_point"])
    current_best_threshold = threshold_from_operating_points(config, current_best_op, "current")
    cases.append(
        normalize_probability_case(
            current_source,
            config,
            CURRENT_CASE_ID,
            "M4_inertia_ridge + isotonic_score_only best-F1 policy",
            "current_companion",
            current_best_op,
            current_best_threshold,
        )
    )
    recall_op = str(config["baselines"]["current_companion"]["recall90_operating_point"])
    cases.append(
        normalize_probability_case(
            current_source,
            config,
            CURRENT_RECALL90_CASE_ID,
            "M4_inertia_ridge + isotonic_score_only recall90 policy",
            "current_companion",
            recall_op,
            threshold_from_operating_points(config, recall_op, "current"),
        )
    )
    challenger_op = str(config["baselines"]["recall_first_challenger"]["selected_operating_point"])
    cases.append(
        normalize_probability_case(
            challenger_source,
            config,
            CHALLENGER_CASE_ID,
            "cost_sensitive_logistic_score_weather selected policy",
            "recall_first_challenger",
            challenger_op,
            threshold_from_operating_points(config, challenger_op, "challenger"),
        )
    )
    parts = [case for case in cases if not case.empty]
    combined = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    return apply_station_policy_thresholds(combined, config)


def apply_station_policy_thresholds(probability_cases: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Use upstream per-station policy thresholds for row-level decisions when available."""
    if probability_cases.empty:
        return probability_cases
    metrics = source_station_metrics(config)
    if metrics.empty or "source_policy_threshold_mean" not in metrics.columns:
        probability_cases["aggregate_policy_threshold"] = probability_cases["policy_threshold"]
        probability_cases["station_policy_threshold"] = probability_cases["policy_threshold"]
        return probability_cases
    thresholds = metrics[["probability_case_id", "station_id", "source_policy_threshold_mean"]].copy()
    out = probability_cases.merge(thresholds, on=["probability_case_id", "station_id"], how="left")
    out["aggregate_policy_threshold"] = out["policy_threshold"]
    out["station_policy_threshold"] = numeric(out["source_policy_threshold_mean"]).combine_first(numeric(out["policy_threshold"]))
    out["policy_threshold"] = out["station_policy_threshold"]
    out["event_predicted"] = numeric(out["probability"]) >= numeric(out["station_policy_threshold"])
    return out.drop(columns=["source_policy_threshold_mean"])


def confusion_from_arrays(y: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    """Compute threshold decision metrics from binary arrays."""
    y = y.astype(int)
    p = pred.astype(int)
    tp = int(((p == 1) & (y == 1)).sum())
    fp = int(((p == 1) & (y == 0)).sum())
    tn = int(((p == 0) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum())
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    return {
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": precision,
        "recall": recall,
        "F1": safe_div(2.0 * precision * recall, precision + recall) if np.isfinite(precision) and np.isfinite(recall) else np.nan,
        "CSI": safe_div(tp, tp + fp + fn),
        "miss_rate": safe_div(fn, tp + fn),
        "false_alarm_ratio": safe_div(fp, tp + fp),
        "false_alarm_rate": safe_div(fp, fp + tn),
    }


def summarize_station_residuals(residual: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build station-level score residual and event-support summary."""
    schema = config["schema"]
    station_col = str(schema["station_col"])
    event_col = str(schema["event_ge31_col"])
    ge33_col = str(schema["event_ge33_col"])
    residual_col = str(schema["residual_col"])
    low_n = int(config["analysis"]["low_support_n_rows"])
    low_events = int(config["analysis"]["low_support_n_events"])
    rows: list[dict[str, Any]] = []
    for station_id, group in residual.groupby(station_col, dropna=False):
        event_mask = bool_series(group[event_col])
        ge33_mask = bool_series(group[ge33_col])
        high_tail = group.loc[event_mask, residual_col]
        rows.append(
            {
                "station_id": station_id,
                "n_rows": int(len(group)),
                "n_ge31": int(event_mask.sum()),
                "n_ge33_exploratory": int(ge33_mask.sum()),
                "event_rate_ge31": safe_div(int(event_mask.sum()), len(group)),
                "mean_score_residual_c": numeric(group[residual_col]).mean(),
                "median_score_residual_c": numeric(group[residual_col]).median(),
                "std_score_residual_c": numeric(group[residual_col]).std(ddof=0),
                "p10_score_residual_c": numeric(group[residual_col]).quantile(0.10),
                "p90_score_residual_c": numeric(group[residual_col]).quantile(0.90),
                "mean_context_adjusted_score_residual_c": numeric(group["context_adjusted_score_residual_c"]).mean(),
                "mean_high_tail_residual_c": numeric(high_tail).mean() if len(high_tail) else np.nan,
                "median_high_tail_residual_c": numeric(high_tail).median() if len(high_tail) else np.nan,
                "mean_context_adjusted_high_tail_residual_c": numeric(group.loc[event_mask, "context_adjusted_score_residual_c"]).mean() if event_mask.any() else np.nan,
                "radiation_hot_support_count": int(bool_series(group["radiation_hot_flag"]).sum()) if "radiation_hot_flag" in group else 0,
                "very_high_shortwave_support_count": int(bool_series(group["shortwave_very_high_flag"]).sum()) if "shortwave_very_high_flag" in group else 0,
                "very_high_shortwave_3h_support_count": int(bool_series(group["shortwave_3h_very_high_flag"]).sum()) if "shortwave_3h_very_high_flag" in group else 0,
                "unique_date_count": int(group[str(schema["date_col"])].nunique()) if str(schema["date_col"]) in group else np.nan,
                "unique_hour_count": int(group[str(schema["hour_col"])].nunique()) if str(schema["hour_col"]) in group else np.nan,
                "low_support_warning_flag": bool(len(group) < low_n or int(event_mask.sum()) < low_events),
                "low_support_reason": low_support_reason(len(group), int(event_mask.sum()), low_n, low_events),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("mean_context_adjusted_score_residual_c", ascending=False, na_position="last")


def low_support_reason(n_rows: int, n_events: int, low_n: int, low_events: int) -> str:
    """Return a compact support warning reason."""
    reasons: list[str] = []
    if n_rows < low_n:
        reasons.append(f"n_rows<{low_n}")
    if n_events < low_events:
        reasons.append(f"n_ge31<{low_events}")
    return ";".join(reasons)


def source_station_metrics(config: dict[str, Any]) -> pd.DataFrame:
    """Read exact station policy metrics from A-L1H.2 and A-L1H.3 when available."""
    rows: list[pd.DataFrame] = []
    threshold_by_station_path = resolve_path(str(config["inputs"]["threshold_by_station"]))
    if threshold_by_station_path.exists():
        current = config["baselines"]["current_companion"]
        station = read_csv(threshold_by_station_path)
        for case_id, op in [
            (CURRENT_CASE_ID, str(current["selected_operating_point"])),
            (CURRENT_RECALL90_CASE_ID, str(current["recall90_operating_point"])),
        ]:
            match = station[
                station["model_name"].astype(str).eq(str(current["model_name"]))
                & station["output_id"].astype(str).eq(str(current["calibrator_id"]))
                & station["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
                & station["operating_point"].astype(str).eq(op)
            ].copy()
            if match.empty and op == "selected_candidate_policy":
                match = station[
                    station["model_name"].astype(str).eq(str(current["model_name"]))
                    & station["output_id"].astype(str).eq(str(current["calibrator_id"]))
                    & station["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
                    & station["operating_point"].astype(str).eq("best_F1")
                ].copy()
            if not match.empty:
                match["probability_case_id"] = case_id
                rows.append(match)
    challenger_path = resolve_path(str(config["inputs"]["challenger_by_station"]))
    if challenger_path.exists():
        challenger = config["baselines"]["recall_first_challenger"]
        station = read_csv(challenger_path)
        op = str(challenger["selected_operating_point"])
        match = station[
            station["candidate_id"].astype(str).eq(str(challenger["candidate_id"]))
            & station["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
            & station["operating_point"].astype(str).eq(op)
        ].copy()
        if match.empty and op == "selected_candidate_policy":
            match = station[
                station["candidate_id"].astype(str).eq(str(challenger["candidate_id"]))
                & station["event_target"].astype(str).eq(PRIMARY_EVENT_ID)
                & station["operating_point"].astype(str).eq("best_F1")
            ].copy()
        if not match.empty:
            match["probability_case_id"] = CHALLENGER_CASE_ID
            rows.append(match)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    keep = [
        "probability_case_id",
        "station_id",
        "threshold_mean",
        "TP",
        "FP",
        "FN",
        "TN",
        "precision",
        "recall",
        "F1",
        "CSI",
        "false_alarm_ratio",
        "miss_rate",
    ]
    out = out[[col for col in keep if col in out.columns]].copy()
    return out.rename(columns={col: f"source_policy_{col}" for col in out.columns if col not in {"probability_case_id", "station_id"}})


def summarize_station_probability_errors(probability_cases: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build station-level probability-error summaries for all requested policies."""
    if probability_cases.empty:
        return pd.DataFrame()
    schema = config["schema"]
    station_col = str(schema["station_col"])
    low_n = int(config["analysis"]["low_support_n_rows"])
    low_events = int(config["analysis"]["low_support_n_events"])
    rows: list[dict[str, Any]] = []
    keys = ["probability_case_id", "probability_case_label", "probability_source_kind", "policy_operating_point", station_col]
    for key, group in probability_cases.groupby(keys, dropna=False):
        y = group["event_observed"].to_numpy(dtype=int)
        pred = bool_series(group["event_predicted"]).to_numpy(dtype=bool)
        conf = confusion_from_arrays(y, pred)
        ge33_count = int(bool_series(group["obs_ge33"]).sum()) if "obs_ge33" in group else np.nan
        rows.append(
            {
                **dict(zip(["probability_case_id", "probability_case_label", "probability_source_kind", "policy_operating_point", "station_id"], key)),
                "policy_threshold": float(numeric(group["policy_threshold"]).dropna().iloc[0]) if numeric(group["policy_threshold"]).notna().any() else np.nan,
                "n_rows": int(len(group)),
                "n_ge31": int(y.sum()),
                "n_ge33_exploratory": ge33_count,
                "observed_event_rate": safe_div(int(y.sum()), len(group)),
                "mean_probability": numeric(group["probability"]).mean(),
                "p_ge31_Brier": numeric(group["brier_component"]).mean(),
                "mean_probability_error_obs_minus_p": numeric(group["probability_error_obs_minus_p"]).mean(),
                "probability_bias_pred_minus_obs": numeric(group["probability_bias_pred_minus_obs"]).mean(),
                "mean_context_adjusted_probability_error_obs_minus_p": numeric(group["context_adjusted_probability_error_obs_minus_p"]).mean(),
                "radiation_hot_support_count": int(bool_series(group["radiation_hot_flag"]).sum()) if "radiation_hot_flag" in group else 0,
                "very_high_shortwave_support_count": int(bool_series(group["shortwave_very_high_flag"]).sum()) if "shortwave_very_high_flag" in group else 0,
                "very_high_shortwave_3h_support_count": int(bool_series(group["shortwave_3h_very_high_flag"]).sum()) if "shortwave_3h_very_high_flag" in group else 0,
                "computed_TP": conf["TP"],
                "computed_FP": conf["FP"],
                "computed_FN": conf["FN"],
                "computed_TN": conf["TN"],
                "computed_precision": conf["precision"],
                "computed_recall": conf["recall"],
                "computed_false_alarm_ratio": conf["false_alarm_ratio"],
                "computed_false_alarm_rate": conf["false_alarm_rate"],
                "computed_miss_rate": conf["miss_rate"],
                "low_support_warning_flag": bool(len(group) < low_n or int(y.sum()) < low_events),
                "low_support_reason": low_support_reason(len(group), int(y.sum()), low_n, low_events),
            }
        )
    out = pd.DataFrame(rows)
    source_metrics = source_station_metrics(config)
    if not source_metrics.empty:
        out = out.merge(source_metrics, on=["probability_case_id", "station_id"], how="left")
    for metric in ["miss_rate", "false_alarm_ratio", "precision", "recall", "TP", "FP", "FN", "TN"]:
        source_col = f"source_policy_{metric}"
        computed_col = f"computed_{metric}"
        final_col = f"{metric}_at_policy" if metric in {"miss_rate", "false_alarm_ratio", "precision", "recall"} else f"{metric}_at_policy"
        if source_col in out.columns:
            out[final_col] = out[source_col].combine_first(out.get(computed_col, pd.Series(np.nan, index=out.index)))
        elif computed_col in out.columns:
            out[final_col] = out[computed_col]
    if "false_alarm_ratio_at_policy" in out.columns:
        out["false_alarm_rate_note"] = "false_alarm_ratio=FP/(TP+FP); computed_false_alarm_rate=FP/(FP+TN)"
    return out.sort_values(["probability_case_id", "mean_context_adjusted_probability_error_obs_minus_p"], ascending=[True, False], na_position="last")


def bootstrap_mean(values: pd.Series, groups: pd.Series, n_iter: int, seed: int) -> tuple[float, float, float, int]:
    """Bootstrap a grouped mean over station date/hour rows."""
    frame = pd.DataFrame({"value": numeric(values), "group": groups.astype(str)}).dropna(subset=["value", "group"])
    if frame.empty:
        return np.nan, np.nan, np.nan, 0
    grouped = frame.groupby("group", dropna=False)["value"].mean().to_numpy(dtype=float)
    estimate = float(np.mean(grouped)) if len(grouped) else np.nan
    if len(grouped) < 2:
        return estimate, np.nan, np.nan, 0
    rng = np.random.default_rng(seed)
    draws = np.empty(n_iter, dtype=float)
    for idx in range(n_iter):
        sample = rng.choice(grouped, size=len(grouped), replace=True)
        draws[idx] = np.mean(sample)
    return estimate, float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975)), n_iter


def bootstrap_miss_rate(group: pd.DataFrame, n_iter: int, seed: int) -> tuple[float, float, float, int]:
    """Bootstrap miss-rate over station date/hour rows."""
    if group.empty:
        return np.nan, np.nan, np.nan, 0
    work = group.copy()
    work["event_observed"] = work["event_observed"].astype(int)
    work["event_predicted"] = bool_series(work["event_predicted"]).astype(int)
    work["fn"] = ((work["event_observed"] == 1) & (work["event_predicted"] == 0)).astype(int)
    hourly = work.groupby("date_hour_key", dropna=False).agg(fn=("fn", "sum"), events=("event_observed", "sum")).reset_index()
    total_events = float(hourly["events"].sum())
    estimate = safe_div(float(hourly["fn"].sum()), total_events)
    if len(hourly) < 2 or total_events <= 0:
        return estimate, np.nan, np.nan, 0
    rng = np.random.default_rng(seed)
    draws: list[float] = []
    ids = np.arange(len(hourly))
    fn = hourly["fn"].to_numpy(dtype=float)
    events = hourly["events"].to_numpy(dtype=float)
    for _ in range(n_iter):
        sample = rng.choice(ids, size=len(ids), replace=True)
        den = float(events[sample].sum())
        if den > 0:
            draws.append(float(fn[sample].sum() / den))
    if not draws:
        return estimate, np.nan, np.nan, 0
    arr = np.asarray(draws, dtype=float)
    return estimate, float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)), len(draws)


def stability_label(
    estimate: float,
    ci_low: float,
    ci_high: float,
    threshold: float,
    low_support: bool,
    one_sided_positive: bool = False,
) -> str:
    """Classify a bootstrap confidence interval into the lane labels."""
    if low_support or not np.isfinite(estimate) or not np.isfinite(ci_low) or not np.isfinite(ci_high):
        return "unstable_low_support"
    if one_sided_positive:
        return "stable_positive_bias" if ci_low > threshold else "no_station_signal"
    if ci_low > threshold:
        return "stable_positive_bias"
    if ci_high < -threshold:
        return "stable_negative_bias"
    return "no_station_signal"


def make_stability_rows(
    residual: pd.DataFrame,
    probability_cases: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Create bootstrap stability rows for residual and probability signals."""
    schema = config["schema"]
    station_col = str(schema["station_col"])
    event_col = str(schema["event_ge31_col"])
    residual_col = str(schema["residual_col"])
    n_iter = int(config["analysis"]["bootstrap_iterations"])
    seed = int(config["analysis"]["random_seed"])
    low_n = int(config["analysis"]["low_support_n_rows"])
    low_events = int(config["analysis"]["low_support_n_events"])
    residual_threshold = float(config["analysis"]["residual_signal_threshold_c"])
    probability_threshold = float(config["analysis"]["probability_signal_threshold"])
    miss_threshold = float(config["analysis"]["miss_rate_signal_threshold"])
    rows: list[dict[str, Any]] = []
    for station_id, group in residual.groupby(station_col, dropna=False):
        event_mask = bool_series(group[event_col])
        low_support_all = len(group) < low_n
        low_support_tail = len(group) < low_n or int(event_mask.sum()) < low_events
        for metric_name, value_col, metric_group, threshold, support_flag, subframe in [
            ("mean_score_residual_c", residual_col, "score_residual", residual_threshold, low_support_all, group),
            (
                "mean_context_adjusted_score_residual_c",
                "context_adjusted_score_residual_c",
                "score_residual_context_adjusted",
                residual_threshold,
                low_support_all,
                group,
            ),
            (
                "mean_high_tail_residual_c",
                residual_col,
                "high_tail_residual",
                residual_threshold,
                low_support_tail,
                group.loc[event_mask].copy(),
            ),
            (
                "mean_context_adjusted_high_tail_residual_c",
                "context_adjusted_score_residual_c",
                "high_tail_residual_context_adjusted",
                residual_threshold,
                low_support_tail,
                group.loc[event_mask].copy(),
            ),
        ]:
            estimate, ci_low, ci_high, boot_n = bootstrap_mean(
                subframe[value_col],
                subframe["date_hour_key"],
                n_iter,
                seed + stable_seed(station_id, metric_name),
            )
            rows.append(
                {
                    "station_id": station_id,
                    "metric_group": metric_group,
                    "metric_name": metric_name,
                    "probability_case_id": "",
                    "n_rows": int(len(group)),
                    "n_ge31": int(event_mask.sum()),
                    "estimate": estimate,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "bootstrap_iterations": boot_n,
                    "stability_label": stability_label(estimate, ci_low, ci_high, threshold, support_flag),
                    "low_support_warning_flag": support_flag,
                }
            )
    if not probability_cases.empty:
        for (case_id, station_id), group in probability_cases.groupby(["probability_case_id", station_col], dropna=False):
            events = int(group["event_observed"].sum())
            low_support = len(group) < low_n or events < low_events
            for metric_name, value_col in [
                ("mean_probability_error_obs_minus_p", "probability_error_obs_minus_p"),
                ("mean_context_adjusted_probability_error_obs_minus_p", "context_adjusted_probability_error_obs_minus_p"),
            ]:
                estimate, ci_low, ci_high, boot_n = bootstrap_mean(
                    group[value_col],
                    group["date_hour_key"],
                    n_iter,
                    seed + stable_seed(station_id, case_id, metric_name),
                )
                rows.append(
                    {
                        "station_id": station_id,
                        "metric_group": "probability_error",
                        "metric_name": metric_name,
                        "probability_case_id": case_id,
                        "n_rows": int(len(group)),
                        "n_ge31": events,
                        "estimate": estimate,
                        "ci_low": ci_low,
                        "ci_high": ci_high,
                        "bootstrap_iterations": boot_n,
                        "stability_label": stability_label(estimate, ci_low, ci_high, probability_threshold, low_support),
                        "low_support_warning_flag": low_support,
                    }
                )
            estimate, ci_low, ci_high, boot_n = bootstrap_miss_rate(
                group,
                n_iter,
                seed + stable_seed(station_id, case_id, "miss_rate"),
            )
            rows.append(
                {
                    "station_id": station_id,
                    "metric_group": "miss_rate",
                    "metric_name": "miss_rate_at_policy",
                    "probability_case_id": case_id,
                    "n_rows": int(len(group)),
                    "n_ge31": events,
                    "estimate": estimate,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "bootstrap_iterations": boot_n,
                    "stability_label": stability_label(estimate, ci_low, ci_high, miss_threshold, low_support, one_sided_positive=True),
                    "low_support_warning_flag": low_support,
                }
            )
    return pd.DataFrame(rows)


def stable_seed(*parts: object) -> int:
    """Create a deterministic small seed offset from text parts."""
    text = "|".join(str(part) for part in parts)
    return sum((idx + 1) * ord(char) for idx, char in enumerate(text)) % 1_000_003


def first_nonnull(series: pd.Series) -> Any:
    """Return the first non-null value from a Series."""
    nonnull = series.dropna()
    return nonnull.iloc[0] if len(nonnull) else np.nan


def station_static_from_csv(path: Path, station_col: str, columns: list[str]) -> pd.DataFrame:
    """Read station-level static columns by taking first non-null values."""
    if not path.exists():
        return pd.DataFrame()
    header = read_csv(path, nrows=0).columns.tolist()
    keep = [station_col, *[col for col in columns if col in header]]
    if station_col not in header or len(keep) <= 1:
        return pd.DataFrame()
    df = read_csv(path, usecols=keep)
    if df.empty:
        return pd.DataFrame()
    return df.groupby(station_col, dropna=False).agg(first_nonnull).reset_index()


def build_station_feature_frame(
    residual: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a station-context feature frame and schema without fitting a model."""
    schema = config["schema"]
    station_col = str(schema["station_col"])
    station_ids = pd.DataFrame({station_col: sorted(residual[station_col].dropna().astype(str).unique())})
    feature_frame = station_ids.copy()
    schema_rows: list[dict[str, Any]] = []

    def merge_source(path_key: str, columns: list[str], feature_class: str, prefix: str = "") -> None:
        nonlocal feature_frame, schema_rows
        path = resolve_path(str(config["inputs"][path_key]))
        source = station_static_from_csv(path, station_col, columns)
        if source.empty:
            for col in columns:
                schema_rows.append(feature_schema_row(col, path_key, rel(path), feature_class, False, False, "source_missing_or_column_unavailable"))
            return
        rename: dict[str, str] = {}
        for col in source.columns:
            if col != station_col:
                rename[col] = f"{prefix}{col}" if prefix else col
        source = source.rename(columns=rename)
        feature_frame = feature_frame.merge(source, on=station_col, how="left")
        for original, final in rename.items():
            schema_rows.append(
                feature_schema_row(
                    final,
                    path_key,
                    rel(path),
                    feature_class,
                    True,
                    feature_allowed(final, feature_class, config),
                    feature_leakage_note(final, feature_class, config),
                    source_column=original,
                    n_stations_available=int(source[final].notna().sum()),
                )
            )

    merge_source("v09_station_pairs", config["analysis"]["station_metadata_columns"], "station_metadata")
    merge_source("v09_station_pairs", config["analysis"]["forcing_pairing_columns"], "forcing_pairing_metadata")
    merge_source("v09_station_pairs", config["analysis"]["station_nearest_morphology_columns"], "morphology_proxy")
    merge_source("station_grid_mapping", config["analysis"]["station_metadata_columns"], "station_metadata", prefix="pairing_")
    merge_source("station_grid_mapping", config["analysis"]["forcing_pairing_columns"], "forcing_pairing_metadata", prefix="pairing_")

    feature_frame, grid_schema = merge_grid_morphology(feature_frame, config)
    schema_rows.extend(grid_schema)
    schema_rows.extend(forbidden_and_unavailable_schema_rows(config))

    feature_schema = pd.DataFrame(schema_rows)
    if not feature_schema.empty and "n_stations_available" not in feature_schema.columns:
        feature_schema["n_stations_available"] = np.nan
    if not feature_schema.empty:
        feature_schema["n_station_universe"] = int(len(station_ids))
        feature_schema["station_coverage_rate"] = numeric(feature_schema["n_stations_available"]) / max(len(station_ids), 1)
    return feature_frame, feature_schema


def feature_schema_row(
    feature_name: str,
    source_role: str,
    source_path: str,
    feature_class: str,
    available: bool,
    allowed: bool,
    leakage_check: str,
    source_column: str | None = None,
    n_stations_available: int | float = np.nan,
) -> dict[str, Any]:
    """Create one station-context feature schema row."""
    return {
        "feature_name": feature_name,
        "source_column": source_column or feature_name,
        "source_role": source_role,
        "source_path": source_path,
        "feature_class": feature_class,
        "available": available,
        "allowed_for_future_preflight_model": allowed,
        "station_level_static": feature_class in {"station_metadata", "forcing_pairing_metadata", "morphology_proxy"},
        "explicit_station_mapping": feature_class != "morphology_proxy" or "station_nearest" in feature_name or "grid_v10_" in feature_name,
        "n_stations_available": n_stations_available,
        "leakage_check": leakage_check,
        "notes": feature_notes(feature_class),
    }


def feature_allowed(feature_name: str, feature_class: str, config: dict[str, Any]) -> bool:
    """Return whether a feature class/name is allowed for a future scoped preflight."""
    if feature_class in {"forbidden_leakage", "unavailable"}:
        return False
    lower = feature_name.lower()
    tokens = [str(token).lower() for token in config["analysis"].get("forbidden_feature_tokens", [])]
    if any(token in lower for token in tokens):
        return False
    return feature_name != "station_id"


def feature_leakage_note(feature_name: str, feature_class: str, config: dict[str, Any]) -> str:
    """Return the no-leakage classification for one feature."""
    if feature_class == "unavailable":
        return "unavailable; not used"
    lower = feature_name.lower()
    tokens = [str(token).lower() for token in config["analysis"].get("forbidden_feature_tokens", [])]
    hits = [token for token in tokens if token in lower]
    if hits or feature_class == "forbidden_leakage":
        return "forbidden leakage or claim-boundary field: " + semicolon(hits or [feature_class])
    if feature_class == "morphology_proxy":
        return "allowed only as descriptive proxy through explicit station-to-cell mapping; not a local WBGT target"
    return "allowed descriptive station-context field"


def feature_notes(feature_class: str) -> str:
    """Return compact feature-class notes."""
    if feature_class == "morphology_proxy":
        return "Do not use to infer station-level WBGT unless mapping is explicit; descriptive only in A-L2.0."
    if feature_class == "forcing_pairing_metadata":
        return "May describe station/weather pairing context, not causal correction."
    if feature_class == "forbidden_leakage":
        return "Inventoried only to enforce exclusion."
    if feature_class == "unavailable":
        return "Not found in configured sources."
    return ""


def merge_grid_morphology(feature_frame: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Merge selected v10 grid morphology through explicit station cell mapping."""
    rows: list[dict[str, Any]] = []
    station_col = str(config["schema"]["station_col"])
    mapping_candidates = [col for col in ["pairing_cell_id", "cell_id", "nearest_grid_cell", "pairing_nearest_grid_cell"] if col in feature_frame.columns]
    if not mapping_candidates:
        path = resolve_path(str(config["inputs"]["grid_v10_basic_morphology"]))
        for col in config["analysis"]["grid_morphology_columns"]:
            rows.append(feature_schema_row(f"grid_v10_{col}", "grid_v10_basic_morphology", rel(path), "morphology_proxy", False, False, "no_explicit_station_cell_mapping"))
        return feature_frame, rows
    mapping_col = mapping_candidates[0]
    out = feature_frame.copy()
    for path_key in ["grid_v10_basic_morphology", "grid_v10_umep_features"]:
        path = resolve_path(str(config["inputs"][path_key]))
        if not path.exists():
            continue
        header = read_csv(path, nrows=0).columns.tolist()
        usecols = ["cell_id", *[col for col in config["analysis"]["grid_morphology_columns"] if col in header]]
        if len(usecols) <= 1:
            continue
        grid = read_csv(path, usecols=usecols).drop_duplicates("cell_id")
        rename = {col: f"grid_v10_{col}" for col in grid.columns if col != "cell_id" and f"grid_v10_{col}" not in out.columns}
        grid = grid.rename(columns=rename)
        out = out.merge(grid, left_on=mapping_col, right_on="cell_id", how="left", suffixes=("", f"_{path_key}"))
        if "cell_id" in out.columns and "cell_id" != mapping_col:
            out = out.drop(columns=["cell_id"])
        for original, final in rename.items():
            rows.append(
                feature_schema_row(
                    final,
                    path_key,
                    rel(path),
                    "morphology_proxy",
                    True,
                    True,
                    "explicit station-to-cell mapping available via " + mapping_col,
                    source_column=original,
                    n_stations_available=int(out[final].notna().sum()) if final in out else 0,
                )
            )
    if station_col in out.columns:
        out[station_col] = out[station_col].astype(str)
    return out, rows


def forbidden_and_unavailable_schema_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Add explicit forbidden and unavailable schema rows."""
    rows: list[dict[str, Any]] = []
    forbidden_examples = [
        "official_wbgt_c",
        "heat_stress_category",
        "wbgt_residual_weather_only_c",
        "obs_ge31",
        "obs_ge33",
        "station_id_as_predictor",
    ]
    for feature in forbidden_examples:
        rows.append(
            feature_schema_row(
                feature,
                "configured_sources",
                "multiple",
                "forbidden_leakage",
                True,
                False,
                feature_leakage_note(feature, "forbidden_leakage", config),
            )
        )
    unavailable = ["sensor_height_m", "instrument_siting_class", "manual_station_shade_class", "station_maintenance_metadata"]
    for feature in unavailable:
        rows.append(
            feature_schema_row(
                feature,
                "data_stations_dir",
                rel(resolve_path(str(config["inputs"]["data_stations_dir"]))),
                "unavailable",
                False,
                False,
                "unavailable; not invented",
                n_stations_available=0,
            )
        )
    return rows


def descriptive_rank_association(feature_frame: pd.DataFrame, signal: pd.Series, feature_names: list[str]) -> tuple[str, float, int]:
    """Return the strongest absolute Spearman rank association descriptively."""
    best_feature = ""
    best_abs = np.nan
    best_n = 0
    for feature in feature_names:
        if feature not in feature_frame.columns:
            continue
        values = numeric(feature_frame[feature])
        pair = pd.DataFrame({"feature": values, "signal": signal}).dropna()
        if len(pair) < 3 or pair["feature"].nunique() < 2 or pair["signal"].nunique() < 2:
            continue
        corr = pair["feature"].rank().corr(pair["signal"].rank())
        if np.isfinite(corr) and (not np.isfinite(best_abs) or abs(corr) > best_abs):
            best_abs = float(abs(corr))
            best_feature = feature
            best_n = int(len(pair))
    return best_feature, best_abs, best_n


def make_identifiability_matrix(
    residual_summary: pd.DataFrame,
    probability_summary: pd.DataFrame,
    stability: pd.DataFrame,
    feature_schema: pd.DataFrame,
    feature_frame: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Build feature-class by signal identifiability matrix."""
    station_col = str(config["schema"]["station_col"])
    min_assoc = int(config["analysis"]["min_stations_for_rank_association"])
    compute_assoc = bool(config["analysis"].get("compute_descriptive_rank_association", True))
    signal_sources: list[tuple[str, str, pd.Series]] = []
    if not residual_summary.empty:
        residual_signal = residual_summary.set_index("station_id")["mean_context_adjusted_score_residual_c"]
        signal_sources.append(("mean_context_adjusted_score_residual_c", "", residual_signal))
        high_tail_signal = residual_summary.set_index("station_id")["mean_context_adjusted_high_tail_residual_c"]
        signal_sources.append(("mean_context_adjusted_high_tail_residual_c", "", high_tail_signal))
    if not probability_summary.empty:
        for case_id, group in probability_summary.groupby("probability_case_id", dropna=False):
            signal = group.set_index("station_id")["mean_context_adjusted_probability_error_obs_minus_p"]
            signal_sources.append(("mean_context_adjusted_probability_error_obs_minus_p", str(case_id), signal))

    allowed_schema = feature_schema[
        feature_schema["available"].astype(bool)
        & feature_schema["allowed_for_future_preflight_model"].astype(bool)
    ].copy() if not feature_schema.empty else pd.DataFrame()
    classes = ["station_metadata", "forcing_pairing_metadata", "morphology_proxy"]
    rows: list[dict[str, Any]] = []
    feature_indexed = feature_frame.set_index(station_col) if station_col in feature_frame.columns else pd.DataFrame()
    for signal_metric, case_id, signal in signal_sources:
        stable_count = stable_signal_count(stability, signal_metric, case_id)
        low_support_count = low_support_count_for_signal(stability, signal_metric, case_id)
        for feature_class in classes:
            class_schema = allowed_schema[allowed_schema["feature_class"].eq(feature_class)].copy()
            feature_names = class_schema["feature_name"].astype(str).tolist() if not class_schema.empty else []
            coverage = numeric(class_schema["n_stations_available"]).max() if "n_stations_available" in class_schema else np.nan
            best_feature = ""
            best_abs_corr = np.nan
            assoc_n = 0
            if compute_assoc and len(signal.dropna()) >= min_assoc and feature_names and not feature_indexed.empty:
                aligned_signal = signal.reindex(feature_indexed.index)
                best_feature, best_abs_corr, assoc_n = descriptive_rank_association(feature_indexed, aligned_signal, feature_names)
            rows.append(
                {
                    "signal_metric": signal_metric,
                    "probability_case_id": case_id,
                    "feature_class": feature_class,
                    "n_stations": int(len(signal.dropna())),
                    "stable_signal_station_count": stable_count,
                    "low_support_station_count": low_support_count,
                    "n_feature_columns_available": int(len(feature_names)),
                    "max_station_feature_coverage": coverage,
                    "best_descriptive_rank_feature": best_feature,
                    "best_abs_spearman_rank_association": best_abs_corr,
                    "association_n_stations": assoc_n,
                    "association_interpretation": association_interpretation(best_abs_corr, assoc_n, min_assoc),
                    "identifiability_assessment": identifiability_assessment(stable_count, len(feature_names), coverage, config),
                }
            )
    return pd.DataFrame(rows)


def stable_signal_count(stability: pd.DataFrame, metric_name: str, case_id: str) -> int:
    """Count stable station labels for a signal metric/case."""
    if stability.empty:
        return 0
    match = stability[stability["metric_name"].eq(metric_name)].copy()
    if case_id:
        match = match[match["probability_case_id"].astype(str).eq(case_id)]
    else:
        match = match[match["probability_case_id"].astype(str).eq("")]
    return int(match["stability_label"].isin(STABLE_LABELS).sum())


def low_support_count_for_signal(stability: pd.DataFrame, metric_name: str, case_id: str) -> int:
    """Count low-support station labels for a signal metric/case."""
    if stability.empty:
        return 0
    match = stability[stability["metric_name"].eq(metric_name)].copy()
    if case_id:
        match = match[match["probability_case_id"].astype(str).eq(case_id)]
    else:
        match = match[match["probability_case_id"].astype(str).eq("")]
    return int(match["stability_label"].eq("unstable_low_support").sum())


def association_interpretation(abs_corr: float, n: int, min_assoc: int) -> str:
    """Return descriptive-only rank association interpretation."""
    if not np.isfinite(abs_corr) or n < min_assoc:
        return "not_computed_or_insufficient_variation"
    if n < 30:
        return "descriptive_only_low_n_not_causal"
    return "descriptive_only_not_causal"


def identifiability_assessment(stable_count: int, feature_count: int, coverage: float, config: dict[str, Any]) -> str:
    """Classify one signal/feature-class row."""
    if stable_count < int(config["analysis"]["min_stable_station_count"]):
        return "signal_not_stable_enough"
    if feature_count < int(config["analysis"]["min_station_feature_count"]):
        return "features_too_sparse"
    if not np.isfinite(float(coverage)) or float(coverage) < float(config["analysis"]["min_feature_station_coverage"]):
        return "feature_station_coverage_weak"
    return "scoped_preflight_model_possible_descriptive_low_n"


def decide_status(
    residual_summary: pd.DataFrame,
    probability_summary: pd.DataFrame,
    stability: pd.DataFrame,
    feature_schema: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[str, str]:
    """Return the A-L2.0 decision status and recommendation."""
    if residual_summary.empty or probability_summary.empty:
        return "BLOCKED", "Do not proceed: station-level residual/probability data could not be built."
    min_stable = int(config["analysis"]["min_stable_station_count"])
    residual_stable = stable_signal_count(stability, "mean_context_adjusted_score_residual_c", "")
    high_tail_stable = stable_signal_count(stability, "mean_context_adjusted_high_tail_residual_c", "")
    challenger_stable = stable_signal_count(stability, "mean_context_adjusted_probability_error_obs_minus_p", CHALLENGER_CASE_ID)
    current_stable = stable_signal_count(stability, "mean_context_adjusted_probability_error_obs_minus_p", CURRENT_CASE_ID)
    allowed_features = feature_schema[
        feature_schema["available"].astype(bool)
        & feature_schema["allowed_for_future_preflight_model"].astype(bool)
    ] if not feature_schema.empty else pd.DataFrame()
    feature_count = int(len(allowed_features))
    feature_coverage = numeric(allowed_features.get("n_stations_available", pd.Series(dtype=float))).max() if not allowed_features.empty else 0
    has_features = feature_count >= int(config["analysis"]["min_station_feature_count"]) and feature_coverage >= int(config["analysis"]["min_feature_station_coverage"])
    has_signal_after_challenger = challenger_stable >= min_stable or high_tail_stable >= min_stable
    has_any_signal = residual_stable >= min_stable or current_stable >= min_stable or high_tail_stable >= min_stable
    if not has_any_signal:
        return "A_L2_NOT_IDENTIFIABLE", "Hold A-L2.1: station signal is unstable or low-support after Level 1 controls."
    if not has_features or not has_signal_after_challenger:
        return "A_L2_DATA_LIMITED", "Do not train a final residual ML model; at most do a scoped A-L2.1 feature audit after review."
    return (
        "A_L2_READY_FOR_SCOPED_PREFLIGHT_MODEL",
        "Proceed only to a scoped A-L2.1 preflight model design, with station_id excluded and no operational claims.",
    )


def headline_summaries(
    residual_summary: pd.DataFrame,
    probability_summary: pd.DataFrame,
    stability: pd.DataFrame,
    feature_schema: pd.DataFrame,
    recommendation: str,
) -> tuple[str, str, str, str]:
    """Create compact final/status headline strings."""
    stable_residual = stable_signal_count(stability, "mean_context_adjusted_score_residual_c", "")
    stable_high_tail = stable_signal_count(stability, "mean_context_adjusted_high_tail_residual_c", "")
    stable_challenger = stable_signal_count(stability, "mean_context_adjusted_probability_error_obs_minus_p", CHALLENGER_CASE_ID)
    residual_text = (
        f"context-adjusted residual stable stations={stable_residual}; "
        f"context-adjusted high-tail stable stations={stable_high_tail}; "
        f"challenger probability-error stable stations={stable_challenger}"
    )
    focus = focus_station_summary(residual_summary, probability_summary)
    allowed = feature_schema[
        feature_schema["available"].astype(bool)
        & feature_schema["allowed_for_future_preflight_model"].astype(bool)
    ] if not feature_schema.empty else pd.DataFrame()
    by_class = allowed.groupby("feature_class")["feature_name"].nunique().to_dict() if not allowed.empty else {}
    feature_text = semicolon(f"{key}:{value}" for key, value in by_class.items()) or "no allowed station-context features found"
    return residual_text, focus, feature_text, recommendation


def focus_station_summary(residual_summary: pd.DataFrame, probability_summary: pd.DataFrame) -> str:
    """Return compact S142/S139 summary."""
    parts: list[str] = []
    for station_id in ["S142", "S139"]:
        res = residual_summary[residual_summary["station_id"].astype(str).eq(station_id)]
        if res.empty:
            parts.append(f"{station_id}:missing")
            continue
        row = res.iloc[0]
        prob = probability_summary[
            probability_summary["station_id"].astype(str).eq(station_id)
            & probability_summary["probability_case_id"].eq(CHALLENGER_CASE_ID)
        ]
        miss = prob["miss_rate_at_policy"].iloc[0] if not prob.empty and "miss_rate_at_policy" in prob else np.nan
        parts.append(
            f"{station_id}:n_ge31={fmt(row['n_ge31'], 0)}, "
            f"ctx_resid={fmt(row['mean_context_adjusted_score_residual_c'])}C, "
            f"challenger_miss={fmt(miss)}"
        )
    return "; ".join(parts)


def write_report(
    path: Path,
    config_path: Path,
    result: PreflightResult,
    inventory: pd.DataFrame,
    residual_summary: pd.DataFrame,
    probability_summary: pd.DataFrame,
    stability: pd.DataFrame,
    feature_schema: pd.DataFrame,
    identifiability: pd.DataFrame,
) -> None:
    """Write the A-L2.0 Markdown preflight report."""
    focus_stability = stability[
        stability["station_id"].astype(str).isin(["S142", "S139"])
        & stability["metric_name"].isin(
            [
                "mean_context_adjusted_score_residual_c",
                "mean_context_adjusted_probability_error_obs_minus_p",
                "miss_rate_at_policy",
            ]
        )
    ].copy()
    top_resid = residual_summary.sort_values("mean_context_adjusted_score_residual_c", ascending=False).head(8)
    low_resid = residual_summary.sort_values("mean_context_adjusted_score_residual_c", ascending=True).head(8)
    prob_focus = probability_summary[
        probability_summary["station_id"].astype(str).isin(["S142", "S139"])
    ].copy()
    feature_counts = (
        feature_schema.groupby(["feature_class", "available", "allowed_for_future_preflight_model"], dropna=False)
        .agg(feature_count=("feature_name", "nunique"), max_station_coverage=("n_stations_available", "max"))
        .reset_index()
        if not feature_schema.empty
        else pd.DataFrame()
    )
    lines = [
        "# System A A-L2.0 Station-Context Residual Identifiability Preflight",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Acceptance status: `{result.acceptance_status}`",
        f"Decision status: `{result.decision_status}`",
        f"Branch: `{git_branch()}`",
        f"Config: `{rel(config_path)}`",
        "",
        "## 1. Why A-L2 is not a Level 1 substitute",
        "",
        "A-L2.0 only asks whether station-level residual or probability-error structure remains identifiable after the current Level 1 score/probability evidence and the A-L1H.3 recall-first challenger. It does not replace WBGT_A, does not recalibrate the canonical Level 1 companion, and does not train a final station-context residual model.",
        "",
        "The current Level 1 contract remains: WBGT_A/model_score is the primary retrospective temporal severity diagnostic; P_ge31 is a retrospective diagnostic companion only; the challenger is recall-first diagnostic evidence, not the canonical replacement.",
        "",
        "## 2. Input inventory",
        "",
        markdown_table(
            inventory,
            ["inventory_role", "exists", "rows_total", "has_station_id", "has_cell_id", "source_class", "notes"],
            limit=40,
        ),
        "",
        "## 3. Station residual summaries",
        "",
        "Residual definition: `score_residual_c = official_wbgt_c - model_score`. Positive residual means the Level 1 score underpredicts the official station WBGT target in this diagnostic input.",
        "",
        "Top context-adjusted positive residual stations:",
        "",
        markdown_table(
            top_resid,
            [
                "station_id",
                "n_rows",
                "n_ge31",
                "mean_score_residual_c",
                "mean_context_adjusted_score_residual_c",
                "mean_high_tail_residual_c",
                "low_support_warning_flag",
            ],
            limit=8,
        ),
        "",
        "Top context-adjusted negative residual stations:",
        "",
        markdown_table(
            low_resid,
            [
                "station_id",
                "n_rows",
                "n_ge31",
                "mean_score_residual_c",
                "mean_context_adjusted_score_residual_c",
                "mean_high_tail_residual_c",
                "low_support_warning_flag",
            ],
            limit=8,
        ),
        "",
        "## 4. Probability error summaries",
        "",
        "`probability_error = obs_ge31 - p_ge31`. Positive values mean observed events exceed predicted probability on average. Three policies are compared: current companion best-F1/selected policy, A-L1H.3 recall-first challenger selected policy, and current companion recall90.",
        "",
        markdown_table(
            prob_focus,
            [
                "probability_case_id",
                "station_id",
                "n_ge31",
                "p_ge31_Brier",
                "mean_context_adjusted_probability_error_obs_minus_p",
                "miss_rate_at_policy",
                "false_alarm_ratio_at_policy",
            ],
            limit=12,
        ),
        "",
        "## 5. S142 and S139 assessment",
        "",
        result.s142_s139_summary,
        "",
        "S142 remains the main high-tail underprediction caveat to review. S139 remains low-support for station-specific conclusions; its threshold behavior is dominated by very small event counts and should not be used as broad reliability proof.",
        "",
        "## 6. Stability / bootstrap findings",
        "",
        result.stable_residual_summary,
        "",
        markdown_table(
            focus_stability,
            [
                "station_id",
                "metric_name",
                "probability_case_id",
                "n_ge31",
                "estimate",
                "ci_low",
                "ci_high",
                "stability_label",
            ],
            limit=24,
        ),
        "",
        "Bootstrap resamples station date/hour rows with deterministic seeds. Stability labels are diagnostic: they do not establish station-context causal correction.",
        "",
        "## 7. Station-context feature availability",
        "",
        result.station_feature_availability,
        "",
        markdown_table(
            feature_counts,
            ["feature_class", "available", "allowed_for_future_preflight_model", "feature_count", "max_station_coverage"],
            limit=20,
        ),
        "",
        "Morphology proxy fields are inventoried only because explicit station-to-cell mapping exists. They are not used here to infer station-level WBGT, and they remain proxy context rather than causal station correction.",
        "",
        "## 8. Identifiability decision",
        "",
        markdown_table(
            identifiability,
            [
                "signal_metric",
                "probability_case_id",
                "feature_class",
                "stable_signal_station_count",
                "n_feature_columns_available",
                "max_station_feature_coverage",
                "best_descriptive_rank_feature",
                "best_abs_spearman_rank_association",
                "identifiability_assessment",
            ],
            limit=40,
        ),
        "",
        f"Decision: `{result.decision_status}`.",
        "",
        "## 9. Whether to proceed to A-L2.1",
        "",
        result.a_l2_1_recommendation,
        "",
        "A-L2.1, if opened, should be a scoped preflight model-design/reproducibility gate only. It should exclude `station_id` as a predictive feature, avoid random station/time splits, and preserve the current Level 1 claim boundaries.",
        "",
        "## 10. Claim boundaries",
        "",
        "- No local 100m WBGT is created or implied.",
        "- No station causal correction is claimed.",
        "- No operational warning probability is claimed.",
        "- The A-L1H.3 challenger is not promoted as canonical replacement.",
        "- No full A-L2 residual ML model is trained in this preflight.",
        "",
        "## Output paths",
        "",
        *[f"- `{rel(out_path)}`" for out_path in result.output_paths],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_status(path: Path, config_path: Path, result: PreflightResult) -> None:
    """Write the A-L2.0 lane status file."""
    lines = [
        "# A-L2.0 Status",
        "",
        f"Status: {result.acceptance_status}",
        f"Decision: {result.decision_status}",
        f"Branch: {git_branch()}",
        "Scope: station-context residual identifiability preflight only.",
        "",
        "Commands run:",
        f"- python scripts/v11_l2_run_identifiability_preflight.py --config {rel(config_path)}",
        "",
        "Key results:",
        f"- {result.stable_residual_summary}",
        f"- {result.s142_s139_summary}",
        f"- {result.station_feature_availability}",
        "",
        "Caveats:",
        "- No final residual ML model trained.",
        "- No station-context causal correction claimed.",
        "- No local 100m WBGT created.",
        "- P_ge31 remains a retrospective diagnostic companion only.",
        "- A-L1H.3 challenger remains recall-first diagnostic evidence only.",
        "",
        f"Next recommended action: {result.a_l2_1_recommendation}",
        "",
        "Files created / modified:",
        *[f"- {rel(out_path)}" for out_path in result.output_paths],
        "",
        "Safe to commit: controlled scripts/config/docs and compact CSV/Markdown outputs only after review.",
        "Not safe to commit: raw data, rasters, SOLWEIG outputs, forecast-live hourly CSVs, or archive raw dumps.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_blocked_outputs(config: dict[str, Any], config_path: Path, reason: str) -> PreflightResult:
    """Write minimal BLOCKED outputs when required station data cannot be built."""
    paths = output_paths(config)
    assert_output_scope(paths)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(config)
    inventory.to_csv(paths["inventory"], index=False)
    for key in ["residual_summary", "probability_summary", "bootstrap", "feature_schema", "identifiability"]:
        pd.DataFrame([{"blocked_reason": reason}]).to_csv(paths[key], index=False)
    result = PreflightResult(
        acceptance_status="BLOCKED",
        decision_status="BLOCKED",
        stable_residual_summary=reason,
        s142_s139_summary="blocked",
        station_feature_availability="blocked",
        a_l2_1_recommendation="Do not proceed until required station-level data are available.",
        output_paths=[paths[key] for key in ["inventory", "residual_summary", "probability_summary", "bootstrap", "feature_schema", "identifiability", "report", "status"]],
    )
    write_report(
        paths["report"],
        config_path,
        result,
        inventory,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    write_status(paths["status"], config_path, result)
    return result


def run_preflight(config_path: Path) -> PreflightResult:
    """Run the A-L2.0 identifiability preflight."""
    config = load_config(config_path)
    paths = output_paths(config)
    assert_output_scope(paths)
    paths["dir"].mkdir(parents=True, exist_ok=True)

    inventory = input_inventory(config)
    inventory.to_csv(paths["inventory"], index=False)

    try:
        residual = prepare_residual_frame(config)
        probability_cases = prepare_probability_cases(config)
    except Exception as exc:
        return write_blocked_outputs(config, config_path, f"Required data build failed: {exc}")
    if residual.empty or probability_cases.empty:
        return write_blocked_outputs(config, config_path, "No station-level residual/probability rows available.")

    residual_summary = summarize_station_residuals(residual, config)
    probability_summary = summarize_station_probability_errors(probability_cases, config)
    stability = make_stability_rows(residual, probability_cases, config)
    feature_frame, feature_schema = build_station_feature_frame(residual, config)
    identifiability = make_identifiability_matrix(
        residual_summary,
        probability_summary,
        stability,
        feature_schema,
        feature_frame,
        config,
    )

    decision_status, recommendation = decide_status(residual_summary, probability_summary, stability, feature_schema, config)
    stable_text, focus_text, feature_text, recommendation = headline_summaries(
        residual_summary,
        probability_summary,
        stability,
        feature_schema,
        recommendation,
    )
    result = PreflightResult(
        acceptance_status="PASS",
        decision_status=decision_status,
        stable_residual_summary=stable_text,
        s142_s139_summary=focus_text,
        station_feature_availability=feature_text,
        a_l2_1_recommendation=recommendation,
        output_paths=[paths[key] for key in ["inventory", "residual_summary", "probability_summary", "bootstrap", "feature_schema", "identifiability", "report", "status"]],
    )

    residual_summary.to_csv(paths["residual_summary"], index=False)
    probability_summary.to_csv(paths["probability_summary"], index=False)
    stability.to_csv(paths["bootstrap"], index=False)
    feature_schema.to_csv(paths["feature_schema"], index=False)
    identifiability.to_csv(paths["identifiability"], index=False)
    write_report(paths["report"], config_path, result, inventory, residual_summary, probability_summary, stability, feature_schema, identifiability)
    write_status(paths["status"], config_path, result)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run System A A-L2.0 station-context identifiability preflight.")
    parser.add_argument("--config", default="configs/v11/systema_l2_identifiability_preflight.yaml")
    args = parser.parse_args()
    result = run_preflight(resolve_path(args.config))
    print(f"[acceptance_status] {result.acceptance_status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[stable_residual] {result.stable_residual_summary}")
    print(f"[s142_s139] {result.s142_s139_summary}")
    print(f"[station_feature_availability] {result.station_feature_availability}")
    print(f"[a_l2_1_recommendation] {result.a_l2_1_recommendation}")
    return 0 if result.acceptance_status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
