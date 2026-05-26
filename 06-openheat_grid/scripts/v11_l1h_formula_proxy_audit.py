#!/usr/bin/env python
"""System A A-L1H.1 formula-v2 / physical proxy diagnostic audit.

Inputs:
    - configs/v11/systema_l1h_formula_proxy_audit.yaml
    - outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv
    - outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv
    - outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv
    - Optional prior formula-audit artifacts declared in the config.

Outputs:
    - formula_input_inventory.csv
    - formula_candidate_registry.csv
    - formula_candidate_predictions.csv.gz
    - formula_component_diagnostics.csv
    - formula_overall_metrics.csv
    - formula_threshold_metrics_31_33.csv
    - formula_residual_by_observed_bin.csv
    - formula_residual_by_radiation_regime.csv
    - formula_ge31_miss_by_regime.csv
    - formula_physics_audit_report.md
    - A_L1H_1_STATUS.md

Saved metrics:
    - Input availability and candidate registry.
    - Overall error, high-tail compression, station residual range, and
      prediction distribution metrics.
    - Fixed_31 / fixed_33 threshold metrics plus ge31 best-F1 threshold scans.
    - Residual and ge31 miss diagnostics by observed WBGT bin and radiation
      regime, including radiation-hot and very-high shortwave regimes.
    - Stull wet-bulb, simplified globe, formula dynamic range, compression, and
      radiation-sensitivity diagnostics for raw proxy candidates.

Scope guard:
    This is a diagnostic audit only. It does not stage or commit files, train
    ML models, implement probability calibration, implement high-tail
    regression, start A-L2, touch System B, touch SOLWEIG outputs, touch raster
    or raw archive paths, or modify archive collector hot paths.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SGT_TZ = "Asia/Singapore"
ADVANCED_PACKAGES = ["pythermalcomfort", "psychrolib", "pywbgt"]
REGIME_COLUMNS = [
    "combined_radiation_hot_regime",
    "shortwave_bin",
    "shortwave_3h_mean_bin",
    "direct_radiation_bin",
    "diffuse_radiation_bin",
    "temperature_bin",
    "humidity_bin",
    "wind_bin",
    "cloud_cover_bin",
]
PRESERVE_COLUMNS = [
    "station_id",
    "timestamp",
    "hour_sgt",
    "date",
    "merge_time_sgt_hour",
    "official_wbgt_c",
    "obs_ge31",
    "obs_ge33",
    "observed_wbgt_bin",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
    "shortwave_3h_mean",
    "direct_radiation",
    "diffuse_radiation",
    "cloud_cover",
    "precipitation",
    *REGIME_COLUMNS,
]


@dataclass(frozen=True)
class AuditResult:
    """Headline result for the A-L1H.1 formula/proxy audit."""

    acceptance_status: str
    decision_status: str
    best_formula_candidate: str
    best_formula_note: str
    comparator_reference: str
    high_tail_comparison: str
    fixed31_result: str
    radiation_hot_result: str
    next_recommended_action: str
    output_paths: list[Path]


def rel(path: Path) -> str:
    """Return a repo-relative POSIX path where possible."""
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
    """Parse the small scalar subset used by explicit lane configs."""
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
    """Parse the narrow YAML subset used by this repository's lane configs."""
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
        container: dict[str, Any] | list[Any] = [] if next_line.startswith("- ") else {}
        if not isinstance(parent, dict):
            raise ValueError(f"Unexpected YAML nested mapping under list: {stripped}")
        parent[key] = container
        stack.append((indent, container))
    return root


def load_config(path: Path) -> dict[str, Any]:
    """Read the explicit A-L1H.1 config."""
    return parse_simple_yaml(path.read_text(encoding="utf-8"))


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


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values for compact CSV cells."""
    out: list[str] = []
    for value in values:
        text = str(value)
        if text and text != "nan" and text not in out:
            out.append(text)
    return ";".join(out)


def numeric(series: pd.Series) -> pd.Series:
    """Convert a Series to numeric values."""
    return pd.to_numeric(series, errors="coerce")


def as_bool(series: pd.Series) -> pd.Series:
    """Convert bool-like values to a filled boolean Series."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes", "y"})


def safe_div(num: float, den: float) -> float:
    """Return a guarded division result."""
    return float(num / den) if den else float("nan")


def safe_r2(y: pd.Series, pred: pd.Series) -> float:
    """Return R2 for valid target/prediction rows."""
    mask = y.notna() & pred.notna()
    if int(mask.sum()) < 2:
        return float("nan")
    yy = y[mask].astype(float)
    pp = pred[mask].astype(float)
    denom = float(((yy - yy.mean()) ** 2).sum())
    if denom == 0.0:
        return float("nan")
    return 1.0 - float(((yy - pp) ** 2).sum()) / denom


def safe_corr(left: pd.Series, right: pd.Series) -> float:
    """Return Pearson correlation for valid numeric rows."""
    ll = numeric(left)
    rr = numeric(right)
    mask = ll.notna() & rr.notna()
    if int(mask.sum()) < 3:
        return float("nan")
    if float(ll[mask].std()) == 0.0 or float(rr[mask].std()) == 0.0:
        return float("nan")
    return float(ll[mask].corr(rr[mask]))


def parse_sgt_hour(series: pd.Series, column_name: str) -> pd.Series:
    """Normalize timestamps to SGT hourly merge-key strings."""
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


def token(value: float | str) -> str:
    """Build a filesystem/CSV-friendly token for candidate IDs."""
    return str(value).replace(".", "p").replace("+", "plus").replace("-", "m")


def markdown_cell(value: Any) -> str:
    """Format a Markdown table cell."""
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value).replace("|", "\\|")


def markdown_table(df: pd.DataFrame, columns: list[str] | None = None, limit: int = 12) -> str:
    """Render a compact Markdown table."""
    if df.empty:
        return "_No rows._"
    shown = df.copy()
    if columns is not None:
        shown = shown[[col for col in columns if col in shown.columns]]
    shown = shown.head(limit)
    headers = [str(col) for col in shown.columns]
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(markdown_cell(row[col]) for col in shown.columns) + " |" for _, row in shown.iterrows()]
    return "\n".join([header, separator, *body])


def stull_wet_bulb_c(t_c: pd.Series, rh_pct: pd.Series) -> pd.Series:
    """Stull (2011) wet-bulb approximation in degrees Celsius."""
    rh = numeric(rh_pct).clip(lower=0, upper=100)
    t = numeric(t_c)
    return (
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * np.power(rh, 1.5) * np.arctan(0.023101 * rh)
        - 4.686035
    )


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Build an input/file inventory without loading large optional tables fully."""
    inputs = config["inputs"]
    paths = [
        ("primary", "residual_weather_merge", resolve_path(str(inputs["residual_weather_merge"]))),
        ("primary", "residual_analysis_input", resolve_path(str(inputs["residual_analysis_input"]))),
        ("primary", "oof_predictions", resolve_path(str(inputs["oof_predictions"]))),
    ]
    for raw_path in inputs.get("optional_input_paths", []):
        paths.append(("optional_discovery", Path(str(raw_path)).stem, resolve_path(str(raw_path))))

    rows: list[dict[str, Any]] = []
    for role, label, path in paths:
        exists = path.exists()
        row: dict[str, Any] = {
            "inventory_role": role,
            "input_label": label,
            "path": rel(path),
            "exists": exists,
            "bytes": path.stat().st_size if exists else np.nan,
            "rows_sampled_or_total": np.nan,
            "column_count": np.nan,
            "columns": "",
            "weather_columns_present": "",
            "proxy_columns_present": "",
            "notes": "",
        }
        if exists and path.suffix.lower() in {".csv", ".gz"}:
            try:
                sample = pd.read_csv(path, nrows=0, compression="infer")
                row["column_count"] = len(sample.columns)
                row["columns"] = semicolon(sample.columns)
                weather_cols = [
                    *config["schema"].get("required_weather_columns", []),
                    *config["schema"].get("optional_weather_columns", []),
                ]
                row["weather_columns_present"] = semicolon([col for col in weather_cols if col in sample.columns])
                proxy_candidates = ["wbgt_proxy_v09_c", "wetbulb_stull_c_v09", "globe_temp_proxy_v09_c"]
                row["proxy_columns_present"] = semicolon([col for col in proxy_candidates if col in sample.columns])
                if role == "primary":
                    row["rows_sampled_or_total"] = int(len(pd.read_csv(path, usecols=[sample.columns[0]], compression="infer")))
            except Exception as exc:
                row["notes"] = f"inventory_read_failed: {exc}"
        elif exists and path.suffix.lower() == ".md":
            row["notes"] = "markdown_context_file"
        rows.append(row)
    return pd.DataFrame(rows)


def read_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read the primary audit inputs."""
    residual_weather = pd.read_csv(resolve_path(str(config["inputs"]["residual_weather_merge"])), low_memory=False)
    residual_input = pd.read_csv(resolve_path(str(config["inputs"]["residual_analysis_input"])), low_memory=False)
    oof = pd.read_csv(resolve_path(str(config["inputs"]["oof_predictions"])), low_memory=False)
    return residual_weather, residual_input, oof


def validate_required_weather(base: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    """Return missing weather columns required for physical formulas."""
    required = list(config["schema"].get("required_weather_columns", []))
    return [col for col in required if col not in base.columns or numeric(base[col]).notna().sum() == 0]


def unique_station_hours(residual_weather: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Deduplicate residual rows to one station-hour target for raw formulas."""
    station_col = str(config["schema"]["station_col"])
    merge_col = str(config["schema"]["merge_time_col"])
    target_col = str(config["schema"]["target_col"])
    keep_cols = [col for col in PRESERVE_COLUMNS if col in residual_weather.columns]
    sort_cols = [station_col, merge_col, str(config["schema"]["model_name_col"]), "cv_scheme", "fold"]
    sorted_frame = residual_weather.sort_values([col for col in sort_cols if col in residual_weather.columns]).copy()
    base = sorted_frame.drop_duplicates([station_col, merge_col], keep="first")[keep_cols].copy()
    duplicate_counts = sorted_frame.groupby([station_col, merge_col], dropna=False).size().rename("dedup_source_residual_rows")
    base = base.merge(duplicate_counts.reset_index(), on=[station_col, merge_col], how="left")
    base[target_col] = numeric(base[target_col])
    base["obs_ge31"] = as_bool(base["obs_ge31"]) if "obs_ge31" in base.columns else base[target_col] >= 31.0
    base["obs_ge33"] = as_bool(base["obs_ge33"]) if "obs_ge33" in base.columns else base[target_col] >= 33.0
    return base


def attach_v09_proxy(base: pd.DataFrame, oof: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str, bool]:
    """Attach the existing v09 proxy from OOF rows or reconstruct when absent."""
    out = base.copy()
    station_col = str(config["schema"]["station_col"])
    timestamp_col = str(config["schema"]["timestamp_col"])
    merge_col = str(config["schema"]["merge_time_col"])
    proxy_col = str(config["schema"]["oof_proxy_col"])

    if proxy_col in oof.columns and station_col in oof.columns and timestamp_col in oof.columns:
        proxy = oof[[station_col, timestamp_col, proxy_col]].copy()
        proxy[merge_col] = parse_sgt_hour(proxy[timestamp_col], timestamp_col)
        proxy[proxy_col] = numeric(proxy[proxy_col])
        proxy_grouped = (
            proxy.dropna(subset=[station_col, merge_col])
            .groupby([station_col, merge_col], as_index=False)
            .agg({proxy_col: "first"})
        )
        out = out.merge(proxy_grouped, on=[station_col, merge_col], how="left")
        if numeric(out[proxy_col]).notna().any():
            return out, "found_in_oof_predictions", True

    out[proxy_col] = compute_simple_wbgt(
        out,
        radiation_col="shortwave_radiation",
        k_value=0.0045,
        wind_floor=0.25,
    )
    return out, "reconstructed_v09_style_from_weather_k0p0045_wf0p25", False


def radiation_series(base: pd.DataFrame, radiation_input: str) -> pd.Series | None:
    """Return the configured radiation input series when available."""
    if radiation_input == "direct_plus_diffuse":
        if {"direct_radiation", "diffuse_radiation"}.issubset(base.columns):
            return numeric(base["direct_radiation"]) + numeric(base["diffuse_radiation"])
        return None
    if radiation_input in base.columns:
        return numeric(base[radiation_input])
    return None


def compute_simple_wbgt(base: pd.DataFrame, radiation_col: str, k_value: float, wind_floor: float) -> pd.Series:
    """Compute Stull wet-bulb plus simplified globe WBGT proxy."""
    twb = stull_wet_bulb_c(base["temperature_2m"], base["relative_humidity_2m"])
    rad = radiation_series(base, radiation_col)
    if rad is None:
        return pd.Series(np.nan, index=base.index)
    t = numeric(base["temperature_2m"])
    wind = numeric(base["wind_speed_10m"])
    globe = t + float(k_value) * rad / np.sqrt(wind.clip(lower=0) + float(wind_floor))
    return 0.7 * twb + 0.2 * globe + 0.1 * t


def prediction_common_columns(df: pd.DataFrame) -> list[str]:
    """Return preserved prediction columns available in a frame."""
    return [col for col in PRESERVE_COLUMNS if col in df.columns]


def make_score_predictions(residual_weather: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Build prediction rows for current M4/M7 OOF score comparators."""
    model_col = str(config["schema"]["model_name_col"])
    score_col = str(config["schema"]["model_score_col"])
    target_col = str(config["schema"]["target_col"])
    registry_rows: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    for model_name in config["candidates"].get("score_comparators", []):
        sub = residual_weather[residual_weather[model_col].astype(str).eq(str(model_name))].copy()
        status = "available" if not sub.empty and score_col in sub.columns else "blocked_missing_oof_score"
        registry_rows.append(
            {
                "candidate_id": model_name,
                "candidate_role": "score_comparator",
                "candidate_family": "current_oof_score",
                "implementation_status": status,
                "row_unit": "residual_model_row",
                "formula_definition": "OOF model_score from residual_weather_merge_full_period; comparator score, not raw formula.",
                "required_columns": semicolon([model_col, score_col, target_col]),
                "missing_columns": "" if status == "available" else score_col,
                "source": rel(resolve_path(str(config["inputs"]["residual_weather_merge"]))),
                "assumptions": "Retains residual-row OOF scores including LOSO and blocked-time rows.",
                "can_compute": status == "available",
            }
        )
        if status != "available":
            continue
        keep = prediction_common_columns(sub)
        pred = sub[keep].copy()
        pred["candidate_id"] = model_name
        pred["candidate_role"] = "score_comparator"
        pred["candidate_family"] = "current_oof_score"
        pred["row_unit"] = "residual_model_row"
        pred["source_model_name"] = sub[model_col].astype(str).values
        pred["cv_scheme"] = sub["cv_scheme"].astype(str).values if "cv_scheme" in sub.columns else ""
        pred["fold"] = sub["fold"].astype(str).values if "fold" in sub.columns else ""
        pred["prediction_wbgt_c"] = numeric(sub[score_col]).values
        pred["wetbulb_stull_c"] = np.nan
        pred["globe_simple_c"] = np.nan
        pred["radiation_input"] = ""
        pred["radiation_value"] = np.nan
        pred["k_value"] = np.nan
        pred["wind_floor"] = np.nan
        pred["v09_proxy_source"] = ""
        frames.append(pred)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(), registry_rows


def make_formula_predictions(
    base: pd.DataFrame,
    config: dict[str, Any],
    v09_source: str,
    v09_found: bool,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Build deduplicated raw formula/proxy prediction rows."""
    target_col = str(config["schema"]["target_col"])
    proxy_col = str(config["schema"]["oof_proxy_col"])
    frames: list[pd.DataFrame] = []
    registry_rows: list[dict[str, Any]] = []
    keep = prediction_common_columns(base)

    proxy_status = "available" if proxy_col in base.columns and numeric(base[proxy_col]).notna().any() else "blocked_missing_proxy"
    registry_rows.append(
        {
            "candidate_id": proxy_col,
            "candidate_role": "raw_proxy",
            "candidate_family": "existing_v09_proxy" if v09_found else "reconstructed_v09_style_proxy",
            "implementation_status": proxy_status,
            "row_unit": "unique_station_hour",
            "formula_definition": "Existing wbgt_proxy_v09_c from OOF rows." if v09_found else "Reconstructed v09-style Stull + simple globe proxy using k=0.0045 and wind_floor=0.25.",
            "required_columns": semicolon([target_col, proxy_col]),
            "missing_columns": "" if proxy_status == "available" else proxy_col,
            "source": v09_source,
            "assumptions": "Comparator proxy only; not promoted as canonical WBGT_A.",
            "can_compute": proxy_status == "available",
        }
    )
    if proxy_status == "available":
        pred = base[keep].copy()
        pred["candidate_id"] = proxy_col
        pred["candidate_role"] = "raw_proxy"
        pred["candidate_family"] = "existing_v09_proxy" if v09_found else "reconstructed_v09_style_proxy"
        pred["row_unit"] = "unique_station_hour"
        pred["source_model_name"] = ""
        pred["cv_scheme"] = ""
        pred["fold"] = ""
        pred["prediction_wbgt_c"] = numeric(base[proxy_col]).values
        pred["wetbulb_stull_c"] = stull_wet_bulb_c(base["temperature_2m"], base["relative_humidity_2m"]).values
        pred["globe_simple_c"] = np.nan
        pred["radiation_input"] = "v09_proxy_column"
        pred["radiation_value"] = np.nan
        pred["k_value"] = np.nan
        pred["wind_floor"] = np.nan
        pred["v09_proxy_source"] = v09_source
        frames.append(pred)

    twb = stull_wet_bulb_c(base["temperature_2m"], base["relative_humidity_2m"])
    t = numeric(base["temperature_2m"])
    wind = numeric(base["wind_speed_10m"])
    for radiation_input in config["candidates"].get("radiation_inputs", []):
        rad = radiation_series(base, str(radiation_input))
        missing = []
        if rad is None or rad.notna().sum() == 0:
            missing.append(str(radiation_input))
        for wind_floor in config["candidates"].get("wind_floor_values", []):
            for k_value in config["candidates"].get("k_values", []):
                k_float = float(k_value)
                wf_float = float(wind_floor)
                candidate_id = f"stull_globe_{token(radiation_input)}_k{token(k_float)}_wf{token(wf_float)}"
                status = "available" if not missing else "blocked_missing_radiation_input"
                registry_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "candidate_role": "raw_formula_proxy",
                        "candidate_family": "stull_wetbulb_simple_globe_k_sweep",
                        "implementation_status": status,
                        "row_unit": "unique_station_hour",
                        "formula_definition": (
                            "wetbulb=Stull(T,RH); globe_simple=T + k*radiation/sqrt(wind_speed_10m + wind_floor); "
                            "WBGT_proxy=0.7*wetbulb + 0.2*globe_simple + 0.1*T"
                        ),
                        "required_columns": semicolon(["temperature_2m", "relative_humidity_2m", "wind_speed_10m", str(radiation_input)]),
                        "missing_columns": semicolon(missing),
                        "source": "computed_from_residual_weather_merge_full_period",
                        "assumptions": f"k={k_float}; wind_floor={wf_float}; radiation_input={radiation_input}; screening formula only.",
                        "can_compute": status == "available",
                    }
                )
                if status != "available" or rad is None:
                    continue
                globe = t + k_float * rad / np.sqrt(wind.clip(lower=0) + wf_float)
                pred_score = 0.7 * twb + 0.2 * globe + 0.1 * t
                pred = base[keep].copy()
                pred["candidate_id"] = candidate_id
                pred["candidate_role"] = "raw_formula_proxy"
                pred["candidate_family"] = "stull_wetbulb_simple_globe_k_sweep"
                pred["row_unit"] = "unique_station_hour"
                pred["source_model_name"] = ""
                pred["cv_scheme"] = ""
                pred["fold"] = ""
                pred["prediction_wbgt_c"] = pred_score.values
                pred["wetbulb_stull_c"] = twb.values
                pred["globe_simple_c"] = globe.values
                pred["radiation_input"] = str(radiation_input)
                pred["radiation_value"] = rad.values
                pred["k_value"] = k_float
                pred["wind_floor"] = wf_float
                pred["v09_proxy_source"] = ""
                frames.append(pred)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(), registry_rows


def package_registry_rows() -> list[dict[str, Any]]:
    """Return availability rows for optional advanced formula routes."""
    rows: list[dict[str, Any]] = []
    for package in ADVANCED_PACKAGES:
        available = importlib.util.find_spec(package) is not None
        rows.append(
            {
                "candidate_id": f"advanced_package_{package}",
                "candidate_role": "advanced_formula_package_check",
                "candidate_family": "optional_advanced_physics_route",
                "implementation_status": "detected_not_used" if available else "unavailable_not_installed",
                "row_unit": "not_computed",
                "formula_definition": "Package availability check only; no advanced formula is computed in this diagnostic unless assumptions are documented.",
                "required_columns": "",
                "missing_columns": "" if available else package,
                "source": package,
                "assumptions": "No pip install performed; advanced route needs separate validation before use.",
                "can_compute": False,
            }
        )

    local_files = list((ROOT / "scripts").rglob("*liljegren*.py")) if (ROOT / "scripts").exists() else []
    rows.append(
        {
            "candidate_id": "local_liljegren_style_implementation",
            "candidate_role": "advanced_formula_local_check",
            "candidate_family": "optional_advanced_physics_route",
            "implementation_status": "detected_not_used" if local_files else "unavailable_no_local_implementation",
            "row_unit": "not_computed",
            "formula_definition": "Local Liljegren-style implementation check only; not faked.",
            "required_columns": "validated implementation; documented units; radiation and wind assumptions",
            "missing_columns": "" if local_files else "validated local Liljegren-style implementation",
            "source": semicolon([rel(path) for path in local_files]) if local_files else "none",
            "assumptions": "Advanced formula route remains blocked/partial until separately validated.",
            "can_compute": False,
        }
    )
    return rows


def finalize_predictions(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Add shared diagnostic columns to prediction rows."""
    target_col = str(config["schema"]["target_col"])
    out = predictions.copy()
    out[target_col] = numeric(out[target_col])
    out["prediction_wbgt_c"] = numeric(out["prediction_wbgt_c"])
    out["residual_official_minus_pred_c"] = out[target_col] - out["prediction_wbgt_c"]
    out["error_pred_minus_official_c"] = out["prediction_wbgt_c"] - out[target_col]
    out["abs_error_c"] = out["error_pred_minus_official_c"].abs()
    out["obs_ge31"] = as_bool(out["obs_ge31"]) if "obs_ge31" in out.columns else out[target_col] >= 31.0
    out["obs_ge33"] = as_bool(out["obs_ge33"]) if "obs_ge33" in out.columns else out[target_col] >= 33.0
    out["pred_ge31_fixed"] = out["prediction_wbgt_c"] >= 31.0
    out["pred_ge33_fixed"] = out["prediction_wbgt_c"] >= 33.0
    out["ge31_event_class_formula"] = np.select(
        [
            out["obs_ge31"] & out["pred_ge31_fixed"],
            out["obs_ge31"] & ~out["pred_ge31_fixed"],
            ~out["obs_ge31"] & out["pred_ge31_fixed"],
        ],
        ["hit", "miss", "false_alarm"],
        default="true_negative",
    )
    out.insert(0, "prediction_row_id", np.arange(len(out)))
    return out


def threshold_counts(y_event: pd.Series, p_event: pd.Series) -> dict[str, Any]:
    """Return binary threshold counts and rates."""
    y = y_event.astype(bool)
    p = p_event.astype(bool)
    hits = int((y & p).sum())
    misses = int((y & ~p).sum())
    false_alarms = int((~y & p).sum())
    true_negatives = int((~y & ~p).sum())
    precision = safe_div(hits, hits + false_alarms)
    recall = safe_div(hits, hits + misses)
    if hits == 0 and (misses > 0 or false_alarms > 0):
        f1 = 0.0
    elif not (math.isnan(precision) or math.isnan(recall)):
        f1 = safe_div(2.0 * precision * recall, precision + recall)
    else:
        f1 = float("nan")
    return {
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "true_negatives": true_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def threshold_values(config: dict[str, Any]) -> list[float]:
    """Build inclusive threshold-scan values from config."""
    start = float(config["analysis"].get("threshold_scan_start_c", 24.0))
    stop = float(config["analysis"].get("threshold_scan_stop_c", 34.0))
    step = float(config["analysis"].get("threshold_scan_step_c", 0.05))
    scale = 100
    return [value / scale for value in range(int(round(start * scale)), int(round(stop * scale)) + 1, int(round(step * scale)))]


def best_f1_threshold(y: pd.Series, score: pd.Series, event_threshold: float, scan_values: list[float]) -> dict[str, float]:
    """Find the score threshold with best F1 for an event threshold."""
    rows: list[dict[str, float]] = []
    event = numeric(y) >= event_threshold
    score_num = numeric(score)
    valid = numeric(y).notna() & score_num.notna()
    for score_threshold in scan_values:
        counts = threshold_counts(event[valid], score_num[valid] >= score_threshold)
        rows.append(
            {
                "score_threshold": score_threshold,
                "precision": counts["precision"],
                "recall": counts["recall"],
                "f1": counts["f1"],
            }
        )
    scan = pd.DataFrame(rows).dropna(subset=["f1"])
    if scan.empty:
        return {"best_f1_threshold": float("nan"), "best_f1": float("nan"), "best_f1_precision": float("nan"), "best_f1_recall": float("nan")}
    chosen = scan.sort_values(["f1", "recall", "precision", "score_threshold"], ascending=[False, False, False, True]).iloc[0]
    return {
        "best_f1_threshold": float(chosen["score_threshold"]),
        "best_f1": float(chosen["f1"]),
        "best_f1_precision": float(chosen["precision"]),
        "best_f1_recall": float(chosen["recall"]),
    }


def overall_metrics(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compute overall prediction and high-tail metrics by candidate."""
    target_col = str(config["schema"]["target_col"])
    rows: list[dict[str, Any]] = []
    official_full = numeric(predictions[target_col])
    for candidate_id, group in predictions.groupby("candidate_id", sort=False):
        y = numeric(group[target_col])
        pred = numeric(group["prediction_wbgt_c"])
        valid = y.notna() & pred.notna()
        yy = y[valid]
        pp = pred[valid]
        err = pp - yy
        residual = yy - pp
        obs31 = group.loc[valid, "obs_ge31"].astype(bool)
        station_residual = group.loc[valid].assign(_residual=residual.values).groupby("station_id")["_residual"].mean()
        official_range = float(yy.quantile(0.99) - yy.quantile(0.50)) if len(yy) else float("nan")
        predicted_range = float(pp.quantile(0.99) - pp.quantile(0.50)) if len(pp) else float("nan")
        row = {
            "candidate_id": candidate_id,
            "candidate_role": group["candidate_role"].iloc[0],
            "candidate_family": group["candidate_family"].iloc[0],
            "row_unit": group["row_unit"].iloc[0],
            "n": int(valid.sum()),
            "unique_station_hours": int(group.loc[valid, ["station_id", "merge_time_sgt_hour"]].drop_duplicates().shape[0]) if "merge_time_sgt_hour" in group.columns else int(valid.sum()),
            "bias": float(err.mean()) if len(err) else float("nan"),
            "MAE": float(err.abs().mean()) if len(err) else float("nan"),
            "RMSE": float(np.sqrt((err**2).mean())) if len(err) else float("nan"),
            "R2": safe_r2(y, pred),
            "max_predicted_wbgt": float(pp.max()) if len(pp) else float("nan"),
            "p95_predicted_wbgt": float(pp.quantile(0.95)) if len(pp) else float("nan"),
            "p99_predicted_wbgt": float(pp.quantile(0.99)) if len(pp) else float("nan"),
            "median_predicted_wbgt": float(pp.quantile(0.50)) if len(pp) else float("nan"),
            "official_p99_wbgt": float(yy.quantile(0.99)) if len(yy) else float("nan"),
            "official_median_wbgt": float(yy.quantile(0.50)) if len(yy) else float("nan"),
            "predicted_p99_minus_median": predicted_range,
            "official_p99_minus_median": official_range,
            "compression_ratio_p99_median": safe_div(predicted_range, official_range),
            "MAE_observed_ge31": float((pp[obs31.values] - yy[obs31.values]).abs().mean()) if int(obs31.sum()) else float("nan"),
            "mean_residual_observed_ge31": float((yy[obs31.values] - pp[obs31.values]).mean()) if int(obs31.sum()) else float("nan"),
            "station_residual_range": float(station_residual.max() - station_residual.min()) if len(station_residual) else float("nan"),
            "corr_prediction_shortwave_radiation": safe_corr(group["prediction_wbgt_c"], group.get("shortwave_radiation", pd.Series(index=group.index, dtype=float))),
            "corr_residual_shortwave_radiation": safe_corr(group["residual_official_minus_pred_c"], group.get("shortwave_radiation", pd.Series(index=group.index, dtype=float))),
            "official_global_p99_wbgt_all_prediction_rows": float(official_full.dropna().quantile(0.99)) if official_full.notna().any() else float("nan"),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def threshold_metrics(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compute fixed 31/33 and best-F1 ge31 threshold metrics."""
    target_col = str(config["schema"]["target_col"])
    scan = threshold_values(config)
    rows: list[dict[str, Any]] = []
    for candidate_id, group in predictions.groupby("candidate_id", sort=False):
        y = numeric(group[target_col])
        pred = numeric(group["prediction_wbgt_c"])
        valid = y.notna() & pred.notna()
        yy = y[valid]
        pp = pred[valid]
        obs31 = yy >= 31.0
        pred31 = pp >= 31.0
        obs33 = yy >= 33.0
        pred33 = pp >= 33.0
        ge31 = threshold_counts(obs31, pred31)
        ge33 = threshold_counts(obs33, pred33)
        best31 = best_f1_threshold(yy, pp, 31.0, scan)
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_role": group["candidate_role"].iloc[0],
                "candidate_family": group["candidate_family"].iloc[0],
                "row_unit": group["row_unit"].iloc[0],
                "n": int(valid.sum()),
                "observed_ge31_count": int(obs31.sum()),
                "predicted_ge31_fixed_count": int(pred31.sum()),
                "hits_ge31": ge31["hits"],
                "misses_ge31": ge31["misses"],
                "false_alarms_ge31": ge31["false_alarms"],
                "precision_ge31": ge31["precision"],
                "recall_ge31": ge31["recall"],
                "f1_ge31": ge31["f1"],
                "best_f1_threshold_ge31": best31["best_f1_threshold"],
                "best_f1_ge31": best31["best_f1"],
                "best_f1_precision_ge31": best31["best_f1_precision"],
                "best_f1_recall_ge31": best31["best_f1_recall"],
                "threshold_gap_to_31": best31["best_f1_threshold"] - 31.0 if pd.notna(best31["best_f1_threshold"]) else float("nan"),
                "observed_ge33_count": int(obs33.sum()),
                "predicted_ge33_fixed_count": int(pred33.sum()),
                "hits_ge33": ge33["hits"],
                "misses_ge33": ge33["misses"],
                "false_alarms_ge33": ge33["false_alarms"],
                "precision_ge33_exploratory": ge33["precision"],
                "recall_ge33": ge33["recall"],
                "f1_ge33_exploratory": ge33["f1"],
            }
        )
    return pd.DataFrame(rows)


def residual_by_observed_bin(predictions: pd.DataFrame) -> pd.DataFrame:
    """Summarise residuals by observed WBGT bin."""
    if "observed_wbgt_bin" not in predictions.columns:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (candidate_id, bin_name), group in predictions.groupby(["candidate_id", "observed_wbgt_bin"], dropna=False, sort=False):
        rows.append(summary_row(candidate_id, "observed_wbgt_bin", str(bin_name), group))
    return pd.DataFrame(rows)


def residual_by_radiation_regime(predictions: pd.DataFrame) -> pd.DataFrame:
    """Summarise residuals and misses by radiation/weather regime labels."""
    rows: list[dict[str, Any]] = []
    for regime_col in [col for col in REGIME_COLUMNS if col in predictions.columns]:
        for (candidate_id, regime_bin), group in predictions.groupby(["candidate_id", regime_col], dropna=False, sort=False):
            rows.append(summary_row(candidate_id, regime_col, str(regime_bin), group))
    return pd.DataFrame(rows)


def summary_row(candidate_id: str, variable: str, bin_name: str, group: pd.DataFrame) -> dict[str, Any]:
    """Return one grouped residual summary row."""
    y = numeric(group["official_wbgt_c"])
    pred = numeric(group["prediction_wbgt_c"])
    valid = y.notna() & pred.notna()
    yy = y[valid]
    pp = pred[valid]
    residual = yy - pp
    obs31 = yy >= 31.0
    pred31 = pp >= 31.0
    counts = threshold_counts(obs31, pred31)
    return {
        "candidate_id": candidate_id,
        "candidate_role": group["candidate_role"].iloc[0],
        "candidate_family": group["candidate_family"].iloc[0],
        "regime_variable": variable,
        "regime_bin": bin_name,
        "n": int(valid.sum()),
        "n_obs_ge31": int(obs31.sum()),
        "n_pred_ge31": int(pred31.sum()),
        "n_ge31_hit": counts["hits"],
        "n_ge31_miss": counts["misses"],
        "n_ge31_false_alarm": counts["false_alarms"],
        "ge31_miss_rate_among_observed": safe_div(counts["misses"], int(obs31.sum())),
        "mean_official_wbgt_c": float(yy.mean()) if len(yy) else float("nan"),
        "mean_prediction_wbgt_c": float(pp.mean()) if len(pp) else float("nan"),
        "mean_residual_official_minus_pred_c": float(residual.mean()) if len(residual) else float("nan"),
        "median_residual_official_minus_pred_c": float(residual.median()) if len(residual) else float("nan"),
        "p75_residual_official_minus_pred_c": float(residual.quantile(0.75)) if len(residual) else float("nan"),
        "p90_residual_official_minus_pred_c": float(residual.quantile(0.90)) if len(residual) else float("nan"),
        "mean_abs_error_c": float((pp - yy).abs().mean()) if len(pp) else float("nan"),
        "p90_abs_error_c": float((pp - yy).abs().quantile(0.90)) if len(pp) else float("nan"),
        "max_abs_error_c": float((pp - yy).abs().max()) if len(pp) else float("nan"),
    }


def ge31_miss_by_regime(regime_summary: pd.DataFrame) -> pd.DataFrame:
    """Extract ge31 miss concentration rows from regime summaries."""
    if regime_summary.empty:
        return pd.DataFrame()
    rows: list[pd.DataFrame] = []
    for candidate_id, group in regime_summary.groupby("candidate_id", sort=False):
        # Sum over all bins is only meaningful within each regime variable.
        for regime_variable, sub in group.groupby("regime_variable", sort=False):
            total_for_variable = int(sub["n_ge31_miss"].sum())
            out = sub.copy()
            out["share_of_candidate_ge31_misses_in_regime_variable"] = out["n_ge31_miss"].map(
                lambda value: safe_div(float(value), float(total_for_variable))
            )
            rows.append(out)
    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return result[
        [
            "candidate_id",
            "candidate_role",
            "candidate_family",
            "regime_variable",
            "regime_bin",
            "n_obs_ge31",
            "n_ge31_miss",
            "ge31_miss_rate_among_observed",
            "share_of_candidate_ge31_misses_in_regime_variable",
            "mean_residual_official_minus_pred_c",
        ]
    ]


def component_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute formula component and compression diagnostics."""
    rows: list[dict[str, Any]] = []
    for candidate_id, group in predictions.groupby("candidate_id", sort=False):
        y = numeric(group["official_wbgt_c"])
        pred = numeric(group["prediction_wbgt_c"])
        valid = y.notna() & pred.notna()
        yy = y[valid]
        pp = pred[valid]
        official_range = float(yy.quantile(0.99) - yy.quantile(0.50)) if len(yy) else float("nan")
        predicted_range = float(pp.quantile(0.99) - pp.quantile(0.50)) if len(pp) else float("nan")
        row = {
            "candidate_id": candidate_id,
            "candidate_role": group["candidate_role"].iloc[0],
            "candidate_family": group["candidate_family"].iloc[0],
            "radiation_input": group["radiation_input"].iloc[0] if "radiation_input" in group.columns else "",
            "k_value": float(group["k_value"].dropna().iloc[0]) if "k_value" in group.columns and group["k_value"].notna().any() else np.nan,
            "wind_floor": float(group["wind_floor"].dropna().iloc[0]) if "wind_floor" in group.columns and group["wind_floor"].notna().any() else np.nan,
            "wetbulb_min_c": float(numeric(group["wetbulb_stull_c"]).min()) if "wetbulb_stull_c" in group.columns and numeric(group["wetbulb_stull_c"]).notna().any() else np.nan,
            "wetbulb_max_c": float(numeric(group["wetbulb_stull_c"]).max()) if "wetbulb_stull_c" in group.columns and numeric(group["wetbulb_stull_c"]).notna().any() else np.nan,
            "globe_simple_min_c": float(numeric(group["globe_simple_c"]).min()) if "globe_simple_c" in group.columns and numeric(group["globe_simple_c"]).notna().any() else np.nan,
            "globe_simple_max_c": float(numeric(group["globe_simple_c"]).max()) if "globe_simple_c" in group.columns and numeric(group["globe_simple_c"]).notna().any() else np.nan,
            "formula_min_c": float(pp.min()) if len(pp) else np.nan,
            "formula_max_c": float(pp.max()) if len(pp) else np.nan,
            "formula_dynamic_range_c": float(pp.max() - pp.min()) if len(pp) else np.nan,
            "predicted_p99_minus_median": predicted_range,
            "official_p99_minus_median": official_range,
            "compression_ratio": safe_div(predicted_range, official_range),
            "corr_prediction_shortwave_radiation": safe_corr(group["prediction_wbgt_c"], group.get("shortwave_radiation", pd.Series(index=group.index, dtype=float))),
            "corr_residual_shortwave_radiation": safe_corr(group["residual_official_minus_pred_c"], group.get("shortwave_radiation", pd.Series(index=group.index, dtype=float))),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def add_regime_rates(overall: pd.DataFrame, ge31_regime: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Attach selected radiation-hot miss-rate diagnostics to overall metrics."""
    out = overall.copy()
    rate_specs = [
        ("combined_radiation_hot_regime", str(config["analysis"].get("radiation_hot_label", "radiation_hot")), "ge31_miss_rate_radiation_hot"),
        ("shortwave_bin", str(config["analysis"].get("very_high_label", "very_high")), "ge31_miss_rate_shortwave_very_high"),
        ("shortwave_3h_mean_bin", str(config["analysis"].get("very_high_label", "very_high")), "ge31_miss_rate_shortwave_3h_mean_very_high"),
    ]
    for variable, bin_name, output_col in rate_specs:
        focus = ge31_regime[
            ge31_regime["regime_variable"].eq(variable)
            & ge31_regime["regime_bin"].astype(str).eq(bin_name)
        ]
        rates = focus.set_index("candidate_id")["ge31_miss_rate_among_observed"].to_dict()
        out[output_col] = out["candidate_id"].map(rates)
    return out


def decide_result(
    overall: pd.DataFrame,
    thresholds: pd.DataFrame,
    ge31_regime: pd.DataFrame,
    missing_weather: list[str],
    output_paths: list[Path],
    config: dict[str, Any],
) -> AuditResult:
    """Classify the audit outcome and choose the best diagnostic formula."""
    if missing_weather:
        return AuditResult(
            acceptance_status="BLOCKED",
            decision_status="BLOCKED",
            best_formula_candidate="none",
            best_formula_note=f"Missing required weather inputs: {semicolon(missing_weather)}",
            comparator_reference="none",
            high_tail_comparison="blocked by missing weather inputs",
            fixed31_result="blocked",
            radiation_hot_result="blocked",
            next_recommended_action="Secure required temperature, humidity, wind, and radiation inputs before formula/proxy audit.",
            output_paths=output_paths,
        )

    comparator_ids = [str(value) for value in config["candidates"].get("score_comparators", [])]
    comparators = overall[overall["candidate_id"].isin(comparator_ids)].copy()
    formula_overall = overall[overall["candidate_role"].isin(["raw_proxy", "raw_formula_proxy"])].copy()
    if formula_overall.empty or comparators.empty:
        return AuditResult(
            acceptance_status="FAILED",
            decision_status="BLOCKED",
            best_formula_candidate="none",
            best_formula_note="Comparator or formula metrics were unavailable.",
            comparator_reference="none",
            high_tail_comparison="unavailable",
            fixed31_result="unavailable",
            radiation_hot_result="unavailable",
            next_recommended_action="Re-run after fixing candidate registry or input joins.",
            output_paths=output_paths,
        )

    comparator_ref = comparators.sort_values(["mean_residual_observed_ge31", "MAE"], ascending=[True, True]).iloc[0]
    formula_best = formula_overall.sort_values(["mean_residual_observed_ge31", "MAE"], ascending=[True, True]).iloc[0]
    comparator_id = str(comparator_ref["candidate_id"])
    best_id = str(formula_best["candidate_id"])
    high_tail_improvement = float(comparator_ref["mean_residual_observed_ge31"] - formula_best["mean_residual_observed_ge31"])

    threshold_map = thresholds.set_index("candidate_id")
    comparator_thr = threshold_map.loc[comparator_id]
    formula_thr = threshold_map.loc[best_id]
    comparator_gap_abs = abs(float(comparator_thr["threshold_gap_to_31"]))
    formula_gap_abs = abs(float(formula_thr["threshold_gap_to_31"]))
    gap_improvement = comparator_gap_abs - formula_gap_abs
    severe_false_alarm_limit = float(config["analysis"].get("severe_false_alarm_multiplier", 2.0)) * max(float(comparator_thr["false_alarms_ge31"]), 1.0)
    false_alarm_ok = float(formula_thr["false_alarms_ge31"]) <= severe_false_alarm_limit
    mae_ok = float(formula_best["MAE"]) <= float(comparator_ref["MAE"]) + float(config["analysis"].get("decision_mae_degradation_limit_c", 0.25))
    high_tail_ok = high_tail_improvement >= float(config["analysis"].get("decision_high_tail_residual_improvement_c", 0.25))
    threshold_ok = gap_improvement >= float(config["analysis"].get("decision_threshold_gap_improvement_c", 0.5))

    any_fixed31_formula = thresholds[
        thresholds["candidate_id"].isin(formula_overall["candidate_id"])
        & (thresholds["predicted_ge31_fixed_count"] > 0)
    ].copy()
    if any_fixed31_formula.empty:
        fixed31_result = "No raw formula/proxy candidate produced fixed_31 crossings."
    else:
        best_fixed = any_fixed31_formula.sort_values(["f1_ge31", "false_alarms_ge31"], ascending=[False, True]).iloc[0]
        fixed31_result = (
            f"Best fixed_31 formula crossing was {best_fixed['candidate_id']} with "
            f"{int(best_fixed['predicted_ge31_fixed_count'])} predicted positives, "
            f"{int(best_fixed['hits_ge31'])} hits, and {int(best_fixed['false_alarms_ge31'])} false alarms."
        )

    rad_focus = ge31_regime[
        ge31_regime["regime_variable"].eq("combined_radiation_hot_regime")
        & ge31_regime["regime_bin"].astype(str).eq(str(config["analysis"].get("radiation_hot_label", "radiation_hot")))
    ]
    rad_map = rad_focus.set_index("candidate_id")["ge31_miss_rate_among_observed"].to_dict()
    radiation_hot_result = (
        f"{best_id} radiation-hot ge31 miss rate={rad_map.get(best_id, np.nan):.3f}; "
        f"{comparator_id} radiation-hot ge31 miss rate={rad_map.get(comparator_id, np.nan):.3f}."
    )

    if high_tail_ok and threshold_ok and false_alarm_ok and mae_ok:
        decision_status = "PROMISING_DIAGNOSTIC"
        next_action = "Open a deeper formula-v2 implementation and validation review before any canonical WBGT_A change."
    else:
        decision_status = "WEAK_OR_NEGATIVE"
        next_action = "A-L1H.2 probability / threshold calibration review is the more direct next action; keep deeper formula-v2 and high-tail regression behind review gates, and start A-L2 only after Level 1 high-tail / regime control."

    high_tail_comparison = (
        f"{best_id} mean observed-ge31 residual={float(formula_best['mean_residual_observed_ge31']):.3f} C "
        f"versus {comparator_id}={float(comparator_ref['mean_residual_observed_ge31']):.3f} C "
        f"(positive means official minus prediction; improvement={high_tail_improvement:.3f} C)."
    )
    best_note = (
        f"Least-compressed raw formula/proxy by observed-ge31 residual was {best_id}; "
        f"MAE={float(formula_best['MAE']):.3f} C, max_pred={float(formula_best['max_predicted_wbgt']):.3f} C, "
        f"best-F1 ge31 threshold={float(formula_thr['best_f1_threshold_ge31']):.2f} C."
    )
    return AuditResult(
        acceptance_status="PASS",
        decision_status=decision_status,
        best_formula_candidate=best_id,
        best_formula_note=best_note,
        comparator_reference=comparator_id,
        high_tail_comparison=high_tail_comparison,
        fixed31_result=fixed31_result,
        radiation_hot_result=radiation_hot_result,
        next_recommended_action=next_action,
        output_paths=output_paths,
    )


def write_report(
    path: Path,
    inventory: pd.DataFrame,
    registry: pd.DataFrame,
    overall: pd.DataFrame,
    thresholds: pd.DataFrame,
    component: pd.DataFrame,
    observed_bin: pd.DataFrame,
    ge31_regime: pd.DataFrame,
    result: AuditResult,
) -> None:
    """Write the Markdown physics-audit report."""
    package_rows = registry[registry["candidate_role"].str.contains("advanced_formula", na=False)].copy()
    comparator_rows = overall[overall["candidate_role"].eq("score_comparator")].sort_values("MAE")
    formula_rows = overall[overall["candidate_role"].isin(["raw_proxy", "raw_formula_proxy"])].sort_values(
        ["mean_residual_observed_ge31", "MAE"],
        ascending=[True, True],
    )
    threshold_focus = thresholds.sort_values(["candidate_role", "f1_ge31", "best_f1_ge31"], ascending=[True, False, False])
    hot_focus = ge31_regime[
        ge31_regime["regime_variable"].isin(["combined_radiation_hot_regime", "shortwave_bin", "shortwave_3h_mean_bin"])
    ].sort_values(["candidate_id", "regime_variable", "regime_bin"])
    high_tail_bins = observed_bin[observed_bin["regime_bin"].isin(["31-32", "32-33", ">=33"])].sort_values(
        ["candidate_id", "regime_bin"]
    )

    lines = [
        "# System A A-L1H.1 Formula / Physical Proxy Audit",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Acceptance status: `{result.acceptance_status}`",
        f"Diagnostic decision: `{result.decision_status}`",
        f"Branch: `{git_branch()}`",
        "",
        "## 1. Inputs and Candidate Registry",
        "",
        "This audit uses the A-L1H.0c full-period residual/weather merge as diagnostic evidence. It does not treat A-L1H.0c as proof that the v09 formula caused high-tail compression.",
        "",
        markdown_table(
            inventory,
            ["inventory_role", "input_label", "path", "exists", "rows_sampled_or_total", "weather_columns_present", "proxy_columns_present", "notes"],
            limit=14,
        ),
        "",
        "Candidate registry summary:",
        "",
        markdown_table(
            registry,
            ["candidate_id", "candidate_role", "candidate_family", "implementation_status", "row_unit", "missing_columns", "source"],
            limit=20,
        ),
        "",
        "## 2. Formula Definitions and Assumptions",
        "",
        "- `M4_inertia_ridge` and `M7_compact_weather_ridge` are current OOF score comparators from residual rows; they are not raw physical formulas.",
        "- `wbgt_proxy_v09_c` is the existing v09 proxy when present in OOF rows; if absent, the audit reconstructs only a labelled v09-style diagnostic.",
        "- Stull simple-globe candidates use `wetbulb=Stull(T,RH)`, `globe_simple=T + k*radiation/sqrt(wind_speed_10m + wind_floor)`, and `WBGT_proxy=0.7*wetbulb + 0.2*globe_simple + 0.1*T`.",
        "- k values, wind floors, and radiation inputs are config-driven. These are screening proxies, not canonical WBGT_A replacements.",
        "- Formula candidates are computed on deduplicated unique station-hour targets; M4/M7 comparators retain residual-row OOF scores including LOSO and blocked-time rows.",
        "",
        "## 3. Advanced Formula Packages",
        "",
        markdown_table(package_rows, ["candidate_id", "implementation_status", "source", "missing_columns", "assumptions"], limit=10),
        "",
        "No Liljegren-style formula is faked. Advanced physics routes require a separate implementation and validation task before any System A reporting use.",
        "",
        "## 4. Overall Metrics",
        "",
        "Comparator scores:",
        "",
        markdown_table(
            comparator_rows,
            ["candidate_id", "n", "bias", "MAE", "RMSE", "R2", "max_predicted_wbgt", "p99_predicted_wbgt", "mean_residual_observed_ge31", "compression_ratio_p99_median"],
            limit=6,
        ),
        "",
        "Best raw formula/proxy candidates by observed-ge31 residual:",
        "",
        markdown_table(
            formula_rows,
            ["candidate_id", "n", "bias", "MAE", "RMSE", "R2", "max_predicted_wbgt", "p99_predicted_wbgt", "mean_residual_observed_ge31", "compression_ratio_p99_median"],
            limit=10,
        ),
        "",
        "## 5. Fixed_31 / Best-F1 Threshold Metrics",
        "",
        markdown_table(
            threshold_focus,
            ["candidate_id", "candidate_role", "observed_ge31_count", "predicted_ge31_fixed_count", "hits_ge31", "misses_ge31", "false_alarms_ge31", "precision_ge31", "recall_ge31", "f1_ge31", "best_f1_threshold_ge31", "best_f1_ge31", "threshold_gap_to_31", "observed_ge33_count", "predicted_ge33_fixed_count", "recall_ge33"],
            limit=16,
        ),
        "",
        "ge33 metrics are exploratory only and are not used to promote a formula candidate.",
        "",
        "## 6. High-Tail Compression Diagnostics",
        "",
        result.high_tail_comparison,
        "",
        markdown_table(
            high_tail_bins,
            ["candidate_id", "regime_bin", "n", "n_obs_ge31", "n_pred_ge31", "n_ge31_miss", "mean_residual_official_minus_pred_c", "mean_abs_error_c"],
            limit=20,
        ),
        "",
        "Component diagnostics:",
        "",
        markdown_table(
            component.sort_values(["candidate_role", "compression_ratio"], ascending=[True, False]),
            ["candidate_id", "radiation_input", "k_value", "wind_floor", "wetbulb_min_c", "wetbulb_max_c", "globe_simple_min_c", "globe_simple_max_c", "formula_dynamic_range_c", "compression_ratio", "corr_prediction_shortwave_radiation", "corr_residual_shortwave_radiation"],
            limit=14,
        ),
        "",
        "## 7. Radiation-Hot Regime Diagnostics",
        "",
        result.radiation_hot_result,
        "",
        markdown_table(
            hot_focus,
            ["candidate_id", "regime_variable", "regime_bin", "n_obs_ge31", "n_ge31_miss", "ge31_miss_rate_among_observed", "share_of_candidate_ge31_misses_in_regime_variable", "mean_residual_official_minus_pred_c"],
            limit=24,
        ),
        "",
        "## 8. Formula Improvement Versus M4/M7",
        "",
        result.best_formula_note,
        "",
        f"Decision: `{result.decision_status}`. The audit checks whether any formula materially reduces observed-ge31 residuals and moves the best-F1 threshold closer to 31 C without severe false alarms or large overall MAE degradation.",
        "",
        "## 9. Fixed_31 Crossing Review",
        "",
        result.fixed31_result,
        "",
        "A formula candidate is not promoted as canonical WBGT_A from this diagnostic, even when threshold behavior improves.",
        "",
        "## 10. Route Assessment",
        "",
        f"Formula route assessment: `{result.decision_status}`.",
        "",
        "Allowed interpretation: diagnostic evidence for formula/proxy review in retrospective System A L1H. Disallowed interpretation: validated local WBGT prediction, real-time heat risk forecast, or proof that v09 caused the high-tail compression.",
        "",
        "## 11. Next Recommended Action",
        "",
        result.next_recommended_action,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(path: Path, config_path: Path, result: AuditResult) -> None:
    """Write the lane status file."""
    outputs = "\n".join(f"- `{rel(output_path)}`" for output_path in result.output_paths)
    lines = [
        "# A-L1H.1 Status",
        "",
        f"Status: {result.acceptance_status}",
        f"Diagnostic decision: {result.decision_status}",
        f"Generated: {date.today().isoformat()}",
        f"Branch: {git_branch()}",
        "",
        "## Scope",
        "",
        "Formula-v2 / physical proxy diagnostic audit for System A L1H high-tail compression. No ML training, probability calibration, high-tail regression, A-L2, System B, SOLWEIG, raster, raw archive, or archive collector changes.",
        "",
        "## Command",
        "",
        f"- `python scripts/v11_l1h_run_formula_proxy_audit.py --config {rel(config_path)}`",
        "",
        "## Files Created / Modified",
        "",
        outputs,
        "",
        "## Key Results",
        "",
        f"- Best diagnostic formula candidate: {result.best_formula_candidate}",
        f"- Best formula note: {result.best_formula_note}",
        f"- Comparator reference: {result.comparator_reference}",
        f"- High-tail comparison: {result.high_tail_comparison}",
        f"- Fixed_31 result: {result.fixed31_result}",
        f"- Radiation-hot result: {result.radiation_hot_result}",
        f"- Next recommended action: {result.next_recommended_action}",
        "",
        "## Caveats",
        "",
        "- A-L1H.0c supports prioritising formula/proxy audit; it does not prove v09 caused compression.",
        "- Formula candidates are screening diagnostics and are not canonical WBGT_A replacements.",
        "- ge33 remains exploratory.",
        "",
        "## Safe To Commit",
        "",
        "- Config, scripts, docs, and compact diagnostic outputs from this lane after review.",
        "",
        "## Not Safe To Commit",
        "",
        "- Raw archives, rasters, SOLWEIG outputs, tif/tiff files, svfs.zip, patch zip packages, or large hourly forecast CSVs.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit(config_path: Path) -> AuditResult:
    """Run the A-L1H.1 formula/proxy audit and write outputs."""
    config = load_config(config_path)
    output_dir = resolve_path(str(config["outputs"]["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory = input_inventory(config)
    residual_weather, _residual_input, oof = read_inputs(config)
    missing_weather = validate_required_weather(residual_weather, config)

    base = unique_station_hours(residual_weather, config)
    base, v09_source, v09_found = attach_v09_proxy(base, oof, config)
    score_predictions, score_registry = make_score_predictions(residual_weather, config)
    formula_predictions, formula_registry = make_formula_predictions(base, config, v09_source, v09_found)
    registry = pd.DataFrame([*score_registry, *formula_registry, *package_registry_rows()])
    predictions = finalize_predictions(pd.concat([score_predictions, formula_predictions], ignore_index=True), config)

    overall = overall_metrics(predictions, config)
    thresholds = threshold_metrics(predictions, config)
    observed_bin = residual_by_observed_bin(predictions)
    radiation_regime = residual_by_radiation_regime(predictions)
    ge31_regime = ge31_miss_by_regime(radiation_regime)
    component = component_diagnostics(predictions)
    overall = add_regime_rates(overall, ge31_regime, config)

    inventory_path = output_dir / "formula_input_inventory.csv"
    registry_path = output_dir / "formula_candidate_registry.csv"
    predictions_path = output_dir / "formula_candidate_predictions.csv.gz"
    component_path = output_dir / "formula_component_diagnostics.csv"
    overall_path = output_dir / "formula_overall_metrics.csv"
    threshold_path = output_dir / "formula_threshold_metrics_31_33.csv"
    observed_bin_path = output_dir / "formula_residual_by_observed_bin.csv"
    radiation_regime_path = output_dir / "formula_residual_by_radiation_regime.csv"
    ge31_regime_path = output_dir / "formula_ge31_miss_by_regime.csv"
    report_path = output_dir / "formula_physics_audit_report.md"
    status_path = output_dir / "A_L1H_1_STATUS.md"

    inventory.to_csv(inventory_path, index=False)
    registry.to_csv(registry_path, index=False)
    predictions.to_csv(predictions_path, index=False, compression="gzip")
    component.to_csv(component_path, index=False)
    overall.to_csv(overall_path, index=False)
    thresholds.to_csv(threshold_path, index=False)
    observed_bin.to_csv(observed_bin_path, index=False)
    radiation_regime.to_csv(radiation_regime_path, index=False)
    ge31_regime.to_csv(ge31_regime_path, index=False)

    output_paths = [
        inventory_path,
        registry_path,
        predictions_path,
        component_path,
        overall_path,
        threshold_path,
        observed_bin_path,
        radiation_regime_path,
        ge31_regime_path,
        report_path,
        status_path,
    ]
    result = decide_result(overall, thresholds, ge31_regime, missing_weather, output_paths, config)
    write_report(report_path, inventory, registry, overall, thresholds, component, observed_bin, ge31_regime, result)
    write_status(status_path, config_path, result)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Run A-L1H.1 formula-v2 / physical proxy diagnostic audit."
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h_formula_proxy_audit.yaml")
    args = parser.parse_args()

    result = run_audit(resolve_path(args.config))
    print(f"[acceptance_status] {result.acceptance_status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[best_formula_candidate] {result.best_formula_candidate}")
    print(f"[comparator_reference] {result.comparator_reference}")
    print(f"[high_tail_comparison] {result.high_tail_comparison}")
    print(f"[fixed31_result] {result.fixed31_result}")
    print(f"[radiation_hot_result] {result.radiation_hot_result}")
    print(f"[next_recommended_action] {result.next_recommended_action}")
    return 0 if result.acceptance_status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
