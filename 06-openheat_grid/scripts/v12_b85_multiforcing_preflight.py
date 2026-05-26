"""Design the B8.5-F0 System B multi-forcing sensitivity preflight.

Inputs:
    configs/v12/systemb_b85_multiforcing_preflight.yaml
    B8.3 model-card gate artifacts.
    B6/B7 N24/N150 System B sample and label artifacts.
    Available System A / archive weather forcing tables declared in config.

Outputs:
    docs/v12/OpenHeat_SystemB_B8_5_multiforcing_preflight_CN.md
    outputs/v12_surrogate/b8_5_multiforcing_preflight/candidate_forcing_day_inventory.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/selected_forcing_days.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/n24_cell_set_for_multiforcing.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_expected_outputs_contract.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_stability_metrics_protocol.md
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_qgis_execution_readme.md
    outputs/v12_surrogate/b8_5_multiforcing_preflight/B8_5_F0_STATUS.md

Saved metrics:
    N24 provenance, selected forcing-day weather summaries, expected run count,
    planned scenario/hour/cell coverage, expected-output contract rows, and the
    post-SOLWEIG stability metric protocol.

This is preflight / protocol design only. It does not run QGIS or SOLWEIG,
does not create rasters, does not create AOI-wide predictions, does not compute
local WBGT, and does not create hazard_score, risk_score, or System A/B coupling
outputs.
"""

from __future__ import annotations

import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_multiforcing_preflight.yaml"
SINGAPORE_TZ = "Asia/Singapore"
BLOCKED = "BLOCKED"
PASS = "PASS"
FAILED = "FAILED"


@dataclass(frozen=True)
class B85PreflightResult:
    """Compact result returned by the B8.5-F0 preflight generator."""

    status: str
    n_cells: int
    selected_forcing_days: list[str]
    run_matrix_rows: int
    qgis_solweig_executed: str
    next_recommended_action: str
    files_created: list[Path]
    status_path: Path


def repo_path(value: str | Path) -> Path:
    """Resolve a config path relative to the OpenHeat project directory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_scalar(value: str) -> Any:
    """Parse a small YAML scalar when PyYAML is unavailable."""
    stripped = value.strip()
    if stripped in {"true", "True"}:
        return True
    if stripped in {"false", "False"}:
        return False
    if stripped in {"null", "None", "~"}:
        return None
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped.strip("\"'")


def read_simple_yaml(path: Path) -> dict[str, Any]:
    """Read the simple nested YAML shape used by this config."""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for idx, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Unsupported YAML list placement: {line}")
            parent.append(parse_scalar(text[2:].strip()))
            continue
        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = []
        for future in lines[idx + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Load the YAML config, preferring PyYAML when installed."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Config did not parse to a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def rel(path: Path) -> str:
    """Return a repository-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def now_stamp() -> str:
    """Return a compact local timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def command_output(args: list[str]) -> str:
    """Run a lightweight command for status reporting."""
    completed = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV-like table while preserving cell IDs as strings."""
    return pd.read_csv(path, dtype={"cell_id": "string"}, compression="infer")


def numeric(series: pd.Series) -> pd.Series:
    """Coerce a pandas Series to numeric values."""
    return pd.to_numeric(series, errors="coerce")


def safe_mean(series: pd.Series) -> float:
    """Return a numeric mean or NaN for empty inputs."""
    values = numeric(series).dropna()
    return float(values.mean()) if not values.empty else float("nan")


def safe_p90(series: pd.Series) -> float:
    """Return a numeric p90 or NaN for empty inputs."""
    values = numeric(series).dropna()
    return float(values.quantile(0.90)) if not values.empty else float("nan")


def fmt_number(value: Any, digits: int = 3) -> str:
    """Format a numeric value for Markdown, using NA for missing values."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "NA"
    if math.isnan(number):
        return "NA"
    return f"{number:.{digits}f}"


def clean_text(value: Any) -> str:
    """Return a compact string for CSV/Markdown cells."""
    if pd.isna(value):
        return ""
    return str(value).replace("\n", " ").strip()


def ensure_parent(path: Path) -> None:
    """Create a file parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_outputs(config: dict[str, Any]) -> None:
    """Create output directories declared by config."""
    for value in config["outputs"].values():
        path = repo_path(value)
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)


def aggregate_label_metrics(targets_path: Path) -> pd.DataFrame:
    """Aggregate existing N150 SOLWEIG-derived labels to cell-level diagnostics."""
    if not targets_path.exists():
        return pd.DataFrame(columns=["cell_id"])
    targets = read_csv(targets_path)
    if targets.empty or "cell_id" not in targets.columns:
        return pd.DataFrame(columns=["cell_id"])
    targets["cell_id"] = targets["cell_id"].astype(str)
    aggregations: dict[str, tuple[str, str]] = {
        "n_b7_label_rows": ("run_id", "count"),
        "n_scenarios": ("scenario", "nunique"),
        "n_hours": ("hour_sgt", "nunique"),
    }
    for column in ["delta_tmrt_p90_c", "m_rad_pct01", "tmrt_p90_c"]:
        if column in targets.columns:
            aggregations[f"mean_{column}"] = (column, "mean")
            aggregations[f"min_{column}"] = (column, "min")
            aggregations[f"max_{column}"] = (column, "max")
    out = targets.groupby("cell_id", as_index=False).agg(**aggregations)
    if "reuse_existing_n24_label" in targets.columns:
        reuse = (
            targets.assign(reuse_existing_n24_label=targets["reuse_existing_n24_label"].astype(str).str.lower())
            .groupby("cell_id")["reuse_existing_n24_label"]
            .apply(lambda values: "true" in set(values))
            .reset_index(name="has_reuse_existing_n24_label")
        )
        out = out.merge(reuse, on="cell_id", how="left")
    return out


def first_existing(config: dict[str, Any], keys: Iterable[str]) -> tuple[str, Path | None]:
    """Return the first existing configured path among several keys."""
    inputs = config["inputs"]
    for key in keys:
        path = repo_path(inputs[key])
        if path.exists():
            return key, path
    return "", None


def deterministic_fallback_n24(config: dict[str, Any], metrics: pd.DataFrame) -> pd.DataFrame:
    """Build a deterministic N24 fallback from N150 when original N24 provenance is unavailable."""
    selected_path = repo_path(config["inputs"]["n150_selected_cells"])
    if not selected_path.exists() or metrics.empty:
        return pd.DataFrame(columns=["cell_id"])

    n150 = read_csv(selected_path)
    n150["cell_id"] = n150["cell_id"].astype(str)
    pool = n150.merge(metrics, on="cell_id", how="left")
    for column in [
        "mean_delta_tmrt_p90_c",
        "max_delta_tmrt_p90_c",
        "mean_m_rad_pct01",
        "max_m_rad_pct01",
    ]:
        if column not in pool.columns:
            pool[column] = np.nan

    text_cols = [
        column
        for column in ["primary_sampling_stratum", "secondary_sampling_strata", "typology_label", "auto_qa_flag"]
        if column in pool.columns
    ]
    pool["_role_text"] = pool[text_cols].astype(str).agg("|".join, axis=1).str.lower() if text_cols else ""
    selected_rows: list[pd.Series] = []
    selected_cells: set[str] = set()

    role_rules = [
        ("hot_high_delta", "max_delta_tmrt_p90_c", False, ""),
        ("shaded_low_delta", "mean_delta_tmrt_p90_c", True, "shaded|canopy|low_svf"),
        ("overhead_confounded", "max_delta_tmrt_p90_c", False, "overhead|covered_walkway|transport"),
        ("high_svf_low_shade", "mean_delta_tmrt_p90_c", False, "open|high_svf"),
        ("low_svf_high_shade", "mean_delta_tmrt_p90_c", True, "low_svf|shaded|canopy"),
        ("high_water_near_water", "mean_delta_tmrt_p90_c", False, "water"),
        ("high_building_density", "mean_delta_tmrt_p90_c", False, "dense_built|street_canyon|building"),
        ("high_road_hardscape", "mean_delta_tmrt_p90_c", False, "road|hardscape|paved"),
    ]

    for role, sort_col, ascending, pattern in role_rules:
        candidates = pool.loc[~pool["cell_id"].isin(selected_cells)].copy()
        if pattern:
            candidates = candidates.loc[candidates["_role_text"].str.contains(pattern, regex=True, na=False)].copy()
        if candidates.empty:
            candidates = pool.loc[~pool["cell_id"].isin(selected_cells)].copy()
        candidates = candidates.sort_values([sort_col, "cell_id"], ascending=[ascending, True], na_position="last")
        for _, row in candidates.head(3).iterrows():
            if row["cell_id"] not in selected_cells and len(selected_rows) < int(config["design"]["expected_n_cells"]):
                row = row.copy()
                row["fallback_role"] = role
                selected_rows.append(row)
                selected_cells.add(str(row["cell_id"]))

    remaining = pool.loc[~pool["cell_id"].isin(selected_cells)].copy()
    remaining = remaining.sort_values(["mean_delta_tmrt_p90_c", "cell_id"], ascending=[False, True], na_position="last")
    for _, row in remaining.iterrows():
        if len(selected_rows) >= int(config["design"]["expected_n_cells"]):
            break
        row = row.copy()
        row["fallback_role"] = "deterministic_fill"
        selected_rows.append(row)
        selected_cells.add(str(row["cell_id"]))

    return pd.DataFrame(selected_rows)


def build_n24_cell_set(config: dict[str, Any]) -> tuple[pd.DataFrame, str, bool]:
    """Select the N24 cell set, preferring original retained N24 provenance."""
    metrics = aggregate_label_metrics(repo_path(config["inputs"]["n150_modifier_targets"]))
    source_key, source_path = first_existing(
        config,
        [
            "n150_retained_n24_cells",
            "n24_selected_cells_freeze",
            "n24_selected_cells",
        ],
    )

    fallback_used = False
    provenance_note = "original_retained_n24_cells"
    if source_path is not None:
        cells = read_csv(source_path)
        if "cell_id" not in cells.columns or cells["cell_id"].nunique() < int(config["design"]["expected_n_cells"]):
            fallback_used = True
            provenance_note = "configured_n24_file_insufficient_fallback_from_n150"
            cells = deterministic_fallback_n24(config, metrics)
    else:
        fallback_used = True
        provenance_note = "n24_provenance_unavailable_fallback_from_n150"
        cells = deterministic_fallback_n24(config, metrics)

    if cells.empty:
        out = pd.DataFrame(columns=["cell_id"])
        return out, provenance_note, fallback_used

    cells["cell_id"] = cells["cell_id"].astype(str)
    if "selection_rank" in cells.columns:
        cells["_selection_rank_sort"] = numeric(cells["selection_rank"])
        cells = cells.sort_values(["_selection_rank_sort", "cell_id"], na_position="last")
    else:
        cells = cells.sort_values("cell_id")
    cells = cells.drop_duplicates("cell_id").head(int(config["design"]["expected_n_cells"])).copy()
    cells.insert(0, "b85_cell_rank", range(1, len(cells) + 1))
    cells["n24_source_file"] = rel(source_path) if source_path is not None else "fallback_from_n150_modifier_targets"
    cells["n24_provenance_status"] = provenance_note
    cells["fallback_used"] = "yes" if fallback_used else "no"
    cells["b85_selection_note"] = np.where(
        fallback_used,
        "Deterministic fallback subset spanning target/typology roles; not the original retained N24.",
        "Original retained B6/B7 N24 continuity cell.",
    )
    out = cells.merge(metrics, on="cell_id", how="left")
    drop_cols = [column for column in ["_selection_rank_sort"] if column in out.columns]
    return out.drop(columns=drop_cols), provenance_note, fallback_used


def parse_sgt_datetime(series: pd.Series) -> pd.Series:
    """Parse Singapore-time strings, preserving local dates for offset-free timestamps."""
    text = series.astype(str).str.strip()
    offset_mask = text.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True, na=False)
    out = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    if offset_mask.any():
        parsed_offset = pd.to_datetime(text.loc[offset_mask], errors="coerce", utc=True)
        out.loc[offset_mask] = parsed_offset.dt.tz_convert(SINGAPORE_TZ).dt.tz_localize(None)
    if (~offset_mask).any():
        out.loc[~offset_mask] = pd.to_datetime(text.loc[~offset_mask], errors="coerce")
    return out


def time_column(df: pd.DataFrame) -> str | None:
    """Find the best available Singapore-time column in a weather table."""
    for column in [
        "valid_time_sgt_hour",
        "valid_time_sgt",
        "valid_time_sgt_dt",
        "time_sgt",
        "timestamp_sgt",
        "timestamp_sgt_dt",
    ]:
        if column in df.columns:
            return column
    return None


def add_weather_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized datetime/date/hour columns to a weather-like DataFrame."""
    out = df.copy()
    column = time_column(out)
    if column is None:
        out["_b85_time_sgt"] = pd.NaT
    else:
        out["_b85_time_sgt"] = parse_sgt_datetime(out[column])
    if "hour_sgt" in out.columns:
        hour_values = np.floor(numeric(out["hour_sgt"]))
        out["_b85_hour_sgt"] = hour_values.astype("Int64")
    else:
        out["_b85_hour_sgt"] = out["_b85_time_sgt"].dt.hour.astype("Int64")
    out["_b85_date"] = out["_b85_time_sgt"].dt.strftime("%Y-%m-%d")
    return out


def add_shortwave_3h(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 3-hour shortwave mean where the source does not already provide one."""
    out = df.copy()
    if "shortwave_radiation" not in out.columns:
        out["shortwave_3h_mean"] = np.nan
        return out
    out["_shortwave_numeric"] = numeric(out["shortwave_radiation"])
    station_col = "station_id" if "station_id" in out.columns else None
    sort_cols = [column for column in [station_col, "_b85_time_sgt"] if column]
    out = out.sort_values(sort_cols) if sort_cols else out
    if "shortwave_3h_mean" in out.columns:
        existing = numeric(out["shortwave_3h_mean"])
    else:
        existing = pd.Series(np.nan, index=out.index)
    if station_col:
        computed = out.groupby(station_col, dropna=False)["_shortwave_numeric"].transform(
            lambda values: values.rolling(3, min_periods=1).mean()
        )
    else:
        computed = out["_shortwave_numeric"].rolling(3, min_periods=1).mean()
    out["shortwave_3h_mean"] = existing.where(existing.notna(), computed)
    return out.drop(columns=["_shortwave_numeric"])


def source_status_row(source_name: str, path_text: str, status: str, notes: str) -> dict[str, Any]:
    """Build a non-candidate source inventory row."""
    return {
        "forcing_day_id": "",
        "date": "",
        "source_name": source_name,
        "source_file": path_text,
        "source_status": status,
        "selection_status": "not_selected",
        "regime_label": "",
        "rationale": notes,
        "n_station_hours": 0,
        "n_unique_stations": 0,
        "n_official_wbgt_obs": "",
        "n_ge31_obs": "",
        "mean_temperature_2m_c": "",
        "p90_temperature_2m_c": "",
        "mean_rh_pct": "",
        "p90_rh_pct": "",
        "mean_wind_speed_10m_ms": "",
        "p90_wind_speed_10m_ms": "",
        "mean_shortwave_wm2": "",
        "p90_shortwave_wm2": "",
        "mean_shortwave_3h_wm2": "",
        "p90_shortwave_3h_wm2": "",
        "mean_cloud_cover_pct": "",
        "p90_cloud_cover_pct": "",
        "mean_diffuse_radiation_wm2": "",
        "p90_diffuse_radiation_wm2": "",
        "cloud_diffuse_summary": "",
        "recommended_hours_available": "",
        "recommended_hours_missing": "",
        "missing_forcing_fraction": "",
        "source_priority": 99,
    }


def summarize_weather_source(
    source_name: str,
    path: Path,
    recommended_hours: list[int],
    source_priority: int,
) -> list[dict[str, Any]]:
    """Summarize candidate forcing days from one weather-like source file."""
    if not path.exists():
        return [source_status_row(source_name, rel(path), "missing_input", "Configured source is absent in this worktree.")]
    try:
        weather = read_csv(path)
    except Exception as exc:  # pragma: no cover - defensive inventory path
        return [source_status_row(source_name, rel(path), "read_failed", f"Could not read source: {exc}")]
    if weather.empty:
        return [source_status_row(source_name, rel(path), "empty_input", "Source exists but has no rows.")]

    weather = add_shortwave_3h(add_weather_time_columns(weather))
    if weather["_b85_time_sgt"].isna().all():
        return [source_status_row(source_name, rel(path), "no_parseable_time", "No parseable Singapore-time column found.")]

    weather = weather.loc[weather["_b85_hour_sgt"].isin(recommended_hours)].copy()
    if weather.empty:
        return [
            source_status_row(
                source_name,
                rel(path),
                "no_recommended_hour_rows",
                f"No rows at recommended hours {','.join(str(hour) for hour in recommended_hours)}.",
            )
        ]

    core_columns = [
        column
        for column in [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "shortwave_radiation",
            "shortwave_3h_mean",
        ]
        if column in weather.columns
    ]
    rows: list[dict[str, Any]] = []
    for date, group in weather.groupby("_b85_date", dropna=True):
        hours_available = sorted(int(hour) for hour in group["_b85_hour_sgt"].dropna().unique().tolist())
        missing_hours = [hour for hour in recommended_hours if hour not in set(hours_available)]
        n_station_hours = int(len(group))
        n_unique_stations = int(group["station_id"].nunique()) if "station_id" in group.columns else 0
        if core_columns:
            missing_values = int(group[core_columns].isna().sum().sum())
            missing_fraction = missing_values / float(len(group) * len(core_columns))
        else:
            missing_fraction = float("nan")
        cloud_mean = safe_mean(group["cloud_cover"]) if "cloud_cover" in group.columns else float("nan")
        diffuse_mean = safe_mean(group["diffuse_radiation"]) if "diffuse_radiation" in group.columns else float("nan")
        rows.append(
            {
                "forcing_day_id": "",
                "date": str(date),
                "source_name": source_name,
                "source_file": rel(path),
                "source_status": "candidate",
                "selection_status": "not_selected",
                "regime_label": "",
                "rationale": "",
                "n_station_hours": n_station_hours,
                "n_unique_stations": n_unique_stations,
                "n_official_wbgt_obs": "",
                "n_ge31_obs": "",
                "mean_temperature_2m_c": safe_mean(group["temperature_2m"]) if "temperature_2m" in group.columns else float("nan"),
                "p90_temperature_2m_c": safe_p90(group["temperature_2m"]) if "temperature_2m" in group.columns else float("nan"),
                "mean_rh_pct": safe_mean(group["relative_humidity_2m"]) if "relative_humidity_2m" in group.columns else float("nan"),
                "p90_rh_pct": safe_p90(group["relative_humidity_2m"]) if "relative_humidity_2m" in group.columns else float("nan"),
                "mean_wind_speed_10m_ms": safe_mean(group["wind_speed_10m"]) if "wind_speed_10m" in group.columns else float("nan"),
                "p90_wind_speed_10m_ms": safe_p90(group["wind_speed_10m"]) if "wind_speed_10m" in group.columns else float("nan"),
                "mean_shortwave_wm2": safe_mean(group["shortwave_radiation"]) if "shortwave_radiation" in group.columns else float("nan"),
                "p90_shortwave_wm2": safe_p90(group["shortwave_radiation"]) if "shortwave_radiation" in group.columns else float("nan"),
                "mean_shortwave_3h_wm2": safe_mean(group["shortwave_3h_mean"]) if "shortwave_3h_mean" in group.columns else float("nan"),
                "p90_shortwave_3h_wm2": safe_p90(group["shortwave_3h_mean"]) if "shortwave_3h_mean" in group.columns else float("nan"),
                "mean_cloud_cover_pct": cloud_mean,
                "p90_cloud_cover_pct": safe_p90(group["cloud_cover"]) if "cloud_cover" in group.columns else float("nan"),
                "mean_diffuse_radiation_wm2": diffuse_mean,
                "p90_diffuse_radiation_wm2": safe_p90(group["diffuse_radiation"]) if "diffuse_radiation" in group.columns else float("nan"),
                "cloud_diffuse_summary": f"mean_cloud={fmt_number(cloud_mean)}; mean_diffuse={fmt_number(diffuse_mean)}",
                "recommended_hours_available": ",".join(str(hour) for hour in hours_available),
                "recommended_hours_missing": ",".join(str(hour) for hour in missing_hours),
                "missing_forcing_fraction": missing_fraction,
                "source_priority": source_priority,
            }
        )
    return rows


def summarize_official_wbgt(path: Path, recommended_hours: list[int]) -> pd.DataFrame:
    """Summarize official WBGT and GE31 richness by date when available."""
    if not path.exists():
        return pd.DataFrame(columns=["date"])
    try:
        pairs = read_csv(path)
    except Exception:
        return pd.DataFrame(columns=["date"])
    if pairs.empty or "official_wbgt_c" not in pairs.columns:
        return pd.DataFrame(columns=["date"])
    pairs = add_weather_time_columns(pairs)
    pairs = pairs.loc[pairs["_b85_hour_sgt"].isin(recommended_hours)].copy()
    if pairs.empty:
        return pd.DataFrame(columns=["date"])
    pairs["_official_wbgt_c"] = numeric(pairs["official_wbgt_c"])
    pairs["_ge31"] = pairs["_official_wbgt_c"].ge(31.0)
    summary = (
        pairs.groupby("_b85_date", as_index=False)
        .agg(
            n_official_wbgt_obs=("_official_wbgt_c", "count"),
            n_ge31_obs=("_ge31", "sum"),
            mean_official_wbgt_c=("_official_wbgt_c", "mean"),
            p90_official_wbgt_c=("_official_wbgt_c", lambda values: float(values.dropna().quantile(0.90)) if not values.dropna().empty else np.nan),
        )
        .rename(columns={"_b85_date": "date"})
    )
    return summary


def classify_regimes(candidates: pd.DataFrame) -> pd.DataFrame:
    """Assign protocol-scale forcing regime labels from available weather summaries."""
    out = candidates.copy()
    out["regime_label"] = ""
    usable = out.loc[out["source_status"].eq("candidate")].copy()
    if usable.empty:
        return out
    shortwave_threshold = numeric(usable["mean_shortwave_3h_wm2"]).quantile(0.60)
    rh_threshold = numeric(usable["mean_rh_pct"]).quantile(0.60)
    wind_threshold = numeric(usable["mean_wind_speed_10m_ms"]).quantile(0.40)
    for idx, row in usable.iterrows():
        mean_sw3 = float(row["mean_shortwave_3h_wm2"]) if pd.notna(row["mean_shortwave_3h_wm2"]) else float("nan")
        mean_rh = float(row["mean_rh_pct"]) if pd.notna(row["mean_rh_pct"]) else float("nan")
        mean_wind = float(row["mean_wind_speed_10m_ms"]) if pd.notna(row["mean_wind_speed_10m_ms"]) else float("nan")
        if not math.isnan(mean_sw3) and mean_sw3 >= shortwave_threshold:
            label = "high_shortwave_hot"
        elif not math.isnan(mean_rh) and mean_rh >= rh_threshold:
            label = "humid_hot_cloudy_or_diffuse"
        elif not math.isnan(mean_wind) and mean_wind <= wind_threshold:
            label = "lowwind_hot_optional"
        else:
            label = "mixed_hot_forcing"
        out.loc[idx, "regime_label"] = label
    return out


def select_forcing_days(candidates: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Select 2-3 candidate forcing days or mark the gate blocked."""
    design = config["design"]
    min_days = int(design["min_forcing_days"])
    max_days = int(design["max_forcing_days"])
    recommended_hours = [int(hour) for hour in design["recommended_hours_sgt"]]
    usable = candidates.loc[candidates["source_status"].eq("candidate")].copy()
    if usable.empty:
        blocked = pd.DataFrame(
            [
                {
                    "forcing_day_id": BLOCKED,
                    "date": "",
                    "regime_label": BLOCKED,
                    "rationale": "No reliable forcing-day candidate source was available.",
                    "n_station_hours": 0,
                    "n_ge31_obs": "",
                    "mean_temperature_2m_c": "",
                    "p90_temperature_2m_c": "",
                    "mean_rh_pct": "",
                    "p90_rh_pct": "",
                    "mean_wind_speed_10m_ms": "",
                    "p90_wind_speed_10m_ms": "",
                    "mean_shortwave_wm2": "",
                    "p90_shortwave_wm2": "",
                    "mean_shortwave_3h_wm2": "",
                    "p90_shortwave_3h_wm2": "",
                    "cloud_diffuse_summary": "",
                    "recommended_hours": ",".join(str(hour) for hour in recommended_hours),
                    "source_file": "",
                }
            ]
        )
        return candidates, blocked, BLOCKED

    usable["missing_forcing_fraction"] = numeric(usable["missing_forcing_fraction"])
    usable["n_station_hours"] = numeric(usable["n_station_hours"])
    usable = usable.loc[
        usable["n_station_hours"].ge(int(design["min_station_hours_per_day"]))
        & usable["missing_forcing_fraction"].le(float(design["max_missing_forcing_fraction"]))
        & usable["recommended_hours_missing"].fillna("").eq("")
    ].copy()
    if usable.empty:
        blocked = pd.DataFrame(
            [
                {
                    "forcing_day_id": BLOCKED,
                    "date": "",
                    "regime_label": BLOCKED,
                    "rationale": "Candidate sources exist, but none met station-hour, missingness, and recommended-hour criteria.",
                    "n_station_hours": 0,
                    "n_ge31_obs": "",
                    "mean_temperature_2m_c": "",
                    "p90_temperature_2m_c": "",
                    "mean_rh_pct": "",
                    "p90_rh_pct": "",
                    "mean_wind_speed_10m_ms": "",
                    "p90_wind_speed_10m_ms": "",
                    "mean_shortwave_wm2": "",
                    "p90_shortwave_wm2": "",
                    "mean_shortwave_3h_wm2": "",
                    "p90_shortwave_3h_wm2": "",
                    "cloud_diffuse_summary": "",
                    "recommended_hours": ",".join(str(hour) for hour in recommended_hours),
                    "source_file": "",
                }
            ]
        )
        return candidates, blocked, BLOCKED

    selected_indices: list[int] = []
    high_sw = usable.sort_values(["mean_shortwave_3h_wm2", "mean_shortwave_wm2", "source_priority"], ascending=[False, False, True])
    if not high_sw.empty:
        selected_indices.append(int(high_sw.index[0]))
    remaining = usable.loc[~usable.index.isin(selected_indices)].copy()
    humid = remaining.sort_values(["mean_rh_pct", "mean_diffuse_radiation_wm2", "source_priority"], ascending=[False, False, True])
    if not humid.empty:
        selected_indices.append(int(humid.index[0]))
    remaining = usable.loc[~usable.index.isin(selected_indices)].copy()
    if len(selected_indices) < max_days and len(usable) >= max_days:
        lowwind = remaining.sort_values(["mean_wind_speed_10m_ms", "mean_temperature_2m_c", "source_priority"], ascending=[True, False, True])
        if not lowwind.empty:
            selected_indices.append(int(lowwind.index[0]))

    selected_indices = selected_indices[:max_days]
    selected = candidates.loc[selected_indices].copy()
    if len(selected) < min_days:
        status = BLOCKED
        selected["rationale"] = "Fewer than the minimum required forcing days were available."
    else:
        status = PASS

    selected = selected.reset_index(drop=True)
    forcing_ids: list[str] = []
    rationales: list[str] = []
    for idx, row in selected.iterrows():
        date_token = str(row["date"]).replace("-", "")
        if idx == 0:
            regime = "high_shortwave_hot"
            rationale = (
                "Selected as the highest available 3-hour shortwave forcing day "
                "with GE31-rich official-WBGT support in the available source."
            )
            selection_basis = (
                "ge31-rich high-shortwave/hot forcing day with official WBGT GE31 "
                "observations in the available v09 paired station file"
            )
        elif idx == 1:
            regime = "humid_hot_cloudy_or_diffuse"
            rationale = (
                "Selected to contrast FD01 with higher humidity and lower shortwave/3-hour "
                "shortwave under cloudy or diffuse conditions; not GE31-rich under available evidence."
            )
            selection_basis = (
                "contrast day for humidity/cloud/diffuse/radiation diversity; official GE31 "
                "observations are unavailable in the local paired station file and the day is not "
                "treated as GE31-rich"
            )
        else:
            regime = "lowwind_hot_optional"
            rationale = "Optional third regime selected for low-wind hot sensitivity if later execution budget allows."
            selection_basis = "optional low-wind contrast day if later execution budget allows"
        selected.loc[idx, "regime_label"] = regime
        selected.loc[idx, "selection_basis"] = selection_basis
        forcing_ids.append(f"FD{idx + 1:02d}_{regime}_{date_token}")
        rationales.append(rationale)
    selected["forcing_day_id"] = forcing_ids
    selected["rationale"] = rationales
    selected["selection_status"] = "selected"
    selected["recommended_hours"] = ",".join(str(hour) for hour in recommended_hours)
    selected["ge31_rich_status"] = np.where(
        numeric(selected.get("n_ge31_obs", pd.Series(index=selected.index))).gt(0),
        "ge31_rich",
        "not_ge31_rich_ge31_unavailable",
    )
    selected["n_official_wbgt_obs"] = selected.get("n_official_wbgt_obs", pd.Series(index=selected.index)).fillna(
        "not_available"
    )
    selected["n_ge31_obs"] = selected.get("n_ge31_obs", pd.Series(index=selected.index)).fillna("not_available")
    selected["temp_mean"] = selected["mean_temperature_2m_c"]
    selected["temp_p90"] = selected["p90_temperature_2m_c"]
    selected["rh_mean"] = selected["mean_rh_pct"]
    selected["rh_p90"] = selected["p90_rh_pct"]
    selected["wind_mean"] = selected["mean_wind_speed_10m_ms"]
    selected["wind_p90"] = selected["p90_wind_speed_10m_ms"]
    selected["shortwave_mean"] = selected["mean_shortwave_wm2"]
    selected["shortwave_p90"] = selected["p90_shortwave_wm2"]
    selected["shortwave_3h_mean"] = selected["mean_shortwave_3h_wm2"]
    selected["shortwave_3h_p90"] = selected["p90_shortwave_3h_wm2"]
    selected["cloud_cover_mean"] = selected["mean_cloud_cover_pct"]
    selected["cloud_cover_p90"] = selected["p90_cloud_cover_pct"]
    selected["diffuse_radiation_mean"] = selected["mean_diffuse_radiation_wm2"]
    selected["diffuse_radiation_p90"] = selected["p90_diffuse_radiation_wm2"]

    inventory = candidates.copy()
    inventory.loc[inventory.index.isin(selected_indices), "selection_status"] = "selected"
    inventory.loc[inventory.index.isin(selected_indices), "forcing_day_id"] = forcing_ids
    inventory.loc[inventory.index.isin(selected_indices), "selection_basis"] = selected["selection_basis"].tolist()
    inventory["ge31_rich_status"] = np.where(
        numeric(inventory.get("n_ge31_obs", pd.Series(index=inventory.index))).gt(0),
        "ge31_rich",
        np.where(inventory["source_status"].eq("candidate"), "not_ge31_rich_ge31_unavailable", "not_available"),
    )
    selected_cols = [
        "forcing_day_id",
        "date",
        "regime_label",
        "n_station_hours",
        "n_official_wbgt_obs",
        "n_ge31_obs",
        "ge31_rich_status",
        "temp_mean",
        "temp_p90",
        "rh_mean",
        "rh_p90",
        "wind_mean",
        "wind_p90",
        "shortwave_mean",
        "shortwave_p90",
        "shortwave_3h_mean",
        "shortwave_3h_p90",
        "cloud_cover_mean",
        "cloud_cover_p90",
        "diffuse_radiation_mean",
        "diffuse_radiation_p90",
        "selection_basis",
        "rationale",
        "recommended_hours",
        "source_file",
    ]
    return inventory, selected[selected_cols], status


def build_forcing_inventory(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Build candidate and selected forcing-day tables."""
    weather_sources = config["weather_sources"]
    recommended_hours = [int(hour) for hour in config["design"]["recommended_hours_sgt"]]
    rows: list[dict[str, Any]] = []
    source_order = [
        ("al1h_residual_weather_full_period", weather_sources["al1h_residual_weather_full_period"]),
        ("v09_historical_forecast_by_station_hourly", weather_sources["v09_historical_forecast_by_station_hourly"]),
    ]
    for source_priority, (source_name, path_text) in enumerate(source_order, start=1):
        rows.extend(summarize_weather_source(source_name, repo_path(path_text), recommended_hours, source_priority))

    live_glob = str(weather_sources["v11_live_chunks_glob"])
    live_paths = sorted(ROOT.glob(live_glob))
    if live_paths:
        for live_path in live_paths:
            rows.extend(summarize_weather_source("v11_live_chunk", live_path, recommended_hours, 3))
    else:
        rows.append(source_status_row("v11_live_chunk", live_glob, "missing_input", "No v11 live chunk files matched the configured glob."))

    ge31_path = repo_path(weather_sources["al1h_ge31_miss_by_weather_regime_full_period"])
    if not ge31_path.exists():
        rows.append(
            source_status_row(
                "al1h_ge31_miss_by_weather_regime_full_period",
                rel(ge31_path),
                "missing_input",
                "A-L1H GE31 miss-by-weather-regime file is absent in this B8 worktree.",
            )
        )

    candidates = pd.DataFrame(rows)
    official_summaries = [
        summarize_official_wbgt(repo_path(weather_sources["v09_wbgt_station_pairs"]), recommended_hours),
    ]
    for live_path in live_paths:
        official_summaries.append(summarize_official_wbgt(live_path, recommended_hours))
    official = pd.concat([frame for frame in official_summaries if not frame.empty], ignore_index=True) if official_summaries else pd.DataFrame(columns=["date"])
    if not official.empty:
        official = official.groupby("date", as_index=False).agg(
            n_official_wbgt_obs=("n_official_wbgt_obs", "sum"),
            n_ge31_obs=("n_ge31_obs", "sum"),
            mean_official_wbgt_c=("mean_official_wbgt_c", "mean"),
            p90_official_wbgt_c=("p90_official_wbgt_c", "max"),
        )
        candidates = candidates.drop(columns=[column for column in ["n_official_wbgt_obs", "n_ge31_obs"] if column in candidates.columns])
        candidates = candidates.merge(official, on="date", how="left")
    candidates["n_official_wbgt_obs"] = candidates.get(
        "n_official_wbgt_obs", pd.Series(index=candidates.index, dtype="float")
    ).fillna("not_available")
    candidates["n_ge31_obs"] = candidates.get("n_ge31_obs", pd.Series(index=candidates.index, dtype="float")).fillna(
        "not_available"
    )
    candidates = classify_regimes(candidates)
    candidates, selected, status = select_forcing_days(candidates, config)
    return candidates, selected, status


def build_run_matrix(cells: pd.DataFrame, selected_days: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build the planned SOLWEIG run matrix without executing SOLWEIG."""
    scenarios = [str(scenario) for scenario in config["design"]["scenarios"]]
    hours = [int(hour) for hour in config["design"]["recommended_hours_sgt"]]
    if cells.empty or selected_days.empty or BLOCKED in set(selected_days["forcing_day_id"].astype(str)):
        return pd.DataFrame(
            columns=[
                "run_id",
                "cell_id",
                "forcing_day_id",
                "date",
                "hour_sgt",
                "scenario",
                "expected_output_group",
                "status",
                "qgis_required",
                "solweig_execute_now",
                "notes",
            ]
        )
    rows: list[dict[str, Any]] = []
    for _, cell in cells.iterrows():
        cell_id = str(cell["cell_id"])
        for _, day in selected_days.iterrows():
            forcing_day_id = str(day["forcing_day_id"])
            for hour in hours:
                for scenario in scenarios:
                    scenario_token = "overhead" if scenario == "overhead_as_canopy" else scenario
                    run_id = f"b85_f0_{forcing_day_id}_{cell_id}_{scenario_token}_h{hour:02d}"
                    rows.append(
                        {
                            "run_id": run_id,
                            "cell_id": cell_id,
                            "forcing_day_id": forcing_day_id,
                            "date": str(day["date"]),
                            "hour_sgt": hour,
                            "scenario": scenario,
                            "expected_output_group": f"b85_f0/{forcing_day_id}/{cell_id}/{scenario_token}/h{hour:02d}",
                            "status": "planned",
                            "qgis_required": "yes",
                            "solweig_execute_now": "no",
                            "notes": "Protocol row only; execute later in QGIS/SOLWEIG outside B8.5-F0.",
                        }
                    )
    return pd.DataFrame(rows)


def build_expected_outputs_contract(config: dict[str, Any]) -> pd.DataFrame:
    """Create the future output contract for a later SOLWEIG execution lane."""
    out_dir = str(config["outputs"]["out_dir"])
    return pd.DataFrame(
        [
            {
                "contract_id": "run_matrix",
                "artifact_type": "preflight_manifest_csv",
                "expected_path_pattern": config["outputs"]["run_matrix"],
                "produced_in_f0": "yes",
                "qgis_required": "no",
                "solweig_required": "no",
                "required_keys": "run_id,cell_id,forcing_day_id,date,hour_sgt,scenario",
                "required_metrics": "planned row count and coverage only",
                "forbidden_claims": "No local WBGT, hazard_score, risk_score, or AOI-wide inference.",
                "notes": "Authoritative B8.5-F0 protocol matrix.",
            },
            {
                "contract_id": "future_solweig_tmrt_rasters",
                "artifact_type": "future_qgis_solweig_raster_outputs",
                "expected_path_pattern": "future controlled SOLWEIG work directory per expected_output_group/Tmrt_average.tif",
                "produced_in_f0": "no",
                "qgis_required": "yes",
                "solweig_required": "yes",
                "required_keys": "run_id,cell_id,forcing_day_id,hour_sgt,scenario",
                "required_metrics": "valid raster exists only after approved execution",
                "forbidden_claims": "Raster Tmrt must not be described as WBGT or risk.",
                "notes": "Path pattern is a future contract only; B8.5-F0 creates no raster files.",
            },
            {
                "contract_id": "future_focus_tmrt_summary",
                "artifact_type": "future_aggregation_csv",
                "expected_path_pattern": f"{out_dir}/future_b85_focus_tmrt_summary.csv",
                "produced_in_f0": "no",
                "qgis_required": "after_execution",
                "solweig_required": "after_execution",
                "required_keys": "run_id,cell_id,forcing_day_id,date,hour_sgt,scenario",
                "required_metrics": "tmrt_mean_c,tmrt_p50_c,tmrt_p75_c,tmrt_p90_c,tmrt_p95_c,tmrt_max_c,valid_pixel_count",
                "forbidden_claims": "No WBGT conversion and no hazard/risk score.",
                "notes": "Must be machine-readable and traceable to the run matrix.",
            },
            {
                "contract_id": "future_delta_targets",
                "artifact_type": "future_delta_modifier_csv",
                "expected_path_pattern": f"{out_dir}/future_b85_modifier_targets_by_forcing_day.csv",
                "produced_in_f0": "no",
                "qgis_required": "after_execution",
                "solweig_required": "after_execution",
                "required_keys": "cell_id,forcing_day_id,date,hour_sgt,scenario",
                "required_metrics": "delta_tmrt_p90_c,m_rad_pct01,reference_rule,n_reference_cells",
                "forbidden_claims": "Delta Tmrt is not delta WBGT and m_rad_pct01 is not risk.",
                "notes": "Use same-hour, same-scenario, same-forcing-day reference rules unless explicitly revised.",
            },
            {
                "contract_id": "future_stability_metrics",
                "artifact_type": "future_protocol_metrics_csv_md",
                "expected_path_pattern": f"{out_dir}/future_b85_multiforcing_stability_metrics.*",
                "produced_in_f0": "no",
                "qgis_required": "after_execution",
                "solweig_required": "after_execution",
                "required_keys": "metric_id,scenario,hour_sgt,forcing_day_pair,aggregation_level",
                "required_metrics": "rank_correlation,top_k_overlap,sign_stability,m_rad_pct01_rank_stability,cell_class_stability,unstable_cell_flags",
                "forbidden_claims": "Stability evidence is not validation of local WBGT prediction.",
                "notes": "Metrics defined in b85_f0_stability_metrics_protocol.md.",
            },
        ]
    )


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    """Render a compact Markdown table."""
    if df.empty:
        return "_None._"
    view = df[columns].head(max_rows).copy()
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(clean_text(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def write_stability_protocol(path: Path, config: dict[str, Any], selected: pd.DataFrame) -> None:
    """Write the post-SOLWEIG stability metric protocol."""
    recommended_hours = ",".join(str(hour) for hour in config["design"]["recommended_hours_sgt"])
    selected_summary = (
        markdown_table(
            selected,
            ["forcing_day_id", "date", "regime_label", "n_station_hours", "n_ge31_obs", "selection_basis"],
        )
        if not selected.empty
        else "_No selected forcing days._"
    )
    text = f"""# B8.5-F0 Stability Metrics Protocol

Generated: {now_stamp()}

## Scope

This is a post-SOLWEIG analysis protocol for the later B8.5 execution lane. B8.5-F0 did not execute QGIS or SOLWEIG, did not create rasters, did not create local WBGT, and did not create `hazard_score`, `risk_score`, System A/B coupling, or AOI-wide inference outputs.

## Planned Forcing Days

{selected_summary}

FD01 is the GE31-rich high-shortwave/hot forcing day. FD02 is a contrast day for humidity/cloud/diffuse/radiation diversity; it is not treated as GE31-rich when GE31 observations are unavailable in the local paired station file.

Recommended hours: `{recommended_hours}` SGT. Scenarios: `base`, `overhead_as_canopy`.

## Required Post-Execution Inputs

- Completed run matrix with one row per `cell_id x forcing_day_id x hour_sgt x scenario`.
- Aggregated Tmrt summaries keyed by `run_id`, `cell_id`, `forcing_day_id`, `date`, `hour_sgt`, and `scenario`.
- Per-forcing-day `delta_tmrt_p90_c` and `m_rad_pct01` computed within the same forcing day, hour, and scenario reference domain.

## Metrics

1. Rank correlation of `delta_tmrt_p90_c` across forcing days: compute Spearman correlations for each forcing-day pair at cell level, with all hours/scenarios pooled only as a diagnostic view.
2. Spearman by hour/scenario: compute pairwise Spearman separately for every `hour_sgt x scenario` slice to detect timing-specific instability.
3. Top-k overlap: compare top 10%, top 20%, and top 5 cells by `delta_tmrt_p90_c` across forcing days; report Jaccard overlap and shared-cell counts.
4. Sign stability: flag cells where `delta_tmrt_p90_c` changes sign across forcing days for the same hour/scenario.
5. `m_rad_pct01` rank stability: compute Spearman and absolute percentile-rank drift for `m_rad_pct01`; summarize median, p90, and max drift.
6. Cell class stability: assign within-day classes such as high, middle, and low radiative modifier; report class transition matrices across forcing days.
7. Unstable-cell inventory: list cells with high rank drift, class flips, sign flips, or repeated top-k disagreement, including their N24 provenance and typology notes.
8. Forcing-day interaction notes: describe whether instability concentrates in a scenario, hour, or typology. Keep this descriptive; do not infer causal real-world heat-risk drivers.

## Suggested Review Thresholds

- Treat low rank correlation, low top-k overlap, or many sign/class flips as a blocker for B9 AOI-wide inference.
- Do not promote System B beyond internal SOLWEIG-derived modifier ranking unless multi-forcing stability is accepted by review.
- Keep `delta_tmrt_p90_c` as a radiative modifier label; do not convert it to local WBGT.
"""
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def write_qgis_readme(path: Path, config: dict[str, Any], run_matrix: pd.DataFrame) -> None:
    """Write a protocol-only QGIS execution README for the later execution lane."""
    text = f"""# B8.5-F0 QGIS Execution README

Generated: {now_stamp()}

## Status

B8.5-F0 is preflight only. QGIS was not run. SOLWEIG was not run. No raster files were created.

## Manifest

- Planned run matrix: `{config["outputs"]["run_matrix"]}`
- Planned rows: `{len(run_matrix)}`
- Cells: `24`, from `original_retained_n24_cells`
- Forcing days: `FD01_high_shortwave_hot_20260507`, `FD02_humid_hot_cloudy_or_diffuse_20260508`
- Scenarios: `base`, `overhead_as_canopy`
- Hours: `{",".join(str(hour) for hour in config["design"]["recommended_hours_sgt"])}`

## Forcing-Day Interpretation

FD01 is the GE31-rich high-shortwave/hot forcing day. FD02 is a contrast day for humidity/cloud/diffuse/radiation diversity; GE31 observations are unavailable in the local paired station file for FD02, so it is not treated as GE31-rich.

## Later Execution Rules

1. Use `b85_f0_solweig_run_matrix.csv` as the controlling manifest.
2. Execute only the listed N24 cells, selected forcing days, five hours, and two scenarios.
3. Keep outputs grouped by `expected_output_group` so aggregation can trace every result back to one manifest row.
4. Do not expand this preflight into AOI-wide prediction.
5. Do not create local WBGT, hazard_score, risk_score, or System A/B coupling outputs.
6. Do not interpret SOLWEIG Tmrt as WBGT.

## Expected Completion Evidence

- A later run log with one status per `run_id`.
- Aggregated Tmrt summary CSV keyed by `run_id`.
- Delta / modifier target CSV computed within the forcing-day reference domain.
- Stability metrics CSV and Markdown report following `b85_f0_stability_metrics_protocol.md`.

This README is intentionally not an execution command. It is a handoff contract for a future approved QGIS/SOLWEIG lane.
"""
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def write_cn_doc(path: Path, result_status: str, n_cells: int, selected: pd.DataFrame, run_rows: int, fallback_used: bool) -> None:
    """Write the Chinese B8.5-F0 protocol note."""
    selected_table = markdown_table(
        selected,
        ["forcing_day_id", "date", "regime_label", "n_station_hours", "n_ge31_obs", "selection_basis"],
    )
    fallback_text = "是，使用确定性 N150 回退子集。" if fallback_used else "否，使用 B6/B7 保留 N24 连续性样本。"
    text = f"""# OpenHeat System B B8.5-F0 多强迫预检说明

生成时间：{now_stamp()}

## 结论

- 状态：`{result_status}`
- N24 cell 数量：`{n_cells}`
- N24 来源：`original_retained_n24_cells`
- 计划 SOLWEIG run matrix 行数：`{run_rows}`
- QGIS / SOLWEIG 是否执行：`no`
- N24 是否回退选择：{fallback_text}

## 边界

本文件只用于 B8.5-F0 预检、协议和 manifest 说明。此阶段没有运行 QGIS，没有运行 SOLWEIG，没有创建 raster，没有创建 AOI 全域推理，没有创建局地 WBGT，没有创建 `hazard_score` 或 `risk_score`，也没有创建 System A/B coupling 输出。

System B 当前仍是 SOLWEIG 派生局地辐射修饰标签的候选 surrogate/emulator 工作流。`delta_tmrt_p90_c` 不是 delta WBGT，`m_rad_pct01` 不是风险，B8.5-F0 不批准 B9 AOI-wide inference。

## 科学目的

B8.2/B8.3 显示 `extra_trees` 可作为 N150 单一 forcing setup 下的内部候选模型，但多 forcing 稳定性尚未测试。B8.5-F0 的目标是在 B9 全域推理前，设计一个小规模敏感性运行协议：

- N24 cells
- 2 个 forcing days
- 5 个小时：10、12、13、15、16 SGT
- 2 个场景：`base`、`overhead_as_canopy`
- 共 `{n_cells} x 2 x 5 x 2 = {run_rows}` 个计划 run

## 已选 forcing days

{selected_table}

FD01 是 GE31-rich 的高短波、高热 forcing day。FD02 的作用不是提供第二个 GE31-rich 事件，而是作为湿度、云量、散射辐射和短波辐射结构不同的对照日。

## 后续评估

后续执行完成后，应比较不同 forcing day 下 `delta_tmrt_p90_c` 与 `m_rad_pct01` 的排序稳定性、top-k overlap、符号稳定性、cell class 稳定性以及不稳定 cell 清单。若这些证据不稳定，B9 AOI-wide inference 应继续阻塞。
"""
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")
    return
    selected_table = markdown_table(
        selected,
        ["forcing_day_id", "date", "regime_label", "n_station_hours", "n_ge31_obs", "source_file"],
    )
    fallback_text = "是，使用了确定性 N150 回退子集。" if fallback_used else "否，使用 B6/B7 保留 N24 连续性样本。"
    text = f"""# OpenHeat System B B8.5 多强迫预检说明

生成时间：{now_stamp()}

## 结论

- 状态：`{result_status}`
- N24 cell 数量：`{n_cells}`
- 计划 SOLWEIG run matrix 行数：`{run_rows}`
- N24 是否回退选择：{fallback_text}

## 边界

本文件只定义 B8.5-F0 预检 / 协议 / manifest。没有运行 QGIS，没有运行 SOLWEIG，没有创建 raster，没有创建 AOI 全域推理，没有创建局地 WBGT，没有创建 hazard_score / risk_score，也没有创建 System A/B coupling 输出。

System B 当前只能表述为 SOLWEIG 派生局地辐射修饰标签的候选 surrogate/emulator 证据。`delta_tmrt_p90_c` 不是 delta WBGT，`m_rad_pct01` 不是风险。

## 科学目的

B8.2/B8.3 显示 `extra_trees` 可作为 N150 单一 forcing setup 下的内部候选模型，但多 forcing 稳定性尚未测试。B8.5-F0 的目标是在 B9 全域推理前，设计一个小规模 N24 x 2-3 forcing days x 5 hours x 2 scenarios 的敏感性运行协议。

## 已选 forcing days

{selected_table}

## 后续评估

后续执行完成后，应比较不同 forcing day 下 `delta_tmrt_p90_c` 与 `m_rad_pct01` 的排序稳定性、top-k overlap、符号稳定性、cell class 稳定性以及不稳定 cell 清单。若这些证据不稳定，B9 AOI-wide inference 应继续阻塞。
"""
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def write_status(
    path: Path,
    config: dict[str, Any],
    status: str,
    n_cells: int,
    selected: pd.DataFrame,
    run_matrix: pd.DataFrame,
    files_created: list[Path],
    commands: list[str],
    fallback_used: bool,
    provenance_note: str,
) -> None:
    """Write the B8.5-F0 lane status report."""
    selected_days_text = ", ".join(selected["forcing_day_id"].astype(str).tolist()) if not selected.empty else "none"
    branch = command_output(["git", "branch", "--show-current"])
    status_short = command_output(["git", "status", "--short", "--", "."])
    commands_text = "\n".join(f"- `{command}`" for command in commands) if commands else "- Not recorded."
    files_text = "\n".join(f"- `{rel(path)}`" for path in files_created)
    text = f"""# B8.5-F0 Status

Generated: {now_stamp()}

## Status

{status}

## Branch

`{branch}`

## Scope

Preflight / protocol / manifest design only for System B multi-forcing sensitivity. No QGIS, no SOLWEIG, no rasters, no AOI-wide inference, no local WBGT, no hazard_score, no risk_score, and no System A/B coupling output.

## Commands Run

{commands_text}

## Key Results

- N24 cells: `{n_cells}`
- N24 provenance: `{provenance_note}`
- N24 fallback used: `{"yes" if fallback_used else "no"}`
- Selected forcing days: `{selected_days_text}`
- FD01 interpretation: GE31-rich high-shortwave/hot forcing day.
- FD02 interpretation: contrast day for humidity/cloud/diffuse/radiation diversity; official GE31 observations are unavailable in the local paired station file and the day is not treated as GE31-rich.
- Run matrix rows: `{len(run_matrix)}`
- QGIS/SOLWEIG executed: `no`

## Caveats

- A-L1H weather-regime outputs were not present in this B8 worktree if marked missing in the candidate inventory.
- Available forcing-day selection relies on configured System A/archive weather sources, especially v09 hourly forecast rows when A-L1H files are absent.
- This does not validate local WBGT prediction and does not approve B9 AOI-wide inference.

## Files Created / Modified

{files_text}

## Safe To Commit

Protocol scripts, config, docs, and compact CSV/Markdown outputs listed above after human review.

## Not Safe To Commit

Any rasters, `data/solweig/`, `data/rasters/`, raw archive dumps, large forecast CSVs, or generated SOLWEIG execution products outside this compact preflight output set.

## Current Git Status Short

```text
{status_short}
```

## Next Recommended Action

Review the B8.5-F0 manifest and selected forcing days. If accepted, run the future QGIS/SOLWEIG execution lane against this manifest, then compute the stability metrics before any B9 AOI-wide inference decision.
"""
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def write_outputs(
    config: dict[str, Any],
    n24: pd.DataFrame,
    candidates: pd.DataFrame,
    selected: pd.DataFrame,
    run_matrix: pd.DataFrame,
    contract: pd.DataFrame,
    status: str,
    fallback_used: bool,
    provenance_note: str,
    commands: list[str],
) -> list[Path]:
    """Write all configured B8.5-F0 artifacts."""
    output_paths = {key: repo_path(value) for key, value in config["outputs"].items()}
    files = [
        output_paths["n24_cell_set"],
        output_paths["candidate_forcing_day_inventory"],
        output_paths["selected_forcing_days"],
        output_paths["run_matrix"],
        output_paths["expected_outputs_contract"],
        output_paths["stability_metrics_protocol"],
        output_paths["qgis_execution_readme"],
        output_paths["canonical_note"],
        output_paths["status"],
    ]
    for path in files:
        ensure_parent(path)
    n24.to_csv(output_paths["n24_cell_set"], index=False)
    candidates.to_csv(output_paths["candidate_forcing_day_inventory"], index=False)
    selected.to_csv(output_paths["selected_forcing_days"], index=False)
    run_matrix.to_csv(output_paths["run_matrix"], index=False)
    contract.to_csv(output_paths["expected_outputs_contract"], index=False)
    write_stability_protocol(output_paths["stability_metrics_protocol"], config, selected)
    write_qgis_readme(output_paths["qgis_execution_readme"], config, run_matrix)
    write_cn_doc(output_paths["canonical_note"], status, len(n24), selected, len(run_matrix), fallback_used)
    write_status(
        output_paths["status"],
        config,
        status,
        len(n24),
        selected,
        run_matrix,
        files,
        commands,
        fallback_used,
        provenance_note,
    )
    return files


def run(config_path: Path = DEFAULT_CONFIG, commands: list[str] | None = None) -> B85PreflightResult:
    """Run the B8.5-F0 preflight generator."""
    config = read_config(config_path)
    ensure_outputs(config)
    n24, provenance_note, fallback_used = build_n24_cell_set(config)
    candidates, selected, forcing_status = build_forcing_inventory(config)
    run_matrix = build_run_matrix(n24, selected, config)
    contract = build_expected_outputs_contract(config)

    expected_n_cells = int(config["design"]["expected_n_cells"])
    expected_rows = len(n24) * max(0, len(selected.loc[~selected["forcing_day_id"].astype(str).eq(BLOCKED)])) * len(config["design"]["recommended_hours_sgt"]) * len(config["design"]["scenarios"])
    if len(n24) != expected_n_cells:
        status = FAILED if forcing_status == PASS else BLOCKED
    elif forcing_status == BLOCKED:
        status = BLOCKED
    elif len(run_matrix) != expected_rows:
        status = FAILED
    else:
        status = PASS

    files_created = write_outputs(
        config,
        n24,
        candidates,
        selected,
        run_matrix,
        contract,
        status,
        fallback_used,
        provenance_note,
        commands or [],
    )
    selected_ids = [] if selected.empty else selected["forcing_day_id"].astype(str).tolist()
    next_action = (
        "Review and approve the B8.5-F0 manifest, then execute the future QGIS/SOLWEIG lane and compute stability metrics."
        if status == PASS
        else "Resolve the blocked forcing-day source or N24 provenance issue before execution."
    )
    return B85PreflightResult(
        status=status,
        n_cells=len(n24),
        selected_forcing_days=selected_ids,
        run_matrix_rows=len(run_matrix),
        qgis_solweig_executed="no",
        next_recommended_action=next_action,
        files_created=files_created,
        status_path=repo_path(config["outputs"]["status"]),
    )


if __name__ == "__main__":
    result = run()
    print(f"Status: {result.status}")
    print(f"N cells: {result.n_cells}")
    print(f"Selected forcing days: {', '.join(result.selected_forcing_days)}")
    print(f"Run matrix rows: {result.run_matrix_rows}")
    print(f"QGIS/SOLWEIG executed: {result.qgis_solweig_executed}")
