#!/usr/bin/env python
"""Synthetic smoke tests for v1.1 prospective metadata helpers.

Inputs
------
Synthetic in-memory rows only. This script performs no API calls and reads no
archive data.

Outputs
-------
- ``outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv``
- ``outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.md``

Saved metrics
-------------
The CSV records one row per smoke assertion with pass/fail status and details.
The Markdown summary records the same assertions and the expected schema fields.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from v11_prospective_metadata_helpers import (
    PROSPECTIVE_METADATA_FIELDS,
    attach_prospective_metadata,
    build_issue_valid_pair_id,
    compute_lead_time_hours,
)


OUT_DIR = Path("outputs/v11_level1/prospective_eval/metadata_patch")
OUT_CSV = OUT_DIR / "prospective_metadata_schema_smoke.csv"
OUT_MD = OUT_DIR / "prospective_metadata_schema_smoke.md"


def record(results: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    results.append({"test": name, "passed": bool(passed), "detail": detail})


def main() -> None:
    results: list[dict[str, Any]] = []

    row_id = build_issue_valid_pair_id(
        station_id="S001",
        valid_time_utc="2026-05-25T12:00:00Z",
        forecast_provider="open-meteo",
        forecast_api_product="forecast_api",
        forecast_issue_time_utc=None,
        model_run_time_utc=None,
        forecast_retrieved_at_utc="2026-05-25T00:05:00Z",
        source_lane="local_loop",
    )
    record(results, "helper creates issue_valid_pair_id", row_id.startswith("ivp_") and len(row_id) == 20, row_id)

    missing_lead = compute_lead_time_hours("2026-05-25T12:00:00Z")
    record(results, "lead_time is None when issue/model time missing", missing_lead is None, str(missing_lead))

    lead = compute_lead_time_hours(
        valid_time_utc="2026-05-25T12:00:00Z",
        model_run_time_utc="2026-05-25T00:00:00Z",
    )
    record(results, "lead_time computed correctly when model_run_time exists", lead == 12.0, str(lead))

    legacy = attach_prospective_metadata(
        {"station_id": "S001", "timestamp_utc": "2026-05-25T12:00:00Z"},
        {
            "mode": "legacy",
            "forecast_provider": "open-meteo",
            "forecast_api_product": "forecast_api",
            "source_lane": "local_loop",
        },
    )
    legacy_flags = str(legacy["quality_flag"])
    record(
        results,
        "legacy row gets legacy/missing metadata flags",
        "legacy_missing_prospective_metadata" in legacy_flags and "missing_lead_time" in legacy_flags,
        legacy_flags,
    )

    strict = attach_prospective_metadata(
        {
            "station_id": "S001",
            "timestamp_utc": "2026-05-25T12:00:00Z",
            "timestamp_sgt": "2026-05-25 20:00:00+08:00",
            "official_wbgt_c": 31.2,
        },
        {
            "mode": "strict",
            "forecast_provider": "open-meteo",
            "forecast_api_product": "forecast_api",
            "forecast_issue_time_utc": "2026-05-25T00:00:00Z",
            "model_run_time_utc": "2026-05-25T00:00:00Z",
            "forecast_requested_at_utc": "2026-05-25T00:04:00Z",
            "forecast_retrieved_at_utc": "2026-05-25T00:05:00Z",
            "official_retrieved_at_utc": "2026-05-25T12:10:00Z",
            "collector_run_id": "collector_smoke",
            "source_lane": "local_loop",
        },
    )
    strict_flags = str(strict["quality_flag"])
    record(
        results,
        "strict prospective row passes required metadata",
        strict_flags == "ok_prospective_metadata" and strict["forecast_lead_time_hours"] == 12.0,
        strict_flags,
    )

    frame = attach_prospective_metadata(pd.DataFrame([strict]), {"mode": "strict"})
    missing_cols = [col for col in PROSPECTIVE_METADATA_FIELDS if col not in frame.columns]
    record(results, "output columns match expected schema", not missing_cols, ",".join(missing_cols) or "all present")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result_df = pd.DataFrame(results)
    result_df.to_csv(OUT_CSV, index=False)

    passed_count = int(result_df["passed"].sum())
    md_df = result_df.copy()
    md_df["detail"] = md_df["detail"].astype(str).str.replace("|", r"\|", regex=False)
    lines = [
        "# Prospective Metadata Schema Smoke",
        "",
        f"- Tests passed: {passed_count}/{len(result_df)}",
        f"- Output CSV: `{OUT_CSV}`",
        f"- API calls: none",
        f"- Archive reads/writes: none",
        "",
        "## Results",
        "",
        md_df.to_markdown(index=False),
        "",
        "## Expected Prospective Metadata Fields",
        "",
    ]
    lines.extend(f"- `{field}`" for field in PROSPECTIVE_METADATA_FIELDS)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    if not bool(result_df["passed"].all()):
        raise SystemExit(1)

    print(f"[OK] prospective metadata schema smoke passed: {OUT_CSV}")
    print(f"[OK] summary: {OUT_MD}")


if __name__ == "__main__":
    main()
