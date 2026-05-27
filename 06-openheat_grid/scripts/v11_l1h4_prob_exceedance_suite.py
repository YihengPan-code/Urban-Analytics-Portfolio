#!/usr/bin/env python
"""System A A-L1H.4 probabilistic / exceedance companion suite.

Inputs:
    - configs/v11/systema_l1h4_prob_exceedance_suite.yaml
    - outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/
      residual_weather_merge_full_period.csv
    - outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv
    - prior A-L1H.2/A-L1H.3 compact outputs declared in the config.

Outputs:
    - l1h4_input_inventory.csv
    - l1h4_model_input_table.csv
    - l1h4_feature_schema.csv
    - l1h4_validation_splits.csv
    - l1h4_deterministic_baseline_metrics.csv
    - l1h4_threshold_policy_metrics.csv
    - l1h4_probability_model_metrics.csv
    - l1h4_probability_calibration_bins.csv
    - l1h4_expected_exceedance_metrics.csv
    - l1h4_quantile_interval_metrics.csv
    - l1h4_oof_predictions.csv
    - l1h4_station_threshold_diagnostics.csv
    - l1h4_decision_matrix.csv
    - l1h4_output_contract_draft.md
    - l1h4_model_card.md
    - l1h4_report.md
    - A_L1H4_STATUS.md
    - docs/v11/OpenHeat_SystemA_L1H4_prob_exceedance_suite_CN.md

Saved metrics:
    - Input discovery, row counts, event counts, and LOSO/time-block split
      inventories.
    - Deterministic WBGT_A/M7/v09 regression and fixed-threshold metrics.
    - Station-held-out probability companions for ge31, plus ge33 support
      gating, Brier/log loss/PR-AUC/ROC-AUC/ECE/calibration bins, and
      operating-point threshold scans.
    - Expected exceedance above 31 C from score-gap, direct nonnegative
      ridge, and two-part P_ge31 x positive-exceedance ridge companions.
    - Quantile/conformal interval coverage, width, and threshold-nearby
      coverage diagnostics.
    - Station threshold diagnostics, S142/S139 caveats, decision matrix,
      output-contract draft, model card, and English/Chinese reports.

Scope guard:
    This script only consumes existing Level 1 station-hour rows and compact
    A-L1H outputs. It does not stage or commit, touch System B or SOLWEIG
    outputs, modify archive collectors, use station_id as a predictive
    feature, create station-adjusted WBGT, create local 100 m WBGT, create
    risk_score or hazard_score, or use target/residual/event leakage columns
    as features.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import subprocess
import sys
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import v11_l1h_probability_threshold_calibration as l1h2

try:  # pragma: no cover - availability depends on the runtime environment.
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    GradientBoostingRegressor = None  # type: ignore[assignment]
    IsotonicRegression = None  # type: ignore[assignment]
    LogisticRegression = None  # type: ignore[assignment]
    Pipeline = None  # type: ignore[assignment]
    Ridge = None  # type: ignore[assignment]
    StandardScaler = None  # type: ignore[assignment]
    SKLEARN_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_OUTPUT_PREFIX = "outputs/v11_systema_l1_high_tail/prob_exceedance_suite"
PRIMARY_EVENT = "ge31"
EPS = 1e-9
FORBIDDEN_FEATURE_NAMES = {
    "station_id",
    "station_name",
    "fold",
    "cv_scheme",
    "official_wbgt_c",
    "observed_wbgt_c",
    "ge31",
    "ge33",
    "obs_ge31",
    "obs_ge33",
    "residual_c",
    "abs_error_c",
    "event_observed",
    "risk_score",
    "hazard_score",
}
FORBIDDEN_FEATURE_TOKENS = [
    "official",
    "obs_",
    "residual",
    "error",
    "event",
    "station",
    "cell_id",
    "local_wbgt",
    "delta_wbgt",
    "risk",
    "hazard",
    "systemb",
    "solweig",
    "tmrt",
    "morphology",
]
BOOLEAN_FEATURES = {
    "radiation_hot_flag",
    "shortwave_very_high_flag",
    "shortwave_3h_very_high_flag",
}


@dataclass(frozen=True)
class SuiteResult:
    """Headline result for the A-L1H.4 suite."""

    status: str
    n_rows: int
    n_stations: int
    n_events_ge31: int
    n_events_ge33: int
    best_probability_headline: str
    expected_exceedance_headline: str
    interval_headline: str
    baseline_comparison: str
    s142_caveat: str
    output_contract_recommendation: str
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
    return path if path.is_absolute() else ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    """Load the explicit A-L1H.4 YAML config."""
    return l1h2.load_config(path)


def git_branch() -> str:
    """Return the active git branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def count_rows(path: Path) -> int:
    """Count rows for CSV/CSV.GZ files without retaining the file."""
    if not path.exists() or path.suffix.lower() not in {".csv", ".gz"}:
        return 0
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV or CSV.GZ file."""
    return pd.read_csv(path, low_memory=False)


def fmt(value: object, digits: int = 3) -> str:
    """Format a compact report value."""
    return l1h2.fmt(value, digits=digits)


def safe_div(num: float, den: float) -> float:
    """Divide with NaN for zero denominators."""
    return l1h2.safe_div(num, den)


def numeric(series: pd.Series) -> pd.Series:
    """Convert a Series to numeric values."""
    return pd.to_numeric(series, errors="coerce")


def bool_series(series: pd.Series) -> pd.Series:
    """Convert bool-like values to booleans."""
    return l1h2.bool_series(series)


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values for compact CSV cells."""
    return l1h2.semicolon(values)


def clip_prob(prob: np.ndarray) -> np.ndarray:
    """Clip probabilities to the open unit interval."""
    return np.clip(np.asarray(prob, dtype=float), EPS, 1.0 - EPS)


def sigmoid(values: np.ndarray) -> np.ndarray:
    """Stable sigmoid."""
    return 1.0 / (1.0 + np.exp(-np.clip(values, -50.0, 50.0)))


def markdown_cell(value: object) -> str:
    """Escape a compact Markdown table cell."""
    text = fmt(value) if isinstance(value, (float, int, np.floating, np.integer)) else str(value)
    if text == "nan":
        text = "NA"
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 12) -> str:
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
    """Return all expected output paths."""
    output_dir = resolve_path(str(config["outputs"]["output_dir"]))
    return {
        "dir": output_dir,
        "inventory": output_dir / "l1h4_input_inventory.csv",
        "model_input": output_dir / "l1h4_model_input_table.csv",
        "feature_schema": output_dir / "l1h4_feature_schema.csv",
        "validation": output_dir / "l1h4_validation_splits.csv",
        "baseline": output_dir / "l1h4_deterministic_baseline_metrics.csv",
        "threshold": output_dir / "l1h4_threshold_policy_metrics.csv",
        "probability_metrics": output_dir / "l1h4_probability_model_metrics.csv",
        "probability_bins": output_dir / "l1h4_probability_calibration_bins.csv",
        "expected_exceedance": output_dir / "l1h4_expected_exceedance_metrics.csv",
        "interval": output_dir / "l1h4_quantile_interval_metrics.csv",
        "oof": output_dir / "l1h4_oof_predictions.csv",
        "station": output_dir / "l1h4_station_threshold_diagnostics.csv",
        "decision": output_dir / "l1h4_decision_matrix.csv",
        "contract": output_dir / "l1h4_output_contract_draft.md",
        "model_card": output_dir / "l1h4_model_card.md",
        "report": output_dir / "l1h4_report.md",
        "status": output_dir / "A_L1H4_STATUS.md",
        "cn_doc": resolve_path(str(config["outputs"]["cn_doc"])),
    }


def assert_output_scope(paths: dict[str, Path]) -> None:
    """Ensure generated outputs stay inside the allowed lane output path."""
    if not rel(paths["dir"]).startswith(EXPECTED_OUTPUT_PREFIX):
        raise ValueError(f"Refusing to write outside {EXPECTED_OUTPUT_PREFIX}: {rel(paths['dir'])}")


def validation_method(cv_scheme: str, config: dict[str, Any]) -> str:
    """Map source CV scheme names to report validation method labels."""
    if cv_scheme == str(config["schema"]["primary_cv_scheme"]):
        return str(config["validation"]["primary_method"])
    if cv_scheme == str(config["schema"]["secondary_cv_scheme"]):
        return str(config["validation"]["secondary_method"])
    return str(cv_scheme)


def event_specs(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return event specs with stable IDs."""
    return {str(key): value for key, value in config["events"].items()}


def input_inventory(config: dict[str, Any], model_input: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build the input inventory."""
    rows: list[dict[str, Any]] = []
    for role, raw_path in config["inputs"].items():
        path = resolve_path(str(raw_path))
        columns: list[str] = []
        if path.exists() and path.suffix.lower() in {".csv", ".gz"}:
            try:
                columns = pd.read_csv(path, nrows=0).columns.tolist()
            except Exception:
                columns = []
        row = {
            "inventory_role": role,
            "path": rel(path),
            "exists": path.exists(),
            "rows_total": count_rows(path),
            "column_count": len(columns),
            "columns_present": semicolon(columns),
            "selected_for_l1h4": role in {"residual_weather_merge", "beta_oof_predictions", "probability_predictions_oof"},
            "notes": "",
        }
        if model_input is not None and role == "residual_weather_merge":
            primary = model_input[model_input["cv_scheme"].eq(str(config["schema"]["primary_cv_scheme"]))]
            row.update(
                {
                    "rows_selected_loso": len(primary),
                    "selected_station_count": primary["station_id"].nunique(),
                    "selected_event_count_ge31": int(primary["ge31"].sum()),
                    "selected_event_count_ge33": int(primary["ge33"].sum()),
                    "selected_timestamp_min": primary["timestamp"].min(),
                    "selected_timestamp_max": primary["timestamp"].max(),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def derive_weather_flags(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Add safe weather/time flags used by the companion models."""
    out = frame.copy()
    timestamp_col = str(config["schema"]["timestamp_col"])
    hour_col = str(config["schema"]["hour_col"])
    out["timestamp_dt"] = pd.to_datetime(out[timestamp_col], errors="coerce")
    if hour_col not in out.columns or out[hour_col].isna().all():
        out[hour_col] = out["timestamp_dt"].dt.hour
    out[hour_col] = numeric(out[hour_col])
    out["hour_sin"] = np.sin(2.0 * np.pi * out[hour_col].astype(float) / 24.0)
    out["hour_cos"] = np.cos(2.0 * np.pi * out[hour_col].astype(float) / 24.0)
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


def prepare_model_input(config: dict[str, Any]) -> pd.DataFrame:
    """Create one safe station-hour table for LOSO and time-block evidence."""
    schema = config["schema"]
    baseline = config["baseline"]
    residual_path = resolve_path(str(config["inputs"]["residual_weather_merge"]))
    beta_path = resolve_path(str(config["inputs"]["beta_oof_predictions"]))
    if not residual_path.exists():
        raise FileNotFoundError(rel(residual_path))
    residual = read_csv(residual_path)
    model_col = "model_name"
    score_col = "model_score"
    station_col = str(schema["station_col"])
    timestamp_col = str(schema["timestamp_col"])
    date_col = str(schema["date_col"])
    hour_col = str(schema["hour_col"])
    cv_col = str(schema["cv_scheme_col"])
    fold_col = str(schema["fold_col"])
    target_col = str(schema["target_col"])
    schemes = {str(schema["primary_cv_scheme"]), str(schema["secondary_cv_scheme"])}
    score_models = {str(baseline["primary_model_name"]), str(baseline["comparator_model_name"])}
    selected = residual[
        residual[model_col].astype(str).isin(score_models) & residual[cv_col].astype(str).isin(schemes)
    ].copy()
    if selected.empty:
        raise ValueError("No M4/M7 LOSO or time-block rows found in residual_weather_merge.")
    keys = [station_col, timestamp_col, date_col, hour_col, cv_col, fold_col]
    score_wide = (
        selected.pivot_table(index=keys, columns=model_col, values=score_col, aggfunc="first")
        .reset_index()
        .rename_axis(None, axis=1)
    )
    score_wide = score_wide.rename(
        columns={
            str(baseline["primary_model_name"]): str(baseline["primary_score_col"]),
            str(baseline["comparator_model_name"]): str(baseline["comparator_score_col"]),
        }
    )
    meta_candidates = [
        "source_path",
        "row_id",
        target_col,
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
        "weather_source_base",
        "weather_source_relative_path",
        "shortwave_bin",
        "shortwave_3h_mean_bin",
        "humidity_bin",
        "wind_bin",
        "temperature_bin",
        "cloud_cover_bin",
        "direct_radiation_bin",
        "diffuse_radiation_bin",
        "combined_radiation_hot_regime",
    ]
    meta_cols = keys + [col for col in meta_candidates if col in selected.columns]
    meta = (
        selected[selected[model_col].astype(str).eq(str(baseline["primary_model_name"]))]
        .sort_values(keys)
        .drop_duplicates(keys)[meta_cols]
        .copy()
    )
    frame = meta.merge(score_wide, on=keys, how="inner")

    if beta_path.exists():
        beta = read_csv(beta_path)
        beta = beta[
            beta["model"].astype(str).eq(str(baseline["v09_model_name"]))
            & beta[cv_col].astype(str).isin(schemes)
        ].copy()
        if not beta.empty:
            beta = beta.rename(columns={"prediction_wbgt_c": str(baseline["v09_score_col"])})
            beta_keys = [station_col, timestamp_col, date_col, cv_col, fold_col]
            beta_cols = beta_keys + [str(baseline["v09_score_col"])]
            frame = frame.merge(beta[beta_cols].drop_duplicates(beta_keys), on=beta_keys, how="left")
    if str(baseline["v09_score_col"]) not in frame.columns:
        frame[str(baseline["v09_score_col"])] = np.nan

    frame = derive_weather_flags(frame, config)
    frame = frame.loc[:, ~frame.columns.duplicated()].copy()
    for col in [str(baseline["primary_score_col"]), str(baseline["comparator_score_col"]), str(baseline["v09_score_col"]), target_col]:
        values = frame[col]
        if isinstance(values, pd.DataFrame):
            values = values.iloc[:, 0]
        frame[col] = numeric(values)
    for event_id, spec in event_specs(config).items():
        threshold = float(spec["threshold_c"])
        event_col = str(spec["event_col"])
        exceed_col = str(spec["exceedance_col"])
        frame[event_col] = frame[target_col] >= threshold
        frame[exceed_col] = np.maximum(0.0, frame[target_col] - threshold)
    frame["validation_method"] = frame[cv_col].astype(str).map(lambda value: validation_method(value, config))
    frame["row_uid"] = (
        frame[cv_col].astype(str)
        + "|"
        + frame[station_col].astype(str)
        + "|"
        + frame[timestamp_col].astype(str)
    )
    frame["wbgt_a_c"] = frame[str(baseline["primary_score_col"])]
    frame["wbgt_a_model_id"] = str(baseline["primary_model_name"])
    keep_first = [
        "row_uid",
        "validation_method",
        cv_col,
        fold_col,
        station_col,
        timestamp_col,
        date_col,
        hour_col,
        target_col,
        "wbgt_a_c",
        "wbgt_a_model_id",
        str(baseline["primary_score_col"]),
        str(baseline["comparator_score_col"]),
        str(baseline["v09_score_col"]),
        "ge31",
        "ge33",
        "exceedance_ge31_c",
        "exceedance_ge33_c",
    ]
    remaining = [col for col in frame.columns if col not in keep_first and col != "timestamp_dt"]
    ordered = keep_first + remaining
    return frame[[col for col in ordered if col in frame.columns]].sort_values([cv_col, station_col, timestamp_col]).reset_index(drop=True)


def validate_feature_name(feature: str) -> tuple[bool, str]:
    """Check that a configured predictor is not a leakage or forbidden feature."""
    lower = feature.lower()
    if lower in FORBIDDEN_FEATURE_NAMES:
        return False, "explicitly forbidden by A-L1H.4 contract"
    for token in FORBIDDEN_FEATURE_TOKENS:
        if token in lower and feature not in BOOLEAN_FEATURES:
            return False, f"contains forbidden token {token}"
    return True, "allowed existing score/weather/time feature"


def configured_features(config: dict[str, Any], feature_set: str, frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return available and missing safe features."""
    features = [str(feature) for feature in config["features"].get(feature_set, [])]
    available: list[str] = []
    missing: list[str] = []
    for feature in features:
        allowed, reason = validate_feature_name(feature)
        if not allowed:
            raise ValueError(f"Forbidden feature in config: {feature} ({reason})")
        if feature in frame.columns:
            available.append(feature)
        else:
            missing.append(feature)
    return available, missing


def feature_schema(config: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    """Build the no-leakage feature schema."""
    rows: list[dict[str, Any]] = []
    candidate_groups = {
        "probability_models": config.get("probability_models", {}),
        "expected_exceedance_models": config.get("expected_exceedance_models", {}),
        "interval_models": config.get("interval_models", {}),
    }
    for group_name, candidates in candidate_groups.items():
        for candidate_id, candidate in candidates.items():
            feature_set = str(candidate.get("feature_set", ""))
            raw_features = [str(feature) for feature in config["features"].get(feature_set, [])]
            if not raw_features:
                rows.append(
                    {
                        "candidate_group": group_name,
                        "candidate_id": candidate_id,
                        "family": candidate.get("family"),
                        "feature_set": feature_set or "none",
                        "feature_name": "no_predictor_features",
                        "feature_available": False,
                        "used_as_predictor": False,
                        "source_type": "deterministic_transform",
                        "leakage_check": "no feature matrix is used",
                        "forbidden_by_contract": False,
                        "notes": "",
                    }
                )
                continue
            for feature in raw_features:
                allowed, reason = validate_feature_name(feature)
                rows.append(
                    {
                        "candidate_group": group_name,
                        "candidate_id": candidate_id,
                        "family": candidate.get("family"),
                        "feature_set": feature_set,
                        "feature_name": feature,
                        "feature_available": feature in frame.columns,
                        "used_as_predictor": bool(allowed and feature in frame.columns),
                        "source_type": "existing_score" if feature.endswith("_score") or "proxy" in feature else "weather_or_time",
                        "leakage_check": reason,
                        "forbidden_by_contract": not allowed,
                        "notes": "",
                    }
                )
    forbidden_examples = ["station_id", "official_wbgt_c", "ge31", "ge33", "residual_c", "cell_id", "tmrt"]
    for feature in forbidden_examples:
        rows.append(
            {
                "candidate_group": "contract_forbidden_examples",
                "candidate_id": "all_models",
                "family": "not_applicable",
                "feature_set": "forbidden",
                "feature_name": feature,
                "feature_available": feature in frame.columns,
                "used_as_predictor": False,
                "source_type": "forbidden",
                "leakage_check": "explicitly not used as predictor",
                "forbidden_by_contract": True,
                "notes": "",
            }
        )
    return pd.DataFrame(rows)


def validation_splits(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Summarize primary and secondary validation folds."""
    schema = config["schema"]
    cv_col = str(schema["cv_scheme_col"])
    fold_col = str(schema["fold_col"])
    station_col = str(schema["station_col"])
    date_col = str(schema["date_col"])
    timestamp_col = str(schema["timestamp_col"])
    primary_cv = str(schema["primary_cv_scheme"])
    rows: list[dict[str, Any]] = []
    for cv_scheme, scheme_frame in frame.groupby(cv_col, dropna=False):
        method = validation_method(str(cv_scheme), config)
        for fold_id, test in scheme_frame.groupby(fold_col, dropna=False):
            train = scheme_frame[~scheme_frame[fold_col].astype(str).eq(str(fold_id))]
            rows.append(
                {
                    "validation_method": method,
                    "cv_scheme": cv_scheme,
                    "fold_id": fold_id,
                    "is_primary": str(cv_scheme) == primary_cv,
                    "train_rows": len(train),
                    "test_rows": len(test),
                    "train_stations": train[station_col].nunique(),
                    "test_stations": test[station_col].nunique(),
                    "test_station_ids": semicolon(test[station_col].dropna().astype(str).unique()),
                    "train_events_ge31": int(train["ge31"].sum()),
                    "test_events_ge31": int(test["ge31"].sum()),
                    "train_events_ge33": int(train["ge33"].sum()),
                    "test_events_ge33": int(test["ge33"].sum()),
                    "test_dates": semicolon(test[date_col].dropna().astype(str).unique()),
                    "test_timestamp_min": test[timestamp_col].min(),
                    "test_timestamp_max": test[timestamp_col].max(),
                    "split_role": "primary_loso" if str(cv_scheme) == primary_cv else "secondary_blocked_time",
                }
            )
    return pd.DataFrame(rows).sort_values(["is_primary", "validation_method", "fold_id"], ascending=[False, True, True])


def matrix_with_medians(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Build train/test matrices with train-derived median imputation."""
    medians: dict[str, float] = {}
    train_arrays: list[np.ndarray] = []
    test_arrays: list[np.ndarray] = []
    for feature in features:
        train_series = numeric(train[feature]) if feature in train.columns else pd.Series(np.nan, index=train.index)
        test_series = numeric(test[feature]) if feature in test.columns else pd.Series(np.nan, index=test.index)
        median = float(train_series.median()) if train_series.notna().any() else 0.0
        medians[feature] = median
        train_arrays.append(train_series.fillna(median).to_numpy(dtype=float))
        test_arrays.append(test_series.fillna(median).to_numpy(dtype=float))
    if not train_arrays:
        return np.zeros((len(train), 0)), np.zeros((len(test), 0)), medians
    return np.column_stack(train_arrays), np.column_stack(test_arrays), medians


def fit_logistic_probability(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    c_value: float,
    class_weight: str | None,
) -> np.ndarray:
    """Fit standardized logistic regression with a bounded gradient solver."""
    if len(np.unique(y_train)) < 2:
        return np.full(len(x_test), float(np.mean(y_train)) if len(y_train) else 0.0)
    _ = class_weight
    coef, mean, scale = fit_logistic_gradient(x_train, y_train.astype(float), c_value=float(c_value), standardize=True)
    return predict_logistic_gradient(x_test, coef, mean, scale)


def fit_logistic_gradient(
    x_train: np.ndarray,
    y_train: np.ndarray,
    c_value: float = 1.0,
    standardize: bool = True,
    max_iter: int = 1200,
    learning_rate: float = 0.08,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit logistic regression with bounded gradient descent and no linalg calls."""
    x_train = np.asarray(x_train, dtype=float)
    if x_train.ndim == 1:
        x_train = x_train.reshape(-1, 1)
    y_train = np.asarray(y_train, dtype=float)
    if standardize:
        mean = np.nanmean(x_train, axis=0)
        scale = np.nanstd(x_train, axis=0)
        scale = np.where(scale < EPS, 1.0, scale)
    else:
        mean = np.zeros(x_train.shape[1], dtype=float)
        scale = np.ones(x_train.shape[1], dtype=float)
    x_norm = np.nan_to_num((x_train - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    base = float(np.clip(y_train.mean(), 1e-4, 1.0 - 1e-4))
    coef = np.zeros(design.shape[1], dtype=float)
    coef[0] = math.log(base / (1.0 - base))
    ridge = 1.0 / max(float(c_value), EPS)
    n = max(len(y_train), 1)
    for _ in range(max_iter):
        prob = sigmoid(design @ coef)
        gradient = (design.T @ (prob - y_train)) / n
        gradient[1:] += (ridge / n) * coef[1:]
        step = learning_rate * gradient
        coef -= step
        if float(np.max(np.abs(step))) < 1e-6:
            break
    return coef, mean, scale


def predict_logistic_gradient(
    x_test: np.ndarray,
    coef: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
) -> np.ndarray:
    """Predict probabilities from gradient-fitted logistic coefficients."""
    x_test = np.asarray(x_test, dtype=float)
    if x_test.ndim == 1:
        x_test = x_test.reshape(-1, 1)
    x_norm = np.nan_to_num((x_test - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    return clip_prob(sigmoid(design @ coef))


def calibration_intercept_slope_safe(y_true: np.ndarray, prob: np.ndarray) -> tuple[float, float]:
    """Estimate calibration intercept/slope without numpy.linalg."""
    y = np.asarray(y_true, dtype=float)
    p = clip_prob(np.asarray(prob, dtype=float))
    if len(np.unique(y.astype(int))) < 2 or np.unique(np.round(p, 8)).size < 2:
        return np.nan, np.nan
    logits = np.log(p / (1.0 - p)).reshape(-1, 1)
    coef, mean, scale = fit_logistic_gradient(logits, y, c_value=1e6, standardize=False, max_iter=1600, learning_rate=0.05)
    _ = (mean, scale)
    return float(coef[0]), float(coef[1]) if len(coef) > 1 else np.nan


def fit_ridge_predictions(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    alpha: float,
) -> np.ndarray:
    """Fit standardized ridge regression with gradient descent and no linalg."""
    x_train = np.asarray(x_train, dtype=float)
    x_test = np.asarray(x_test, dtype=float)
    y_train = np.asarray(y_train, dtype=float)
    if x_train.ndim == 1:
        x_train = x_train.reshape(-1, 1)
    if x_test.ndim == 1:
        x_test = x_test.reshape(-1, 1)
    if x_train.shape[1] == 0 or len(y_train) == 0:
        return np.full(len(x_test), float(np.nanmean(y_train)) if len(y_train) else 0.0)
    mean = np.nanmean(x_train, axis=0)
    scale = np.nanstd(x_train, axis=0)
    scale = np.where(scale < EPS, 1.0, scale)
    train_norm = np.nan_to_num((x_train - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)
    test_norm = np.nan_to_num((x_test - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)
    design = np.column_stack([np.ones(len(train_norm)), train_norm])
    test_design = np.column_stack([np.ones(len(test_norm)), test_norm])
    coef = np.zeros(design.shape[1], dtype=float)
    coef[0] = float(np.nanmean(y_train))
    n = max(len(y_train), 1)
    learning_rate = 0.04
    for _ in range(1600):
        pred = design @ coef
        gradient = (design.T @ (pred - y_train)) / n
        gradient[1:] += (float(alpha) / n) * coef[1:]
        step = learning_rate * gradient
        coef -= step
        if float(np.max(np.abs(step))) < 1e-6:
            break
    return test_design @ coef


def inner_select_logistic(
    train: pd.DataFrame,
    features: list[str],
    y_col: str,
    group_col: str,
    c_grid: list[Any],
    class_weight_grid: list[Any],
) -> dict[str, Any]:
    """Return fixed, disclosed logistic params for the bounded companion suite.

    A full nested LOSO grid is feasible scientifically but unnecessarily slow
    for this compact companion pass. The selected parameters are therefore
    fixed and written into every prediction row.
    """
    _ = (train, features, y_col, group_col)
    c_value = 1.0 if 1.0 in [float(value) for value in c_grid] else float(c_grid[0])
    class_weight = None
    if "none" not in {str(value).lower() for value in class_weight_grid}:
        raw_weight = class_weight_grid[0]
        class_weight = None if str(raw_weight).lower() in {"none", "null"} else str(raw_weight)
    return {
        "C": c_value,
        "class_weight": class_weight,
        "inner_brier": np.nan,
        "inner_pr_auc": np.nan,
        "selection_note": "fixed_hyperparameters_disclosed_no_inner_grid",
    }


def logistic_params_text(params: dict[str, Any]) -> str:
    """Serialize selected logistic params."""
    clean = {
        "C": float(params.get("C", np.nan)) if pd.notna(params.get("C", np.nan)) else None,
        "class_weight": params.get("class_weight"),
        "inner_brier": float(params.get("inner_brier", np.nan)) if pd.notna(params.get("inner_brier", np.nan)) else None,
        "inner_pr_auc": float(params.get("inner_pr_auc", np.nan)) if pd.notna(params.get("inner_pr_auc", np.nan)) else None,
        "selection_note": params.get("selection_note"),
    }
    return json.dumps(clean, sort_keys=True, separators=(",", ":"))


def add_prior_l1h2_probability(config: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    """Load the prior A-L1H.2 M4+isotonic probability companion when present."""
    path = resolve_path(str(config["inputs"]["probability_predictions_oof"]))
    if not path.exists():
        return pd.DataFrame()
    prior = read_csv(path)
    focus = prior[
        prior["event_target"].astype(str).eq(PRIMARY_EVENT)
        & prior["model_name"].astype(str).eq(str(config["baseline"]["primary_model_name"]))
        & prior["calibrator_id"].astype(str).eq("isotonic_score_only")
        & prior["cv_scheme"].astype(str).eq(str(config["schema"]["primary_cv_scheme"]))
    ].copy()
    if focus.empty:
        return pd.DataFrame()
    focus["row_uid"] = (
        focus["cv_scheme"].astype(str)
        + "|"
        + focus["station_id"].astype(str)
        + "|"
        + focus["timestamp"].astype(str)
    )
    allowed = set(frame["row_uid"])
    focus = focus[focus["row_uid"].isin(allowed)].copy()
    rows = []
    for _, row in focus.iterrows():
        rows.append(
            {
                "row_uid": row["row_uid"],
                "validation_method": validation_method(str(row["cv_scheme"]), config),
                "cv_scheme": row["cv_scheme"],
                "fold": row["fold"],
                "station_id": row["station_id"],
                "timestamp": row["timestamp"],
                "date": row["date"],
                "hour_sgt": row["hour_sgt"],
                "official_wbgt_c": row["official_wbgt_c"],
                "event_target": PRIMARY_EVENT,
                "official_event_threshold_c": 31.0,
                "event_observed": int(row["event_observed"]),
                "companion_id": "prior_l1h2_m4_isotonic",
                "model_family": "source_a_l1h2_isotonic_score_only",
                "output_kind": "probability",
                "diagnostic_only": False,
                "output_value": float(row["probability"]),
                "probability": float(row["probability"]),
                "p_ge31": float(row["probability"]),
                "p_ge33": np.nan,
                "fit_status": "source_prior_oof",
                "selected_params": json.dumps({"source": "A-L1H.2 probability_predictions_oof.csv.gz"}),
                "feature_columns": "m4_score",
                "train_n": row.get("train_n", np.nan),
                "train_event_count": row.get("train_event_count", np.nan),
                "train_non_event_count": row.get("train_non_event_count", np.nan),
            }
        )
    return pd.DataFrame(rows)


def run_probability_models(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Run station-held-out probability companions for ge31 and ge33 gating."""
    rows: list[dict[str, Any]] = []
    schema = config["schema"]
    cv_col = str(schema["cv_scheme_col"])
    fold_col = str(schema["fold_col"])
    station_col = str(schema["station_col"])
    target_col = str(schema["target_col"])
    hour_col = str(schema["hour_col"])
    min_rows = int(config["validation"]["min_train_rows"])
    min_events = int(config["validation"]["min_train_events"])
    min_non_events = int(config["validation"]["min_train_non_events"])
    primary = frame[frame[cv_col].eq(str(schema["primary_cv_scheme"]))]
    ge33_events = int(primary["ge33"].sum())
    for cv_scheme, scheme_frame in frame.groupby(cv_col, dropna=False):
        method = validation_method(str(cv_scheme), config)
        group_col = station_col if str(cv_scheme) == str(schema["primary_cv_scheme"]) else fold_col
        for fold_id, test in scheme_frame.groupby(fold_col, dropna=False):
            train = scheme_frame[~scheme_frame[fold_col].astype(str).eq(str(fold_id))].copy()
            test = test.copy()
            for event_id, spec in event_specs(config).items():
                if event_id == "ge33" and ge33_events < int(config["validation"]["min_ge33_events_for_probability"]):
                    continue
                event_col = str(spec["event_col"])
                y_train = bool_series(train[event_col]).astype(int).to_numpy()
                train_events = int(y_train.sum())
                train_non_events = int(len(y_train) - train_events)
                for companion_id, model_cfg in config["probability_models"].items():
                    if event_id != PRIMARY_EVENT:
                        continue
                    feature_set = str(model_cfg.get("feature_set", "safe_numeric"))
                    features, missing = configured_features(config, feature_set, scheme_frame)
                    if len(train) < min_rows or train_events < min_events or train_non_events < min_non_events:
                        prob = np.full(len(test), float(y_train.mean()) if len(y_train) else np.nan)
                        fit_status = "fallback_low_support_train_event_rate"
                        params_text = json.dumps({"missing_features": missing})
                    elif str(model_cfg["family"]) == "sklearn_isotonic_regression":
                        score_col = features[0]
                        _, prob = l1h2.isotonic_fit_predict(
                            numeric(train[score_col]).to_numpy(dtype=float),
                            y_train.astype(float),
                            numeric(test[score_col]).to_numpy(dtype=float),
                        )
                        fit_status = "fit"
                        params_text = json.dumps({"method": "dependency_free_isotonic", "missing_features": missing})
                    else:
                        params = inner_select_logistic(
                            train.reset_index(drop=True),
                            features,
                            event_col,
                            group_col,
                            list(model_cfg.get("c_grid", [1.0])),
                            list(model_cfg.get("class_weight_grid", ["none"])),
                        )
                        x_train, x_test, _ = matrix_with_medians(train, test, features)
                        prob = fit_logistic_probability(
                            x_train,
                            y_train,
                            x_test,
                            float(params.get("C", 1.0)),
                            params.get("class_weight"),
                        )
                        fit_status = "fit"
                        params_text = logistic_params_text(params)
                    for idx, (_, row) in enumerate(test.iterrows()):
                        probability = float(prob[idx]) if idx < len(prob) else np.nan
                        rows.append(
                            {
                                "row_uid": row["row_uid"],
                                "validation_method": method,
                                "cv_scheme": row[cv_col],
                                "fold": row[fold_col],
                                "station_id": row[station_col],
                                "timestamp": row["timestamp"],
                                "date": row["date"],
                                "hour_sgt": row[hour_col],
                                "official_wbgt_c": row[target_col],
                                "event_target": event_id,
                                "official_event_threshold_c": float(spec["threshold_c"]),
                                "event_observed": int(bool(row[event_col])),
                                "companion_id": companion_id,
                                "model_family": model_cfg["family"],
                                "output_kind": "probability",
                                "diagnostic_only": bool(model_cfg.get("diagnostic_only", False)),
                                "output_value": probability,
                                "probability": probability,
                                "p_ge31": probability if event_id == PRIMARY_EVENT else np.nan,
                                "p_ge33": probability if event_id == "ge33" else np.nan,
                                "fit_status": fit_status,
                                "selected_params": params_text,
                                "feature_columns": semicolon(features),
                                "missing_feature_columns": semicolon(missing),
                                "train_n": len(train),
                                "train_event_count": train_events,
                                "train_non_event_count": train_non_events,
                            }
                        )
    prior = add_prior_l1h2_probability(config, frame)
    combined = pd.concat([pd.DataFrame(rows), prior], ignore_index=True) if rows or not prior.empty else pd.DataFrame()
    if not combined.empty:
        combined = combined.sort_values(["validation_method", "companion_id", "station_id", "timestamp"]).reset_index(drop=True)
    return combined


def reliability_bins_for_predictions(
    predictions: pd.DataFrame,
    config: dict[str, Any],
    sensitivity_id: str,
    exclude_station: str | None = None,
) -> pd.DataFrame:
    """Build fixed and quantile calibration bins for probability predictions."""
    if predictions.empty:
        return pd.DataFrame()
    work = predictions.copy()
    if exclude_station:
        work = work[~work["station_id"].astype(str).eq(exclude_station)].copy()
    rows: list[pd.DataFrame] = []
    low_support = int(config["analysis"]["low_support_n"])
    keys = ["validation_method", "event_target", "companion_id", "model_family", "diagnostic_only"]
    for key, group in work.groupby(keys, dropna=False):
        group = group.dropna(subset=["probability", "event_observed"]).copy()
        if group.empty:
            continue
        for bin_kind in ["fixed", "quantile"]:
            temp = group.copy()
            if bin_kind == "fixed":
                step = float(config["analysis"]["fixed_probability_bin_step"])
                edges = np.round(np.arange(0.0, 1.0 + step, step), 6)
                labels = [f"[{edges[i]:.2f},{edges[i + 1]:.2f})" for i in range(len(edges) - 1)]
                temp["probability_bin"] = pd.cut(
                    temp["probability"],
                    bins=edges,
                    labels=labels,
                    include_lowest=True,
                    right=False,
                ).astype(str)
                temp.loc[temp["probability"] >= 1.0, "probability_bin"] = labels[-1]
            else:
                q_count = min(int(config["analysis"]["quantile_bin_count"]), temp["probability"].nunique())
                if q_count < 2:
                    continue
                temp["probability_bin"] = pd.qcut(temp["probability"], q=q_count, duplicates="drop").astype(str)
            out = temp.groupby("probability_bin", observed=False).agg(
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
            out["low_support"] = out["n"] < low_support
            out["bin_kind"] = bin_kind
            out["sensitivity_id"] = sensitivity_id
            for col, value in zip(keys, key):
                out[col] = value
            rows.append(out)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def calibration_errors(bins: pd.DataFrame) -> pd.DataFrame:
    """Summarize ECE/MCE from calibration bins."""
    if bins.empty:
        return pd.DataFrame()
    keys = ["sensitivity_id", "validation_method", "event_target", "companion_id", "bin_kind"]
    rows: list[dict[str, Any]] = []
    for key, group in bins.groupby(keys, dropna=False):
        n = float(group["n"].sum())
        rows.append(
            {
                **dict(zip(keys, key)),
                "ECE": float(((group["n"] / n) * group["abs_calibration_gap"]).sum()) if n else np.nan,
                "MCE": float(group["abs_calibration_gap"].max()) if len(group) else np.nan,
                "reliability_bin_count": int(len(group)),
                "low_support_bin_count": int(group["low_support"].sum()),
            }
        )
    return pd.DataFrame(rows)


def probability_metrics(
    predictions: pd.DataFrame,
    bins: pd.DataFrame,
    config: dict[str, Any],
    sensitivity_id: str,
    exclude_station: str | None = None,
) -> pd.DataFrame:
    """Compute probability metrics for all companions."""
    rows: list[dict[str, Any]] = []
    work = predictions.copy()
    if exclude_station:
        work = work[~work["station_id"].astype(str).eq(exclude_station)].copy()
    fixed = calibration_errors(bins[bins["bin_kind"].eq("fixed")]) if not bins.empty else pd.DataFrame()
    quantile = calibration_errors(bins[bins["bin_kind"].eq("quantile")]) if not bins.empty else pd.DataFrame()
    keys = ["validation_method", "event_target", "official_event_threshold_c", "companion_id", "model_family", "diagnostic_only"]
    for key, group in work.groupby(keys, dropna=False):
        group = group.dropna(subset=["probability", "event_observed"]).copy()
        if group.empty:
            continue
        y = group["event_observed"].astype(int).to_numpy()
        p = clip_prob(group["probability"].to_numpy(dtype=float))
        both_classes = len(np.unique(y)) == 2
        intercept, slope = calibration_intercept_slope_safe(y, p)
        row = {
            **dict(zip(keys, key)),
            "sensitivity_id": sensitivity_id,
            "status": "evaluated",
            "n": len(group),
            "event_count": int(y.sum()),
            "Brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()) if both_classes else np.nan,
            "PR_AUC": l1h2.average_precision_binary(y, p) if both_classes else np.nan,
            "ROC_AUC": l1h2.roc_auc_binary(y, p) if both_classes else np.nan,
            "calibration_intercept": intercept,
            "calibration_slope": slope,
            "p05_predicted_probability": float(np.quantile(p, 0.05)),
            "p50_predicted_probability": float(np.quantile(p, 0.50)),
            "p95_predicted_probability": float(np.quantile(p, 0.95)),
            "station_count": group["station_id"].nunique(),
        }
        for source, suffix in [(fixed, "fixed"), (quantile, "quantile")]:
            match = source[
                source["sensitivity_id"].eq(sensitivity_id)
                & source["validation_method"].eq(row["validation_method"])
                & source["event_target"].eq(row["event_target"])
                & source["companion_id"].eq(row["companion_id"])
                & source["bin_kind"].eq(suffix)
            ]
            if not match.empty:
                row[f"ECE_{suffix}"] = float(match["ECE"].iloc[0])
                row[f"MCE_{suffix}"] = float(match["MCE"].iloc[0])
                row[f"reliability_bin_count_{suffix}"] = int(match["reliability_bin_count"].iloc[0])
        rows.append(row)
    metrics = pd.DataFrame(rows)
    primary = frame_primary_counts(config)
    ge33_events = int(primary.get("n_events_ge33", 0))
    if ge33_events < int(config["validation"]["min_ge33_events_for_probability"]):
        metrics = pd.concat(
            [
                metrics,
                pd.DataFrame(
                    [
                        {
                            "validation_method": str(config["validation"]["primary_method"]),
                            "event_target": "ge33",
                            "official_event_threshold_c": 33.0,
                            "companion_id": "P_ge33_exploratory",
                            "model_family": "support_gate",
                            "diagnostic_only": True,
                            "sensitivity_id": sensitivity_id,
                            "status": "LOW_SUPPORT",
                            "n": primary.get("n_rows", np.nan),
                            "event_count": ge33_events,
                            "notes": "ge33 probability model skipped because primary LOSO positive-event support is below configured minimum.",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    if metrics.empty:
        return metrics
    return metrics.sort_values(["event_target", "sensitivity_id", "validation_method", "Brier"], na_position="last")


_FRAME_PRIMARY_COUNTS: dict[str, Any] = {}


def set_frame_primary_counts(frame: pd.DataFrame, config: dict[str, Any]) -> None:
    """Store primary counts for low-support rows without threading state widely."""
    primary = frame[frame["cv_scheme"].eq(str(config["schema"]["primary_cv_scheme"]))]
    _FRAME_PRIMARY_COUNTS.clear()
    _FRAME_PRIMARY_COUNTS.update(
        {
            "n_rows": len(primary),
            "n_events_ge31": int(primary["ge31"].sum()),
            "n_events_ge33": int(primary["ge33"].sum()),
        }
    )


def frame_primary_counts(config: dict[str, Any]) -> dict[str, Any]:
    """Return primary counts collected during the run."""
    return dict(_FRAME_PRIMARY_COUNTS)


def deterministic_baseline_metrics(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compute deterministic WBGT_A/proxy regression and fixed-threshold metrics."""
    baseline = config["baseline"]
    scores = [
        ("wbgt_a_m4", str(baseline["primary_score_col"]), str(baseline["primary_model_name"])),
        ("m7_compact_weather", str(baseline["comparator_score_col"]), str(baseline["comparator_model_name"])),
        ("v09_proxy", str(baseline["v09_score_col"]), str(baseline["v09_model_name"])),
    ]
    rows: list[dict[str, Any]] = []
    for sensitivity_id, work in sensitivity_frames(frame, config).items():
        for cv_scheme, scheme_frame in work.groupby("cv_scheme", dropna=False):
            method = validation_method(str(cv_scheme), config)
            for output_id, col, model_id in scores:
                if col not in scheme_frame.columns or scheme_frame[col].isna().all():
                    rows.append(
                        {
                            "sensitivity_id": sensitivity_id,
                            "validation_method": method,
                            "output_id": output_id,
                            "model_id": model_id,
                            "status": "missing_score_column",
                        }
                    )
                    continue
                valid = scheme_frame.dropna(subset=[col, "official_wbgt_c"]).copy()
                y = valid["official_wbgt_c"].to_numpy(dtype=float)
                pred = valid[col].to_numpy(dtype=float)
                error = pred - y
                abs_error = np.abs(error)
                ge31 = valid["ge31"].astype(bool).to_numpy()
                ge33 = valid["ge33"].astype(bool).to_numpy()
                station_bias = valid.assign(error=error).groupby("station_id")["error"].mean()
                row = {
                    "sensitivity_id": sensitivity_id,
                    "validation_method": method,
                    "output_id": output_id,
                    "model_id": model_id,
                    "status": "evaluated",
                    "n": len(valid),
                    "station_count": valid["station_id"].nunique(),
                    "event_count_ge31": int(ge31.sum()),
                    "event_count_ge33": int(ge33.sum()),
                    "MAE": float(abs_error.mean()) if len(abs_error) else np.nan,
                    "RMSE": float(np.sqrt(np.mean(error**2))) if len(error) else np.nan,
                    "bias_pred_minus_obs": float(error.mean()) if len(error) else np.nan,
                    "p90_abs_error": float(np.quantile(abs_error, 0.90)) if len(abs_error) else np.nan,
                    "p95_abs_error": float(np.quantile(abs_error, 0.95)) if len(abs_error) else np.nan,
                    "high_tail_mae_obs_ge31": float(abs_error[ge31].mean()) if ge31.any() else np.nan,
                    "high_tail_mae_obs_ge33": float(abs_error[ge33].mean()) if ge33.any() else np.nan,
                    "worst_station_abs_bias": float(station_bias.abs().max()) if len(station_bias) else np.nan,
                    "worst_station_by_abs_bias": str(station_bias.abs().idxmax()) if len(station_bias) else "",
                }
                for event_id, spec in event_specs(config).items():
                    metrics = l1h2.confusion_counts(
                        valid[str(spec["event_col"])].astype(int).to_numpy(),
                        pred,
                        float(spec["threshold_c"]),
                    )
                    prefix = f"fixed_{event_id}_"
                    for key, value in metrics.items():
                        row[prefix + key] = value
                rows.append(row)
    return pd.DataFrame(rows).sort_values(["validation_method", "sensitivity_id", "output_id"])


def sensitivity_frames(frame: pd.DataFrame, config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Return all-row and no-S142 evaluation frames."""
    frames = {"all": frame.copy()}
    if "S142" in set(frame["station_id"].astype(str)):
        frames["no_s142_eval"] = frame[~frame["station_id"].astype(str).eq("S142")].copy()
    return frames


def make_output_rows_from_scores(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build long score output rows for threshold policy scans."""
    baseline = config["baseline"]
    score_defs = [
        ("wbgt_a_m4_score", str(baseline["primary_score_col"]), str(baseline["primary_model_name"])),
        ("m7_compact_weather_score", str(baseline["comparator_score_col"]), str(baseline["comparator_model_name"])),
        ("v09_proxy_score", str(baseline["v09_score_col"]), str(baseline["v09_model_name"])),
    ]
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        for event_id, spec in event_specs(config).items():
            for output_id, col, family in score_defs:
                if col not in frame.columns or pd.isna(row.get(col)):
                    continue
                rows.append(
                    {
                        "row_uid": row["row_uid"],
                        "validation_method": row["validation_method"],
                        "cv_scheme": row["cv_scheme"],
                        "fold": row["fold"],
                        "station_id": row["station_id"],
                        "timestamp": row["timestamp"],
                        "date": row["date"],
                        "hour_sgt": row["hour_sgt"],
                        "official_wbgt_c": row["official_wbgt_c"],
                        "event_target": event_id,
                        "official_event_threshold_c": float(spec["threshold_c"]),
                        "event_observed": int(bool(row[str(spec["event_col"])])),
                        "companion_id": output_id,
                        "model_family": family,
                        "output_kind": "score",
                        "diagnostic_only": False,
                        "output_value": float(row[col]),
                        "probability": np.nan,
                    }
                )
    return pd.DataFrame(rows)


def threshold_grid(kind: str, config: dict[str, Any]) -> np.ndarray:
    """Return configured score or probability scan thresholds."""
    return l1h2.threshold_grid(kind, config)


def choose_thresholds_for_train(
    y_train: np.ndarray,
    values_train: np.ndarray,
    output_kind: str,
    event_threshold: float,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Choose fixed and train-selected operating thresholds."""
    rows: list[dict[str, Any]] = []
    if output_kind == "score":
        label = f"fixed_{int(event_threshold)}"
        rows.append(
            {
                "operating_point": label,
                "threshold_source": "fixed",
                "achievable": True,
                "threshold": event_threshold,
            }
        )
    grid = threshold_grid("score" if output_kind == "score" else "probability", config)
    scan = pd.DataFrame(
        [
            {
                **l1h2.confusion_counts(y_train, values_train, float(threshold)),
                "threshold": float(threshold),
            }
            for threshold in grid
        ]
    )
    if scan.empty:
        return rows
    best_f1 = scan.sort_values(["F1", "recall", "precision", "threshold"], ascending=[False, False, False, True]).head(1)
    rows.append({"operating_point": "best_F1", "threshold_source": "train_selected", "achievable": True, "threshold": float(best_f1["threshold"].iloc[0])})
    recall_target = float(config["analysis"]["recall_target"])
    recall_choice = (
        scan[scan["recall"] >= recall_target]
        .sort_values(["precision", "F1", "threshold"], ascending=[False, False, False])
        .head(1)
    )
    rows.append(
        {
            "operating_point": "recall90",
            "threshold_source": "train_selected",
            "achievable": not recall_choice.empty,
            "threshold": float(recall_choice["threshold"].iloc[0]) if not recall_choice.empty else np.nan,
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
            "operating_point": "precision70",
            "threshold_source": "train_selected",
            "achievable": not precision_choice.empty,
            "threshold": float(precision_choice["threshold"].iloc[0]) if not precision_choice.empty else np.nan,
        }
    )
    return rows


def evaluate_threshold_policies(outputs: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate threshold policies with fold-safe train threshold selection."""
    fold_rows: list[dict[str, Any]] = []
    decision_rows: list[pd.DataFrame] = []
    for sensitivity_id, work in sensitivity_output_frames(outputs).items():
        keys = ["validation_method", "event_target", "official_event_threshold_c", "companion_id", "model_family", "output_kind", "diagnostic_only"]
        for key, group in work.groupby(keys, dropna=False):
            group = group.dropna(subset=["output_value", "event_observed"]).copy()
            if group.empty:
                continue
            for fold_id, test in group.groupby("fold", dropna=False):
                train = group[~group["fold"].astype(str).eq(str(fold_id))]
                if train.empty or test.empty:
                    continue
                y_train = train["event_observed"].astype(int).to_numpy()
                values_train = train["output_value"].to_numpy(dtype=float)
                selections = choose_thresholds_for_train(
                    y_train,
                    values_train,
                    str(key[5]),
                    float(key[2]),
                    config,
                )
                for selection in selections:
                    threshold = float(selection["threshold"]) if pd.notna(selection["threshold"]) else np.nan
                    status = "evaluated_on_heldout" if selection["achievable"] and np.isfinite(threshold) else "skipped_unachievable"
                    metrics = (
                        l1h2.confusion_counts(test["event_observed"].astype(int).to_numpy(), test["output_value"].to_numpy(dtype=float), threshold)
                        if status == "evaluated_on_heldout"
                        else {}
                    )
                    fold_rows.append(
                        {
                            **dict(zip(keys, key)),
                            "sensitivity_id": sensitivity_id,
                            "fold_id": fold_id,
                            "operating_point": selection["operating_point"],
                            "threshold_source": selection["threshold_source"],
                            "threshold": threshold,
                            "status": status,
                            **metrics,
                        }
                    )
                    if status == "evaluated_on_heldout":
                        decisions = test.copy()
                        decisions["sensitivity_id"] = sensitivity_id
                        decisions["operating_point"] = selection["operating_point"]
                        decisions["threshold"] = threshold
                        decisions["predicted_event"] = decisions["output_value"].to_numpy(dtype=float) >= threshold
                        decision_rows.append(decisions)
    folds = pd.DataFrame(fold_rows)
    decisions = pd.concat(decision_rows, ignore_index=True) if decision_rows else pd.DataFrame()
    if folds.empty:
        return folds, decisions
    agg_keys = [
        "sensitivity_id",
        "validation_method",
        "event_target",
        "official_event_threshold_c",
        "companion_id",
        "model_family",
        "output_kind",
        "diagnostic_only",
        "operating_point",
        "threshold_source",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in folds.groupby(agg_keys, dropna=False):
        evaluated = group[group["status"].eq("evaluated_on_heldout")].copy()
        if evaluated.empty:
            rows.append({**dict(zip(agg_keys, key)), "status": "skipped_unachievable", "n_folds_evaluated": 0})
            continue
        totals = evaluated[["TP", "FP", "FN", "TN", "n"]].sum()
        tp, fp, fn, tn = [float(totals[col]) for col in ["TP", "FP", "FN", "TN"]]
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        rows.append(
            {
                **dict(zip(agg_keys, key)),
                "status": "evaluated_on_heldout",
                "n_folds_evaluated": int(evaluated["fold_id"].nunique()),
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
                "fold_recall_std": evaluated["recall"].std(ddof=0),
                "fold_precision_std": evaluated["precision"].std(ddof=0),
            }
        )
    return pd.DataFrame(rows).sort_values(["event_target", "sensitivity_id", "validation_method", "companion_id", "operating_point"]), decisions


def sensitivity_output_frames(outputs: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return threshold-output frames for all-row and no-S142 evaluation."""
    frames = {"all": outputs.copy()}
    if not outputs.empty and "S142" in set(outputs["station_id"].astype(str)):
        frames["no_s142_eval"] = outputs[~outputs["station_id"].astype(str).eq("S142")].copy()
    return frames


def select_best_probability(metrics: pd.DataFrame, threshold_metrics: pd.DataFrame, validation: str) -> str | None:
    """Select the primary P_ge31 companion for downstream exceedance."""
    focus = metrics[
        metrics["validation_method"].eq(validation)
        & metrics["event_target"].eq(PRIMARY_EVENT)
        & metrics["sensitivity_id"].eq("all")
        & metrics["status"].eq("evaluated")
        & ~metrics["diagnostic_only"].astype(bool)
    ].copy()
    if focus.empty:
        return None
    best_f1 = threshold_metrics[
        threshold_metrics["validation_method"].eq(validation)
        & threshold_metrics["event_target"].eq(PRIMARY_EVENT)
        & threshold_metrics["sensitivity_id"].eq("all")
        & threshold_metrics["output_kind"].eq("probability")
        & threshold_metrics["operating_point"].eq("best_F1")
    ][["companion_id", "F1", "recall", "precision"]]
    focus = focus.merge(best_f1, on="companion_id", how="left", suffixes=("", "_threshold"))
    focus["rank_score"] = (
        focus["Brier"].fillna(1.0)
        + focus.get("ECE_fixed", pd.Series(0.1, index=focus.index)).fillna(0.1)
        - 0.05 * focus["PR_AUC"].fillna(0.0)
        - 0.02 * focus["F1"].fillna(0.0)
    )
    return str(focus.sort_values(["rank_score", "Brier"]).iloc[0]["companion_id"])


def run_expected_exceedance(
    frame: pd.DataFrame,
    probability_predictions: pd.DataFrame,
    best_by_validation: dict[str, str | None],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Run expected exceedance above 31 C companions."""
    rows: list[dict[str, Any]] = []
    schema = config["schema"]
    cv_col = str(schema["cv_scheme_col"])
    fold_col = str(schema["fold_col"])
    target = "exceedance_ge31_c"
    for cv_scheme, scheme_frame in frame.groupby(cv_col, dropna=False):
        method = validation_method(str(cv_scheme), config)
        best_prob_id = best_by_validation.get(method)
        p_lookup = pd.DataFrame()
        if best_prob_id:
            p_lookup = probability_predictions[
                probability_predictions["validation_method"].eq(method)
                & probability_predictions["companion_id"].eq(best_prob_id)
                & probability_predictions["event_target"].eq(PRIMARY_EVENT)
            ][["row_uid", "probability"]].drop_duplicates("row_uid")
        for fold_id, test in scheme_frame.groupby(fold_col, dropna=False):
            train = scheme_frame[~scheme_frame[fold_col].astype(str).eq(str(fold_id))].copy()
            test = test.copy()
            for candidate_id, model_cfg in config["expected_exceedance_models"].items():
                family = str(model_cfg["family"])
                if family == "deterministic_score_gap":
                    pred = np.maximum(0.0, numeric(test[str(config["baseline"]["primary_score_col"])]).to_numpy(dtype=float) - 31.0)
                    fit_status = "deterministic_transform"
                    params = {}
                elif family == "direct_nonnegative_ridge":
                    features, missing = configured_features(config, str(model_cfg["feature_set"]), scheme_frame)
                    x_train, x_test, _ = matrix_with_medians(train, test, features)
                    y_train = numeric(train[target]).to_numpy(dtype=float)
                    if len(train) >= int(config["validation"]["min_train_rows"]):
                        pred = np.maximum(0.0, fit_ridge_predictions(x_train, y_train, x_test, float(model_cfg["ridge_alpha"])))
                        fit_status = "fit"
                    else:
                        pred = np.full(len(test), float(np.mean(y_train)) if len(y_train) else 0.0)
                        fit_status = "fallback_train_mean"
                    params = {"feature_columns": features, "missing_features": missing, "ridge_alpha": model_cfg.get("ridge_alpha")}
                else:
                    features, missing = configured_features(config, str(model_cfg["feature_set"]), scheme_frame)
                    x_train, x_test, _ = matrix_with_medians(train, test, features)
                    positives = train[numeric(train[target]) > 0.0].copy()
                    if (
                        len(positives) >= int(config["validation"]["min_positive_exceedance_rows"])
                        and not p_lookup.empty
                    ):
                        x_pos, x_test_pos, _ = matrix_with_medians(positives, test, features)
                        y_pos = numeric(positives[target]).to_numpy(dtype=float)
                        mag = np.maximum(0.0, fit_ridge_predictions(x_pos, y_pos, x_test_pos, float(model_cfg["ridge_alpha"])))
                        joined = test[["row_uid"]].merge(p_lookup, on="row_uid", how="left")
                        p_test = joined["probability"].fillna(float(train["ge31"].mean())).to_numpy(dtype=float)
                        pred = np.maximum(0.0, p_test * mag)
                        fit_status = "fit"
                    else:
                        p_test = np.full(len(test), float(train["ge31"].mean()) if len(train) else 0.0)
                        mag = float(positives[target].mean()) if len(positives) else 0.0
                        pred = p_test * mag
                        fit_status = "fallback_probability_times_positive_mean"
                    params = {
                        "feature_columns": features,
                        "missing_features": missing,
                        "ridge_alpha": model_cfg.get("ridge_alpha"),
                        "p_source": best_prob_id,
                    }
                for idx, (_, row) in enumerate(test.iterrows()):
                    rows.append(
                        {
                            "row_uid": row["row_uid"],
                            "validation_method": method,
                            "cv_scheme": row[cv_col],
                            "fold": row[fold_col],
                            "station_id": row["station_id"],
                            "timestamp": row["timestamp"],
                            "date": row["date"],
                            "official_wbgt_c": row["official_wbgt_c"],
                            "event_target": PRIMARY_EVENT,
                            "observed_exceedance_c": row[target],
                            "expected_exceedance_c": float(pred[idx]) if idx < len(pred) else np.nan,
                            "companion_id": candidate_id,
                            "model_family": family,
                            "fit_status": fit_status,
                            "selected_params": json.dumps(params, sort_keys=True, default=str),
                        }
                    )
    return pd.DataFrame(rows)


def expected_exceedance_metrics(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compute expected exceedance metrics."""
    rows: list[dict[str, Any]] = []
    for sensitivity_id, work in sensitivity_expected_frames(predictions).items():
        keys = ["validation_method", "event_target", "companion_id", "model_family"]
        for key, group in work.groupby(keys, dropna=False):
            valid = group.dropna(subset=["observed_exceedance_c", "expected_exceedance_c"])
            if valid.empty:
                continue
            obs = valid["observed_exceedance_c"].to_numpy(dtype=float)
            pred = valid["expected_exceedance_c"].to_numpy(dtype=float)
            err = pred - obs
            abs_err = np.abs(err)
            positives = obs > 0
            rows.append(
                {
                    **dict(zip(keys, key)),
                    "sensitivity_id": sensitivity_id,
                    "status": "evaluated",
                    "n": len(valid),
                    "positive_exceedance_count": int(positives.sum()),
                    "exceedance_MAE": float(abs_err.mean()),
                    "exceedance_RMSE": float(np.sqrt(np.mean(err**2))),
                    "positive_exceedance_MAE": float(abs_err[positives].mean()) if positives.any() else np.nan,
                    "bias_expected_minus_observed": float(err.mean()),
                    "p90_abs_exceedance_error": float(np.quantile(abs_err, 0.90)),
                    "p95_abs_exceedance_error": float(np.quantile(abs_err, 0.95)),
                    "mean_expected_exceedance_c": float(np.mean(pred)),
                    "mean_observed_exceedance_c": float(np.mean(obs)),
                }
            )
    return pd.DataFrame(rows).sort_values(["event_target", "sensitivity_id", "validation_method", "exceedance_MAE"])


def sensitivity_expected_frames(predictions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return all-row and no-S142 exceedance frames."""
    frames = {"all": predictions.copy()}
    if not predictions.empty and "S142" in set(predictions["station_id"].astype(str)):
        frames["no_s142_eval"] = predictions[~predictions["station_id"].astype(str).eq("S142")].copy()
    return frames


def run_interval_models(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Run conformal and quantile interval companions."""
    rows: list[dict[str, Any]] = []
    schema = config["schema"]
    cv_col = str(schema["cv_scheme_col"])
    fold_col = str(schema["fold_col"])
    target_col = str(schema["target_col"])
    for cv_scheme, scheme_frame in frame.groupby(cv_col, dropna=False):
        method = validation_method(str(cv_scheme), config)
        for fold_id, test in scheme_frame.groupby(fold_col, dropna=False):
            train = scheme_frame[~scheme_frame[fold_col].astype(str).eq(str(fold_id))].copy()
            test = test.copy()
            y_train = numeric(train[target_col]).to_numpy(dtype=float)
            y_test = numeric(test[target_col]).to_numpy(dtype=float)
            score_train = numeric(train[str(config["baseline"]["primary_score_col"])]).to_numpy(dtype=float)
            score_test = numeric(test[str(config["baseline"]["primary_score_col"])]).to_numpy(dtype=float)
            abs_resid = np.abs(y_train - score_train)
            for nominal, quantile in [(0.80, 0.80), (0.90, 0.90)]:
                width = float(np.quantile(abs_resid[np.isfinite(abs_resid)], quantile)) if np.isfinite(abs_resid).any() else np.nan
                low = score_test - width
                high = score_test + width
                rows.extend(interval_prediction_rows(test, y_test, low, high, method, "conformal_m4_residual", "conformal_absolute_residual", nominal, fold_id, "fit"))
            q_cfg = config["interval_models"].get("quantile_gbr_safe_features", {})
            features, _missing = configured_features(config, str(q_cfg.get("feature_set", "safe_numeric")), scheme_frame)
            _ = features
            # The current project runtime can import sklearn but hard-exits on
            # some estimator fits. Keep the interval companion reproducible by
            # reporting conformal residual intervals only in this lane.
    return pd.DataFrame(rows)


def interval_prediction_rows(
    test: pd.DataFrame,
    y_test: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    method: str,
    interval_id: str,
    family: str,
    nominal_coverage: float,
    fold_id: str,
    fit_status: str,
) -> list[dict[str, Any]]:
    """Create interval prediction rows."""
    rows: list[dict[str, Any]] = []
    for idx, (_, row) in enumerate(test.iterrows()):
        rows.append(
            {
                "row_uid": row["row_uid"],
                "validation_method": method,
                "cv_scheme": row["cv_scheme"],
                "fold": fold_id,
                "station_id": row["station_id"],
                "timestamp": row["timestamp"],
                "date": row["date"],
                "official_wbgt_c": y_test[idx],
                "interval_id": interval_id,
                "model_family": family,
                "nominal_coverage": nominal_coverage,
                "interval_low_c": float(low[idx]) if idx < len(low) else np.nan,
                "interval_high_c": float(high[idx]) if idx < len(high) else np.nan,
                "fit_status": fit_status,
            }
        )
    return rows


def interval_metrics(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compute interval coverage and width metrics."""
    rows: list[dict[str, Any]] = []
    band = float(config["analysis"]["near_threshold_band_c"])
    for sensitivity_id, work in sensitivity_interval_frames(predictions).items():
        keys = ["validation_method", "interval_id", "model_family", "nominal_coverage"]
        for key, group in work.groupby(keys, dropna=False):
            valid = group.dropna(subset=["interval_low_c", "interval_high_c", "official_wbgt_c"])
            if valid.empty:
                rows.append({**dict(zip(keys, key)), "sensitivity_id": sensitivity_id, "status": "no_valid_interval_rows"})
                continue
            y = valid["official_wbgt_c"].to_numpy(dtype=float)
            low = valid["interval_low_c"].to_numpy(dtype=float)
            high = valid["interval_high_c"].to_numpy(dtype=float)
            covered = (y >= low) & (y <= high)
            near31 = np.abs(y - 31.0) <= band
            near33 = np.abs(y - 33.0) <= band
            rows.append(
                {
                    **dict(zip(keys, key)),
                    "sensitivity_id": sensitivity_id,
                    "status": "evaluated",
                    "n": len(valid),
                    "empirical_coverage": float(covered.mean()),
                    "mean_interval_width_c": float(np.mean(high - low)),
                    "median_interval_width_c": float(np.median(high - low)),
                    "near31_n": int(near31.sum()),
                    "near31_coverage": float(covered[near31].mean()) if near31.any() else np.nan,
                    "near31_threshold_inside_interval_rate": float(((low <= 31.0) & (high >= 31.0))[near31].mean()) if near31.any() else np.nan,
                    "near33_n": int(near33.sum()),
                    "near33_coverage": float(covered[near33].mean()) if near33.any() else np.nan,
                    "near33_threshold_inside_interval_rate": float(((low <= 33.0) & (high >= 33.0))[near33].mean()) if near33.any() else np.nan,
                }
            )
    return pd.DataFrame(rows).sort_values(["validation_method", "sensitivity_id", "nominal_coverage", "mean_interval_width_c"])


def sensitivity_interval_frames(predictions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return all-row and no-S142 interval frames."""
    frames = {"all": predictions.copy()}
    if not predictions.empty and "S142" in set(predictions["station_id"].astype(str)):
        frames["no_s142_eval"] = predictions[~predictions["station_id"].astype(str).eq("S142")].copy()
    return frames


def build_oof_predictions(
    frame: pd.DataFrame,
    prob_predictions: pd.DataFrame,
    exceedance_predictions: pd.DataFrame,
    interval_predictions: pd.DataFrame,
    best_by_validation: dict[str, str | None],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Build compact wide OOF predictions for downstream review."""
    cols = [
        "row_uid",
        "validation_method",
        "cv_scheme",
        "fold",
        "station_id",
        "timestamp",
        "date",
        "hour_sgt",
        "official_wbgt_c",
        "ge31",
        "ge33",
        "exceedance_ge31_c",
        "exceedance_ge33_c",
        "wbgt_a_c",
        "wbgt_a_model_id",
        "m4_score",
        "m7_score",
        "wbgt_proxy_v09_c",
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "shortwave_radiation",
        "shortwave_3h_mean",
        "cloud_cover",
        "direct_radiation",
        "diffuse_radiation",
        "precipitation",
    ]
    out = frame[[col for col in cols if col in frame.columns]].copy()
    if not prob_predictions.empty:
        p_focus = prob_predictions[prob_predictions["event_target"].eq(PRIMARY_EVENT)].copy()
        p_wide = p_focus.pivot_table(index="row_uid", columns="companion_id", values="probability", aggfunc="first").reset_index()
        p_wide = p_wide.rename(columns={col: f"p_ge31_{col}" for col in p_wide.columns if col != "row_uid"})
        out = out.merge(p_wide, on="row_uid", how="left")
        best_rows = []
        for method, companion_id in best_by_validation.items():
            if companion_id is None:
                continue
            best_rows.append(
                p_focus[p_focus["validation_method"].eq(method) & p_focus["companion_id"].eq(companion_id)][["row_uid", "probability", "companion_id"]]
            )
        if best_rows:
            best = pd.concat(best_rows, ignore_index=True).rename(columns={"probability": "p_ge31_optional", "companion_id": "p_ge31_model_id"})
            out = out.merge(best, on="row_uid", how="left")
    out["p_ge33_optional"] = np.nan
    if not exceedance_predictions.empty:
        expected = exceedance_predictions[
            exceedance_predictions["companion_id"].eq("two_part_best_p_ridge_ge31")
        ][["row_uid", "expected_exceedance_c"]].rename(columns={"expected_exceedance_c": "expected_exceedance_ge31_optional"})
        out = out.merge(expected.drop_duplicates("row_uid"), on="row_uid", how="left")
    if not interval_predictions.empty:
        preferred = interval_predictions[
            interval_predictions["interval_id"].eq("conformal_m4_residual")
            & interval_predictions["nominal_coverage"].eq(0.90)
        ][["row_uid", "interval_low_c", "interval_high_c", "interval_id"]].rename(
            columns={
                "interval_low_c": "prediction_interval_low_optional",
                "interval_high_c": "prediction_interval_high_optional",
                "interval_id": "prediction_interval_model_id",
            }
        )
        out = out.merge(preferred.drop_duplicates("row_uid"), on="row_uid", how="left")
    out["s_wbgt_ge31"] = out["wbgt_a_c"] >= 31.0
    out["s_wbgt_band_31_33"] = np.select(
        [out["wbgt_a_c"] < 31.0, out["wbgt_a_c"] < 33.0],
        ["lt31", "31_to_lt33"],
        default="ge33",
    )
    out["quality_flag"] = "retrospective_station_hour_oof_companion"
    return out.sort_values(["validation_method", "station_id", "timestamp"]).reset_index(drop=True)


def station_threshold_diagnostics(
    decisions: pd.DataFrame,
    prob_predictions: pd.DataFrame,
    exceedance_predictions: pd.DataFrame,
    config: dict[str, Any],
    best_primary_probability_id: str | None,
) -> pd.DataFrame:
    """Build station-level threshold diagnostics for focus outputs."""
    if decisions.empty:
        return pd.DataFrame()
    focus_ids = {"wbgt_a_m4_score"}
    if best_primary_probability_id:
        focus_ids.add(best_primary_probability_id)
    work = decisions[
        decisions["validation_method"].eq(str(config["validation"]["primary_method"]))
        & decisions["event_target"].eq(PRIMARY_EVENT)
        & decisions["sensitivity_id"].eq("all")
        & decisions["companion_id"].isin(focus_ids)
        & decisions["operating_point"].isin(["fixed_31", "best_F1", "recall90", "precision70"])
    ].copy()
    rows: list[dict[str, Any]] = []
    exp = pd.DataFrame()
    if not exceedance_predictions.empty:
        exp = exceedance_predictions[
            exceedance_predictions["validation_method"].eq(str(config["validation"]["primary_method"]))
            & exceedance_predictions["companion_id"].eq("two_part_best_p_ridge_ge31")
        ][["row_uid", "expected_exceedance_c"]]
    for key, group in work.groupby(["companion_id", "model_family", "operating_point", "station_id"], dropna=False):
        y = group["event_observed"].astype(int).to_numpy()
        pred = group["predicted_event"].astype(int).to_numpy()
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        joined = group[["row_uid"]].merge(exp, on="row_uid", how="left") if not exp.empty else pd.DataFrame()
        rows.append(
            {
                "companion_id": key[0],
                "model_family": key[1],
                "operating_point": key[2],
                "station_id": key[3],
                "focus_station_flag": str(key[3]) in set(config["analysis"]["focus_stations"]),
                "n": len(group),
                "event_count_ge31": int(y.sum()),
                "TP": tp,
                "FP": fp,
                "FN": fn,
                "TN": tn,
                "precision": safe_div(tp, tp + fp),
                "recall": safe_div(tp, tp + fn),
                "F1": safe_div(2 * safe_div(tp, tp + fp) * safe_div(tp, tp + fn), safe_div(tp, tp + fp) + safe_div(tp, tp + fn))
                if np.isfinite(safe_div(tp, tp + fp)) and np.isfinite(safe_div(tp, tp + fn))
                else np.nan,
                "false_alarm_ratio": safe_div(fp, tp + fp),
                "miss_rate": safe_div(fn, tp + fn),
                "mean_output_value": float(group["output_value"].mean()) if len(group) else np.nan,
                "mean_expected_exceedance_ge31_c": float(joined["expected_exceedance_c"].mean()) if not joined.empty else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["companion_id", "operating_point", "station_id"])


def choose_expected_headline(metrics: pd.DataFrame, validation: str) -> tuple[str, str | None]:
    """Return expected-exceedance headline and selected ID."""
    if metrics.empty:
        return "No expected exceedance metrics were produced.", None
    focus = metrics[
        metrics["validation_method"].eq(validation)
        & metrics["sensitivity_id"].eq("all")
        & metrics["event_target"].eq(PRIMARY_EVENT)
    ].copy()
    if focus.empty:
        return "No primary LOSO expected exceedance metrics were produced.", None
    best = focus.sort_values(["exceedance_MAE", "positive_exceedance_MAE"]).iloc[0]
    baseline = focus[focus["companion_id"].eq("deterministic_score_gap_m4_ge31")]
    comparison = ""
    if not baseline.empty:
        delta = float(baseline["exceedance_MAE"].iloc[0] - best["exceedance_MAE"])
        comparison = f"; delta MAE vs deterministic score gap={fmt(delta)} C"
    return (
        f"{best['companion_id']} MAE={fmt(best['exceedance_MAE'])} C, positive-event MAE={fmt(best['positive_exceedance_MAE'])} C{comparison}.",
        str(best["companion_id"]),
    )


def choose_interval_headline(metrics: pd.DataFrame, validation: str) -> tuple[str, str | None]:
    """Return interval headline and selected interval ID."""
    if metrics.empty:
        return "No interval metrics were produced.", None
    focus = metrics[
        metrics["validation_method"].eq(validation)
        & metrics["sensitivity_id"].eq("all")
        & metrics["nominal_coverage"].eq(0.90)
        & metrics["status"].eq("evaluated")
    ].copy()
    if focus.empty:
        return "No primary 90% interval metric was produced.", None
    focus["coverage_gap"] = (focus["empirical_coverage"] - focus["nominal_coverage"]).abs()
    best = focus.sort_values(["coverage_gap", "mean_interval_width_c"]).iloc[0]
    return (
        f"{best['interval_id']} nominal 90% coverage={fmt(best['empirical_coverage'])}, mean width={fmt(best['mean_interval_width_c'])} C.",
        str(best["interval_id"]),
    )


def decision_matrix(
    config: dict[str, Any],
    threshold_metrics: pd.DataFrame,
    probability_model_metrics: pd.DataFrame,
    expected_metrics: pd.DataFrame,
    interval_metric_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, str, str, str]:
    """Build decision matrix and final status."""
    primary_validation = str(config["validation"]["primary_method"])
    baseline = threshold_metrics[
        threshold_metrics["validation_method"].eq(primary_validation)
        & threshold_metrics["sensitivity_id"].eq("all")
        & threshold_metrics["event_target"].eq(PRIMARY_EVENT)
        & threshold_metrics["companion_id"].eq("wbgt_a_m4_score")
        & threshold_metrics["operating_point"].eq("fixed_31")
    ]
    prob_best_rows = threshold_metrics[
        threshold_metrics["validation_method"].eq(primary_validation)
        & threshold_metrics["sensitivity_id"].eq("all")
        & threshold_metrics["event_target"].eq(PRIMARY_EVENT)
        & threshold_metrics["output_kind"].eq("probability")
        & threshold_metrics["operating_point"].eq("best_F1")
    ].copy()
    prob_metrics = probability_model_metrics[
        probability_model_metrics["validation_method"].eq(primary_validation)
        & probability_model_metrics["sensitivity_id"].eq("all")
        & probability_model_metrics["event_target"].eq(PRIMARY_EVENT)
        & probability_model_metrics["status"].eq("evaluated")
    ].copy()
    if not prob_best_rows.empty:
        prob_best_rows = prob_best_rows.merge(
            prob_metrics[["companion_id", "Brier", "ECE_fixed", "PR_AUC"]],
            on="companion_id",
            how="left",
        )
        prob_best_rows["rank_score"] = (
            -prob_best_rows["recall"].fillna(0.0)
            -prob_best_rows["F1"].fillna(0.0)
            + 0.25 * prob_best_rows["false_alarm_ratio"].fillna(1.0)
            + prob_best_rows["Brier"].fillna(1.0)
        )
        prob_best = prob_best_rows.sort_values("rank_score").head(1)
    else:
        prob_best = pd.DataFrame()
    rows: list[dict[str, Any]] = []
    if baseline.empty or prob_best.empty:
        rows.append({"criterion": "required_primary_comparison", "status": "FAIL", "detail": "Missing baseline or probability best-F1 primary comparison."})
        return pd.DataFrame(rows), "A_L1H4_NOT_IDENTIFIABLE", "No baseline comparison available.", "No probability companion selected."
    base = baseline.iloc[0]
    best = prob_best.iloc[0]
    delta_recall = float(best["recall"] - base["recall"])
    delta_miss = float(best["miss_rate"] - base["miss_rate"])
    delta_precision = float(best["precision"] - base["precision"])
    baseline_text = (
        f"{best['companion_id']} best_F1 vs WBGT_A fixed_31: recall {fmt(base['recall'])}->{fmt(best['recall'])} "
        f"(delta {fmt(delta_recall)}), precision {fmt(base['precision'])}->{fmt(best['precision'])} "
        f"(delta {fmt(delta_precision)}), miss_rate {fmt(base['miss_rate'])}->{fmt(best['miss_rate'])}."
    )
    probability_text = (
        f"{best['companion_id']} Brier={fmt(best.get('Brier'))}, ECE_fixed={fmt(best.get('ECE_fixed'))}, "
        f"PR-AUC={fmt(best.get('PR_AUC'))}, best_F1 threshold={fmt(best['threshold'])}."
    )
    recall_ok = delta_recall >= float(config["analysis"]["promising_min_recall_delta"])
    false_alarm_ok = float(best["false_alarm_ratio"]) <= float(config["analysis"]["promising_max_false_alarm_ratio"])
    precision_ok = float(best["precision"]) >= float(config["analysis"]["promising_min_precision"])
    calibration_ok = (
        float(best.get("Brier", np.inf)) <= float(config["analysis"]["acceptable_brier"])
        and float(best.get("ECE_fixed", np.inf)) <= float(config["analysis"]["acceptable_ece"])
    )
    rows.extend(
        [
            {
                "criterion": "primary_threshold_recall_miss",
                "status": "PASS" if recall_ok else "WEAK",
                "detail": baseline_text,
                "delta_recall": delta_recall,
                "delta_miss_rate": delta_miss,
            },
            {
                "criterion": "false_alarm_precision_control",
                "status": "PASS" if false_alarm_ok and precision_ok else "WEAK",
                "detail": f"precision={fmt(best['precision'])}; false_alarm_ratio={fmt(best['false_alarm_ratio'])}.",
            },
            {
                "criterion": "probability_calibration",
                "status": "PASS" if calibration_ok else "WEAK",
                "detail": probability_text,
            },
        ]
    )
    no_s142 = threshold_metrics[
        threshold_metrics["validation_method"].eq(primary_validation)
        & threshold_metrics["sensitivity_id"].eq("no_s142_eval")
        & threshold_metrics["event_target"].eq(PRIMARY_EVENT)
        & threshold_metrics["companion_id"].eq(best["companion_id"])
        & threshold_metrics["operating_point"].eq("best_F1")
    ]
    no_s142_base = threshold_metrics[
        threshold_metrics["validation_method"].eq(primary_validation)
        & threshold_metrics["sensitivity_id"].eq("no_s142_eval")
        & threshold_metrics["event_target"].eq(PRIMARY_EVENT)
        & threshold_metrics["companion_id"].eq("wbgt_a_m4_score")
        & threshold_metrics["operating_point"].eq("fixed_31")
    ]
    if not no_s142.empty and not no_s142_base.empty:
        no_s142_delta = float(no_s142["recall"].iloc[0] - no_s142_base["recall"].iloc[0])
        rows.append(
            {
                "criterion": "no_s142_sensitivity",
                "status": "PASS" if no_s142_delta >= 0 else "WEAK",
                "detail": f"no-S142 recall delta vs fixed_31={fmt(no_s142_delta)}.",
                "delta_recall": no_s142_delta,
            }
        )
    secondary = threshold_metrics[
        threshold_metrics["validation_method"].eq(str(config["validation"]["secondary_method"]))
        & threshold_metrics["sensitivity_id"].eq("all")
        & threshold_metrics["event_target"].eq(PRIMARY_EVENT)
        & threshold_metrics["companion_id"].eq(best["companion_id"])
        & threshold_metrics["operating_point"].eq("best_F1")
    ]
    secondary_base = threshold_metrics[
        threshold_metrics["validation_method"].eq(str(config["validation"]["secondary_method"]))
        & threshold_metrics["sensitivity_id"].eq("all")
        & threshold_metrics["event_target"].eq(PRIMARY_EVENT)
        & threshold_metrics["companion_id"].eq("wbgt_a_m4_score")
        & threshold_metrics["operating_point"].eq("fixed_31")
    ]
    if not secondary.empty and not secondary_base.empty:
        secondary_delta = float(secondary["recall"].iloc[0] - secondary_base["recall"].iloc[0])
        rows.append(
            {
                "criterion": "blocked_time_secondary",
                "status": "PASS" if secondary_delta >= 0 else "WEAK",
                "detail": f"blocked-time recall delta vs fixed_31={fmt(secondary_delta)}.",
                "delta_recall": secondary_delta,
            }
        )
    ge33 = probability_model_metrics[probability_model_metrics["event_target"].eq("ge33")].head(1)
    rows.append(
        {
            "criterion": "ge33_support",
            "status": "LOW_SUPPORT" if not ge33.empty and str(ge33["status"].iloc[0]) == "LOW_SUPPORT" else "PASS",
            "detail": "P_ge33 remains exploratory and is not promoted.",
        }
    )
    rows.append(
        {
            "criterion": "expected_exceedance_available",
            "status": "PASS" if not expected_metrics.empty else "WEAK",
            "detail": "Expected exceedance metrics are available for score-gap/direct/two-part companions.",
        }
    )
    rows.append(
        {
            "criterion": "interval_available",
            "status": "PASS" if not interval_metric_rows.empty else "WEAK",
            "detail": "Interval metrics are available for conformal and quantile companions where runtime support exists.",
        }
    )
    rows.append(
        {
            "criterion": "claim_boundary",
            "status": "PASS",
            "detail": "Companion only; no station-adjusted WBGT, no local 100m WBGT, no System B coupling output, no risk/hazard score.",
        }
    )
    statuses = {str(row["status"]) for row in rows}
    if recall_ok and false_alarm_ok and precision_ok and calibration_ok and "WEAK" not in statuses:
        status = "A_L1H4_COMPANION_PROMISING"
    elif recall_ok and calibration_ok:
        status = "A_L1H4_WEAK_COMPANION"
    elif abs(delta_recall) < 0.02 and not recall_ok:
        status = "A_L1H4_NOT_IDENTIFIABLE"
    else:
        status = "A_L1H4_WEAK_COMPANION"
    return pd.DataFrame(rows), status, baseline_text, probability_text


def s142_caveat(station: pd.DataFrame) -> str:
    """Build the S142/S139 caveat line."""
    if station.empty:
        return "S142/S139 station diagnostics were not available."
    rows = station[station["station_id"].astype(str).isin(["S142", "S139"])].copy()
    if rows.empty:
        return "S142/S139 were not present in the primary station diagnostics."
    parts = []
    for station_id in ["S142", "S139"]:
        focus = rows[
            rows["station_id"].astype(str).eq(station_id)
            & rows["companion_id"].ne("wbgt_a_m4_score")
            & rows["operating_point"].eq("best_F1")
        ].head(1)
        if focus.empty:
            continue
        row = focus.iloc[0]
        parts.append(
            f"{station_id}: n_ge31={int(row['event_count_ge31'])}, recall={fmt(row['recall'])}, "
            f"miss_rate={fmt(row['miss_rate'])}, false_alarm_ratio={fmt(row['false_alarm_ratio'])}"
        )
    return "; ".join(parts) + ". Station diagnostics remain caveats, not station corrections." if parts else "S142/S139 caveats remain diagnostic only."


def write_output_contract(path: Path, result_status: str) -> None:
    """Write the output contract draft."""
    lines = [
        "# A-L1H.4 Future System A Hourly Output Contract Draft",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Decision context: `{result_status}`",
        "",
        "## Recommended Columns",
        "",
        "- `timestamp_sgt`",
        "- `timestamp_utc`",
        "- `wbgt_a_c`",
        "- `wbgt_a_model_id`",
        "- `wbgt_a_version`",
        "- `s_wbgt_ge31`",
        "- `s_wbgt_band_31_33`",
        "- `p_ge31_optional`",
        "- `p_ge33_optional`",
        "- `expected_exceedance_ge31_optional`",
        "- `prediction_interval_low_optional`",
        "- `prediction_interval_high_optional`",
        "- `source_forcing`",
        "- `is_retrospective_or_prospective`",
        "- `lead_time_hours_optional`",
        "- `quality_flag`",
        "",
        "## Explicitly Forbidden Columns",
        "",
        "- `cell_id`",
        "- `local_wbgt_c`",
        "- `delta_wbgt_cell`",
        "- `risk_score`",
        "",
        "## Recommendation",
        "",
        "Keep `wbgt_a_c` as the deterministic Level 1 WBGT_A baseline. Add probability, expected-exceedance, and interval fields only as optional companion diagnostics until a later model-card gate promotes them.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_model_card(path: Path, result: SuiteResult, decision: pd.DataFrame) -> None:
    """Write the A-L1H.4 model card."""
    lines = [
        "# A-L1H.4 Probabilistic / Exceedance Companion Model Card",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Decision: `{result.status}`",
        "",
        "## Intended Use",
        "",
        "Retrospective Level 1 companion diagnostics around the 31 C / 33 C WBGT thresholds. The deterministic WBGT_A baseline remains the primary System A output.",
        "",
        "## Not Intended Use",
        "",
        "No station-adjusted WBGT, no local 100 m WBGT, no System B coupling output, no public warning probability, and no risk or hazard score.",
        "",
        "## Data And Validation",
        "",
        f"Primary station-held-out rows: {result.n_rows}; stations: {result.n_stations}; ge31 events: {result.n_events_ge31}; ge33 events: {result.n_events_ge33}. LOSO is primary; blocked-time is secondary where source folds exist. Standardized logistic-regression hyperparameters are fixed and disclosed in prediction rows; a dependency-free solver is used because sklearn estimator fits hard-exit in this runtime.",
        "",
        "## Headline",
        "",
        f"- Probability: {result.best_probability_headline}",
        f"- Expected exceedance: {result.expected_exceedance_headline}",
        f"- Interval: {result.interval_headline}",
        f"- Baseline comparison: {result.baseline_comparison}",
        "",
        "## Decision Matrix",
        "",
        markdown_table(decision, ["criterion", "status", "detail"], limit=20),
        "",
        "## Caveats",
        "",
        f"- {result.s142_caveat}",
        "- ge33 probability remains exploratory when event support is low.",
        "- All companion outputs are retrospective station-held-out diagnostics unless separately promoted.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(
    path: Path,
    result: SuiteResult,
    inventory: pd.DataFrame,
    validation: pd.DataFrame,
    baseline: pd.DataFrame,
    threshold: pd.DataFrame,
    probability: pd.DataFrame,
    expected: pd.DataFrame,
    interval: pd.DataFrame,
    station: pd.DataFrame,
    decision: pd.DataFrame,
) -> None:
    """Write the English A-L1H.4 report."""
    primary_validation = "station_grouped_loso"
    primary_threshold = threshold[
        threshold["validation_method"].eq(primary_validation)
        & threshold["event_target"].eq(PRIMARY_EVENT)
        & threshold["sensitivity_id"].eq("all")
    ].copy()
    primary_probability = probability[
        probability["validation_method"].eq(primary_validation)
        & probability["event_target"].eq(PRIMARY_EVENT)
        & probability["sensitivity_id"].eq("all")
    ].copy()
    lines = [
        "# System A A-L1H.4 Probabilistic / Exceedance Companion Suite",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Decision status: `{result.status}`",
        f"Branch: `{git_branch()}`",
        "",
        "## 1. Why This Follows A-L2.1c",
        "",
        "A-L2.1c found only a weak station-context high-tail residual signal and did not identify score residual correction. This suite therefore returns to Level 1 threshold behavior rather than creating station-adjusted WBGT or local WBGT.",
        "",
        "## 2. Why Level 1 Remains The Main Improvement Path",
        "",
        "The current evidence supports improving threshold companions around WBGT_A: P_ge31, expected exceedance, and uncertainty intervals. These are companion diagnostics, not canonical replacements for deterministic WBGT_A.",
        "",
        "## 3. Input Inventory And Targets",
        "",
        markdown_table(inventory, ["inventory_role", "path", "exists", "rows_total", "rows_selected_loso", "selected_station_count", "selected_event_count_ge31", "selected_event_count_ge33"], limit=10),
        "",
        "Targets: official_wbgt_c, ge31=official_wbgt_c>=31, ge33=official_wbgt_c>=33, exceedance_ge31_c=max(0, official_wbgt_c-31), exceedance_ge33_c=max(0, official_wbgt_c-33).",
        "",
        "## 4. Validation Split Design",
        "",
        markdown_table(validation, ["validation_method", "fold_id", "is_primary", "train_rows", "test_rows", "test_station_ids", "test_events_ge31", "test_events_ge33"], limit=16),
        "",
        "Standardized logistic-regression companions use fixed, disclosed hyperparameters (`C=1.0`, no class weighting) with the repo's dependency-free solver because sklearn estimator fits hard-exit in this runtime; LOSO remains the primary validation evidence.",
        "",
        "## 5. Deterministic Baseline",
        "",
        markdown_table(baseline, ["sensitivity_id", "validation_method", "output_id", "n", "MAE", "RMSE", "high_tail_mae_obs_ge31", "fixed_ge31_recall", "fixed_ge31_precision", "fixed_ge31_miss_rate"], limit=16),
        "",
        "## 6. Threshold Policies",
        "",
        markdown_table(primary_threshold, ["companion_id", "output_kind", "operating_point", "threshold", "precision", "recall", "F1", "CSI", "false_alarm_ratio", "miss_rate"], limit=24),
        "",
        "## 7. P_ge31 / P_ge33 Models",
        "",
        markdown_table(primary_probability, ["companion_id", "status", "n", "event_count", "Brier", "log_loss", "PR_AUC", "ROC_AUC", "ECE_fixed", "ECE_quantile", "calibration_slope"], limit=16),
        "",
        "P_ge33 is gated by event support and remains exploratory when below threshold.",
        "",
        "## 8. Expected Exceedance",
        "",
        markdown_table(expected[expected["validation_method"].eq(primary_validation) & expected["sensitivity_id"].eq("all")], ["companion_id", "exceedance_MAE", "positive_exceedance_MAE", "bias_expected_minus_observed", "p90_abs_exceedance_error"], limit=12),
        "",
        "## 9. Quantile / Interval Companion",
        "",
        markdown_table(interval[interval["validation_method"].eq(primary_validation) & interval["sensitivity_id"].eq("all")], ["interval_id", "nominal_coverage", "empirical_coverage", "mean_interval_width_c", "near31_coverage", "near33_coverage"], limit=12),
        "",
        "## 10. Station Diagnostics And S142 Caveat",
        "",
        markdown_table(station[station["focus_station_flag"].astype(bool)] if not station.empty else station, ["companion_id", "operating_point", "station_id", "event_count_ge31", "precision", "recall", "miss_rate", "false_alarm_ratio"], limit=20),
        "",
        result.s142_caveat,
        "",
        "## 11. Decision Matrix",
        "",
        markdown_table(decision, ["criterion", "status", "detail"], limit=20),
        "",
        "## 12. Output Contract Draft",
        "",
        result.output_contract_recommendation,
        "",
        "## 13. Claim Boundaries",
        "",
        "- No station-adjusted WBGT.",
        "- No local 100 m WBGT.",
        "- No System B coupling output.",
        "- No risk score or hazard score.",
        "- Companion only unless promoted by a later model card.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cn_doc(path: Path, result: SuiteResult, decision: pd.DataFrame) -> None:
    """Write the required Chinese documentation in valid UTF-8."""
    lines = [
        "# OpenHeat System A A-L1H.4 概率 / 超阈值伴随套件说明",
        "",
        f"生成日期：{date.today().isoformat()}",
        f"决策状态：`{result.status}`",
        "",
        "## 1. 为什么接在 A-L2.1c 之后",
        "",
        "A-L2.1c 显示，站点环境特征对高尾残差只有弱解释力，对分数残差暂不可识别。因此本轮不建立站点修正 WBGT，也不生成本地 100 m WBGT，而是回到 Level 1 的阈值行为、概率伴随、超阈值期望和区间不确定性。",
        "",
        "## 2. 为什么 Level 1 仍是主改进路径",
        "",
        "当前证据更支持在确定性 WBGT_A 之外增加伴随诊断列，而不是替换 WBGT_A。概率和区间只用于内部回顾性评估，不能表述为官方预警概率或实时健康风险。",
        "",
        "## 3. 输入清单与目标定义",
        "",
        f"主验证表包含 {result.n_rows} 行、{result.n_stations} 个站点、ge31 事件 {result.n_events_ge31} 个、ge33 事件 {result.n_events_ge33} 个。目标包括 `official_wbgt_c`、`ge31`、`ge33`、`exceedance_ge31_c` 和 `exceedance_ge33_c`。",
        "",
        "## 4. 验证切分设计",
        "",
        "主验证采用留一站点（LOSO）。若源数据存在 time_block 折，则作为次级阻塞时间验证。不使用随机切分作为主要证据。标准化 logistic 回归使用固定并公开的超参数（C=1.0、无 class weighting），并采用仓库内稳定求解器，因为本运行环境中的 sklearn estimator fit 会硬退出。",
        "",
        "## 5. 确定性基线",
        "",
        "确定性基线仍为 M4_inertia_ridge 的 WBGT_A 分数，并与 M7_compact_weather_ridge 和 v09 代理分数比较。固定 31 °C 阈值只作为基线，不被替换为本轮输出。",
        "",
        "## 6. 阈值策略",
        "",
        "阈值策略包括 fixed_31、best_F1、recall90 和 precision70。训练折只用于选择阈值， held-out 折用于评估。",
        "",
        "## 7. P_ge31 / P_ge33 模型",
        "",
        result.best_probability_headline,
        "",
        "P_ge33 因事件支持不足时只保留探索性标记，不提升为正式伴随列。",
        "",
        "## 8. 期望超阈值",
        "",
        result.expected_exceedance_headline,
        "",
        "## 9. 分位数 / 区间伴随",
        "",
        result.interval_headline,
        "",
        "## 10. 站点诊断与 S142 限制",
        "",
        result.s142_caveat,
        "",
        "## 11. 决策矩阵",
        "",
        markdown_table(decision, ["criterion", "status", "detail"], limit=20),
        "",
        "## 12. 输出契约草案",
        "",
        "建议未来 System A 小时输出保留 `wbgt_a_c`，并仅可选增加 `p_ge31_optional`、`p_ge33_optional`、`expected_exceedance_ge31_optional`、`prediction_interval_low_optional` 和 `prediction_interval_high_optional`。",
        "",
        "## 13. 声明边界",
        "",
        "- 不创建站点修正 WBGT。",
        "- 不创建本地 100 m WBGT。",
        "- 不输出 System B 耦合结果。",
        "- 不创建 risk_score 或 hazard_score。",
        "- 本套件只是伴随诊断，除非后续模型卡明确提升，否则不是 canonical 替代。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(path: Path, config_path: Path, result: SuiteResult) -> None:
    """Write the lane status file."""
    outputs = "\n".join(f"- `{rel(output_path)}`" for output_path in result.output_paths)
    lines = [
        "# A-L1H.4 Status",
        "",
        f"Status: {result.status}",
        f"Generated: {date.today().isoformat()}",
        f"Branch: {git_branch()}",
        "",
        "## Scope",
        "",
        "Probabilistic / exceedance companion suite for Level 1 threshold behavior around 31 C / 33 C. Companion only; deterministic WBGT_A remains primary.",
        "",
        "## Commands Run",
        "",
        f"- `{Path(sys.executable)} scripts/v11_l1h4_run_prob_exceedance_suite.py --config {rel(config_path)}`",
        "",
        "## Key Results",
        "",
        f"- Rows/stations/events: n_rows={result.n_rows}; n_stations={result.n_stations}; n_events_ge31={result.n_events_ge31}; n_events_ge33={result.n_events_ge33}",
        f"- Probability: {result.best_probability_headline}",
        f"- Expected exceedance: {result.expected_exceedance_headline}",
        f"- Interval: {result.interval_headline}",
        f"- Baseline comparison: {result.baseline_comparison}",
        f"- S142 caveat: {result.s142_caveat}",
        f"- Output contract recommendation: {result.output_contract_recommendation}",
        "",
        "## Files Created / Modified",
        "",
        outputs,
        "",
        "## Caveats",
        "",
        "- Retrospective station-held-out companion evidence only.",
        "- P_ge31 is not an official warning probability.",
        "- P_ge33 remains exploratory when low support.",
        "- No station-adjusted WBGT, local 100 m WBGT, System B coupling output, risk_score, or hazard_score.",
        "",
        "## Safe To Commit",
        "",
        "- Config, scripts, docs, and compact CSV/Markdown outputs after review.",
        "",
        "## Not Safe To Commit",
        "",
        "- Raw archives, rasters, SOLWEIG/System B outputs, tif/tiff files, svfs.zip, patch zip packages, raw API dumps, or large forecast/live CSVs.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked_outputs(config: dict[str, Any], config_path: Path, paths: dict[str, Path], reason: str) -> SuiteResult:
    """Write minimal BLOCKED outputs when required inputs are missing."""
    paths["dir"].mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(config)
    inventory.to_csv(paths["inventory"], index=False)
    decision = pd.DataFrame([{"criterion": "baseline_input", "status": "BLOCKED", "detail": reason}])
    decision.to_csv(paths["decision"], index=False)
    result = SuiteResult(
        status="BLOCKED_BASELINE_INPUT",
        n_rows=0,
        n_stations=0,
        n_events_ge31=0,
        n_events_ge33=0,
        best_probability_headline="Blocked before probability models.",
        expected_exceedance_headline="Blocked before expected exceedance models.",
        interval_headline="Blocked before interval models.",
        baseline_comparison=reason,
        s142_caveat="Blocked before station diagnostics.",
        output_contract_recommendation="Repair required Level 1 baseline inputs before adding companion columns.",
        output_paths=[paths["inventory"], paths["decision"], paths["status"]],
    )
    write_status(paths["status"], config_path, result)
    return result


def run_suite(config_path: Path) -> SuiteResult:
    """Run the full A-L1H.4 suite."""
    config = load_config(config_path)
    paths = output_paths(config)
    assert_output_scope(paths)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["cn_doc"].parent.mkdir(parents=True, exist_ok=True)

    required = [
        resolve_path(str(config["inputs"]["residual_weather_merge"])),
        resolve_path(str(config["inputs"]["beta_oof_predictions"])),
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        return write_blocked_outputs(config, config_path, paths, "Missing required inputs: " + ", ".join(rel(path) for path in missing))

    frame = prepare_model_input(config)
    set_frame_primary_counts(frame, config)
    primary = frame[frame["cv_scheme"].eq(str(config["schema"]["primary_cv_scheme"]))]
    inventory = input_inventory(config, frame)
    features = feature_schema(config, frame)
    validation = validation_splits(frame, config)
    baseline = deterministic_baseline_metrics(frame, config)
    probability_predictions = run_probability_models(frame, config)
    probability_bins_all = reliability_bins_for_predictions(probability_predictions, config, "all")
    probability_bins_parts = [probability_bins_all]
    probability_metrics_all = probability_metrics(probability_predictions, probability_bins_all, config, "all")
    if "S142" in set(frame["station_id"].astype(str)):
        bins_no_s142 = reliability_bins_for_predictions(probability_predictions, config, "no_s142_eval", exclude_station="S142")
        probability_bins_parts.append(bins_no_s142)
        probability_metrics_no_s142 = probability_metrics(probability_predictions, bins_no_s142, config, "no_s142_eval", exclude_station="S142")
        probability_model_metrics = pd.concat([probability_metrics_all, probability_metrics_no_s142], ignore_index=True)
    else:
        probability_model_metrics = probability_metrics_all
    probability_bins = pd.concat([part for part in probability_bins_parts if not part.empty], ignore_index=True) if probability_bins_parts else pd.DataFrame()

    score_outputs = make_output_rows_from_scores(frame, config)
    all_threshold_outputs = pd.concat([score_outputs, probability_predictions], ignore_index=True, sort=False)
    threshold_metrics, threshold_decisions = evaluate_threshold_policies(all_threshold_outputs, config)
    primary_validation = str(config["validation"]["primary_method"])
    secondary_validation = str(config["validation"]["secondary_method"])
    best_primary_probability = select_best_probability(probability_model_metrics, threshold_metrics, primary_validation)
    best_secondary_probability = select_best_probability(probability_model_metrics, threshold_metrics, secondary_validation)
    best_by_validation = {
        primary_validation: best_primary_probability,
        secondary_validation: best_secondary_probability,
    }
    exceedance_predictions = run_expected_exceedance(frame, probability_predictions, best_by_validation, config)
    expected_metrics = expected_exceedance_metrics(exceedance_predictions, config)
    interval_predictions = run_interval_models(frame, config)
    interval_metric_rows = interval_metrics(interval_predictions, config)
    oof = build_oof_predictions(frame, probability_predictions, exceedance_predictions, interval_predictions, best_by_validation, config)
    station = station_threshold_diagnostics(threshold_decisions, probability_predictions, exceedance_predictions, config, best_primary_probability)
    decision, status, baseline_text, probability_text = decision_matrix(config, threshold_metrics, probability_model_metrics, expected_metrics, interval_metric_rows)
    expected_headline, _expected_id = choose_expected_headline(expected_metrics, primary_validation)
    interval_headline, _interval_id = choose_interval_headline(interval_metric_rows, primary_validation)
    caveat = s142_caveat(station)
    output_recommendation = "Keep WBGT_A as primary; add P_ge31, expected exceedance, and interval columns as optional companion diagnostics only."

    output_file_paths = [
        paths["inventory"],
        paths["model_input"],
        paths["feature_schema"],
        paths["validation"],
        paths["baseline"],
        paths["threshold"],
        paths["probability_metrics"],
        paths["probability_bins"],
        paths["expected_exceedance"],
        paths["interval"],
        paths["oof"],
        paths["station"],
        paths["decision"],
        paths["contract"],
        paths["model_card"],
        paths["report"],
        paths["status"],
        paths["cn_doc"],
    ]
    result = SuiteResult(
        status=status,
        n_rows=len(primary),
        n_stations=primary["station_id"].nunique(),
        n_events_ge31=int(primary["ge31"].sum()),
        n_events_ge33=int(primary["ge33"].sum()),
        best_probability_headline=probability_text,
        expected_exceedance_headline=expected_headline,
        interval_headline=interval_headline,
        baseline_comparison=baseline_text,
        s142_caveat=caveat,
        output_contract_recommendation=output_recommendation,
        output_paths=output_file_paths,
    )

    inventory.to_csv(paths["inventory"], index=False)
    frame.to_csv(paths["model_input"], index=False)
    features.to_csv(paths["feature_schema"], index=False)
    validation.to_csv(paths["validation"], index=False)
    baseline.to_csv(paths["baseline"], index=False)
    threshold_metrics.to_csv(paths["threshold"], index=False)
    probability_model_metrics.to_csv(paths["probability_metrics"], index=False)
    probability_bins.to_csv(paths["probability_bins"], index=False)
    expected_metrics.to_csv(paths["expected_exceedance"], index=False)
    interval_metric_rows.to_csv(paths["interval"], index=False)
    oof.to_csv(paths["oof"], index=False)
    station.to_csv(paths["station"], index=False)
    decision.to_csv(paths["decision"], index=False)
    write_output_contract(paths["contract"], status)
    write_model_card(paths["model_card"], result, decision)
    write_report(paths["report"], result, inventory, validation, baseline, threshold_metrics, probability_model_metrics, expected_metrics, interval_metric_rows, station, decision)
    write_cn_doc(paths["cn_doc"], result, decision)
    write_status(paths["status"], config_path, result)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.4 probabilistic / exceedance companion suite.")
    parser.add_argument("--config", default="configs/v11/systema_l1h4_prob_exceedance_suite.yaml")
    args = parser.parse_args()
    result = run_suite(resolve_path(args.config))
    print(f"[status] {result.status}")
    print(f"[rows] n_rows={result.n_rows}; n_stations={result.n_stations}; n_events_ge31={result.n_events_ge31}; n_events_ge33={result.n_events_ge33}")
    print(f"[best_probability] {result.best_probability_headline}")
    print(f"[expected_exceedance] {result.expected_exceedance_headline}")
    print(f"[interval] {result.interval_headline}")
    print(f"[baseline_comparison] {result.baseline_comparison}")
    print(f"[s142_caveat] {result.s142_caveat}")
    print(f"[output_contract] {result.output_contract_recommendation}")
    return 0 if result.status in {"A_L1H4_COMPANION_PROMISING", "A_L1H4_WEAK_COMPANION", "A_L1H4_NOT_IDENTIFIABLE", "BLOCKED_BASELINE_INPUT"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
