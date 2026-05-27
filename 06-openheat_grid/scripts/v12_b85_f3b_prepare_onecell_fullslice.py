"""Prepare the B8.5-F3b one-cell full-slice QGIS/SOLWEIG package.

Inputs:
    configs/v12/systemb_b85_f3b_onecell_fullslice.yaml
    outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_run_readiness.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv
    outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_raster_qa_report.md
    scripts/qgis/v12_b85_f3a_microbatch_qgis_runner.py

Outputs:
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_onecell_manifest.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_pre_execution_asset_check.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_expected_run_log_schema.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_manual_qgis_run_instructions.md
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_postrun_validation.csv
    docs/v12/OpenHeat_SystemB_B8_5_F3b_onecell_fullslice_CN.md
    outputs/v12_surrogate/b8_5_f3b_onecell/B8_5_F3B_STATUS.md

Saved metrics:
    Exact 20-run manifest, per-run pre-execution readiness flags, expected
    output paths, expected run-log schema, postrun placeholder rows, and final
    preparation decision status.

This script does not run QGIS, run SOLWEIG, create/copy/move/open rasters,
copy/open svfs.zip, create AOI-wide predictions, compute local WBGT, create
hazard_score or risk_score outputs, create System A/B coupling outputs, stage,
or commit. It prepares human-controlled execution only.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f3b_onecell_fullslice.yaml"

YES = "yes"
NO = "no"
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
FAILED = "FAILED"
NOT_RUN_YET = "NOT_RUN_YET"
READY_FOR_HUMAN_ONECELL_SLICE = "READY_FOR_HUMAN_ONECELL_SLICE"
ONECELL_SLICE_EXECUTED_PASS = "ONECELL_SLICE_EXECUTED_PASS"
ONECELL_SLICE_EXECUTED_PARTIAL = "ONECELL_SLICE_EXECUTED_PARTIAL"
BLOCKED_PRECHECK = "BLOCKED_PRECHECK"
BLOCKED_POSTRUN = "BLOCKED_POSTRUN"

FORBIDDEN_SCOPE_TRUE_KEYS = {
    "qgis_executed_by_codex",
    "solweig_executed_by_codex",
    "create_rasters",
    "copy_rasters",
    "open_rasters_in_preparation",
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
class PrepareResult:
    """Compact result for the F3b preparation run."""

    decision_status: str
    manifest_run_count: int
    pre_execution_ready_count: int
    postrun_status: str
    raster_qa_status: str
    local_run_log_path: Path
    files_created: list[Path]


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def repo_path(value: str | Path) -> Path:
    """Resolve repository-relative paths against the OpenHeat subdirectory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: Path | str) -> str:
    """Return a repository-relative POSIX path when possible."""
    p = repo_path(path)
    try:
        return p.resolve(strict=False).relative_to(ROOT.resolve(strict=False)).as_posix()
    except ValueError:
        return p.as_posix()


def path_text(path: Path | str) -> str:
    """Return a slash-separated path string."""
    return Path(path).as_posix()


def parse_inline_list(text: str) -> list[Any]:
    """Parse a small YAML inline list."""
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    return [parse_scalar(part.strip()) for part in inner.split(",")]


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by project configs."""
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return parse_inline_list(stripped)
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
            parent.append(parse_scalar(text[2:].strip()))
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
            raise ValueError(f"Config did not parse to a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV as dictionaries."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv_rows(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    """Write dictionaries as UTF-8 CSV with stable field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_text(path: Path, text: str) -> None:
    """Write a UTF-8 text artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def markdown_table(rows: Sequence[dict[str, Any]], columns: Sequence[str], max_rows: int | None = None) -> str:
    """Render a compact Markdown table."""
    selected = list(rows[:max_rows]) if max_rows is not None else list(rows)
    if not selected:
        return "_No rows._"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in selected:
        vals = [clean(row.get(col, "")).replace("|", "/") for col in columns]
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep, *body])


def is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is below parent after non-strict resolution."""
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def git_root() -> Path:
    """Return the Git worktree root."""
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    text = completed.stdout.strip()
    return Path(text) if text else ROOT


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


def changed_forbidden_paths(status_lines: Iterable[str]) -> list[str]:
    """Identify forbidden changed files from Git status output."""
    forbidden_fragments = [
        "data/solweig/",
        "data/rasters/",
        "data/archive/",
        "svfs.zip",
        "hourly_grid_heatstress_forecast",
    ]
    forbidden_suffixes = (".tif", ".tiff", ".zip")
    hits: list[str] = []
    for line in status_lines:
        path = line[3:].replace("\\", "/")
        lower = path.lower()
        if lower.endswith(forbidden_suffixes) or any(fragment in lower for fragment in forbidden_fragments):
            hits.append(path)
    return hits


def onecell(config: dict[str, Any]) -> dict[str, Any]:
    """Return the one-cell full-slice config section."""
    return config["onecell_fullslice"]


def expected_run_count(config: dict[str, Any]) -> int:
    """Return forcing-days x hours x scenarios run count."""
    section = onecell(config)
    return len(section["forcing_days"]) * len(section["hours_sgt"]) * len(section["scenarios"])


def normalize_yes(value: Any) -> bool:
    """Return True for project yes-like values."""
    return clean(value).lower() in {"yes", "true", "pass", "ready_for_manual_qgis"}


def normalize_pass(value: Any) -> bool:
    """Return True for project PASS-like values."""
    return clean(value).upper() == PASS


def ensure_scope_is_preparation_only(config: dict[str, Any]) -> None:
    """Refuse a config that crosses the F3b preparation boundary."""
    scope = config.get("scope", {})
    bad = [key for key in FORBIDDEN_SCOPE_TRUE_KEYS if bool(scope.get(key))]
    if bad:
        raise ValueError(f"Forbidden scope flags must remain false: {', '.join(sorted(bad))}")
    section = onecell(config)
    required_false = {
        "execute_qgis_or_solweig": section.get("execute_qgis_or_solweig"),
        "write_raster_outputs_from_python": section.get("write_raster_outputs_from_python"),
    }
    bad_false = [f"{key}={value!r}" for key, value in required_false.items() if value is not False]
    if bad_false:
        raise ValueError("Unsafe one-cell config flags: " + "; ".join(bad_false))
    if section.get("repo_runner_dry_run") is not True:
        raise ValueError("onecell_fullslice.repo_runner_dry_run must remain true.")
    if int(section["expected_run_count"]) != expected_run_count(config):
        raise ValueError("expected_run_count must equal forcing_days x hours_sgt x scenarios.")
    if int(section["expected_run_count"]) != 20:
        raise ValueError("F3b one-cell full slice must contain exactly 20 runs.")


def row_key(row: dict[str, str]) -> tuple[str, str, int, str]:
    """Return the canonical run key for F0/F2d rows."""
    return (
        clean(row.get("cell_id")),
        clean(row.get("forcing_day_id")),
        int(clean(row.get("hour_sgt"))),
        clean(row.get("scenario")),
    )


def expected_keys(config: dict[str, Any]) -> list[tuple[str, str, int, str]]:
    """Return the exact ordered F3b run keys."""
    section = onecell(config)
    keys: list[tuple[str, str, int, str]] = []
    for forcing_day in section["forcing_days"]:
        for hour in section["hours_sgt"]:
            for scenario in section["scenarios"]:
                keys.append((section["cell_id"], forcing_day, int(hour), scenario))
    return keys


def f2d_row_ready(row: dict[str, str]) -> bool:
    """Return whether an F2d readiness row passes required prechecks."""
    return (
        normalize_yes(row.get("cell_geometry_ready"))
        and normalize_yes(row.get("raster_tiles_ready"))
        and normalize_yes(row.get("svf_ready"))
        and normalize_yes(row.get("met_forcing_ready"))
        and normalize_yes(row.get("output_root_ready"))
        and normalize_pass(row.get("qgis_manual_check_status"))
        and normalize_yes(row.get("ready_for_manual_qgis"))
        and clean(row.get("run_readiness")).lower() == "ready_for_manual_qgis"
    )


def expected_output_group(config: dict[str, Any], key: tuple[str, str, int, str]) -> str:
    """Return the F3b expected output group for one run."""
    cell_id, forcing_day, hour, scenario = key
    prefix = str(onecell(config)["expected_output_group_prefix"])
    return f"{prefix}/{forcing_day}/{cell_id}/{scenario}/h{hour:02d}"


def expected_output_dir(config: dict[str, Any], group: str) -> Path:
    """Return the expected local-only SOLWEIG output directory."""
    return Path(str(onecell(config)["local_solweig_output_root"])) / group


def build_manifest_rows(
    config: dict[str, Any],
    f2d_rows: Sequence[dict[str, str]],
    f0_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    """Build exactly 20 F3b manifest rows from F2d/F0 metadata."""
    f2d_by_key = {row_key(row): row for row in f2d_rows}
    f0_by_key = {row_key(row): row for row in f0_rows}
    manifest: list[dict[str, str]] = []
    for key in expected_keys(config):
        if key not in f2d_by_key:
            raise ValueError(f"Missing F2d readiness row for key: {key}")
        if key not in f0_by_key:
            raise ValueError(f"Missing F0 run-matrix row for key: {key}")
        cell_id, forcing_day, hour, scenario = key
        f2d = f2d_by_key[key]
        f0 = f0_by_key[key]
        group = expected_output_group(config, key)
        out_dir = expected_output_dir(config, group)
        tmrt_path = out_dir / "Tmrt_average.tif"
        manifest.append(
            {
                "run_id": f"b85_f3b_{forcing_day}_{cell_id}_{scenario}_h{hour:02d}",
                "cell_id": cell_id,
                "forcing_day_id": forcing_day,
                "date": clean(f2d.get("date") or f0.get("date")),
                "hour_sgt": str(hour),
                "scenario": scenario,
                "expected_output_group": group,
                "expected_output_dir": out_dir.as_posix(),
                "expected_tmrt_path": tmrt_path.as_posix(),
                "expected_output_paths": tmrt_path.as_posix(),
                "source_f2d_run_id": clean(f2d.get("run_id")),
                "source_f0_run_id": clean(f0.get("run_id")),
                "source_f0_status": clean(f0.get("status")),
                "source_f0_solweig_execute_now": clean(f0.get("solweig_execute_now")),
                "qgis_solweig_executed": NO,
            }
        )
    if len(manifest) != int(onecell(config)["expected_run_count"]):
        raise ValueError(f"Manifest row count is {len(manifest)}, expected 20.")
    return manifest


def path_outside_git_and_under_local(config: dict[str, Any], path: Path) -> bool:
    """Return whether expected output path is local-only and outside Git."""
    local_root = Path(str(onecell(config)["local_solweig_output_root"]))
    return is_relative_to(path, local_root) and not is_relative_to(path, git_root())


def build_precheck_rows(
    config: dict[str, Any],
    manifest_rows: Sequence[dict[str, str]],
    f2d_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    """Build per-run pre-execution asset checks from F2d readiness metadata."""
    f2d_by_key = {row_key(row): row for row in f2d_rows}
    rows: list[dict[str, str]] = []
    for manifest in manifest_rows:
        key = row_key(manifest)
        f2d = f2d_by_key[key]
        output_path = Path(manifest["expected_tmrt_path"])
        outside_git = path_outside_git_and_under_local(config, output_path)
        f2d_ready = f2d_row_ready(f2d)
        run_ready = f2d_ready and outside_git
        blockers: list[str] = []
        if not normalize_yes(f2d.get("cell_geometry_ready")):
            blockers.append("cell_geometry_not_ready")
        if not normalize_yes(f2d.get("raster_tiles_ready")):
            blockers.append("raster_tiles_not_ready")
        if not normalize_yes(f2d.get("svf_ready")):
            blockers.append("svf_not_ready")
        if not normalize_yes(f2d.get("met_forcing_ready")):
            blockers.append("met_forcing_not_ready")
        if not normalize_yes(f2d.get("output_root_ready")):
            blockers.append("output_root_not_ready")
        if not normalize_pass(f2d.get("qgis_manual_check_status")):
            blockers.append("qgis_manual_check_not_pass")
        if not outside_git:
            blockers.append("expected_output_path_not_local_only")
        rows.append(
            {
                "run_id": manifest["run_id"],
                "cell_id": manifest["cell_id"],
                "forcing_day_id": manifest["forcing_day_id"],
                "date": manifest["date"],
                "hour_sgt": manifest["hour_sgt"],
                "scenario": manifest["scenario"],
                "cell_geometry_ready": clean(f2d.get("cell_geometry_ready")),
                "raster_tiles_ready": clean(f2d.get("raster_tiles_ready")),
                "svf_ready": clean(f2d.get("svf_ready")),
                "met_forcing_ready": clean(f2d.get("met_forcing_ready")),
                "output_root_ready": clean(f2d.get("output_root_ready")),
                "qgis_manual_check_status": clean(f2d.get("qgis_manual_check_status")),
                "expected_output_path_outside_git": YES if outside_git else NO,
                "run_ready": YES if run_ready else NO,
                "pre_execution_status": PASS if run_ready else BLOCKED_PRECHECK,
                "blockers": "none" if not blockers else "; ".join(blockers),
                "notes": "Derived from F2d/F0 metadata; no raster or svfs.zip content opened.",
            }
        )
    return rows


def expected_run_log_schema_rows() -> list[dict[str, str]]:
    """Return the expected local QGIS runner run-log schema."""
    rows = [
        ("run_id", "string", YES, "unique 20-row F3b manifest run_id", "Primary one-cell full-slice run key."),
        ("cell_id", "string", YES, "TP_0037", "Focus cell identifier."),
        ("forcing_day_id", "string", YES, "FD01_high_shortwave_hot_20260507|FD02_humid_hot_cloudy_or_diffuse_20260508", "Forcing day key."),
        ("date", "date", YES, "YYYY-MM-DD", "Forcing day date in Singapore local time."),
        ("hour_sgt", "integer", YES, "10|12|13|15|16", "Execution hour in Singapore Standard Time."),
        ("scenario", "string", YES, "base|overhead_as_canopy", "SOLWEIG scenario."),
        ("started_at", "datetime", YES, "ISO-8601 local timestamp", "Manual QGIS attempt start time."),
        ("completed_at", "datetime", YES, "ISO-8601 local timestamp", "Manual QGIS attempt completion time."),
        ("status", "string", YES, "dry_run|success|failed|skipped|blocked", "Manual execution status."),
        ("error_message", "string", NO, "free text", "Error details when status is failed or blocked."),
        ("qgis_algorithm_id", "string", YES, "QGIS processing algorithm id", "QGIS/SOLWEIG algorithm used by the local-only runner."),
        ("expected_output_dir", "string", YES, "C:/OpenHeat-local/solweig/b85_f1_tiles/...", "Local-only SOLWEIG output directory."),
        ("expected_tmrt_path", "string", YES, ".../Tmrt_average.tif", "Expected Tmrt raster path for existence/size validation."),
        ("expected_output_paths", "string", YES, "semicolon-separated local-only paths", "Expected output paths recorded by the runner."),
        ("notes", "string", NO, "free text", "Manual-review comments."),
    ]
    return [
        {
            "column_name": column,
            "dtype": dtype,
            "required": required,
            "allowed_values_or_format": allowed,
            "description": description,
        }
        for column, dtype, required, allowed, description in rows
    ]


def postrun_placeholder_rows(manifest_rows: Sequence[dict[str, str]], log_path: Path) -> list[dict[str, str]]:
    """Build NOT_RUN_YET rows before manual execution."""
    run_log_exists = YES if log_path.exists() else NO
    status = "RUN_LOG_PRESENT_VALIDATE_NEXT" if log_path.exists() else NOT_RUN_YET
    phase = "EXECUTED_PENDING_VALIDATION" if log_path.exists() else "PREPARED"
    return [
        {
            "run_id": row["run_id"],
            "phase": phase,
            "postrun_status": status,
            "run_log_exists": run_log_exists,
            "run_log_status": "",
            "expected_tmrt_path": row["expected_tmrt_path"],
            "file_exists": "",
            "file_size_bytes": "",
            "validation_status": status,
            "notes": "Preparation placeholder; validator does not open raster content.",
        }
        for row in manifest_rows
    ]


def manifest_fieldnames() -> list[str]:
    """Return F3b manifest fieldnames."""
    return [
        "run_id",
        "cell_id",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "expected_output_group",
        "expected_output_dir",
        "expected_tmrt_path",
        "expected_output_paths",
        "source_f2d_run_id",
        "source_f0_run_id",
        "source_f0_status",
        "source_f0_solweig_execute_now",
        "qgis_solweig_executed",
    ]


def precheck_fieldnames() -> list[str]:
    """Return pre-execution asset check fieldnames."""
    return [
        "run_id",
        "cell_id",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "cell_geometry_ready",
        "raster_tiles_ready",
        "svf_ready",
        "met_forcing_ready",
        "output_root_ready",
        "qgis_manual_check_status",
        "expected_output_path_outside_git",
        "run_ready",
        "pre_execution_status",
        "blockers",
        "notes",
    ]


def postrun_fieldnames() -> list[str]:
    """Return postrun validation fieldnames."""
    return [
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
    ]


def all_lane_paths(config: dict[str, Any]) -> list[Path]:
    """Return compact F3b artifacts owned by this lane."""
    outputs = config["outputs"]
    paths = [
        DEFAULT_CONFIG,
        ROOT / "scripts/v12_b85_f3b_prepare_onecell_fullslice.py",
        ROOT / "scripts/v12_b85_f3b_validate_onecell_fullslice.py",
        ROOT / "scripts/v12_b85_f3b_raster_qa.py",
        repo_path(config["qgis_execution"]["runner_script"]),
        repo_path(outputs["canonical_note_cn"]),
        repo_path(outputs["manifest"]),
        repo_path(outputs["pre_execution_asset_check"]),
        repo_path(outputs["expected_run_log_schema"]),
        repo_path(outputs["manual_qgis_run_instructions"]),
        repo_path(outputs["postrun_validation"]),
        repo_path(outputs["raster_inventory"]),
        repo_path(outputs["raster_stats"]),
        repo_path(outputs["hourly_profile"]),
        repo_path(outputs["pairwise_delta_by_hour"]),
        repo_path(outputs["forcing_day_contrast_by_hour"]),
        repo_path(outputs["alignment_qa"]),
        repo_path(outputs["sanity_checks"]),
        repo_path(outputs["onecell_report"]),
        repo_path(outputs["status"]),
    ]
    return paths


def write_manual_instructions(
    path: Path,
    config: dict[str, Any],
    decision_status: str,
    ready_count: int,
) -> None:
    """Write the human-only QGIS one-cell full-slice run instructions."""
    section = onecell(config)
    outputs = config["outputs"]
    runner = repo_path(config["qgis_execution"]["runner_script"])
    manifest = repo_path(outputs["manifest"])
    local_copy_root = Path(str(section["local_runner_copy_root"]))
    local_log = Path(str(section["local_run_log_path"]))
    local_output_root = Path(str(section["local_solweig_output_root"]))
    text = f"""# B8.5-F3b Manual QGIS One-Cell Full-Slice Instructions

Generated: {now_stamp()}

## Decision

`{decision_status}`

## Authorized Slice

- Cell: `{section['cell_id']}`
- Forcing days: `{', '.join(section['forcing_days'])}`
- Hours SGT: `{', '.join(str(h) for h in section['hours_sgt'])}`
- Scenarios: `{', '.join(section['scenarios'])}`
- Expected run count: `{section['expected_run_count']}`
- Pre-execution ready count: `{ready_count}/{section['expected_run_count']}`

## Human Gate

Codex/Python did not run QGIS or SOLWEIG. This package authorizes only a 20-run one-cell human-controlled slice. It is not B9, not local WBGT, not risk, not System A/B coupling, and not permission for the full 480.

## Required Manual Steps

1. Review the manifest: `{rel(manifest)}`.
2. Review the repo-tracked runner without changing it: `{rel(runner)}`.
3. Copy the runner to a local-only path under `{local_copy_root.as_posix()}`.
4. In the local-only copy only, manually change `DRY_RUN = False`.
5. Run exactly the 20 manifest rows. DO NOT RUN FULL 480.
6. Keep the run log at `{local_log.as_posix()}`.
7. Keep SOLWEIG outputs under `{local_output_root.as_posix()}` only.
8. Do not commit rasters, `.tif`, `.tiff`, `svfs.zip`, local met forcing files, or local-only outputs.

## After Manual Execution

Run:

```powershell
python scripts/v12_b85_f3b_validate_onecell_fullslice.py --config configs/v12/systemb_b85_f3b_onecell_fullslice.yaml
python scripts/v12_b85_f3b_raster_qa.py --config configs/v12/systemb_b85_f3b_onecell_fullslice.yaml
```

Full 480 remains blocked until this one-cell full slice passes postrun validation and raster-content QA.
"""
    write_text(path, text)


def write_cn_doc(
    path: Path,
    config: dict[str, Any],
    decision_status: str,
    ready_count: int,
    postrun_status: str,
    raster_qa_status: str,
) -> None:
    """Write the UTF-8 Chinese control note for F3b."""
    section = onecell(config)
    text = f"""# OpenHeat System B B8.5-F3b 单网格完整切片执行包中文说明

生成时间：{now_stamp()}

## 结论

- 决策状态：`{decision_status}`
- cell_id：`{section['cell_id']}`
- manifest run count：`{section['expected_run_count']}`
- 预执行 ready 数量：`{ready_count}/{section['expected_run_count']}`
- postrun 状态：`{postrun_status}`
- raster QA 状态：`{raster_qa_status}`
- 预期本地 run log：`{section['local_run_log_path']}`

## 本轮授权范围

本轮只准备 TP_0037 的 one-cell full slice，组合为 2 个 forcing days、5 个 SGT 小时、2 个 scenarios，共 20 次人工控制的 QGIS/SOLWEIG 运行。

- forcing days：`FD01_high_shortwave_hot_20260507` 与 `FD02_humid_hot_cloudy_or_diffuse_20260508`
- hours_sgt：`10, 12, 13, 15, 16`
- scenarios：`base` 与 `overhead_as_canopy`
- 输出 group 前缀：`{section['expected_output_group_prefix']}`

## 边界声明

- Codex/Python 没有运行 QGIS/SOLWEIG。
- preparation lane 没有创建、复制、移动或打开任何 raster。
- preparation lane 没有复制或打开 `svfs.zip`。
- Raster QA 只会在人工执行完成且 postrun validation 通过后读取本地 `Tmrt_average.tif` 内容。
- 不会写出或提交任何 raster、image、GeoTIFF、PNG 或大型数组。
- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 full 480。
- 没有进行 Tmrt-to-WBGT conversion。
- 没有创建 AOI-wide prediction、hazard_score、risk_score 或 System A/B coupling 输出。
- 本说明只授权 20-run one-cell human-controlled slice。
- Full 480 在 one-cell full slice 通过前仍然 blocked。

## 人工执行方式

仓库中的 QGIS runner 必须保持 `DRY_RUN=True`。如果人工审查后要真正执行，必须把 runner 复制到 `C:/OpenHeat-local/solweig/b85_f3b_onecell` 下的本地非 Git 路径，并且只在本地副本中手动改为 `DRY_RUN=False`。真实 SOLWEIG 输出只能写入 `C:/OpenHeat-local/solweig/b85_f1_tiles/...`，run log 只能写入 `C:/OpenHeat-local/solweig/b85_f3b_onecell/run_logs/b85_f3b_onecell_qgis_run_log.csv`。

## 验证方式

pre-execution asset check 使用 F2d/F0 readiness 元数据生成，不打开 raster 内容。postrun validator 不读取 raster 内容；它只检查本地 run log 是否存在、20 个 run 是否为 success、预期 `Tmrt_average.tif` 是否存在且文件大小大于 0。若人工尚未执行，validator 和 raster QA 会输出 `NOT_RUN_YET`，不会把“未执行”误报为失败。
"""
    write_text(path, text)


def write_status_report(
    path: Path,
    config: dict[str, Any],
    decision_status: str,
    manifest_count: int,
    ready_count: int,
    postrun_status: str,
    raster_qa_status: str,
    notes: str,
) -> None:
    """Write the F3b lane status Markdown."""
    section = onecell(config)
    files_block = "\n".join(f"- `{rel(item)}`" for item in all_lane_paths(config))
    text = f"""# B8.5-F3b Status

Generated: {now_stamp()}

## Status

`{decision_status}`

## Branch

`{config['branch']}`

## Scope

One-cell full-slice execution package, postrun validator, and raster-content QA aggregation for TP_0037 only. Codex/Python did not run QGIS/SOLWEIG. Preparation did not create, copy, move, or open rasters, and did not copy/open `svfs.zip`. Raster QA reads local raster contents only after human execution and postrun validation. This is not B9, not local WBGT, not risk, not full 480, and not Tmrt-to-WBGT conversion.

## Key Results

- Cell_id: `{section['cell_id']}`
- Manifest run count: `{manifest_count}`
- Pre-execution ready count: `{ready_count}/{section['expected_run_count']}`
- Postrun status: `{postrun_status}`
- Raster QA status: `{raster_qa_status}`
- Local run log path expected: `{section['local_run_log_path']}`
- QGIS/SOLWEIG executed by Codex: `no`
- Full 480 status: `blocked_until_onecell_full_slice_passes`
- Notes: {notes}

## Files Created / Modified

{files_block}

## Commands To Verify

- `python -m compileall scripts/v12_b85_f3b_prepare_onecell_fullslice.py scripts/v12_b85_f3b_validate_onecell_fullslice.py scripts/v12_b85_f3b_raster_qa.py scripts/qgis/v12_b85_f3b_onecell_qgis_runner.py`
- `python scripts/v12_b85_f3b_prepare_onecell_fullslice.py --config configs/v12/systemb_b85_f3b_onecell_fullslice.yaml`
- `python scripts/v12_b85_f3b_validate_onecell_fullslice.py --config configs/v12/systemb_b85_f3b_onecell_fullslice.yaml`
- `python scripts/v12_b85_f3b_raster_qa.py --config configs/v12/systemb_b85_f3b_onecell_fullslice.yaml`
- Python mojibake check on `docs/v12/OpenHeat_SystemB_B8_5_F3b_onecell_fullslice_CN.md`
- `git status --short -- .`
- forbidden-file check

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown control artifacts listed above after review.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and large forecast CSV files.
"""
    write_text(path, text)


def prepare(config_path: Path) -> PrepareResult:
    """Load config and write the F3b one-cell full-slice package."""
    config = read_config(repo_path(config_path))
    ensure_scope_is_preparation_only(config)
    outputs = config["outputs"]
    repo_path(outputs["out_dir"]).mkdir(parents=True, exist_ok=True)

    f2d_rows = read_csv_rows(repo_path(config["inputs"]["f2d_run_readiness"]))
    f0_rows = read_csv_rows(repo_path(config["inputs"]["f0_run_matrix"]))
    manifest_rows = build_manifest_rows(config, f2d_rows, f0_rows)
    precheck_rows = build_precheck_rows(config, manifest_rows, f2d_rows)
    ready_count = sum(1 for row in precheck_rows if row["run_ready"] == YES)
    local_log = Path(str(onecell(config)["local_run_log_path"]))
    postrun_status = NOT_RUN_YET if not local_log.exists() else "RUN_LOG_PRESENT_VALIDATE_NEXT"
    decision = READY_FOR_HUMAN_ONECELL_SLICE if ready_count == int(onecell(config)["expected_run_count"]) else BLOCKED_PRECHECK
    raster_qa_status = NOT_RUN_YET
    notes = "Prepared only; no QGIS/SOLWEIG execution by Codex/Python."

    write_csv_rows(repo_path(outputs["manifest"]), manifest_rows, manifest_fieldnames())
    write_csv_rows(repo_path(outputs["pre_execution_asset_check"]), precheck_rows, precheck_fieldnames())
    write_csv_rows(
        repo_path(outputs["expected_run_log_schema"]),
        expected_run_log_schema_rows(),
        ["column_name", "dtype", "required", "allowed_values_or_format", "description"],
    )
    write_csv_rows(repo_path(outputs["postrun_validation"]), postrun_placeholder_rows(manifest_rows, local_log), postrun_fieldnames())
    write_manual_instructions(repo_path(outputs["manual_qgis_run_instructions"]), config, decision, ready_count)
    write_cn_doc(repo_path(outputs["canonical_note_cn"]), config, decision, ready_count, postrun_status, raster_qa_status)
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

    return PrepareResult(
        decision_status=decision,
        manifest_run_count=len(manifest_rows),
        pre_execution_ready_count=ready_count,
        postrun_status=postrun_status,
        raster_qa_status=raster_qa_status,
        local_run_log_path=local_log,
        files_created=all_lane_paths(config),
    )


def main() -> int:
    """Parse CLI arguments and prepare the F3b one-cell full slice."""
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the B8.5-F3b 20-run one-cell full-slice QGIS/SOLWEIG "
            "execution package. Does not run QGIS/SOLWEIG or open raster/SVF contents."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F3b YAML config path.")
    args = parser.parse_args()
    try:
        result = prepare(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print(f"Status: {result.decision_status}")
    print(f"Manifest run count: {result.manifest_run_count}")
    print(f"Pre-execution ready count: {result.pre_execution_ready_count}")
    print(f"Postrun status: {result.postrun_status}")
    print(f"Raster QA status: {result.raster_qa_status}")
    print(f"Local run log path expected: {result.local_run_log_path.as_posix()}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status == READY_FOR_HUMAN_ONECELL_SLICE else 2


if __name__ == "__main__":
    raise SystemExit(main())
