#!/usr/bin/env python
"""System A A-L1H.0b weather-regime residual merge.

Inputs:
    - configs/v11/systema_l1h_weather_regime_merge.yaml
    - outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv
    - Existing weather/feature CSV or CSV.GZ tables declared in the config.

Outputs:
    - weather_source_inventory.csv
    - residual_weather_merge_input.csv
    - residual_by_weather_regime.csv
    - ge31_miss_by_weather_regime.csv
    - weather_regime_bias_report.md
    - A_L1H_0B_STATUS.md

Saved metrics:
    - Candidate weather-source inventory with detected keys/columns and overlap.
    - Row retention after station_id + SGT hourly timestamp merge.
    - Residual and fixed ge31 miss concentration summaries by weather-regime bins.

This script consumes existing residual diagnostics and weather tables only. It
does not train models, implement formula-v2, calibrate probabilities, run
high-tail regression, touch System B, or touch SOLWEIG/raster/archive hot paths.
"""
from __future__ import annotations

import argparse
import gzip
import math
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


@dataclass(frozen=True)
class WeatherCandidate:
    """Detected metadata and merge fitness for one weather candidate."""

    path: Path
    exists: bool
    size_bytes: int
    readable: bool
    row_count: int
    station_column: str | None
    time_column: str | None
    weather_columns: list[str]
    recovered_columns: list[str]
    unique_weather_keys: int
    matched_residual_rows: int
    retention_rate: float
    score: float
    reason: str


@dataclass(frozen=True)
class MergeResult:
    """Headline status and output paths from the A-L1H.0b merge."""

    status: str
    selected_weather_source: str | None
    merge_keys: str
    residual_rows: int
    matched_rows: int
    retention_rate: float
    recovered_weather_columns: list[str]
    missing_weather_columns: list[str]
    plausible_interaction: str
    next_action: str
    output_paths: list[Path]


def rel(path: Path) -> str:
    """Return a repo-relative POSIX path when possible."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_config(path: Path) -> dict[str, Any]:
    """Read the YAML config for this lane."""
    return parse_simple_yaml(path.read_text(encoding="utf-8"))


def parse_scalar(value: str) -> Any:
    """Parse the scalar subset used by this lane config."""
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
    """Parse the small YAML subset used by this explicit config file."""
    raw_lines = []
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

        next_container: dict[str, Any] | list[Any]
        next_line = raw_lines[index + 1][1] if index + 1 < len(raw_lines) else ""
        next_container = [] if next_line.startswith("- ") else {}
        if not isinstance(parent, dict):
            raise ValueError(f"Unexpected YAML nested mapping under list: {stripped}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def git_branch() -> str:
    """Return the current git branch if available."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def existing_candidate_paths(config: dict[str, Any]) -> list[Path]:
    """Build the ordered weather-candidate list from explicit paths and globs."""
    seen: set[Path] = set()
    paths: list[Path] = []
    for raw_path in config["inputs"].get("candidate_weather_paths", []):
        path = ROOT / raw_path
        if path not in seen:
            paths.append(path)
            seen.add(path)
    for pattern in config["inputs"].get("candidate_weather_globs", []):
        for path in sorted(ROOT.glob(pattern)):
            if path not in seen:
                paths.append(path)
                seen.add(path)
    return paths


def read_header(path: Path) -> list[str]:
    """Read CSV header columns without loading all rows."""
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8", errors="replace", newline="") as f:
            return pd.read_csv(f, nrows=0).columns.tolist()
    except Exception:
        return []


def count_rows(path: Path) -> int:
    """Count data rows in a CSV or CSV.GZ candidate."""
    if not path.exists():
        return 0
    opener = gzip.open if path.suffix == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8", errors="replace") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except Exception:
        return 0


def first_present(columns: list[str], aliases: list[str]) -> str | None:
    """Return the first alias present in the column list."""
    col_set = set(columns)
    for col in aliases:
        if col in col_set:
            return col
    return None


def parse_sgt_hour(series: pd.Series, column_name: str) -> pd.Series:
    """Parse a timestamp column into an SGT hourly key string."""
    parsed = pd.to_datetime(series, errors="coerce")
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        sgt = parsed.dt.tz_convert(SGT_TZ)
    elif "utc" in column_name.lower():
        sgt = pd.to_datetime(series, errors="coerce", utc=True).dt.tz_convert(SGT_TZ)
    else:
        sgt = parsed.dt.tz_localize(SGT_TZ, nonexistent="NaT", ambiguous="NaT")
    return sgt.dt.floor("h").dt.strftime("%Y-%m-%d %H:%M:%S%z")


def normalize_residual_keys(residual: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    """Add station/time merge keys to the residual input."""
    out = residual.copy()
    station_col = first_present(out.columns.tolist(), config["schema"]["station_columns"])
    time_col = first_present(out.columns.tolist(), config["schema"]["residual_time_columns"])
    if station_col is None or time_col is None:
        raise ValueError("Residual input lacks station_id or parseable timestamp columns.")
    out["merge_station_id"] = out[station_col].astype(str)
    out["merge_time_sgt_hour"] = parse_sgt_hour(out[time_col], time_col)
    out["merge_key_available"] = out["merge_station_id"].ne("") & out["merge_time_sgt_hour"].notna()
    return out, f"{station_col}+{time_col}->SGT_hour"


def load_weather(path: Path) -> pd.DataFrame:
    """Load a weather candidate from CSV or CSV.GZ."""
    if path.suffix == ".gz":
        return pd.read_csv(path, compression="gzip")
    return pd.read_csv(path)


def recover_shortwave_3h_mean(weather: pd.DataFrame) -> pd.DataFrame:
    """Derive a per-station 3-hour shortwave mean when source radiation exists."""
    out = weather.copy()
    if "shortwave_3h_mean" in out.columns or "shortwave_radiation" not in out.columns:
        return out
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
    columns: list[str],
    config: dict[str, Any],
) -> tuple[pd.DataFrame | None, str | None, str | None, list[str], list[str], str]:
    """Normalize a weather source to one row per station/hour merge key."""
    station_col = first_present(columns, config["schema"]["station_columns"])
    time_col = first_present(columns, config["schema"]["weather_time_columns"])
    configured_weather = config["schema"]["weather_columns"]
    available_weather = [col for col in configured_weather if col in columns]
    if station_col is None or time_col is None or len(available_weather) < 1:
        return None, station_col, time_col, available_weather, [], "missing_station_time_or_weather_columns"

    raw = load_weather(path)
    raw = raw[[station_col, time_col, *available_weather]].copy()
    raw["merge_station_id"] = raw[station_col].astype(str)
    raw["merge_time_sgt_hour"] = parse_sgt_hour(raw[time_col], time_col)
    for col in available_weather:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    raw = recover_shortwave_3h_mean(raw)
    recovered = [col for col in configured_weather if col in raw.columns]
    value_cols = [col for col in recovered if pd.to_numeric(raw[col], errors="coerce").notna().any()]
    if not value_cols:
        return None, station_col, time_col, available_weather, recovered, "weather_columns_all_empty"

    keep = ["merge_station_id", "merge_time_sgt_hour", *value_cols]
    normalized = (
        raw[keep]
        .dropna(subset=["merge_station_id", "merge_time_sgt_hour"])
        .groupby(["merge_station_id", "merge_time_sgt_hour"], as_index=False)[value_cols]
        .mean(numeric_only=True)
    )
    return normalized, station_col, time_col, available_weather, value_cols, "usable"


def inventory_candidates(
    residual: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, WeatherCandidate | None, dict[str, pd.DataFrame]]:
    """Inspect weather sources and select the highest-retention usable candidate."""
    max_size = int(float(config["inputs"].get("max_candidate_size_mb", 25)) * 1024 * 1024)
    normalized_by_path: dict[str, pd.DataFrame] = {}
    candidates: list[WeatherCandidate] = []
    residual_keys = residual[["merge_station_id", "merge_time_sgt_hour"]].copy()
    residual_keys["residual_key_row"] = np.arange(len(residual_keys))

    for path in existing_candidate_paths(config):
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        readable = bool(exists and size <= max_size)
        columns = read_header(path) if readable else []
        row_count = count_rows(path) if readable else 0
        weather: pd.DataFrame | None = None
        station_col: str | None = None
        time_col: str | None = None
        available_weather: list[str] = []
        recovered_weather: list[str] = []
        unique_keys = 0
        matched_rows = 0
        retention = 0.0
        reason = "missing" if not exists else "over_size_limit" if not readable else "inspected"

        if readable:
            try:
                weather, station_col, time_col, available_weather, recovered_weather, reason = normalize_weather(path, columns, config)
            except Exception as exc:
                reason = f"read_or_normalize_failed: {exc}"
                weather = None
            if weather is not None:
                unique_keys = len(weather)
                merged = residual_keys.merge(
                    weather[["merge_station_id", "merge_time_sgt_hour"]].drop_duplicates(),
                    on=["merge_station_id", "merge_time_sgt_hour"],
                    how="inner",
                )
                matched_rows = int(len(merged))
                retention = matched_rows / len(residual) if len(residual) else 0.0
                normalized_by_path[rel(path)] = weather

        minimum_cols = config["schema"]["minimum_regime_columns"]
        minimum_recovered = [col for col in recovered_weather if col in minimum_cols]
        score = retention * 1000 + len(minimum_recovered) * 20 + len(recovered_weather)
        if len(minimum_recovered) < int(config["analysis"].get("minimum_regime_column_count", 3)):
            score -= 100
        candidates.append(WeatherCandidate(
            path=path,
            exists=exists,
            size_bytes=size,
            readable=readable,
            row_count=row_count,
            station_column=station_col,
            time_column=time_col,
            weather_columns=available_weather,
            recovered_columns=recovered_weather,
            unique_weather_keys=unique_keys,
            matched_residual_rows=matched_rows,
            retention_rate=retention,
            score=score,
            reason=reason,
        ))

    rows = [
        {
            "path": rel(item.path),
            "exists": "yes" if item.exists else "no",
            "size_bytes": item.size_bytes,
            "readable": "yes" if item.readable else "no",
            "row_count": item.row_count,
            "station_column": item.station_column or "",
            "time_column": item.time_column or "",
            "detected_weather_columns": "|".join(item.weather_columns),
            "recovered_weather_columns": "|".join(item.recovered_columns),
            "unique_weather_keys": item.unique_weather_keys,
            "matched_residual_rows": item.matched_residual_rows,
            "retention_rate": item.retention_rate,
            "candidate_score": item.score,
            "selected_for_merge": "no",
            "reason": item.reason,
        }
        for item in candidates
    ]
    inventory = pd.DataFrame(rows).sort_values(["candidate_score", "path"], ascending=[False, True])

    selected: WeatherCandidate | None = None
    min_cols = int(config["analysis"].get("minimum_regime_column_count", 3))
    min_retention = float(config["analysis"].get("minimum_row_retention_rate", 0.30))
    for item in sorted(candidates, key=lambda c: c.score, reverse=True):
        recovered_minimum = [col for col in item.recovered_columns if col in config["schema"]["minimum_regime_columns"]]
        if item.retention_rate >= min_retention and len(recovered_minimum) >= min_cols:
            selected = item
            break
    if selected is not None and not inventory.empty:
        selected_path = rel(selected.path)
        inventory.loc[inventory["path"].eq(selected_path), "selected_for_merge"] = "yes"
        inventory.loc[inventory["path"].eq(selected_path), "reason"] = (
            inventory.loc[inventory["path"].eq(selected_path), "reason"].astype(str)
            + "; selected_highest_retention_usable_source"
        )
    return inventory, selected, normalized_by_path


def quantile_bin(series: pd.Series, min_rows_4_bins: int) -> pd.Series:
    """Create low/mid/high or four-bin quantile labels for a numeric series."""
    numeric = pd.to_numeric(series, errors="coerce")
    valid_count = int(numeric.notna().sum())
    if valid_count < 6 or numeric.nunique(dropna=True) < 3:
        return pd.Series("missing", index=series.index, dtype="object")
    n_bins = 4 if valid_count >= min_rows_4_bins and numeric.nunique(dropna=True) >= 4 else 3
    labels = FOUR_BIN_LABELS if n_bins == 4 else LOW_MID_HIGH
    ranked = numeric.rank(method="first")
    binned = pd.qcut(ranked, q=n_bins, labels=labels, duplicates="drop")
    return binned.astype("object").where(binned.notna(), "missing")


def add_regimes(df: pd.DataFrame, weather_columns: list[str], min_rows_4_bins: int) -> tuple[pd.DataFrame, list[str]]:
    """Add weather-regime bins to the merged residual table."""
    out = df.copy()
    bin_specs = {
        "shortwave_radiation": "shortwave_bin",
        "shortwave_3h_mean": "shortwave_3h_mean_bin",
        "relative_humidity_2m": "humidity_bin",
        "wind_speed_10m": "wind_bin",
        "temperature_2m": "temperature_bin",
        "cloud_cover": "cloud_cover_bin",
        "precipitation": "precipitation_bin",
        "direct_radiation": "direct_radiation_bin",
        "diffuse_radiation": "diffuse_radiation_bin",
    }
    regime_cols: list[str] = []
    for weather_col, bin_col in bin_specs.items():
        if weather_col in weather_columns and weather_col in out.columns:
            out[bin_col] = quantile_bin(out[weather_col], min_rows_4_bins)
            if not out[bin_col].eq("missing").all():
                regime_cols.append(bin_col)

    hot_col = "temperature_bin"
    humid_col = "humidity_bin"
    wind_col = "wind_bin"
    sw_col = "shortwave_bin" if "shortwave_bin" in out.columns else "shortwave_3h_mean_bin"
    if all(col in out.columns for col in [hot_col, humid_col, wind_col, sw_col]):
        high_labels = {"high", "very_high"}
        enough_data = ~out[[hot_col, humid_col, wind_col, sw_col]].eq("missing").any(axis=1)
        combined = (
            out[hot_col].isin(high_labels)
            & out[humid_col].isin(high_labels)
            & out[wind_col].eq("low")
            & out[sw_col].isin(high_labels)
        )
        out["combined_hot_humid_lowwind_highsw"] = np.select(
            [~enough_data, combined],
            ["missing", "hot_humid_lowwind_highsw"],
            default="other",
        )
        regime_cols.append("combined_hot_humid_lowwind_highsw")
    return out, regime_cols


def summary_table(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Build residual and fixed ge31 summaries for grouping columns."""
    rows: list[dict[str, Any]] = []
    for keys, group in df.groupby(group_cols, dropna=False, observed=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: key for col, key in zip(group_cols, keys)}
        obs_ge31 = group["obs_ge31"].astype(bool)
        miss = group["ge31_event_class"].astype(str).eq("miss")
        hit = group["ge31_event_class"].astype(str).eq("hit")
        false_alarm = group["ge31_event_class"].astype(str).eq("false_alarm")
        row.update({
            "n": int(len(group)),
            "n_obs_ge31": int(obs_ge31.sum()),
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
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols)


def residual_by_regime(df: pd.DataFrame, regime_cols: list[str]) -> pd.DataFrame:
    """Build a long residual summary for each weather-regime variable."""
    parts: list[pd.DataFrame] = []
    for col in regime_cols:
        tmp = df.copy()
        tmp["regime_variable"] = col
        tmp["regime_bin"] = tmp[col].astype(str)
        parts.append(summary_table(tmp, ["model_name", "regime_variable", "regime_bin"]))
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def miss_by_regime(df: pd.DataFrame, regime_cols: list[str]) -> pd.DataFrame:
    """Build fixed ge31 miss-concentration summaries for each regime."""
    parts: list[pd.DataFrame] = []
    total_misses = (
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
            lambda row: row["n_ge31_miss"] / total_misses.get(row["model_name"], 0)
            if total_misses.get(row["model_name"], 0) else np.nan,
            axis=1,
        )
        parts.append(summary)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values(
        ["model_name", "share_of_model_ge31_misses", "n_ge31_miss"],
        ascending=[True, False, False],
    )


def format_float(value: Any, digits: int = 3) -> str:
    """Format a numeric value for Markdown."""
    if pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def table_md(df: pd.DataFrame, columns: list[str], limit: int = 10) -> str:
    """Return a compact Markdown table."""
    if df.empty:
        return "_No rows._"
    shown = df[columns].head(limit).copy()
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body: list[str] = []
    for _, row in shown.iterrows():
        values = [markdown_cell(row[col]) for col in columns]
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *body])


def markdown_cell(value: Any) -> str:
    """Format one Markdown table cell without optional dependencies."""
    if pd.isna(value):
        return "NA"
    if isinstance(value, float):
        return f"{value:.3f}"
    text = str(value)
    return text.replace("|", "\\|")


def classify_interaction(regime: pd.DataFrame, primary_model: str) -> tuple[str, str]:
    """Classify whether weather-regime residual interaction looks plausible."""
    sub = regime[regime["model_name"].eq(primary_model)].copy()
    if sub.empty:
        return "not_interpretable", "No regime rows were available for the primary model."
    ranges = sub.groupby("regime_variable")["mean_residual_c"].agg(lambda s: s.max() - s.min()).sort_values(ascending=False)
    miss_ranges = sub.groupby("regime_variable")["ge31_miss_rate_among_observed"].agg(lambda s: s.max() - s.min()).sort_values(ascending=False)
    top_residual = float(ranges.iloc[0]) if not ranges.empty else 0.0
    top_miss = float(miss_ranges.iloc[0]) if not miss_ranges.empty else 0.0
    if top_residual >= 0.75 or top_miss >= 0.30:
        return (
            "plausible_but_partial",
            f"Largest residual-bin range is {top_residual:.2f} C and largest ge31 miss-rate range is {top_miss:.2f}; interpret as partial-period diagnostic evidence only.",
        )
    return (
        "weak_or_mixed",
        f"Largest residual-bin range is {top_residual:.2f} C and largest ge31 miss-rate range is {top_miss:.2f}; weather interaction is not cleanly separated.",
    )


def recommend_next(plausible_interaction: str, retention_rate: float) -> str:
    """Recommend the next A-L1H action without implementing it."""
    if retention_rate < 0.50:
        return "mixed staged follow-up: first secure a full-period weather feature table, then revisit formula-v2 / physical proxy and threshold-calibration gates."
    if plausible_interaction == "plausible_but_partial":
        return "mixed staged follow-up: prioritize formula-v2 / physical proxy review before probability threshold calibration; keep high-tail regression behind a review gate."
    return "mixed staged follow-up: compare formula-v2 / physical proxy and probability threshold calibration only after confirming weather-source coverage."


def write_report(
    result: MergeResult,
    inventory: pd.DataFrame,
    merged: pd.DataFrame,
    regime: pd.DataFrame,
    miss: pd.DataFrame,
    report_path: Path,
    selected: WeatherCandidate | None,
    interaction_note: str,
) -> None:
    """Write the Markdown weather-regime bias report."""
    primary_model = "M4_inertia_ridge"
    if selected is not None:
        selected_inventory = inventory[inventory["path"].eq(rel(selected.path))]
        selected_reason = selected_inventory["reason"].iloc[0] if not selected_inventory.empty else selected.reason
    else:
        selected_reason = "No usable weather source selected."

    primary_regime = regime[regime["model_name"].eq(primary_model)].copy() if not regime.empty else pd.DataFrame()
    primary_miss = miss[miss["model_name"].eq(primary_model)].copy() if not miss.empty else pd.DataFrame()
    top_miss = primary_miss.sort_values(["share_of_model_ge31_misses", "n_ge31_miss"], ascending=False).head(8)
    top_residual = primary_regime.sort_values("mean_residual_c", ascending=False).head(8)
    missing_cols = ", ".join(result.missing_weather_columns) if result.missing_weather_columns else "none"
    recovered_cols = ", ".join(result.recovered_weather_columns) if result.recovered_weather_columns else "none"

    lines = [
        "# System A A-L1H.0b Weather-Regime Residual Merge",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Status: {result.status}",
        f"Branch: {git_branch()}",
        "",
        "## 1. Weather Source Selected",
        "",
        f"- Selected source: `{result.selected_weather_source or 'none'}`",
        f"- Selection note: {selected_reason}",
        "- This source is used only for station/hour weather covariates; target values in weather-pair files are not used for matching.",
        "",
        "## 2. Merge Keys Used",
        "",
        f"- Merge keys: `{result.merge_keys}`",
        "- Preferred logic: exact `station_id` plus SGT hourly timestamp. Timestamps are normalized to SGT hour buckets before merging.",
        "- Target WBGT values are not part of the merge key.",
        "",
        "## 3. Row Retention",
        "",
        f"- Residual rows: {result.residual_rows}",
        f"- Rows with matched weather: {result.matched_rows}",
        f"- Retention rate: {result.retention_rate:.1%}",
        "- Unmatched residual rows are retained in `residual_weather_merge_input.csv` with `has_weather_match = False`, but regime summaries use matched rows only.",
        "",
        "## 4. Missing Weather Columns",
        "",
        f"- Recovered columns: {recovered_cols}",
        f"- Missing configured columns: {missing_cols}",
        "",
        "## 5. Residual by Weather Regime",
        "",
        table_md(
            top_residual,
            [
                "regime_variable",
                "regime_bin",
                "n",
                "n_obs_ge31",
                "mean_residual_c",
                "p90_residual_c",
                "ge31_miss_rate_among_observed",
            ],
        ),
        "",
        "## 6. ge31 Miss Concentration by Regime",
        "",
        table_md(
            top_miss,
            [
                "regime_variable",
                "regime_bin",
                "n_obs_ge31",
                "n_ge31_miss",
                "ge31_miss_rate_among_observed",
                "share_of_model_ge31_misses",
                "mean_residual_c",
            ],
        ),
        "",
        "## 7. Plausibility Interpretation",
        "",
        f"- Weather-regime interaction classification: `{result.plausible_interaction}`",
        f"- Interpretation: {interaction_note}",
        "- This is a retrospective OOF diagnostic on matched rows only. It supports prioritisation, not a validated local WBGT prediction or operational warning claim.",
        "",
        "## 8. Next Recommended Action",
        "",
        result.next_action,
        "",
        "## Candidate Inventory",
        "",
        table_md(
            inventory,
            [
                "path",
                "exists",
                "readable",
                "recovered_weather_columns",
                "matched_residual_rows",
                "retention_rate",
                "selected_for_merge",
                "reason",
            ],
            limit=12,
        ),
        "",
        "## Claim Boundaries",
        "",
        "- This remains a WBGT-gated, SOLWEIG-informed, surrogate-assisted local heat hazard ranking diagnostic lane.",
        "- Do not describe this as validated local WBGT prediction, real-time heat risk forecasting, probability calibration, or high-tail regression.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(config_path: Path, result: MergeResult, status_path: Path) -> None:
    """Write the A-L1H.0b lane status file."""
    output_lines = "\n".join(f"- `{rel(path)}`" for path in result.output_paths)
    lines = [
        "# A-L1H.0b Status",
        "",
        f"Status: {result.status}",
        f"Generated: {date.today().isoformat()}",
        f"Branch: {git_branch()}",
        "",
        "## Scope",
        "",
        "Weather-regime residual merge only, using existing residual diagnostics and existing weather/feature tables. No training, formula-v2 implementation, probability calibration, high-tail regression, A-L2 work, System B outputs, SOLWEIG, rasters, or archive hot-path changes.",
        "",
        "## Command",
        "",
        f"- `python scripts/v11_l1h_run_weather_regime_merge.py --config {rel(config_path)}`",
        "",
        "## Outputs",
        "",
        output_lines,
        "",
        "## Headline",
        "",
        f"- Selected weather source: `{result.selected_weather_source or 'none'}`",
        f"- Merge row retention: {result.matched_rows} / {result.residual_rows} ({result.retention_rate:.1%})",
        f"- Recovered weather columns: {', '.join(result.recovered_weather_columns) if result.recovered_weather_columns else 'none'}",
        f"- Weather-regime interaction: {result.plausible_interaction}",
        f"- Next recommended action: {result.next_action}",
    ]
    status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_merge(config_path: Path) -> MergeResult:
    """Run the weather-regime residual merge and write all configured outputs."""
    config = load_config(config_path)
    output_dir = ROOT / config["analysis"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    residual_path = ROOT / config["inputs"]["residual_input"]
    residual_raw = pd.read_csv(residual_path)
    residual, residual_key_note = normalize_residual_keys(residual_raw, config)
    inventory, selected, normalized_by_path = inventory_candidates(residual, config)
    inventory_path = output_dir / "weather_source_inventory.csv"
    inventory.to_csv(inventory_path, index=False)

    output_paths = [inventory_path]
    configured_weather = config["schema"]["weather_columns"]
    missing_weather = configured_weather.copy()
    recovered_weather: list[str] = []
    matched_rows = 0
    retention = 0.0
    status = "BLOCKED"
    merge_keys = f"{residual_key_note}; weather_key=unavailable"
    selected_source: str | None = None
    regime = pd.DataFrame()
    miss = pd.DataFrame()
    interaction = "not_interpretable"
    interaction_note = "No usable weather source was available."

    if selected is not None:
        selected_source = rel(selected.path)
        weather = normalized_by_path[selected_source]
        recovered_weather = selected.recovered_columns
        missing_weather = [col for col in configured_weather if col not in recovered_weather]
        merge_keys = f"{residual_key_note}; weather={selected.station_column}+{selected.time_column}->SGT_hour"
        merged = residual.merge(weather, on=["merge_station_id", "merge_time_sgt_hour"], how="left")
        merged["has_weather_match"] = merged[recovered_weather].notna().any(axis=1)
        matched_rows = int(merged["has_weather_match"].sum())
        retention = matched_rows / len(merged) if len(merged) else 0.0
        min_cols = int(config["analysis"].get("minimum_regime_column_count", 3))
        min_retention = float(config["analysis"].get("minimum_row_retention_rate", 0.30))
        minimum_recovered = [col for col in recovered_weather if col in config["schema"]["minimum_regime_columns"]]
        matched = merged[merged["has_weather_match"]].copy()
        if retention >= min_retention and len(minimum_recovered) >= min_cols and not matched.empty:
            merged, regime_cols = add_regimes(
                merged,
                recovered_weather,
                int(config["analysis"].get("quantile_regime_min_rows_4_bins", 120)),
            )
            matched = merged[merged["has_weather_match"]].copy()
            regime = residual_by_regime(matched, regime_cols)
            miss = miss_by_regime(matched, regime_cols)
            interaction, interaction_note = classify_interaction(regime, str(config["analysis"]["primary_model"]))
            status = "PASS"
        else:
            interaction_note = (
                f"Matched retention {retention:.1%} or minimum recovered regime columns "
                f"({len(minimum_recovered)}) did not meet configured interpretability thresholds."
            )
    else:
        merged = residual.copy()
        merged["has_weather_match"] = False

    merged_path = output_dir / "residual_weather_merge_input.csv"
    regime_path = output_dir / "residual_by_weather_regime.csv"
    miss_path = output_dir / "ge31_miss_by_weather_regime.csv"
    report_path = output_dir / "weather_regime_bias_report.md"
    status_path = output_dir / "A_L1H_0B_STATUS.md"

    merged.to_csv(merged_path, index=False)
    regime.to_csv(regime_path, index=False)
    miss.to_csv(miss_path, index=False)
    output_paths.extend([merged_path, regime_path, miss_path, report_path, status_path])

    next_action = recommend_next(interaction, retention)
    result = MergeResult(
        status=status,
        selected_weather_source=selected_source,
        merge_keys=merge_keys,
        residual_rows=len(residual),
        matched_rows=matched_rows,
        retention_rate=retention,
        recovered_weather_columns=recovered_weather,
        missing_weather_columns=missing_weather,
        plausible_interaction=interaction,
        next_action=next_action,
        output_paths=output_paths,
    )
    write_report(result, inventory, merged, regime, miss, report_path, selected, interaction_note)
    write_status(config_path, result, status_path)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Merge A-L1H residual diagnostics with existing station/hour weather "
            "features and summarize weather-regime residual concentration."
        )
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h_weather_regime_merge.yaml")
    args = parser.parse_args()

    result = run_merge(ROOT / args.config)
    print(f"[status] {result.status}")
    print(f"[selected_weather_source] {result.selected_weather_source}")
    print(f"[retention] {result.matched_rows}/{result.residual_rows} ({result.retention_rate:.1%})")
    print(f"[recovered_weather_columns] {', '.join(result.recovered_weather_columns) if result.recovered_weather_columns else 'none'}")
    print(f"[plausible_interaction] {result.plausible_interaction}")
    print(f"[next_action] {result.next_action}")
    return 0 if result.status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
