"""Assess B8.5-F2a local asset readiness and simulate a dry-run gate.

Inputs:
    configs/v12/systemb_b85_f2_asset_readiness.yaml
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_required_asset_inventory.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_qgis_parameter_contract.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_expected_run_log_schema.csv
    scripts/qgis/v12_b85_qgis_solweig_execution_SKELETON.py
    configs/v12/systemb_b85_f1_execution_package.yaml

Outputs:
    docs/v12/OpenHeat_SystemB_B8_5_F2_asset_readiness_CN.md
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_asset_readiness_summary.csv
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_asset_readiness_by_asset.csv
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_asset_readiness_by_run.csv
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_missing_assets.csv
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_local_output_root_check.csv
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_dry_run_simulation_log.csv
    outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_manual_execution_checklist.md
    outputs/v12_surrogate/b8_5_f2_asset_readiness/B8_5_F2A_STATUS.md

Saved metrics:
    Manifest row/cell/day/hour/scenario/solweig_execute_now checks, classified
    F1 asset inventory readiness, missing asset classes, one per-run readiness
    row, one dry-run simulation-log row per run_id, and local output root status.

This script does not run QGIS, run SOLWEIG, create rasters, copy rasters,
create AOI-wide predictions, create local WBGT, create hazard_score/risk_score,
create System A/B coupling outputs, stage files, or commit files. Raster and
SVF paths are checked only with pathlib existence checks.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f2_asset_readiness.yaml"

YES = "yes"
NO = "no"
PASS = "PASS"
FAIL = "FAIL"
NEEDS_CREATE = "NEEDS_CREATE"
READY_FOR_MANUAL_QGIS = "READY_FOR_MANUAL_QGIS"
PARTIAL_ASSETS_MISSING = "PARTIAL_ASSETS_MISSING"
BLOCKED = "BLOCKED"
FAILED = "FAILED"

READINESS_PRESENT = "present"
READINESS_MISSING = "missing_but_expected_local"
READINESS_MANUAL = "manual_check_required"
READINESS_NOT_REQUIRED = "not_required_for_this_gate"

RUN_READY = "ready_for_manual_qgis"
RUN_MISSING_CELL = "blocked_missing_cell_asset"
RUN_MISSING_MET = "blocked_missing_met_forcing"
RUN_MISSING_SVF = "blocked_missing_svf"
RUN_MANUAL = "blocked_manual_check_required"


@dataclass(frozen=True)
class AssetReadinessResult:
    """Return object for the F2a gate."""

    decision_status: str
    ready_run_count: int
    total_run_count: int
    local_output_root_status: str
    missing_asset_summary: str
    next_recommended_action: str
    files_created: list[Path]


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by OpenHeat configs."""
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
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
    """Read the simple nested YAML shape used by this repository."""
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
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = []
        for future in lines[idx + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Load YAML config, preferring PyYAML with a no-dependency fallback."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Config did not parse to a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def repo_path(value: str | Path) -> Path:
    """Resolve a path relative to the OpenHeat project subdirectory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def git_root() -> Path:
    """Return the Git root for the current OpenHeat worktree."""
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return ROOT.resolve()


def git_output(args: list[str]) -> str:
    """Return stdout for a lightweight Git command."""
    completed = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def rel(path: Path) -> str:
    """Return a project-relative path where possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV into dictionaries with string values."""
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


def sorted_unique(values: Iterable[Any]) -> list[str]:
    """Return sorted unique non-empty strings."""
    return sorted({clean(value) for value in values if clean(value)})


def normalize_yes_no(value: Any) -> str:
    """Normalize no/yes flags from YAML and CSV."""
    if isinstance(value, bool):
        return YES if value else NO
    lowered = clean(value).lower()
    if lowered in {"true", "1", "y"}:
        return YES
    if lowered in {"false", "0", "n"}:
        return NO
    return lowered


def is_path_like(value: str) -> bool:
    """Return whether an inventory value looks like a repository/local path."""
    if not value:
        return False
    candidate = value.replace("\\", "/")
    if "/" in candidate:
        return True
    path = Path(value)
    return path.is_absolute()


def inventory_path(value: str) -> Path:
    """Resolve a F1 inventory path without opening asset contents."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def path_exists_for_inventory(value: str) -> str:
    """Check existence for path-like F1 inventory entries."""
    if not is_path_like(value):
        return NO
    return YES if inventory_path(value).exists() else NO


def classify_asset_type(source_type: str) -> str:
    """Map F1 inventory classes to the F2a readiness taxonomy."""
    mapping = {
        "control_file": "control_file",
        "reference_script_or_manifest": "reference_script_or_manifest",
        "raster_tile": "raster_tile",
        "global_raster_reference": "raster_tile",
        "svf_zip": "svf_zip",
        "cell_geometry": "cell_geometry",
        "cell_geometry_or_vector": "cell_geometry",
        "met_forcing_file": "met_forcing_file",
        "local_output_root": "local_output_root",
        "qgis_algorithm_manual_check": "qgis_algorithm_manual_check",
    }
    return mapping.get(source_type, "reference_script_or_manifest")


def readiness_status_for_asset(asset_type: str, required: str, exists: str, path_like: bool) -> str:
    """Classify one asset readiness row."""
    if normalize_yes_no(required) != YES:
        return READINESS_NOT_REQUIRED
    if asset_type == "qgis_algorithm_manual_check":
        return READINESS_MANUAL
    if not path_like:
        return READINESS_MANUAL
    if exists == YES:
        return READINESS_PRESENT
    return READINESS_MISSING


def manual_action_for_asset(row: dict[str, str]) -> str:
    """Return the exact manual check needed for a missing/manual asset."""
    asset_type = row["asset_type"]
    logical_name = row["logical_name"]
    path = row["expected_path"]
    if row["readiness_status"] == READINESS_MANUAL:
        if asset_type == "qgis_algorithm_manual_check":
            return f"Open QGIS/UMEP manually and confirm the algorithm id is available: {path}"
        return f"Confirm the required non-file reference manually: {logical_name}"
    if asset_type == "local_output_root":
        return f"Create or confirm this local-only output root outside Git before manual QGIS execution: {path}"
    if asset_type == "met_forcing_file":
        return f"Create or locate the SOLWEIG met forcing text file, then update the package path if needed: {path}"
    if asset_type == "svf_zip":
        return f"Regenerate or locate the scenario-specific SVF zip locally; do not copy or commit svfs.zip: {path}"
    if asset_type == "raster_tile":
        return f"Regenerate or locate the required raster input locally; do not copy or commit raster files: {path}"
    if asset_type == "cell_geometry":
        return f"Regenerate or locate the focus-cell geometry/vector reference locally: {path}"
    return f"Confirm this required asset exists before manual QGIS execution: {path}"


def build_asset_readiness(config: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Classify the F1 required asset inventory for this F2a gate."""
    inventory_rows = read_csv_rows(repo_path(config["inputs"]["f1_required_asset_inventory"]))
    by_asset: list[dict[str, str]] = []
    for row in inventory_rows:
        source_path = clean(row.get("expected_path", ""))
        asset_type = classify_asset_type(clean(row.get("asset_type", "")))
        path_like = is_path_like(source_path)
        observed_exists = path_exists_for_inventory(source_path) if path_like else NO
        readiness = readiness_status_for_asset(
            asset_type=asset_type,
            required=clean(row.get("required_for_execution", "")),
            exists=observed_exists,
            path_like=path_like,
        )
        resolved_path = ""
        if path_like:
            resolved_path = inventory_path(source_path).resolve().as_posix()
        out = {
            "asset_type": asset_type,
            "source_asset_type": clean(row.get("asset_type", "")),
            "logical_name": clean(row.get("logical_name", "")),
            "expected_path": source_path,
            "resolved_path": resolved_path,
            "required_for_execution": normalize_yes_no(row.get("required_for_execution", "")),
            "commit_safe": normalize_yes_no(row.get("commit_safe", "")),
            "exists": observed_exists,
            "is_path_like": YES if path_like else NO,
            "readiness_status": readiness,
            "notes": clean(row.get("notes", "")),
        }
        by_asset.append(out)
    missing = [
        {**row, "next_manual_check": manual_action_for_asset(row)}
        for row in by_asset
        if row["readiness_status"] in {READINESS_MISSING, READINESS_MANUAL}
        and row["required_for_execution"] == YES
    ]
    return by_asset, missing


def manifest_check_row(
    check_name: str,
    status: str,
    expected: Any,
    observed: Any,
    detail: str = "",
) -> dict[str, str]:
    """Build one manifest check row for summary assembly."""
    return {
        "section": "manifest",
        "check_name": check_name,
        "status": status,
        "expected": clean(expected),
        "observed": clean(observed),
        "detail": clean(detail),
    }


def control_input_check_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    """Validate compact F1/F2 control inputs required by this gate."""
    required_keys = [
        "f1_required_asset_inventory",
        "f1_qgis_parameter_contract",
        "f1_expected_run_log_schema",
        "f1_manifest_validation",
        "f1_execution_package_config",
    ]
    rows: list[dict[str, str]] = []
    for key in required_keys:
        path = repo_path(config["inputs"][key])
        rows.append(
            {
                "section": "control_input",
                "check_name": f"{key}_exists",
                "status": PASS if path.exists() else FAIL,
                "expected": rel(path),
                "observed": "exists" if path.exists() else "missing",
                "detail": "Required compact F1/F2 control artifact; no raster content opened.",
            }
        )
    return rows


def validate_manifest(config: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]], bool]:
    """Validate the F0 run matrix without executing any rows."""
    matrix_path = repo_path(config["inputs"]["f0_run_matrix"])
    expected = config["expected_manifest"]
    rows: list[dict[str, str]] = control_input_check_rows(config)
    if not matrix_path.exists():
        rows.append(manifest_check_row("run_matrix_exists", FAIL, rel(matrix_path), "missing"))
        return [], rows, False

    manifest = read_csv_rows(matrix_path)
    expected_hours = [str(int(hour)) for hour in expected["hours_sgt"]]
    expected_scenarios = sorted(str(scenario) for scenario in expected["scenarios"])
    expected_execute = normalize_yes_no(expected["solweig_execute_now"])
    observed_cells = sorted_unique(row.get("cell_id", "") for row in manifest)
    observed_days = sorted_unique(row.get("forcing_day_id", "") for row in manifest)
    observed_hours = sorted_unique(row.get("hour_sgt", "") for row in manifest)
    observed_scenarios = sorted_unique(row.get("scenario", "") for row in manifest)
    observed_execute = sorted_unique(normalize_yes_no(row.get("solweig_execute_now", "")) for row in manifest)

    rows.extend(
        [
            manifest_check_row("run_matrix_exists", PASS, rel(matrix_path), "exists"),
            manifest_check_row(
                "planned_rows",
                PASS if len(manifest) == int(expected["planned_rows"]) else FAIL,
                expected["planned_rows"],
                len(manifest),
            ),
            manifest_check_row(
                "unique_cells",
                PASS if len(observed_cells) == int(expected["unique_cells"]) else FAIL,
                expected["unique_cells"],
                len(observed_cells),
                ",".join(observed_cells),
            ),
            manifest_check_row(
                "forcing_days",
                PASS if len(observed_days) == int(expected["forcing_days"]) else FAIL,
                expected["forcing_days"],
                len(observed_days),
                ",".join(observed_days),
            ),
            manifest_check_row(
                "hours_sgt",
                PASS if observed_hours == expected_hours else FAIL,
                ",".join(expected_hours),
                ",".join(observed_hours),
            ),
            manifest_check_row(
                "scenarios",
                PASS if observed_scenarios == expected_scenarios else FAIL,
                ",".join(expected_scenarios),
                ",".join(observed_scenarios),
            ),
            manifest_check_row(
                "solweig_execute_now",
                PASS if observed_execute == [expected_execute] else FAIL,
                expected_execute,
                ",".join(observed_execute),
            ),
        ]
    )
    return manifest, rows, all(row["status"] == PASS for row in rows)


def scenario_suffix(scenario: str) -> str:
    """Return the scenario folder suffix used by F1 output groups."""
    if scenario == "base":
        return "base"
    if scenario == "overhead_as_canopy":
        return "overhead"
    return scenario


def expected_forcing_path(config: dict[str, Any], row: dict[str, str]) -> Path:
    """Build an expected met forcing path for one manifest row."""
    date_yyyymmdd = row["date"].replace("-", "_")
    template = str(config["asset_templates"]["met_forcing_path_template"])
    return repo_path(template.format(date_yyyymmdd=date_yyyymmdd, hour_sgt=int(row["hour_sgt"])))


def run_input_paths(config: dict[str, Any], row: dict[str, str]) -> dict[str, Path]:
    """Build expected local input paths for one manifest row."""
    templates = config["asset_templates"]
    cell_root = repo_path(templates["existing_n24_tile_root_reference"]) / row["cell_id"]
    vegetation_name = (
        templates["vegetation_base_name"]
        if row["scenario"] == "base"
        else templates["vegetation_overhead_name"]
    )
    svf_name = templates["svf_base_zip"] if row["scenario"] == "base" else templates["svf_overhead_zip"]
    return {
        "focus_cell": cell_root / str(templates["focus_geojson_name"]),
        "dsm_buildings": cell_root / str(templates["dsm_buildings_name"]),
        "dem": cell_root / str(templates["dem_name"]),
        "wall_height": cell_root / str(templates["wall_height_name"]),
        "wall_aspect": cell_root / str(templates["wall_aspect_name"]),
        "scenario_vegetation": cell_root / str(vegetation_name),
        "scenario_svf": cell_root / str(svf_name),
        "met_forcing": expected_forcing_path(config, row),
    }


def output_tmrt_path(config: dict[str, Any], row: dict[str, str]) -> Path:
    """Build the expected local-only Tmrt output path without creating it."""
    root = Path(str(config["asset_templates"]["manual_local_raw_output_root"]))
    output_group = row.get("expected_output_group") or (
        f"b85_f0/{row['forcing_day_id']}/{row['cell_id']}/{scenario_suffix(row['scenario'])}/h{int(row['hour_sgt']):02d}"
    )
    return root / output_group / "Tmrt_average.tif"


def missing_path_names(paths: dict[str, Path], keys: list[str]) -> list[str]:
    """Return missing path labels and paths for selected input keys."""
    missing: list[str] = []
    for key in keys:
        path = paths[key]
        if not path.exists():
            missing.append(f"{key}: {rel(path)}")
    return missing


def skeleton_manual_status(config: dict[str, Any]) -> tuple[str, str]:
    """Check that the skeleton exists and preserves the dry-run/manual gate."""
    skeleton_path = repo_path(config["inputs"]["qgis_skeleton_script"])
    if not skeleton_path.exists():
        return FAIL, f"Skeleton missing: {rel(skeleton_path)}"
    text = skeleton_path.read_text(encoding="utf-8")
    missing_phrases = [
        phrase
        for phrase in config["qgis_manual_check"]["required_skeleton_phrases"]
        if str(phrase) not in text
    ]
    if missing_phrases:
        return FAIL, f"Skeleton missing required gate phrases: {', '.join(missing_phrases)}"
    return PASS, "Skeleton exists and states DRY_RUN=True / human manual verification."


def build_run_readiness(
    config: dict[str, Any],
    manifest: list[dict[str, str]],
    skeleton_status: str,
) -> list[dict[str, str]]:
    """Build one readiness row per F0 run_id."""
    run_rows: list[dict[str, str]] = []
    for row in manifest:
        paths = run_input_paths(config, row)
        missing_common = missing_path_names(paths, ["focus_cell", "dsm_buildings", "dem", "wall_height", "wall_aspect"])
        missing_scenario = missing_path_names(paths, ["scenario_vegetation"])
        missing_svf = missing_path_names(paths, ["scenario_svf"])
        missing_met = missing_path_names(paths, ["met_forcing"])
        if skeleton_status != PASS:
            run_readiness = RUN_MANUAL
        elif missing_common or missing_scenario:
            run_readiness = RUN_MISSING_CELL
        elif missing_met:
            run_readiness = RUN_MISSING_MET
        elif missing_svf:
            run_readiness = RUN_MISSING_SVF
        else:
            run_readiness = RUN_READY

        tmrt_path = output_tmrt_path(config, row)
        run_rows.append(
            {
                "run_id": row.get("run_id", ""),
                "cell_id": row.get("cell_id", ""),
                "forcing_day_id": row.get("forcing_day_id", ""),
                "date": row.get("date", ""),
                "hour_sgt": row.get("hour_sgt", ""),
                "scenario": row.get("scenario", ""),
                "expected_output_group": row.get("expected_output_group", ""),
                "cell_assets_ready": YES if not missing_common else NO,
                "scenario_inputs_ready": YES if not missing_scenario else NO,
                "svf_ready": YES if not missing_svf else NO,
                "met_forcing_ready": YES if not missing_met else NO,
                "manual_check_status": "manual_qgis_algorithm_check_required_not_blocking"
                if skeleton_status == PASS
                else "manual_check_blocking",
                "run_readiness": run_readiness,
                "missing_cell_assets": "; ".join(missing_common),
                "missing_scenario_inputs": "; ".join(missing_scenario),
                "missing_svf_assets": "; ".join(missing_svf),
                "missing_met_forcing": "; ".join(missing_met),
                "expected_tmrt_path": tmrt_path.as_posix(),
                "qgis_solweig_executed": NO,
            }
        )
    return run_rows


def build_dry_run_log(run_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create one dry-run simulation row per run without executing QGIS."""
    rows: list[dict[str, str]] = []
    for row in run_rows:
        ready = row["run_readiness"] == RUN_READY
        missing_chunks = [
            row.get("missing_cell_assets", ""),
            row.get("missing_scenario_inputs", ""),
            row.get("missing_svf_assets", ""),
            row.get("missing_met_forcing", ""),
        ]
        missing_detail = "; ".join(chunk for chunk in missing_chunks if chunk)
        rows.append(
            {
                "run_id": row["run_id"],
                "cell_id": row["cell_id"],
                "forcing_day_id": row["forcing_day_id"],
                "date": row["date"],
                "hour_sgt": row["hour_sgt"],
                "scenario": row["scenario"],
                "dry_run_status": "dry_run_ready" if ready else "dry_run_blocked",
                "run_readiness": row["run_readiness"],
                "qgis_solweig_executed": NO,
                "output_tmrt_path": row["expected_tmrt_path"],
                "notes": "DRY_RUN simulation only; QGIS/SOLWEIG not called."
                if ready
                else f"DRY_RUN simulation blocked by missing/manual inputs: {missing_detail}",
            }
        )
    return rows


def is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is under parent, with Python-version-safe handling."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def local_output_root_check(config: dict[str, Any]) -> list[dict[str, str]]:
    """Check that the configured local output root is outside the Git worktree."""
    configured = str(config["asset_templates"]["manual_local_raw_output_root"])
    output_root = Path(configured).resolve()
    root = git_root()
    inside_git = is_relative_to(output_root, root)
    exists = output_root.exists()
    parent_exists = output_root.parent.exists()
    if inside_git:
        status = FAIL
        can_create = NO
        notes = "Configured output root is inside the Git worktree; manual execution must not use it."
    elif exists:
        status = PASS
        can_create = YES
        notes = "Configured output root exists outside Git."
    else:
        status = NEEDS_CREATE
        can_create = YES if output_root.anchor and Path(output_root.anchor).exists() else NO
        notes = "Configured output root is outside Git and should be created by a human before manual QGIS execution."
    return [
        {
            "configured_output_root": configured,
            "resolved_output_root": output_root.as_posix(),
            "project_root": ROOT.resolve().as_posix(),
            "git_root": root.as_posix(),
            "exists": YES if exists else NO,
            "parent_exists": YES if parent_exists else NO,
            "inside_git_worktree": YES if inside_git else NO,
            "can_be_created_by_human": can_create,
            "status": status,
            "notes": notes,
        }
    ]


def count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    """Count rows by a categorical key."""
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key, "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def format_counts(counts: dict[str, int]) -> str:
    """Format categorical counts as a short summary string."""
    if not counts:
        return "none"
    return "; ".join(f"{key}={value}" for key, value in counts.items())


def missing_asset_summary(missing_assets: list[dict[str, str]]) -> str:
    """Summarize required missing/manual asset rows by F2 asset class."""
    return format_counts(count_by(missing_assets, "asset_type"))


def decide_status(
    manifest_ok: bool,
    skeleton_status: str,
    local_root_status: str,
    run_rows: list[dict[str, str]],
    missing_assets: list[dict[str, str]],
) -> str:
    """Apply the F2a decision logic."""
    if not manifest_ok or skeleton_status != PASS or local_root_status == FAIL:
        return BLOCKED
    total = len(run_rows)
    ready = sum(1 for row in run_rows if row["run_readiness"] == RUN_READY)
    if total == 480 and ready == total:
        return READY_FOR_MANUAL_QGIS
    if missing_assets or ready < total:
        return PARTIAL_ASSETS_MISSING
    return BLOCKED


def next_action(decision: str, missing_summary: str, local_root_status: str) -> str:
    """Return the next recommended manual action."""
    if decision == READY_FOR_MANUAL_QGIS:
        return "Manual QGIS execution may proceed after human review of the skeleton, algorithm id, and output root."
    if decision == PARTIAL_ASSETS_MISSING:
        return (
            "Resolve missing local assets before manual QGIS execution. "
            f"Missing/manual classes: {missing_summary}. Local output root status: {local_root_status}."
        )
    if decision == BLOCKED:
        return "Resolve blocked manifest, skeleton, or local output-root safety checks before any manual QGIS execution."
    return "Investigate script failure before any further execution."


def output_paths(config: dict[str, Any]) -> list[Path]:
    """Return expected files created or modified by this F2a gate."""
    outputs = config["outputs"]
    return [
        repo_path("configs/v12/systemb_b85_f2_asset_readiness.yaml"),
        repo_path("scripts/v12_b85_f2_asset_readiness.py"),
        repo_path("scripts/v12_b85_run_f2_asset_readiness.py"),
        repo_path(outputs["canonical_note_cn"]),
        repo_path(outputs["summary"]),
        repo_path(outputs["by_asset"]),
        repo_path(outputs["by_run"]),
        repo_path(outputs["missing_assets"]),
        repo_path(outputs["local_output_root_check"]),
        repo_path(outputs["dry_run_simulation_log"]),
        repo_path(outputs["manual_execution_checklist"]),
        repo_path(outputs["status"]),
    ]


def write_summary(
    path: Path,
    decision: str,
    manifest_checks: list[dict[str, str]],
    by_asset: list[dict[str, str]],
    run_rows: list[dict[str, str]],
    missing_assets: list[dict[str, str]],
    local_root_rows: list[dict[str, str]],
    skeleton_status: str,
    skeleton_detail: str,
    action: str,
) -> None:
    """Write the one-row F2a summary CSV."""
    ready_count = sum(1 for row in run_rows if row["run_readiness"] == RUN_READY)
    manifest_status = PASS if all(row["status"] == PASS for row in manifest_checks) else FAIL
    local_root = local_root_rows[0]
    row = {
        "decision_status": decision,
        "manifest_status": manifest_status,
        "manifest_rows": len(run_rows),
        "ready_run_count": ready_count,
        "total_run_count": len(run_rows),
        "run_readiness_counts": format_counts(count_by(run_rows, "run_readiness")),
        "asset_readiness_counts": format_counts(count_by(by_asset, "readiness_status")),
        "missing_asset_count": len(missing_assets),
        "missing_asset_summary": missing_asset_summary(missing_assets),
        "local_output_root_status": local_root["status"],
        "local_output_root_inside_git": local_root["inside_git_worktree"],
        "skeleton_status": skeleton_status,
        "skeleton_detail": skeleton_detail,
        "qgis_solweig_executed": NO,
        "rasters_created_or_copied": NO,
        "is_b9": NO,
        "is_local_wbgt": NO,
        "is_risk": NO,
        "next_recommended_action": action,
    }
    write_csv_rows(path, [row], list(row.keys()))


def markdown_file_list(paths: list[Path]) -> str:
    """Render a Markdown file list."""
    return "\n".join(f"- `{rel(path)}`" for path in paths)


def top_missing_manual_checks(missing_assets: list[dict[str, str]], limit: int = 20) -> str:
    """Render concise manual checks for the most useful missing rows."""
    if not missing_assets:
        return "- None."
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in missing_assets:
        grouped.setdefault(row["asset_type"], []).append(row)
    lines: list[str] = []
    for asset_type, rows in sorted(grouped.items()):
        lines.append(f"- `{asset_type}`: {len(rows)} required rows need manual confirmation.")
        for row in rows[: min(limit, len(rows))]:
            lines.append(f"- `{row['logical_name']}`: {row['next_manual_check']}")
        if len(rows) > limit:
            lines.append(f"- `{asset_type}`: {len(rows) - limit} additional rows are listed in the missing-assets CSV.")
    return "\n".join(lines)


def write_manual_checklist(
    path: Path,
    decision: str,
    missing_assets: list[dict[str, str]],
    local_root_rows: list[dict[str, str]],
    run_rows: list[dict[str, str]],
) -> None:
    """Write the manual execution checklist for a human reviewer."""
    local_root = local_root_rows[0]
    ready_count = sum(1 for row in run_rows if row["run_readiness"] == RUN_READY)
    text = f"""# B8.5-F2a Manual Execution Checklist

Generated: {now_stamp()}

## Gate Status

- Decision: `{decision}`
- Ready runs: `{ready_count}/{len(run_rows)}`
- Local output root status: `{local_root["status"]}`
- QGIS/SOLWEIG executed: `no`
- Rasters created or copied: `no`
- This is not B9, not local WBGT, and not risk.

## Required Before Manual QGIS

- Confirm the QGIS skeleton still has `DRY_RUN = True` until a human reviewer intentionally changes it inside QGIS.
- Confirm the UMEP Processing algorithm id manually inside QGIS.
- Confirm every required N24 focus-cell geometry, DSM/DEM/wall/vegetation raster input, SVF zip, and met forcing text file exists locally.
- Confirm the raw SOLWEIG output root is outside Git before execution.
- Do not commit rasters, `svfs.zip`, raw archive files, large forecast CSVs, or local SOLWEIG outputs.

## Missing Or Manual Checks

{top_missing_manual_checks(missing_assets)}

## Local Output Root

- Configured root: `{local_root["configured_output_root"]}`
- Resolved root: `{local_root["resolved_output_root"]}`
- Inside Git worktree: `{local_root["inside_git_worktree"]}`
- Exists now: `{local_root["exists"]}`
- Human create/check status: `{local_root["status"]}`

## Next Action

Manual QGIS execution can proceed only if the decision is `READY_FOR_MANUAL_QGIS`. If the decision is `PARTIAL_ASSETS_MISSING`, resolve the missing assets listed above and in `b85_f2_missing_assets.csv`, then rerun this readiness gate.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_cn_doc(
    path: Path,
    decision: str,
    ready_count: int,
    total_count: int,
    missing_summary: str,
    local_root_status: str,
    action: str,
) -> None:
    """Write the canonical Chinese F2a asset-readiness note."""
    text = f"""# OpenHeat System B B8.5-F2a 本地资产就绪性说明

生成时间：{now_stamp()}

## 结论

本次门禁状态为 `{decision}`。就绪运行数为 `{ready_count}/{total_count}`。缺失或需要人工确认的资产类别为：`{missing_summary}`。本地原始输出根目录检查状态为 `{local_root_status}`。

## 范围边界

本次工作只是 B8.5-F2a 本地资产就绪性与 dry-run 规划门禁。QGIS 没有运行，SOLWEIG 没有运行，没有创建或复制任何 raster，没有创建 `svfs.zip`，没有创建 AOI-wide prediction，没有创建 local WBGT，没有创建 `hazard_score`、`risk_score`，也没有创建 System A/B coupling 输出。

这不是 B9。它不是本地 WBGT 预测，也不是风险图或风险评分。SOLWEIG 相关路径只用于检查人工执行前的本地资产是否足够，不代表 Tmrt 等于 WBGT，也不代表风险已经建模完成。

## 判读规则

只有当状态为 `READY_FOR_MANUAL_QGIS` 时，下一步才可以进入人工复核后的 QGIS 执行。若状态为 `PARTIAL_ASSETS_MISSING`，必须先补齐或人工确认缺失资产，再重新运行本门禁。若状态为 `BLOCKED`，必须先修复 manifest、skeleton 或本地输出根目录安全问题。

## 当前缺口与人工检查

缺失或需要人工确认的资产类别摘要：`{missing_summary}`。

具体缺失路径和人工检查动作见：

- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_missing_assets.csv`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_manual_execution_checklist.md`

本地输出根目录只允许作为 Git 工作树外的人工 QGIS 输出位置。若检查结果为 `NEEDS_CREATE`，应由人工在本地创建；本脚本不会创建该目录，也不会写入 SOLWEIG raster 输出。

## 下一步建议

{action}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_status(
    path: Path,
    decision: str,
    ready_count: int,
    total_count: int,
    missing_summary: str,
    local_root_status: str,
    action: str,
    files_created: list[Path],
) -> None:
    """Write the B8.5-F2a status Markdown report."""
    branch = git_output(["git", "branch", "--show-current"])
    status_short = git_output(["git", "status", "--short", "--", "."])
    text = f"""# B8.5-F2a Status

Generated: {now_stamp()}

## Status

{decision}

## Branch

`{branch}`

## Scope

Local asset readiness and dry-run planning gate only. QGIS/SOLWEIG was not run. No rasters were created or copied. This is not B9. This is not local WBGT. This is not risk. No AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling output was created.

## Key Results

- Ready runs: `{ready_count}/{total_count}`
- Missing/manual asset classes: `{missing_summary}`
- Local output root status: `{local_root_status}`
- QGIS/SOLWEIG executed: `no`
- Dry-run simulation log created: `yes`

## Next Recommended Action

{action}

Manual QGIS execution can proceed only if readiness is `READY_FOR_MANUAL_QGIS`. If readiness is `PARTIAL_ASSETS_MISSING`, resolve the missing asset classes and exact manual checks listed in `b85_f2_missing_assets.csv` and `b85_f2_manual_execution_checklist.md`, then rerun this gate.

## Files Created / Modified

{markdown_file_list(files_created)}

## Git Status Short

```text
{status_short}
```
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(config_path: Path = DEFAULT_CONFIG) -> AssetReadinessResult:
    """Run the full B8.5-F2a readiness gate and write all compact outputs."""
    config = read_config(config_path)
    outputs = config["outputs"]
    repo_path(outputs["out_dir"]).mkdir(parents=True, exist_ok=True)

    manifest, manifest_checks, manifest_ok = validate_manifest(config)
    by_asset, missing_assets = build_asset_readiness(config)
    skeleton_status, skeleton_detail = skeleton_manual_status(config)
    run_rows = build_run_readiness(config, manifest, skeleton_status)
    dry_run_rows = build_dry_run_log(run_rows)
    local_root_rows = local_output_root_check(config)
    decision = decide_status(
        manifest_ok=manifest_ok,
        skeleton_status=skeleton_status,
        local_root_status=local_root_rows[0]["status"],
        run_rows=run_rows,
        missing_assets=missing_assets,
    )
    missing_summary = missing_asset_summary(missing_assets)
    action = next_action(decision, missing_summary, local_root_rows[0]["status"])
    files_created = output_paths(config)

    write_csv_rows(
        repo_path(outputs["by_asset"]),
        by_asset,
        [
            "asset_type",
            "source_asset_type",
            "logical_name",
            "expected_path",
            "resolved_path",
            "required_for_execution",
            "commit_safe",
            "exists",
            "is_path_like",
            "readiness_status",
            "notes",
        ],
    )
    write_csv_rows(
        repo_path(outputs["missing_assets"]),
        missing_assets,
        [
            "asset_type",
            "source_asset_type",
            "logical_name",
            "expected_path",
            "resolved_path",
            "required_for_execution",
            "commit_safe",
            "exists",
            "is_path_like",
            "readiness_status",
            "notes",
            "next_manual_check",
        ],
    )
    write_csv_rows(
        repo_path(outputs["by_run"]),
        run_rows,
        [
            "run_id",
            "cell_id",
            "forcing_day_id",
            "date",
            "hour_sgt",
            "scenario",
            "expected_output_group",
            "cell_assets_ready",
            "scenario_inputs_ready",
            "svf_ready",
            "met_forcing_ready",
            "manual_check_status",
            "run_readiness",
            "missing_cell_assets",
            "missing_scenario_inputs",
            "missing_svf_assets",
            "missing_met_forcing",
            "expected_tmrt_path",
            "qgis_solweig_executed",
        ],
    )
    write_csv_rows(
        repo_path(outputs["local_output_root_check"]),
        local_root_rows,
        [
            "configured_output_root",
            "resolved_output_root",
            "project_root",
            "git_root",
            "exists",
            "parent_exists",
            "inside_git_worktree",
            "can_be_created_by_human",
            "status",
            "notes",
        ],
    )
    write_csv_rows(
        repo_path(outputs["dry_run_simulation_log"]),
        dry_run_rows,
        [
            "run_id",
            "cell_id",
            "forcing_day_id",
            "date",
            "hour_sgt",
            "scenario",
            "dry_run_status",
            "run_readiness",
            "qgis_solweig_executed",
            "output_tmrt_path",
            "notes",
        ],
    )
    write_summary(
        repo_path(outputs["summary"]),
        decision,
        manifest_checks,
        by_asset,
        run_rows,
        missing_assets,
        local_root_rows,
        skeleton_status,
        skeleton_detail,
        action,
    )
    ready_count = sum(1 for row in run_rows if row["run_readiness"] == RUN_READY)
    write_manual_checklist(
        repo_path(outputs["manual_execution_checklist"]),
        decision,
        missing_assets,
        local_root_rows,
        run_rows,
    )
    write_cn_doc(
        repo_path(outputs["canonical_note_cn"]),
        decision,
        ready_count,
        len(run_rows),
        missing_summary,
        local_root_rows[0]["status"],
        action,
    )
    write_status(
        repo_path(outputs["status"]),
        decision,
        ready_count,
        len(run_rows),
        missing_summary,
        local_root_rows[0]["status"],
        action,
        files_created,
    )

    return AssetReadinessResult(
        decision_status=decision,
        ready_run_count=ready_count,
        total_run_count=len(run_rows),
        local_output_root_status=local_root_rows[0]["status"],
        missing_asset_summary=missing_summary,
        next_recommended_action=action,
        files_created=files_created,
    )


def main() -> int:
    """Parse CLI arguments and run the F2a readiness gate."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F2a local asset readiness and dry-run simulation artifacts. "
            "Does not run QGIS/SOLWEIG, create rasters, copy rasters, or create WBGT/risk outputs."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F2a YAML config path.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(f"Status: {result.decision_status}")
    print(f"Ready runs: {result.ready_run_count}/{result.total_run_count}")
    print(f"Missing asset summary: {result.missing_asset_summary}")
    print(f"Local output root status: {result.local_output_root_status}")
    print("QGIS/SOLWEIG executed: no")
    print(f"Next recommended action: {result.next_recommended_action}")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status in {READY_FOR_MANUAL_QGIS, PARTIAL_ASSETS_MISSING, BLOCKED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
