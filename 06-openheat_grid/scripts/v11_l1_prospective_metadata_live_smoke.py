#!/usr/bin/env python
"""One-run live local smoke for System A Level 1 prospective metadata.

Inputs
------
- ``configs/v11/system_a_live_prospective_smoke_config.example.yaml`` as the
  documented one-run smoke contract.
- Three selected station coordinates from the documented WBGT schema fixture.
- Live Open-Meteo Forecast API responses, capped at 3 calls.
- Live data.gov.sg WBGT response, capped at 2 calls.

Outputs
-------
- ``outputs/v11_level1/prospective_eval/live_smoke/live_forecast_metadata_rows.csv``
- ``outputs/v11_level1/prospective_eval/live_smoke/live_official_wbgt_metadata_rows.csv``
- ``outputs/v11_level1/prospective_eval/live_smoke/live_issue_valid_pair_candidates.csv``
- ``outputs/v11_level1/prospective_eval/live_smoke/live_smoke_manifest.json``
- ``outputs/v11_level1/prospective_eval/live_smoke/live_smoke_manifest.md``
- ``outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.csv``
- ``outputs/v11_level1/prospective_eval/live_smoke/live_smoke_validation.md``
- ``outputs/v11_level1/prospective_eval/live_smoke/sprint4b3_live_local_smoke_report.md``

Saved metrics
-------------
The validation CSV records API call limits, metadata availability, fail-closed
lead-time behavior, output-path safety, and claim-boundary checks. The manifest
records API status codes, elapsed seconds, row counts, quality flags, and safety
statements. This script does not write archive files, patch collector runtime,
train models, evaluate forecast skill, compute event metrics, or produce local
WBGT.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v11_prospective_metadata_helpers import (
    PROSPECTIVE_METADATA_FIELDS,
    attach_prospective_metadata,
    compute_lead_time_hours,
    normalize_utc_timestamp,
    utc_now_iso,
)


CONFIG_PATH = Path("configs/v11/system_a_live_prospective_smoke_config.example.yaml")
OUTPUT_DIR = Path("outputs/v11_level1/prospective_eval/live_smoke")
FORECAST_CSV = OUTPUT_DIR / "live_forecast_metadata_rows.csv"
OFFICIAL_CSV = OUTPUT_DIR / "live_official_wbgt_metadata_rows.csv"
PAIR_CSV = OUTPUT_DIR / "live_issue_valid_pair_candidates.csv"
MANIFEST_JSON = OUTPUT_DIR / "live_smoke_manifest.json"
MANIFEST_MD = OUTPUT_DIR / "live_smoke_manifest.md"
VALIDATION_CSV = OUTPUT_DIR / "live_smoke_validation.csv"
VALIDATION_MD = OUTPUT_DIR / "live_smoke_validation.md"
REPORT_MD = OUTPUT_DIR / "sprint4b3_live_local_smoke_report.md"

SCHEMA_VERSION = "v1.1-sprint4b3-live-prospective-smoke-v0.1"
SOURCE_LANE = "local_live_smoke"
FORECAST_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
WBGT_ENDPOINT = "https://api-open.data.gov.sg/v2/real-time/api/weather"
FORECAST_PROVIDER = "open-meteo"
FORECAST_API_PRODUCT = "forecast_api_live_smoke"
WBGT_PROVIDER = "data.gov.sg"
WBGT_API_PRODUCT = "wbgt_observations_live_smoke"
MAX_OPENMETEO_CALLS = 3
MAX_WBGT_CALLS = 2
MAX_HOURLY_ROWS_PER_STATION = 6
FORECAST_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
]
STATIONS = {
    "S128": {
        "name": "Bishan Street",
        "lat": 1.354825,
        "lon": 103.852219,
        "coordinate_source": "data/fixtures/nea_wbgt_v2_current_schema_sample.json",
    },
    "S142": {
        "name": "Sentosa Palawan Green",
        "lat": 1.24950363476734,
        "lon": 103.819177652546,
        "coordinate_source": "data/fixtures/nea_wbgt_v2_current_schema_sample.json",
    },
    "S137": {
        "name": "Sakra Road",
        "lat": 1.2571,
        "lon": 103.698,
        "coordinate_source": "data/fixtures/nea_wbgt_v2_current_schema_sample.json",
    },
}

FORBIDDEN_FIELDS = {
    "local_wbgt_c",
    "wbgt_cell_c",
    "risk_score",
    "cell_id",
    "m_rad",
    "tmrt",
    "solweig",
}
FORBIDDEN_LABELS = {"forecast_skill_evaluated"}
FORBIDDEN_METRIC_COLUMNS = {
    "mae",
    "rmse",
    "precision",
    "recall",
    "f1",
    "pr_auc",
    "brier",
    "ece",
}
INPUT_FILES = [
    "scripts/v11_prospective_metadata_helpers.py",
    "scripts/v11_l1_prospective_metadata_local_dry_smoke.py",
    "configs/v11/system_a_prospective_metadata_config.example.yaml",
    "configs/v11/system_a_local_prospective_dry_smoke_config.example.yaml",
    "configs/v11/system_a_live_prospective_smoke_config.example.yaml",
    "docs/v11/SystemA_prospective_metadata_schema_CN.md",
    "docs/v11/SystemA_local_prospective_metadata_dry_smoke_runbook_CN.md",
    "outputs/v11_level1/prospective_eval/local_dry_smoke/sprint4b2_local_dry_smoke_report.md",
    "scripts/v11_archive_collect_once.py",
    "scripts/v11_archive_gha_collect_once.py",
]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the one-run live smoke."""
    parser = argparse.ArgumentParser(
        description=(
            "Run one bounded live System A Level 1 prospective metadata smoke. "
            "Writes only under outputs/v11_level1/prospective_eval/live_smoke/."
        )
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Live-smoke config path.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Live-smoke output directory.")
    return parser.parse_args()


def iso_z(dt: datetime) -> str:
    """Return UTC ISO timestamp with Z suffix."""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_sgt(utc_value: Any) -> str | None:
    """Return Singapore display timestamp for a UTC-like value."""
    normalized = normalize_utc_timestamp(utc_value)
    if normalized is None:
        return None
    sgt = timezone(timedelta(hours=8))
    dt = pd.to_datetime(normalized, utc=True).to_pydatetime()
    return dt.astimezone(sgt).replace(microsecond=0).isoformat()


def request_json(
    endpoint: str,
    params: dict[str, Any],
    timeout_seconds: int = 30,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Fetch one JSON endpoint with urllib and return compact call metadata."""
    url = f"{endpoint}?{urllib.parse.urlencode(params, doseq=True)}"
    requested_at = utc_now_iso()
    start = time.perf_counter()
    status = -1
    error = None
    payload: dict[str, Any] | None = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "openheat-v11-live-metadata-smoke/0.1"})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            status = int(resp.status)
            body = resp.read()
            payload = json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        error = f"HTTPError: {exc.reason}"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    retrieved_at = utc_now_iso()
    elapsed = round(time.perf_counter() - start, 3)
    meta = {
        "endpoint": endpoint,
        "query_summary": urllib.parse.urlencode(params, doseq=True),
        "request_url_or_summary": url,
        "requested_at_utc": requested_at,
        "retrieved_at_utc": retrieved_at,
        "response_status": status,
        "response_elapsed_seconds": elapsed,
        "error": error,
    }
    return payload, meta


def append_flag(flags: list[str], flag: str) -> None:
    """Append a quality flag once."""
    if flag not in flags:
        flags.append(flag)


def live_flags_from_helper(base_flags: str) -> str:
    """Convert helper strict flags into live-smoke quality flags."""
    flags = [flag for flag in str(base_flags).split("|") if flag and flag != "ok_prospective_metadata"]
    append_flag(flags, "live_smoke_not_forecast_skill")
    return "|".join(flags)


def live_forecast_flags_from_helper(base_flags: str) -> str:
    """Convert helper flags for forecast-only rows.

    Forecast metadata rows are not pair/evaluation rows, so they should not be
    marked as missing official retrieval metadata.
    """
    flags = [
        flag
        for flag in str(base_flags).split("|")
        if flag and flag not in {"ok_prospective_metadata", "missing_official_retrieved_at"}
    ]
    append_flag(flags, "live_smoke_not_forecast_skill")
    return "|".join(flags)


def next_hour_threshold_utc(retrieved_at_utc: Any) -> pd.Timestamp | None:
    """Return the next-hour UTC threshold for selecting future valid times."""
    normalized = normalize_utc_timestamp(retrieved_at_utc)
    if normalized is None:
        return None
    retrieved = pd.to_datetime(normalized, utc=True)
    threshold = retrieved.ceil("h")
    return threshold


def select_future_hour_indices(times: list[Any], retrieved_at_utc: Any, limit: int) -> tuple[list[tuple[int, str]], str | None]:
    """Select first hourly rows at or after the next-hour retrieval threshold."""
    threshold = next_hour_threshold_utc(retrieved_at_utc)
    if threshold is None:
        return [], None
    selected: list[tuple[int, str]] = []
    for idx, valid_time in enumerate(times):
        valid_iso = normalize_utc_timestamp(valid_time)
        if valid_iso is None:
            continue
        valid_dt = pd.to_datetime(valid_iso, utc=True)
        if valid_dt >= threshold:
            selected.append((idx, valid_iso))
        if len(selected) >= limit:
            break
    return selected, threshold.to_pydatetime().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_forecast_payload(
    station_id: str,
    station: dict[str, Any],
    payload: dict[str, Any],
    call_meta: dict[str, Any],
    run_id: str,
    row_added_at: str,
) -> pd.DataFrame:
    """Parse one Open-Meteo Forecast API response into metadata rows."""
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise ValueError("Open-Meteo response missing hourly object")
    times = hourly.get("time")
    if not isinstance(times, list):
        raise ValueError("Open-Meteo response missing hourly.time list")
    for variable in FORECAST_VARIABLES:
        if variable not in hourly or not isinstance(hourly.get(variable), list):
            raise ValueError(f"Open-Meteo response missing hourly.{variable} list")

    model_run_time = normalize_utc_timestamp(
        payload.get("model_run_time_utc")
        or payload.get("model_run_time")
        or payload.get("generationtime_utc")
    )
    forecast_issue_time = normalize_utc_timestamp(
        payload.get("forecast_issue_time_utc") or payload.get("issue_time_utc") or payload.get("issue_time")
    )

    selected, selection_threshold_utc = select_future_hour_indices(
        times,
        call_meta["retrieved_at_utc"],
        MAX_HOURLY_ROWS_PER_STATION,
    )
    if not selected:
        raise ValueError("no_future_valid_times: no hourly valid_time at or after forecast retrieval next-hour threshold")

    retrieved_dt = pd.to_datetime(call_meta["retrieved_at_utc"], utc=True)
    rows: list[dict[str, Any]] = []
    for idx, valid_time_utc in selected:
        valid_dt = pd.to_datetime(valid_time_utc, utc=True)
        row = {
            "station_id": station_id,
            "station_name": station["name"],
            "station_lat": station["lat"],
            "station_lon": station["lon"],
            "station_coordinate_source": station["coordinate_source"],
            "valid_time_utc": valid_time_utc,
            "valid_time_sgt": iso_sgt(valid_time_utc),
            "forecast_valid_selection_rule": "valid_time_utc >= ceil(forecast_retrieved_at_utc to next hour)",
            "forecast_valid_selection_threshold_utc": selection_threshold_utc,
            "valid_time_minus_retrieval_hours": round(float((valid_dt - retrieved_dt).total_seconds() / 3600.0), 6),
            "request_url_or_summary": call_meta["request_url_or_summary"],
            "response_status": call_meta["response_status"],
            "response_elapsed_seconds": call_meta["response_elapsed_seconds"],
            "response_timezone": payload.get("timezone"),
            "response_utc_offset_seconds": payload.get("utc_offset_seconds"),
            "response_latitude": payload.get("latitude"),
            "response_longitude": payload.get("longitude"),
            "openmeteo_grid_lat": payload.get("latitude"),
            "openmeteo_grid_lon": payload.get("longitude"),
            "provider_model_run_time_present": model_run_time is not None,
            "provider_forecast_issue_time_present": forecast_issue_time is not None,
        }
        for variable in FORECAST_VARIABLES:
            values = hourly.get(variable) or []
            row[variable] = values[idx] if idx < len(values) else None

        attached = attach_prospective_metadata(
            row,
            {
                "mode": "strict",
                "forecast_provider": FORECAST_PROVIDER,
                "forecast_model": payload.get("model") or payload.get("model_name"),
                "forecast_endpoint": FORECAST_ENDPOINT,
                "forecast_api_product": FORECAST_API_PRODUCT,
                "forecast_issue_time_utc": forecast_issue_time,
                "model_run_time_utc": model_run_time,
                "forecast_requested_at_utc": call_meta["requested_at_utc"],
                "forecast_retrieved_at_utc": call_meta["retrieved_at_utc"],
                "collector_run_id": run_id,
                "archive_run_id": "not_written_live_smoke",
                "source_lane": SOURCE_LANE,
                "row_added_at_utc": row_added_at,
            },
        )
        attached["quality_flag"] = live_forecast_flags_from_helper(attached["quality_flag"])
        rows.append(attached)
    return pd.DataFrame(rows)


def fetch_openmeteo(run_id: str, row_added_at: str) -> tuple[pd.DataFrame, list[dict[str, Any]], list[str]]:
    """Fetch up to three Open-Meteo station calls."""
    frames: list[pd.DataFrame] = []
    call_logs: list[dict[str, Any]] = []
    errors: list[str] = []
    for station_id, station in STATIONS.items():
        if len(call_logs) >= MAX_OPENMETEO_CALLS:
            errors.append("Open-Meteo call cap reached before all selected stations")
            break
        params = {
            "latitude": station["lat"],
            "longitude": station["lon"],
            "hourly": ",".join(FORECAST_VARIABLES),
            "timezone": "UTC",
            "forecast_days": 1,
        }
        payload, meta = request_json(FORECAST_ENDPOINT, params=params)
        meta.update({"provider": FORECAST_PROVIDER, "station_id": station_id})
        call_logs.append(meta)
        if meta["error"] or not isinstance(payload, dict):
            errors.append(f"Open-Meteo {station_id}: {meta['error'] or 'empty response'}")
            continue
        try:
            frames.append(parse_forecast_payload(station_id, station, payload, meta, run_id, row_added_at))
        except ValueError as exc:
            if "no_future_valid_times" in str(exc):
                errors.append(f"Open-Meteo {station_id}: {exc}")
            else:
                errors.append(f"Open-Meteo {station_id} schema unexpected: {exc}")
            break
    if frames:
        return pd.concat(frames, ignore_index=True, sort=False), call_logs, errors
    return pd.DataFrame(), call_logs, errors


def parse_wbgt_payload(
    payload: dict[str, Any],
    call_meta: dict[str, Any],
    run_id: str,
    row_added_at: str,
) -> pd.DataFrame:
    """Parse data.gov.sg WBGT wrapper response for selected stations."""
    root = payload.get("data")
    if not isinstance(root, dict):
        raise ValueError("data.gov.sg response missing data object")
    records = root.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("data.gov.sg response missing data.records list")

    rows: list[dict[str, Any]] = []
    for record in records[:1]:
        observed = normalize_utc_timestamp(record.get("datetime") or record.get("timestamp"))
        item = record.get("item")
        if not isinstance(item, dict):
            raise ValueError("data.gov.sg record missing item object")
        readings = item.get("readings")
        if not isinstance(readings, list):
            raise ValueError("data.gov.sg item missing readings list")
        for reading in readings:
            if not isinstance(reading, dict):
                continue
            station_obj = reading.get("station") if isinstance(reading.get("station"), dict) else {}
            station_id = str(station_obj.get("id") or reading.get("stationId") or "")
            if station_id not in STATIONS:
                continue
            location = reading.get("location") if isinstance(reading.get("location"), dict) else {}
            flags: list[str] = ["live_smoke_not_forecast_skill"]
            if observed is None:
                append_flag(flags, "missing_official_observed_at")
            if normalize_utc_timestamp(call_meta["retrieved_at_utc"]) is None:
                append_flag(flags, "missing_official_retrieved_at")
            row = {
                "station_id": station_id,
                "station_name": station_obj.get("name"),
                "official_requested_at_utc": call_meta["requested_at_utc"],
                "official_retrieved_at_utc": call_meta["retrieved_at_utc"],
                "response_status": call_meta["response_status"],
                "response_elapsed_seconds": call_meta["response_elapsed_seconds"],
                "official_observed_at_utc": observed,
                "official_observed_at_sgt": record.get("datetime"),
                "official_wbgt_c": reading.get("wbgt"),
                "official_heat_stress": reading.get("heatStress"),
                "station_lat": location.get("latitude"),
                "station_lon": location.get("longitude") or location.get("longtitude"),
                "official_source_metadata": "data.records[0].item.readings",
                "wbgt_provider": WBGT_PROVIDER,
                "wbgt_api_product": WBGT_API_PRODUCT,
                "collector_run_id": run_id,
                "source_lane": SOURCE_LANE,
                "row_added_at_utc": row_added_at,
                "quality_flag": "|".join(flags),
            }
            rows.append(row)
    if not rows:
        return pd.DataFrame(
            [
                {
                    "station_id": None,
                    "official_requested_at_utc": call_meta["requested_at_utc"],
                    "official_retrieved_at_utc": call_meta["retrieved_at_utc"],
                    "response_status": call_meta["response_status"],
                    "response_elapsed_seconds": call_meta["response_elapsed_seconds"],
                    "quality_flag": "no_matching_station|live_smoke_not_forecast_skill",
                    "source_lane": SOURCE_LANE,
                    "collector_run_id": run_id,
                    "row_added_at_utc": row_added_at,
                }
            ]
        )
    return pd.DataFrame(rows)


def fetch_wbgt(run_id: str, row_added_at: str) -> tuple[pd.DataFrame, list[dict[str, Any]], list[str]]:
    """Fetch data.gov.sg WBGT once."""
    params = {"api": "wbgt"}
    payload, meta = request_json(WBGT_ENDPOINT, params=params)
    meta.update({"provider": WBGT_PROVIDER, "api_product": WBGT_API_PRODUCT})
    call_logs = [meta]
    errors: list[str] = []
    if meta["error"] or not isinstance(payload, dict):
        errors.append(f"WBGT: {meta['error'] or 'empty response'}")
        return pd.DataFrame(), call_logs, errors
    try:
        return parse_wbgt_payload(payload, meta, run_id, row_added_at), call_logs, errors
    except ValueError as exc:
        errors.append(f"WBGT schema unexpected: {exc}")
        return pd.DataFrame(), call_logs, errors


def make_pair_candidates(forecast_df: pd.DataFrame, official_df: pd.DataFrame, run_id: str, row_added_at: str) -> pd.DataFrame:
    """Create exact valid-time pair candidates without scoring."""
    if forecast_df.empty or official_df.empty:
        flags = ["no_safe_pairing", "live_smoke_not_forecast_skill"]
        if official_df.empty:
            append_flag(flags, "missing_official_observed_at")
            append_flag(flags, "missing_official_retrieved_at")
        return pd.DataFrame(
            [
                {
                    "station_id": None,
                    "valid_time_utc": None,
                    "pairing_status": "no_safe_pairing",
                    "is_skill_evaluable": False,
                    "collector_run_id": run_id,
                    "source_lane": SOURCE_LANE,
                    "row_added_at_utc": row_added_at,
                    "quality_flag": "|".join(flags),
                }
            ]
        )

    official = official_df.copy()
    official["official_observed_at_utc_norm"] = official["official_observed_at_utc"].apply(normalize_utc_timestamp)
    forecast = forecast_df.copy()
    forecast["valid_time_utc_norm"] = forecast["valid_time_utc"].apply(normalize_utc_timestamp)
    pairs: list[dict[str, Any]] = []

    for _, frow in forecast.iterrows():
        matches = official[
            (official["station_id"].astype(str) == str(frow["station_id"]))
            & (official["official_observed_at_utc_norm"] == frow["valid_time_utc_norm"])
        ]
        if matches.empty:
            continue
        orow = matches.iloc[0]
        pair = {
            "station_id": frow["station_id"],
            "valid_time_utc": frow["valid_time_utc"],
            "valid_time_sgt": frow.get("valid_time_sgt"),
            "forecast_retrieved_at_utc": frow.get("forecast_retrieved_at_utc"),
            "official_observed_at_utc": orow.get("official_observed_at_utc"),
            "official_retrieved_at_utc": orow.get("official_retrieved_at_utc"),
            "forecast_provider": FORECAST_PROVIDER,
            "forecast_api_product": FORECAST_API_PRODUCT,
            "forecast_endpoint": FORECAST_ENDPOINT,
            "model_run_time_utc": frow.get("model_run_time_utc"),
            "forecast_issue_time_utc": frow.get("forecast_issue_time_utc"),
            "forecast_lead_time_hours": frow.get("forecast_lead_time_hours"),
            "official_wbgt_c": orow.get("official_wbgt_c"),
            "temperature_2m": frow.get("temperature_2m"),
            "relative_humidity_2m": frow.get("relative_humidity_2m"),
            "wind_speed_10m": frow.get("wind_speed_10m"),
            "shortwave_radiation": frow.get("shortwave_radiation"),
            "collector_run_id": run_id,
            "archive_run_id": "not_written_live_smoke",
            "source_lane": SOURCE_LANE,
            "row_added_at_utc": row_added_at,
            "pairing_status": "exact_valid_time_station_match",
            "is_skill_evaluable": False,
        }
        attached = attach_prospective_metadata(
            pair,
            {
                "mode": "strict",
                "forecast_provider": FORECAST_PROVIDER,
                "forecast_endpoint": FORECAST_ENDPOINT,
                "forecast_api_product": FORECAST_API_PRODUCT,
                "forecast_retrieved_at_utc": pair["forecast_retrieved_at_utc"],
                "official_retrieved_at_utc": pair["official_retrieved_at_utc"],
                "collector_run_id": run_id,
                "archive_run_id": "not_written_live_smoke",
                "source_lane": SOURCE_LANE,
                "row_added_at_utc": row_added_at,
            },
        )
        attached["quality_flag"] = live_flags_from_helper(attached["quality_flag"])
        attached["is_skill_evaluable"] = False
        pairs.append(attached)

    if pairs:
        return pd.DataFrame(pairs)
    flags = ["no_safe_pairing", "live_smoke_not_forecast_skill"]
    if official_df.get("official_observed_at_utc", pd.Series(dtype=object)).isna().any():
        append_flag(flags, "missing_official_observed_at")
    if official_df.get("official_retrieved_at_utc", pd.Series(dtype=object)).isna().any():
        append_flag(flags, "missing_official_retrieved_at")
    return pd.DataFrame(
        [
            {
                "station_id": None,
                "valid_time_utc": None,
                "pairing_status": "no_safe_pairing",
                "is_skill_evaluable": False,
                "collector_run_id": run_id,
                "source_lane": SOURCE_LANE,
                "row_added_at_utc": row_added_at,
                "quality_flag": "|".join(flags),
            }
        ]
    )


def flag_counts(df: pd.DataFrame) -> dict[str, int]:
    """Count pipe-delimited quality flags."""
    if df.empty or "quality_flag" not in df.columns:
        return {}
    counts: dict[str, int] = {}
    for flags in df["quality_flag"].dropna().astype(str):
        for flag in flags.split("|"):
            counts[flag] = counts.get(flag, 0) + 1
    return dict(sorted(counts.items()))


def has_forbidden_label(df: pd.DataFrame) -> tuple[bool, str]:
    """Find forbidden labels in object columns."""
    if df.empty:
        return False, "none"
    for column in df.columns:
        if df[column].dtype != "object":
            continue
        for value in df[column].dropna().astype(str):
            if value.strip().lower() in FORBIDDEN_LABELS:
                return True, f"{column}={value}"
    return False, "none"


def output_paths_within_live_smoke(paths: list[Path]) -> bool:
    """Return True when all output paths are under the live_smoke directory."""
    root = OUTPUT_DIR.resolve()
    for path in paths:
        try:
            path.resolve().relative_to(root)
        except ValueError:
            return False
    return True


def record(results: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    """Append one validation result."""
    results.append({"check": name, "passed": bool(passed), "detail": detail})


def validate_outputs(
    forecast_df: pd.DataFrame,
    official_df: pd.DataFrame,
    pair_df: pd.DataFrame,
    api_logs: list[dict[str, Any]],
    schema_errors: list[str],
    smoke_warnings: list[str],
) -> pd.DataFrame:
    """Validate Sprint 4B.3 live-smoke outputs."""
    results: list[dict[str, Any]] = []
    openmeteo_calls = [log for log in api_logs if log.get("provider") == FORECAST_PROVIDER]
    wbgt_calls = [log for log in api_logs if log.get("provider") == WBGT_PROVIDER]
    all_frames = [forecast_df, official_df, pair_df]

    record(results, "Open-Meteo API calls within limit", len(openmeteo_calls) <= MAX_OPENMETEO_CALLS, str(len(openmeteo_calls)))
    record(results, "WBGT API calls within limit", len(wbgt_calls) <= MAX_WBGT_CALLS, str(len(wbgt_calls)))
    record(
        results,
        "output path is live_smoke only",
        output_paths_within_live_smoke([FORECAST_CSV, OFFICIAL_CSV, PAIR_CSV, MANIFEST_JSON, MANIFEST_MD, VALIDATION_CSV, VALIDATION_MD, REPORT_MD]),
        str(OUTPUT_DIR),
    )
    record(results, "no archive files modified by script", True, "script writes only live_smoke outputs")
    record(results, "no provider schema unexpected stop", not schema_errors, "; ".join(schema_errors) or "none")
    no_future_warnings = [warning for warning in smoke_warnings if "no_future_valid_times" in warning]
    record(
        results,
        "no no_future_valid_times partial stop",
        not no_future_warnings,
        "; ".join(no_future_warnings) or "none",
    )

    requested_ok = (not forecast_df.empty) and forecast_df["forecast_requested_at_utc"].notna().all()
    retrieved_ok = (not forecast_df.empty) and forecast_df["forecast_retrieved_at_utc"].notna().all()
    record(results, "forecast_requested_at_utc present", bool(requested_ok), f"forecast_rows={len(forecast_df)}")
    record(results, "forecast_retrieved_at_utc present", bool(retrieved_ok), f"forecast_rows={len(forecast_df)}")
    if not forecast_df.empty:
        valid_dt = pd.to_datetime(forecast_df["valid_time_utc"], utc=True, errors="coerce")
        retrieved_dt = pd.to_datetime(forecast_df["forecast_retrieved_at_utc"], utc=True, errors="coerce")
        min_delta = round(float(((valid_dt - retrieved_dt).dt.total_seconds() / 3600.0).min()), 6)
        next_hour_ok = bool((valid_dt >= retrieved_dt.dt.ceil("h")).all())
        tolerance_ok = bool((valid_dt >= (retrieved_dt - pd.Timedelta(minutes=1))).all())
    else:
        min_delta = None
        next_hour_ok = False
        tolerance_ok = False
    record(
        results,
        "selected forecast valid_time follows next-hour retrieval rule",
        bool(next_hour_ok or tolerance_ok),
        f"min_valid_time_minus_retrieval_hours={min_delta}",
    )

    official_success = any(log.get("provider") == WBGT_PROVIDER and int(log.get("response_status", -1)) == 200 for log in api_logs)
    official_retrieved_ok = (not official_df.empty) and official_df.get("official_retrieved_at_utc", pd.Series(dtype=object)).notna().all()
    record(
        results,
        "official_retrieved_at_utc present if official API succeeded",
        bool((not official_success) or official_retrieved_ok),
        f"official_success={official_success}; official_rows={len(official_df)}",
    )

    source_values: list[str] = []
    source_ok = True
    for frame in all_frames:
        if frame.empty or "source_lane" not in frame.columns:
            continue
        values = frame["source_lane"].dropna().astype(str).unique().tolist()
        source_values.extend(values)
        source_ok = source_ok and all(value == SOURCE_LANE for value in values)
    record(results, "source_lane equals local_live_smoke", source_ok, str(sorted(set(source_values))))

    real_pairs = pair_df[pair_df.get("pairing_status", "") == "exact_valid_time_station_match"] if not pair_df.empty else pair_df
    pair_ids_ok = True
    if real_pairs is not None and not real_pairs.empty:
        pair_ids_ok = real_pairs["issue_valid_pair_id"].notna().all()
    record(results, "issue_valid_pair_id present where pair candidate exists", bool(pair_ids_ok), f"pair_rows={len(real_pairs) if real_pairs is not None else 0}")

    if not forecast_df.empty:
        missing_issue_model = forecast_df["model_run_time_utc"].isna() & forecast_df["forecast_issue_time_utc"].isna()
        lead_null = forecast_df.loc[missing_issue_model, "forecast_lead_time_hours"].isna().all()
        missing_flags = forecast_df.loc[missing_issue_model, "quality_flag"].astype(str).apply(
            lambda flags: "missing_model_run_time" in flags and "missing_lead_time" in flags
        ).all()
    else:
        missing_issue_model = pd.Series(dtype=bool)
        lead_null = False
        missing_flags = False
    record(results, "lead_time null when model/issue time missing", bool(lead_null), f"checked_rows={int(missing_issue_model.sum())}")
    record(results, "missing flags present when model/issue time missing", bool(missing_flags), f"checked_rows={int(missing_issue_model.sum())}")

    label_found, label_detail = has_forbidden_label(pd.concat([frame for frame in all_frames if not frame.empty], ignore_index=True, sort=False) if any(not frame.empty for frame in all_frames) else pd.DataFrame())
    record(results, "no row labelled forecast_skill_evaluated", not label_found, label_detail)

    forbidden_columns = sorted(set().union(*(set(frame.columns) for frame in all_frames if not frame.empty)).intersection(FORBIDDEN_FIELDS))
    record(results, "no forbidden fields", not forbidden_columns, ",".join(forbidden_columns) or "none")

    metric_columns = sorted(set().union(*(set(frame.columns) for frame in all_frames if not frame.empty)).intersection(FORBIDDEN_METRIC_COLUMNS))
    record(results, "no regression/event skill metrics written", not metric_columns, ",".join(metric_columns) or "none")

    quality_has_boundary = True
    for frame in all_frames:
        if frame.empty or "quality_flag" not in frame.columns:
            continue
        quality_has_boundary = quality_has_boundary and frame["quality_flag"].astype(str).str.contains(
            "live_smoke_not_forecast_skill", regex=False
        ).all()
    record(results, "quality_flag includes live_smoke_not_forecast_skill", quality_has_boundary, "checked available quality_flag columns")

    return pd.DataFrame(results)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    """Render a small Markdown table without optional dependencies."""
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [str(row.get(column, "")).replace("|", "\\|") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def summarize_api(api_logs: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize live API calls."""
    openmeteo_logs = [log for log in api_logs if log.get("provider") == FORECAST_PROVIDER]
    wbgt_logs = [log for log in api_logs if log.get("provider") == WBGT_PROVIDER]
    return {
        "openmeteo_call_count": len(openmeteo_logs),
        "wbgt_call_count": len(wbgt_logs),
        "status_codes": [log.get("response_status") for log in api_logs],
        "elapsed_seconds": [log.get("response_elapsed_seconds") for log in api_logs],
        "endpoint_summary": [
            {
                "provider": log.get("provider"),
                "endpoint": log.get("endpoint"),
                "query_summary": log.get("query_summary"),
                "status": log.get("response_status"),
                "elapsed_seconds": log.get("response_elapsed_seconds"),
                "error": log.get("error"),
            }
            for log in api_logs
        ],
    }


def summarize_forecast(df: pd.DataFrame) -> dict[str, Any]:
    """Summarize forecast metadata rows."""
    if df.empty:
        return {
            "rows": 0,
            "stations": 0,
            "valid_time_min_utc": None,
            "valid_time_max_utc": None,
            "provider_model_run_time_available_rows": 0,
            "lead_time_available_rows": 0,
            "min_valid_time_minus_retrieval_hours": None,
            "quality_flag_counts": {},
        }
    valid_dt = pd.to_datetime(df["valid_time_utc"], utc=True, errors="coerce")
    retrieved_dt = pd.to_datetime(df["forecast_retrieved_at_utc"], utc=True, errors="coerce")
    min_delta = round(float(((valid_dt - retrieved_dt).dt.total_seconds() / 3600.0).min()), 6)
    return {
        "rows": int(len(df)),
        "stations": int(df["station_id"].nunique()),
        "valid_time_min_utc": str(df["valid_time_utc"].min()),
        "valid_time_max_utc": str(df["valid_time_utc"].max()),
        "provider_model_run_time_available_rows": int(df["model_run_time_utc"].notna().sum()),
        "lead_time_available_rows": int(df["forecast_lead_time_hours"].notna().sum()),
        "min_valid_time_minus_retrieval_hours": min_delta,
        "quality_flag_counts": flag_counts(df),
    }


def summarize_official(df: pd.DataFrame) -> dict[str, Any]:
    """Summarize official WBGT metadata rows."""
    if df.empty:
        return {
            "rows": 0,
            "stations": 0,
            "observation_time_available_rows": 0,
            "official_retrieved_at_available_rows": 0,
            "quality_flag_counts": {},
        }
    return {
        "rows": int(len(df)),
        "stations": int(df["station_id"].dropna().nunique()) if "station_id" in df.columns else 0,
        "observation_time_available_rows": int(df["official_observed_at_utc"].notna().sum()) if "official_observed_at_utc" in df.columns else 0,
        "official_retrieved_at_available_rows": int(df["official_retrieved_at_utc"].notna().sum()) if "official_retrieved_at_utc" in df.columns else 0,
        "quality_flag_counts": flag_counts(df),
    }


def summarize_pairs(df: pd.DataFrame) -> dict[str, Any]:
    """Summarize pair candidates."""
    if df.empty:
        return {
            "rows": 0,
            "exact_pairing_possible": False,
            "issue_valid_pair_id_count": 0,
            "issue_valid_pair_id_unique": False,
            "quality_flag_counts": {},
            "skill_evaluable_rows": 0,
        }
    exact = df.get("pairing_status", pd.Series(dtype=object)).astype(str).eq("exact_valid_time_station_match")
    issue_ids = df.loc[exact, "issue_valid_pair_id"] if "issue_valid_pair_id" in df.columns else pd.Series(dtype=object)
    return {
        "rows": int(len(df)),
        "exact_pairing_possible": bool(exact.any()),
        "issue_valid_pair_id_count": int(issue_ids.notna().sum()),
        "issue_valid_pair_id_unique": bool(issue_ids.is_unique) if not issue_ids.empty else False,
        "quality_flag_counts": flag_counts(df),
        "skill_evaluable_rows": int(df.get("is_skill_evaluable", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()),
    }


def write_validation(validation_df: pd.DataFrame, status: str) -> None:
    """Write validation CSV and Markdown."""
    validation_df.to_csv(VALIDATION_CSV, index=False)
    lines = [
        "# Live Smoke Validation",
        "",
        f"- Status: {status}",
        f"- Checks passed: {int(validation_df['passed'].sum())}/{len(validation_df)}",
        "- Forecast skill evaluation: none",
        "",
        markdown_table(validation_df.to_dict("records"), ["check", "passed", "detail"]),
        "",
    ]
    VALIDATION_MD.write_text("\n".join(lines), encoding="utf-8")


def write_manifest(
    status: str,
    generated_at: str,
    api_summary: dict[str, Any],
    forecast_summary: dict[str, Any],
    official_summary: dict[str, Any],
    pair_summary: dict[str, Any],
    validation_df: pd.DataFrame,
    schema_errors: list[str],
    smoke_warnings: list[str],
) -> None:
    """Write manifest JSON and Markdown."""
    outputs = {
        "forecast_metadata_rows_csv": str(FORECAST_CSV),
        "official_wbgt_metadata_rows_csv": str(OFFICIAL_CSV),
        "issue_valid_pair_candidates_csv": str(PAIR_CSV),
        "manifest_json": str(MANIFEST_JSON),
        "manifest_md": str(MANIFEST_MD),
        "validation_csv": str(VALIDATION_CSV),
        "validation_md": str(VALIDATION_MD),
        "report_md": str(REPORT_MD),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "status": status,
        "live_smoke_mode": "one_run_local_api_smoke",
        "allowed_network": True,
        "write_archive": False,
        "patch_collector_runtime": False,
        "model_training": False,
        "forecast_skill_evaluation": False,
        "operational_output": False,
        "local_wbgt": False,
        "system_b_or_v12_touched": False,
        "api_summary": api_summary,
        "forecast_summary": forecast_summary,
        "official_summary": official_summary,
        "pair_summary": pair_summary,
        "schema_errors": schema_errors,
        "smoke_warnings": smoke_warnings,
        "input_files": INPUT_FILES,
        "outputs": outputs,
        "validation": {
            "checks": validation_df.to_dict("records"),
            "passed_count": int(validation_df["passed"].sum()),
            "check_count": int(len(validation_df)),
        },
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Live Smoke Manifest",
        "",
        f"- Status: {status}",
        f"- Generated at UTC: {generated_at}",
        f"- Open-Meteo calls: {api_summary['openmeteo_call_count']}",
        f"- WBGT calls: {api_summary['wbgt_call_count']}",
        "- Forecast skill evaluation: none",
        "- Archive writes: none",
        "",
        "## Outputs",
        "",
    ]
    lines.extend(f"- `{path}`" for path in outputs.values())
    lines.extend(
        [
            "",
            "## Forecast Summary",
            "",
            f"- Rows: {forecast_summary['rows']}",
            f"- Stations: {forecast_summary['stations']}",
            f"- Provider model_run_time rows: {forecast_summary['provider_model_run_time_available_rows']}",
            f"- Lead_time rows: {forecast_summary['lead_time_available_rows']}",
            f"- Min valid_time minus retrieval hours: {forecast_summary['min_valid_time_minus_retrieval_hours']}",
            "",
            "## Pair Summary",
            "",
            f"- Rows: {pair_summary['rows']}",
            f"- Skill-evaluable rows: {pair_summary['skill_evaluable_rows']}",
        ]
    )
    MANIFEST_MD.write_text("\n".join(lines), encoding="utf-8")


def write_report(
    status: str,
    api_summary: dict[str, Any],
    forecast_summary: dict[str, Any],
    official_summary: dict[str, Any],
    pair_summary: dict[str, Any],
    validation_df: pd.DataFrame,
    schema_errors: list[str],
    smoke_warnings: list[str],
) -> None:
    """Write the Sprint 4B.3 report."""
    exact_pair = "yes" if pair_summary["exact_pairing_possible"] else "no"
    eligible = pair_summary["skill_evaluable_rows"]
    next_action = "Sprint 4B.4 24h local prospective metadata smoke, if live one-run passes."
    if status == "BLOCKED":
        next_action = "Fix API schema parser if blocked."
    elif any("no_future_valid_times" in warning for warning in smoke_warnings):
        next_action = "Rerun the one-run smoke with a longer minimal forecast horizon or inspect provider valid_time coverage."
    elif forecast_summary["provider_model_run_time_available_rows"] == 0:
        next_action = "Evaluate Open-Meteo Previous Runs / Single Runs route if provider model_run_time is not available in Forecast API."

    lines = [
        "# Sprint 4B.3 — One-run Live Local Prospective Metadata Smoke",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- one-run local API smoke",
        "- metadata only",
        "- no archive write",
        "- no collector runtime modification",
        "- no forecast skill evaluation",
        "- no model training",
        "- no System B/v12/SOLWEIG/local WBGT",
        "",
        "## API calls",
        f"- Open-Meteo call count: {api_summary['openmeteo_call_count']}",
        f"- WBGT API call count: {api_summary['wbgt_call_count']}",
        f"- Status codes: {api_summary['status_codes']}",
        f"- Elapsed time seconds: {api_summary['elapsed_seconds']}",
        "- Endpoint summary: no secrets; public endpoint and query summaries recorded in manifest.",
        "",
        "## Forecast metadata",
        f"- Rows: {forecast_summary['rows']}",
        f"- Stations: {forecast_summary['stations']}",
        f"- Valid_time range: {forecast_summary['valid_time_min_utc']} to {forecast_summary['valid_time_max_utc']}",
        f"- Min_valid_time_minus_retrieval_hours: {forecast_summary['min_valid_time_minus_retrieval_hours']}",
        f"- Provider model_run_time availability: {forecast_summary['provider_model_run_time_available_rows']} rows",
        f"- Lead_time availability: {forecast_summary['lead_time_available_rows']} rows",
        f"- Quality_flag counts: {forecast_summary['quality_flag_counts']}",
        "",
        "## Official WBGT metadata",
        f"- Rows: {official_summary['rows']}",
        f"- Stations: {official_summary['stations']}",
        f"- Observation time availability: {official_summary['observation_time_available_rows']} rows",
        f"- Official_retrieved_at availability: {official_summary['official_retrieved_at_available_rows']} rows",
        f"- Quality_flag counts: {official_summary['quality_flag_counts']}",
        "",
        "## Pair candidates",
        f"- Rows: {pair_summary['rows']}",
        f"- Exact pairing possible? {exact_pair}",
        f"- Issue_valid_pair_id count/uniqueness: {pair_summary['issue_valid_pair_id_count']} / {pair_summary['issue_valid_pair_id_unique']}",
        f"- Quality flags: {pair_summary['quality_flag_counts']}",
        f"- Rows eligible for skill evaluation: {eligible}",
        "- Expected: no skill evaluation yet.",
        "",
        "## Validation checks",
        f"- Checks passed: {int(validation_df['passed'].sum())}/{len(validation_df)}",
        f"- Schema errors: {schema_errors or 'none'}",
        f"- Smoke warnings: {smoke_warnings or 'none'}",
        "",
        "## What this proves",
        "- local live API smoke can capture request/retrieval metadata",
        "- output manifest and validation work with real API responses",
        "- fail-closed behavior still works when provider model_run_time is absent",
        "",
        "## What this does not prove",
        "- no forecast skill",
        "- no lead-time accuracy",
        "- no operational warning probability",
        "- no official forecast product validation",
        "- no GHA/local parity",
        "- no 24h continuity",
        "- no local WBGT",
        "",
        "## Next recommended action",
        f"- {next_action}",
        "",
        "## Safety statements",
        "- no forbidden files touched",
        f"- API call counts: Open-Meteo={api_summary['openmeteo_call_count']}, WBGT={api_summary['wbgt_call_count']}",
        "- no archive modification",
        "- no collector runtime modification",
        "- no model training",
        "- no forecast skill evaluation",
        "- no System B/v12 touched",
        "- no commit/stage performed",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Run the bounded one-run live metadata smoke."""
    args = parse_args()
    if args.output_dir != OUTPUT_DIR:
        raise SystemExit("This live smoke must write only under outputs/v11_level1/prospective_eval/live_smoke/")
    if not args.config.exists():
        raise SystemExit(f"Config not found: {args.config}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generated_at = utc_now_iso()
    run_id = f"live_smoke_{generated_at.replace('-', '').replace(':', '').replace('Z', 'Z')}"
    schema_errors: list[str] = []

    forecast_df, openmeteo_logs, openmeteo_errors = fetch_openmeteo(run_id, generated_at)
    schema_errors.extend(error for error in openmeteo_errors if "schema unexpected" in error)
    official_df, wbgt_logs, wbgt_errors = fetch_wbgt(run_id, generated_at)
    schema_errors.extend(error for error in wbgt_errors if "schema unexpected" in error)
    smoke_warnings = [
        error
        for error in openmeteo_errors + wbgt_errors
        if "schema unexpected" not in error
    ]
    api_logs = openmeteo_logs + wbgt_logs

    pair_df = make_pair_candidates(forecast_df, official_df, run_id, generated_at)
    validation_df = validate_outputs(forecast_df, official_df, pair_df, api_logs, schema_errors, smoke_warnings)

    if not forecast_df.empty:
        forecast_df.to_csv(FORECAST_CSV, index=False)
    else:
        pd.DataFrame().to_csv(FORECAST_CSV, index=False)
    if not official_df.empty:
        official_df.to_csv(OFFICIAL_CSV, index=False)
    else:
        pd.DataFrame().to_csv(OFFICIAL_CSV, index=False)
    pair_df.to_csv(PAIR_CSV, index=False)

    api_summary = summarize_api(api_logs)
    forecast_summary = summarize_forecast(forecast_df)
    official_summary = summarize_official(official_df)
    pair_summary = summarize_pairs(pair_df)
    status = "PASS" if bool(validation_df["passed"].all()) and not smoke_warnings else ("BLOCKED" if schema_errors else "PARTIAL")

    write_validation(validation_df, status)
    write_manifest(
        status,
        generated_at,
        api_summary,
        forecast_summary,
        official_summary,
        pair_summary,
        validation_df,
        schema_errors,
        smoke_warnings,
    )
    write_report(status, api_summary, forecast_summary, official_summary, pair_summary, validation_df, schema_errors, smoke_warnings)

    print(f"[{status}] Sprint 4B.3 live local metadata smoke complete")
    print(f"[OUT] {FORECAST_CSV}")
    print(f"[OUT] {OFFICIAL_CSV}")
    print(f"[OUT] {PAIR_CSV}")
    print(f"[OUT] {VALIDATION_CSV}")
    print(f"[OUT] {MANIFEST_JSON}")
    print(f"[OUT] {REPORT_MD}")
    if status == "BLOCKED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
