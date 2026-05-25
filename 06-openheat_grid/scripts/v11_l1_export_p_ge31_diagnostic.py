#!/usr/bin/env python
"""Export Sprint 4C System A Level 1 P_ge31 diagnostic package.

Inputs:
    - configs/v11/p_ge31_diagnostic_export_config.yaml
    - outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv
    - outputs/v11_level1/probability_calibration/probability_model_selection_summary.csv
    - outputs/v11_level1/probability_calibration/reliability_summary.csv
    - outputs/v11_level1/probability_calibration/probability_by_station.csv
    - outputs/v11_level1/probability_calibration/probability_by_hour.csv
    - Optional threshold context:
      outputs/v11_level1/probability_calibration/probability_threshold_metrics.csv

Outputs:
    - outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic.csv
    - outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic_sample.csv
    - outputs/v11_level1/p_ge31_export/p_ge31_aoi_temporal_schema.csv
    - outputs/v11_level1/p_ge31_export/p_ge31_export_validation_report.md
    - outputs/v11_level1/p_ge31_export/p_ge31_reliability_hardening_report.md
    - outputs/v11_level1/p_ge31_export/p_ge31_reliability_summary.csv
    - outputs/v11_level1/p_ge31_export/p_ge31_contract_compliance.csv
    - outputs/v11_level1/p_ge31_export/p_ge31_aoi_temporal_design_note.md
    - outputs/v11_level1/p_ge31_export/sprint4c_p_ge31_export_hardening_report.md

Saved metrics:
    - Station diagnostic row count and source row count.
    - Required-column, forbidden-column, probability-range, retrospective,
      station diagnostic mode, AOI schema-only, missing-value, and row-count
      contract checks.
    - Selected Sprint 3B Brier, ECE_10, average precision, ROC_AUC, and
      station probability-bias diagnostics.
    - AOI temporal boundary note documenting that no AOI aggregation method was
      selected in Sprint 4C.

This script packages existing retrospective Sprint 3B P_ge31 diagnostic outputs.
It does not train calibrators, rerun probability calibration, retrain any WBGT
model, implement prospective evaluation, touch collector code, touch Level 2,
System B, SOLWEIG, v12, rasters, risk maps, local WBGT, or 100m cell outputs.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v11/p_ge31_diagnostic_export_config.yaml"
PROBABILITY_DIR = ROOT / "outputs/v11_level1/probability_calibration"

STATION_COLUMNS = [
    "timestamp_sgt",
    "timestamp_utc",
    "station_id",
    "dataset_label",
    "output_mode",
    "spatial_scope",
    "wbgt_a_score_c",
    "wbgt_a_score_model_id",
    "wbgt_a_score_version",
    "p_ge31_diagnostic",
    "p_ge31_calibrator_id",
    "p_ge31_validation_context",
    "ge31_screening_flag_best_f1_optional",
    "ge31_screening_flag_high_recall_optional",
    "p_ge33_exploratory_optional",
    "is_retrospective",
    "source_prediction_context",
    "quality_flag",
    "notes",
]
AOI_SCHEMA_COLUMNS = [
    "timestamp_sgt",
    "timestamp_utc",
    "aoi_id",
    "dataset_label",
    "output_mode",
    "spatial_scope",
    "aggregation_method",
    "wbgt_a_score_c",
    "wbgt_a_score_model_id",
    "wbgt_a_score_version",
    "p_ge31_diagnostic",
    "p_ge31_calibrator_id",
    "p_ge31_validation_context",
    "ge31_screening_flag_best_f1_optional",
    "ge31_screening_flag_high_recall_optional",
    "p_ge33_exploratory_optional",
    "is_retrospective",
    "source_prediction_context",
    "quality_flag",
    "notes",
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Package existing Sprint 3B p_ge31_diagnostic predictions into the "
            "Sprint 4C retrospective diagnostic export contract."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to p_ge31 diagnostic export YAML config.",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict:
    """Load YAML config."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_repo_path(value: str | Path) -> Path:
    """Resolve a repository-relative or absolute path."""
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def rel(path: Path) -> str:
    """Return a repository-relative display path."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def fmt(value: object, digits: int = 3) -> str:
    """Format numeric report values with NA fallback."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "NA" if value is None else str(value)
    if not np.isfinite(number):
        return "NA"
    return f"{number:.{digits}f}"


def semicolon(values: Iterable[object]) -> str:
    """Join non-empty values in stable order."""
    out: list[str] = []
    for value in values:
        text = str(value)
        if text and text != "nan" and text not in out:
            out.append(text)
    return ";".join(out)


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    """Build a compact Markdown table without optional dependencies."""
    if not rows:
        return ["No rows available."]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [str(row.get(column, "NA")).replace("\n", " ") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first available column from a candidate list."""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def boolish_true(series: pd.Series) -> pd.Series:
    """Convert a boolean-like series to true/false."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def filter_predictions(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Filter to the selected Sprint 3B diagnostic context when columns exist."""
    out = df.copy()
    filters = [
        (first_existing_column(out, ["dataset_label"]), "hourly_max"),
        (first_existing_column(out, ["model", "model_id", "wbgt_a_score_model_id"]), config["default_score_model"]),
        (first_existing_column(out, ["calibrator", "probability_calibrator_id", "p_ge31_calibrator_id"]), config["default_calibrator"]),
        (first_existing_column(out, ["validation_scheme", "p_ge31_validation_context"]), config["validation_context"]),
    ]
    for column, expected in filters:
        if column is not None:
            out = out[out[column].astype(str).eq(str(expected))].copy()
    return out


def timestamp_utc_from_sgt(values: pd.Series) -> pd.Series:
    """Convert timestamp_sgt values to UTC strings when timezone data are present."""
    timestamps = pd.to_datetime(values, errors="coerce", utc=True)
    return timestamps.dt.strftime("%Y-%m-%d %H:%M:%S%z").where(timestamps.notna(), "")


def load_thresholds(config: dict) -> tuple[pd.DataFrame, dict[tuple[str, str], float], dict[str, float]]:
    """Load training-selected threshold context for optional screening flags."""
    path = PROBABILITY_DIR / "probability_threshold_metrics.csv"
    if not path.exists():
        return pd.DataFrame(), {}, {}
    df = pd.read_csv(path)
    mask = (
        df["dataset_label"].astype(str).eq("hourly_max")
        & df["model"].astype(str).eq(config["default_score_model"])
        & df["event_target"].astype(str).eq("ge31")
        & df["calibrator"].astype(str).eq(config["default_calibrator"])
        & df["validation_scheme"].astype(str).eq(config["validation_context"])
        & df["achievable"].astype(str).str.lower().isin({"true", "1"})
    )
    selected = df[mask].copy()
    by_fold: dict[tuple[str, str], float] = {}
    fallback: dict[str, float] = {}
    for operating_point in ["best_F1_train", "recall90_train"]:
        op = selected[selected["operating_point"].astype(str).eq(operating_point)].copy()
        if op.empty:
            continue
        fallback[operating_point] = float(op["probability_threshold"].mean())
        for _, row in op.iterrows():
            by_fold[(str(row.get("fold_id", "")), operating_point)] = float(row["probability_threshold"])
    return selected, by_fold, fallback


def threshold_flag(
    frame: pd.DataFrame,
    probability_col: str,
    fold_col: str | None,
    operating_point: str,
    by_fold: dict[tuple[str, str], float],
    fallback: dict[str, float],
) -> pd.Series:
    """Apply optional probability thresholds, using fold thresholds when available."""
    if probability_col not in frame.columns or operating_point not in fallback:
        return pd.Series(pd.NA, index=frame.index, dtype="object")
    if fold_col is None:
        threshold = fallback[operating_point]
        return frame[probability_col].astype(float).ge(threshold)
    thresholds = frame[fold_col].astype(str).map(
        lambda fold_id: by_fold.get((fold_id, operating_point), fallback[operating_point])
    )
    return frame[probability_col].astype(float).ge(thresholds.astype(float))


def selected_station_metrics(config: dict) -> pd.DataFrame:
    """Load station diagnostics for the selected model/calibrator/context."""
    path = PROBABILITY_DIR / "probability_by_station.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    mask = (
        df["dataset_label"].astype(str).eq("hourly_max")
        & df["model"].astype(str).eq(config["default_score_model"])
        & df["event_target"].astype(str).eq("ge31")
        & df["calibrator"].astype(str).eq(config["default_calibrator"])
        & df["validation_scheme"].astype(str).eq(config["validation_context"])
    )
    return df[mask].copy()


def quality_flags_for_row(row: pd.Series, station_lookup: dict[str, dict[str, float]], config: dict) -> str:
    """Assign row-level export quality flags."""
    flags = ["ok_retrospective_diagnostic", "not_operational_warning"]
    probability = row.get("p_ge31_diagnostic")
    if pd.isna(probability):
        flags.append("missing_probability")
    station = str(row.get("station_id", ""))
    station_info = station_lookup.get(station)
    if station_info:
        event_count = station_info.get("event_count", np.nan)
        bias = station_info.get("probability_bias", np.nan)
        if np.isfinite(event_count) and event_count < float(config.get("low_support_event_count_threshold", 10)):
            flags.append("low_support_station")
        if np.isfinite(bias) and abs(bias) >= float(config.get("station_bias_abs_warning_threshold", 0.075)):
            flags.append("station_bias_warning")
    return semicolon(flags)


def build_station_export(raw: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, dict[str, object]]:
    """Build the station diagnostic export frame."""
    filtered = filter_predictions(raw, config)
    model_col = first_existing_column(filtered, ["model", "model_id", "wbgt_a_score_model_id"])
    score_col = first_existing_column(filtered, ["score", "wbgt_a_score_c", "prediction_wbgt_c"])
    prob_col = first_existing_column(filtered, ["p_ge31", "p_ge31_diagnostic", "probability"])
    calibrator_col = first_existing_column(filtered, ["probability_calibrator_id", "calibrator", "p_ge31_calibrator_id"])
    validation_col = first_existing_column(filtered, ["validation_scheme", "p_ge31_validation_context"])
    fold_col = first_existing_column(filtered, ["fold_id"])
    if score_col is None:
        raise SystemExit("[ERROR] No score column found for wbgt_a_score_c mapping.")
    if prob_col is None:
        filtered["p_ge31_diagnostic"] = np.nan
        prob_col = "p_ge31_diagnostic"

    thresholds, by_fold_thresholds, fallback_thresholds = load_thresholds(config)
    station_metrics = selected_station_metrics(config)
    station_lookup: dict[str, dict[str, float]] = {}
    for _, row in station_metrics.iterrows():
        station_lookup[str(row["station_id"])] = {
            "event_count": float(row.get("event_count", np.nan)),
            "probability_bias": float(row.get("probability_bias", np.nan)),
        }

    out = pd.DataFrame(index=filtered.index)
    out["timestamp_sgt"] = filtered.get("timestamp_sgt", pd.Series("", index=filtered.index)).astype(str)
    if "timestamp_utc" in filtered.columns:
        out["timestamp_utc"] = filtered["timestamp_utc"].astype(str)
    else:
        out["timestamp_utc"] = timestamp_utc_from_sgt(out["timestamp_sgt"])
    out["station_id"] = filtered.get("station_id", pd.Series("", index=filtered.index)).astype(str)
    out["dataset_label"] = filtered.get("dataset_label", pd.Series("hourly_max", index=filtered.index)).astype(str)
    out["output_mode"] = "station_diagnostic"
    out["spatial_scope"] = "station"
    out["wbgt_a_score_c"] = pd.to_numeric(filtered[score_col], errors="coerce")
    out["wbgt_a_score_model_id"] = (
        filtered[model_col].astype(str) if model_col is not None else config["default_score_model"]
    )
    out["wbgt_a_score_version"] = config["schema_version"]
    out["p_ge31_diagnostic"] = pd.to_numeric(filtered[prob_col], errors="coerce")
    out["p_ge31_calibrator_id"] = (
        filtered[calibrator_col].astype(str) if calibrator_col is not None else config["default_calibrator"]
    )
    out["p_ge31_validation_context"] = (
        filtered[validation_col].astype(str) if validation_col is not None else config["validation_context"]
    )
    out["ge31_screening_flag_best_f1_optional"] = threshold_flag(
        filtered, prob_col, fold_col, "best_F1_train", by_fold_thresholds, fallback_thresholds
    )
    out["ge31_screening_flag_high_recall_optional"] = threshold_flag(
        filtered, prob_col, fold_col, "recall90_train", by_fold_thresholds, fallback_thresholds
    )
    out["p_ge33_exploratory_optional"] = (
        pd.to_numeric(filtered["p_ge33"], errors="coerce") if "p_ge33" in filtered.columns else pd.NA
    )
    out["is_retrospective"] = True
    fold_text = filtered[fold_col].astype(str) if fold_col is not None else pd.Series("", index=filtered.index)
    out["source_prediction_context"] = (
        "Sprint 3B held-out blocked-date retrospective diagnostic predictions"
        + fold_text.map(lambda value: f"; fold_id={value}" if value else "")
    )
    out["quality_flag"] = out.apply(lambda row: quality_flags_for_row(row, station_lookup, config), axis=1)
    out["notes"] = (
        "Retrospective station diagnostic only; not operational warning probability; "
        "not prospective; not local WBGT; not 100m cell severity."
    )
    out = out[STATION_COLUMNS].sort_values(["timestamp_sgt", "station_id"]).reset_index(drop=True)
    meta = {
        "source_rows": len(raw),
        "filtered_rows": len(filtered),
        "threshold_rows": len(thresholds),
        "best_f1_threshold_mean": fallback_thresholds.get("best_F1_train", np.nan),
        "high_recall_threshold_mean": fallback_thresholds.get("recall90_train", np.nan),
    }
    return out, meta


def write_schema_only_outputs(out_dir: Path) -> None:
    """Write empty contract-shaped outputs for blocked source cases."""
    pd.DataFrame(columns=STATION_COLUMNS).to_csv(out_dir / "p_ge31_station_diagnostic.csv", index=False)
    pd.DataFrame(columns=STATION_COLUMNS).to_csv(out_dir / "p_ge31_station_diagnostic_sample.csv", index=False)
    pd.DataFrame(columns=AOI_SCHEMA_COLUMNS).to_csv(out_dir / "p_ge31_aoi_temporal_schema.csv", index=False)


def selected_overall_metrics(config: dict) -> pd.DataFrame:
    """Load selected model metrics from Sprint 3B selection summary."""
    path = PROBABILITY_DIR / "probability_model_selection_summary.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    mask = (
        df["dataset_label"].astype(str).eq("hourly_max")
        & df["model"].astype(str).eq(config["default_score_model"])
        & df["event_target"].astype(str).eq("ge31")
        & df["calibrator"].astype(str).eq(config["default_calibrator"])
        & df["validation_scheme"].astype(str).eq(config["validation_context"])
    )
    return df[mask].copy()


def selected_reliability_bins(config: dict) -> pd.DataFrame:
    """Load selected pre-calibration reliability summary rows."""
    path = PROBABILITY_DIR / "reliability_summary.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    mask = (
        df["dataset_label"].astype(str).eq("hourly_max")
        & df["model"].astype(str).eq(config["default_score_model"])
        & df["event_target"].astype(str).eq("ge31")
    )
    return df[mask].copy()


def selected_hour_metrics(config: dict) -> pd.DataFrame:
    """Load selected hour diagnostics."""
    path = PROBABILITY_DIR / "probability_by_hour.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    mask = (
        df["dataset_label"].astype(str).eq("hourly_max")
        & df["model"].astype(str).eq(config["default_score_model"])
        & df["event_target"].astype(str).eq("ge31")
        & df["calibrator"].astype(str).eq(config["default_calibrator"])
        & df["validation_scheme"].astype(str).eq(config["validation_context"])
    )
    return df[mask].copy()


def write_reliability_outputs(out_dir: Path, config: dict) -> dict[str, object]:
    """Write reliability hardening CSV and Markdown report."""
    overall = selected_overall_metrics(config)
    reliability = selected_reliability_bins(config)
    stations = selected_station_metrics(config)
    hours = selected_hour_metrics(config)

    rows: list[dict[str, object]] = []
    if not overall.empty:
        row = overall.iloc[0]
        rows.append(
            {
                "summary_scope": "selected_overall",
                "dataset_label": row.get("dataset_label"),
                "model": row.get("model"),
                "calibrator": row.get("calibrator"),
                "validation_scheme": row.get("validation_scheme"),
                "station_id": "",
                "n": row.get("n"),
                "event_count": row.get("event_count"),
                "observed_event_rate": row.get("observed_event_rate"),
                "mean_predicted_probability": row.get("mean_predicted_probability"),
                "probability_bias": row.get("probability_bias"),
                "Brier": row.get("Brier"),
                "ECE_10": row.get("ECE_10"),
                "average_precision": row.get("average_precision"),
                "ROC_AUC": row.get("ROC_AUC"),
                "precision": row.get("best_F1_train_selected_precision"),
                "recall": row.get("best_F1_train_selected_recall"),
                "F1": row.get("best_F1_train_selected_F1"),
                "monotonicity": "",
                "notes": "Sprint 3B selected retrospective diagnostic candidate.",
            }
        )
    for _, row in reliability.iterrows():
        rows.append(
            {
                "summary_scope": f"pre_calibration_reliability_{row.get('bin_kind')}",
                "dataset_label": row.get("dataset_label"),
                "model": row.get("model"),
                "calibrator": "",
                "validation_scheme": row.get("validation_scheme"),
                "station_id": "",
                "n": "",
                "event_count": "",
                "observed_event_rate": "",
                "mean_predicted_probability": "",
                "probability_bias": "",
                "Brier": "",
                "ECE_10": "",
                "average_precision": "",
                "ROC_AUC": "",
                "precision": "",
                "recall": "",
                "F1": "",
                "monotonicity": row.get("monotonicity"),
                "notes": (
                    f"n_bins={row.get('n_bins')}; low_support_bins={row.get('n_low_support_bins')}; "
                    f"event_rate_range={fmt(row.get('event_rate_min'))}-{fmt(row.get('event_rate_max'))}"
                ),
            }
        )
    focus = stations[stations.get("station_id", pd.Series(dtype=str)).astype(str).isin(["S142", "S137", "S135", "S139"])]
    for _, row in focus.iterrows():
        rows.append(
            {
                "summary_scope": "focus_station",
                "dataset_label": row.get("dataset_label"),
                "model": row.get("model"),
                "calibrator": row.get("calibrator"),
                "validation_scheme": row.get("validation_scheme"),
                "station_id": row.get("station_id"),
                "n": row.get("n"),
                "event_count": row.get("event_count"),
                "observed_event_rate": row.get("observed_event_rate"),
                "mean_predicted_probability": row.get("mean_predicted_probability"),
                "probability_bias": row.get("probability_bias"),
                "Brier": row.get("Brier"),
                "ECE_10": "",
                "average_precision": "",
                "ROC_AUC": "",
                "precision": row.get("precision"),
                "recall": row.get("recall"),
                "F1": row.get("F1"),
                "monotonicity": "",
                "notes": "Focus-station station bias diagnostic.",
            }
        )

    summary = pd.DataFrame(rows)
    summary_path = out_dir / "p_ge31_reliability_summary.csv"
    summary.to_csv(summary_path, index=False)

    overall_row = overall.iloc[0].to_dict() if not overall.empty else {}
    bias_threshold = float(config.get("station_bias_abs_warning_threshold", 0.075))
    station_warning_count = int((stations["probability_bias"].abs() >= bias_threshold).sum()) if not stations.empty else 0
    low_support_count = (
        int((stations["event_count"] < float(config.get("low_support_event_count_threshold", 10))).sum())
        if not stations.empty
        else 0
    )
    focus_rows = []
    for _, row in focus.sort_values("station_id").iterrows():
        focus_rows.append(
            {
                "station_id": row.get("station_id"),
                "event_count": row.get("event_count"),
                "event_rate": fmt(row.get("observed_event_rate")),
                "mean_p": fmt(row.get("mean_predicted_probability")),
                "bias": fmt(row.get("probability_bias")),
                "Brier": fmt(row.get("Brier")),
                "precision": fmt(row.get("precision")),
                "recall": fmt(row.get("recall")),
            }
        )
    worst_hours = []
    if not hours.empty:
        temp = hours.assign(abs_bias=hours["probability_bias"].abs()).sort_values("abs_bias", ascending=False).head(5)
        for _, row in temp.iterrows():
            worst_hours.append(
                {
                    "hour": int(row.get("hour")),
                    "n": int(row.get("n")),
                    "event_rate": fmt(row.get("observed_event_rate")),
                    "mean_p": fmt(row.get("mean_predicted_probability")),
                    "bias": fmt(row.get("probability_bias")),
                    "Brier": fmt(row.get("Brier")),
                }
            )

    report_lines = [
        "# P_ge31 Reliability Hardening Report",
        "",
        "## Selected model/calibrator",
        "",
        f"- Score model: `{config['default_score_model']}`",
        f"- Calibrator: `{config['default_calibrator']}`",
        f"- Validation context: `{config['validation_context']}`",
        "- Scope: retrospective System A Level 1 diagnostic only.",
        "",
        "## Sprint 3B metrics",
        "",
        f"- Brier: {fmt(overall_row.get('Brier'))}",
        f"- ECE_10: {fmt(overall_row.get('ECE_10'))}",
        f"- Average precision: {fmt(overall_row.get('average_precision'))}",
        f"- ROC_AUC: {fmt(overall_row.get('ROC_AUC'))}",
        f"- Observed event rate: {fmt(overall_row.get('observed_event_rate'))}",
        f"- Mean predicted probability: {fmt(overall_row.get('mean_predicted_probability'))}",
        f"- Probability bias: {fmt(overall_row.get('probability_bias'))}",
        "",
        "## Station bias warnings",
        "",
        f"- Stations with abs(probability_bias) >= {bias_threshold}: {station_warning_count}",
        f"- Stations with event_count below {config.get('low_support_event_count_threshold', 10)}: {low_support_count}",
        "",
        "## S142/S137/S135/S139 behavior",
        "",
        *markdown_table(
            focus_rows,
            ["station_id", "event_count", "event_rate", "mean_p", "bias", "Brier", "precision", "recall"],
        ),
        "",
        "## Hour diagnostics",
        "",
        *markdown_table(worst_hours, ["hour", "n", "event_rate", "mean_p", "bias", "Brier"]),
        "",
        "## Known limitations",
        "",
        "- Retrospective calibration context only.",
        "- No lead-time skill is established.",
        "- Station bias remains, including underprediction at S142/S137 and overprediction at S139.",
        "- ge33 remains exploratory and is not promoted in this export.",
        "- This is not an operational warning probability.",
        "",
        "## Reliability interpretation",
        "",
        "- Acceptable for retrospective diagnostic use: yes, with station-bias caveats.",
        "- Enough for operational use: no.",
    ]
    (out_dir / "p_ge31_reliability_hardening_report.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )
    return {
        "overall": overall_row,
        "station_warning_count": station_warning_count,
        "low_support_count": low_support_count,
        "reliability_summary_rows": len(summary),
    }


def write_aoi_design_note(out_dir: Path) -> None:
    """Write the AOI temporal design note."""
    lines = [
        "# P_ge31 AOI Temporal Design Note",
        "",
        "Sprint 4C exports station-level retrospective diagnostics only. These rows are not System B temporal severity by themselves.",
        "",
        "System B should consume AOI-level temporal severity, not raw station diagnostic rows. This sprint does not select an AOI aggregation method and does not silently promote station rows to AOI or 100m cell severity.",
        "",
        "Candidate future AOI aggregation methods include:",
        "",
        "- `station_anchor_S128_or_ToaPayoh_station`, if validated.",
        "- `network_median`.",
        "- `network_p90`.",
        "- `max_or_high_recall_screening`.",
        "- `probability-pooled statistic`.",
        "",
        "Each aggregation method must be separately justified, versioned, and checked against the Level 1 output contract before System B consumption.",
        "",
        "Do not use station rows as 100m cell severity. Do not treat this export as local WBGT, cell-level WBGT, or risk.",
    ]
    (out_dir / "p_ge31_aoi_temporal_design_note.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def contract_checks(station: pd.DataFrame, aoi_schema: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Run contract-compliance checks for the Sprint 4C export."""
    required = list(config["required_columns"])
    forbidden = list(config["forbidden_columns"])
    rows: list[dict[str, object]] = []

    missing_required = [column for column in required if column not in station.columns]
    rows.append(
        {
            "check_name": "required_columns_present",
            "status": "PASS" if not missing_required else "FAIL",
            "observed": semicolon(missing_required) if missing_required else "all required columns present",
            "expected": semicolon(required),
            "notes": "",
        }
    )
    present_forbidden = [column for column in forbidden if column in station.columns]
    rows.append(
        {
            "check_name": "forbidden_columns_absent",
            "status": "PASS" if not present_forbidden else "FAIL",
            "observed": semicolon(present_forbidden) if present_forbidden else "no forbidden columns present",
            "expected": semicolon(forbidden),
            "notes": "",
        }
    )
    retro_ok = "is_retrospective" in station.columns and boolish_true(station["is_retrospective"]).all()
    rows.append(
        {
            "check_name": "is_retrospective_true",
            "status": "PASS" if retro_ok else "FAIL",
            "observed": str(retro_ok),
            "expected": "all station rows true",
            "notes": "",
        }
    )
    mode_ok = "output_mode" in station.columns and station["output_mode"].astype(str).eq("station_diagnostic").all()
    rows.append(
        {
            "check_name": "station_diagnostic_mode_labelled",
            "status": "PASS" if mode_ok else "FAIL",
            "observed": semicolon(station["output_mode"].unique()) if "output_mode" in station.columns else "missing",
            "expected": "station_diagnostic",
            "notes": "",
        }
    )
    aoi_ok = len(aoi_schema) == 0 and "aoi_id" in aoi_schema.columns and "station_id" not in aoi_schema.columns
    rows.append(
        {
            "check_name": "aoi_temporal_schema_only",
            "status": "PASS" if aoi_ok else "FAIL",
            "observed": f"rows={len(aoi_schema)}; columns={semicolon(aoi_schema.columns)}",
            "expected": "zero rows; aoi_id present; station_id absent",
            "notes": "AOI temporal mode was not silently created from station rows.",
        }
    )
    quality_ok = "quality_flag" in station.columns and station["quality_flag"].notna().all()
    rows.append(
        {
            "check_name": "quality_flag_present",
            "status": "PASS" if quality_ok else "FAIL",
            "observed": f"missing={int(station['quality_flag'].isna().sum())}" if "quality_flag" in station.columns else "missing column",
            "expected": "quality_flag present on every row",
            "notes": "",
        }
    )
    if "p_ge31_diagnostic" in station.columns:
        probabilities = pd.to_numeric(station["p_ge31_diagnostic"], errors="coerce")
        probability_ok = probabilities.dropna().between(0, 1).all()
        missing_probability = int(probabilities.isna().sum())
    else:
        probability_ok = False
        missing_probability = len(station)
    rows.append(
        {
            "check_name": "p_ge31_diagnostic_within_0_1",
            "status": "PASS" if probability_ok else "FAIL",
            "observed": f"missing_probability={missing_probability}",
            "expected": "all non-missing probabilities within [0,1]",
            "notes": "",
        }
    )
    missing_required_values = {
        column: int(station[column].isna().sum() + station[column].astype(str).eq("").sum())
        for column in required
        if column in station.columns
    }
    missing_required_total = sum(missing_required_values.values())
    rows.append(
        {
            "check_name": "missing_values_count",
            "status": "PASS" if missing_required_total == 0 else "FAIL",
            "observed": semicolon(f"{key}={value}" for key, value in missing_required_values.items()),
            "expected": "required columns have zero missing/blank values",
            "notes": f"total_required_missing={missing_required_total}",
        }
    )
    rows.append(
        {
            "check_name": "row_count",
            "status": "PASS" if len(station) > 0 else "FAIL",
            "observed": len(station),
            "expected": "station diagnostic export has rows when source predictions exist",
            "notes": "",
        }
    )
    return pd.DataFrame(rows)


def write_export_validation_report(
    out_dir: Path,
    config: dict,
    meta: dict[str, object],
    compliance: pd.DataFrame,
    blocked_reason: str | None = None,
) -> None:
    """Write export validation report."""
    status = "BLOCKED" if blocked_reason else ("PASS" if compliance["status"].eq("FAIL").sum() == 0 else "PARTIAL")
    lines = [
        "# P_ge31 Export Validation Report",
        "",
        f"## Status: {status}",
        "",
        f"- Schema version: `{config['schema_version']}`",
        f"- Source rows: {meta.get('source_rows', 0)}",
        f"- Filtered/export rows: {meta.get('filtered_rows', 0)}",
        f"- Mean best-F1 threshold used for optional flags: {fmt(meta.get('best_f1_threshold_mean'))}",
        f"- Mean high-recall threshold used for optional flags: {fmt(meta.get('high_recall_threshold_mean'))}",
        "",
        "## Scope checks",
        "",
        "- No model training.",
        "- No probability calibration rerun.",
        "- No prospective claim.",
        "- No operational warning probability.",
        "- No local WBGT or cell-level severity output.",
    ]
    if blocked_reason:
        lines.extend(["", "## Blocker", "", blocked_reason])
    lines.extend(
        [
            "",
            "## Compliance checks",
            "",
            *markdown_table(
                compliance.to_dict("records"),
                ["check_name", "status", "observed", "expected", "notes"],
            ),
        ]
    )
    (out_dir / "p_ge31_export_validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_report(
    out_dir: Path,
    config: dict,
    input_counts: list[dict[str, object]],
    compliance: pd.DataFrame,
    reliability_meta: dict[str, object],
    blocked_reason: str | None = None,
) -> None:
    """Write the Sprint 4C summary report."""
    failed_checks = int(compliance["status"].eq("FAIL").sum())
    status = "BLOCKED" if blocked_reason else ("PASS" if failed_checks == 0 else "PARTIAL")
    overall = reliability_meta.get("overall", {})
    lines = [
        "# Sprint 4C - P_ge31 Diagnostic Export / Reliability Hardening",
        "",
        "## Status",
        "",
        status,
        "",
        "## Scope",
        "",
        "- retrospective diagnostic export only",
        "- no model training",
        "- no prospective claim",
        "- no local WBGT",
        "- no System B/v12/SOLWEIG",
        "",
        "## Inputs",
        "",
        *markdown_table(input_counts, ["file", "exists", "row_count"]),
        "",
        "## Export outputs",
        "",
        "- `outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic.csv`",
        "- `outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic_sample.csv`",
        "- `outputs/v11_level1/p_ge31_export/p_ge31_aoi_temporal_schema.csv`",
        "- `outputs/v11_level1/p_ge31_export/p_ge31_export_validation_report.md`",
        "- `outputs/v11_level1/p_ge31_export/p_ge31_reliability_hardening_report.md`",
        "- `outputs/v11_level1/p_ge31_export/p_ge31_reliability_summary.csv`",
        "- `outputs/v11_level1/p_ge31_export/p_ge31_contract_compliance.csv`",
        "- `outputs/v11_level1/p_ge31_export/p_ge31_aoi_temporal_design_note.md`",
        "",
        "## Contract compliance",
        "",
        f"- Failed checks: {failed_checks}",
        f"- Overall compliance status: {status if status != 'BLOCKED' else 'BLOCKED'}",
        "",
        "## Reliability summary",
        "",
        f"- Selected model/calibrator: `{config['default_score_model']} + {config['default_calibrator']} + {config['validation_context']}`",
        f"- Brier: {fmt(overall.get('Brier'))}",
        f"- ECE_10: {fmt(overall.get('ECE_10'))}",
        f"- Average precision: {fmt(overall.get('average_precision'))}",
        f"- ROC_AUC: {fmt(overall.get('ROC_AUC'))}",
        f"- Station bias warning count: {reliability_meta.get('station_warning_count', 0)}",
        f"- Low-support station count: {reliability_meta.get('low_support_count', 0)}",
        "",
        "## AOI temporal boundary",
        "",
        "station_diagnostic export is not System B cell severity.",
        "",
        "AOI temporal aggregation is deferred.",
        "",
        "## Caveats",
        "",
        "- retrospective",
        "- not operational",
        "- no lead-time skill",
        "- no local WBGT",
        "- ge33 exploratory",
        "- station bias remains",
        "",
        "## Next action",
        "",
        "- after 4B.1 metadata patch, run 24h prospective metadata smoke;",
        "- later choose AOI temporal aggregation method;",
        "- do not integrate with System B until AOI temporal contract is selected.",
    ]
    if blocked_reason:
        lines.extend(["", "## Blocker", "", blocked_reason])
    (out_dir / "sprint4c_p_ge31_export_hardening_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def input_counts(paths: list[Path]) -> list[dict[str, object]]:
    """Return existence and row counts for report inputs."""
    rows: list[dict[str, object]] = []
    for path in paths:
        exists = path.exists()
        if exists and path.suffix.lower() == ".csv":
            try:
                row_count: object = len(pd.read_csv(path))
            except Exception as exc:  # pragma: no cover - report-only fallback.
                row_count = f"unreadable: {exc}"
        else:
            row_count = "NA"
        rows.append({"file": rel(path), "exists": exists, "row_count": row_count})
    return rows


def main() -> None:
    """Run the Sprint 4C export."""
    args = parse_args()
    config = load_yaml(resolve_repo_path(args.config))
    input_path = resolve_repo_path(config["input_prediction_file"])
    out_dir = resolve_repo_path(config["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    report_inputs = [
        ROOT / "docs/v11/SystemA_Level1_Interim_Model_Card_CN.md",
        ROOT / "configs/v11/system_a_level1_output_contract.yaml",
        ROOT / "outputs/v11_level1/model_card/system_a_level1_output_contract.md",
        input_path,
        PROBABILITY_DIR / "sprint3b_pge31_probability_calibration_report.md",
        PROBABILITY_DIR / "probability_model_selection_summary.csv",
        PROBABILITY_DIR / "reliability_summary.csv",
        PROBABILITY_DIR / "probability_by_station.csv",
        PROBABILITY_DIR / "probability_by_hour.csv",
    ]
    counts = input_counts(report_inputs)

    blocked_reason = None
    if not input_path.exists():
        blocked_reason = (
            f"Required prediction input `{rel(input_path)}` is missing. "
            "Sprint 4C did not rerun probability calibration; schema-only outputs were written."
        )
        write_schema_only_outputs(out_dir)
        station = pd.read_csv(out_dir / "p_ge31_station_diagnostic.csv")
        aoi_schema = pd.read_csv(out_dir / "p_ge31_aoi_temporal_schema.csv")
        compliance = contract_checks(station, aoi_schema, config)
        compliance.to_csv(out_dir / "p_ge31_contract_compliance.csv", index=False)
        reliability_meta = write_reliability_outputs(out_dir, config)
        write_aoi_design_note(out_dir)
        write_export_validation_report(out_dir, config, {"source_rows": 0, "filtered_rows": 0}, compliance, blocked_reason)
        write_summary_report(out_dir, config, counts, compliance, reliability_meta, blocked_reason)
        return

    raw = pd.read_csv(input_path)
    station, meta = build_station_export(raw, config)
    station.to_csv(out_dir / "p_ge31_station_diagnostic.csv", index=False)
    station.head(int(config.get("max_sample_rows", 200))).to_csv(
        out_dir / "p_ge31_station_diagnostic_sample.csv", index=False
    )
    aoi_schema = pd.DataFrame(columns=AOI_SCHEMA_COLUMNS)
    aoi_schema.to_csv(out_dir / "p_ge31_aoi_temporal_schema.csv", index=False)
    compliance = contract_checks(station, aoi_schema, config)
    compliance.to_csv(out_dir / "p_ge31_contract_compliance.csv", index=False)
    reliability_meta = write_reliability_outputs(out_dir, config)
    write_aoi_design_note(out_dir)
    write_export_validation_report(out_dir, config, meta, compliance)
    write_summary_report(out_dir, config, counts, compliance, reliability_meta)
    print(f"[OK] Wrote Sprint 4C p_ge31 export package to {rel(out_dir)}")
    print(f"[OK] Station diagnostic rows: {len(station)}")
    print(f"[OK] Compliance failures: {int(compliance['status'].eq('FAIL').sum())}")


if __name__ == "__main__":
    main()
