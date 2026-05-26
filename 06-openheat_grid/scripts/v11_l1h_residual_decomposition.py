#!/usr/bin/env python
"""System A A-L1H.0 high-tail residual decomposition.

Inputs:
    - configs/v11/systema_l1h_residual_decomposition.yaml
    - Existing System A OOF prediction/model-score CSVs declared in the config.

Outputs:
    - residual_input_inventory.csv
    - residual_analysis_input.csv
    - residual_by_observed_bin.csv
    - residual_by_predicted_bin.csv
    - residual_by_station.csv
    - residual_by_hour.csv
    - residual_by_regime.csv
    - ge31_miss_inventory.csv
    - ge31_false_alarm_inventory.csv
    - ge31_hit_inventory.csv
    - ge33_exploratory_inventory.csv
    - high_tail_bias_report.md

Saved metrics:
    - residual = official_wbgt_c - model_score; positive means underprediction.
    - Fixed WBGT >=31 hit/miss/false-alarm counts and precision/recall/F1.
    - Residual summaries by observed bin, predicted bin, station, hour, and
      weather-regime bins when weather columns are available.

This script consumes existing OOF predictions only. It does not train models,
calibrate probabilities, implement formula-v2, touch System B, or touch SOLWEIG.
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
OBSERVED_BIN_LABELS = ["<28", "28-29", "29-30", "30-31", "31-32", "32-33", ">=33"]
OBSERVED_BIN_EDGES = [-math.inf, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, math.inf]
PREDICTED_BIN_LABELS = ["<28", "28-29", "29-30", "30-30.5", "30.5-31", "31-32", "32-33", ">=33"]
PREDICTED_BIN_EDGES = [-math.inf, 28.0, 29.0, 30.0, 30.5, 31.0, 32.0, 33.0, math.inf]


@dataclass(frozen=True)
class Detection:
    """Detected schema columns for one candidate input."""

    target_columns: list[str]
    prediction_columns: list[str]
    model_name_columns: list[str]
    station_columns: list[str]
    time_columns: list[str]
    weather_columns: list[str]


@dataclass(frozen=True)
class AnalysisResult:
    """Paths and headline counts produced by one decomposition run."""

    status: str
    selected_input: str | None
    selected_models: list[str]
    target_column: str | None
    row_count: int
    station_count: int
    observed_ge31_count: int
    predicted_ge31_count: int
    ge31_hit_count: int
    ge31_miss_count: int
    ge31_false_alarm_count: int
    classification: str
    caveat: str
    output_paths: list[Path]


def rel(path: Path) -> str:
    """Return a repo-relative POSIX path when possible."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_config(path: Path) -> dict[str, Any]:
    """Read the YAML config for the lane."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def existing_candidates(config: dict[str, Any]) -> list[Path]:
    """Discover candidate OOF/prediction files from preferred paths and globs."""
    seen: set[Path] = set()
    candidates: list[Path] = []
    preferred = [ROOT / p for p in config["inputs"].get("preferred_paths", [])]
    for path in preferred:
        if path not in seen:
            candidates.append(path)
            seen.add(path)
    for pattern in config["inputs"].get("candidate_globs", []):
        for path in sorted(ROOT.glob(pattern)):
            if path not in seen:
                candidates.append(path)
                seen.add(path)
    return candidates


def read_columns(path: Path) -> list[str]:
    """Read CSV header columns without loading the whole file."""
    if not path.exists():
        return []
    try:
        return pd.read_csv(path, nrows=0).columns.tolist()
    except Exception:
        return []


def count_csv_rows(path: Path) -> int:
    """Count data rows in a CSV file without retaining contents."""
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return max(sum(1 for _ in f) - 1, 0)


def detect_columns(columns: list[str], aliases: dict[str, list[str]]) -> Detection:
    """Detect target, prediction, model, station, time, and weather columns."""
    col_set = set(columns)

    def exact(kind: str) -> list[str]:
        return [col for col in aliases.get(kind, []) if col in col_set]

    prediction_cols = exact("prediction")
    model_specific = [
        col for col in columns
        if col.endswith("_prediction_wbgt_c") or col.endswith("_pred_wbgt_c")
    ]
    for col in model_specific:
        if col not in prediction_cols:
            prediction_cols.append(col)

    return Detection(
        target_columns=exact("target"),
        prediction_columns=prediction_cols,
        model_name_columns=exact("model_name"),
        station_columns=exact("station"),
        time_columns=exact("time"),
        weather_columns=exact("weather"),
    )


def target_priority(path: Path, target_columns: list[str]) -> str | None:
    """Prefer hourly-max targets for threshold diagnostics."""
    path_text = rel(path)
    if "official_wbgt_c_max" in target_columns:
        return "official_wbgt_c_max"
    if "official_hourly_max_wbgt_c" in target_columns:
        return "official_hourly_max_wbgt_c"
    if "hourly_max" in path_text:
        return target_columns[0] if target_columns else None
    return target_columns[0] if target_columns else None


def prediction_priority(prediction_columns: list[str]) -> str | None:
    """Pick the canonical long-format prediction score column when present."""
    for col in ["prediction_wbgt_c", "model_score", "pred_wbgt_c", "wbgt_pred_c", "y_pred", "prediction", "oof_pred", "score"]:
        if col in prediction_columns:
            return col
    return prediction_columns[0] if prediction_columns else None


def candidate_score(path: Path, exists: bool, detection: Detection, preferred_paths: list[str]) -> tuple[int, str]:
    """Score candidate suitability for transparent input selection."""
    if not exists:
        return 0, "missing"
    score = 0
    reason_parts: list[str] = []
    path_rel = rel(path)
    if path_rel in preferred_paths:
        preference_rank = preferred_paths.index(path_rel)
        score += 100 - preference_rank * 10
        reason_parts.append(f"preferred_rank_{preference_rank + 1}")
    if "hourly_max" in path_rel:
        score += 40
        reason_parts.append("hourly_max_threshold_relevant")
    if detection.target_columns:
        score += 20
    else:
        reason_parts.append("no_detected_target")
    if detection.prediction_columns:
        score += 20
    else:
        reason_parts.append("no_detected_prediction")
    if detection.model_name_columns:
        score += 10
    else:
        reason_parts.append("no_detected_model_name")
    if detection.station_columns:
        score += 5
    if detection.time_columns:
        score += 5
    return score, "; ".join(reason_parts) or "usable_nonpreferred_candidate"


def build_input_inventory(config: dict[str, Any]) -> tuple[pd.DataFrame, Path | None]:
    """Create the candidate inventory and select the best usable input file."""
    aliases = config["column_aliases"]
    preferred_paths = config["inputs"].get("preferred_paths", [])
    rows: list[dict[str, Any]] = []
    candidate_paths = existing_candidates(config)
    best_path: Path | None = None
    best_score = -1

    for path in candidate_paths:
        exists = path.exists()
        columns = read_columns(path)
        detection = detect_columns(columns, aliases)
        score, reason = candidate_score(path, exists, detection, preferred_paths)
        usable = bool(exists and detection.target_columns and detection.prediction_columns)
        if usable and score > best_score:
            best_path = path
            best_score = score
        rows.append({
            "path": rel(path),
            "exists": "yes" if exists else "no",
            "row_count": count_csv_rows(path) if exists else 0,
            "columns": "|".join(columns),
            "detected_target_columns": "|".join(detection.target_columns),
            "detected_prediction_columns": "|".join(detection.prediction_columns),
            "detected_model_name_columns": "|".join(detection.model_name_columns),
            "detected_station_columns": "|".join(detection.station_columns),
            "detected_time_columns": "|".join(detection.time_columns),
            "detected_weather_columns": "|".join(detection.weather_columns),
            "candidate_score": score,
            "selected_for_analysis": "no",
            "reason": reason,
        })

    inventory = pd.DataFrame(rows).sort_values(["candidate_score", "path"], ascending=[False, True])
    if best_path is not None and not inventory.empty:
        inventory.loc[inventory["path"].eq(rel(best_path)), "selected_for_analysis"] = "yes"
        inventory.loc[inventory["path"].eq(rel(best_path)), "reason"] = (
            inventory.loc[inventory["path"].eq(rel(best_path)), "reason"].astype(str)
            + "; selected_existing_usable_input"
        )
    return inventory, best_path


def add_event_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add residual, error, fixed-threshold flags, event classes, and bins."""
    out = df.copy()
    out["residual_c"] = out["official_wbgt_c"] - out["model_score"]
    out["abs_error_c"] = out["residual_c"].abs()
    out["obs_ge31"] = out["official_wbgt_c"] >= 31.0
    out["pred_ge31_fixed"] = out["model_score"] >= 31.0
    out["obs_ge33"] = out["official_wbgt_c"] >= 33.0
    out["pred_ge33_fixed"] = out["model_score"] >= 33.0
    out["ge31_event_class"] = np.select(
        [
            out["obs_ge31"] & out["pred_ge31_fixed"],
            out["obs_ge31"] & ~out["pred_ge31_fixed"],
            ~out["obs_ge31"] & out["pred_ge31_fixed"],
        ],
        ["hit", "miss", "false_alarm"],
        default="true_negative",
    )
    out["observed_wbgt_bin"] = pd.cut(
        out["official_wbgt_c"],
        bins=OBSERVED_BIN_EDGES,
        labels=OBSERVED_BIN_LABELS,
        right=False,
        include_lowest=True,
    ).astype(str)
    out["predicted_score_bin"] = pd.cut(
        out["model_score"],
        bins=PREDICTED_BIN_EDGES,
        labels=PREDICTED_BIN_LABELS,
        right=False,
        include_lowest=True,
    ).astype(str)
    return out


def derive_hour(raw: pd.DataFrame, time_columns: list[str]) -> pd.Series:
    """Return hour_sgt from an hour column or parseable timestamp."""
    for col in ["hour_sgt", "hour"]:
        if col in raw.columns:
            return pd.to_numeric(raw[col], errors="coerce")
    for col in ["timestamp_sgt", "timestamp", "valid_time_sgt"]:
        if col in raw.columns:
            parsed = pd.to_datetime(raw[col], errors="coerce")
            return parsed.dt.hour
    return pd.Series(np.nan, index=raw.index)


def quantile_labels(n_bins: int) -> list[str]:
    """Labels for weather-regime quantile bins."""
    return ["low", "mid", "high"] if n_bins == 3 else ["low", "mid", "high", "very_high"]


def add_weather_regimes(df: pd.DataFrame, weather_columns: list[str], min_rows_4_bins: int) -> tuple[pd.DataFrame, list[str]]:
    """Create low/mid/high weather-regime bins for available weather columns."""
    out = df.copy()
    created: list[str] = []
    for col in weather_columns:
        if col not in out.columns:
            continue
        numeric = pd.to_numeric(out[col], errors="coerce")
        if numeric.notna().sum() < 6 or numeric.nunique(dropna=True) < 3:
            continue
        n_bins = 4 if numeric.notna().sum() >= min_rows_4_bins and numeric.nunique(dropna=True) >= 4 else 3
        try:
            binned = pd.qcut(numeric, q=n_bins, labels=quantile_labels(n_bins), duplicates="drop")
        except ValueError:
            continue
        bin_col = {
            "shortwave_radiation": "shortwave_bin",
            "relative_humidity_2m": "humidity_bin",
            "wind_speed_10m": "wind_bin",
            "temperature_2m": "temperature_bin",
        }.get(col, f"{col}_bin")
        out[bin_col] = binned.astype("object").where(binned.notna(), "missing")
        created.append(bin_col)

    key_bins = [col for col in ["shortwave_bin", "humidity_bin", "wind_bin", "temperature_bin"] if col in out.columns]
    if len(key_bins) >= 3:
        out["combined_regime"] = out[key_bins].astype(str).agg("|".join, axis=1)
        created.append("combined_regime")
    return out, created


def prepare_analysis_input(config: dict[str, Any], selected_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Normalize the selected OOF file into the lane analysis schema."""
    raw = pd.read_csv(selected_path)
    aliases = config["column_aliases"]
    detection = detect_columns(raw.columns.tolist(), aliases)
    target_col = target_priority(selected_path, detection.target_columns)
    pred_col = prediction_priority(detection.prediction_columns)
    model_col = detection.model_name_columns[0] if detection.model_name_columns else None
    station_col = detection.station_columns[0] if detection.station_columns else None
    if not target_col or not pred_col:
        raise ValueError("Required target/prediction columns could not be detected from selected input.")

    primary_models = config["analysis"].get("primary_models", [])
    comparator_models = config["analysis"].get("comparator_models", [])
    selected_models = primary_models + [m for m in comparator_models if m not in primary_models]

    if model_col:
        raw = raw[raw[model_col].astype(str).isin(selected_models)].copy()
    else:
        raw = raw.copy()
        raw["model_name"] = Path(pred_col).stem
        model_col = "model_name"

    if raw.empty:
        raise ValueError(f"Selected input has none of the requested models: {selected_models}")

    keep_cols = [col for col in raw.columns if col in set(detection.weather_columns)]
    normalized = pd.DataFrame({
        "source_path": rel(selected_path),
        "row_id": raw["row_id"] if "row_id" in raw.columns else raw.index,
        "model_name": raw[model_col].astype(str),
        "official_wbgt_c": pd.to_numeric(raw[target_col], errors="coerce"),
        "model_score": pd.to_numeric(raw[pred_col], errors="coerce"),
        "station_id": raw[station_col].astype(str) if station_col else "",
        "hour_sgt": derive_hour(raw, detection.time_columns),
    })
    for col in ["timestamp_sgt", "timestamp", "valid_time_sgt", "date", "cv_scheme", "fold"]:
        if col in raw.columns:
            normalized[col] = raw[col]
    for col in keep_cols:
        normalized[col] = pd.to_numeric(raw[col], errors="coerce")

    normalized = normalized[normalized["official_wbgt_c"].notna() & normalized["model_score"].notna()].copy()
    normalized = add_event_fields(normalized)
    normalized, regime_cols = add_weather_regimes(
        normalized,
        detection.weather_columns,
        int(config["analysis"].get("quantile_regime_min_rows_4_bins", 120)),
    )

    meta = {
        "target_column": target_col,
        "prediction_column": pred_col,
        "model_column": model_col,
        "station_column": station_col,
        "time_columns": detection.time_columns,
        "weather_columns": detection.weather_columns,
        "regime_columns": regime_cols,
        "selected_models": sorted(normalized["model_name"].dropna().astype(str).unique().tolist()),
    }
    return normalized, meta


def summary_table(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Build a fixed residual summary table for any grouping columns."""
    rows: list[dict[str, Any]] = []
    for keys, group in df.groupby(group_cols, dropna=False, observed=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: key for col, key in zip(group_cols, keys)}
        obs_ge31 = group["obs_ge31"]
        pred_ge31 = group["pred_ge31_fixed"]
        hit = group["ge31_event_class"].eq("hit")
        miss = group["ge31_event_class"].eq("miss")
        false_alarm = group["ge31_event_class"].eq("false_alarm")
        row.update({
            "n": int(len(group)),
            "n_obs_ge31": int(obs_ge31.sum()),
            "n_pred_ge31": int(pred_ge31.sum()),
            "n_ge31_hit": int(hit.sum()),
            "n_ge31_miss": int(miss.sum()),
            "n_ge31_false_alarm": int(false_alarm.sum()),
            "mean_official_wbgt_c": group["official_wbgt_c"].mean(),
            "mean_model_score": group["model_score"].mean(),
            "mean_residual_c": group["residual_c"].mean(),
            "median_residual_c": group["residual_c"].median(),
            "p75_residual_c": group["residual_c"].quantile(0.75),
            "p90_residual_c": group["residual_c"].quantile(0.90),
            "mean_abs_error_c": group["abs_error_c"].mean(),
            "p90_abs_error_c": group["abs_error_c"].quantile(0.90),
            "max_abs_error_c": group["abs_error_c"].max(),
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols)


def station_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build station-level residual diagnostics with S142/S139 markers."""
    base = summary_table(df, ["model_name", "station_id"])
    high_tail = (
        df[df["obs_ge31"]]
        .groupby(["model_name", "station_id"], dropna=False)["residual_c"]
        .agg(high_tail_obs_ge31_mean_residual_c="mean", high_tail_obs_ge31_p90_residual_c=lambda s: s.quantile(0.90))
        .reset_index()
    )
    out = base.merge(high_tail, on=["model_name", "station_id"], how="left")
    out["is_S142"] = out["station_id"].astype(str).eq("S142")
    out["is_S139"] = out["station_id"].astype(str).eq("S139")
    out["ge31_miss_rate_among_observed"] = np.where(
        out["n_obs_ge31"] > 0,
        out["n_ge31_miss"] / out["n_obs_ge31"],
        np.nan,
    )
    out["false_alarm_count"] = out["n_ge31_false_alarm"]
    out["sample_size_note"] = np.where(out["n"] < 30, "small_n", "")
    column_order = [
        "model_name", "station_id", "is_S142", "is_S139", "n", "n_obs_ge31",
        "n_pred_ge31", "n_ge31_hit", "n_ge31_miss", "ge31_miss_rate_among_observed",
        "false_alarm_count", "mean_official_wbgt_c", "mean_model_score",
        "mean_residual_c", "median_residual_c", "p75_residual_c", "p90_residual_c",
        "mean_abs_error_c", "p90_abs_error_c", "max_abs_error_c",
        "high_tail_obs_ge31_mean_residual_c", "high_tail_obs_ge31_p90_residual_c",
        "sample_size_note",
    ]
    return out[column_order].sort_values(["model_name", "mean_residual_c"], ascending=[True, False])


def regime_summary(df: pd.DataFrame, regime_cols: list[str]) -> pd.DataFrame:
    """Build weather-regime summaries or a limitation row if no regimes exist."""
    if not regime_cols:
        limited = summary_table(df.assign(regime_variable="no_weather_regime", regime_bin="weather_columns_absent"), ["model_name", "regime_variable", "regime_bin"])
        return limited
    parts: list[pd.DataFrame] = []
    for col in regime_cols:
        tmp = df.copy()
        tmp["regime_variable"] = col
        tmp["regime_bin"] = tmp[col].astype(str)
        parts.append(summary_table(tmp, ["model_name", "regime_variable", "regime_bin"]))
    return pd.concat(parts, ignore_index=True)


def fixed_metrics(df: pd.DataFrame, model: str) -> dict[str, Any]:
    """Fixed 31C threshold metrics for one model."""
    sub = df[df["model_name"].eq(model)]
    hits = int(sub["ge31_event_class"].eq("hit").sum())
    misses = int(sub["ge31_event_class"].eq("miss").sum())
    false_alarms = int(sub["ge31_event_class"].eq("false_alarm").sum())
    precision = hits / (hits + false_alarms) if hits + false_alarms else np.nan
    recall = hits / (hits + misses) if hits + misses else np.nan
    f1 = 2 * precision * recall / (precision + recall) if pd.notna(precision) and pd.notna(recall) and precision + recall else np.nan
    return {
        "observed_ge31": int(sub["obs_ge31"].sum()),
        "predicted_ge31": int(sub["pred_ge31_fixed"].sum()),
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def classify_pattern(df: pd.DataFrame, station: pd.DataFrame, regime: pd.DataFrame, primary_model: str) -> tuple[str, str]:
    """Return a cautious preliminary diagnostic classification."""
    sub = df[df["model_name"].eq(primary_model)].copy()
    obs_events = sub[sub["obs_ge31"]]
    if obs_events.empty:
        return "blocked_no_observed_ge31", "No observed ge31 rows were available for the primary model."

    compression_share = obs_events["predicted_score_bin"].isin(["29-30", "30-30.5", "30.5-31"]).mean()
    obs_bin_summary = summary_table(sub, ["model_name", "observed_wbgt_bin"])
    high_bins = obs_bin_summary[obs_bin_summary["observed_wbgt_bin"].isin(["31-32", "32-33", ">=33"])]
    low_bins = obs_bin_summary[obs_bin_summary["observed_wbgt_bin"].isin(["29-30", "30-31"])]
    residual_increases = bool(
        not high_bins.empty
        and not low_bins.empty
        and high_bins["mean_residual_c"].mean() > low_bins["mean_residual_c"].mean() + 0.25
    )

    station_sub = station[station["model_name"].eq(primary_model)].copy()
    station_range = station_sub["mean_residual_c"].max() - station_sub["mean_residual_c"].min() if not station_sub.empty else 0.0
    station_signal = bool(pd.notna(station_range) and station_range >= 0.75)

    weather_limited = regime["regime_variable"].astype(str).eq("no_weather_regime").all()
    regime_signal = False
    if not weather_limited:
        regime_sub = regime[regime["model_name"].eq(primary_model)].copy()
        if not regime_sub.empty:
            regime_range = regime_sub.groupby("regime_variable")["mean_residual_c"].agg(lambda s: s.max() - s.min())
            regime_signal = bool((regime_range >= 0.75).any())

    compression_signal = compression_share >= 0.50 or residual_increases
    if compression_signal and station_signal:
        classification = "mixed: global Level 1 score compression with station-specific residual bias"
    elif compression_signal and regime_signal:
        classification = "mixed: global Level 1 score compression with weather-regime interaction"
    elif station_signal and regime_signal:
        classification = "mixed: station-specific residual bias with weather-regime interaction"
    elif compression_signal:
        classification = "global Level 1 score compression"
    elif station_signal:
        classification = "station-specific residual bias"
    elif regime_signal:
        classification = "weather-regime interaction"
    else:
        classification = "mixed or weakly separated residual structure"

    caveat = (
        f"For {primary_model}, {compression_share:.1%} of observed ge31 rows fall in predicted 29-31 bins; "
        f"station mean-residual range is {station_range:.2f} C; "
        f"weather regimes are {'limited by absent weather columns' if weather_limited else 'available'}."
    )
    return classification, caveat


def format_float(value: Any, digits: int = 3) -> str:
    """Format numeric values for Markdown."""
    if pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def write_report(
    df: pd.DataFrame,
    meta: dict[str, Any],
    selected_path: Path,
    observed: pd.DataFrame,
    predicted: pd.DataFrame,
    station: pd.DataFrame,
    regime: pd.DataFrame,
    report_path: Path,
    classification: str,
    caveat: str,
) -> None:
    """Write the Markdown high-tail bias report."""
    models = meta["selected_models"]
    primary_model = models[0]
    sub = df[df["model_name"].eq(primary_model)]
    timestamp_cols = [col for col in ["timestamp_sgt", "timestamp", "valid_time_sgt"] if col in df.columns]
    timestamp_span = "not available"
    if timestamp_cols:
        col = timestamp_cols[0]
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().any():
            timestamp_span = f"{parsed.min()} to {parsed.max()}"

    fixed = fixed_metrics(df, primary_model)
    ge31_pred_bins = (
        sub[sub["obs_ge31"]]["predicted_score_bin"].value_counts(dropna=False)
        .rename_axis("predicted_score_bin")
        .reset_index(name="observed_ge31_rows")
    )
    top_pos = station[station["model_name"].eq(primary_model)].head(5)
    top_neg = station[station["model_name"].eq(primary_model)].tail(5).sort_values("mean_residual_c")
    s_notes = station[
        station["model_name"].eq(primary_model) & station["station_id"].astype(str).isin(["S142", "S139"])
    ]

    lines = [
        "# System A A-L1H.0 High-Tail Residual Decomposition",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Input Source Selected",
        "",
        f"- File path: `{rel(selected_path)}`",
        f"- Model(s): `{', '.join(models)}`",
        f"- Target: `{meta['target_column']}` normalized to `official_wbgt_c`",
        f"- Model score: `{meta['prediction_column']}` normalized to `model_score`",
        f"- Row count: {len(df)} selected model rows",
        f"- Station count: {df['station_id'].nunique(dropna=True)}",
        f"- Timestamp span: {timestamp_span}",
        "",
        "## Residual Sign Convention",
        "",
        "`residual_c = official_wbgt_c - model_score`. Positive residuals mean System A underprediction against the official WBGT target in this diagnostic input.",
        "",
        "## ge31 Fixed-Threshold Summary",
        "",
        f"- Observed ge31 count: {fixed['observed_ge31']}",
        f"- Predicted ge31 count: {fixed['predicted_ge31']}",
        f"- Hits / misses / false alarms: {fixed['hits']} / {fixed['misses']} / {fixed['false_alarms']}",
        f"- Fixed_31 precision / recall / F1: {format_float(fixed['precision'])} / {format_float(fixed['recall'])} / {format_float(fixed['f1'])}",
        "",
        "These are fixed-threshold OOF diagnostics only; `P_ge31` is not treated as an official warning probability here.",
        "",
        "## High-Tail Compression Diagnostics",
        "",
        "Residual by observed bin, primary model:",
        "",
        observed[observed["model_name"].eq(primary_model)].to_markdown(index=False),
        "",
        "Residual by predicted bin, primary model:",
        "",
        predicted[predicted["model_name"].eq(primary_model)].to_markdown(index=False),
        "",
        "Observed ge31 rows by predicted score bin, primary model:",
        "",
        ge31_pred_bins.to_markdown(index=False),
        "",
        caveat,
        "",
        "## Station Diagnostics",
        "",
        "Top positive residual stations, primary model:",
        "",
        top_pos[["station_id", "n", "n_obs_ge31", "n_ge31_miss", "mean_residual_c", "high_tail_obs_ge31_mean_residual_c"]].to_markdown(index=False),
        "",
        "Top negative residual stations, primary model:",
        "",
        top_neg[["station_id", "n", "n_obs_ge31", "n_ge31_miss", "mean_residual_c", "high_tail_obs_ge31_mean_residual_c"]].to_markdown(index=False),
        "",
        "S142 / S139 notes:",
        "",
        s_notes[["station_id", "n", "n_obs_ge31", "n_ge31_miss", "mean_residual_c", "high_tail_obs_ge31_mean_residual_c"]].to_markdown(index=False) if not s_notes.empty else "S142 / S139 are not present in the selected input/model subset.",
        "",
        "## Weather-Regime Diagnostics",
        "",
    ]
    if meta["regime_columns"]:
        lines.extend([
            f"Regime columns created: `{', '.join(meta['regime_columns'])}`",
            "",
            regime[regime["model_name"].eq(primary_model)].to_markdown(index=False),
        ])
    else:
        lines.extend([
            "No configured weather-regime source columns were present in the selected OOF file, so weather-regime decomposition is limited for A-L1H.0.",
            "",
            regime[regime["model_name"].eq(primary_model)].to_markdown(index=False),
        ])
    lines.extend([
        "",
        "## Preliminary Classification",
        "",
        classification,
        "",
        "This is a diagnostic classification from existing OOF scores, not final proof of mechanism and not prospective forecast skill.",
        "",
        "## Next Recommended Action",
        "",
        next_action_for(classification),
        "",
        "## Claim Boundaries",
        "",
        "- This remains a retrospective OOF diagnostic for WBGT_A temporal heat-stress scoring.",
        "- It is not validated local 100m WBGT prediction and not an operational prospective forecast skill claim.",
        "- ge33 rows are exploratory only.",
    ])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def next_action_for(classification: str) -> str:
    """Map a preliminary classification to the lane's next review gate."""
    text = classification.lower()
    if "mixed" in text:
        return "Recommend a staged review: first confirm score-compression evidence, then decide between A-L1H.1 formula-v2, A-L1H.2 probability calibration, A-L1H.3 high-tail regression review gate, and A-L2 station-context preflight. Do not launch one large model change."
    if "station-specific" in text:
        return "Recommend A-L2 station-context preflight after review, with no claim that station context has solved high-tail prediction yet."
    if "weather-regime" in text:
        return "Recommend regime-specific high-tail calibration review after confirming weather-regime stability."
    if "global" in text or "compression" in text:
        return "Recommend A-L1H.1 formula-v2 / A-L1H.2 probability calibration / A-L1H.3 high-tail regression review gate, in that order of review, without training during A-L1H.0."
    return "Recommend reviewing residual tables before selecting the next lane."


def write_outputs(config: dict[str, Any]) -> AnalysisResult:
    """Run discovery, residual decomposition, and report writing."""
    out_dir = ROOT / config["analysis"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []

    inventory, selected = build_input_inventory(config)
    inventory_path = out_dir / "residual_input_inventory.csv"
    inventory.to_csv(inventory_path, index=False)
    output_paths.append(inventory_path)

    if selected is None:
        report_path = out_dir / "high_tail_bias_report.md"
        report_path.write_text(
            "# System A A-L1H.0 High-Tail Residual Decomposition\n\n"
            "Status: BLOCKED\n\n"
            "No usable existing OOF/model-score file was found. See `residual_input_inventory.csv` for schema diagnostics.\n",
            encoding="utf-8",
        )
        output_paths.append(report_path)
        return AnalysisResult("BLOCKED", None, [], None, 0, 0, 0, 0, 0, 0, 0, "blocked_no_usable_input", "No usable OOF input found.", output_paths)

    df, meta = prepare_analysis_input(config, selected)
    analysis_input_path = out_dir / "residual_analysis_input.csv"
    observed_path = out_dir / "residual_by_observed_bin.csv"
    predicted_path = out_dir / "residual_by_predicted_bin.csv"
    station_path = out_dir / "residual_by_station.csv"
    hour_path = out_dir / "residual_by_hour.csv"
    regime_path = out_dir / "residual_by_regime.csv"
    miss_path = out_dir / "ge31_miss_inventory.csv"
    false_alarm_path = out_dir / "ge31_false_alarm_inventory.csv"
    hit_path = out_dir / "ge31_hit_inventory.csv"
    ge33_path = out_dir / "ge33_exploratory_inventory.csv"
    report_path = out_dir / "high_tail_bias_report.md"

    observed = summary_table(df, ["model_name", "observed_wbgt_bin"])
    predicted = summary_table(df, ["model_name", "predicted_score_bin"])
    station = station_summary(df)
    hour = summary_table(df, ["model_name", "hour_sgt"])
    regime = regime_summary(df, meta["regime_columns"])
    primary_model = config["analysis"].get("primary_models", meta["selected_models"])[0]
    classification, caveat = classify_pattern(df, station, regime, primary_model)

    df.to_csv(analysis_input_path, index=False)
    observed.to_csv(observed_path, index=False)
    predicted.to_csv(predicted_path, index=False)
    station.to_csv(station_path, index=False)
    hour.to_csv(hour_path, index=False)
    regime.to_csv(regime_path, index=False)
    df[df["ge31_event_class"].eq("miss")].sort_values(["official_wbgt_c", "residual_c"], ascending=[False, False]).to_csv(miss_path, index=False)
    df[df["ge31_event_class"].eq("false_alarm")].sort_values(["model_score"], ascending=[False]).to_csv(false_alarm_path, index=False)
    df[df["ge31_event_class"].eq("hit")].sort_values(["official_wbgt_c", "model_score"], ascending=[False, False]).to_csv(hit_path, index=False)
    ge33 = df[df["obs_ge33"] | df["pred_ge33_fixed"]].copy()
    ge33["ge33_exploratory_flag"] = "exploratory_only"
    ge33.sort_values(["official_wbgt_c", "model_score"], ascending=[False, False]).to_csv(ge33_path, index=False)

    write_report(df, meta, selected, observed, predicted, station, regime, report_path, classification, caveat)

    output_paths.extend([
        analysis_input_path, observed_path, predicted_path, station_path, hour_path,
        regime_path, miss_path, false_alarm_path, hit_path, ge33_path, report_path,
    ])
    fixed = fixed_metrics(df, primary_model)
    return AnalysisResult(
        status="PASS",
        selected_input=rel(selected),
        selected_models=meta["selected_models"],
        target_column=meta["target_column"],
        row_count=len(df),
        station_count=int(df["station_id"].nunique(dropna=True)),
        observed_ge31_count=int(fixed["observed_ge31"]),
        predicted_ge31_count=int(fixed["predicted_ge31"]),
        ge31_hit_count=int(fixed["hits"]),
        ge31_miss_count=int(fixed["misses"]),
        ge31_false_alarm_count=int(fixed["false_alarms"]),
        classification=classification,
        caveat=caveat,
        output_paths=output_paths,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="A-L1H.0 residual decomposition from existing System A OOF predictions only."
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h_residual_decomposition.yaml")
    args = parser.parse_args(argv)

    config_path = ROOT / args.config
    config = load_config(config_path)
    result = write_outputs(config)
    print(f"[status] {result.status}")
    print(f"[selected_input] {result.selected_input}")
    print(f"[models] {', '.join(result.selected_models)}")
    print(f"[rows] {result.row_count}")
    print(f"[classification] {result.classification}")
    return 0 if result.status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
