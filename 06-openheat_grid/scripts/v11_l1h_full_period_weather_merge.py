#!/usr/bin/env python
"""System A A-L1H.0c full-period weather-regime residual merge.

Inputs:
    - configs/v11/systema_l1h_full_period_weather_merge.yaml
    - outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv
    - outputs/v11_systema_l1_high_tail/weather_regime_merge_inputs/best_weather_feature_source.csv.gz
    - Optional preflight inventory and configured fallback weather tables.

Outputs:
    - full_period_weather_source_inventory.csv
    - residual_weather_merge_full_period.csv
    - residual_by_weather_regime_full_period.csv
    - ge31_miss_by_weather_regime_full_period.csv
    - weather_regime_full_period_decision_report.md
    - A_L1H_0C_STATUS.md

Saved metrics:
    - Weather-source inventory with provenance, recovered columns, station/hour
      overlap, row retention, observed ge31 coverage, and station coverage.
    - Residual and fixed ge31 miss summaries by weather-regime bins using matched
      residual rows only.
    - Full-period decision status and weather-regime interaction classification.

This script consumes existing residual diagnostics and recovered weather features
only. It does not train models, implement formula-v2, calibrate probabilities,
run high-tail regression, start A-L2, touch System B, or touch SOLWEIG/raster/
archive hot paths.
"""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SGT_TZ = "Asia/Singapore"
LOW_MID_HIGH = ["low", "mid", "high"]
FOUR_BIN_LABELS = ["low", "mid", "high", "very_high"]
WEATHER_BIN_SPECS = {
    "shortwave_radiation": "shortwave_bin",
    "shortwave_3h_mean": "shortwave_3h_mean_bin",
    "relative_humidity_2m": "humidity_bin",
    "wind_speed_10m": "wind_bin",
    "temperature_2m": "temperature_bin",
    "cloud_cover": "cloud_cover_bin",
    "direct_radiation": "direct_radiation_bin",
    "diffuse_radiation": "diffuse_radiation_bin",
}
WEATHER_REGIME_DIAGNOSTIC_NOTE = (
    "Weather-regime diagnostic coverage: PASS_FULL_PERIOD. Radiation-hot regimes contain nearly all observed ge31 "
    "events and misses, but conditional miss-rate enrichment beyond the observed-ge31 base rate is mixed. This "
    "supports full-period weather-regime diagnostic evidence, not causal proof. The dominant issue remains global "
    "high-tail score compression, with station-specific bias and weather-regime structure as interacting diagnostics."
)


@dataclass(frozen=True)
class CandidateEvaluation:
    """Weather-source fit and provenance for one candidate."""

    role: str
    path: Path
    exists: bool
    readable: bool
    row_count: int
    station_column: str | None
    time_column: str | None
    recovered_weather_columns: list[str]
    unique_weather_keys: int
    matched_residual_rows: int
    retention_rate: float
    matched_observed_ge31_rows: int
    observed_ge31_coverage_rate: float
    matched_ge31_miss_rows: int
    station_coverage_count: int
    station_coverage_rate: float
    source_base: str
    source_relative_path: str
    reason: str
    error: str


@dataclass(frozen=True)
class MergeResult:
    """Headline result from the full-period weather merge."""

    status: str
    selected_weather_source: str | None
    selected_source_base: str
    selected_source_relative_path: str
    merge_keys: str
    total_residual_rows: int
    matched_rows: int
    unmatched_rows: int
    retention_rate: float
    total_observed_ge31_rows: int
    matched_observed_ge31_rows: int
    matched_observed_ge31_primary_rows: int
    matched_unique_observed_ge31_events: int
    total_unique_observed_ge31_events: int
    matched_ge31_miss_rows: int
    matched_ge31_miss_primary_rows: int
    station_coverage_count: int
    total_stations: int
    recovered_weather_columns: list[str]
    missing_weather_columns: list[str]
    weather_regime_classification: str
    weather_regime_note: str
    next_recommended_action: str
    output_paths: list[Path]


def rel(path: Path) -> str:
    """Return a repo-relative POSIX path where possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def local_preflight_path_label(raw_path: Any) -> str:
    """Label local-only preflight paths without exposing machine-specific roots."""
    return "local_preflight_path_omitted" if str(raw_path or "").strip() else ""


def resolve_path(raw_path: str) -> Path:
    """Resolve an absolute or repo-relative path."""
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


def parse_scalar(value: str) -> Any:
    """Parse the small scalar subset used by the explicit lane config."""
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
    """Parse the narrow YAML subset used by this config file."""
    raw_lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        raw_lines.append((indent, raw.strip()))

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    for index, (indent, stripped) in enumerate(raw_lines):
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Unexpected YAML list item: {stripped}")
            parent.append(parse_scalar(stripped[2:].strip()))
            continue

        key, separator, value = stripped.partition(":")
        if separator == "":
            raise ValueError(f"Unexpected YAML line: {stripped}")
        key = key.strip()
        value = value.strip()
        if value:
            if not isinstance(parent, dict):
                raise ValueError(f"Unexpected YAML mapping under list: {stripped}")
            parent[key] = parse_scalar(value)
            continue

        next_line = raw_lines[index + 1][1] if index + 1 < len(raw_lines) else ""
        next_container: dict[str, Any] | list[Any] = [] if next_line.startswith("- ") else {}
        if not isinstance(parent, dict):
            raise ValueError(f"Unexpected YAML nested mapping under list: {stripped}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def load_config(path: Path) -> dict[str, Any]:
    """Read the explicit lane config."""
    return parse_simple_yaml(path.read_text(encoding="utf-8"))


def git_branch() -> str:
    """Return the current git branch when available."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def first_present(columns: list[str], aliases: list[str]) -> str | None:
    """Return the first configured alias present in the table columns."""
    column_set = set(columns)
    for alias in aliases:
        if alias in column_set:
            return alias
    return None


def parse_sgt_hour(series: pd.Series, column_name: str) -> pd.Series:
    """Normalize a timestamp column to an SGT hourly merge-key string."""
    parsed = pd.to_datetime(series, errors="coerce")
    try:
        parsed_tz = parsed.dt.tz
    except AttributeError:
        parsed_tz = None

    if parsed_tz is not None:
        sgt = parsed.dt.tz_convert(SGT_TZ)
    elif "utc" in column_name.lower():
        sgt = pd.to_datetime(series, errors="coerce", utc=True).dt.tz_convert(SGT_TZ)
    else:
        sgt = parsed.dt.tz_localize(SGT_TZ, nonexistent="NaT", ambiguous="NaT")
    return sgt.dt.floor("h").dt.strftime("%Y-%m-%d %H:%M:%S%z")


def as_bool(series: pd.Series) -> pd.Series:
    """Convert bool-like values to a filled boolean Series."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes", "y"})


def normalize_residual_keys(residual: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str, str]:
    """Add merge keys to the residual input."""
    out = residual.copy()
    station_col = first_present(out.columns.tolist(), config["schema"]["station_columns"])
    time_col = first_present(out.columns.tolist(), config["schema"]["residual_time_columns"])
    if station_col is None or time_col is None:
        raise ValueError("Residual input lacks configured station or timestamp columns.")
    out["merge_station_id"] = out[station_col].astype(str)
    out["merge_time_sgt_hour"] = parse_sgt_hour(out[time_col], time_col)
    out["merge_key_available"] = out["merge_station_id"].ne("") & out["merge_time_sgt_hour"].notna()
    return out, station_col, time_col


def read_best_source_note(path: Path) -> dict[str, str]:
    """Read BEST_SOURCE key-value provenance when present."""
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    return values


def candidate_paths(config: dict[str, Any], preflight: pd.DataFrame | None) -> list[tuple[str, Path]]:
    """Build ordered candidate paths without requiring original diagnostics inputs."""
    seen: set[Path] = set()
    ordered: list[tuple[str, Path]] = []

    preferred = resolve_path(str(config["inputs"]["preferred_weather_source"]))
    ordered.append(("preferred_compact_recovered_source", preferred))
    seen.add(preferred.resolve())

    for raw in config["inputs"].get("fallback_weather_paths", []):
        path = resolve_path(str(raw))
        key = path.resolve()
        if key not in seen:
            ordered.append(("configured_fallback", path))
            seen.add(key)

    if preflight is not None and {"base", "relative_path", "exists"}.issubset(preflight.columns):
        for _, row in preflight.iterrows():
            if str(row.get("base", "")).lower() != "al1h":
                continue
            if str(row.get("exists", "")).lower() not in {"true", "yes", "1"}:
                continue
            path = resolve_path(str(row["relative_path"]))
            key = path.resolve()
            if key not in seen:
                ordered.append(("preflight_available_fallback", path))
                seen.add(key)
    return ordered


def read_preflight(config: dict[str, Any]) -> pd.DataFrame | None:
    """Read the optional preflight inventory."""
    path = resolve_path(str(config["inputs"]["preflight_inventory"]))
    if not path.exists():
        return None
    return pd.read_csv(path)


def read_csv_any(path: Path) -> pd.DataFrame:
    """Read a CSV or CSV.GZ table."""
    return pd.read_csv(path, compression="infer")


def add_shortwave_3h_mean(weather: pd.DataFrame) -> pd.DataFrame:
    """Recover a station-wise rolling 3-hour shortwave mean when absent."""
    if "shortwave_3h_mean" in weather.columns or "shortwave_radiation" not in weather.columns:
        return weather
    out = weather.copy()
    out["_shortwave_numeric"] = pd.to_numeric(out["shortwave_radiation"], errors="coerce")
    out["_time_sort"] = pd.to_datetime(out["merge_time_sgt_hour"], format="%Y-%m-%d %H:%M:%S%z", errors="coerce")
    out = out.sort_values(["merge_station_id", "_time_sort"])
    out["shortwave_3h_mean"] = (
        out.groupby("merge_station_id")["_shortwave_numeric"]
        .transform(lambda s: s.rolling(window=3, min_periods=1).mean())
    )
    return out.drop(columns=["_shortwave_numeric", "_time_sort"])


def normalize_weather(
    path: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str, str, list[str], str, str]:
    """Normalize a weather source to one row per station/hour merge key."""
    raw = read_csv_any(path)
    station_col = first_present(raw.columns.tolist(), config["schema"]["station_columns"])
    time_col = first_present(raw.columns.tolist(), config["schema"]["weather_time_columns"])
    if station_col is None or time_col is None:
        raise ValueError("missing configured station or weather timestamp column")

    configured_weather = list(config["schema"]["weather_columns"])
    present_weather = [col for col in configured_weather if col in raw.columns]
    if not present_weather:
        raise ValueError("no configured weather columns found")

    source_cols = [col for col in ["source_base", "source_relative_path"] if col in raw.columns]
    keep_cols = [station_col, time_col, *present_weather, *source_cols]
    out = raw[keep_cols].copy()
    out["merge_station_id"] = out[station_col].astype(str)
    out["merge_time_sgt_hour"] = parse_sgt_hour(out[time_col], time_col)
    for col in present_weather:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = add_shortwave_3h_mean(out)

    recovered = [col for col in configured_weather if col in out.columns and out[col].notna().any()]
    if not recovered:
        raise ValueError("configured weather columns are all empty")

    aggregate: dict[str, str] = {col: "mean" for col in recovered}
    for col in source_cols:
        aggregate[col] = "first"
    normalized = (
        out.dropna(subset=["merge_station_id", "merge_time_sgt_hour"])
        .groupby(["merge_station_id", "merge_time_sgt_hour"], as_index=False)
        .agg(aggregate)
    )

    source_base = ""
    source_relative_path = ""
    if "source_base" in normalized.columns:
        source_base = str(normalized["source_base"].dropna().iloc[0]) if normalized["source_base"].notna().any() else ""
    if "source_relative_path" in normalized.columns:
        values = normalized["source_relative_path"].dropna()
        source_relative_path = str(values.iloc[0]) if not values.empty else ""
    return normalized, station_col, time_col, recovered, source_base, source_relative_path


def evaluate_candidate(
    role: str,
    path: Path,
    residual: pd.DataFrame,
    config: dict[str, Any],
    best_source_note: dict[str, str],
) -> tuple[CandidateEvaluation, pd.DataFrame | None]:
    """Evaluate one weather candidate against residual station/hour keys."""
    exists = path.exists()
    size_limit = float(config["inputs"].get("max_source_size_mb", 25)) * 1024 * 1024
    readable = bool(exists and path.stat().st_size <= size_limit)
    if not exists:
        return empty_candidate(role, path, "missing", "file does not exist")
    if not readable:
        return empty_candidate(role, path, "not_read", "over configured size limit")

    try:
        weather, station_col, time_col, recovered, source_base, source_relative_path = normalize_weather(path, config)
        if not source_base and role == "preferred_compact_recovered_source":
            source_base = best_source_note.get("base", "")
        if not source_relative_path and role == "preferred_compact_recovered_source":
            source_relative_path = best_source_note.get("relative_path", "")

        weather_keys = weather[["merge_station_id", "merge_time_sgt_hour"]].drop_duplicates()
        residual_match = residual[["merge_station_id", "merge_time_sgt_hour", "obs_ge31", "ge31_event_class", "station_id"]].copy()
        residual_match["_residual_row_index"] = np.arange(len(residual_match))
        matched = residual_match.merge(
            weather_keys.assign(_has_weather_key=True),
            on=["merge_station_id", "merge_time_sgt_hour"],
            how="left",
        )
        has_match = matched["_has_weather_key"].fillna(False).astype(bool)
        obs_ge31 = as_bool(matched["obs_ge31"])
        miss = matched["ge31_event_class"].astype(str).eq("miss")
        matched_station_count = int(matched.loc[has_match, "station_id"].nunique())
        total_stations = max(int(residual["station_id"].nunique()), 1)
        matched_obs = int((has_match & obs_ge31).sum())
        total_obs = int(obs_ge31.sum())
        evaluation = CandidateEvaluation(
            role=role,
            path=path,
            exists=True,
            readable=True,
            row_count=int(len(weather)),
            station_column=station_col,
            time_column=time_col,
            recovered_weather_columns=recovered,
            unique_weather_keys=int(len(weather_keys)),
            matched_residual_rows=int(has_match.sum()),
            retention_rate=float(has_match.mean()) if len(has_match) else 0.0,
            matched_observed_ge31_rows=matched_obs,
            observed_ge31_coverage_rate=matched_obs / total_obs if total_obs else 0.0,
            matched_ge31_miss_rows=int((has_match & miss).sum()),
            station_coverage_count=matched_station_count,
            station_coverage_rate=matched_station_count / total_stations,
            source_base=source_base,
            source_relative_path=source_relative_path,
            reason="usable",
            error="",
        )
        return evaluation, weather
    except Exception as exc:
        return empty_candidate(role, path, "read_or_normalize_failed", str(exc))


def empty_candidate(role: str, path: Path, reason: str, error: str) -> tuple[CandidateEvaluation, None]:
    """Build a non-usable candidate evaluation."""
    exists = path.exists()
    return (
        CandidateEvaluation(
            role=role,
            path=path,
            exists=exists,
            readable=False,
            row_count=0,
            station_column=None,
            time_column=None,
            recovered_weather_columns=[],
            unique_weather_keys=0,
            matched_residual_rows=0,
            retention_rate=0.0,
            matched_observed_ge31_rows=0,
            observed_ge31_coverage_rate=0.0,
            matched_ge31_miss_rows=0,
            station_coverage_count=0,
            station_coverage_rate=0.0,
            source_base="",
            source_relative_path="",
            reason=reason,
            error=error,
        ),
        None,
    )


def candidate_to_row(candidate: CandidateEvaluation, selected: bool) -> dict[str, Any]:
    """Convert an evaluated candidate to an inventory row."""
    relative_path = rel(candidate.path)
    return {
        "inventory_role": candidate.role,
        "evaluation_mode": "evaluated_current_run",
        "path": relative_path,
        "relative_path": relative_path,
        "local_preflight_path": "",
        "exists": candidate.exists,
        "readable": candidate.readable,
        "row_count": candidate.row_count,
        "station_column": candidate.station_column or "",
        "time_column": candidate.time_column or "",
        "recovered_weather_columns": "|".join(candidate.recovered_weather_columns),
        "unique_weather_keys": candidate.unique_weather_keys,
        "matched_residual_rows": candidate.matched_residual_rows,
        "retention_rate": candidate.retention_rate,
        "matched_observed_ge31_rows": candidate.matched_observed_ge31_rows,
        "observed_ge31_coverage_rate": candidate.observed_ge31_coverage_rate,
        "matched_ge31_miss_rows": candidate.matched_ge31_miss_rows,
        "station_coverage_count": candidate.station_coverage_count,
        "station_coverage_rate": candidate.station_coverage_rate,
        "source_base": candidate.source_base,
        "source_relative_path": candidate.source_relative_path,
        "selected_for_merge": selected,
        "matches_selected_provenance": selected,
        "reason": candidate.reason,
        "error": candidate.error,
    }


def preflight_reference_rows(preflight: pd.DataFrame | None, selected_source_relative_path: str) -> list[dict[str, Any]]:
    """Convert preflight inventory rows into provenance-preserving references."""
    if preflight is None:
        return []
    rows: list[dict[str, Any]] = []
    for _, item in preflight.iterrows():
        relative_path = str(item.get("relative_path", ""))
        local_preflight_path = local_preflight_path_label(item.get("local_preflight_path", item.get("path", "")))
        rows.append(
            {
                "inventory_role": "preflight_reference",
                "evaluation_mode": "preflight_reference_not_loaded",
                "path": relative_path,
                "relative_path": relative_path,
                "local_preflight_path": local_preflight_path,
                "exists": item.get("exists", ""),
                "readable": item.get("readable", ""),
                "row_count": item.get("row_count", ""),
                "station_column": item.get("station_column", ""),
                "time_column": item.get("time_column", ""),
                "recovered_weather_columns": item.get("weather_columns", ""),
                "unique_weather_keys": item.get("unique_weather_keys", ""),
                "matched_residual_rows": item.get("matched_residual_rows", ""),
                "retention_rate": item.get("retention_rate", ""),
                "matched_observed_ge31_rows": "",
                "observed_ge31_coverage_rate": "",
                "matched_ge31_miss_rows": "",
                "station_coverage_count": "",
                "station_coverage_rate": "",
                "source_base": item.get("base", ""),
                "source_relative_path": relative_path,
                "selected_for_merge": False,
                "matches_selected_provenance": relative_path == selected_source_relative_path,
                "reason": "preflight provenance reference",
                "error": item.get("error", ""),
            }
        )
    return rows


def choose_candidate(candidates: list[CandidateEvaluation], config: dict[str, Any]) -> CandidateEvaluation | None:
    """Choose the preferred compact source when usable, otherwise highest retention."""
    min_columns = int(config["analysis"].get("minimum_regime_column_count", 3))
    minimum_columns = set(config["schema"]["minimum_regime_columns"])

    def usable(candidate: CandidateEvaluation) -> bool:
        recovered_minimum = minimum_columns.intersection(candidate.recovered_weather_columns)
        return candidate.reason == "usable" and len(recovered_minimum) >= min_columns and candidate.matched_residual_rows > 0

    preferred = next((item for item in candidates if item.role == "preferred_compact_recovered_source"), None)
    if preferred is not None and usable(preferred):
        return preferred
    usable_candidates = [item for item in candidates if usable(item)]
    if not usable_candidates:
        return None
    return sorted(
        usable_candidates,
        key=lambda item: (item.retention_rate, len(item.recovered_weather_columns), item.matched_residual_rows),
        reverse=True,
    )[0]


def quantile_bin(series: pd.Series, min_rows_4_bins: int) -> pd.Series:
    """Create low/mid/high or four-bin labels from matched numeric values."""
    numeric = pd.to_numeric(series, errors="coerce")
    valid_count = int(numeric.notna().sum())
    if valid_count < 6 or numeric.nunique(dropna=True) < 3:
        return pd.Series("missing", index=series.index, dtype="object")
    n_bins = 4 if valid_count >= min_rows_4_bins and numeric.nunique(dropna=True) >= 4 else 3
    labels = FOUR_BIN_LABELS if n_bins == 4 else LOW_MID_HIGH
    ranked = numeric.rank(method="first")
    binned = pd.qcut(ranked, q=n_bins, labels=labels, duplicates="drop")
    return binned.astype("object").where(binned.notna(), "missing")


def add_regimes(
    merged: pd.DataFrame,
    recovered_weather_columns: list[str],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Add configured weather-regime bins using matched rows only."""
    out = merged.copy()
    matched = out["has_weather_match"].astype(bool)
    min_rows = int(config["analysis"].get("quantile_regime_min_rows_4_bins", 120))
    regime_cols: list[str] = []
    notes: list[str] = []

    for weather_col, bin_col in WEATHER_BIN_SPECS.items():
        if weather_col not in recovered_weather_columns or weather_col not in out.columns:
            continue
        out[bin_col] = "missing"
        out.loc[matched, bin_col] = quantile_bin(out.loc[matched, weather_col], min_rows).values
        if not out.loc[matched, bin_col].eq("missing").all():
            regime_cols.append(bin_col)

    high_labels = {"high", "very_high"}
    radiation_bin_cols = [col for col in ["shortwave_bin", "shortwave_3h_mean_bin", "direct_radiation_bin", "diffuse_radiation_bin"] if col in out.columns]
    if "temperature_bin" in out.columns and radiation_bin_cols:
        out["combined_radiation_hot_regime"] = "missing"
        hot = out["temperature_bin"].isin(high_labels)
        radiation_high = out[radiation_bin_cols].isin(high_labels).any(axis=1)
        valid = matched & out[["temperature_bin", *radiation_bin_cols]].ne("missing").all(axis=1)
        out.loc[valid & hot & radiation_high, "combined_radiation_hot_regime"] = "radiation_hot"
        out.loc[valid & hot & ~radiation_high, "combined_radiation_hot_regime"] = "hot_not_highradiation"
        out.loc[valid & ~hot & radiation_high, "combined_radiation_hot_regime"] = "highradiation_not_hot"
        out.loc[valid & ~hot & ~radiation_high, "combined_radiation_hot_regime"] = "other"
        regime_cols.append("combined_radiation_hot_regime")
        notes.append("combined_radiation_hot_regime included from temperature and radiation quantile bins.")

    needed = ["temperature_bin", "humidity_bin", "wind_bin"]
    sw_col = "shortwave_bin" if "shortwave_bin" in out.columns else "shortwave_3h_mean_bin"
    if sw_col in out.columns and all(col in out.columns for col in needed):
        combined = (
            out["temperature_bin"].isin(high_labels)
            & out["humidity_bin"].isin(high_labels)
            & out["wind_bin"].eq("low")
            & out[sw_col].isin(high_labels)
        )
        obs_ge31 = as_bool(out["obs_ge31"])
        combined_count = int((matched & combined).sum())
        combined_obs = int((matched & combined & obs_ge31).sum())
        min_combined = int(config["analysis"].get("minimum_combined_regime_rows", 20))
        min_obs = int(config["analysis"].get("minimum_combined_regime_observed_ge31", 5))
        if combined_count >= min_combined and combined_obs >= min_obs:
            out["combined_hot_humid_lowwind_highsw_regime"] = "missing"
            valid = matched & out[["temperature_bin", "humidity_bin", "wind_bin", sw_col]].ne("missing").all(axis=1)
            out.loc[valid & combined, "combined_hot_humid_lowwind_highsw_regime"] = "hot_humid_lowwind_highsw"
            out.loc[valid & ~combined, "combined_hot_humid_lowwind_highsw_regime"] = "other"
            regime_cols.append("combined_hot_humid_lowwind_highsw_regime")
            notes.append(
                "combined_hot_humid_lowwind_highsw_regime included "
                f"with {combined_count} matched rows and {combined_obs} observed ge31 rows."
            )
        else:
            notes.append(
                "combined_hot_humid_lowwind_highsw_regime not included because it was not meaningful "
                f"under configured thresholds ({combined_count} rows, {combined_obs} observed ge31 rows)."
            )
    return out, regime_cols, notes


def summary_table(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Build residual and fixed ge31 summaries for grouping columns."""
    rows: list[dict[str, Any]] = []
    for keys, group in df.groupby(group_cols, dropna=False, observed=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        obs_ge31 = as_bool(group["obs_ge31"])
        pred_ge31 = as_bool(group["pred_ge31_fixed"])
        event_class = group["ge31_event_class"].astype(str)
        miss = event_class.eq("miss")
        hit = event_class.eq("hit")
        false_alarm = event_class.eq("false_alarm")
        row = {col: key for col, key in zip(group_cols, keys)}
        row.update(
            {
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
                "ge31_miss_rate_among_observed": miss.sum() / obs_ge31.sum() if obs_ge31.sum() else np.nan,
            }
        )
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(group_cols)


def residual_by_regime(df: pd.DataFrame, regime_cols: list[str]) -> pd.DataFrame:
    """Build a long residual summary for each weather-regime variable."""
    parts: list[pd.DataFrame] = []
    for col in regime_cols:
        tmp = df.assign(regime_variable=col, regime_bin=df[col].astype(str))
        parts.append(summary_table(tmp, ["model_name", "regime_variable", "regime_bin"]))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def miss_by_regime(df: pd.DataFrame, regime_cols: list[str]) -> pd.DataFrame:
    """Build fixed ge31 miss-concentration summaries for each regime."""
    parts: list[pd.DataFrame] = []
    totals = (
        df.groupby("model_name")["ge31_event_class"]
        .apply(lambda s: int(s.astype(str).eq("miss").sum()))
        .to_dict()
    )
    for col in regime_cols:
        summary = summary_table(
            df.assign(regime_variable=col, regime_bin=df[col].astype(str)),
            ["model_name", "regime_variable", "regime_bin"],
        )
        summary["share_of_model_ge31_misses"] = summary.apply(
            lambda row: row["n_ge31_miss"] / totals.get(row["model_name"], 0)
            if totals.get(row["model_name"], 0)
            else np.nan,
            axis=1,
        )
        parts.append(summary)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values(
        ["model_name", "share_of_model_ge31_misses", "n_ge31_miss"],
        ascending=[True, False, False],
    )


def decide_status(
    retention_rate: float,
    observed_ge31_coverage_rate: float,
    config: dict[str, Any],
) -> str:
    """Classify whether full-period decomposition is available."""
    pass_retention = float(config["analysis"].get("pass_retention_rate", 0.80))
    pass_event = float(config["analysis"].get("pass_event_coverage_rate", 0.80))
    partial_retention = float(config["analysis"].get("partial_retention_rate", 0.40))
    if retention_rate >= pass_retention and observed_ge31_coverage_rate >= pass_event:
        return "PASS_FULL_PERIOD"
    if retention_rate >= partial_retention:
        return "PARTIAL_DIAGNOSTIC"
    return "BLOCKED_FOR_FULL_PERIOD"


def classify_weather_regime(
    status: str,
    regime: pd.DataFrame,
    primary_model: str,
    config: dict[str, Any],
) -> tuple[str, str]:
    """Classify weather-regime interaction strength without upgrading claims."""
    if status == "BLOCKED_FOR_FULL_PERIOD":
        return "blocked", "Weather-regime decomposition is blocked because row retention is below the full-period threshold."
    sub = regime[regime["model_name"].eq(primary_model)].copy() if not regime.empty else pd.DataFrame()
    if sub.empty:
        return "blocked", "No matched weather-regime rows were available for the primary model."

    residual_ranges = sub.groupby("regime_variable")["mean_residual_c"].agg(lambda s: s.max() - s.min())
    miss_ranges = sub.groupby("regime_variable")["ge31_miss_rate_among_observed"].agg(lambda s: s.max() - s.min())
    top_residual = float(residual_ranges.max()) if not residual_ranges.empty else 0.0
    top_miss = float(miss_ranges.max()) if not miss_ranges.empty else 0.0
    residual_threshold = float(config["analysis"].get("supported_residual_range_c", 0.75))
    miss_threshold = float(config["analysis"].get("supported_miss_rate_range", 0.30))
    note = f"Largest primary-model residual-bin range is {top_residual:.2f} C; largest ge31 miss-rate range is {top_miss:.2f}."

    if status == "PASS_FULL_PERIOD" and (top_residual >= residual_threshold or top_miss >= miss_threshold):
        return "supported_full_period", note
    if status == "PARTIAL_DIAGNOSTIC" and (top_residual >= residual_threshold or top_miss >= miss_threshold):
        return "plausible_but_partial", note
    return "weak_or_unresolved", note


def next_action(status: str, classification: str) -> str:
    """Recommend the next A-L1H action without performing it."""
    if status != "PASS_FULL_PERIOD":
        return "secure canonical full-period hourly feature matrix before any separate formula audit, probability / threshold calibration review, high-tail regression review, or A-L2 work."
    if classification == "supported_full_period":
        return "close A-L1H.0c as full-period weather-regime residual diagnostic evidence; use it only to inform separately scoped formula-audit review, with probability calibration, high-tail regression, and A-L2 behind explicit review gates."
    return "close A-L1H.0c as diagnostic evidence; keep formula-audit review separate and keep probability calibration, high-tail regression, and A-L2 behind explicit review gates."


def markdown_cell(value: Any) -> str:
    """Format one Markdown table cell."""
    if pd.isna(value):
        return "NA"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value).replace("|", "\\|")


def table_md(df: pd.DataFrame, columns: list[str], limit: int = 12) -> str:
    """Render a compact Markdown table."""
    if df.empty:
        return "_No rows._"
    shown = df[columns].head(limit).copy()
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(markdown_cell(row[col]) for col in columns) + " |" for _, row in shown.iterrows()]
    return "\n".join([header, separator, *body])


def unique_observed_events(df: pd.DataFrame) -> int:
    """Count unique observed ge31 station/hour events across duplicated model rows."""
    obs = as_bool(df["obs_ge31"])
    return int(df.loc[obs, ["merge_station_id", "merge_time_sgt_hour"]].drop_duplicates().shape[0])


def build_result(
    config: dict[str, Any],
    selected: CandidateEvaluation | None,
    merged: pd.DataFrame,
    regime: pd.DataFrame,
    output_paths: list[Path],
    merge_keys: str,
) -> MergeResult:
    """Assemble the result dataclass from merged outputs."""
    primary_model = str(config["analysis"]["primary_model"])
    has_match = merged["has_weather_match"].astype(bool)
    obs = as_bool(merged["obs_ge31"])
    miss = merged["ge31_event_class"].astype(str).eq("miss")
    primary = merged["model_name"].astype(str).eq(primary_model)
    matched_rows = int(has_match.sum())
    total_rows = int(len(merged))
    total_obs = int(obs.sum())
    matched_obs = int((has_match & obs).sum())
    obs_coverage = matched_obs / total_obs if total_obs else 0.0
    status = decide_status(matched_rows / total_rows if total_rows else 0.0, obs_coverage, config)
    classification, note = classify_weather_regime(status, regime, primary_model, config)

    recovered = selected.recovered_weather_columns if selected is not None else []
    missing_weather = [col for col in config["schema"]["weather_columns"] if col not in recovered]
    return MergeResult(
        status=status,
        selected_weather_source=rel(selected.path) if selected is not None else None,
        selected_source_base=selected.source_base if selected is not None else "",
        selected_source_relative_path=selected.source_relative_path if selected is not None else "",
        merge_keys=merge_keys,
        total_residual_rows=total_rows,
        matched_rows=matched_rows,
        unmatched_rows=total_rows - matched_rows,
        retention_rate=matched_rows / total_rows if total_rows else 0.0,
        total_observed_ge31_rows=total_obs,
        matched_observed_ge31_rows=matched_obs,
        matched_observed_ge31_primary_rows=int((has_match & obs & primary).sum()),
        matched_unique_observed_ge31_events=unique_observed_events(merged.loc[has_match].copy()),
        total_unique_observed_ge31_events=unique_observed_events(merged.copy()),
        matched_ge31_miss_rows=int((has_match & miss).sum()),
        matched_ge31_miss_primary_rows=int((has_match & miss & primary).sum()),
        station_coverage_count=int(merged.loc[has_match, "station_id"].nunique()),
        total_stations=int(merged["station_id"].nunique()),
        recovered_weather_columns=recovered,
        missing_weather_columns=missing_weather,
        weather_regime_classification=classification,
        weather_regime_note=note,
        next_recommended_action=next_action(status, classification),
        output_paths=output_paths,
    )


def write_report(
    report_path: Path,
    config: dict[str, Any],
    result: MergeResult,
    inventory: pd.DataFrame,
    regime: pd.DataFrame,
    miss: pd.DataFrame,
    regime_notes: list[str],
) -> None:
    """Write the A-L1H.0c decision report."""
    primary_model = str(config["analysis"]["primary_model"])
    previous_rows = int(config["analysis"].get("previous_a_l1h_0b_matched_rows", 0))
    previous_rate = float(config["analysis"].get("previous_a_l1h_0b_retention_rate", 0.0))
    primary_regime = regime[regime["model_name"].eq(primary_model)].copy() if not regime.empty else pd.DataFrame()
    primary_miss = miss[miss["model_name"].eq(primary_model)].copy() if not miss.empty else pd.DataFrame()
    residual_top = primary_regime.sort_values("mean_residual_c", ascending=False).head(10)
    miss_top = primary_miss.sort_values(["share_of_model_ge31_misses", "n_ge31_miss"], ascending=False).head(10)
    inventory_table = inventory.sort_values(
        ["selected_for_merge", "evaluation_mode", "retention_rate"],
        ascending=[False, True, False],
    )
    missing = ", ".join(result.missing_weather_columns) if result.missing_weather_columns else "none"
    recovered = ", ".join(result.recovered_weather_columns) if result.recovered_weather_columns else "none"
    regime_note_text = "\n".join(f"- {note}" for note in regime_notes) if regime_notes else "- No combined-regime notes."

    lines = [
        "# System A A-L1H.0c Full-Period Weather-Regime Decision Report",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Status: {result.status}",
        f"Branch: {git_branch()}",
        "",
        "## 1. Sources Tried",
        "",
        table_md(
            inventory_table,
            [
                "inventory_role",
                "evaluation_mode",
                "path",
                "matched_residual_rows",
                "retention_rate",
                "recovered_weather_columns",
                "selected_for_merge",
                "reason",
            ],
            limit=16,
        ),
        "",
        "## 2. Source Selected",
        "",
        f"- Selected weather source: `{result.selected_weather_source or 'none'}`",
        f"- Selected source base: `{result.selected_source_base or 'unknown'}`",
        f"- Original provenance: `{result.selected_source_relative_path or 'unknown'}`",
        "- The original diagnostics input is not copied or required for this run; the compact recovered source is used for weather covariates.",
        "",
        "## 3. Improvement Over A-L1H.0b",
        "",
        f"- A-L1H.0b matched rows: {previous_rows} / {result.total_residual_rows} ({previous_rate:.1%})",
        f"- A-L1H.0c matched rows: {result.matched_rows} / {result.total_residual_rows} ({result.retention_rate:.1%})",
        f"- Improvement: {result.matched_rows - previous_rows} rows and {(result.retention_rate - previous_rate) * 100:.1f} percentage points.",
        "",
        "## 4. Merge Keys",
        "",
        f"- Merge keys: `{result.merge_keys}`",
        "- Matching uses exact `station_id` plus SGT hourly timestamp only.",
        "- Target WBGT values are not used as merge keys.",
        "- Unmatched residual rows remain in the merged output with `has_weather_match = False`.",
        "",
        "## 5. Row Retention And Station Coverage",
        "",
        f"- Total residual rows: {result.total_residual_rows}",
        f"- Matched rows: {result.matched_rows}",
        f"- Unmatched rows: {result.unmatched_rows}",
        f"- Retention rate: {result.retention_rate:.1%}",
        f"- Matched observed ge31 rows: {result.matched_observed_ge31_rows} / {result.total_observed_ge31_rows}",
        f"- Matched unique observed ge31 station-hour events: {result.matched_unique_observed_ge31_events} / {result.total_unique_observed_ge31_events}",
        f"- Matched ge31 miss rows: {result.matched_ge31_miss_rows}",
        f"- Matched observed ge31 rows for `{primary_model}`: {result.matched_observed_ge31_primary_rows}",
        f"- Matched ge31 miss rows for `{primary_model}`: {result.matched_ge31_miss_primary_rows}",
        f"- Station coverage: {result.station_coverage_count} / {result.total_stations}",
        "",
        "## 6. Weather Columns Recovered",
        "",
        f"- Recovered columns: {recovered}",
        f"- Missing configured columns: {missing}",
        "",
        "## 7. Residual / ge31 Miss By Weather Regime",
        "",
        "Residual by weather regime, primary model:",
        "",
        table_md(
            residual_top,
            [
                "regime_variable",
                "regime_bin",
                "n",
                "n_obs_ge31",
                "n_ge31_miss",
                "mean_residual_c",
                "p90_residual_c",
                "ge31_miss_rate_among_observed",
            ],
            limit=10,
        ),
        "",
        "ge31 miss concentration by weather regime, primary model:",
        "",
        table_md(
            miss_top,
            [
                "regime_variable",
                "regime_bin",
                "n_obs_ge31",
                "n_ge31_miss",
                "ge31_miss_rate_among_observed",
                "share_of_model_ge31_misses",
                "mean_residual_c",
            ],
            limit=10,
        ),
        "",
        "Combined-regime notes:",
        "",
        regime_note_text,
        "",
        "## 8. Weather-Regime Interaction Classification",
        "",
        f"- Classification: `{result.weather_regime_classification}`",
        f"- Evidence note: {result.weather_regime_note}",
        f"- Interpretation: {WEATHER_REGIME_DIAGNOSTIC_NOTE}",
        "- This is full-period retrospective System A WBGT_A residual diagnostic evidence only when status is `PASS_FULL_PERIOD`; it is not validated local WBGT prediction and not an operational warning probability.",
        "",
        "## 9. Recommended Next Action",
        "",
        f"- Recommended next action: {result.next_recommended_action}",
        "- Do not start A-L2 unless station bias remains after weather/regime control.",
        "- Do not implement formula-v2, probability calibration, or high-tail regression inside this merge task.",
        "",
        "## Claim Boundaries",
        "",
        "- Allowed: retrospective System A WBGT_A temporal severity diagnostics; full-period weather-regime residual diagnostics; evidence to inform later WBGT-gated radiative priority only after System B coupling.",
        "- Disallowed: validated local WBGT prediction, real-time heat risk forecast, standalone local hazard prioritisation from System A alone, official warning probability claims, SOLWEIG Tmrt equals WBGT, probability calibration, or high-tail regression claims.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(status_path: Path, config_path: Path, result: MergeResult) -> None:
    """Write the A-L1H.0c status file."""
    outputs = "\n".join(f"- `{rel(path)}`" for path in result.output_paths)
    lines = [
        "# A-L1H.0c Status",
        "",
        f"Status: {result.status}",
        f"Generated: {date.today().isoformat()}",
        f"Branch: {git_branch()}",
        "",
        "## Scope",
        "",
        "Full-period weather feature recovery / merge hardening for System A A-L1H residual diagnostics only. No model training, formula-v2, probability calibration, high-tail regression, A-L2, System B, SOLWEIG, rasters, or archive hot-path work.",
        "",
        "## Command",
        "",
        f"- `python scripts/v11_l1h_run_full_period_weather_merge.py --config {rel(config_path)}`",
        "",
        "## Outputs",
        "",
        outputs,
        "",
        "## Key Results",
        "",
        f"- Selected weather source: `{result.selected_weather_source or 'none'}`",
        f"- Original provenance: `{result.selected_source_base or 'unknown'}:{result.selected_source_relative_path or 'unknown'}`",
        f"- Retention: {result.matched_rows} / {result.total_residual_rows} ({result.retention_rate:.1%})",
        f"- Matched observed ge31 rows: {result.matched_observed_ge31_rows} / {result.total_observed_ge31_rows}",
        f"- Station coverage: {result.station_coverage_count} / {result.total_stations}",
        f"- Weather columns recovered: {', '.join(result.recovered_weather_columns) if result.recovered_weather_columns else 'none'}",
        f"- Weather-regime classification: {result.weather_regime_classification}",
        f"- Weather-regime interpretation: {WEATHER_REGIME_DIAGNOSTIC_NOTE}",
        f"- Next recommended action: {result.next_recommended_action}",
        "",
        "## Safe To Commit",
        "",
        "- Config, scripts, docs, and compact Markdown/CSV diagnostic outputs from this task.",
        "",
        "## Not Safe To Commit",
        "",
        "- Raw archives, rasters, SOLWEIG outputs, tif/tiff files, svfs.zip, patch zip packages, or large hourly forecast CSVs.",
    ]
    status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_merge(config_path: Path) -> MergeResult:
    """Run the full-period weather merge and write configured outputs."""
    config = load_config(config_path)
    output_dir = resolve_path(str(config["outputs"]["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    residual_path = resolve_path(str(config["inputs"]["residual_input"]))
    residual_raw = pd.read_csv(residual_path)
    residual, residual_station_col, residual_time_col = normalize_residual_keys(residual_raw, config)
    best_source_note = read_best_source_note(resolve_path(str(config["inputs"]["best_source_note"])))
    preflight = read_preflight(config)

    evaluations: list[CandidateEvaluation] = []
    normalized_by_path: dict[str, pd.DataFrame] = {}
    for role, path in candidate_paths(config, preflight):
        evaluation, normalized = evaluate_candidate(role, path, residual, config, best_source_note)
        evaluations.append(evaluation)
        if normalized is not None:
            normalized_by_path[rel(path)] = normalized

    selected = choose_candidate(evaluations, config)
    selected_rel = rel(selected.path) if selected is not None else ""
    inventory_rows = [candidate_to_row(item, rel(item.path) == selected_rel) for item in evaluations]
    inventory_rows.extend(preflight_reference_rows(preflight, selected.source_relative_path if selected is not None else ""))
    inventory = pd.DataFrame(inventory_rows)
    inventory_path = output_dir / "full_period_weather_source_inventory.csv"
    inventory.to_csv(inventory_path, index=False)

    merge_keys = f"{residual_station_col}+{residual_time_col}->SGT_hour; weather=unavailable"
    regime_notes: list[str] = []
    if selected is not None:
        weather = normalized_by_path[selected_rel]
        merge_keys = f"{residual_station_col}+{residual_time_col}->SGT_hour; weather={selected.station_column}+{selected.time_column}->SGT_hour"
        merged = residual.merge(weather, on=["merge_station_id", "merge_time_sgt_hour"], how="left")
        merged["has_weather_match"] = merged[selected.recovered_weather_columns].notna().any(axis=1)
        if "source_base" in merged.columns:
            merged = merged.rename(columns={"source_base": "weather_source_base"})
        if "source_relative_path" in merged.columns:
            merged = merged.rename(columns={"source_relative_path": "weather_source_relative_path"})
        merged, regime_cols, regime_notes = add_regimes(merged, selected.recovered_weather_columns, config)
        matched = merged[merged["has_weather_match"]].copy()
        regime = residual_by_regime(matched, regime_cols)
        miss = miss_by_regime(matched, regime_cols)
    else:
        merged = residual.copy()
        merged["has_weather_match"] = False
        regime = pd.DataFrame()
        miss = pd.DataFrame()

    merged_path = output_dir / "residual_weather_merge_full_period.csv"
    regime_path = output_dir / "residual_by_weather_regime_full_period.csv"
    miss_path = output_dir / "ge31_miss_by_weather_regime_full_period.csv"
    report_path = output_dir / "weather_regime_full_period_decision_report.md"
    status_path = output_dir / "A_L1H_0C_STATUS.md"

    merged.to_csv(merged_path, index=False)
    regime.to_csv(regime_path, index=False)
    miss.to_csv(miss_path, index=False)

    output_paths = [inventory_path, merged_path, regime_path, miss_path, report_path, status_path]
    result = build_result(config, selected, merged, regime, output_paths, merge_keys)
    write_report(report_path, config, result, inventory, regime, miss, regime_notes)
    write_status(status_path, config_path, result)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Run A-L1H.0c full-period weather feature recovery / merge hardening "
            "for residual weather-regime diagnostics."
        )
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h_full_period_weather_merge.yaml")
    args = parser.parse_args()

    result = run_merge(resolve_path(args.config))
    print(f"[status] {result.status}")
    print(f"[selected_weather_source] {result.selected_weather_source}")
    print(f"[selected_source_provenance] {result.selected_source_base}:{result.selected_source_relative_path}")
    print(f"[retention_rate] {result.retention_rate:.6f}")
    print(f"[matched_rows] {result.matched_rows}/{result.total_residual_rows}")
    print(f"[matched_observed_ge31_rows] {result.matched_observed_ge31_rows}/{result.total_observed_ge31_rows}")
    print(f"[matched_ge31_miss_rows] {result.matched_ge31_miss_rows}")
    print(f"[weather_columns_recovered] {', '.join(result.recovered_weather_columns) if result.recovered_weather_columns else 'none'}")
    print(f"[weather_regime_classification] {result.weather_regime_classification}")
    print(f"[next_recommended_action] {result.next_recommended_action}")
    return 0 if result.status in {"PASS_FULL_PERIOD", "PARTIAL_DIAGNOSTIC", "BLOCKED_FOR_FULL_PERIOD"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
