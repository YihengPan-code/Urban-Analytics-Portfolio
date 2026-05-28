"""Estimate B8.7b future runtime/storage from prior compact logs.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml, optional local F5
    run-log CSV, and F5 postrun validation metadata.
Outputs:
    b87b_runtime_storage_estimate.csv.
Saved metrics:
    Prior log availability, observed mean/median duration when available,
    reliability caveat, expected output count, Tmrt-only storage estimate from
    prior file-size metadata, and storage caveats. This script reads compact CSV
    logs only; it does not open raster outputs or run QGIS/SOLWEIG.
"""

from __future__ import annotations

import argparse
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean
from v12_b87b_input_inventory import config_list, load_config, out_path, path_exists_metadata
from v12_b87b_input_inventory import read_csv_rows, write_csv_rows


@dataclass(frozen=True)
class RuntimeStorageEstimateResult:
    """B8.7b runtime/storage estimate result."""

    status: str
    duration_headline: str
    storage_headline: str


def numeric(value: Any) -> float | None:
    """Parse a float when possible."""
    try:
        return float(clean(value))
    except ValueError:
        return None


def add_metric(
    rows: list[dict[str, Any]],
    metric: str,
    value: Any,
    units: str,
    source: str,
    status: str,
    caveat: str,
) -> None:
    """Append one runtime/storage metric row."""
    rows.append(
        {
            "metric": metric,
            "value": value,
            "units": units,
            "source": source,
            "status": status,
            "reliability_caveat": caveat,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )


def run(config_path: Path = DEFAULT_CONFIG) -> RuntimeStorageEstimateResult:
    """Create runtime and storage estimates from prior metadata."""
    config = load_config(config_path)
    rows: list[dict[str, Any]] = []
    duration_values: list[float] = []
    log_source = "none"
    for candidate in config_list(config, "local_run_log_candidates"):
        exists, _ = path_exists_metadata(candidate)
        if exists != "yes":
            continue
        log_rows = read_csv_rows(candidate)
        duration_values = [
            value
            for value in (numeric(row.get("duration_seconds")) for row in log_rows)
            if value is not None and value >= 0
        ]
        log_source = candidate
        add_metric(rows, "prior_f5_local_run_log_found", "yes", "boolean", candidate, "PASS", "local_audit_only")
        add_metric(rows, "prior_f5_local_run_log_rows", len(log_rows), "rows", candidate, "PASS", "local_audit_only")
        break
    if not duration_values:
        add_metric(rows, "prior_f5_local_run_log_found", "no", "boolean", "local_run_log_candidates", "WARN", "duration unknown")
        duration_status = "UNKNOWN"
        duration_headline = "prior duration log unavailable; runtime unknown"
    else:
        mean_duration = statistics.fmean(duration_values)
        median_duration = statistics.median(duration_values)
        reliability = (
            "UNRELIABLE_LOCAL_COPY_OR_CACHE_TIMING"
            if mean_duration < 5.0
            else "USABLE_PRIOR_WALLTIME_SAMPLE"
        )
        status = "WARN" if reliability.startswith("UNRELIABLE") else "PASS"
        add_metric(rows, "observed_duration_rows", len(duration_values), "runs", log_source, status, reliability)
        add_metric(rows, "observed_mean_duration_seconds", f"{mean_duration:.3f}", "seconds/run", log_source, status, reliability)
        add_metric(rows, "observed_median_duration_seconds", f"{median_duration:.3f}", "seconds/run", log_source, status, reliability)
        if status == "PASS":
            estimated = mean_duration * int(config["planned_additional_solweig_run_count"])
            add_metric(rows, "estimated_duration_for_3000_runs_seconds", f"{estimated:.1f}", "seconds", log_source, "PASS", reliability)
            duration_headline = f"mean prior duration {mean_duration:.2f}s/run; estimate {estimated / 3600:.2f}h"
            duration_status = "PASS"
        else:
            add_metric(
                rows,
                "estimated_duration_for_3000_runs_seconds",
                "unknown_due_unreliable_prior_log",
                "seconds",
                log_source,
                "WARN",
                reliability,
            )
            duration_headline = "prior F5 log is subsecond/local-copy-like; runtime estimate remains unknown"
            duration_status = "WARN"

    postrun = read_csv_rows(config["f5_postrun_validation_path"])
    sizes = [
        value
        for value in (numeric(row.get("file_size_bytes")) for row in postrun)
        if value is not None and value > 0
    ]
    planned_runs = int(config["planned_additional_solweig_run_count"])
    add_metric(rows, "expected_output_count", planned_runs, "Tmrt_average.tif files", "configured planned run count", "PASS", "Tmrt-only count; full SOLWEIG directories may include more files")
    if sizes:
        mean_size = statistics.fmean(sizes)
        estimated_bytes = mean_size * planned_runs
        add_metric(rows, "prior_mean_tmrt_file_size_bytes", f"{mean_size:.1f}", "bytes/file", config["f5_postrun_validation_path"], "PASS", "metadata from compact postrun CSV; raster not opened")
        add_metric(rows, "estimated_tmrt_only_storage_mb", f"{estimated_bytes / (1024 * 1024):.2f}", "MB", config["f5_postrun_validation_path"], "WARN", "Tmrt_average.tif only; raw SOLWEIG output directory storage may be larger")
        storage_headline = f"Tmrt-only estimate about {estimated_bytes / (1024 * 1024):.2f} MB for {planned_runs} outputs"
    else:
        add_metric(rows, "estimated_tmrt_only_storage_mb", "unknown", "MB", config["f5_postrun_validation_path"], "WARN", "file-size metadata unavailable")
        storage_headline = "storage estimate unknown"

    add_metric(rows, "storage_caveat", "raw SOLWEIG output directories may exceed Tmrt-only estimate", "text", "B87B", "WARN", "do not commit raw outputs or rasters")

    write_csv_rows(
        out_path(config, "b87b_runtime_storage_estimate.csv"),
        rows,
        ["metric", "value", "units", "source", "status", "reliability_caveat", "claim_boundary"],
    )
    overall = "PASS" if duration_status == "PASS" else "WARN"
    return RuntimeStorageEstimateResult(status=overall, duration_headline=duration_headline, storage_headline=storage_headline)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Estimate B8.7b future runtime/storage from prior compact logs. "
            "Does not open raster outputs or run QGIS/SOLWEIG."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
