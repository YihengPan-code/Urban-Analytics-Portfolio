#!/usr/bin/env python
"""Helpers for OpenHeat v1.1 System A Level 1 prospective metadata.

Inputs
------
- Row dictionaries or pandas DataFrames from future collector outputs.
- A metadata context dictionary with collector/run/source fields.

Outputs
-------
- Additive prospective metadata columns for future forecast/official pair rows.
- Deterministic ``issue_valid_pair_id`` values.
- Row-level quality flags for strict prospective and legacy modes.

Saved metrics
-------------
This helper module does not write files. Diagnostic callers should persist
machine-readable CSV/JSON plus a short Markdown summary.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Any, Mapping

import pandas as pd


PROSPECTIVE_METADATA_FIELDS: tuple[str, ...] = (
    "issue_valid_pair_id",
    "valid_time_utc",
    "valid_time_sgt",
    "forecast_issue_time_utc",
    "model_run_time_utc",
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
    "official_observed_at_utc",
    "official_retrieved_at_utc",
    "official_wbgt_publication_delay_minutes",
    "collector_run_id",
    "archive_run_id",
    "gha_run_id",
    "scheduled_at_utc",
    "started_at_utc",
    "completed_at_utc",
    "source_lane",
    "row_added_at_utc",
    "quality_flag",
)


QUALITY_FLAGS: tuple[str, ...] = (
    "ok_prospective_metadata",
    "missing_model_run_time",
    "missing_forecast_issue_time",
    "missing_forecast_retrieved_at",
    "missing_official_retrieved_at",
    "missing_lead_time",
    "legacy_missing_prospective_metadata",
)


def utc_now_iso() -> str:
    """Return the current UTC time as a second-resolution ISO string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def normalize_utc_timestamp(value: Any) -> str | None:
    """Normalize a timestamp-like value to UTC ISO format, or return None.

    Naive timestamps are interpreted as UTC because prospective metadata fields
    ending in ``_utc`` must not silently inherit a local timezone.
    """
    if _is_missing(value):
        return None
    try:
        ts = pd.to_datetime(value, errors="coerce", utc=True)
    except Exception:
        return None
    if pd.isna(ts):
        return None
    if isinstance(ts, pd.Series):
        if ts.empty or pd.isna(ts.iloc[0]):
            return None
        ts = ts.iloc[0]
    py_dt = ts.to_pydatetime()
    return py_dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hours_between(later_utc: Any, earlier_utc: Any) -> float | None:
    later = normalize_utc_timestamp(later_utc)
    earlier = normalize_utc_timestamp(earlier_utc)
    if later is None or earlier is None:
        return None
    later_dt = pd.to_datetime(later, utc=True)
    earlier_dt = pd.to_datetime(earlier, utc=True)
    return round(float((later_dt - earlier_dt).total_seconds() / 3600.0), 6)


def compute_lead_time_hours(
    valid_time_utc: Any,
    forecast_issue_time_utc: Any = None,
    model_run_time_utc: Any = None,
) -> float | None:
    """Compute lead time from provider model/run time or reliable issue time.

    The provider model run time is preferred. If it is missing, a caller may
    provide a semantically reliable forecast issue time. Retrieval time is not
    accepted as a substitute issue time.
    """
    reference_time = model_run_time_utc if normalize_utc_timestamp(model_run_time_utc) else forecast_issue_time_utc
    return _hours_between(valid_time_utc, reference_time)


def compute_forecast_age_hours(
    forecast_retrieved_at_utc: Any,
    model_run_time_utc: Any = None,
) -> float | None:
    """Compute forecast age as retrieval time minus provider model run time."""
    if normalize_utc_timestamp(model_run_time_utc) is None:
        return None
    return _hours_between(forecast_retrieved_at_utc, model_run_time_utc)


def build_issue_valid_pair_id(
    station_id: Any,
    valid_time_utc: Any,
    forecast_provider: Any,
    forecast_api_product: Any,
    forecast_issue_time_utc: Any = None,
    model_run_time_utc: Any = None,
    forecast_retrieved_at_utc: Any = None,
    source_lane: Any = None,
) -> str:
    """Build a deterministic short id for one provider/source issue-valid row.

    Missing issue/model time is represented explicitly in the hash input so
    legacy or incomplete prospective rows still receive stable row identifiers.
    Quality flags are assigned by ``validate_prospective_metadata_row``.
    """
    issue_or_model = normalize_utc_timestamp(model_run_time_utc) or normalize_utc_timestamp(forecast_issue_time_utc)
    parts = [
        str(station_id or "unknown_station"),
        normalize_utc_timestamp(valid_time_utc) or "missing_valid_time_utc",
        str(forecast_provider or "unknown_provider"),
        str(forecast_api_product or "unknown_product"),
        issue_or_model or "missing_issue_or_model_time",
        normalize_utc_timestamp(forecast_retrieved_at_utc) or "missing_forecast_retrieval_time",
        str(source_lane or "unknown_lane"),
    ]
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"ivp_{digest}"


def _first_present(row: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row and not _is_missing(row[name]):
            return row[name]
    return None


def validate_prospective_metadata_row(row: Mapping[str, Any], mode: str = "strict") -> list[str]:
    """Return row-level prospective metadata quality flags.

    ``strict`` requires prospective timing fields. ``legacy`` marks historical
    rows as missing prospective metadata without making them look evaluable.
    """
    if mode not in {"strict", "legacy"}:
        raise ValueError("mode must be 'strict' or 'legacy'")

    flags: list[str] = []
    model_run = normalize_utc_timestamp(row.get("model_run_time_utc"))
    issue_time = normalize_utc_timestamp(row.get("forecast_issue_time_utc"))
    forecast_retrieved = normalize_utc_timestamp(row.get("forecast_retrieved_at_utc"))
    official_retrieved = normalize_utc_timestamp(row.get("official_retrieved_at_utc"))
    lead_time = row.get("forecast_lead_time_hours")

    if model_run is None:
        flags.append("missing_model_run_time")
    if issue_time is None:
        flags.append("missing_forecast_issue_time")
    if forecast_retrieved is None:
        flags.append("missing_forecast_retrieved_at")
    if official_retrieved is None:
        flags.append("missing_official_retrieved_at")
    if _is_missing(lead_time):
        flags.append("missing_lead_time")

    if mode == "legacy":
        flags.append("legacy_missing_prospective_metadata")

    blocking = {
        "missing_forecast_retrieved_at",
        "missing_official_retrieved_at",
        "missing_lead_time",
    }
    if not any(flag in blocking for flag in flags) and (model_run is not None or issue_time is not None):
        flags.insert(0, "ok_prospective_metadata")
    return flags


def _attach_to_mapping(row: Mapping[str, Any], metadata_context: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    context = dict(metadata_context)

    valid_time_utc = normalize_utc_timestamp(
        _first_present(out, ("valid_time_utc", "timestamp_utc", "official_observed_at_utc"))
        or context.get("valid_time_utc")
    )
    forecast_issue_time = normalize_utc_timestamp(
        _first_present(out, ("forecast_issue_time_utc",))
        or context.get("forecast_issue_time_utc")
    )
    model_run_time = normalize_utc_timestamp(
        _first_present(out, ("model_run_time_utc",))
        or context.get("model_run_time_utc")
    )
    forecast_retrieved = normalize_utc_timestamp(
        _first_present(out, ("forecast_retrieved_at_utc", "fetch_timestamp_utc_om"))
        or context.get("forecast_retrieved_at_utc")
    )
    official_retrieved = normalize_utc_timestamp(
        _first_present(out, ("official_retrieved_at_utc", "fetch_timestamp_utc"))
        or context.get("official_retrieved_at_utc")
    )
    official_observed = normalize_utc_timestamp(
        _first_present(out, ("official_observed_at_utc", "timestamp_utc"))
        or context.get("official_observed_at_utc")
        or valid_time_utc
    )

    defaults = {
        "valid_time_utc": valid_time_utc,
        "valid_time_sgt": _first_present(out, ("valid_time_sgt", "timestamp_sgt")) or context.get("valid_time_sgt"),
        "forecast_issue_time_utc": forecast_issue_time,
        "model_run_time_utc": model_run_time,
        "forecast_requested_at_utc": normalize_utc_timestamp(context.get("forecast_requested_at_utc")),
        "forecast_retrieved_at_utc": forecast_retrieved,
        "forecast_provider": _first_present(out, ("forecast_provider",)) or context.get("forecast_provider"),
        "forecast_model": _first_present(out, ("forecast_model",)) or context.get("forecast_model"),
        "forecast_endpoint": _first_present(out, ("forecast_endpoint", "endpoint_url")) or context.get("forecast_endpoint"),
        "forecast_api_product": _first_present(out, ("forecast_api_product",)) or context.get("forecast_api_product"),
        "openmeteo_grid_lat": _first_present(out, ("openmeteo_grid_lat",)) or context.get("openmeteo_grid_lat"),
        "openmeteo_grid_lon": _first_present(out, ("openmeteo_grid_lon",)) or context.get("openmeteo_grid_lon"),
        "official_observed_at_utc": official_observed,
        "official_retrieved_at_utc": official_retrieved,
        "collector_run_id": _first_present(out, ("collector_run_id",)) or context.get("collector_run_id"),
        "archive_run_id": _first_present(out, ("archive_run_id",)) or context.get("archive_run_id"),
        "gha_run_id": _first_present(out, ("gha_run_id",)) or context.get("gha_run_id"),
        "scheduled_at_utc": normalize_utc_timestamp(context.get("scheduled_at_utc")),
        "started_at_utc": normalize_utc_timestamp(context.get("started_at_utc")),
        "completed_at_utc": normalize_utc_timestamp(context.get("completed_at_utc")),
        "source_lane": _first_present(out, ("source_lane",)) or context.get("source_lane"),
        "row_added_at_utc": normalize_utc_timestamp(_first_present(out, ("row_added_at_utc",)) or context.get("row_added_at_utc") or utc_now_iso()),
    }

    lead_time = compute_lead_time_hours(valid_time_utc, forecast_issue_time, model_run_time)
    forecast_age = compute_forecast_age_hours(forecast_retrieved, model_run_time)
    defaults["forecast_lead_time_hours"] = lead_time
    defaults["forecast_age_hours"] = forecast_age
    defaults["official_wbgt_publication_delay_minutes"] = None
    delay_hours = _hours_between(official_retrieved, official_observed)
    if delay_hours is not None:
        defaults["official_wbgt_publication_delay_minutes"] = round(delay_hours * 60.0, 3)

    for field in PROSPECTIVE_METADATA_FIELDS:
        if field != "quality_flag":
            out[field] = out.get(field) if not _is_missing(out.get(field)) else defaults.get(field)

    out["issue_valid_pair_id"] = build_issue_valid_pair_id(
        station_id=out.get("station_id"),
        valid_time_utc=out.get("valid_time_utc"),
        forecast_provider=out.get("forecast_provider"),
        forecast_api_product=out.get("forecast_api_product"),
        forecast_issue_time_utc=out.get("forecast_issue_time_utc"),
        model_run_time_utc=out.get("model_run_time_utc"),
        forecast_retrieved_at_utc=out.get("forecast_retrieved_at_utc"),
        source_lane=out.get("source_lane"),
    )
    flags = validate_prospective_metadata_row(out, mode=str(context.get("mode", "strict")))
    out["quality_flag"] = "|".join(flags)
    return out


def attach_prospective_metadata(row_or_df: Any, metadata_context: Mapping[str, Any]) -> Any:
    """Add prospective schema fields without removing existing fields.

    The input may be a row mapping or a pandas DataFrame. DataFrame inputs are
    processed row-wise to preserve per-row valid times and station ids.
    """
    if isinstance(row_or_df, pd.DataFrame):
        rows = [_attach_to_mapping(row, metadata_context) for row in row_or_df.to_dict("records")]
        return pd.DataFrame(rows)
    if isinstance(row_or_df, Mapping):
        return _attach_to_mapping(row_or_df, metadata_context)
    raise TypeError("row_or_df must be a mapping or pandas DataFrame")
