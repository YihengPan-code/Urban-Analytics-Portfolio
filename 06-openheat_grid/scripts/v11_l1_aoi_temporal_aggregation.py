#!/usr/bin/env python
"""Run System A Level 1 Sprint 4D AOI temporal aggregation dry run.

Inputs:
    - configs/v11/system_a_aoi_temporal_aggregation_config.example.yaml
    - outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic.csv
    - outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic_sample.csv
    - Fallback only:
      outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv

Outputs:
    - outputs/v11_level1/aoi_temporal_aggregation/aoi_input_schema_audit.csv
    - outputs/v11_level1/aoi_temporal_aggregation/aoi_station_coverage_by_timestamp.csv
    - outputs/v11_level1/aoi_temporal_aggregation/aoi_station_cohort_summary.csv
    - outputs/v11_level1/aoi_temporal_aggregation/aoi_temporal_aggregation_candidates.csv
    - outputs/v11_level1/aoi_temporal_aggregation/aoi_temporal_method_comparison.csv
    - outputs/v11_level1/aoi_temporal_aggregation/aoi_temporal_top_decile_overlap.csv
    - outputs/v11_level1/aoi_temporal_aggregation/aoi_temporal_anchor_sensitivity.csv
    - outputs/v11_level1/aoi_temporal_aggregation/aoi_temporal_recommendation_matrix.csv
    - outputs/v11_level1/aoi_temporal_aggregation/sprint4d_aoi_temporal_aggregation_report.md
    - docs/v11/SystemA_AOI_temporal_aggregation_design_CN.md

Saved metrics:
    - Input schema, source, row, station, timestamp, dataset-label, missingness,
      quality-flag, sample/full, and retrospective-context audit.
    - Station coverage by timestamp and station-level cohort summaries.
    - Candidate AOI temporal severity aggregations from existing station-level
      retrospective diagnostics only.
    - Method distribution, correlation, difference, top-decile overlap, anchor,
      and high-event-station sensitivity diagnostics.
    - Recommendation matrix with allowed and forbidden downstream use.

This script does not train models, rerun M4/M7/full_dynamic, rerun probability
calibration, call APIs, modify archives, touch collector runtime, write cell-level
outputs, create local WBGT, create risk scores, integrate System B, use SOLWEIG,
or touch v12 outputs.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v11/system_a_aoi_temporal_aggregation_config.example.yaml"

DEFAULTS: dict[str, Any] = {
    "schema_version": "v1.1-sprint4d-aoi-temporal-aggregation",
    "aggregation_version": "v1.1-sprint4d-design-dry-run",
    "aoi_id": "ToaPayoh_or_OpenHeat_AOI_candidate",
    "inputs": {
        "station_diagnostic": "outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic.csv",
        "station_diagnostic_sample": "outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic_sample.csv",
        "fallback_probability_predictions": "outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv",
    },
    "output_dir": "outputs/v11_level1/aoi_temporal_aggregation",
    "design_doc": "docs/v11/SystemA_AOI_temporal_aggregation_design_CN.md",
    "dataset_selection": {
        "primary": "hourly_max",
        "secondary_optional": "hourly_mean",
        "include_secondary_when_primary_available": False,
    },
    "coverage": {
        "minimum_station_count_nominal": 20,
        "minimum_coverage_fraction": 0.80,
        "high_event_stations": ["S142", "S137", "S135"],
        "low_event_or_overprediction_sensitive_stations": ["S139", "S124"],
        "local_anchor_station": "S128",
    },
}

REQUIRED_OR_PREFERRED_COLUMNS = [
    "timestamp_sgt",
    "timestamp_utc",
    "station_id",
    "dataset_label",
    "wbgt_a_score_c",
    "wbgt_a_score_model_id",
    "p_ge31_diagnostic",
    "p_ge31_calibrator_id",
    "p_ge31_validation_context",
    "is_retrospective",
    "quality_flag",
]
OPTIONAL_COLUMNS = [
    "official_wbgt_c",
    "ge31_screening_flag_best_f1_optional",
    "ge31_screening_flag_high_recall_optional",
    "notes",
]
FORBIDDEN_OUTPUT_COLUMNS = {
    "cell_id",
    "local_wbgt_c",
    "wbgt_cell_c",
    "delta_wbgt_cell",
    "risk_score",
    "m_rad",
    "tmrt",
    "solweig",
    "exposure",
    "vulnerability",
}
HIGH_EVENT_STATIONS = {"S142", "S137", "S135"}
LOW_EVENT_OR_OVERPREDICTION_SENSITIVE_STATIONS = {"S139", "S124"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate existing System A station-level retrospective diagnostics "
            "into candidate AOI temporal severity signals. Writes CSV/Markdown "
            "audits under outputs/v11_level1/aoi_temporal_aggregation. Does not "
            "train models, rerun p_ge31 calibration, create local WBGT, create "
            "cell-level outputs, create risk scores, or integrate System B."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Config YAML path.")
    parser.add_argument("--input", type=Path, default=None, help="Optional existing station diagnostic CSV.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional output directory override.")
    return parser.parse_args()


def read_config(path: Path) -> dict[str, Any]:
    config = DEFAULTS.copy()
    if not path.exists():
        return config
    try:
        import yaml  # type: ignore
    except ImportError:
        return config
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return deep_merge(config, loaded)


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def repo_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


def select_input(config: dict[str, Any], override: Path | None) -> tuple[Path | None, str, bool]:
    if override is not None:
        return repo_path(override), "user_override", False

    inputs = config["inputs"]
    full_path = repo_path(inputs["station_diagnostic"])
    sample_path = repo_path(inputs["station_diagnostic_sample"])
    fallback_path = repo_path(inputs["fallback_probability_predictions"])

    if full_path.exists():
        return full_path, "full_station_diagnostic", False
    if sample_path.exists():
        return sample_path, "station_diagnostic_sample_only", True
    if fallback_path.exists():
        return fallback_path, "fallback_probability_predictions", False
    return None, "missing", False


def write_blocked_report(output_dir: Path, input_status: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = output_dir / "sprint4d_aoi_temporal_aggregation_report.md"
    report.write_text(
        "\n".join(
            [
                "# Sprint 4D - System A AOI Temporal Aggregation Design",
                "",
                "## Status",
                "BLOCKED",
                "",
                "## Reason",
                "No allowed existing p_ge31 station diagnostic input was found.",
                "",
                "## Input status",
                input_status,
                "",
                "## Actions not taken",
                "- No model training.",
                "- No M4/M7/full_dynamic rerun.",
                "- No p_ge31 probability calibration rerun.",
                "- No API calls.",
                "- No archive modification.",
                "- No System B, v12, SOLWEIG, local WBGT, cell-level, or risk outputs.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def read_input(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["wbgt_a_score_c", "p_ge31_diagnostic", "official_wbgt_c"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["timestamp_sgt", "timestamp_utc", "station_id", "dataset_label", "quality_flag"]:
        if col in out.columns:
            out[col] = out[col].astype("string")
    if "is_retrospective" in out.columns:
        out["is_retrospective_bool"] = out["is_retrospective"].map(to_bool)
    else:
        out["is_retrospective_bool"] = True
    return out


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def split_flags(series: pd.Series) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw in series.dropna().astype(str):
        for part in raw.split(";"):
            flag = part.strip()
            if flag:
                counts[flag] = counts.get(flag, 0) + 1
    return dict(sorted(counts.items()))


def join_counts(counts: dict[str, int]) -> str:
    return "; ".join(f"{key}:{value}" for key, value in counts.items())


def join_values(values: pd.Series | list[Any] | set[Any]) -> str:
    if isinstance(values, pd.Series):
        items = values.dropna().astype(str).unique().tolist()
    else:
        items = [str(item) for item in values if not pd.isna(item)]
    return ";".join(sorted(items))


def percentile(series: pd.Series, q: float) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return math.nan
    return float(clean.quantile(q))


def probability_any(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna().clip(0.0, 1.0)
    if clean.empty:
        return math.nan
    return float(1.0 - np.prod(1.0 - clean.to_numpy()))


def select_dataset_rows(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    labels = set(df["dataset_label"].dropna().astype(str)) if "dataset_label" in df.columns else set()
    primary = config["dataset_selection"].get("primary", "hourly_max")
    secondary = config["dataset_selection"].get("secondary_optional", "hourly_mean")
    include_secondary = bool(config["dataset_selection"].get("include_secondary_when_primary_available", False))

    if primary in labels:
        selected = [primary]
        if include_secondary and secondary in labels:
            selected.append(secondary)
    elif secondary in labels:
        selected = [secondary]
    else:
        selected = sorted(labels)

    mask = df["dataset_label"].astype(str).isin(selected) if selected else pd.Series(False, index=df.index)
    if "is_retrospective_bool" in df.columns:
        mask = mask & df["is_retrospective_bool"]
    return df.loc[mask].copy(), selected


def build_schema_audit(
    df: pd.DataFrame,
    filtered: pd.DataFrame,
    input_path: Path,
    input_status: str,
    sample_only: bool,
    selected_labels: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    missing_cols = [col for col in REQUIRED_OR_PREFERRED_COLUMNS if col not in df.columns]
    optional_missing = [col for col in OPTIONAL_COLUMNS if col not in df.columns]
    rows.extend(
        [
            {"metric": "input_path", "value": str(input_path.relative_to(ROOT) if input_path.is_relative_to(ROOT) else input_path)},
            {"metric": "input_status", "value": input_status},
            {"metric": "sample_only", "value": sample_only},
            {"metric": "full_station_diagnostic", "value": input_status == "full_station_diagnostic"},
            {"metric": "row_count", "value": len(df)},
            {"metric": "filtered_row_count", "value": len(filtered)},
            {"metric": "station_count", "value": df["station_id"].nunique(dropna=True) if "station_id" in df.columns else ""},
            {"metric": "filtered_station_count", "value": filtered["station_id"].nunique(dropna=True) if "station_id" in filtered.columns else ""},
            {"metric": "timestamp_count", "value": df["timestamp_sgt"].nunique(dropna=True) if "timestamp_sgt" in df.columns else ""},
            {
                "metric": "filtered_timestamp_count",
                "value": filtered["timestamp_sgt"].nunique(dropna=True) if "timestamp_sgt" in filtered.columns else "",
            },
            {"metric": "dataset_label_values", "value": join_values(df["dataset_label"]) if "dataset_label" in df.columns else ""},
            {"metric": "selected_dataset_labels", "value": ";".join(selected_labels)},
            {"metric": "missing_required_or_preferred_columns", "value": ";".join(missing_cols)},
            {"metric": "missing_optional_columns", "value": ";".join(optional_missing)},
        ]
    )
    for col in REQUIRED_OR_PREFERRED_COLUMNS:
        if col in df.columns:
            missing_count = int(df[col].isna().sum())
            rows.append({"metric": f"missing_count__{col}", "value": missing_count})
            rows.append({"metric": f"missing_fraction__{col}", "value": missing_count / len(df) if len(df) else math.nan})
    if "quality_flag" in df.columns:
        for flag, count in split_flags(df["quality_flag"]).items():
            rows.append({"metric": f"quality_flag_count__{flag}", "value": count})
    return pd.DataFrame(rows)


def build_coverage(filtered: pd.DataFrame, expected_stations: set[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = ["timestamp_sgt", "timestamp_utc", "dataset_label"]
    for keys, group in filtered.groupby(group_cols, dropna=False, sort=True):
        stations = sorted(group["station_id"].dropna().astype(str).unique().tolist())
        missing = sorted(expected_stations - set(stations))
        quality_counts = split_flags(group["quality_flag"]) if "quality_flag" in group.columns else {}
        rows.append(
            {
                "timestamp_sgt": keys[0],
                "timestamp_utc": keys[1],
                "dataset_label": keys[2],
                "station_count": len(stations),
                "stations_present": ";".join(stations),
                "missing_station_count": len(missing),
                "missing_stations": ";".join(missing),
                "station_coverage_fraction": len(stations) / len(expected_stations) if expected_stations else math.nan,
                "has_S128": "S128" in stations,
                "has_S142": "S142" in stations,
                "has_S137": "S137" in stations,
                "has_S135": "S135" in stations,
                "has_S139": "S139" in stations,
                "min_wbgt_a_score_c": group["wbgt_a_score_c"].min(skipna=True),
                "max_wbgt_a_score_c": group["wbgt_a_score_c"].max(skipna=True),
                "median_wbgt_a_score_c": group["wbgt_a_score_c"].median(skipna=True),
                "min_p_ge31_diagnostic": group["p_ge31_diagnostic"].min(skipna=True),
                "max_p_ge31_diagnostic": group["p_ge31_diagnostic"].max(skipna=True),
                "median_p_ge31_diagnostic": group["p_ge31_diagnostic"].median(skipna=True),
                "quality_flag_summary": join_counts(quality_counts),
            }
        )
    return pd.DataFrame(rows)


def build_station_cohort(filtered: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    has_observed = "official_wbgt_c" in filtered.columns
    for station_id, group in filtered.groupby("station_id", dropna=False, sort=True):
        station = str(station_id)
        notes: list[str] = []
        if station in HIGH_EVENT_STATIONS:
            notes.append("known high-event station from previous reports")
        if station in LOW_EVENT_OR_OVERPREDICTION_SENSITIVE_STATIONS:
            notes.append("known low-event / overprediction-sensitive station")
        observed_ge31 = ""
        if has_observed:
            observed_ge31 = int((group["official_wbgt_c"] >= 31.0).sum())
        rows.append(
            {
                "station_id": station,
                "n_rows": len(group),
                "p_ge31_mean": group["p_ge31_diagnostic"].mean(skipna=True),
                "p_ge31_p90": percentile(group["p_ge31_diagnostic"], 0.90),
                "wbgt_score_mean": group["wbgt_a_score_c"].mean(skipna=True),
                "wbgt_score_p90": percentile(group["wbgt_a_score_c"], 0.90),
                "observed_ge31_count": observed_ge31,
                "note": "; ".join(notes),
            }
        )
    return pd.DataFrame(rows)


def build_candidates(
    filtered: pd.DataFrame,
    coverage: pd.DataFrame,
    expected_stations: set[str],
    config: dict[str, Any],
    sample_only: bool,
    input_status: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = ["timestamp_sgt", "timestamp_utc", "dataset_label"]
    aggregation_version = config["aggregation_version"]
    aoi_id = config["aoi_id"]
    for keys, group in filtered.groupby(group_cols, dropna=False, sort=True):
        stations = sorted(group["station_id"].dropna().astype(str).unique().tolist())
        s128 = group[group["station_id"].astype(str) == "S128"]
        no_s142 = group[group["station_id"].astype(str) != "S142"]
        no_high = group[~group["station_id"].astype(str).isin(HIGH_EVENT_STATIONS)]
        quality_counts = split_flags(group["quality_flag"]) if "quality_flag" in group.columns else {}
        notes = [
            "candidate pending human review",
            "retrospective station-network diagnostic aggregation only",
            f"input_status={input_status}",
        ]
        if sample_only:
            notes.append("sample_only_not_suitable_for_final_aggregation")
        row = {
            "timestamp_sgt": keys[0],
            "timestamp_utc": keys[1],
            "dataset_label": keys[2],
            "aoi_id": aoi_id,
            "station_count": len(stations),
            "station_coverage_fraction": len(stations) / len(expected_stations) if expected_stations else math.nan,
            "stations_present": ";".join(stations),
            "aggregation_version": aggregation_version,
            "network_mean_wbgt_a_score_c": group["wbgt_a_score_c"].mean(skipna=True),
            "network_median_wbgt_a_score_c": group["wbgt_a_score_c"].median(skipna=True),
            "network_p75_wbgt_a_score_c": percentile(group["wbgt_a_score_c"], 0.75),
            "network_p90_wbgt_a_score_c": percentile(group["wbgt_a_score_c"], 0.90),
            "network_max_wbgt_a_score_c": group["wbgt_a_score_c"].max(skipna=True),
            "network_mean_p_ge31": group["p_ge31_diagnostic"].mean(skipna=True),
            "network_median_p_ge31": group["p_ge31_diagnostic"].median(skipna=True),
            "network_p75_p_ge31": percentile(group["p_ge31_diagnostic"], 0.75),
            "network_p90_p_ge31": percentile(group["p_ge31_diagnostic"], 0.90),
            "network_max_p_ge31": group["p_ge31_diagnostic"].max(skipna=True),
            "anchor_S128_wbgt_a_score_c": s128["wbgt_a_score_c"].iloc[0] if len(s128) else math.nan,
            "anchor_S128_p_ge31": s128["p_ge31_diagnostic"].iloc[0] if len(s128) else math.nan,
            "exclude_S142_network_p90_wbgt_a_score_c": percentile(no_s142["wbgt_a_score_c"], 0.90),
            "exclude_S142_network_p90_p_ge31": percentile(no_s142["p_ge31_diagnostic"], 0.90),
            "exclude_high_event_stations_network_p90_wbgt_a_score_c": percentile(no_high["wbgt_a_score_c"], 0.90),
            "exclude_high_event_stations_network_p90_p_ge31": percentile(no_high["p_ge31_diagnostic"], 0.90),
            "probability_any_independence_experimental": probability_any(group["p_ge31_diagnostic"]),
            "quality_flag": join_counts(quality_counts),
            "method_caveats": (
                "S128 anchor is sensitivity only and not AOI truth; network_max is upper-bound "
                "sensitivity only; probability_any assumes station independence and is disabled by default"
            ),
            "notes": "; ".join(notes),
        }
        rows.append(row)
    candidates = pd.DataFrame(rows)
    if not coverage.empty:
        coverage_cols = ["timestamp_sgt", "timestamp_utc", "dataset_label", "missing_station_count"]
        candidates = candidates.merge(coverage[coverage_cols], on=["timestamp_sgt", "timestamp_utc", "dataset_label"], how="left")
    return candidates


def candidate_columns(candidates: pd.DataFrame) -> list[str]:
    return [
        col
        for col in candidates.columns
        if (
            col.endswith("_p_ge31")
            or col.endswith("_wbgt_a_score_c")
            or col == "probability_any_independence_experimental"
        )
        and col not in {"anchor_S128_wbgt_a_score_c"}
    ] + (["anchor_S128_wbgt_a_score_c"] if "anchor_S128_wbgt_a_score_c" in candidates.columns else [])


def build_method_comparison(candidates: pd.DataFrame, low_station_threshold: int, coverage_threshold: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    numeric_cols = candidate_columns(candidates)
    low_station_count = int((candidates["station_count"] < low_station_threshold).sum()) if "station_count" in candidates else 0
    low_coverage_count = (
        int((candidates["station_coverage_fraction"] < coverage_threshold).sum()) if "station_coverage_fraction" in candidates else 0
    )
    for col in numeric_cols:
        values = pd.to_numeric(candidates[col], errors="coerce").dropna()
        rows.append(
            {
                "metric_kind": "series_summary",
                "candidate": col,
                "comparator": "",
                "n_timestamps": len(values),
                "mean": values.mean() if len(values) else math.nan,
                "p50": values.quantile(0.50) if len(values) else math.nan,
                "p90": values.quantile(0.90) if len(values) else math.nan,
                "max": values.max() if len(values) else math.nan,
                "value": "",
                "low_station_threshold": low_station_threshold,
                "low_station_count": low_station_count,
                "coverage_threshold": coverage_threshold,
                "low_coverage_count": low_coverage_count,
            }
        )

    corr_cols = [
        "network_median_p_ge31",
        "network_p90_p_ge31",
        "network_max_p_ge31",
        "anchor_S128_p_ge31",
        "network_median_wbgt_a_score_c",
        "network_p90_wbgt_a_score_c",
    ]
    available = [col for col in corr_cols if col in candidates.columns]
    for idx, left in enumerate(available):
        for right in available[idx + 1 :]:
            pair = candidates[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
            value = pair[left].corr(pair[right]) if len(pair) >= 2 else math.nan
            rows.append(
                {
                    "metric_kind": "correlation",
                    "candidate": left,
                    "comparator": right,
                    "n_timestamps": len(pair),
                    "mean": "",
                    "p50": "",
                    "p90": "",
                    "max": "",
                    "value": value,
                    "low_station_threshold": low_station_threshold,
                    "low_station_count": low_station_count,
                    "coverage_threshold": coverage_threshold,
                    "low_coverage_count": low_coverage_count,
                }
            )

    mad_pairs = [
        ("network_p90_p_ge31", "network_median_p_ge31"),
        ("anchor_S128_p_ge31", "network_median_p_ge31"),
        ("anchor_S128_p_ge31", "network_p90_p_ge31"),
        ("network_max_p_ge31", "network_p90_p_ge31"),
    ]
    for left, right in mad_pairs:
        if left in candidates.columns and right in candidates.columns:
            pair = candidates[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
            value = (pair[left] - pair[right]).abs().mean() if len(pair) else math.nan
            rows.append(
                {
                    "metric_kind": "mean_absolute_difference",
                    "candidate": left,
                    "comparator": right,
                    "n_timestamps": len(pair),
                    "mean": "",
                    "p50": "",
                    "p90": "",
                    "max": "",
                    "value": value,
                    "low_station_threshold": low_station_threshold,
                    "low_station_count": low_station_count,
                    "coverage_threshold": coverage_threshold,
                    "low_coverage_count": low_coverage_count,
                }
            )

    sensitivity_checks = [
        ("s142_exclusion_changes_p90_gt_0p05", "network_p90_p_ge31", "exclude_S142_network_p90_p_ge31"),
        (
            "high_event_exclusion_changes_p90_gt_0p05",
            "network_p90_p_ge31",
            "exclude_high_event_stations_network_p90_p_ge31",
        ),
    ]
    for metric, left, right in sensitivity_checks:
        pair = candidates[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
        value = int(((pair[left] - pair[right]).abs() > 0.05).sum()) if len(pair) else 0
        rows.append(
            {
                "metric_kind": metric,
                "candidate": left,
                "comparator": right,
                "n_timestamps": len(pair),
                "mean": "",
                "p50": "",
                "p90": "",
                "max": "",
                "value": value,
                "low_station_threshold": low_station_threshold,
                "low_station_count": low_station_count,
                "coverage_threshold": coverage_threshold,
                "low_coverage_count": low_coverage_count,
            }
        )
    return pd.DataFrame(rows)


def top_decile_indices(candidates: pd.DataFrame, col: str) -> set[int]:
    values = pd.to_numeric(candidates[col], errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return set()
    threshold = valid.quantile(0.90)
    return set(values[values >= threshold].index.tolist())


def build_top_decile_overlap(candidates: pd.DataFrame) -> pd.DataFrame:
    pairs = [
        ("network_median_p_ge31", "network_p90_p_ge31"),
        ("network_p90_p_ge31", "network_max_p_ge31"),
        ("anchor_S128_p_ge31", "network_median_p_ge31"),
        ("anchor_S128_p_ge31", "network_p90_p_ge31"),
    ]
    rows: list[dict[str, Any]] = []
    for left, right in pairs:
        left_set = top_decile_indices(candidates, left) if left in candidates.columns else set()
        right_set = top_decile_indices(candidates, right) if right in candidates.columns else set()
        overlap = left_set & right_set
        union = left_set | right_set
        rows.append(
            {
                "candidate_a": left,
                "candidate_b": right,
                "n_top_decile_a": len(left_set),
                "n_top_decile_b": len(right_set),
                "n_overlap": len(overlap),
                "jaccard_overlap": len(overlap) / len(union) if union else math.nan,
                "overlap_fraction_of_a": len(overlap) / len(left_set) if left_set else math.nan,
                "overlap_fraction_of_b": len(overlap) / len(right_set) if right_set else math.nan,
            }
        )
    return pd.DataFrame(rows)


def build_anchor_sensitivity(candidates: pd.DataFrame) -> pd.DataFrame:
    out = candidates[
        [
            "timestamp_sgt",
            "timestamp_utc",
            "dataset_label",
            "station_count",
            "network_median_p_ge31",
            "network_p90_p_ge31",
            "network_max_p_ge31",
            "anchor_S128_p_ge31",
            "exclude_S142_network_p90_p_ge31",
            "exclude_high_event_stations_network_p90_p_ge31",
        ]
    ].copy()
    out["anchor_minus_median_p_ge31"] = out["anchor_S128_p_ge31"] - out["network_median_p_ge31"]
    out["anchor_minus_p90_p_ge31"] = out["anchor_S128_p_ge31"] - out["network_p90_p_ge31"]
    out["max_minus_p90_p_ge31"] = out["network_max_p_ge31"] - out["network_p90_p_ge31"]
    out["s142_exclusion_delta_p90_p_ge31"] = out["exclude_S142_network_p90_p_ge31"] - out["network_p90_p_ge31"]
    out["high_event_exclusion_delta_p90_p_ge31"] = (
        out["exclude_high_event_stations_network_p90_p_ge31"] - out["network_p90_p_ge31"]
    )
    out["s142_exclusion_abs_delta_gt_0p05"] = out["s142_exclusion_delta_p90_p_ge31"].abs() > 0.05
    out["high_event_exclusion_abs_delta_gt_0p05"] = out["high_event_exclusion_delta_p90_p_ge31"].abs() > 0.05
    return out


def build_recommendation_matrix(metrics: dict[str, Any]) -> pd.DataFrame:
    p90_median_mad = metrics.get("p90_median_mad", math.nan)
    anchor_p90_mad = metrics.get("anchor_p90_mad", math.nan)
    s142_count = metrics.get("s142_delta_count", 0)
    high_count = metrics.get("high_delta_count", 0)
    rows = [
        {
            "candidate": "network_median_score",
            "recommended_status": "default_candidate",
            "use_case": "background AOI temporal severity candidate",
            "evidence_summary": "Median score is robust to single-station high tails; candidate pending human review.",
            "advantages": "Stable central station-network summary of wbgt_a_score_c.",
            "risks": "May understate spatially localized high station diagnostic severity.",
            "required_caveat": "Retrospective diagnostic aggregation only; not local WBGT.",
            "allowed_downstream_use": "Future System B temporal gate candidate after coupling review.",
            "forbidden_downstream_use": "Cell-level WBGT, risk score, official warning, prospective skill claim.",
        },
        {
            "candidate": "network_p90_p_ge31",
            "recommended_status": "default_candidate",
            "use_case": "conservative AOI event-gate candidate",
            "evidence_summary": f"Mean absolute p90-minus-median p_ge31 difference={p90_median_mad:.4f}; candidate pending human review.",
            "advantages": "Captures high-tail station-network diagnostic probability without using max.",
            "risks": "Sensitive to high-event stations and station coverage.",
            "required_caveat": "Retrospective diagnostic probability aggregation; not official warning probability.",
            "allowed_downstream_use": "Future conservative System B temporal gate candidate after human review.",
            "forbidden_downstream_use": "Operational alert, local WBGT, risk map, forecast skill claim.",
        },
        {
            "candidate": "anchor_S128",
            "recommended_status": "sensitivity_candidate",
            "use_case": "local-anchor sensitivity",
            "evidence_summary": f"Mean absolute S128-minus-p90 p_ge31 difference={anchor_p90_mad:.4f}; S128 is not validated AOI truth.",
            "advantages": "Provides a single-station local-anchor comparison when S128 exists.",
            "risks": "Single station may not represent Toa Payoh AOI; missing anchor rows can occur.",
            "required_caveat": "Sensitivity only; not validated as Toa Payoh AOI truth.",
            "allowed_downstream_use": "Sensitivity diagnostics in human review.",
            "forbidden_downstream_use": "Default AOI truth, local WBGT, official probability, risk score.",
        },
        {
            "candidate": "network_max",
            "recommended_status": "sensitivity_candidate",
            "use_case": "upper-bound sensitivity",
            "evidence_summary": "Max is expected to be more volatile than p90 and is retained only as an upper-bound check.",
            "advantages": "Shows strongest station diagnostic signal at each timestamp.",
            "risks": "Highly sensitive to outlier stations and quality issues.",
            "required_caveat": "Upper-bound sensitivity only; not a default gate.",
            "allowed_downstream_use": "Stress-test comparison.",
            "forbidden_downstream_use": "Default AOI aggregation, official warning, risk map.",
        },
        {
            "candidate": "probability_any_independence_experimental",
            "recommended_status": "experimental",
            "use_case": "disabled probability-composition experiment",
            "evidence_summary": "Computed for diagnostics only; assumes station independence.",
            "advantages": "Documents behavior of any-station event framing.",
            "risks": "Independence assumption is not justified for nearby weather stations.",
            "required_caveat": "Experimental and disabled by default.",
            "allowed_downstream_use": "Exploratory comparison only.",
            "forbidden_downstream_use": "Default AOI gate, official warning, forecast skill, risk map.",
        },
        {
            "candidate": "exclude_S142_p90_sensitivity",
            "recommended_status": "sensitivity_candidate",
            "use_case": "high-event-station sensitivity",
            "evidence_summary": f"S142 exclusion changed p90 by >0.05 at {s142_count} timestamps.",
            "advantages": "Checks whether S142 dominates conservative p90 behavior.",
            "risks": "Exclusion is not a final default and may remove real high-tail information.",
            "required_caveat": "Sensitivity only; not final station selection.",
            "allowed_downstream_use": "Human review of high-event station influence.",
            "forbidden_downstream_use": "Default exclusion without validation.",
        },
        {
            "candidate": "exclude_high_event_stations_p90_sensitivity",
            "recommended_status": "sensitivity_candidate",
            "use_case": "S142/S137/S135 high-event sensitivity",
            "evidence_summary": f"High-event station exclusion changed p90 by >0.05 at {high_count} timestamps.",
            "advantages": "Checks high-event station influence on conservative gate.",
            "risks": "Can suppress genuine severe station-network diagnostic signals.",
            "required_caveat": "Sensitivity only, not default.",
            "allowed_downstream_use": "Human review and robustness audit.",
            "forbidden_downstream_use": "Default exclusion, risk score, local WBGT, official warning.",
        },
    ]
    return pd.DataFrame(rows)


def extract_metric(method_comparison: pd.DataFrame, kind: str, left: str, right: str) -> float:
    mask = (
        (method_comparison["metric_kind"] == kind)
        & (method_comparison["candidate"] == left)
        & (method_comparison["comparator"] == right)
    )
    if not mask.any():
        return math.nan
    return float(pd.to_numeric(method_comparison.loc[mask, "value"], errors="coerce").iloc[0])


def extract_count(method_comparison: pd.DataFrame, kind: str) -> int:
    mask = method_comparison["metric_kind"] == kind
    if not mask.any():
        return 0
    return int(pd.to_numeric(method_comparison.loc[mask, "value"], errors="coerce").fillna(0).iloc[0])


def build_design_doc(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# System A AOI Temporal Aggregation Design",
                "",
                "## Status",
                "Design + retrospective dry-run / not System B integration.",
                "",
                "## Why needed",
                "Station diagnostic rows are not AOI temporal severity. System B needs a timestamp-level AOI temporal gate candidate before any coupling contract can be reviewed.",
                "",
                "## Inputs",
                "- Primary station diagnostic source: outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic.csv.",
                "- Sample-only source is allowed only for schema smoke checks and is not suitable for final aggregation.",
                "- Fallback source is outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv if no exported station diagnostic exists.",
                "- Contract context: configs/v11/system_a_level1_output_contract.yaml and System A Level 1 model-card outputs.",
                "",
                "## Candidate methods",
                "- network_mean: diagnostic average only.",
                "- network_median: background severity candidate using median score and probability.",
                "- network_p75: moderate-conservative station-network candidate.",
                "- network_p90: conservative event-gate candidate.",
                "- network_max: upper-bound sensitivity only.",
                "- anchor_S128: local-anchor sensitivity only if S128 exists; not validated as Toa Payoh AOI truth.",
                "- exclude_S142_network_p90: high-event-station sensitivity.",
                "- exclude_high_event_stations_network_p90: S142/S137/S135 sensitivity only, not default.",
                "- probability_any_independence_experimental: disabled-by-default experiment that assumes station independence.",
                "",
                "## Recommended candidate set",
                "- network_median_wbgt_a_score_c as background severity candidate pending human review.",
                "- network_p90_p_ge31 as conservative event-gate candidate pending human review.",
                "- anchor_S128 as sensitivity only.",
                "- network_max as upper-bound sensitivity only.",
                "",
                "## Claim boundaries",
                "Allowed:",
                "- AOI temporal severity candidate.",
                "- Retrospective diagnostic aggregation.",
                "- Future System B temporal gate candidate.",
                "",
                "Forbidden:",
                "- Local WBGT.",
                "- Cell-level WBGT.",
                "- Risk score.",
                "- Official warning probability.",
                "- Prospective forecast skill.",
                "- System B integration completed.",
                "",
                "## What remains unresolved",
                "- Final AOI aggregation selection.",
                "- System B coupling contract.",
                "- Prospective evaluation.",
                "- Actual AOI validation.",
                "- Exposure/vulnerability risk layer.",
                "",
                "## Next step",
                "System A/System B coupling contract after human review, or System B target robustness audit.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def build_report(
    path: Path,
    input_path: Path,
    input_status: str,
    sample_only: bool,
    filtered: pd.DataFrame,
    coverage: pd.DataFrame,
    candidates: pd.DataFrame,
    method_comparison: pd.DataFrame,
    top_overlap: pd.DataFrame,
    anchor_sensitivity: pd.DataFrame,
) -> None:
    row_count = len(filtered)
    station_count = filtered["station_id"].nunique(dropna=True) if "station_id" in filtered else 0
    timestamp_count = filtered["timestamp_sgt"].nunique(dropna=True) if "timestamp_sgt" in filtered else 0
    dataset_labels = join_values(filtered["dataset_label"]) if "dataset_label" in filtered else ""
    coverage_mean = coverage["station_coverage_fraction"].mean() if "station_coverage_fraction" in coverage else math.nan
    station_count_min = int(coverage["station_count"].min()) if not coverage.empty else 0
    station_count_max = int(coverage["station_count"].max()) if not coverage.empty else 0
    p90_median_mad = extract_metric(
        method_comparison, "mean_absolute_difference", "network_p90_p_ge31", "network_median_p_ge31"
    )
    anchor_p90_mad = extract_metric(
        method_comparison, "mean_absolute_difference", "anchor_S128_p_ge31", "network_p90_p_ge31"
    )
    max_p90_mad = extract_metric(method_comparison, "mean_absolute_difference", "network_max_p_ge31", "network_p90_p_ge31")
    s142_count = extract_count(method_comparison, "s142_exclusion_changes_p90_gt_0p05")
    high_count = extract_count(method_comparison, "high_event_exclusion_changes_p90_gt_0p05")
    median_p90_overlap = top_overlap[
        (top_overlap["candidate_a"] == "network_median_p_ge31") & (top_overlap["candidate_b"] == "network_p90_p_ge31")
    ]
    median_p90_jaccard = (
        float(median_p90_overlap["jaccard_overlap"].iloc[0]) if len(median_p90_overlap) else math.nan
    )
    anchor_available = int(candidates["anchor_S128_p_ge31"].notna().sum()) if "anchor_S128_p_ge31" in candidates else 0
    quality_summary = join_counts(split_flags(filtered["quality_flag"])) if "quality_flag" in filtered else ""
    status = "PASS" if not sample_only and row_count > 0 else "PARTIAL"

    path.write_text(
        "\n".join(
            [
                "# Sprint 4D - System A AOI Temporal Aggregation Design",
                "",
                "## Status",
                status,
                "",
                "## Scope",
                "- System A Level 1 interface only.",
                "- Retrospective aggregation only.",
                "- No model training.",
                "- No System B integration.",
                "- No local WBGT.",
                "- No risk map.",
                "",
                "## Inputs",
                f"- Input file: {input_path.relative_to(ROOT) if input_path.is_relative_to(ROOT) else input_path}.",
                f"- Input status: {input_status}.",
                f"- Sample-only: {sample_only}.",
                f"- Filtered rows: {row_count}.",
                f"- Station count: {station_count}.",
                f"- Timestamp count: {timestamp_count}.",
                f"- Dataset labels used: {dataset_labels}.",
                "",
                "## Coverage",
                f"- Station count per timestamp ranged from {station_count_min} to {station_count_max}.",
                f"- Mean station coverage fraction: {coverage_mean:.3f}.",
                f"- Quality flags: {quality_summary}.",
                f"- S128 anchor rows available for {anchor_available} candidate timestamps.",
                "",
                "## Candidate methods",
                "- network_mean, network_median, network_p75, network_p90, and network_max are station-network diagnostic aggregations.",
                "- anchor_S128 is retained as local-anchor sensitivity only.",
                "- exclude_S142 and exclude_high_event_stations p90 variants are high-event-station sensitivities only.",
                "- probability_any_independence_experimental is computed as a disabled-by-default diagnostic and assumes station independence.",
                "",
                "## Comparison findings",
                f"- Mean absolute network_p90_p_ge31 vs network_median_p_ge31 difference: {p90_median_mad:.4f}.",
                f"- Mean absolute anchor_S128_p_ge31 vs network_p90_p_ge31 difference: {anchor_p90_mad:.4f}.",
                f"- Mean absolute network_max_p_ge31 vs network_p90_p_ge31 difference: {max_p90_mad:.4f}.",
                f"- Median-vs-p90 top-decile Jaccard overlap: {median_p90_jaccard:.4f}.",
                f"- S142 exclusion changed p90 by >0.05 at {s142_count} timestamps.",
                f"- High-event-station exclusion changed p90 by >0.05 at {high_count} timestamps.",
                "- p_ge31 aggregation should be interpreted as diagnostic probability aggregation, not official warning probability.",
                "- wbgt_a_score_c aggregation should be interpreted as score aggregation, not local WBGT.",
                "",
                "## Recommendation",
                "- Background severity candidate: network_median_wbgt_a_score_c, pending human review.",
                "- Conservative event-gate candidate: network_p90_p_ge31, pending human review.",
                "- Sensitivity candidates: anchor_S128, network_max, exclude_S142 p90, and exclude_high_event_stations p90.",
                "- Experimental only: probability_any_independence_experimental.",
                "",
                "## Downstream contract implications",
                "The dry-run can inform a later System A/System B coupling contract by offering timestamp-level AOI temporal gate candidates. It cannot be passed downstream as local WBGT, cell-level hazard, risk score, official warning probability, or prospective forecast skill.",
                "",
                "## Caveats",
                "- Retrospective only.",
                "- Station-network diagnostic aggregation only.",
                "- Not local WBGT.",
                "- Not prospective.",
                "- Not risk.",
                "- Aggregation is not validated as true Toa Payoh WBGT.",
                "- No final default aggregation is claimed; candidates remain pending human review.",
                "",
                "## Next recommended action",
                "AOI aggregation human review, followed by System A/System B coupling contract or System B target robustness audit.",
                "",
                "## Run safeguards",
                "- No forbidden files touched.",
                "- No model training.",
                "- No System B/v12/SOLWEIG touched.",
                "- No archive modification.",
                "- No API calls.",
                "- No commit/stage performed.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def assert_no_forbidden_columns(df: pd.DataFrame) -> None:
    forbidden = sorted(FORBIDDEN_OUTPUT_COLUMNS & set(df.columns))
    if forbidden:
        raise ValueError(f"Forbidden output columns present: {forbidden}")


def main() -> int:
    args = parse_args()
    config = read_config(repo_path(args.config))
    output_dir = repo_path(args.output_dir or config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path, input_status, sample_only = select_input(config, args.input)
    if input_path is None or not input_path.exists():
        write_blocked_report(output_dir, input_status)
        print("BLOCKED: no allowed existing station diagnostic input found.")
        return 0

    df = normalize_frame(read_input(input_path))
    filtered, selected_labels = select_dataset_rows(df, config)
    expected_stations = set(filtered["station_id"].dropna().astype(str).unique().tolist()) if "station_id" in filtered else set()
    expected_station_count = len(expected_stations)
    nominal_threshold = int(config["coverage"].get("minimum_station_count_nominal", 20))
    if expected_station_count and expected_station_count < nominal_threshold:
        low_station_threshold = max(1, math.floor(expected_station_count * 0.8))
    else:
        low_station_threshold = nominal_threshold
    coverage_threshold = float(config["coverage"].get("minimum_coverage_fraction", 0.80))

    schema_audit = build_schema_audit(df, filtered, input_path, input_status, sample_only, selected_labels)
    coverage = build_coverage(filtered, expected_stations)
    station_cohort = build_station_cohort(filtered)
    candidates = build_candidates(filtered, coverage, expected_stations, config, sample_only, input_status)
    assert_no_forbidden_columns(candidates)
    method_comparison = build_method_comparison(candidates, low_station_threshold, coverage_threshold)
    top_overlap = build_top_decile_overlap(candidates)
    anchor_sensitivity = build_anchor_sensitivity(candidates)

    metrics = {
        "p90_median_mad": extract_metric(
            method_comparison, "mean_absolute_difference", "network_p90_p_ge31", "network_median_p_ge31"
        ),
        "anchor_p90_mad": extract_metric(
            method_comparison, "mean_absolute_difference", "anchor_S128_p_ge31", "network_p90_p_ge31"
        ),
        "s142_delta_count": extract_count(method_comparison, "s142_exclusion_changes_p90_gt_0p05"),
        "high_delta_count": extract_count(method_comparison, "high_event_exclusion_changes_p90_gt_0p05"),
    }
    recommendation = build_recommendation_matrix(metrics)

    schema_audit.to_csv(output_dir / "aoi_input_schema_audit.csv", index=False)
    coverage.to_csv(output_dir / "aoi_station_coverage_by_timestamp.csv", index=False)
    station_cohort.to_csv(output_dir / "aoi_station_cohort_summary.csv", index=False)
    candidates.to_csv(output_dir / "aoi_temporal_aggregation_candidates.csv", index=False)
    method_comparison.to_csv(output_dir / "aoi_temporal_method_comparison.csv", index=False)
    top_overlap.to_csv(output_dir / "aoi_temporal_top_decile_overlap.csv", index=False)
    anchor_sensitivity.to_csv(output_dir / "aoi_temporal_anchor_sensitivity.csv", index=False)
    recommendation.to_csv(output_dir / "aoi_temporal_recommendation_matrix.csv", index=False)
    build_design_doc(repo_path(config["design_doc"]))
    build_report(
        output_dir / "sprint4d_aoi_temporal_aggregation_report.md",
        input_path,
        input_status,
        sample_only,
        filtered,
        coverage,
        candidates,
        method_comparison,
        top_overlap,
        anchor_sensitivity,
    )
    print(f"PASS: wrote Sprint 4D AOI temporal aggregation outputs to {output_dir.relative_to(ROOT)}")
    print(f"input_status={input_status}; sample_only={sample_only}; rows={len(filtered)}; timestamps={len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
