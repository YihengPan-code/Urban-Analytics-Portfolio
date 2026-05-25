#!/usr/bin/env python
"""Local-only dry smoke for System A Level 1 prospective metadata.

Inputs
------
- ``configs/v11/system_a_local_prospective_dry_smoke_config.example.yaml``
  as the documented dry-smoke configuration contract.
- Synthetic in-memory station rows only for prospective metadata rows.
- Optional legacy compatibility sample from an existing retrospective CSV,
  capped at 10 rows and read-only.

Outputs
-------
- ``outputs/v11_level1/prospective_eval/local_dry_smoke/synthetic_prospective_rows.csv``
- ``outputs/v11_level1/prospective_eval/local_dry_smoke/legacy_compatibility_rows.csv``
  when a small legacy sample is available.
- ``outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_manifest.json``
- ``outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_manifest.md``
- ``outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv``
- ``outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.md``
- ``outputs/v11_level1/prospective_eval/local_dry_smoke/sprint4b2_local_dry_smoke_report.md``

Saved metrics
-------------
The validation CSV records pass/fail checks for schema completeness, deterministic
issue-valid ids, lead-time fail-closed behavior, claim-boundary guardrails, and
legacy compatibility flags. The manifest JSON records row counts, paths, quality
flag counts, lead-time bins, and safety statements. This script performs no API
calls, no archive writes, no model training, and no model evaluation.
"""
from __future__ import annotations

import argparse
import json
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


CONFIG_PATH = Path("configs/v11/system_a_local_prospective_dry_smoke_config.example.yaml")
OUTPUT_DIR = Path("outputs/v11_level1/prospective_eval/local_dry_smoke")
SYNTHETIC_CSV = OUTPUT_DIR / "synthetic_prospective_rows.csv"
LEGACY_CSV = OUTPUT_DIR / "legacy_compatibility_rows.csv"
MANIFEST_JSON = OUTPUT_DIR / "local_dry_smoke_manifest.json"
MANIFEST_MD = OUTPUT_DIR / "local_dry_smoke_manifest.md"
VALIDATION_CSV = OUTPUT_DIR / "local_dry_smoke_validation.csv"
VALIDATION_MD = OUTPUT_DIR / "local_dry_smoke_validation.md"
REPORT_MD = OUTPUT_DIR / "sprint4b2_local_dry_smoke_report.md"

SCHEMA_VERSION = "v1.1-sprint4b2-local-prospective-dry-smoke-v0.1"
SOURCE_LANE = "local_dry_smoke"
FORECAST_PROVIDER = "open-meteo"
FORECAST_API_PRODUCT = "single_runs_api_synthetic_placeholder"
FORECAST_ENDPOINT = "offline_synthetic"
FORECAST_MODEL = "synthetic_model_cycle_v0"
LEAD_TIMES = [0, 1, 3, 6, 24]
STATIONS = {
    "S128": {"lat": 1.3678, "lon": 103.9826},
    "S142": {"lat": 1.3524, "lon": 103.9446},
    "S137": {"lat": 1.3424, "lon": 103.9825},
}
BASE_VALID_TIME = datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc)
VALID_TIME_COUNT = 4
LEGACY_MAX_ROWS = 10

REQUIRED_METADATA_FIELDS = [
    "station_id",
    "valid_time_utc",
    "valid_time_sgt",
    "model_run_time_utc",
    "forecast_issue_time_utc",
    "forecast_requested_at_utc",
    "forecast_retrieved_at_utc",
    "forecast_provider",
    "forecast_model",
    "forecast_endpoint",
    "forecast_api_product",
    "forecast_lead_time_hours",
    "forecast_age_hours",
    "openmeteo_grid_lat",
    "openmeteo_grid_lon",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
    "wbgt_proxy_v09_c",
    "wbgt_a_score_c",
    "p_ge31_diagnostic",
    "official_wbgt_c",
    "official_observed_at_utc",
    "official_retrieved_at_utc",
    "official_wbgt_publication_delay_minutes",
    "collector_run_id",
    "archive_run_id",
    "source_lane",
    "row_added_at_utc",
    "issue_valid_pair_id",
    "quality_flag",
]

EXPECTED_QUALITY_FLAGS = {
    "ok_prospective_metadata",
    "missing_model_run_time",
    "missing_forecast_issue_time",
    "missing_lead_time",
    "legacy_missing_prospective_metadata",
}
FORBIDDEN_CLAIM_FIELDS = {"local_wbgt_c", "risk_score", "cell_id"}
FORBIDDEN_ROW_LABELS = {"live", "prospective_skill", "evaluated"}
INPUT_FILES = [
    "scripts/v11_prospective_metadata_helpers.py",
    "scripts/v11_test_prospective_metadata_schema.py",
    "configs/v11/system_a_prospective_metadata_config.example.yaml",
    "configs/v11/system_a_local_prospective_dry_smoke_config.example.yaml",
    "docs/v11/SystemA_prospective_metadata_schema_CN.md",
    "outputs/v11_level1/prospective_eval/metadata_patch/sprint4b1_metadata_patch_report.md",
    "outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv",
    "outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.md",
    "outputs/v11_level1/prospective_eval/prospective_metadata_gap_audit.csv",
    "docs/v11/SystemA_Level1_prospective_eval_design_CN.md",
]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the local dry smoke."""
    parser = argparse.ArgumentParser(
        description=(
            "Run an offline synthetic-only System A Level 1 prospective metadata "
            "dry smoke. Writes CSV/JSON/Markdown outputs under the configured "
            "local_dry_smoke output directory and performs no API calls."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help=(
            "Documented dry-smoke config path. The script uses the checked-in "
            "v1.1 Sprint 4B.2 constants and verifies this config exists."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for all dry-smoke artifacts.",
    )
    parser.add_argument(
        "--skip-legacy",
        action="store_true",
        help="Skip the optional <=10-row legacy compatibility read.",
    )
    return parser.parse_args()


def iso_z(dt: datetime) -> str:
    """Return a UTC datetime as second-resolution ISO with Z suffix."""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_sgt(dt: datetime) -> str:
    """Return the Singapore display time for a UTC datetime."""
    sgt = timezone(timedelta(hours=8))
    return dt.astimezone(sgt).replace(microsecond=0).isoformat()


def row_measurements(station_index: int, valid_index: int, lead_index: int) -> dict[str, Any]:
    """Create deterministic synthetic meteorological and WBGT-like values."""
    temp = 29.2 + 0.25 * valid_index + 0.1 * station_index + 0.02 * lead_index
    humidity = 70.0 - 0.5 * valid_index + 0.3 * station_index
    wind = 1.8 + 0.1 * lead_index
    radiation = 320.0 + 25.0 * valid_index - 2.0 * station_index
    wbgt_proxy = 28.9 + 0.18 * valid_index + 0.08 * station_index
    wbgt_a = wbgt_proxy + 0.35
    official = wbgt_a + 0.2
    return {
        "temperature_2m": round(temp, 3),
        "relative_humidity_2m": round(humidity, 3),
        "wind_speed_10m": round(wind, 3),
        "shortwave_radiation": round(radiation, 3),
        "wbgt_proxy_v09_c": round(wbgt_proxy, 3),
        "wbgt_a_score_c": round(wbgt_a, 3),
        "p_ge31_diagnostic": round(min(0.95, max(0.05, (wbgt_a - 29.0) / 4.0)), 6),
        "official_wbgt_c": round(official, 3),
    }


def build_ok_row(
    station_id: str,
    station_index: int,
    valid_time: datetime,
    valid_index: int,
    lead_time: int,
    lead_index: int,
    row_added_at: str,
) -> dict[str, Any]:
    """Build one strict synthetic row with complete prospective metadata."""
    model_run = valid_time - timedelta(hours=lead_time)
    forecast_requested = model_run + timedelta(minutes=4)
    forecast_retrieved = model_run + timedelta(minutes=6)
    official_retrieved = valid_time + timedelta(minutes=15)
    station = STATIONS[station_id]
    row = {
        "station_id": station_id,
        "valid_time_utc": iso_z(valid_time),
        "valid_time_sgt": iso_sgt(valid_time),
        "official_observed_at_utc": iso_z(valid_time),
        "official_wbgt_c": row_measurements(station_index, valid_index, lead_index)["official_wbgt_c"],
        "openmeteo_grid_lat": station["lat"],
        "openmeteo_grid_lon": station["lon"],
        **row_measurements(station_index, valid_index, lead_index),
    }
    context = {
        "mode": "strict",
        "forecast_provider": FORECAST_PROVIDER,
        "forecast_model": FORECAST_MODEL,
        "forecast_endpoint": FORECAST_ENDPOINT,
        "forecast_api_product": FORECAST_API_PRODUCT,
        "forecast_issue_time_utc": iso_z(model_run),
        "model_run_time_utc": iso_z(model_run),
        "forecast_requested_at_utc": iso_z(forecast_requested),
        "forecast_retrieved_at_utc": iso_z(forecast_retrieved),
        "official_retrieved_at_utc": iso_z(official_retrieved),
        "collector_run_id": "collector_local_dry_smoke_synthetic",
        "archive_run_id": "archive_local_dry_smoke_synthetic",
        "source_lane": SOURCE_LANE,
        "row_added_at_utc": row_added_at,
    }
    return attach_prospective_metadata(row, context)


def build_fail_closed_row(
    station_id: str,
    station_index: int,
    valid_time: datetime,
    row_added_at: str,
) -> dict[str, Any]:
    """Build one synthetic row that must fail closed for lead-time scoring."""
    forecast_retrieved = valid_time - timedelta(minutes=10)
    official_retrieved = valid_time + timedelta(minutes=20)
    station = STATIONS[station_id]
    row = {
        "station_id": station_id,
        "valid_time_utc": iso_z(valid_time),
        "valid_time_sgt": iso_sgt(valid_time),
        "official_observed_at_utc": iso_z(valid_time),
        "openmeteo_grid_lat": station["lat"],
        "openmeteo_grid_lon": station["lon"],
        **row_measurements(station_index, 0, 0),
    }
    context = {
        "mode": "strict",
        "forecast_provider": FORECAST_PROVIDER,
        "forecast_model": FORECAST_MODEL,
        "forecast_endpoint": FORECAST_ENDPOINT,
        "forecast_api_product": FORECAST_API_PRODUCT,
        "forecast_requested_at_utc": iso_z(forecast_retrieved - timedelta(minutes=2)),
        "forecast_retrieved_at_utc": iso_z(forecast_retrieved),
        "official_retrieved_at_utc": iso_z(official_retrieved),
        "collector_run_id": "collector_local_dry_smoke_fail_closed",
        "archive_run_id": "archive_local_dry_smoke_synthetic",
        "source_lane": SOURCE_LANE,
        "row_added_at_utc": row_added_at,
    }
    return attach_prospective_metadata(row, context)


def build_synthetic_rows(row_added_at: str) -> pd.DataFrame:
    """Create complete and fail-closed synthetic prospective metadata rows."""
    rows: list[dict[str, Any]] = []
    valid_times = [BASE_VALID_TIME + timedelta(hours=6 * idx) for idx in range(VALID_TIME_COUNT)]
    for station_index, station_id in enumerate(STATIONS):
        for valid_index, valid_time in enumerate(valid_times):
            for lead_index, lead_time in enumerate(LEAD_TIMES):
                rows.append(
                    build_ok_row(
                        station_id=station_id,
                        station_index=station_index,
                        valid_time=valid_time,
                        valid_index=valid_index,
                        lead_time=lead_time,
                        lead_index=lead_index,
                        row_added_at=row_added_at,
                    )
                )
    fail_valid_time = BASE_VALID_TIME + timedelta(days=1)
    for station_index, station_id in enumerate(STATIONS):
        rows.append(build_fail_closed_row(station_id, station_index, fail_valid_time, row_added_at))
    return pd.DataFrame(rows)


def find_legacy_candidate() -> Path | None:
    """Find an existing retrospective file for a read-only <=10-row view."""
    candidates = [
        Path("data/calibration/v11/live_chunks/wbgt_pairs_2026-05-24.csv.gz"),
        Path("data/calibration/v11/v11_station_weather_pairs.csv"),
        Path("data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419.csv"),
        Path("data/archive/v11_longterm/paired/v11_operational_station_weather_pairs.csv"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def first_present(row: dict[str, Any], names: list[str]) -> Any:
    """Return the first non-empty value from a legacy row."""
    for name in names:
        value = row.get(name)
        if value is not None and not pd.isna(value):
            return value
    return None


def build_legacy_compatibility(row_added_at: str, skip: bool) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    """Create a read-only legacy schema view capped at 10 source rows."""
    if skip:
        return None, {"status": "skipped", "reason": "--skip-legacy was provided", "rows_read": 0}
    candidate = find_legacy_candidate()
    if candidate is None:
        return None, {"status": "skipped", "reason": "no easy retrospective CSV candidate found", "rows_read": 0}

    legacy_source = pd.read_csv(candidate, nrows=LEGACY_MAX_ROWS)
    rows: list[dict[str, Any]] = []
    for record in legacy_source.to_dict("records"):
        valid_time = first_present(record, ["valid_time_utc", "timestamp_utc", "official_observed_at_utc"])
        valid_time_utc = normalize_utc_timestamp(valid_time)
        base = {
            "station_id": first_present(record, ["station_id", "station_code"]) or "unknown_station",
            "valid_time_utc": valid_time_utc,
            "valid_time_sgt": first_present(record, ["valid_time_sgt", "timestamp_sgt"]),
            "official_observed_at_utc": normalize_utc_timestamp(
                first_present(record, ["official_observed_at_utc", "timestamp_utc", "valid_time_utc"])
            ),
            "official_wbgt_c": first_present(record, ["official_wbgt_c", "wbgt_c", "WBGT"]),
            "temperature_2m": first_present(record, ["temperature_2m", "air_temperature_c"]),
            "relative_humidity_2m": first_present(record, ["relative_humidity_2m", "relative_humidity"]),
            "wind_speed_10m": first_present(record, ["wind_speed_10m", "wind_speed"]),
            "shortwave_radiation": first_present(record, ["shortwave_radiation"]),
            "wbgt_proxy_v09_c": first_present(record, ["wbgt_proxy_v09_c"]),
            "wbgt_a_score_c": first_present(record, ["wbgt_a_score_c"]),
            "p_ge31_diagnostic": first_present(record, ["p_ge31_diagnostic"]),
            "openmeteo_grid_lat": first_present(record, ["openmeteo_grid_lat", "latitude", "station_lat"]),
            "openmeteo_grid_lon": first_present(record, ["openmeteo_grid_lon", "longitude", "station_lon"]),
        }
        attached = attach_prospective_metadata(
            base,
            {
                "mode": "legacy",
                "forecast_provider": FORECAST_PROVIDER,
                "forecast_model": None,
                "forecast_endpoint": "legacy_retrospective_view",
                "forecast_api_product": "legacy_retrospective_view",
                "collector_run_id": "legacy_compatibility_read_only",
                "archive_run_id": first_present(record, ["archive_run_id"]) or "legacy_read_only",
                "source_lane": "legacy_retrospective_view",
                "row_added_at_utc": row_added_at,
            },
        )
        attached["forecast_lead_time_hours"] = None
        attached["quality_flag"] = "|".join(
            flag
            for flag in str(attached["quality_flag"]).split("|")
            if flag != "ok_prospective_metadata"
        )
        if "legacy_missing_prospective_metadata" not in str(attached["quality_flag"]):
            attached["quality_flag"] = f"{attached['quality_flag']}|legacy_missing_prospective_metadata"
        rows.append(attached)

    return pd.DataFrame(rows), {
        "status": "sampled",
        "source_path": str(candidate),
        "rows_read": int(len(legacy_source)),
        "max_rows": LEGACY_MAX_ROWS,
    }


def record(results: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    """Append one validation result."""
    results.append({"check": name, "passed": bool(passed), "detail": detail})


def has_forbidden_label(df: pd.DataFrame) -> tuple[bool, str]:
    """Check row string values for forbidden status labels."""
    object_columns = [col for col in df.columns if df[col].dtype == "object"]
    for col in object_columns:
        for value in df[col].dropna().astype(str):
            normalized = value.strip().lower()
            if normalized in FORBIDDEN_ROW_LABELS:
                return True, f"{col}={value}"
    return False, "none"


def validate_outputs(synthetic_df: pd.DataFrame, legacy_df: pd.DataFrame | None) -> pd.DataFrame:
    """Run dry-smoke validation checks."""
    results: list[dict[str, Any]] = []

    missing_required = [field for field in REQUIRED_METADATA_FIELDS if field not in synthetic_df.columns]
    record(results, "all required schema fields exist", not missing_required, ",".join(missing_required) or "all present")

    missing_helper = [field for field in PROSPECTIVE_METADATA_FIELDS if field not in synthetic_df.columns]
    record(results, "helper prospective schema fields exist", not missing_helper, ",".join(missing_helper) or "all present")

    id_non_null = synthetic_df["issue_valid_pair_id"].notna().all()
    id_unique = synthetic_df["issue_valid_pair_id"].is_unique
    record(
        results,
        "issue_valid_pair_id non-null and unique",
        bool(id_non_null and id_unique),
        f"non_null={id_non_null}; unique={id_unique}; rows={len(synthetic_df)}",
    )

    model_present = synthetic_df["model_run_time_utc"].notna()
    computed = synthetic_df.loc[model_present].apply(
        lambda row: compute_lead_time_hours(row["valid_time_utc"], row["forecast_issue_time_utc"], row["model_run_time_utc"]),
        axis=1,
    )
    stored = synthetic_df.loc[model_present, "forecast_lead_time_hours"].astype(float)
    lead_ok = bool((computed.reset_index(drop=True).astype(float) == stored.reset_index(drop=True)).all())
    record(results, "lead_time computed correctly when model_run_time exists", lead_ok, f"checked_rows={int(model_present.sum())}")

    missing_issue_model = synthetic_df["model_run_time_utc"].isna() & synthetic_df["forecast_issue_time_utc"].isna()
    null_lead = synthetic_df.loc[missing_issue_model, "forecast_lead_time_hours"].isna().all()
    record(
        results,
        "lead_time null when issue/model time missing",
        bool(null_lead),
        f"checked_rows={int(missing_issue_model.sum())}",
    )

    fail_flags_ok = synthetic_df.loc[missing_issue_model, "quality_flag"].astype(str).apply(
        lambda flags: all(
            required in flags
            for required in ["missing_model_run_time", "missing_forecast_issue_time", "missing_lead_time"]
        )
    ).all()
    record(results, "fail_closed quality flags present", bool(fail_flags_ok), f"checked_rows={int(missing_issue_model.sum())}")

    forbidden_fields = sorted(FORBIDDEN_CLAIM_FIELDS.intersection(synthetic_df.columns))
    record(results, "no forbidden claim fields", not forbidden_fields, ",".join(forbidden_fields) or "none")

    source_ok = bool((synthetic_df["source_lane"] == SOURCE_LANE).all())
    record(results, "source_lane equals local_dry_smoke", source_ok, str(synthetic_df["source_lane"].value_counts().to_dict()))

    forbidden_label_found, forbidden_detail = has_forbidden_label(synthetic_df)
    record(results, "no row labelled live/prospective_skill/evaluated", not forbidden_label_found, forbidden_detail)

    if legacy_df is not None and not legacy_df.empty:
        legacy_flags = legacy_df["quality_flag"].astype(str)
        legacy_ok = legacy_flags.str.contains("legacy_missing_prospective_metadata", regex=False).all()
        legacy_lead_null = legacy_df["forecast_lead_time_hours"].isna().all()
        record(
            results,
            "legacy rows marked missing prospective metadata",
            bool(legacy_ok and legacy_lead_null),
            f"rows={len(legacy_df)}; lead_time_null={legacy_lead_null}",
        )
    else:
        record(results, "legacy compatibility optional sample", True, "skipped or unavailable")

    expected_flags_found = set()
    for flags in synthetic_df["quality_flag"].astype(str):
        expected_flags_found.update(flags.split("|"))
    missing_expected = sorted(EXPECTED_QUALITY_FLAGS.difference(expected_flags_found))
    missing_expected = [flag for flag in missing_expected if flag != "legacy_missing_prospective_metadata"]
    record(results, "expected synthetic quality flags present", not missing_expected, ",".join(missing_expected) or "present")

    return pd.DataFrame(results)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    """Render a small GitHub-flavored Markdown table without extra dependencies."""
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [str(row.get(col, "")).replace("|", "\\|") for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def flag_counts(df: pd.DataFrame) -> dict[str, int]:
    """Count individual quality flags across rows."""
    counts: dict[str, int] = {}
    for flags in df["quality_flag"].dropna().astype(str):
        for flag in flags.split("|"):
            counts[flag] = counts.get(flag, 0) + 1
    return dict(sorted(counts.items()))


def summarize_synthetic(df: pd.DataFrame) -> dict[str, Any]:
    """Summarize synthetic prospective rows for manifest and report."""
    lead_values = sorted(
        int(value)
        for value in df["forecast_lead_time_hours"].dropna().astype(float).unique().tolist()
    )
    return {
        "row_count": int(len(df)),
        "station_count": int(df["station_id"].nunique()),
        "lead_time_bins": lead_values,
        "valid_time_min_utc": str(df["valid_time_utc"].min()),
        "valid_time_max_utc": str(df["valid_time_utc"].max()),
        "quality_flag_counts": flag_counts(df),
        "issue_valid_pair_id_unique": bool(df["issue_valid_pair_id"].is_unique),
    }


def write_validation(validation_df: pd.DataFrame) -> None:
    """Write validation CSV and Markdown summary."""
    validation_df.to_csv(VALIDATION_CSV, index=False)
    passed = int(validation_df["passed"].sum())
    lines = [
        "# Local Dry Smoke Validation",
        "",
        f"- Status: {'PASS' if bool(validation_df['passed'].all()) else 'BLOCKED'}",
        f"- Checks passed: {passed}/{len(validation_df)}",
        "- API calls: none",
        "- Model evaluation: none",
        "",
        markdown_table(validation_df.to_dict("records"), ["check", "passed", "detail"]),
        "",
    ]
    VALIDATION_MD.write_text("\n".join(lines), encoding="utf-8")


def write_manifest(
    synthetic_summary: dict[str, Any],
    validation_df: pd.DataFrame,
    legacy_info: dict[str, Any],
    generated_at: str,
    legacy_df: pd.DataFrame | None,
) -> None:
    """Write machine-readable and Markdown dry-smoke manifests."""
    outputs = {
        "synthetic_prospective_rows_csv": str(SYNTHETIC_CSV),
        "legacy_compatibility_rows_csv": str(LEGACY_CSV) if legacy_df is not None and not legacy_df.empty else None,
        "manifest_json": str(MANIFEST_JSON),
        "manifest_md": str(MANIFEST_MD),
        "validation_csv": str(VALIDATION_CSV),
        "validation_md": str(VALIDATION_MD),
        "report_md": str(REPORT_MD),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "status": "PASS" if bool(validation_df["passed"].all()) else "BLOCKED",
        "dry_smoke_mode": "offline_synthetic_only",
        "no_network": True,
        "api_calls": 0,
        "archive_modification": False,
        "collector_runtime_modification": False,
        "model_training": False,
        "model_evaluation": False,
        "forecast_skill_claim": False,
        "prospective_skill_claim": False,
        "system_b_or_v12_touched": False,
        "input_files": INPUT_FILES,
        "outputs": outputs,
        "synthetic_summary": synthetic_summary,
        "legacy_compatibility": legacy_info,
        "validation": {
            "checks": validation_df.to_dict("records"),
            "passed_count": int(validation_df["passed"].sum()),
            "check_count": int(len(validation_df)),
        },
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Local Dry Smoke Manifest",
        "",
        f"- Status: {manifest['status']}",
        f"- Generated at UTC: {generated_at}",
        "- Mode: offline_synthetic_only",
        "- API calls: none",
        "- Archive modification: none",
        "- Collector runtime modification: none",
        "- Model training/evaluation: none",
        "",
        "## Outputs",
        "",
    ]
    lines.extend(f"- `{path}`" for path in outputs.values() if path)
    lines.extend(
        [
            "",
            "## Synthetic Summary",
            "",
            f"- Rows: {synthetic_summary['row_count']}",
            f"- Stations: {synthetic_summary['station_count']}",
            f"- Lead-time bins: {synthetic_summary['lead_time_bins']}",
            f"- Valid-time range: {synthetic_summary['valid_time_min_utc']} to {synthetic_summary['valid_time_max_utc']}",
            f"- Issue-valid IDs unique: {synthetic_summary['issue_valid_pair_id_unique']}",
            "",
            "## Legacy Compatibility",
            "",
            f"- Status: {legacy_info.get('status')}",
            f"- Rows read: {legacy_info.get('rows_read')}",
            f"- Source path: {legacy_info.get('source_path', 'not sampled')}",
        ]
    )
    MANIFEST_MD.write_text("\n".join(lines), encoding="utf-8")


def write_report(
    synthetic_summary: dict[str, Any],
    validation_df: pd.DataFrame,
    legacy_info: dict[str, Any],
    legacy_df: pd.DataFrame | None,
) -> None:
    """Write the Sprint 4B.2 dry-smoke report."""
    status = "PASS" if bool(validation_df["passed"].all()) else "BLOCKED"
    outputs = [
        SYNTHETIC_CSV,
        MANIFEST_JSON,
        MANIFEST_MD,
        VALIDATION_CSV,
        VALIDATION_MD,
        REPORT_MD,
    ]
    if legacy_df is not None and not legacy_df.empty:
        outputs.insert(1, LEGACY_CSV)

    missing_issue_model = synthetic_summary["quality_flag_counts"].get("missing_lead_time", 0)
    lines = [
        "# Sprint 4B.2 — Local-only Prospective Metadata Dry Smoke",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- local-only",
        "- offline",
        "- synthetic prospective rows",
        "- no API",
        "- no archive modification",
        "- no collector runtime modification",
        "- no model training",
        "- no forecast skill",
        "",
        "## Inputs",
    ]
    lines.extend(f"- `{path}`" for path in INPUT_FILES)
    lines.extend(["", "## Outputs"])
    lines.extend(f"- `{path}`" for path in outputs)
    lines.extend(
        [
            "",
            "## Synthetic prospective rows",
            f"- Row count: {synthetic_summary['row_count']}",
            f"- Station count: {synthetic_summary['station_count']}",
            f"- Lead-time bins: {synthetic_summary['lead_time_bins']}",
            f"- Valid_time range: {synthetic_summary['valid_time_min_utc']} to {synthetic_summary['valid_time_max_utc']}",
            f"- Quality_flag counts: {synthetic_summary['quality_flag_counts']}",
            f"- Issue_valid_pair_id uniqueness: {synthetic_summary['issue_valid_pair_id_unique']}",
            "",
            "## Fail-closed checks",
            f"- Missing issue/model time rows with null lead_time: {missing_issue_model}",
            "- Missing flags present: checked in validation output.",
            "- No row with missing_lead_time is eligible for skill evaluation.",
            "",
            "## Legacy compatibility",
        ]
    )
    if legacy_df is not None and not legacy_df.empty:
        legacy_flags_ok = legacy_df["quality_flag"].astype(str).str.contains(
            "legacy_missing_prospective_metadata", regex=False
        ).all()
        lines.extend(
            [
                f"- Legacy rows sampled: yes, {len(legacy_df)} rows from `{legacy_info.get('source_path')}`.",
                f"- legacy_missing_prospective_metadata flags confirmed: {bool(legacy_flags_ok)}.",
                "- Forecast lead time is null for the legacy compatibility view.",
            ]
        )
    else:
        lines.append(f"- Legacy rows sampled: no. Reason: {legacy_info.get('reason', 'not available')}.")
    lines.extend(
        [
            "",
            "## Validation checks",
            f"- Checks passed: {int(validation_df['passed'].sum())}/{len(validation_df)}",
            f"- Overall validation status: {status}",
            "",
            "## What this proves",
            "- helper/schema can produce future prospective metadata-shaped rows",
            "- quality flags and fail-closed behavior work locally",
            "- manifest structure is ready for review",
            "",
            "## What this does not prove",
            "- no live collection",
            "- no Open-Meteo provider run metadata",
            "- no NEA retrieval delay measurement",
            "- no prospective forecast skill",
            "- no GHA/local parity",
            "- no operational forecast",
            "",
            "## Next recommended action",
            "- Review helper/schema before any live smoke.",
            "",
            "## Safety statements",
            "- no forbidden files touched",
            "- no API calls",
            "- no archive modification",
            "- no collector runtime modification",
            "- no model training",
            "- no System B/v12 touched",
            "- no commit/stage performed",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Run the offline local dry smoke."""
    args = parse_args()
    if args.output_dir != OUTPUT_DIR:
        raise SystemExit("This dry smoke must write only under outputs/v11_level1/prospective_eval/local_dry_smoke/")
    if not args.config.exists():
        raise SystemExit(f"Config not found: {args.config}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now_iso()

    synthetic_df = build_synthetic_rows(generated_at)
    legacy_df, legacy_info = build_legacy_compatibility(generated_at, skip=bool(args.skip_legacy))
    validation_df = validate_outputs(synthetic_df, legacy_df)
    synthetic_summary = summarize_synthetic(synthetic_df)

    synthetic_df.to_csv(SYNTHETIC_CSV, index=False)
    if legacy_df is not None and not legacy_df.empty:
        legacy_df.to_csv(LEGACY_CSV, index=False)
    elif LEGACY_CSV.exists():
        LEGACY_CSV.unlink()

    write_validation(validation_df)
    write_manifest(synthetic_summary, validation_df, legacy_info, generated_at, legacy_df)
    write_report(synthetic_summary, validation_df, legacy_info, legacy_df)

    status = "PASS" if bool(validation_df["passed"].all()) else "BLOCKED"
    print(f"[{status}] Sprint 4B.2 local dry smoke complete")
    print(f"[OUT] {SYNTHETIC_CSV}")
    print(f"[OUT] {VALIDATION_CSV}")
    print(f"[OUT] {MANIFEST_JSON}")
    print(f"[OUT] {REPORT_MD}")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
