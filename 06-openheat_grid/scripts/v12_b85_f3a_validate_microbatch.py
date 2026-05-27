"""Validate the B8.5-F3a human-controlled QGIS/SOLWEIG micro-batch.

Inputs:
    configs/v12/systemb_b85_f3a_microbatch_execution.yaml
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_microbatch_manifest.csv
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_pre_execution_asset_check.csv
    Optional local-only run log:
    C:/OpenHeat-local/solweig/b85_f3a_microbatch/run_logs/b85_f3a_microbatch_qgis_run_log.csv

Outputs:
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_postrun_validation.csv
    outputs/v12_surrogate/b8_5_f3a_microbatch/B8_5_F3A_STATUS.md

Saved metrics:
    Pre-execution ready count, local run-log existence, per-run run-log status,
    expected local Tmrt path existence, expected local Tmrt file size, postrun
    validation status, and final decision status.

This validator does not run QGIS, run SOLWEIG, open raster contents, copy
rasters, copy/open svfs.zip, create AOI-wide predictions, compute local WBGT,
create hazard_score/risk_score outputs, create System A/B coupling outputs,
stage files, or commit files. It only checks metadata, local run-log rows, and
file existence/size for expected local outputs.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from v12_b85_f3a_prepare_microbatch import (
    BLOCKED,
    FAILED,
    NO,
    NOT_RUN_YET,
    PASS,
    READY_FOR_HUMAN_MICROBATCH,
    ROOT,
    YES,
    clean,
    output_paths,
    read_config,
    read_csv_rows,
    rel,
    repo_path,
    write_csv_rows,
    write_status_report,
)


DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f3a_microbatch_execution.yaml"
MICRO_BATCH_EXECUTED_PASS = "MICRO_BATCH_EXECUTED_PASS"
MICRO_BATCH_EXECUTED_PARTIAL = "MICRO_BATCH_EXECUTED_PARTIAL"


def is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is below parent without requiring Python 3.9 helpers."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def git_status_short() -> list[str]:
    """Return short Git status lines under the current OpenHeat subdirectory."""
    completed = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]


def changed_forbidden_paths(status_lines: list[str]) -> list[str]:
    """Identify forbidden changed files from git status output."""
    forbidden_fragments = [
        "data/solweig/",
        "data/rasters/",
        "data/archive/",
        "svfs.zip",
        "hourly_grid_heatstress_forecast",
    ]
    forbidden_suffixes = (".tif", ".tiff")
    hits: list[str] = []
    for line in status_lines:
        path = line[3:].replace("\\", "/")
        lower = path.lower()
        if lower.endswith(forbidden_suffixes) or any(fragment in lower for fragment in forbidden_fragments):
            hits.append(path)
    return hits


def precheck_ready_count(precheck_rows: list[dict[str, str]]) -> int:
    """Count rows that passed the pre-execution gate."""
    return sum(
        1
        for row in precheck_rows
        if clean(row.get("run_ready")).lower() == YES and clean(row.get("pre_execution_status")).upper() == PASS
    )


def expected_path_allowed(config: dict[str, Any], path: Path) -> bool:
    """Return whether an expected output path stays under the configured local root."""
    allowed_root = Path(str(config["microbatch"]["local_solweig_output_root"]))
    return is_relative_to(path, allowed_root)


def not_run_yet_rows(manifest_rows: list[dict[str, str]], log_path: Path) -> list[dict[str, str]]:
    """Build postrun rows when the local human run log does not exist yet."""
    rows: list[dict[str, str]] = []
    for row in manifest_rows:
        rows.append(
            {
                "run_id": row["run_id"],
                "phase": "PREPARED",
                "postrun_status": NOT_RUN_YET,
                "run_log_exists": NO,
                "run_log_status": "",
                "expected_tmrt_path": row["expected_tmrt_path"],
                "file_exists": "",
                "file_size_bytes": "",
                "validation_status": NOT_RUN_YET,
                "notes": f"No local run log found at {log_path.as_posix()}; prepared package has not been manually executed yet.",
            }
        )
    return rows


def blocked_rows(manifest_rows: list[dict[str, str]], reason: str) -> list[dict[str, str]]:
    """Build postrun rows when pre-execution readiness blocks execution."""
    rows: list[dict[str, str]] = []
    for row in manifest_rows:
        rows.append(
            {
                "run_id": row["run_id"],
                "phase": "PREPARED",
                "postrun_status": BLOCKED,
                "run_log_exists": "",
                "run_log_status": "",
                "expected_tmrt_path": row["expected_tmrt_path"],
                "file_exists": "",
                "file_size_bytes": "",
                "validation_status": BLOCKED,
                "notes": reason,
            }
        )
    return rows


def validate_executed_rows(
    config: dict[str, Any],
    manifest_rows: list[dict[str, str]],
    log_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], bool]:
    """Validate a local run log and expected output file metadata."""
    log_by_run_id = {row.get("run_id", ""): row for row in log_rows}
    extra_run_ids = sorted(set(log_by_run_id) - {row["run_id"] for row in manifest_rows})
    rows: list[dict[str, str]] = []
    all_pass = len(log_rows) == len(manifest_rows) and not extra_run_ids
    for manifest_row in manifest_rows:
        run_id = manifest_row["run_id"]
        log_row = log_by_run_id.get(run_id, {})
        log_status = clean(log_row.get("status")).lower() if log_row else "missing"
        expected_tmrt = Path(manifest_row["expected_tmrt_path"])
        path_allowed = expected_path_allowed(config, expected_tmrt)
        exists = expected_tmrt.exists() if path_allowed else False
        file_size = expected_tmrt.stat().st_size if exists else 0
        row_pass = log_status == "success" and exists and file_size > 0 and path_allowed
        all_pass = all_pass and row_pass
        notes: list[str] = []
        if not path_allowed:
            notes.append("expected_tmrt_path_outside_allowed_local_output_root")
        if log_status != "success":
            notes.append(f"run_log_status={log_status}")
        if not exists:
            notes.append("expected_tmrt_missing")
        elif file_size <= 0:
            notes.append("expected_tmrt_zero_size")
        if extra_run_ids:
            notes.append(f"extra_run_ids_in_log={';'.join(extra_run_ids)}")
        rows.append(
            {
                "run_id": run_id,
                "phase": "EXECUTED",
                "postrun_status": "PASS" if row_pass else "FAIL",
                "run_log_exists": YES,
                "run_log_status": log_status,
                "expected_tmrt_path": expected_tmrt.as_posix(),
                "file_exists": YES if exists else NO,
                "file_size_bytes": str(file_size) if exists else "0",
                "validation_status": PASS if row_pass else FAILED,
                "notes": "none" if not notes else "; ".join(notes),
            }
        )
    return rows, all_pass


def postrun_status_from_rows(rows: list[dict[str, str]], decision_status: str) -> str:
    """Return a compact postrun status for reports."""
    if decision_status == READY_FOR_HUMAN_MICROBATCH:
        return NOT_RUN_YET
    if decision_status == BLOCKED:
        return BLOCKED
    passed = sum(1 for row in rows if row.get("validation_status") == PASS)
    total = len(rows)
    return f"{passed}/{total}_EXECUTED_OUTPUTS_VALID"


def validate(config_path: Path) -> int:
    """Validate the prepared micro-batch and optional human run log."""
    config = read_config(repo_path(config_path))
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    precheck_rows = read_csv_rows(repo_path(outputs["pre_execution_asset_check"]))
    expected_runs = int(config["microbatch"]["expected_run_count"])
    ready_count = precheck_ready_count(precheck_rows)
    local_log_path = Path(str(config["microbatch"]["local_run_log_path"]))
    files_created = output_paths(config)
    selected_cell = manifest_rows[0]["cell_id"] if manifest_rows else ""

    status_lines = git_status_short()
    forbidden_hits = changed_forbidden_paths(status_lines)
    if forbidden_hits:
        postrun_rows = blocked_rows(manifest_rows, "Forbidden changed files detected: " + "; ".join(forbidden_hits))
        decision_status = BLOCKED
        notes = "Forbidden changed files detected."
        exit_code = 2
    elif len(manifest_rows) != expected_runs:
        postrun_rows = blocked_rows(manifest_rows, f"Manifest row count {len(manifest_rows)} != expected {expected_runs}.")
        decision_status = BLOCKED
        notes = "Manifest count mismatch."
        exit_code = 2
    elif ready_count != expected_runs:
        postrun_rows = blocked_rows(
            manifest_rows,
            f"Pre-execution ready count {ready_count}/{expected_runs}; human micro-batch remains blocked.",
        )
        decision_status = BLOCKED
        notes = "Pre-execution checks did not pass."
        exit_code = 2
    elif not local_log_path.exists():
        postrun_rows = not_run_yet_rows(manifest_rows, local_log_path)
        decision_status = READY_FOR_HUMAN_MICROBATCH
        notes = "Prepared only; no local human QGIS run log exists yet."
        exit_code = 0
    else:
        log_rows = read_csv_rows(local_log_path)
        postrun_rows, all_pass = validate_executed_rows(config, manifest_rows, log_rows)
        decision_status = MICRO_BATCH_EXECUTED_PASS if all_pass else MICRO_BATCH_EXECUTED_PARTIAL
        notes = "Human run log found and validated without opening raster contents."
        exit_code = 0 if all_pass else 2

    write_csv_rows(
        repo_path(outputs["postrun_validation"]),
        postrun_rows,
        [
            "run_id",
            "phase",
            "postrun_status",
            "run_log_exists",
            "run_log_status",
            "expected_tmrt_path",
            "file_exists",
            "file_size_bytes",
            "validation_status",
            "notes",
        ],
    )
    compact_postrun_status = postrun_status_from_rows(postrun_rows, decision_status)
    write_status_report(
        repo_path(outputs["status"]),
        config,
        decision_status,
        selected_cell,
        len(manifest_rows),
        ready_count,
        compact_postrun_status,
        files_created,
        notes,
    )

    print(f"Status: {decision_status}")
    print(f"Micro-batch run count: {len(manifest_rows)}")
    print(f"Pre-execution ready count: {ready_count}")
    print(f"Postrun status: {compact_postrun_status}")
    print(f"Local run log path expected: {local_log_path.as_posix()}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print(f"Forbidden files touched: {'none' if not forbidden_hits else '; '.join(forbidden_hits)}")
    return exit_code


def main() -> int:
    """Parse CLI arguments and validate the F3a micro-batch."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate the B8.5-F3a prepared micro-batch and optional local-only QGIS run log. "
            "Does not run QGIS/SOLWEIG or open raster contents."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F3a YAML config path.")
    args = parser.parse_args()
    try:
        return validate(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
