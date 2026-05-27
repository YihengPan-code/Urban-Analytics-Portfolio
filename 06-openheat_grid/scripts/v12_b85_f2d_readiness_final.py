"""Rerun the B8.5-F2d final SOLWEIG readiness gate.

Inputs:
    configs/v12/systemb_b85_f2d_readiness_final.yaml
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_asset_remap_table.csv
    outputs/v12_surrogate/b8_5_f2c_met_forcing/b85_f2c_next_remap_roots.yaml
    Optional local QGIS manual check text file declared in the config.

Outputs:
    docs/v12/OpenHeat_SystemB_B8_5_F2d_readiness_final_CN.md
    outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_root_inventory.csv
    outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_asset_status.csv
    outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_run_readiness.csv
    outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_readiness_summary.csv
    outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_execution_precheck_checklist.md
    outputs/v12_surrogate/b8_5_f2d_readiness_final/B8_5_F2D_STATUS.md

Saved metrics:
    Manifest counts, root inventory, file asset status, 480-row run readiness,
    file-assets-ready count, ready-for-manual-QGIS count, output-root status,
    QGIS manual check status, remaining blockers, and final decision status.

This script does not stage, commit, run QGIS, run SOLWEIG, create/copy/open
rasters, copy/open svfs.zip, create AOI-wide predictions, compute local WBGT,
create hazard_score/risk_score, or create System A/B coupling outputs. Raster
and svfs.zip paths are checked by metadata existence only; their contents are
not read.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f2d_readiness_final.yaml"

YES = "yes"
NO = "no"
PASS = "PASS"
FAIL = "FAIL"
PENDING = "PENDING"
READY_FOR_MANUAL_QGIS = "READY_FOR_MANUAL_QGIS"
FILE_ASSETS_READY_QGIS_CHECK_PENDING = "FILE_ASSETS_READY_QGIS_CHECK_PENDING"
OUTPUT_ROOT_MISSING = "OUTPUT_ROOT_MISSING"
PARTIAL_ASSETS_MISSING = "PARTIAL_ASSETS_MISSING"
BLOCKED = "BLOCKED"
FAILED = "FAILED"

FILE_ASSET_TYPES = {"cell_geometry", "raster_tile", "svf_zip", "met_forcing_file"}
REMAPPED_FILE_ASSET_TYPES = {"cell_geometry", "raster_tile", "svf_zip"}
FORBIDDEN_SCOPE_TRUE_KEYS = {
    "qgis_executed",
    "solweig_executed",
    "create_rasters",
    "copy_rasters",
    "open_rasters",
    "copy_svf_zip",
    "open_svf_zip",
    "create_aoi_predictions",
    "create_local_wbgt",
    "create_hazard_score",
    "create_risk_score",
    "create_system_ab_coupling",
    "stage_changes",
    "commit_changes",
}


@dataclass(frozen=True)
class RootAlias:
    """Configured root alias used for metadata-only path resolution."""

    root_alias: str
    root_path: Path
    root_kind: str
    role: str
    commit_safe_to_reference: str
    notes: str


@dataclass(frozen=True)
class OutputRootCheck:
    """Local SOLWEIG output-root readiness check."""

    path: Path
    exists: bool
    is_dir: bool
    outside_git_worktree: bool
    status: str
    notes: str


@dataclass(frozen=True)
class QgisManualCheck:
    """Optional human-written QGIS algorithm manual check status."""

    path: Path
    exists: bool
    manual_check_status: str
    status_raw: str
    notes: str


@dataclass(frozen=True)
class F2dResult:
    """Return object for the F2d final readiness rerun."""

    decision_status: str
    file_assets_ready_count: int
    ready_for_manual_qgis_count: int
    output_root_status: str
    qgis_manual_check_status: str
    remaining_blockers: str
    files_created: list[Path]


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def path_text(path: Path | str) -> str:
    """Return a stable slash-separated path string."""
    return Path(path).as_posix()


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by project configs."""
    stripped = value.strip()
    if stripped == "[]":
        return []
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"yes", "no"}:
        return lowered
    if lowered in {"null", "none", "~"}:
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
    """Read the simple nested YAML shape used by OpenHeat configs."""
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
            item_text = text[2:].strip()
            if ":" in item_text:
                key, _, raw_value = item_text.partition(":")
                item: dict[str, Any] = {key.strip(): parse_scalar(raw_value.strip())}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(parse_scalar(item_text))
            continue
        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            if not isinstance(parent, dict):
                raise ValueError(f"Unsupported YAML mapping placement: {line}")
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = {}
        for future in lines[idx + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        if not isinstance(parent, dict):
            raise ValueError(f"Unsupported YAML parent for key: {line}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Load YAML, preferring PyYAML with a no-dependency fallback."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"YAML did not parse to a mapping: {path_text(path)}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def repo_path(value: str | Path) -> Path:
    """Resolve a path relative to the project subdirectory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def git_root() -> Path:
    """Return the enclosing git root used for outside-worktree checks."""
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip())


def is_relative_to(path: Path, parent: Path) -> bool:
    """Return True when path is under parent after non-strict resolution."""
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def safe_relative(path: Path, parent: Path) -> str:
    """Return a slash-relative path when possible, otherwise an absolute path."""
    try:
        return path.resolve(strict=False).relative_to(parent.resolve(strict=False)).as_posix()
    except ValueError:
        return path_text(path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read CSV rows as dictionaries."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write dictionaries to CSV with stable UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text after creating the parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    """Hash a small text met forcing file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_yes_no(value: bool) -> str:
    """Format a boolean as yes/no."""
    return YES if value else NO


def root_aliases_from_config(config: dict[str, Any], f2c_config: dict[str, Any]) -> list[RootAlias]:
    """Build root aliases from F2d config and F2c next-root metadata."""
    roots: list[RootAlias] = []
    for item in config.get("root_aliases", []) or []:
        roots.append(
            RootAlias(
                root_alias=clean(item.get("root_alias")),
                root_path=Path(clean(item.get("root_path"))),
                root_kind=clean(item.get("root_kind")),
                role=clean(item.get("role")),
                commit_safe_to_reference=clean(item.get("commit_safe_to_reference")) or NO,
                notes=clean(item.get("notes")),
            )
        )
    for item in f2c_config.get("root_aliases", []) or []:
        alias = clean(item.get("root_alias"))
        if any(root.root_alias == alias for root in roots):
            continue
        roots.append(
            RootAlias(
                root_alias=alias,
                root_path=Path(clean(item.get("root_path"))),
                root_kind=clean(item.get("root_kind")),
                role="generated_fd02_met_forcing",
                commit_safe_to_reference=clean(item.get("commit_safe_to_reference")) or YES,
                notes=clean(item.get("notes")),
            )
        )
    return roots


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Return configured output paths."""
    outputs = config.get("outputs", {}) or {}
    return {
        "canonical_note_cn": repo_path(outputs["canonical_note_cn"]),
        "root_inventory": repo_path(outputs["root_inventory"]),
        "asset_status": repo_path(outputs["asset_status"]),
        "run_readiness": repo_path(outputs["run_readiness"]),
        "readiness_summary": repo_path(outputs["readiness_summary"]),
        "execution_precheck_checklist": repo_path(outputs["execution_precheck_checklist"]),
        "status": repo_path(outputs["status"]),
    }


def enforce_scope(config: dict[str, Any]) -> None:
    """Fail fast if the config would authorize execution or unsafe IO."""
    if bool(config.get("execute_qgis_or_solweig")):
        raise ValueError("execute_qgis_or_solweig must remain false for F2d readiness.")
    if bool(config.get("open_or_copy_rasters")):
        raise ValueError("open_or_copy_rasters must remain false for F2d readiness.")
    if not bool(config.get("dry_run_only")):
        raise ValueError("dry_run_only must remain true for F2d readiness.")
    scope = config.get("scope", {}) or {}
    for key in FORBIDDEN_SCOPE_TRUE_KEYS:
        if bool(scope.get(key)):
            raise ValueError(f"Forbidden scope flag is true: {key}")


def manual_qgis_check(path: Path) -> QgisManualCheck:
    """Read the optional QGIS check file and extract manual_check_status."""
    if not path.exists():
        return QgisManualCheck(
            path=path,
            exists=False,
            manual_check_status=PENDING,
            status_raw="",
            notes="QGIS manual check file is missing.",
        )
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"manual_check_status\s*[:=]\s*([A-Za-z0-9_-]+)", text, flags=re.IGNORECASE)
    raw_status = clean(match.group(1)).upper() if match else ""
    if raw_status == PASS:
        status = PASS
        notes = "manual_check_status=PASS found in local check file."
    elif raw_status == FAIL:
        status = FAIL
        notes = "manual_check_status=FAIL found in local check file."
    else:
        status = PENDING
        notes = "Check file exists but manual_check_status=PASS was not found."
    return QgisManualCheck(
        path=path,
        exists=True,
        manual_check_status=status,
        status_raw=raw_status,
        notes=notes,
    )


def local_output_root_check(path: Path, repo_root: Path) -> OutputRootCheck:
    """Check that the local output root exists as a directory outside git."""
    exists = path.exists()
    is_dir = path.is_dir() if exists else False
    outside_git = not is_relative_to(path, repo_root)
    if exists and is_dir and outside_git:
        status = PASS
        notes = "Local output root exists and is outside the current Git worktree."
    elif not exists:
        status = OUTPUT_ROOT_MISSING
        notes = "Local output root does not exist."
    elif not is_dir:
        status = FAIL
        notes = "Local output root path exists but is not a directory."
    else:
        status = FAIL
        notes = "Local output root is inside the current Git worktree."
    return OutputRootCheck(
        path=path,
        exists=exists,
        is_dir=is_dir,
        outside_git_worktree=outside_git,
        status=status,
        notes=notes,
    )


def make_root_inventory(
    roots: list[RootAlias],
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Create root/check inventory rows."""
    rows: list[dict[str, Any]] = []
    for root in roots:
        exists = root.root_path.exists()
        rows.append(
            {
                "root_alias": root.root_alias,
                "root_path": path_text(root.root_path),
                "root_kind": root.root_kind,
                "role": root.role,
                "exists": as_yes_no(exists),
                "is_dir": as_yes_no(root.root_path.is_dir() if exists else False),
                "inside_current_git_worktree": as_yes_no(is_relative_to(root.root_path, repo_root)),
                "outside_current_git_worktree": as_yes_no(not is_relative_to(root.root_path, repo_root)),
                "commit_safe_to_reference": root.commit_safe_to_reference,
                "status": PASS if exists else FAIL,
                "notes": root.notes,
            }
        )
    rows.append(
        {
            "root_alias": "local_output_root",
            "root_path": path_text(output_root.path),
            "root_kind": "local_solweig_output_root",
            "role": "manual_qgis_solweig_output_target",
            "exists": as_yes_no(output_root.exists),
            "is_dir": as_yes_no(output_root.is_dir),
            "inside_current_git_worktree": as_yes_no(is_relative_to(output_root.path, repo_root)),
            "outside_current_git_worktree": as_yes_no(output_root.outside_git_worktree),
            "commit_safe_to_reference": YES,
            "status": output_root.status,
            "notes": output_root.notes,
        }
    )
    rows.append(
        {
            "root_alias": "qgis_manual_check_file",
            "root_path": path_text(qgis_check.path),
            "root_kind": "local_manual_check_file",
            "role": "human_qgis_algorithm_availability_check",
            "exists": as_yes_no(qgis_check.exists),
            "is_dir": NO,
            "inside_current_git_worktree": as_yes_no(is_relative_to(qgis_check.path, repo_root)),
            "outside_current_git_worktree": as_yes_no(not is_relative_to(qgis_check.path, repo_root)),
            "commit_safe_to_reference": YES,
            "status": qgis_check.manual_check_status,
            "notes": qgis_check.notes,
        }
    )
    return rows


def manifest_status(
    run_rows: list[dict[str, str]], expectations: dict[str, Any]
) -> tuple[str, dict[str, int], list[str]]:
    """Validate run-matrix shape against F2d expectations."""
    counts = {
        "rows": len(run_rows),
        "cells": len({clean(row.get("cell_id")) for row in run_rows}),
        "forcing_days": len({clean(row.get("forcing_day_id")) for row in run_rows}),
        "hours": len({clean(row.get("hour_sgt")) for row in run_rows}),
        "scenarios": len({clean(row.get("scenario")) for row in run_rows}),
    }
    blockers: list[str] = []
    for key, expected in expectations.items():
        observed = counts.get(key)
        if observed != int(expected):
            blockers.append(f"manifest_{key}_expected_{expected}_observed_{observed}")
    return (PASS if not blockers else FAIL, counts, blockers)


def f2c_target_met_by_hour(f2c_config: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Return FD02 local met forcing rows keyed by hour."""
    targets: dict[int, dict[str, Any]] = {}
    for item in f2c_config.get("target_met_forcing_files", []) or []:
        hour = int(item["hour_sgt"])
        targets[hour] = item
    return targets


def remap_path(row: dict[str, str], root_by_alias: dict[str, RootAlias]) -> Path | None:
    """Resolve a remapped F2b asset path without opening its contents."""
    alias = clean(row.get("selected_root_alias"))
    relative = clean(row.get("selected_relative_path"))
    if not alias or not relative:
        return None
    root = root_by_alias.get(alias)
    if root is None:
        return None
    return root.root_path / Path(relative)


def remapped_asset_status_rows(
    remap_rows: list[dict[str, str]], root_by_alias: dict[str, RootAlias]
) -> list[dict[str, Any]]:
    """Create status rows for F2b-recovered geometry, raster, and SVF assets."""
    rows: list[dict[str, Any]] = []
    for row in remap_rows:
        asset_type = clean(row.get("asset_type"))
        if asset_type not in REMAPPED_FILE_ASSET_TYPES:
            continue
        resolved_path = remap_path(row, root_by_alias)
        exists = bool(resolved_path and resolved_path.exists())
        remap_ready = clean(row.get("remap_status")) == "recovered_by_root_remap"
        asset_ready = exists and remap_ready
        notes = clean(row.get("notes"))
        if asset_type in {"raster_tile", "svf_zip"}:
            notes = f"{notes} Metadata existence check only; contents were not opened or copied.".strip()
        rows.append(
            {
                "asset_type": asset_type,
                "logical_name": clean(row.get("logical_name")),
                "forcing_day_id": "",
                "hour_sgt": "",
                "cell_id": cell_from_logical_name(clean(row.get("logical_name"))),
                "scenario": scenario_from_logical_name(clean(row.get("logical_name"))),
                "source": "f2b_remap_table",
                "selected_root_alias": clean(row.get("selected_root_alias")),
                "expected_path": clean(row.get("original_expected_path")),
                "selected_relative_path": clean(row.get("selected_relative_path")),
                "resolved_path": path_text(resolved_path) if resolved_path else "",
                "exists": as_yes_no(exists),
                "sha256_expected": "",
                "sha256_actual": "",
                "sha256_match": "not_required",
                "asset_ready": as_yes_no(asset_ready),
                "used_in_run_readiness": as_yes_no(clean(row.get("logical_name")) != "building_dsm_path"),
                "forbidden_asset_opened_or_copied": NO,
                "notes": notes,
            }
        )
    return rows


def cell_from_logical_name(logical_name: str) -> str:
    """Extract TP cell id from a logical asset name when present."""
    parts = logical_name.split("_")
    if len(parts) >= 2 and parts[0] == "TP":
        return f"{parts[0]}_{parts[1]}"
    return ""


def scenario_from_logical_name(logical_name: str) -> str:
    """Infer base/overhead scenario from a logical asset name."""
    if logical_name.endswith("_vegetation_base") or logical_name.endswith("_svf_base"):
        return "base"
    if logical_name.endswith("_vegetation_overhead") or logical_name.endswith("_svf_overhead"):
        return "overhead_as_canopy"
    return ""


def met_filename(date_value: str, hour: int, station_id: str) -> str:
    """Build the expected v09 SOLWEIG met forcing text filename."""
    date_token = date_value.replace("-", "_")
    return f"v09_met_forcing_{date_token}_{station_id}_h{hour:02d}.txt"


def met_asset_status_rows(
    run_rows: list[dict[str, str]],
    f2c_targets: dict[int, dict[str, Any]],
    roots: dict[str, RootAlias],
) -> list[dict[str, Any]]:
    """Create FD01/FD02 met forcing status rows."""
    rows: list[dict[str, Any]] = []
    unique_met = sorted(
        {
            (
                clean(row.get("forcing_day_id")),
                clean(row.get("date")),
                int(clean(row.get("hour_sgt"))),
            )
            for row in run_rows
        }
    )
    station_id = "S128"
    for target in f2c_targets.values():
        station_id = clean(target.get("station_id")) or station_id
        break
    for forcing_day_id, date_value, hour in unique_met:
        is_fd02 = forcing_day_id.startswith("FD02")
        if is_fd02:
            target = f2c_targets.get(hour, {})
            target_path = clean(target.get("local_output_path"))
            resolved_path = Path(target_path) if target_path else Path(f"missing_fd02_met_forcing_h{hour:02d}.txt")
            expected_sha = clean(target.get("sha256"))
            root_alias = "b85_f2c_local_met_forcing"
            selected_relative = (
                safe_relative(resolved_path, roots[root_alias].root_path)
                if root_alias in roots and target_path
                else path_text(resolved_path)
            )
            source = "f2c_next_remap_roots"
        else:
            root_alias = "b8_worktree_project"
            relative = Path("data/solweig") / met_filename(date_value, hour, station_id)
            resolved_path = roots[root_alias].root_path / relative
            selected_relative = path_text(relative)
            expected_sha = ""
            source = "existing_fd01_met_forcing"
        exists = resolved_path.exists()
        actual_sha = ""
        sha_match = "not_required"
        if expected_sha:
            if exists and resolved_path.suffix.lower() == ".txt":
                actual_sha = sha256_file(resolved_path)
                sha_match = PASS if actual_sha == expected_sha else FAIL
            else:
                sha_match = FAIL
        asset_ready = exists and sha_match != FAIL
        rows.append(
            {
                "asset_type": "met_forcing_file",
                "logical_name": f"{forcing_day_id}_h{hour:02d}",
                "forcing_day_id": forcing_day_id,
                "hour_sgt": str(hour),
                "cell_id": "",
                "scenario": "",
                "source": source,
                "selected_root_alias": root_alias,
                "expected_path": (
                    clean(f2c_targets.get(hour, {}).get("local_output_path"))
                    if is_fd02
                    else path_text(Path("data/solweig") / met_filename(date_value, hour, station_id))
                ),
                "selected_relative_path": selected_relative,
                "resolved_path": path_text(resolved_path),
                "exists": as_yes_no(exists),
                "sha256_expected": expected_sha,
                "sha256_actual": actual_sha,
                "sha256_match": sha_match,
                "asset_ready": as_yes_no(asset_ready),
                "used_in_run_readiness": YES,
                "forbidden_asset_opened_or_copied": NO,
                "notes": (
                    "FD02 generated local met forcing text file; SHA checked when listed."
                    if is_fd02
                    else "FD01 existing met forcing text file; existence checked."
                ),
            }
        )
    return rows


def control_status_rows(
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
) -> list[dict[str, Any]]:
    """Create non-file execution-gate status rows."""
    return [
        {
            "asset_type": "local_output_root",
            "logical_name": "manual_local_raw_output_root",
            "forcing_day_id": "",
            "hour_sgt": "",
            "cell_id": "",
            "scenario": "",
            "source": "f2d_config",
            "selected_root_alias": "local_output_root",
            "expected_path": path_text(output_root.path),
            "selected_relative_path": "",
            "resolved_path": path_text(output_root.path),
            "exists": as_yes_no(output_root.exists),
            "sha256_expected": "",
            "sha256_actual": "",
            "sha256_match": "not_required",
            "asset_ready": as_yes_no(output_root.status == PASS),
            "used_in_run_readiness": YES,
            "forbidden_asset_opened_or_copied": NO,
            "notes": output_root.notes,
        },
        {
            "asset_type": "qgis_algorithm_manual_check",
            "logical_name": "solweig_algorithm_id_hint",
            "forcing_day_id": "",
            "hour_sgt": "",
            "cell_id": "",
            "scenario": "",
            "source": "local_manual_check_file",
            "selected_root_alias": "qgis_manual_check_file",
            "expected_path": path_text(qgis_check.path),
            "selected_relative_path": "",
            "resolved_path": path_text(qgis_check.path),
            "exists": as_yes_no(qgis_check.exists),
            "sha256_expected": "",
            "sha256_actual": "",
            "sha256_match": "not_required",
            "asset_ready": as_yes_no(qgis_check.manual_check_status == PASS),
            "used_in_run_readiness": YES,
            "forbidden_asset_opened_or_copied": NO,
            "notes": qgis_check.notes,
        },
    ]


def scenario_slug(scenario: str) -> str:
    """Return the output directory scenario slug used by B8.5 manifests."""
    if scenario == "overhead_as_canopy":
        return "overhead"
    return scenario


def required_asset_names(row: dict[str, str]) -> dict[str, list[str]]:
    """Return logical asset names required by one SOLWEIG run."""
    cell_id = clean(row.get("cell_id"))
    scenario = clean(row.get("scenario"))
    vegetation = "vegetation_overhead" if scenario == "overhead_as_canopy" else "vegetation_base"
    svf = "svf_overhead" if scenario == "overhead_as_canopy" else "svf_base"
    hour = int(clean(row.get("hour_sgt")))
    forcing_day_id = clean(row.get("forcing_day_id"))
    return {
        "cell_geometry": [f"{cell_id}_focus_cell"],
        "raster_tile": [
            f"{cell_id}_dsm_buildings",
            f"{cell_id}_dem",
            f"{cell_id}_wall_height",
            f"{cell_id}_wall_aspect",
            f"{cell_id}_{vegetation}",
        ],
        "svf_zip": [f"{cell_id}_{svf}"],
        "met_forcing_file": [f"{forcing_day_id}_h{hour:02d}"],
    }


def make_asset_lookup(asset_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Index asset status rows by type and logical name."""
    return {
        (clean(row.get("asset_type")), clean(row.get("logical_name"))): row
        for row in asset_rows
    }


def missing_assets_text(asset_names: dict[str, list[str]], lookup: dict[tuple[str, str], dict[str, Any]]) -> str:
    """Return a compact missing asset list for one run."""
    missing: list[str] = []
    for asset_type, logical_names in asset_names.items():
        for logical_name in logical_names:
            asset = lookup.get((asset_type, logical_name))
            if asset is None:
                missing.append(f"{asset_type}:{logical_name}:missing_status_row")
            elif clean(asset.get("asset_ready")) != YES:
                reason = clean(asset.get("notes")) or clean(asset.get("resolved_path"))
                missing.append(f"{asset_type}:{logical_name}:{reason}")
    return "; ".join(missing)


def all_assets_ready(asset_type: str, names: list[str], lookup: dict[tuple[str, str], dict[str, Any]]) -> bool:
    """Return True if every named asset row is ready."""
    for name in names:
        asset = lookup.get((asset_type, name))
        if asset is None or clean(asset.get("asset_ready")) != YES:
            return False
    return True


def make_run_readiness_rows(
    run_rows: list[dict[str, str]],
    asset_rows: list[dict[str, Any]],
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
) -> list[dict[str, Any]]:
    """Evaluate readiness for all 480 run-matrix rows."""
    lookup = make_asset_lookup(asset_rows)
    rows: list[dict[str, Any]] = []
    for row in run_rows:
        asset_names = required_asset_names(row)
        cell_ready = all_assets_ready("cell_geometry", asset_names["cell_geometry"], lookup)
        raster_ready = all_assets_ready("raster_tile", asset_names["raster_tile"], lookup)
        svf_ready = all_assets_ready("svf_zip", asset_names["svf_zip"], lookup)
        met_ready = all_assets_ready("met_forcing_file", asset_names["met_forcing_file"], lookup)
        file_assets_ready = cell_ready and raster_ready and svf_ready and met_ready
        ready_for_manual_qgis = file_assets_ready and output_root.status == PASS and qgis_check.manual_check_status == PASS
        if not file_assets_ready:
            run_readiness = "blocked_file_assets_missing"
        elif output_root.status != PASS:
            run_readiness = "blocked_output_root_missing_or_invalid"
        elif qgis_check.manual_check_status != PASS:
            run_readiness = "blocked_qgis_manual_check_not_pass"
        else:
            run_readiness = "ready_for_manual_qgis"
        expected_output_dir = output_root.path / clean(row.get("expected_output_group"))
        rows.append(
            {
                "run_id": clean(row.get("run_id")),
                "cell_id": clean(row.get("cell_id")),
                "forcing_day_id": clean(row.get("forcing_day_id")),
                "date": clean(row.get("date")),
                "hour_sgt": clean(row.get("hour_sgt")),
                "scenario": clean(row.get("scenario")),
                "expected_output_group": clean(row.get("expected_output_group")),
                "cell_geometry_ready": as_yes_no(cell_ready),
                "raster_tiles_ready": as_yes_no(raster_ready),
                "svf_ready": as_yes_no(svf_ready),
                "met_forcing_ready": as_yes_no(met_ready),
                "file_assets_ready": as_yes_no(file_assets_ready),
                "output_root_ready": as_yes_no(output_root.status == PASS),
                "qgis_manual_check_status": qgis_check.manual_check_status,
                "ready_for_manual_qgis": as_yes_no(ready_for_manual_qgis),
                "run_readiness": run_readiness,
                "missing_file_assets": missing_assets_text(asset_names, lookup),
                "expected_output_dir": path_text(expected_output_dir),
                "qgis_solweig_executed": NO,
            }
        )
    return rows


def remaining_blockers(
    manifest_blockers: list[str],
    file_assets_ready_count: int,
    total_runs: int,
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
) -> str:
    """Return semicolon-delimited blockers."""
    blockers = list(manifest_blockers)
    if file_assets_ready_count < total_runs:
        blockers.append(f"file_assets_ready_{file_assets_ready_count}_of_{total_runs}")
    if output_root.status != PASS:
        blockers.append("local_output_root_missing_or_invalid")
    if qgis_check.manual_check_status == FAIL:
        blockers.append("qgis_manual_check_failed")
    elif qgis_check.manual_check_status != PASS:
        blockers.append("qgis_manual_check_missing_or_pending")
    return "; ".join(blockers) if blockers else "none"


def decide_status(
    manifest_ok: bool,
    file_assets_ready_count: int,
    total_runs: int,
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
) -> str:
    """Choose the final F2d decision status."""
    if not manifest_ok:
        return BLOCKED
    if file_assets_ready_count < total_runs:
        return PARTIAL_ASSETS_MISSING
    if output_root.status != PASS:
        return OUTPUT_ROOT_MISSING
    if qgis_check.manual_check_status == PASS:
        return READY_FOR_MANUAL_QGIS
    return FILE_ASSETS_READY_QGIS_CHECK_PENDING


def summary_row(
    decision: str,
    manifest_counts: dict[str, int],
    manifest_check_status: str,
    file_assets_ready_count: int,
    ready_for_manual_qgis_count: int,
    total_runs: int,
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
    blockers: str,
) -> dict[str, Any]:
    """Create the one-row readiness summary."""
    return {
        "decision_status": decision,
        "manifest_status": manifest_check_status,
        "manifest_rows": manifest_counts.get("rows", 0),
        "manifest_cells": manifest_counts.get("cells", 0),
        "manifest_forcing_days": manifest_counts.get("forcing_days", 0),
        "manifest_hours": manifest_counts.get("hours", 0),
        "manifest_scenarios": manifest_counts.get("scenarios", 0),
        "file_assets_ready_count": file_assets_ready_count,
        "total_run_count": total_runs,
        "ready_for_manual_qgis_count": ready_for_manual_qgis_count,
        "output_root_status": output_root.status,
        "output_root_exists": as_yes_no(output_root.exists),
        "output_root_outside_git_worktree": as_yes_no(output_root.outside_git_worktree),
        "qgis_manual_check_status": qgis_check.manual_check_status,
        "remaining_blockers": blockers,
        "qgis_solweig_executed": NO,
        "rasters_created_copied_opened": NO,
        "svfs_zip_copied_opened": NO,
        "dry_run_only": YES,
        "created_at": now_stamp(),
    }


def table_lines(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    """Render small Markdown table lines."""
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(clean(row.get(column)) for column in columns) + " |")
    return lines


def write_status(
    path: Path,
    decision: str,
    file_assets_ready_count: int,
    ready_for_manual_qgis_count: int,
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
    blockers: str,
    files_created: list[Path],
    manifest_counts: dict[str, int],
) -> None:
    """Write the F2d status Markdown."""
    text = "\n".join(
        [
            "# B8.5-F2d Status",
            "",
            f"Generated: {now_stamp()}",
            "",
            "## Status",
            "",
            f"`{decision}`",
            "",
            "## Scope",
            "",
            "B8.5-F2d is a readiness rerun only. QGIS/SOLWEIG was not run. "
            "No rasters were created, copied, or opened. `svfs.zip` was not copied or opened. "
            "This is not B9. This is not local WBGT. This is not risk. "
            "No AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling output was created. "
            "Even `READY_FOR_MANUAL_QGIS` is not execution; it is permission for a human-controlled execution lane.",
            "",
            "## Key Results",
            "",
            f"- Manifest rows: `{manifest_counts.get('rows', 0)}`",
            f"- Manifest cells: `{manifest_counts.get('cells', 0)}`",
            f"- Manifest forcing days: `{manifest_counts.get('forcing_days', 0)}`",
            f"- Manifest hours: `{manifest_counts.get('hours', 0)}`",
            f"- Manifest scenarios: `{manifest_counts.get('scenarios', 0)}`",
            f"- File assets ready: `{file_assets_ready_count}/480`",
            f"- Ready for manual QGIS: `{ready_for_manual_qgis_count}/480`",
            f"- Output root status: `{output_root.status}`",
            f"- QGIS manual check status: `{qgis_check.manual_check_status}`",
            f"- Remaining blockers: `{blockers}`",
            "- QGIS/SOLWEIG executed: `no`",
            "",
            "## Files Created / Modified",
            "",
            *[f"- `{path_text(path)}`" for path in files_created],
            "",
            "## Caveats",
            "",
            "This only authorizes the next manual QGIS review if the status is `READY_FOR_MANUAL_QGIS`. "
            "Manual execution remains outside this lane and must stay human-controlled.",
            "",
        ]
    )
    write_text(path, text)


def write_cn_doc(
    path: Path,
    decision: str,
    file_assets_ready_count: int,
    ready_for_manual_qgis_count: int,
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
    blockers: str,
    manifest_counts: dict[str, int],
) -> None:
    """Write the UTF-8 Chinese readiness note."""
    text = "\n".join(
        [
            "# OpenHeat System B B8.5-F2d final readiness 中文说明",
            "",
            f"生成时间：{now_stamp()}",
            "",
            "## 结论",
            "",
            f"- 决策状态：`{decision}`",
            f"- 文件资产 ready：`{file_assets_ready_count}/480`",
            f"- ready_for_manual_qgis：`{ready_for_manual_qgis_count}/480`",
            f"- local output root 状态：`{output_root.status}`",
            f"- QGIS manual check 状态：`{qgis_check.manual_check_status}`",
            f"- 剩余阻塞项：`{blockers}`",
            "",
            "## Manifest 检查",
            "",
            f"- 行数：`{manifest_counts.get('rows', 0)}`",
            f"- cell 数：`{manifest_counts.get('cells', 0)}`",
            f"- forcing day 数：`{manifest_counts.get('forcing_days', 0)}`",
            f"- hour 数：`{manifest_counts.get('hours', 0)}`",
            f"- scenario 数：`{manifest_counts.get('scenarios', 0)}`",
            "",
            "## 边界声明",
            "",
            "- 本轮没有运行 QGIS/SOLWEIG。",
            "- 本轮没有创建、复制或打开任何 raster。",
            "- 本轮没有复制或打开 `svfs.zip`。",
            "- 本轮只是 readiness rerun，不是 B9。",
            "- 本轮不是 local WBGT。",
            "- 本轮不是 risk。",
            "- 本轮没有创建 AOI-wide prediction、local WBGT、hazard_score、risk_score 或 System A/B coupling 输出。",
            "- 只有当状态为 `READY_FOR_MANUAL_QGIS` 时，本说明才授权下一步人工 QGIS review。",
            "- 即使是 `READY_FOR_MANUAL_QGIS`，也不是执行；它只是允许进入由人工控制的执行 lane。",
            "",
            "## 解释",
            "",
            "本轮把 F2b 找回的 tile/SVF/cell geometry 资产通过 `original_project` root alias 重新纳入检查，"
            "并把 F2c 生成的 FD02 local met forcing 文件纳入检查。FD02 met forcing 如有 sha256 记录，"
            "本轮会对文本文件计算 sha256 并比对；raster 和 `svfs.zip` 只做存在性元数据检查，不读取内容。",
            "",
        ]
    )
    write_text(path, text)


def write_checklist(
    path: Path,
    decision: str,
    output_root: OutputRootCheck,
    qgis_check: QgisManualCheck,
    blockers: str,
) -> None:
    """Write a compact pre-execution checklist for human review."""
    qgis_box = "x" if qgis_check.manual_check_status == PASS else " "
    output_box = "x" if output_root.status == PASS else " "
    decision_box = "x" if decision == READY_FOR_MANUAL_QGIS else " "
    text = "\n".join(
        [
            "# B8.5-F2d Execution Precheck Checklist",
            "",
            f"Generated: {now_stamp()}",
            "",
            "- [x] Readiness rerun only.",
            "- [x] QGIS/SOLWEIG was not run.",
            "- [x] No rasters were created, copied, or opened.",
            "- [x] `svfs.zip` was not copied or opened.",
            "- [x] No AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling output was created.",
            f"- [{output_box}] Local output root exists outside the Git worktree: `{path_text(output_root.path)}`.",
            f"- [{qgis_box}] QGIS manual check is PASS: `{path_text(qgis_check.path)}`.",
            f"- [{decision_box}] Decision is `READY_FOR_MANUAL_QGIS`.",
            "",
            "## Remaining Blockers",
            "",
            f"`{blockers}`",
            "",
            "## Next Manual Gate",
            "",
            "Proceed only to a human-controlled QGIS review when the decision is `READY_FOR_MANUAL_QGIS`. "
            "This checklist is not execution permission for automated QGIS/SOLWEIG.",
            "",
        ]
    )
    write_text(path, text)


def asset_status_fieldnames() -> list[str]:
    """Return stable asset-status CSV columns."""
    return [
        "asset_type",
        "logical_name",
        "forcing_day_id",
        "hour_sgt",
        "cell_id",
        "scenario",
        "source",
        "selected_root_alias",
        "expected_path",
        "selected_relative_path",
        "resolved_path",
        "exists",
        "sha256_expected",
        "sha256_actual",
        "sha256_match",
        "asset_ready",
        "used_in_run_readiness",
        "forbidden_asset_opened_or_copied",
        "notes",
    ]


def run(config_path: Path = DEFAULT_CONFIG) -> F2dResult:
    """Run the final readiness rerun and write all configured artifacts."""
    config = read_config(config_path)
    enforce_scope(config)
    paths = output_paths(config)
    repo_root = git_root()
    files_created = [
        paths["root_inventory"],
        paths["asset_status"],
        paths["run_readiness"],
        paths["readiness_summary"],
        paths["execution_precheck_checklist"],
        paths["status"],
        paths["canonical_note_cn"],
    ]

    run_matrix_path = repo_path(config["run_matrix_path"])
    remap_table_path = repo_path(config["f2b_remap_table_path"])
    f2c_roots_path = repo_path(config["f2c_next_remap_roots_path"])
    output_root = local_output_root_check(Path(clean(config["local_output_root"])), repo_root)
    qgis_check = manual_qgis_check(Path(clean(config["qgis_manual_check_path"])))

    missing_core_inputs = [
        path_text(path)
        for path in [run_matrix_path, remap_table_path, f2c_roots_path]
        if not path.exists()
    ]
    if missing_core_inputs:
        blockers = "core_inputs_missing: " + "; ".join(missing_core_inputs)
        roots = root_aliases_from_config(config, {})
        root_rows = make_root_inventory(roots, output_root, qgis_check, repo_root)
        summary = summary_row(
            BLOCKED,
            {"rows": 0, "cells": 0, "forcing_days": 0, "hours": 0, "scenarios": 0},
            FAIL,
            0,
            0,
            480,
            output_root,
            qgis_check,
            blockers,
        )
        write_csv_rows(paths["root_inventory"], root_rows, list(root_rows[0].keys()))
        write_csv_rows(paths["asset_status"], [], asset_status_fieldnames())
        write_csv_rows(paths["run_readiness"], [], [])
        write_csv_rows(paths["readiness_summary"], [summary], list(summary.keys()))
        write_checklist(paths["execution_precheck_checklist"], BLOCKED, output_root, qgis_check, blockers)
        write_status(paths["status"], BLOCKED, 0, 0, output_root, qgis_check, blockers, files_created, {})
        write_cn_doc(paths["canonical_note_cn"], BLOCKED, 0, 0, output_root, qgis_check, blockers, {})
        return F2dResult(BLOCKED, 0, 0, output_root.status, qgis_check.manual_check_status, blockers, files_created)

    f2c_config = read_config(f2c_roots_path)
    roots = root_aliases_from_config(config, f2c_config)
    root_by_alias = {root.root_alias: root for root in roots}
    root_rows = make_root_inventory(roots, output_root, qgis_check, repo_root)

    run_rows = read_csv_rows(run_matrix_path)
    remap_rows = read_csv_rows(remap_table_path)
    manifest_check_status, counts, manifest_blockers = manifest_status(
        run_rows, config.get("manifest_expectations", {}) or {}
    )

    asset_rows = remapped_asset_status_rows(remap_rows, root_by_alias)
    asset_rows.extend(met_asset_status_rows(run_rows, f2c_target_met_by_hour(f2c_config), root_by_alias))
    asset_rows.extend(control_status_rows(output_root, qgis_check))
    asset_rows = sorted(
        asset_rows,
        key=lambda row: (
            clean(row.get("asset_type")),
            clean(row.get("cell_id")),
            clean(row.get("scenario")),
            clean(row.get("forcing_day_id")),
            clean(row.get("hour_sgt")),
            clean(row.get("logical_name")),
        ),
    )

    run_readiness_rows = make_run_readiness_rows(run_rows, asset_rows, output_root, qgis_check)
    total_runs = len(run_readiness_rows)
    file_assets_ready_count = sum(1 for row in run_readiness_rows if row["file_assets_ready"] == YES)
    ready_for_manual_qgis_count = sum(
        1 for row in run_readiness_rows if row["ready_for_manual_qgis"] == YES
    )
    blockers = remaining_blockers(
        manifest_blockers,
        file_assets_ready_count,
        total_runs,
        output_root,
        qgis_check,
    )
    decision = decide_status(
        manifest_check_status == PASS,
        file_assets_ready_count,
        total_runs,
        output_root,
        qgis_check,
    )
    summary = summary_row(
        decision,
        counts,
        manifest_check_status,
        file_assets_ready_count,
        ready_for_manual_qgis_count,
        total_runs,
        output_root,
        qgis_check,
        blockers,
    )

    write_csv_rows(paths["root_inventory"], root_rows, list(root_rows[0].keys()))
    write_csv_rows(paths["asset_status"], asset_rows, asset_status_fieldnames())
    write_csv_rows(paths["run_readiness"], run_readiness_rows, list(run_readiness_rows[0].keys()))
    write_csv_rows(paths["readiness_summary"], [summary], list(summary.keys()))
    write_checklist(paths["execution_precheck_checklist"], decision, output_root, qgis_check, blockers)
    write_status(
        paths["status"],
        decision,
        file_assets_ready_count,
        ready_for_manual_qgis_count,
        output_root,
        qgis_check,
        blockers,
        files_created,
        counts,
    )
    write_cn_doc(
        paths["canonical_note_cn"],
        decision,
        file_assets_ready_count,
        ready_for_manual_qgis_count,
        output_root,
        qgis_check,
        blockers,
        counts,
    )

    return F2dResult(
        decision_status=decision,
        file_assets_ready_count=file_assets_ready_count,
        ready_for_manual_qgis_count=ready_for_manual_qgis_count,
        output_root_status=output_root.status,
        qgis_manual_check_status=qgis_check.manual_check_status,
        remaining_blockers=blockers,
        files_created=files_created,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the F2d readiness rerun."""
    parser = argparse.ArgumentParser(
        description=(
            "Rerun B8.5-F2d final readiness using F2b root remap assets, "
            "F2c local FD02 met forcing, local output root, and optional QGIS "
            "manual check file. This never runs QGIS/SOLWEIG."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F2d YAML config path.")
    return parser


def main() -> int:
    """Parse CLI args and run the F2d readiness rerun."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run(repo_path(args.config))
    except Exception as exc:
        print(f"Decision status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print(f"Decision status: {result.decision_status}")
    print(f"File assets ready: {result.file_assets_ready_count}/480")
    print(f"Ready for manual QGIS: {result.ready_for_manual_qgis_count}/480")
    print(f"Output root status: {result.output_root_status}")
    print(f"QGIS manual check status: {result.qgis_manual_check_status}")
    print(f"Remaining blockers: {result.remaining_blockers}")
    print("QGIS/SOLWEIG executed: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path_text(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
