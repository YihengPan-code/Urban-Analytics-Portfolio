"""Recover B8.5-F2a missing local SOLWEIG assets by root remap only.

Inputs:
    configs/v12/systemb_b85_f2b_asset_recovery_remap.yaml
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_missing_assets.csv
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_asset_readiness_by_run.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_required_asset_inventory.csv

Outputs:
    docs/v12/OpenHeat_SystemB_B8_5_F2b_asset_recovery_remap_CN.md
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_root_candidate_inventory.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_asset_recovery_by_missing_asset.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_asset_remap_table.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_missing_after_remap.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_run_readiness_after_remap.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_readiness_delta_summary.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_local_output_root_plan.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_met_forcing_recovery_plan.csv
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/b85_f2b_manual_remap_checklist.md
    outputs/v12_surrogate/b8_5_f2b_asset_recovery/B8_5_F2B_STATUS.md

Saved metrics:
    Root-candidate inventory, one remap row per F2a missing/manual asset,
    missing-after-remap counts, per-run readiness after remap, F2a/F2b ready
    run deltas, recovered/still-missing counts by asset type, and manual local
    output-root / met-forcing plans.

This script does not run QGIS, run SOLWEIG, create rasters, copy rasters,
open rasters for analysis, copy/open svfs.zip, create AOI-wide predictions,
compute local WBGT, create hazard_score/risk_score, create System A/B coupling
outputs, stage files, or commit files. Raster and SVF assets are checked only
with pathlib existence checks.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f2b_asset_recovery_remap.yaml"

YES = "yes"
NO = "no"
READY_AFTER_REMAP = "READY_AFTER_REMAP"
READY_IF_OUTPUT_ROOT_CREATED = "READY_IF_OUTPUT_ROOT_CREATED"
PARTIAL_REMAP_AVAILABLE = "PARTIAL_REMAP_AVAILABLE"
NO_ASSET_ROOT_FOUND = "NO_ASSET_ROOT_FOUND"
BLOCKED = "BLOCKED"
FAILED = "FAILED"

RECOVERED = "recovered_by_root_remap"
STILL_MISSING = "still_missing"
MANUAL_CHECK_REQUIRED = "manual_check_required"
LOCAL_OUTPUT_ROOT_NEEDS_CREATE = "local_output_root_needs_create"
NOT_PATH_LIKE = "not_path_like"

FILE_ASSET_TYPES = {"cell_geometry", "met_forcing_file", "raster_tile", "svf_zip"}
RASTER_SUFFIXES = {".tif", ".tiff"}


@dataclass(frozen=True)
class CandidateRoot:
    """Configured root alias to test without copying assets."""

    root_alias: str
    root_path: Path
    root_kind: str
    commit_safe_to_reference: str
    notes: str


@dataclass(frozen=True)
class AssetRecoveryResult:
    """Return object for the F2b remap gate."""

    decision_status: str
    f2a_ready_runs: int
    f2b_ready_runs_strict: int
    f2b_ready_runs_if_output_root_created: int
    f2b_ready_runs_if_qgis_check_passes: int
    f2b_ready_runs_if_both_pass: int
    recovered_by_type: dict[str, int]
    still_missing_by_type: dict[str, int]
    selected_root_aliases: list[str]
    local_output_root_action: str
    files_created: list[Path]


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def parse_scalar(value: str) -> Any:
    """Parse the small scalar subset used in this config."""
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
        return stripped.strip("\"'")


def count_indent(line: str) -> int:
    """Return leading-space count."""
    return len(line) - len(line.lstrip(" "))


def split_key_value(text: str) -> tuple[str, str]:
    """Split one YAML-like key/value line."""
    key, sep, value = text.partition(":")
    if not sep:
        raise ValueError(f"Unsupported config line: {text}")
    return key.strip(), value.strip()


def read_simple_yaml(path: Path) -> dict[str, Any]:
    """Read the explicit YAML shape used by the F2b config."""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    config: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        indent = count_indent(line)
        if indent != 0:
            raise ValueError(f"Unexpected top-level indentation: {line}")
        key, value = split_key_value(line.strip())
        if value:
            config[key] = parse_scalar(value)
            index += 1
            continue
        if key in {"candidate_roots", "user_configured_extra_roots"}:
            items: list[dict[str, Any]] = []
            index += 1
            while index < len(lines) and count_indent(lines[index]) > indent:
                item_line = lines[index]
                if not item_line.strip().startswith("- "):
                    index += 1
                    continue
                item: dict[str, Any] = {}
                item_text = item_line.strip()[2:].strip()
                if item_text:
                    item_key, item_value = split_key_value(item_text)
                    item[item_key] = parse_scalar(item_value)
                index += 1
                while index < len(lines) and count_indent(lines[index]) >= indent + 4:
                    child_key, child_value = split_key_value(lines[index].strip())
                    item[child_key] = parse_scalar(child_value)
                    index += 1
                items.append(item)
            config[key] = items
            continue
        mapping: dict[str, Any] = {}
        index += 1
        while index < len(lines) and count_indent(lines[index]) > indent:
            child_key, child_value = split_key_value(lines[index].strip())
            mapping[child_key] = parse_scalar(child_value)
            index += 1
        config[key] = mapping
    return config


def read_config(path: Path) -> dict[str, Any]:
    """Load the F2b config without requiring external YAML packages."""
    return read_simple_yaml(path)


def repo_path(value: str | Path) -> Path:
    """Resolve a path relative to the OpenHeat project subdirectory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV into dictionaries."""
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write a UTF-8 CSV artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_text(path: Path, text: str) -> None:
    """Write a UTF-8 text artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git_output(args: list[str]) -> str:
    """Return stdout for a lightweight Git command."""
    completed = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def sorted_counter_text(counter: Counter[str] | dict[str, int]) -> str:
    """Format a count mapping as stable key=value text."""
    return "; ".join(f"{key}={counter[key]}" for key in sorted(counter) if counter[key])


def as_yes_no(value: Any) -> str:
    """Normalize boolean-ish values to yes/no."""
    lowered = clean(value).lower()
    if lowered in {"true", "1", "y", "yes"}:
        return YES
    return NO


def path_text(path: Path) -> str:
    """Return stable POSIX-style path text."""
    return path.as_posix()


def is_path_like(value: str) -> bool:
    """Return whether a value looks like a filesystem path."""
    if not value:
        return False
    normalized = value.replace("\\", "/")
    return "/" in normalized or bool(re.match(r"^[A-Za-z]:/", normalized))


def normalize_expected_path(value: str) -> Path:
    """Convert expected path text to a pathlib path."""
    return Path(value.replace("\\", "/"))


def safe_relative(path: Path, root: Path) -> str:
    """Return root-relative path text where possible."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def display_root_path(root: CandidateRoot) -> str:
    """Return a report-safe root path display."""
    raw = path_text(root.root_path)
    if raw.startswith("C:/OpenHeat-local"):
        return raw
    return f"<{root.root_alias}>"


def candidate_roots_from_config(config: dict[str, Any]) -> list[CandidateRoot]:
    """Build root aliases from config, including optional extra roots."""
    raw_roots = list(config.get("candidate_roots", []))
    raw_roots.extend(config.get("user_configured_extra_roots", []) or [])
    roots: list[CandidateRoot] = []
    for item in raw_roots:
        if not isinstance(item, dict):
            continue
        roots.append(
            CandidateRoot(
                root_alias=clean(item.get("root_alias")),
                root_path=Path(clean(item.get("root_path"))),
                root_kind=clean(item.get("root_kind")),
                commit_safe_to_reference=as_yes_no(item.get("commit_safe_to_reference")),
                notes=clean(item.get("notes")),
            )
        )
    return roots


def strip_data_solweig(path: Path) -> Path | None:
    """Return path with leading data/solweig removed when present."""
    parts = path.parts
    if len(parts) >= 3 and parts[0] == "data" and parts[1] == "solweig":
        return Path(*parts[2:])
    return None


def build_direct_candidates(expected: str, root: CandidateRoot) -> list[Path]:
    """Build direct candidate paths for one expected asset under one root."""
    expected_path = normalize_expected_path(expected)
    candidates: list[Path] = []
    if expected_path.is_absolute():
        candidates.append(expected_path)
        return candidates
    candidates.append(root.root_path / expected_path)
    stripped = strip_data_solweig(expected_path)
    if stripped is not None and root.root_alias in {"openheat_local_solweig", "openheat_local_root"}:
        candidates.append(root.root_path / stripped)
    if stripped is not None and stripped.parts and stripped.parts[0] == "v12_n24_tiles":
        candidates.append(root.root_path / Path(*stripped.parts))
    return candidates


def met_glob_patterns(expected: str) -> list[str]:
    """Return conservative met-forcing glob patterns for one expected file."""
    name = Path(expected.replace("\\", "/")).name
    match = re.search(r"(?P<date>\d{4}_?\d{2}_?\d{2}).*S(?P<station>\d+).*h(?P<hour>\d{1,2})", name)
    if not match:
        return [name]
    raw_date = match.group("date").replace("_", "")
    yyyy, mm, dd = raw_date[:4], raw_date[4:6], raw_date[6:8]
    station = f"S{match.group('station')}"
    hour = f"h{int(match.group('hour')):02d}"
    return [
        f"*{yyyy}*{mm}*{dd}*{station}*{hour}*.txt",
        f"*{yyyy}_{mm}_{dd}*{station}*{hour}*.txt",
        f"*{yyyy}{mm}{dd}*{station}*{hour}*.txt",
    ]


def first_existing(candidates: Iterable[Path]) -> Path | None:
    """Return the first existing path without opening file contents."""
    seen: set[str] = set()
    for candidate in candidates:
        key = path_text(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return None


def find_asset_candidates(asset: dict[str, str], roots: list[CandidateRoot]) -> list[dict[str, Any]]:
    """Find existence candidates for one F2a missing/manual asset."""
    asset_type = clean(asset.get("asset_type"))
    expected = clean(asset.get("expected_path"))
    if asset_type == "qgis_algorithm_manual_check":
        return []
    if asset_type == "local_output_root":
        expected_path = normalize_expected_path(expected)
        return [
            {
                "root_alias": "openheat_local_solweig",
                "candidate_path": expected_path,
                "candidate_relative_path": expected_path.name,
                "exists": expected_path.exists(),
                "match_method": "local_output_root_exists",
            }
        ]
    if not is_path_like(expected):
        return []

    matches: list[dict[str, Any]] = []
    for root in roots:
        direct_candidates = build_direct_candidates(expected, root)
        direct = first_existing(direct_candidates)
        if direct is not None:
            matches.append(
                {
                    "root_alias": root.root_alias,
                    "candidate_path": direct,
                    "candidate_relative_path": safe_relative(direct, root.root_path),
                    "exists": True,
                    "match_method": "direct_path",
                }
            )
            continue
        if asset_type == "met_forcing_file" and root.root_path.exists():
            found: Path | None = None
            for pattern in met_glob_patterns(expected):
                for candidate in root.root_path.glob(f"**/{pattern}"):
                    if candidate.exists():
                        found = candidate
                        break
                if found is not None:
                    break
            if found is not None:
                matches.append(
                    {
                        "root_alias": root.root_alias,
                        "candidate_path": found,
                        "candidate_relative_path": safe_relative(found, root.root_path),
                        "exists": True,
                        "match_method": "met_forcing_glob",
                    }
                )
    return matches


def selected_match(matches: list[dict[str, Any]], roots: list[CandidateRoot]) -> dict[str, Any] | None:
    """Pick the first match according to configured root order."""
    order = {root.root_alias: index for index, root in enumerate(roots)}
    existing = [match for match in matches if match.get("exists")]
    if not existing:
        return None
    return sorted(existing, key=lambda row: order.get(clean(row.get("root_alias")), 999))[0]


def split_missing_assets(value: str) -> list[str]:
    """Parse F2a per-run missing fields into expected path strings."""
    paths: list[str] = []
    for chunk in clean(value).split(";"):
        if not chunk.strip():
            continue
        _, sep, tail = chunk.partition(":")
        candidate = tail if sep else chunk
        candidate = candidate.strip()
        if candidate:
            paths.append(candidate)
    return paths


def row_for_expected(remap_by_expected: dict[str, dict[str, Any]], expected: str) -> dict[str, Any] | None:
    """Return remap row by normalized expected path."""
    return remap_by_expected.get(clean(expected).replace("\\", "/"))


def is_recovered(remap_by_expected: dict[str, dict[str, Any]], expected: str) -> bool:
    """Return whether an expected path was recovered."""
    row = row_for_expected(remap_by_expected, expected)
    return bool(row and row.get("remap_status") == RECOVERED)


def any_unrecovered(remap_by_expected: dict[str, dict[str, Any]], paths: Iterable[str]) -> bool:
    """Return whether any path remains unrecovered."""
    return any(not is_recovered(remap_by_expected, path) for path in paths)


def has_unrecovered_raster(remap_by_expected: dict[str, dict[str, Any]], paths: Iterable[str]) -> bool:
    """Return whether any raster path remains unrecovered."""
    for path in paths:
        if Path(path).suffix.lower() in RASTER_SUFFIXES and not is_recovered(remap_by_expected, path):
            return True
    return False


def make_root_inventory(
    roots: list[CandidateRoot],
    recovery_rows: list[dict[str, Any]],
    remap_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Summarize root candidate existence and match counts."""
    all_matches = Counter(clean(row["candidate_root_alias"]) for row in recovery_rows if row["candidate_exists"] == YES)
    selected = Counter(clean(row["selected_root_alias"]) for row in remap_rows if clean(row["selected_root_alias"]))
    file_matches = Counter(
        clean(row["candidate_root_alias"])
        for row in recovery_rows
        if row["candidate_exists"] == YES and clean(row["asset_type"]) in FILE_ASSET_TYPES
    )
    rows: list[dict[str, Any]] = []
    for root in roots:
        rows.append(
            {
                "root_alias": root.root_alias,
                "root_kind": root.root_kind,
                "root_path_display": display_root_path(root),
                "root_exists": YES if root.root_path.exists() else NO,
                "root_parent_exists": YES if root.root_path.parent.exists() else NO,
                "commit_safe_to_reference": root.commit_safe_to_reference,
                "matched_missing_assets": all_matches[root.root_alias],
                "matched_file_assets": file_matches[root.root_alias],
                "selected_missing_assets": selected[root.root_alias],
                "notes": root.notes,
            }
        )
    return rows


def local_output_root_plan(expected: str) -> tuple[str, list[dict[str, Any]]]:
    """Create a plan row for the local output root without creating it."""
    path = normalize_expected_path(expected)
    exists = path.exists()
    parent_exists = path.parent.exists()
    if exists:
        action = "exists_no_action"
    elif parent_exists:
        action = "human_create_directory"
    else:
        action = "human_create_parent_and_directory"
    command = f"New-Item -ItemType Directory -Force -Path '{path_text(path)}'"
    return action, [
        {
            "local_output_root_alias": "openheat_local_solweig/b85_f1_tiles",
            "local_output_root_display": path_text(path),
            "exists": YES if exists else NO,
            "parent_exists": YES if parent_exists else NO,
            "inside_git_worktree": YES if is_inside_git(path) else NO,
            "create_local_output_root": NO,
            "human_command_if_missing": "" if exists else command,
            "notes": "Local-only manual QGIS output root; this script did not create it.",
        }
    ]


def is_inside_git(path: Path) -> bool:
    """Return whether a path is inside the current Git root."""
    git_root_text = git_output(["git", "rev-parse", "--show-toplevel"])
    if not git_root_text:
        return False
    try:
        path.resolve().relative_to(Path(git_root_text).resolve())
        return True
    except ValueError:
        return False


def compute_run_readiness(
    f2a_run_rows: list[dict[str, str]],
    remap_by_expected: dict[str, dict[str, Any]],
    local_output_root_exists: bool,
) -> list[dict[str, Any]]:
    """Recompute per-run readiness using remapped file assets."""
    rows: list[dict[str, Any]] = []
    for run in f2a_run_rows:
        cell_paths = split_missing_assets(run.get("missing_cell_assets", ""))
        scenario_paths = split_missing_assets(run.get("missing_scenario_inputs", ""))
        svf_paths = split_missing_assets(run.get("missing_svf_assets", ""))
        met_paths = split_missing_assets(run.get("missing_met_forcing", ""))
        blocked_cell = any_unrecovered(remap_by_expected, cell_paths)
        blocked_raster = has_unrecovered_raster(remap_by_expected, [*cell_paths, *scenario_paths])
        blocked_svf = any_unrecovered(remap_by_expected, svf_paths)
        blocked_met = any_unrecovered(remap_by_expected, met_paths)
        blocked_output = not local_output_root_exists
        blocked_manual = True
        file_blocked = blocked_cell or blocked_raster or blocked_svf or blocked_met
        ready_strict = not (file_blocked or blocked_output or blocked_manual)
        ready_if_qgis = not (file_blocked or blocked_output)
        ready_if_output = not (file_blocked or blocked_manual)
        ready_if_both = not file_blocked
        partial_manual_only = (not file_blocked) and (not blocked_output) and blocked_manual
        status_parts = []
        if blocked_cell:
            status_parts.append("blocked_missing_cell_asset")
        if blocked_met:
            status_parts.append("blocked_missing_met_forcing")
        if blocked_svf:
            status_parts.append("blocked_missing_svf")
        if blocked_raster:
            status_parts.append("blocked_missing_raster")
        if blocked_output:
            status_parts.append("blocked_local_output_root")
        if blocked_manual:
            status_parts.append("blocked_manual_check_required")
        if not status_parts:
            status_parts.append("ready_for_manual_qgis_after_remap")
        rows.append(
            {
                "run_id": run.get("run_id", ""),
                "cell_id": run.get("cell_id", ""),
                "forcing_day_id": run.get("forcing_day_id", ""),
                "date": run.get("date", ""),
                "hour_sgt": run.get("hour_sgt", ""),
                "scenario": run.get("scenario", ""),
                "expected_output_group": run.get("expected_output_group", ""),
                "ready_for_manual_qgis_after_remap": YES if ready_strict else NO,
                "blocked_missing_cell_asset": YES if blocked_cell else NO,
                "blocked_missing_met_forcing": YES if blocked_met else NO,
                "blocked_missing_svf": YES if blocked_svf else NO,
                "blocked_missing_raster": YES if blocked_raster else NO,
                "blocked_local_output_root": YES if blocked_output else NO,
                "blocked_manual_check_required": YES if blocked_manual else NO,
                "partial_manual_check_only": YES if partial_manual_only else NO,
                "ready_if_qgis_manual_check_passes": YES if ready_if_qgis else NO,
                "ready_if_output_root_created": YES if ready_if_output else NO,
                "ready_if_output_root_created_and_qgis_manual_check_passes": YES if ready_if_both else NO,
                "run_readiness_after_remap": "; ".join(status_parts),
                "qgis_solweig_executed": NO,
            }
        )
    return rows


def decide(
    total_runs: int,
    recovered_file_count: int,
    ready_if_both: int,
    local_output_root_exists: bool,
) -> str:
    """Return the B8.5-F2b decision status."""
    if total_runs == 0:
        return BLOCKED
    if recovered_file_count == 0:
        return NO_ASSET_ROOT_FOUND
    if ready_if_both == total_runs and local_output_root_exists:
        return READY_AFTER_REMAP
    if ready_if_both == total_runs and not local_output_root_exists:
        return READY_IF_OUTPUT_ROOT_CREATED
    return PARTIAL_REMAP_AVAILABLE


def make_markdown_list(values: Iterable[Path]) -> str:
    """Format path list for reports."""
    rows: list[str] = []
    for path in values:
        try:
            display = path.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            display = path.name
        rows.append(f"- `{display}`")
    return "\n".join(rows)


def write_manual_checklist(
    path: Path,
    decision: str,
    selected_aliases: list[str],
    local_output_root_action: str,
    recovered_by_type: Counter[str],
    still_missing_by_type: Counter[str],
) -> None:
    """Write the manual remap checklist."""
    text = f"""# B8.5-F2b Manual Remap Checklist

Generated: {now_stamp()}

## Decision

`{decision}`

## Safe execution boundary

- QGIS/SOLWEIG executed: `no`
- No rasters were created, copied, opened for analysis, or staged.
- `svfs.zip` was not copied or opened.
- This is not B9, not local WBGT, not hazard_score, not risk, and not System A/B coupling.
- This only determines whether local assets can be found/remapped for later manual execution.

## Human checks before manual QGIS

- Confirm QGIS/UMEP SOLWEIG algorithm availability manually.
- Confirm the selected root aliases are available on the execution machine: `{", ".join(selected_aliases) or "none"}`.
- Local output root action: `{local_output_root_action}`.
- Do not copy raster tiles or `svfs.zip` into Git.
- Keep manual SOLWEIG outputs under the local-only root convention.

## Recovered assets by type

`{sorted_counter_text(recovered_by_type) or "none"}`

## Still missing assets by type

`{sorted_counter_text(still_missing_by_type) or "none"}`
"""
    write_text(path, text)


def write_cn_doc(
    path: Path,
    decision: str,
    f2a_ready: int,
    strict_ready: int,
    if_output: int,
    if_qgis: int,
    if_both: int,
    recovered_by_type: Counter[str],
    still_missing_by_type: Counter[str],
    selected_aliases: list[str],
    local_output_root_action: str,
) -> None:
    """Write the UTF-8 Chinese note."""
    text = f"""# OpenHeat System B B8.5-F2b 本地资产恢复与路径重映射说明

生成时间：{now_stamp()}

## 结论

本次门禁状态为 `{decision}`。F2a 就绪运行数为 `0/480`；F2b 严格就绪运行数为 `{strict_ready}/480`。若仅由人工创建本地输出目录，则就绪运行数为 `{if_output}/480`；若 QGIS 算法人工检查通过，则就绪运行数为 `{if_qgis}/480`；若本地输出目录已创建且 QGIS 算法人工检查通过，则就绪运行数为 `{if_both}/480`。

恢复资产计数：`{sorted_counter_text(recovered_by_type) or "none"}`。
仍缺失资产计数：`{sorted_counter_text(still_missing_by_type) or "none"}`。
已选择根别名：`{", ".join(selected_aliases) or "none"}`。
本地输出目录动作：`{local_output_root_action}`。

## 范围边界

本次工作只是 B8.5-F2b 本地 SOLWEIG 资产发现、根别名重映射与就绪模拟门禁。QGIS 没有运行，SOLWEIG 没有运行；没有创建、复制、打开分析或暂存任何 raster；没有复制或打开 `svfs.zip`；没有创建 AOI-wide prediction；没有创建 local WBGT、`hazard_score`、`risk_score` 或 System A/B coupling 输出。

这不是 B9，不是本地 WBGT 预测，不是风险图，也不是风险评分。它只判断人工执行前所需的本地资产是否可通过根别名找到和引用。实际人工 QGIS 执行仍需要人工确认。

## 路径卫生

报告优先使用根别名与相对路径，不把本地用户目录作为可移植约定。`C:/OpenHeat-local/...` 只作为 Git 工作树外的本地执行约定；大体量 raster 与 `svfs.zip` 不应复制进本工作树，也不应提交。

## 下一步

先按 `b85_f2b_manual_remap_checklist.md` 完成人工检查。若状态不是 `READY_AFTER_REMAP`，应先解决仍缺失的文件资产或创建本地输出目录，然后重新运行本门禁。只有人工确认 QGIS/UMEP 算法可用后，才可进入后续手动执行。
"""
    if f2a_ready != 0:
        text += f"\n备注：检测到 F2a ready runs 为 `{f2a_ready}`，与预期 0 不同，请复核输入摘要。\n"
    write_text(path, text)


def write_status(
    path: Path,
    decision: str,
    result_counts: dict[str, int],
    recovered_by_type: Counter[str],
    still_missing_by_type: Counter[str],
    selected_aliases: list[str],
    local_output_root_action: str,
    files_created: list[Path],
) -> None:
    """Write the lane status Markdown."""
    text = f"""# B8.5-F2b Status

Generated: {now_stamp()}

## Status

`{decision}`

## Scope

Local SOLWEIG asset discovery, root remap, and readiness simulation only. QGIS/SOLWEIG was not run. No rasters were created, copied, opened for analysis, or staged. `svfs.zip` was not copied or opened. This is not B9. This is not local WBGT. This is not risk. No AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling output was created.

## Key Results

- F2a ready runs: `{result_counts["f2a_ready"]}/480`
- F2b ready runs strict: `{result_counts["strict"]}/480`
- F2b ready runs if output root created: `{result_counts["if_output"]}/480`
- F2b ready runs if QGIS check passes: `{result_counts["if_qgis"]}/480`
- F2b ready runs if output root created and QGIS check passes: `{result_counts["if_both"]}/480`
- Recovered assets by type: `{sorted_counter_text(recovered_by_type) or "none"}`
- Still missing assets by type: `{sorted_counter_text(still_missing_by_type) or "none"}`
- Selected root aliases: `{", ".join(selected_aliases) or "none"}`
- Local output root action: `{local_output_root_action}`
- QGIS/SOLWEIG executed: `no`

## Files Created / Modified

{make_markdown_list(files_created)}

## Caveats

Actual manual QGIS execution requires human confirmation of the QGIS/UMEP SOLWEIG algorithm and local-only output directory. Root aliases are discovery references only; large assets must remain uncommitted.
"""
    write_text(path, text)


def run(config_path: Path) -> AssetRecoveryResult:
    """Run the F2b asset recovery/remap gate."""
    config = read_config(config_path)
    roots = candidate_roots_from_config(config)
    outputs = config.get("outputs", {})
    required_inputs = [
        repo_path(config["f2a_missing_assets_path"]),
        repo_path(config["f2a_run_readiness_path"]),
        repo_path(config["f0_run_matrix_path"]),
        repo_path(config["f1_required_asset_inventory_path"]),
    ]
    missing_inputs = [path for path in required_inputs if not path.exists()]
    if missing_inputs:
        raise FileNotFoundError("Missing required F2b inputs: " + ", ".join(path_text(path) for path in missing_inputs))

    f2a_missing = read_csv_rows(required_inputs[0])
    f2a_runs = read_csv_rows(required_inputs[1])
    f0_runs = read_csv_rows(required_inputs[2])
    if not f0_runs:
        raise ValueError("F0 run matrix has no rows.")

    f2a_summary_path = repo_path(config.get("f2a_summary_path", ""))
    f2a_ready = 0
    if f2a_summary_path.exists():
        summary_rows = read_csv_rows(f2a_summary_path)
        if summary_rows:
            f2a_ready = int(summary_rows[0].get("ready_run_count", "0") or 0)

    recovery_rows: list[dict[str, Any]] = []
    remap_rows: list[dict[str, Any]] = []
    root_by_alias = {root.root_alias: root for root in roots}

    for asset in f2a_missing:
        asset_type = clean(asset.get("asset_type"))
        logical_name = clean(asset.get("logical_name"))
        expected = clean(asset.get("expected_path"))
        matches = find_asset_candidates(asset, roots)
        for match in matches:
            recovery_rows.append(
                {
                    "asset_type": asset_type,
                    "logical_name": logical_name,
                    "original_expected_path": expected,
                    "candidate_root_alias": match["root_alias"],
                    "candidate_relative_path": match["candidate_relative_path"],
                    "candidate_exists": YES if match["exists"] else NO,
                    "match_method": match["match_method"],
                    "notes": "Existence check only; file contents were not opened.",
                }
            )
        selected = selected_match(matches, roots)
        if asset_type == "qgis_algorithm_manual_check":
            remap_status = MANUAL_CHECK_REQUIRED
        elif not is_path_like(expected):
            remap_status = NOT_PATH_LIKE
        elif asset_type == "local_output_root":
            remap_status = RECOVERED if selected and selected["exists"] else LOCAL_OUTPUT_ROOT_NEEDS_CREATE
        elif selected:
            remap_status = RECOVERED
        else:
            remap_status = STILL_MISSING
        selected_alias = clean(selected.get("root_alias")) if selected else ""
        selected_root = root_by_alias.get(selected_alias)
        asset_commit_safe = as_yes_no(asset.get("commit_safe"))
        commit_safe = YES if selected_root and selected_root.commit_safe_to_reference == YES and asset_commit_safe == YES else NO
        can_use = YES if remap_status == RECOVERED else NO
        notes = "Root-alias remap only; do not copy or stage assets."
        if asset_type in {"raster_tile", "svf_zip"}:
            notes += " Large asset is not commit-safe; reference only."
        if remap_status == MANUAL_CHECK_REQUIRED:
            notes = "QGIS/UMEP algorithm availability must be checked manually."
        if remap_status == LOCAL_OUTPUT_ROOT_NEEDS_CREATE:
            notes = "Local-only output root must be created by a human outside Git."
        remap_rows.append(
            {
                "asset_type": asset_type,
                "logical_name": logical_name,
                "original_expected_path": expected,
                "selected_root_alias": selected_alias,
                "selected_relative_path": clean(selected.get("candidate_relative_path")) if selected else "",
                "selected_path_exists": YES if selected else NO,
                "remap_status": remap_status,
                "commit_safe": commit_safe,
                "can_use_for_manual_execution": can_use,
                "notes": notes,
            }
        )

    remap_by_expected = {clean(row["original_expected_path"]).replace("\\", "/"): row for row in remap_rows}
    local_output_expected = clean(config.get("local_output_root_expected"))
    local_output_action, local_output_rows = local_output_root_plan(local_output_expected)
    local_output_exists = local_output_rows[0]["exists"] == YES
    run_rows = compute_run_readiness(f2a_runs, remap_by_expected, local_output_exists)

    strict_ready = sum(1 for row in run_rows if row["ready_for_manual_qgis_after_remap"] == YES)
    if_output = sum(1 for row in run_rows if row["ready_if_output_root_created"] == YES)
    if_qgis = sum(1 for row in run_rows if row["ready_if_qgis_manual_check_passes"] == YES)
    if_both = sum(1 for row in run_rows if row["ready_if_output_root_created_and_qgis_manual_check_passes"] == YES)

    recovered_by_type: Counter[str] = Counter(
        clean(row["asset_type"]) for row in remap_rows if row["remap_status"] == RECOVERED and clean(row["asset_type"]) in FILE_ASSET_TYPES
    )
    still_missing_by_type: Counter[str] = Counter(
        clean(row["asset_type"])
        for row in remap_rows
        if row["remap_status"] in {STILL_MISSING, LOCAL_OUTPUT_ROOT_NEEDS_CREATE, MANUAL_CHECK_REQUIRED}
    )
    missing_after_rows = [
        row for row in remap_rows if row["remap_status"] in {STILL_MISSING, LOCAL_OUTPUT_ROOT_NEEDS_CREATE, MANUAL_CHECK_REQUIRED}
    ]
    selected_aliases = sorted({clean(row["selected_root_alias"]) for row in remap_rows if clean(row["selected_root_alias"])})
    recovered_file_count = sum(recovered_by_type.values())
    decision = decide(len(f0_runs), recovered_file_count, if_both, local_output_exists)

    root_inventory_rows = make_root_inventory(roots, recovery_rows, remap_rows)
    by_missing_rows = []
    for asset in f2a_missing:
        expected = clean(asset.get("expected_path"))
        asset_matches = [row for row in recovery_rows if row["original_expected_path"] == expected]
        by_missing_rows.append(
            {
                "asset_type": clean(asset.get("asset_type")),
                "logical_name": clean(asset.get("logical_name")),
                "original_expected_path": expected,
                "candidate_match_count": len([row for row in asset_matches if row["candidate_exists"] == YES]),
                "candidate_root_aliases": "; ".join(sorted({row["candidate_root_alias"] for row in asset_matches})),
                "selected_root_alias": clean(remap_by_expected.get(expected.replace("\\", "/"), {}).get("selected_root_alias")),
                "remap_status": clean(remap_by_expected.get(expected.replace("\\", "/"), {}).get("remap_status")),
                "notes": "Existence discovery only; no asset copy/open.",
            }
        )
    met_plan_rows = [
        {
            "logical_name": row["logical_name"],
            "original_expected_path": row["original_expected_path"],
            "selected_root_alias": row["selected_root_alias"],
            "selected_relative_path": row["selected_relative_path"],
            "remap_status": row["remap_status"],
            "action": "use_root_alias_remap" if row["remap_status"] == RECOVERED else "locate_or_regenerate_met_forcing_locally",
            "notes": "Met forcing discovery used exact path plus conservative date/station/hour glob patterns.",
        }
        for row in remap_rows
        if row["asset_type"] == "met_forcing_file"
    ]

    delta_rows = [
        {
            "decision_status": decision,
            "f2a_ready_runs": f2a_ready,
            "f2b_ready_runs_strict": strict_ready,
            "f2b_ready_runs_if_output_root_created": if_output,
            "f2b_ready_runs_if_qgis_check_passes": if_qgis,
            "f2b_ready_runs_if_output_root_created_and_qgis_check_passes": if_both,
            "missing_asset_count_before": len(f2a_missing),
            "missing_asset_count_after": len(missing_after_rows),
            "recovered_asset_count_by_type": sorted_counter_text(recovered_by_type),
            "still_missing_by_type": sorted_counter_text(still_missing_by_type),
            "selected_root_aliases": "; ".join(selected_aliases),
            "local_output_root_action": local_output_action,
            "qgis_solweig_executed": NO,
        }
    ]

    files_created = [
        repo_path(outputs["root_candidate_inventory"]),
        repo_path(outputs["by_missing_asset"]),
        repo_path(outputs["remap_table"]),
        repo_path(outputs["missing_after_remap"]),
        repo_path(outputs["run_readiness_after_remap"]),
        repo_path(outputs["readiness_delta_summary"]),
        repo_path(outputs["local_output_root_plan"]),
        repo_path(outputs["met_forcing_recovery_plan"]),
        repo_path(outputs["manual_remap_checklist"]),
        repo_path(outputs["status"]),
        repo_path(outputs["canonical_note_cn"]),
    ]

    write_csv_rows(files_created[0], root_inventory_rows, list(root_inventory_rows[0].keys()))
    write_csv_rows(files_created[1], by_missing_rows, list(by_missing_rows[0].keys()))
    remap_fields = [
        "asset_type",
        "logical_name",
        "original_expected_path",
        "selected_root_alias",
        "selected_relative_path",
        "selected_path_exists",
        "remap_status",
        "commit_safe",
        "can_use_for_manual_execution",
        "notes",
    ]
    write_csv_rows(files_created[2], remap_rows, remap_fields)
    write_csv_rows(files_created[3], missing_after_rows, remap_fields)
    write_csv_rows(files_created[4], run_rows, list(run_rows[0].keys()))
    write_csv_rows(files_created[5], delta_rows, list(delta_rows[0].keys()))
    write_csv_rows(files_created[6], local_output_rows, list(local_output_rows[0].keys()))
    write_csv_rows(files_created[7], met_plan_rows, list(met_plan_rows[0].keys()) if met_plan_rows else [
        "logical_name",
        "original_expected_path",
        "selected_root_alias",
        "selected_relative_path",
        "remap_status",
        "action",
        "notes",
    ])
    write_manual_checklist(files_created[8], decision, selected_aliases, local_output_action, recovered_by_type, still_missing_by_type)
    result_counts = {
        "f2a_ready": f2a_ready,
        "strict": strict_ready,
        "if_output": if_output,
        "if_qgis": if_qgis,
        "if_both": if_both,
    }
    write_status(
        files_created[9],
        decision,
        result_counts,
        recovered_by_type,
        still_missing_by_type,
        selected_aliases,
        local_output_action,
        files_created,
    )
    write_cn_doc(
        files_created[10],
        decision,
        f2a_ready,
        strict_ready,
        if_output,
        if_qgis,
        if_both,
        recovered_by_type,
        still_missing_by_type,
        selected_aliases,
        local_output_action,
    )

    return AssetRecoveryResult(
        decision_status=decision,
        f2a_ready_runs=f2a_ready,
        f2b_ready_runs_strict=strict_ready,
        f2b_ready_runs_if_output_root_created=if_output,
        f2b_ready_runs_if_qgis_check_passes=if_qgis,
        f2b_ready_runs_if_both_pass=if_both,
        recovered_by_type=dict(recovered_by_type),
        still_missing_by_type=dict(still_missing_by_type),
        selected_root_aliases=selected_aliases,
        local_output_root_action=local_output_action,
        files_created=files_created,
    )


def main() -> int:
    """Parse CLI args and run the B8.5-F2b remap gate."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F2b local SOLWEIG asset recovery/remap artifacts "
            "without copying assets or calling QGIS/SOLWEIG."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F2b YAML config path.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(f"Decision status: {result.decision_status}")
    print(f"F2a ready runs: {result.f2a_ready_runs}/480")
    print(f"F2b ready runs strict: {result.f2b_ready_runs_strict}/480")
    print(f"F2b ready runs if output root created: {result.f2b_ready_runs_if_output_root_created}/480")
    print(f"F2b ready runs if QGIS check passes: {result.f2b_ready_runs_if_qgis_check_passes}/480")
    print(
        "F2b ready runs if output root created and QGIS check passes: "
        f"{result.f2b_ready_runs_if_both_pass}/480"
    )
    print(f"Recovered asset count by type: {sorted_counter_text(result.recovered_by_type) or 'none'}")
    print(f"Still missing asset count by type: {sorted_counter_text(result.still_missing_by_type) or 'none'}")
    print(f"Selected root aliases: {', '.join(result.selected_root_aliases) or 'none'}")
    print(f"Local output root action: {result.local_output_root_action}")
    print("QGIS/SOLWEIG executed: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path_text(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
