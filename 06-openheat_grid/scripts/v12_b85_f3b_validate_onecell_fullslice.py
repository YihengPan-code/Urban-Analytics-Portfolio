"""Validate the B8.5-F3b human-controlled one-cell full-slice run.

Inputs:
    configs/v12/systemb_b85_f3b_onecell_fullslice.yaml
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_onecell_manifest.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_pre_execution_asset_check.csv
    Optional local-only run log:
    C:/OpenHeat-local/solweig/b85_f3b_onecell/run_logs/b85_f3b_onecell_qgis_run_log.csv

Outputs:
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_postrun_validation.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/B8_5_F3B_STATUS.md

Saved metrics:
    Manifest count, pre-execution ready count, run-log existence, per-run
    run-log status, expected Tmrt_average.tif existence and file size, compact
    postrun status, and decision status.

This validator does not run QGIS, run SOLWEIG, open raster contents, copy
rasters, copy/open svfs.zip, create AOI-wide predictions, compute local WBGT,
create hazard_score/risk_score outputs, create System A/B coupling outputs,
stage, or commit. It only checks metadata, local run-log rows, and local file
existence/size for expected outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

from v12_b85_f3b_prepare_onecell_fullslice import (
    BLOCKED_POSTRUN,
    BLOCKED_PRECHECK,
    FAIL,
    FAILED,
    NO,
    NOT_RUN_YET,
    ONECELL_SLICE_EXECUTED_PARTIAL,
    PASS,
    READY_FOR_HUMAN_ONECELL_SLICE,
    ROOT,
    YES,
    all_lane_paths,
    changed_forbidden_paths,
    clean,
    expected_keys,
    expected_run_count,
    git_status_short,
    is_relative_to,
    onecell,
    path_outside_git_and_under_local,
    postrun_fieldnames,
    read_config,
    read_csv_rows,
    rel,
    repo_path,
    row_key,
    write_csv_rows,
    write_status_report,
)


DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f3b_onecell_fullslice.yaml"
ONECELL_SLICE_POSTRUN_PASS_RASTER_QA_PENDING = "ONECELL_SLICE_POSTRUN_PASS_RASTER_QA_PENDING"


def precheck_ready_count(precheck_rows: Sequence[dict[str, str]]) -> int:
    """Count rows that passed the pre-execution gate."""
    return sum(
        1
        for row in precheck_rows
        if clean(row.get("run_ready")).lower() == YES and clean(row.get("pre_execution_status")).upper() == PASS
    )


def validate_manifest_scope(config: dict[str, Any], rows: Sequence[dict[str, str]]) -> list[str]:
    """Return manifest scope problems without touching raster contents."""
    notes: list[str] = []
    expected_count = int(onecell(config)["expected_run_count"])
    if len(rows) != expected_count:
        notes.append(f"manifest_row_count={len(rows)} expected={expected_count}")
    observed_keys = [row_key(row) for row in rows]
    required_keys = expected_keys(config)
    missing = [str(key) for key in required_keys if key not in observed_keys]
    extra = [str(key) for key in observed_keys if key not in required_keys]
    if missing:
        notes.append("missing_expected_keys=" + "; ".join(missing))
    if extra:
        notes.append("extra_manifest_keys=" + "; ".join(extra))
    for row in rows:
        tmrt_path = Path(row.get("expected_tmrt_path", ""))
        if not path_outside_git_and_under_local(config, tmrt_path):
            notes.append(f"expected_tmrt_path_not_local_only={row.get('run_id')}")
        expected_group = str(row.get("expected_output_group", ""))
        if expected_group.startswith("b85_f3a"):
            notes.append(f"f3a_output_group_reused={row.get('run_id')}")
    return notes


def not_run_yet_rows(manifest_rows: Sequence[dict[str, str]], log_path: Path) -> list[dict[str, str]]:
    """Build postrun rows when the local run log does not exist."""
    return [
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
            "notes": f"No local run log found at {log_path.as_posix()}; human one-cell slice has not been executed yet.",
        }
        for row in manifest_rows
    ]


def blocked_rows(manifest_rows: Sequence[dict[str, str]], reason: str, status: str) -> list[dict[str, str]]:
    """Build blocked postrun rows."""
    return [
        {
            "run_id": row.get("run_id", ""),
            "phase": "PREPARED",
            "postrun_status": status,
            "run_log_exists": "",
            "run_log_status": "",
            "expected_tmrt_path": row.get("expected_tmrt_path", ""),
            "file_exists": "",
            "file_size_bytes": "",
            "validation_status": status,
            "notes": reason,
        }
        for row in manifest_rows
    ]


def log_path_allowed(config: dict[str, Any], log_path: Path) -> bool:
    """Return whether the run log is under the approved local runner root."""
    return is_relative_to(log_path, Path(str(onecell(config)["local_runner_copy_root"])))


def validate_executed_rows(
    config: dict[str, Any],
    manifest_rows: Sequence[dict[str, str]],
    log_rows: Sequence[dict[str, str]],
) -> tuple[list[dict[str, str]], bool, bool]:
    """Validate local run-log statuses and expected output file metadata only."""
    log_by_run_id = {row.get("run_id", ""): row for row in log_rows}
    expected_run_ids = {row["run_id"] for row in manifest_rows}
    extra_run_ids = sorted(set(log_by_run_id) - expected_run_ids)
    all_log_success = len(log_rows) == len(manifest_rows) and not extra_run_ids
    all_outputs_present = True
    rows: list[dict[str, str]] = []
    for manifest in manifest_rows:
        run_id = manifest["run_id"]
        log = log_by_run_id.get(run_id, {})
        log_status = clean(log.get("status")).lower() if log else "missing"
        expected_tmrt = Path(manifest["expected_tmrt_path"])
        path_allowed = path_outside_git_and_under_local(config, expected_tmrt)
        file_exists = expected_tmrt.exists() if path_allowed else False
        file_size = expected_tmrt.stat().st_size if file_exists else 0
        row_log_success = log_status == "success"
        row_output_ok = path_allowed and file_exists and file_size > 0
        row_pass = row_log_success and row_output_ok
        all_log_success = all_log_success and row_log_success
        all_outputs_present = all_outputs_present and row_output_ok
        notes: list[str] = []
        if log_status != "success":
            notes.append(f"run_log_status={log_status}")
        if not path_allowed:
            notes.append("expected_tmrt_path_not_local_only")
        if not file_exists:
            notes.append("expected_tmrt_missing")
        elif file_size <= 0:
            notes.append("expected_tmrt_zero_size")
        if extra_run_ids:
            notes.append("extra_run_ids_in_log=" + ";".join(extra_run_ids))
        rows.append(
            {
                "run_id": run_id,
                "phase": "EXECUTED",
                "postrun_status": PASS if row_pass else FAIL,
                "run_log_exists": YES,
                "run_log_status": log_status,
                "expected_tmrt_path": expected_tmrt.as_posix(),
                "file_exists": YES if file_exists else NO,
                "file_size_bytes": str(file_size) if file_exists else "0",
                "validation_status": PASS if row_pass else BLOCKED_POSTRUN,
                "notes": "none" if not notes else "; ".join(notes),
            }
        )
    return rows, all_log_success, all_outputs_present


def compact_postrun_status(rows: Sequence[dict[str, str]], decision: str) -> str:
    """Return a compact postrun status for reports."""
    if decision == READY_FOR_HUMAN_ONECELL_SLICE:
        return NOT_RUN_YET
    if decision in {BLOCKED_PRECHECK, BLOCKED_POSTRUN}:
        return decision
    passed = sum(1 for row in rows if row.get("validation_status") == PASS)
    return f"{passed}/{len(rows)}_EXECUTED_OUTPUTS_VALID"


def validate(config_path: Path) -> int:
    """Validate the prepared one-cell slice and optional human run log."""
    config = read_config(repo_path(config_path))
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    precheck_rows = read_csv_rows(repo_path(outputs["pre_execution_asset_check"]))
    local_log = Path(str(onecell(config)["local_run_log_path"]))
    expected_runs = expected_run_count(config)
    ready_count = precheck_ready_count(precheck_rows)
    manifest_notes = validate_manifest_scope(config, manifest_rows)
    forbidden_hits = changed_forbidden_paths(git_status_short())

    if forbidden_hits:
        reason = "Forbidden changed files detected: " + "; ".join(forbidden_hits)
        postrun_rows = blocked_rows(manifest_rows, reason, BLOCKED_PRECHECK)
        decision = BLOCKED_PRECHECK
        notes = reason
        exit_code = 2
    elif manifest_notes:
        reason = "Manifest scope problem: " + "; ".join(manifest_notes)
        postrun_rows = blocked_rows(manifest_rows, reason, BLOCKED_PRECHECK)
        decision = BLOCKED_PRECHECK
        notes = reason
        exit_code = 2
    elif ready_count != expected_runs:
        reason = f"Pre-execution ready count {ready_count}/{expected_runs}; human slice remains blocked."
        postrun_rows = blocked_rows(manifest_rows, reason, BLOCKED_PRECHECK)
        decision = BLOCKED_PRECHECK
        notes = reason
        exit_code = 2
    elif not local_log.exists():
        postrun_rows = not_run_yet_rows(manifest_rows, local_log)
        decision = READY_FOR_HUMAN_ONECELL_SLICE
        notes = "Prepared only; no local human QGIS run log exists yet."
        exit_code = 0
    elif not log_path_allowed(config, local_log):
        reason = f"Run log path is outside approved local runner root: {local_log.as_posix()}"
        postrun_rows = blocked_rows(manifest_rows, reason, BLOCKED_POSTRUN)
        decision = BLOCKED_POSTRUN
        notes = reason
        exit_code = 2
    else:
        log_rows = read_csv_rows(local_log)
        postrun_rows, all_log_success, all_outputs_present = validate_executed_rows(config, manifest_rows, log_rows)
        if all_log_success and all_outputs_present:
            decision = ONECELL_SLICE_POSTRUN_PASS_RASTER_QA_PENDING
            notes = "Human run log and expected raster file existence/size passed; raster content QA still required."
            exit_code = 0
        elif any(row.get("file_exists") == NO for row in postrun_rows):
            decision = BLOCKED_POSTRUN
            notes = "Run log exists, but one or more expected Tmrt_average.tif outputs are missing or zero size."
            exit_code = 2
        else:
            decision = ONECELL_SLICE_EXECUTED_PARTIAL
            notes = "Run log exists, but one or more run statuses are not success."
            exit_code = 2

    write_csv_rows(repo_path(outputs["postrun_validation"]), postrun_rows, postrun_fieldnames())
    postrun_status = compact_postrun_status(postrun_rows, decision)
    raster_qa_status = NOT_RUN_YET if decision != ONECELL_SLICE_POSTRUN_PASS_RASTER_QA_PENDING else "PENDING_RASTER_QA"
    write_status_report(
        repo_path(outputs["status"]),
        config,
        decision,
        len(manifest_rows),
        ready_count,
        postrun_status,
        raster_qa_status,
        notes,
    )

    print(f"Status: {decision}")
    print(f"Manifest run count: {len(manifest_rows)}")
    print(f"Pre-execution ready count: {ready_count}")
    print(f"Postrun status: {postrun_status}")
    print(f"Raster QA status: {raster_qa_status}")
    print(f"Local run log path expected: {local_log.as_posix()}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print(f"Forbidden files touched: {'none' if not forbidden_hits else '; '.join(forbidden_hits)}")
    print("Files created:")
    for path in all_lane_paths(config):
        print(f"- {rel(path)}")
    return exit_code


def main() -> int:
    """Parse CLI arguments and validate the F3b one-cell full slice."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate the B8.5-F3b 20-run one-cell full-slice package and "
            "optional local-only human run log. Does not run QGIS/SOLWEIG or "
            "open raster contents."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F3b YAML config path.")
    args = parser.parse_args()
    try:
        return validate(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
