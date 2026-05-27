"""Prepare the B8.5-F5 N150 / 3000-run multi-forcing package.

Inputs:
    configs/v12/systemb_b85_f5_n150_multiforcing.yaml
    outputs/v12_systemb_n150_sample_design/n150_selected_cells.csv
    outputs/v12_systemb_n150_sample_design/n150_sampling_feature_matrix.csv
    outputs/v12_solweig_n150_execution/n150_base_vs_overhead_delta_merged.csv
    B8.5-F4 anchor/neutral/unstable context CSV files.

Outputs:
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_n150_manifest.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_pre_execution_asset_check.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_expected_run_log_schema.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_manual_qgis_run_instructions.md
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_postrun_validation.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/*.csv placeholder downstream artifacts
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_report.md
    docs/v12/OpenHeat_SystemB_B8_5_F5_N150_multiforcing_CN.md
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/B8_5_F5_STATUS.md

Saved metrics:
    Exact 3000-row manifest, 150-cell count, per-run readiness flags, expected
    local-only Tmrt paths, expected QGIS run-log schema, execution risk
    register, manual execution instructions, and NOT_RUN_YET downstream
    placeholders.

This script does not run QGIS, run SOLWEIG, create/copy/move/open rasters,
copy/open svfs.zip, create local WBGT, create hazard_score/risk_score,
create AOI-wide prediction, create System A/B coupling, perform Tmrt-to-WBGT
conversion, stage, or commit. It prepares a human-controlled N150 / 3000-run
execution package only.
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
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f5_n150_multiforcing.yaml"
_GIT_ROOT_CACHE: Path | None = None

YES = "yes"
NO = "no"
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
FAILED = "FAILED"
PREPARED = "PREPARED"
NOT_RUN_YET = "NOT_RUN_YET"
BLOCKED_PRECHECK = "BLOCKED_PRECHECK"
BLOCKED_POSTRUN = "BLOCKED_POSTRUN"
READY_FOR_HUMAN_N150_MULTIFORCING = "READY_FOR_HUMAN_N150_MULTIFORCING"
N150_MULTIFORCING_EXECUTED_PASS = "N150_MULTIFORCING_EXECUTED_PASS"
N150_MULTIFORCING_EXECUTED_PARTIAL = "N150_MULTIFORCING_EXECUTED_PARTIAL"
N150_MULTIFORCING_STABILITY_REVIEW_READY = "N150_MULTIFORCING_STABILITY_REVIEW_READY"

FORBIDDEN_SCOPE_TRUE_KEYS = {
    "qgis_executed_by_codex",
    "solweig_executed_by_codex",
    "create_rasters",
    "copy_rasters",
    "move_rasters",
    "open_rasters_in_preparation",
    "copy_svf_zip",
    "open_svf_zip",
    "create_aoi_predictions",
    "create_local_wbgt",
    "create_hazard_score",
    "create_risk_score",
    "create_system_ab_coupling",
    "tmrt_to_wbgt_conversion",
    "b9_scope",
    "stage_changes",
    "commit_changes",
}


@dataclass(frozen=True)
class PrepareResult:
    """Compact CLI result for F5 preparation."""

    decision_status: str
    manifest_run_count: int
    unique_cell_count: int
    pre_execution_ready_count: int
    postrun_status: str
    raster_qa_status: str
    label_merge_status: str
    stability_status: str
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


def parse_inline_list(text: str) -> list[Any]:
    """Parse a small YAML inline list."""
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    return [parse_scalar(part.strip()) for part in inner.split(",")]


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by this project config."""
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
    """Write a UTF-8 text artifact without a BOM."""
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
    global _GIT_ROOT_CACHE
    if _GIT_ROOT_CACHE is not None:
        return _GIT_ROOT_CACHE
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    text = completed.stdout.strip()
    _GIT_ROOT_CACHE = Path(text) if text else ROOT
    return _GIT_ROOT_CACHE


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
        "data/raw/buildings_v10/",
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


def ensure_scope_is_preparation_only(config: dict[str, Any]) -> None:
    """Refuse a config that crosses the F5 preparation boundary."""
    scope = config.get("scope", {})
    bad = [key for key in FORBIDDEN_SCOPE_TRUE_KEYS if bool(scope.get(key))]
    if bad:
        raise ValueError(f"Forbidden scope flags must remain false: {', '.join(sorted(bad))}")
    required_false = {
        "execute_qgis_or_solweig": config.get("execute_qgis_or_solweig"),
        "write_raster_outputs_from_python": config.get("write_raster_outputs_from_python"),
    }
    bad_false = [f"{key}={value!r}" for key, value in required_false.items() if value is not False]
    if bad_false:
        raise ValueError("Unsafe F5 config flags: " + "; ".join(bad_false))
    if config.get("repo_runner_dry_run") is not True:
        raise ValueError("repo_runner_dry_run must remain true.")
    if int(config["expected_cell_count"]) != 150:
        raise ValueError("F5 package must contain exactly 150 cells.")
    if int(config["expected_run_count"]) != expected_run_count(config):
        raise ValueError("expected_run_count must equal cells x forcing-days x hours x scenarios.")
    if int(config["expected_run_count"]) != 3000:
        raise ValueError("F5 package must contain exactly 3000 runs.")


def expected_run_count(config: dict[str, Any]) -> int:
    """Return expected cells x forcing-days x hours x scenarios run count."""
    return (
        int(config["expected_cell_count"])
        * len(config["forcing_days"])
        * len(config["hours_sgt"])
        * len(config["scenarios"])
    )


def date_from_forcing_day(forcing_day_id: str) -> str:
    """Return YYYY-MM-DD parsed from the configured forcing day id."""
    raw = forcing_day_id.rsplit("_", 1)[-1]
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    return ""


def boolish(value: Any) -> bool:
    """Return True for project true-like values."""
    return clean(value).lower() in {"true", "yes", "1", "pass"}


def load_selected_cells(config: dict[str, Any]) -> list[dict[str, str]]:
    """Load and validate the canonical 150-cell N150 selection."""
    selected_path = repo_path(config["source_selected_cells_path"])
    selected_rows = read_csv_rows(selected_path)
    selected_rows = sorted(selected_rows, key=lambda row: int(clean(row.get("selection_rank")) or "999999"))
    cells = [clean(row.get("cell_id")) for row in selected_rows if clean(row.get("cell_id"))]
    if len(cells) != int(config["expected_cell_count"]) or len(set(cells)) != int(config["expected_cell_count"]):
        raise ValueError(f"N150 selected cell count is {len(set(cells))}, expected {config['expected_cell_count']}.")

    feature_rows = read_csv_rows(repo_path(config["source_n150_cells_path"]))
    feature_cells = {clean(row.get("cell_id")) for row in feature_rows}
    missing_feature = sorted(set(cells) - feature_cells)
    if missing_feature:
        raise ValueError("Selected N150 cells missing from sampling feature matrix: " + ",".join(missing_feature[:20]))

    legacy_rows = read_csv_rows(repo_path(config["n150_legacy_single_forcing_label_path"]))
    legacy_cells = {clean(row.get("cell_id")) for row in legacy_rows}
    missing_legacy = sorted(set(cells) - legacy_cells)
    if missing_legacy:
        raise ValueError("Selected N150 cells missing from legacy single-forcing label context: " + ",".join(missing_legacy[:20]))
    return selected_rows


def load_anchor_roles(config: dict[str, Any]) -> dict[str, set[str]]:
    """Load F4 robust/neutral/unstable roles for cells included in N150."""
    role_sources = [
        ("robust_priority_anchor", config["n24_f4_anchor_context_path"]),
        ("neutral_boundary", config["n24_f4_neutral_context_path"]),
        ("unstable_review", config["n24_f4_unstable_context_path"]),
    ]
    roles: dict[str, set[str]] = {}
    for role, path_value in role_sources:
        path = repo_path(path_value)
        if not path.exists():
            continue
        for row in read_csv_rows(path):
            cell_id = clean(row.get("cell_id"))
            if cell_id:
                roles.setdefault(cell_id, set()).add(role)
    return roles


def expected_output_group(config: dict[str, Any], forcing_day_id: str, cell_id: str, scenario: str, hour: int) -> str:
    """Return the F5 expected output group for one run."""
    return f"{config['expected_output_group_prefix']}/{forcing_day_id}/{cell_id}/{scenario}/h{hour:02d}"


def expected_output_dir(config: dict[str, Any], group: str) -> Path:
    """Return the expected local-only SOLWEIG output directory."""
    return Path(str(config["local_solweig_output_root"])) / group


def path_outside_git_and_under_local(config: dict[str, Any], path: Path) -> bool:
    """Return whether expected output path is local-only and outside Git."""
    local_root = Path(str(config["local_solweig_output_root"]))
    return is_relative_to(path, local_root) and not is_relative_to(path, git_root())


def met_forcing_path(config: dict[str, Any], forcing_day_id: str, hour: int) -> Path:
    """Return the configured met forcing path for one forcing day/hour."""
    template = str(config["met_forcing_templates"][forcing_day_id])
    return repo_path(template.format(hour=hour))


def scenario_svf_relative(config: dict[str, Any], scenario: str) -> str:
    """Return scenario-specific SVF zip relative path."""
    templates = config["asset_templates"]
    if scenario == "base":
        return str(templates["svf_base_zip"])
    if scenario == "overhead_as_canopy":
        return str(templates["svf_overhead_zip"])
    raise ValueError(f"Unknown scenario: {scenario}")


def scenario_vegetation_name(config: dict[str, Any], scenario: str) -> str:
    """Return scenario-specific vegetation DSM file name."""
    templates = config["asset_templates"]
    if scenario == "base":
        return str(templates["vegetation_base_name"])
    if scenario == "overhead_as_canopy":
        return str(templates["vegetation_overhead_name"])
    raise ValueError(f"Unknown scenario: {scenario}")


def expected_input_paths(config: dict[str, Any], cell_id: str, forcing_day_id: str, hour: int, scenario: str) -> dict[str, Path]:
    """Build expected input paths without opening raster or SVF contents."""
    templates = config["asset_templates"]
    cell_root = Path(str(templates["geometry_raster_svf_root"])) / cell_id
    return expected_input_paths_for_root(config, cell_root.parent.as_posix(), cell_id, forcing_day_id, hour, scenario)


def asset_root_for_selection(config: dict[str, Any], selected_row: dict[str, str]) -> str:
    """Return the input asset root for a selected N150 cell."""
    templates = config["asset_templates"]
    if clean(selected_row.get("selection_status")) == "retained_n24":
        return str(templates.get("retained_n24_geometry_raster_svf_root", templates["geometry_raster_svf_root"]))
    return str(templates["geometry_raster_svf_root"])


def expected_input_paths_for_root(config: dict[str, Any], asset_root: str, cell_id: str, forcing_day_id: str, hour: int, scenario: str) -> dict[str, Path]:
    """Build expected input paths for an explicit asset root without opening contents."""
    templates = config["asset_templates"]
    cell_root = Path(asset_root) / cell_id
    return {
        "focus_cell": cell_root / str(templates["focus_geojson_name"]),
        "input_dsm": cell_root / str(templates["dsm_buildings_name"]),
        "input_dem": cell_root / str(templates["dem_name"]),
        "input_cdsm": cell_root / scenario_vegetation_name(config, scenario),
        "input_height": cell_root / str(templates["wall_height_name"]),
        "input_aspect": cell_root / str(templates["wall_aspect_name"]),
        "input_svf": cell_root / scenario_svf_relative(config, scenario),
        "inputmet": met_forcing_path(config, forcing_day_id, hour),
    }


def path_exists_without_open(path: Path) -> bool:
    """Check path existence without opening file contents."""
    return path.exists()


def build_manifest_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    """Build exactly 3000 F5 manifest rows from the selected N150 cell set."""
    selected_rows = load_selected_cells(config)
    anchor_roles = load_anchor_roles(config)
    legacy_cells = {row["cell_id"] for row in read_csv_rows(repo_path(config["n150_legacy_single_forcing_label_path"]))}
    rows: list[dict[str, str]] = []
    for selected in selected_rows:
        cell_id = clean(selected["cell_id"])
        input_asset_root = asset_root_for_selection(config, selected)
        roles = sorted(anchor_roles.get(cell_id, set()))
        for forcing_day_id in config["forcing_days"]:
            for hour_value in config["hours_sgt"]:
                hour = int(hour_value)
                for scenario in config["scenarios"]:
                    group = expected_output_group(config, forcing_day_id, cell_id, scenario, hour)
                    out_dir = expected_output_dir(config, group)
                    tmrt_path = out_dir / "Tmrt_average.tif"
                    rows.append(
                        {
                            "run_id": f"b85_f5_n150_{forcing_day_id}_{cell_id}_{scenario}_h{hour:02d}",
                            "cell_id": cell_id,
                            "selection_rank": clean(selected.get("selection_rank")),
                            "selection_status": clean(selected.get("selection_status")),
                            "selection_tier": clean(selected.get("selection_tier")),
                            "typology_label": clean(selected.get("typology_label")),
                            "primary_sampling_stratum": clean(selected.get("primary_sampling_stratum")),
                            "n24_f4_context_roles": ";".join(roles),
                            "n150_legacy_single_forcing_label_present": YES if cell_id in legacy_cells else NO,
                            "forcing_day_id": forcing_day_id,
                            "date": date_from_forcing_day(forcing_day_id),
                            "hour_sgt": str(hour),
                            "scenario": scenario,
                            "expected_output_group": group,
                            "expected_output_dir": out_dir.as_posix(),
                            "expected_tmrt_path": tmrt_path.as_posix(),
                            "expected_output_paths": tmrt_path.as_posix(),
                            "input_asset_root": input_asset_root,
                            "source_selected_cells_path": rel(config["source_selected_cells_path"]),
                            "source_sampling_feature_matrix_path": rel(config["source_n150_cells_path"]),
                            "legacy_single_forcing_context_path": rel(config["n150_legacy_single_forcing_label_path"]),
                            "qgis_solweig_executed_by_codex": NO,
                            "claim_boundary": "Tmrt_SOLWEIG_label_only_not_WBGT_not_risk_not_B9",
                        }
                    )
    validate_manifest_shape(config, rows)
    return rows


def validate_manifest_shape(config: dict[str, Any], rows: Sequence[dict[str, str]]) -> None:
    """Refuse any manifest shape other than 150 x 2 x 5 x 2."""
    if len(rows) != int(config["expected_run_count"]):
        raise ValueError(f"Manifest row count is {len(rows)}, expected {config['expected_run_count']}.")
    if len({row["cell_id"] for row in rows}) != int(config["expected_cell_count"]):
        raise ValueError("Manifest unique cell count does not match expected_cell_count.")
    if {row["forcing_day_id"] for row in rows} != set(config["forcing_days"]):
        raise ValueError("Manifest forcing days do not match config.")
    if {int(row["hour_sgt"]) for row in rows} != {int(hour) for hour in config["hours_sgt"]}:
        raise ValueError("Manifest hours do not match config.")
    if {row["scenario"] for row in rows} != set(config["scenarios"]):
        raise ValueError("Manifest scenarios do not match config.")
    if any("b85_f3a" in row["expected_output_group"] or "b85_f3b" in row["expected_output_group"] or "b85_f3c" in row["expected_output_group"] for row in rows):
        raise ValueError("F5 manifest must not use F3a/F3b/F3c output groups.")
    if any("v12_n150_tiles" in row["expected_tmrt_path"] for row in rows):
        raise ValueError("F5 manifest must not use old N150 single-forcing output folders.")


def qgis_manual_check_status(config: dict[str, Any]) -> str:
    """Return PASS when the human QGIS algorithm check marker exists."""
    path = Path(str(config["inputs"]["qgis_manual_check_path"]))
    return PASS if path_exists_without_open(path) else WARN


def build_precheck_rows(config: dict[str, Any], manifest_rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    """Build per-run pre-execution checks without opening raster or SVF contents."""
    qgis_status = qgis_manual_check_status(config)
    output_root = Path(str(config["local_solweig_output_root"]))
    rows: list[dict[str, str]] = []
    for row in manifest_rows:
        hour = int(row["hour_sgt"])
        input_paths = expected_input_paths_for_root(
            config,
            row.get("input_asset_root", str(config["asset_templates"]["geometry_raster_svf_root"])),
            row["cell_id"],
            row["forcing_day_id"],
            hour,
            row["scenario"],
        )
        geometry_ready = path_exists_without_open(input_paths["focus_cell"])
        raster_ready = all(
            path_exists_without_open(input_paths[key])
            for key in ("input_dsm", "input_dem", "input_cdsm", "input_height", "input_aspect")
        )
        svf_ready = path_exists_without_open(input_paths["input_svf"])
        met_ready = path_exists_without_open(input_paths["inputmet"])
        out_path = Path(row["expected_tmrt_path"])
        output_path_ok = path_outside_git_and_under_local(config, out_path)
        output_root_ready = path_exists_without_open(output_root) and output_path_ok
        blockers: list[str] = []
        if not geometry_ready:
            blockers.append("missing_focus_cell_geojson")
        if not raster_ready:
            blockers.append("missing_required_raster_tile_path")
        if not svf_ready:
            blockers.append("missing_svf_zip_path_not_opened")
        if not met_ready:
            blockers.append("missing_met_forcing_file")
        if not output_root_ready:
            blockers.append("local_output_root_missing_or_path_not_local_only")
        if qgis_status != PASS:
            blockers.append("qgis_manual_algorithm_check_missing")
        run_ready = not blockers
        rows.append(
            {
                "run_id": row["run_id"],
                "cell_id": row["cell_id"],
                "forcing_day_id": row["forcing_day_id"],
                "date": row["date"],
                "hour_sgt": row["hour_sgt"],
                "scenario": row["scenario"],
                "cell_geometry_ready": YES if geometry_ready else NO,
                "raster_tiles_ready": YES if raster_ready else NO,
                "svf_ready": YES if svf_ready else NO,
                "met_forcing_ready": YES if met_ready else NO,
                "output_root_ready": YES if output_root_ready else NO,
                "qgis_manual_check_status": qgis_status,
                "expected_output_path_outside_git": YES if output_path_ok else NO,
                "run_ready": YES if run_ready else NO,
                "pre_execution_status": PASS if run_ready else BLOCKED_PRECHECK,
                "blockers": "none" if run_ready else ";".join(blockers),
                "notes": "Path-existence only; no raster contents or svfs.zip contents opened.",
            }
        )
    return rows


def expected_run_log_schema_rows() -> list[dict[str, str]]:
    """Return the expected local QGIS runner run-log schema."""
    rows = [
        ("run_id", "string", YES, "unique 3000-row F5 manifest run_id", "Primary N150 multi-forcing run key."),
        ("cell_id", "string", YES, "TP_####", "N150 cell identifier."),
        ("forcing_day_id", "string", YES, "FD01...|FD02...", "Forcing day key."),
        ("date", "date", YES, "YYYY-MM-DD", "Forcing day date in Singapore local time."),
        ("hour_sgt", "integer", YES, "10|12|13|15|16", "Execution hour in Singapore Standard Time."),
        ("scenario", "string", YES, "base|overhead_as_canopy", "SOLWEIG scenario."),
        ("started_at", "datetime", YES, "ISO-8601 local timestamp", "Manual QGIS attempt start time."),
        ("completed_at", "datetime", YES, "ISO-8601 local timestamp", "Manual QGIS attempt completion time."),
        ("duration_seconds", "float", YES, "perf_counter elapsed seconds", "Wall duration measured by time.perf_counter."),
        ("status", "string", YES, "success|skipped_success_existing_output|failed|blocked|dry_run", "Manual execution or resume status."),
        ("error_message", "string", NO, "free text", "Error details when status is failed or blocked."),
        ("qgis_algorithm_id", "string", YES, "QGIS processing algorithm id", "QGIS/SOLWEIG algorithm used by the local-only runner."),
        ("expected_output_dir", "string", YES, "C:/OpenHeat-local/solweig/b85_f1_tiles/...", "Local-only SOLWEIG output directory."),
        ("expected_tmrt_path", "string", YES, ".../Tmrt_average.tif", "Expected Tmrt raster path for existence/size validation."),
        ("expected_output_paths", "string", YES, "semicolon-separated local-only paths", "Expected output paths recorded by the runner."),
        ("notes", "string", NO, "free text", "Manual-review comments and resume notes."),
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
    phase = "EXECUTED_PENDING_VALIDATION" if log_path.exists() else PREPARED
    return [
        {
            "run_id": row["run_id"],
            "cell_id": row["cell_id"],
            "forcing_day_id": row["forcing_day_id"],
            "hour_sgt": row["hour_sgt"],
            "scenario": row["scenario"],
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
    """Return F5 manifest fieldnames."""
    return [
        "run_id",
        "cell_id",
        "selection_rank",
        "selection_status",
        "selection_tier",
        "typology_label",
        "primary_sampling_stratum",
        "n24_f4_context_roles",
        "n150_legacy_single_forcing_label_present",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "expected_output_group",
        "expected_output_dir",
        "expected_tmrt_path",
        "expected_output_paths",
        "input_asset_root",
        "source_selected_cells_path",
        "source_sampling_feature_matrix_path",
        "legacy_single_forcing_context_path",
        "qgis_solweig_executed_by_codex",
        "claim_boundary",
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
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "scenario",
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


RASTER_INVENTORY_FIELDS = [
    "run_id",
    "cell_id",
    "forcing_day_id",
    "date",
    "hour_sgt",
    "scenario",
    "raster_path",
    "exists",
    "file_size_bytes",
    "crs",
    "width",
    "height",
    "shape",
    "pixel_count",
    "transform",
    "nodata",
    "dtype",
    "band_count",
    "opened_for_qa",
    "copied_or_written",
    "raster_backend",
    "open_error",
]


def raster_stats_fields(thresholds: Sequence[float]) -> list[str]:
    """Return raster stats fieldnames including configured thresholds."""
    fields = [
        "run_id",
        "cell_id",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "raster_path",
        "valid_pixel_count",
        "nodata_pixel_count",
        "nodata_fraction",
        "min_c",
        "p01_c",
        "p05_c",
        "p25_c",
        "mean_c",
        "p50_c",
        "p75_c",
        "p90_c",
        "p95_c",
        "p99_c",
        "max_c",
        "std_c",
    ]
    fields.extend([f"pct_ge_{int(threshold)}" for threshold in thresholds])
    fields.extend(["sanity_status", "sanity_notes"])
    return fields


CELL_HOUR_FIELDS = [
    "cell_id",
    "forcing_day_id",
    "date",
    "hour_sgt",
    "scenario",
    "tmrt_mean_c",
    "tmrt_p50_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "valid_pixel_count",
    "nodata_fraction",
    "sanity_status",
]

PAIRWISE_FIELDS = [
    "cell_id",
    "forcing_day_id",
    "hour_sgt",
    "base_tmrt_p90_c",
    "overhead_tmrt_p90_c",
    "delta_tmrt_mean_c",
    "delta_tmrt_p50_c",
    "delta_tmrt_p90_c",
    "delta_tmrt_p95_c",
    "within_slice_rank",
    "rank_direction",
    "label_source",
    "legacy_single_forcing_comparison_source",
    "notes",
]

CONTRAST_FIELDS = [
    "cell_id",
    "hour_sgt",
    "fd01_forcing_day_id",
    "fd02_forcing_day_id",
    "contrast_direction",
    "delta_tmrt_p90_fd01_c",
    "delta_tmrt_p90_fd02_c",
    "fd02_minus_fd01_delta_tmrt_p90_c",
    "sign_stable",
    "rank_fd01",
    "rank_fd02",
    "rank_drift",
    "notes",
]

CHECK_FIELDS = ["check_name", "status", "value", "details"]

STABILITY_FIELDS = [
    "record_type",
    "cell_id",
    "hour_sgt",
    "metric",
    "value",
    "status",
    "details",
]

LABEL_MERGE_PLAN_FIELDS = [
    "artifact",
    "status",
    "source",
    "output",
    "expected_rows",
    "notes",
]

RISK_REGISTER_FIELDS = ["risk_item", "status", "evidence", "mitigation"]


def placeholder_inventory_rows(manifest_rows: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    """Build raster inventory placeholders without touching local rasters."""
    return [
        {
            "run_id": row["run_id"],
            "cell_id": row["cell_id"],
            "forcing_day_id": row["forcing_day_id"],
            "date": row["date"],
            "hour_sgt": row["hour_sgt"],
            "scenario": row["scenario"],
            "raster_path": row["expected_tmrt_path"],
            "exists": "",
            "file_size_bytes": "",
            "crs": "",
            "width": "",
            "height": "",
            "shape": "",
            "pixel_count": "",
            "transform": "",
            "nodata": "",
            "dtype": "",
            "band_count": "",
            "opened_for_qa": NO,
            "copied_or_written": NO,
            "raster_backend": "",
            "open_error": NOT_RUN_YET,
        }
        for row in manifest_rows
    ]


def placeholder_stats_rows(manifest_rows: Sequence[dict[str, str]], thresholds: Sequence[float]) -> list[dict[str, Any]]:
    """Build raster stats placeholders without touching local rasters."""
    rows: list[dict[str, Any]] = []
    for row in manifest_rows:
        out = {
            "run_id": row["run_id"],
            "cell_id": row["cell_id"],
            "forcing_day_id": row["forcing_day_id"],
            "date": row["date"],
            "hour_sgt": row["hour_sgt"],
            "scenario": row["scenario"],
            "raster_path": row["expected_tmrt_path"],
            "valid_pixel_count": "",
            "nodata_pixel_count": "",
            "nodata_fraction": "",
            "min_c": "",
            "p01_c": "",
            "p05_c": "",
            "p25_c": "",
            "mean_c": "",
            "p50_c": "",
            "p75_c": "",
            "p90_c": "",
            "p95_c": "",
            "p99_c": "",
            "max_c": "",
            "std_c": "",
            "sanity_status": NOT_RUN_YET,
            "sanity_notes": "Raster content QA waits for manual execution and postrun validation.",
        }
        for threshold in thresholds:
            out[f"pct_ge_{int(threshold)}"] = ""
        rows.append(out)
    return rows


def label_merge_plan_rows(config: dict[str, Any], status: str) -> list[dict[str, str]]:
    """Return label merge plan rows."""
    outputs = config["outputs"]
    return [
        {
            "artifact": "cell_hour_summary",
            "status": status,
            "source": rel(outputs["raster_stats"]),
            "output": rel(outputs["cell_hour_summary"]),
            "expected_rows": "3000 after execution",
            "notes": "Scenario-level compact Tmrt summaries; no WBGT conversion.",
        },
        {
            "artifact": "pairwise_delta_by_cell_hour",
            "status": status,
            "source": rel(outputs["raster_stats"]),
            "output": rel(outputs["pairwise_delta_by_cell_hour"]),
            "expected_rows": "1500 after execution",
            "notes": "overhead_as_canopy - base by cell x forcing_day x hour.",
        },
        {
            "artifact": "legacy_single_forcing_context",
            "status": PREPARED,
            "source": rel(config["n150_legacy_single_forcing_label_path"]),
            "output": "metadata only",
            "expected_rows": "0 merged into F5 labels before explicit comparison",
            "notes": "Old N150 single-forcing labels are not mixed into new F5 labels.",
        },
    ]


def execution_risk_register_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    """Return the F5 execution risk register."""
    return [
        {
            "risk_item": "expected_run_count",
            "status": PASS,
            "evidence": "150 cells x 2 forcing days x 5 hours x 2 scenarios = 3000",
            "mitigation": "Runner refuses non-3000 manifests and non-150 cell count.",
        },
        {
            "risk_item": "expected_output_count",
            "status": PASS,
            "evidence": "3000 expected Tmrt_average.tif outputs under C:/OpenHeat-local/solweig/b85_f1_tiles/b85_f5_n150/...",
            "mitigation": "Postrun validator checks local run log and nonzero expected output files without opening raster contents.",
        },
        {
            "risk_item": "local_only_storage_estimate",
            "status": WARN,
            "evidence": "3000 GeoTIFF outputs plus SOLWEIG auxiliaries; rough local-only estimate 0.3-2.0 GB depending compression and auxiliary files.",
            "mitigation": "Do not commit rasters; monitor C:/OpenHeat-local free space before human execution.",
        },
        {
            "risk_item": "resume_and_fail_safe",
            "status": PASS,
            "evidence": f"resume={config['resume']}; fail_safe={config['fail_safe']}",
            "mitigation": "Runner skips successful existing outputs and stops on configured failure limits.",
        },
        {
            "risk_item": "f3b_console_bom_temp_wrapper_issue",
            "status": PASS,
            "evidence": "Manual instructions require utf-8-sig read, explicit __file__, sys.argv=[runner], cwd=runner.parent, and UTF-8 no-BOM local copy.",
            "mitigation": "Preserve F3b/F3c QGIS Console hardening exactly.",
        },
        {
            "risk_item": "h10_caveat_from_f4",
            "status": WARN,
            "evidence": "F4 found h10 weaker; h10 is retained for sensitivity review and not anchor evidence.",
            "mitigation": "Stability summary flags h10 caveat separately.",
        },
        {
            "risk_item": "b86_single_forcing_blocker",
            "status": PASS,
            "evidence": "B8.6 required N150 multi-forcing before promotion/B9.",
            "mitigation": "F5 prepares the N150 multi-forcing execution package only.",
        },
        {
            "risk_item": "claim_boundary",
            "status": PASS,
            "evidence": "not B9 / not risk / not WBGT / no Tmrt-to-WBGT conversion",
            "mitigation": "Docs, runner comments, reports, and statuses repeat these boundaries.",
        },
        {
            "risk_item": "no_raster_in_git",
            "status": PASS,
            "evidence": "Expected outputs are local-only under C:/OpenHeat-local; forbidden-file check covers .tif/.tiff/svfs.zip/data/solweig.",
            "mitigation": "Do not stage or commit rasters.",
        },
    ]


def all_lane_paths(config: dict[str, Any]) -> list[Path]:
    """Return compact F5 artifacts owned by this lane."""
    outputs = config["outputs"]
    return [
        repo_path("configs/v12/systemb_b85_f5_n150_multiforcing.yaml"),
        repo_path("scripts/v12_b85_f5_prepare_n150_multiforcing.py"),
        repo_path("scripts/v12_b85_f5_validate_n150_multiforcing.py"),
        repo_path("scripts/v12_b85_f5_raster_qa.py"),
        repo_path("scripts/v12_b85_f5_label_merge.py"),
        repo_path("scripts/v12_b85_f5_stability_summary.py"),
        repo_path(config["qgis_execution"]["runner_script"]),
        repo_path(outputs["canonical_note_cn"]),
        repo_path(outputs["manifest"]),
        repo_path(outputs["pre_execution_asset_check"]),
        repo_path(outputs["expected_run_log_schema"]),
        repo_path(outputs["manual_qgis_run_instructions"]),
        repo_path(outputs["postrun_validation"]),
        repo_path(outputs["raster_inventory"]),
        repo_path(outputs["raster_stats"]),
        repo_path(outputs["cell_hour_summary"]),
        repo_path(outputs["pairwise_delta_by_cell_hour"]),
        repo_path(outputs["forcing_day_contrast_by_cell_hour"]),
        repo_path(outputs["alignment_qa"]),
        repo_path(outputs["sanity_checks"]),
        repo_path(outputs["label_merge_plan"]),
        repo_path(outputs["stability_summary"]),
        repo_path(outputs["execution_risk_register"]),
        repo_path(outputs["report"]),
        repo_path(outputs["status"]),
    ]


def write_manual_instructions(path: Path, config: dict[str, Any], decision_status: str, ready_count: int) -> None:
    """Write the human-only QGIS N150 run instructions."""
    outputs = config["outputs"]
    runner = repo_path(config["qgis_execution"]["runner_script"])
    manifest = repo_path(outputs["manifest"])
    local_copy_root = Path(str(config["local_runner_copy_root"]))
    local_log = Path(str(config["local_run_log_path"]))
    local_output_root = Path(str(config["local_solweig_output_root"]))
    wrapper = f"""from pathlib import Path
import os
import sys

runner = Path(r"{local_copy_root.as_posix()}/v12_b85_f5_n150_qgis_runner.py")
code = runner.read_text(encoding="utf-8-sig")
globals_dict = {{
    "__name__": "__console__",
    "__file__": str(runner),
}}
sys.argv = [str(runner)]
os.chdir(runner.parent)
exec(compile(code, str(runner), "exec"), globals_dict)
"""
    text = f"""# B8.5-F5 Manual QGIS N150 / 3000-Run Instructions

Generated: {now_stamp()}

## Decision

`{decision_status}`

## Authorized Runset

- Cells: `150`
- Forcing days: `{', '.join(config['forcing_days'])}`
- Hours SGT: `{', '.join(str(h) for h in config['hours_sgt'])}`
- Scenarios: `{', '.join(config['scenarios'])}`
- Expected run count: `{config['expected_run_count']}`
- Pre-execution ready count: `{ready_count}/{config['expected_run_count']}`

## Human Gate

Codex/Python did not run QGIS or SOLWEIG. This package authorizes only the N150 / 3000 human-controlled runset. It is not B9, not local WBGT, not risk, not observed truth, not causal feature importance, and not Tmrt-to-WBGT conversion.

## Required Manual Steps

1. Review the manifest: `{rel(manifest)}`.
2. Review the repo-tracked runner without changing it: `{rel(runner)}`.
3. Copy the runner to a local-only path under `{local_copy_root.as_posix()}`.
4. Keep the repo-tracked runner as `DRY_RUN = True`.
5. In the local-only copy only, manually change `DRY_RUN = False`.
6. Preserve the safety gate; do not remove the Git-worktree refusal checks.
7. Run exactly 3000 manifest rows. DO NOT RUN FULL AOI. N150 / 3000 ONLY.
8. Keep the run log at `{local_log.as_posix()}`.
9. Keep SOLWEIG outputs under `{local_output_root.as_posix()}` only.
10. Do not commit rasters, `.tif`, `.tiff`, `svfs.zip`, local met forcing files, or local-only outputs.

## QGIS Console Robust Wrapper

Use this wrapper in the QGIS Python Console after copying the runner locally and editing only the local copy. It reads the local runner with `encoding="utf-8-sig"`, injects `__file__`, sets `sys.argv = [runner]`, and changes `cwd` to `runner.parent`.

```python
{wrapper}```

## PowerShell Copy Encoding Note

If copying through PowerShell and editing the local runner, write the local copy as UTF-8 without BOM. Do not copy or open `svfs.zip`.

```powershell
$src = "{runner.as_posix()}"
$dst = "{local_copy_root.as_posix()}/v12_b85_f5_n150_qgis_runner.py"
New-Item -ItemType Directory -Force -Path (Split-Path $dst)
$text = Get-Content -Raw -Encoding UTF8 $src
[System.IO.File]::WriteAllText($dst, $text, [System.Text.UTF8Encoding]::new($false))
```

## After Manual Execution

Run, from the repo subdirectory:

```powershell
python scripts/v12_b85_f5_validate_n150_multiforcing.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml
python scripts/v12_b85_f5_raster_qa.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml
python scripts/v12_b85_f5_label_merge.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml
python scripts/v12_b85_f5_stability_summary.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml
```

B9 remains blocked after F5 until a separate promotion review explicitly authorizes it.
"""
    write_text(path, text)


def write_cn_doc(path: Path, config: dict[str, Any], decision_status: str, ready_count: int, postrun_status: str, raster_status: str, label_status: str, stability_status: str) -> None:
    """Write the UTF-8 Chinese control note for F5."""
    text = f"""# OpenHeat System B B8.5-F5 N150 multi-forcing 执行包中文说明

生成时间：{now_stamp()}

## 1. 为什么 F5 跟在 B8.6 后面

B8.5-F4 已通过 N24 decision matrix，并允许在 precheck 后进行 N150 controlled execution。B8.6 找到一个 weak but real 的 N150 single-forcing surrogate baseline，但也明确指出：现有 N150 label 只有 single-forcing，不能支持 promotion 或 B9。因此 F5 的任务是准备 N150 multi-forcing 的 human-execution package，而不是训练 surrogate、不是生成 B9，也不是做 risk。

## 2. Manifest 定义与数量

- cells：150
- forcing days：2
- hours SGT：5（10、12、13、15、16）
- scenarios：2（base、overhead_as_canopy）
- expected run count：3000
- manifest 状态：`{decision_status}`
- pre-execution ready count：`{ready_count}/{config['expected_run_count']}`
- local run log：`{config['local_run_log_path']}`

输出 group 只能使用：

`b85_f5_n150/<forcing_day_id>/<cell_id>/<scenario>/h<hour>`

预期 `Tmrt_average.tif` 只能位于：

`C:/OpenHeat-local/solweig/b85_f1_tiles/<expected_output_group>/Tmrt_average.tif`

## 3. Pre-execution readiness

pre-execution asset check 对每个 run 记录 `cell_geometry_ready`、`raster_tiles_ready`、`svf_ready`、`met_forcing_ready`、`output_root_ready`、`qgis_manual_check_status`、`expected_output_path_outside_git`、`run_ready` 和 `blockers`。本检查只做路径存在性检查，不打开 raster 内容，也不打开 `svfs.zip`。

## 4. Runner safety / resume / fail-safe

仓库中的 runner 必须保持 `DRY_RUN=True`。真实执行只能发生在 `C:/OpenHeat-local/solweig/b85_f5_n150` 下的 local-only copy 中，并且只允许人工在本地副本中把 `DRY_RUN=False`。Runner 会拒绝非 3000-row manifest、非 150-cell manifest、forcing day/hour/scenario 不匹配、从 Git worktree 真实执行、或输出路径不在 `C:/OpenHeat-local/solweig/b85_f1_tiles` 下。Resume 会跳过已有 success run log 且 expected output 存在的 rows，并且 fail-safe 会按配置停止。

## 5. Manual QGIS execution

QGIS Console wrapper 必须读取本地 runner，使用 `encoding="utf-8-sig"`，显式注入 `__file__`，设置 `sys.argv=[runner]`，并把 `cwd` 切换到 `runner.parent`。本地 runner 应写成 UTF-8 without BOM。安全门不能删除。

## 6. Postrun / raster / label / stability scripts

- postrun 状态：`{postrun_status}`
- raster QA 状态：`{raster_status}`
- label merge 状态：`{label_status}`
- stability 状态：`{stability_status}`

人工尚未执行时，这些脚本应输出 `NOT_RUN_YET` 或 `PREPARED`，不能把“尚未执行”误报为失败。postrun validator 不读取 raster 内容；raster QA 只在 postrun 通过后读取 3000 个 local `Tmrt_average.tif`，并且只写 compact CSV。

## 7. F5 可以解锁什么

如果 3000/3000 execution、raster QA、label merge 和 stability summary 都通过，F5 可以为后续 surrogate promotion review 提供 N150 forcing-day stability evidence。它只能支持后续审查，不自动授权 B9。

## 8. F5 不证明什么

- 不证明 local WBGT。
- 不证明 risk。
- 不证明 observed truth。
- 不证明 causal feature importance。
- 不证明 AOI-wide prediction。
- 不证明 B9 readiness。
- 不把 Tmrt 转成 WBGT。

## 9. Claim boundaries

- not B9
- not local WBGT
- not risk
- not observed truth
- not causal feature importance
- no raster committed
- no Tmrt-to-WBGT conversion
- no hazard_score / risk_score / System A-B coupling
"""
    write_text(path, text)


def write_report(path: Path, config: dict[str, Any], decision_status: str, ready_count: int, postrun_status: str, raster_status: str, label_status: str, stability_status: str, risk_rows: Sequence[dict[str, str]]) -> None:
    """Write the F5 Markdown report."""
    text = f"""# B8.5-F5 N150 Multi-Forcing Readiness Report

Generated: {now_stamp()}

## 1. Why F5 Follows B8.6

B8.5-F4 passed the N24 decision matrix and allowed controlled N150 execution after precheck. B8.6 found a weak but real N150 single-forcing surrogate baseline and explicitly required N150 multi-forcing before promotion or B9. F5 therefore prepares the controlled N150 / 3000-run human-execution package.

## 2. Manifest Definition And Count

- Cells: `150`
- Forcing days: `2`
- Hours: `5`
- Scenarios: `2`
- Expected runs: `3000`
- Output group: `b85_f5_n150/<forcing_day_id>/<cell_id>/<scenario>/h<hour>`
- Expected Tmrt path: `C:/OpenHeat-local/solweig/b85_f1_tiles/<expected_output_group>/Tmrt_average.tif`

## 3. Pre-Execution Readiness

- Decision status: `{decision_status}`
- Ready rows: `{ready_count}/{config['expected_run_count']}`
- The asset check records geometry, raster-tile path, SVF path, met forcing path, output root, QGIS manual check, and local-only output-path readiness for every manifest row.
- The check does not open raster contents and does not open `svfs.zip`.

## 4. Runner Safety / Resume / Fail-Safe

The repo QGIS runner remains `DRY_RUN=True`. A human must copy it to `{config['local_runner_copy_root']}`, write the local copy as UTF-8 without BOM, then change only the local copy to `DRY_RUN=False`. The runner refuses manifest mismatches, refuses real execution from the Git worktree, writes outputs only under `{config['local_solweig_output_root']}`, logs every row, flushes after each row, supports resume, and stops on configured failure limits.

## 5. Manual QGIS Execution Instructions

See `{rel(config['outputs']['manual_qgis_run_instructions'])}`. The QGIS Console wrapper reads with `utf-8-sig`, injects `__file__`, sets `sys.argv=[runner]`, and changes `cwd` to `runner.parent`.

## 6. Postrun / Raster / Label / Stability Scripts

- Postrun status: `{postrun_status}`
- Raster QA status: `{raster_status}`
- Label merge status: `{label_status}`
- Stability status: `{stability_status}`

Before human execution these scripts return `NOT_RUN_YET` or `PREPARED` and do not fail. Raster QA reads local raster contents only after postrun validation has confirmed all 3000 outputs.

## 7. What F5 Can Unlock

If execution and QA pass, F5 can unlock a surrogate-promotion review with forcing-day stability evidence for N150. It does not itself authorize B9.

## 8. What F5 Does Not Prove

F5 does not prove local WBGT, risk, observed truth, causal feature importance, AOI-wide prediction, or System A/B coupling.

## 9. Claim Boundaries

- Not B9.
- Not local WBGT.
- Not risk.
- Not observed truth.
- Not causal feature importance.
- No raster committed.
- No Tmrt-to-WBGT conversion.

## Execution Risk Register

{markdown_table(risk_rows, RISK_REGISTER_FIELDS)}
"""
    write_text(path, text)


def write_status(path: Path, config: dict[str, Any], decision_status: str, manifest_count: int, unique_cell_count: int, ready_count: int, postrun_status: str, raster_status: str, label_status: str, stability_status: str, notes: str) -> None:
    """Write the F5 status Markdown."""
    files_block = "\n".join(f"- `{rel(item)}`" for item in all_lane_paths(config))
    text = f"""# B8.5-F5 Status

Generated: {now_stamp()}

## Status

`{decision_status}`

## Branch

`{config['branch']}`

## Scope

N150 / 3000-run multi-forcing readiness and human-execution package only. Codex/Python did not run QGIS/SOLWEIG. This is not B9, not local WBGT, not risk, not observed truth, and not Tmrt-to-WBGT conversion.

## Key Results

- Manifest run count: `{manifest_count}`
- Unique cell count: `{unique_cell_count}`
- Pre-execution ready count: `{ready_count}/{config['expected_run_count']}`
- Postrun status: `{postrun_status}`
- Raster QA status: `{raster_status}`
- Label merge status: `{label_status}`
- Stability status: `{stability_status}`
- Local run log path expected: `{config['local_run_log_path']}`
- QGIS/SOLWEIG executed by Codex: `no`
- B9 status: `blocked`
- Notes: {notes}

## Files Created / Modified

{files_block}

## Commands To Verify

- `python -m compileall scripts/v12_b85_f5_prepare_n150_multiforcing.py scripts/v12_b85_f5_validate_n150_multiforcing.py scripts/v12_b85_f5_raster_qa.py scripts/v12_b85_f5_label_merge.py scripts/v12_b85_f5_stability_summary.py scripts/qgis/v12_b85_f5_n150_qgis_runner.py`
- `python scripts/v12_b85_f5_prepare_n150_multiforcing.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `python scripts/v12_b85_f5_validate_n150_multiforcing.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `python scripts/v12_b85_f5_raster_qa.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `python scripts/v12_b85_f5_label_merge.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- `python scripts/v12_b85_f5_stability_summary.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml`
- Python mojibake check on `docs/v12/OpenHeat_SystemB_B8_5_F5_N150_multiforcing_CN.md`
- `git status --short -- .`
- forbidden-file check

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown control artifacts listed above after review.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and large forecast CSV files.
"""
    write_text(path, text)


def write_initial_downstream_placeholders(config: dict[str, Any], manifest_rows: Sequence[dict[str, str]]) -> None:
    """Write downstream CSV placeholders so scripts are clean before execution."""
    outputs = config["outputs"]
    thresholds = [float(value) for value in config["thresholds_c"]]
    write_csv_rows(repo_path(outputs["raster_inventory"]), placeholder_inventory_rows(manifest_rows), RASTER_INVENTORY_FIELDS)
    write_csv_rows(repo_path(outputs["raster_stats"]), placeholder_stats_rows(manifest_rows, thresholds), raster_stats_fields(thresholds))
    write_csv_rows(repo_path(outputs["cell_hour_summary"]), [], CELL_HOUR_FIELDS)
    write_csv_rows(repo_path(outputs["pairwise_delta_by_cell_hour"]), [], PAIRWISE_FIELDS)
    write_csv_rows(repo_path(outputs["forcing_day_contrast_by_cell_hour"]), [], CONTRAST_FIELDS)
    write_csv_rows(
        repo_path(outputs["alignment_qa"]),
        [{"check_name": "postrun_validation_required_before_raster_content_read", "status": NOT_RUN_YET, "value": "0 rasters opened", "details": "Prepared only; no raster content opened."}],
        CHECK_FIELDS,
    )
    write_csv_rows(
        repo_path(outputs["sanity_checks"]),
        [{"check_name": "no_qgis_or_solweig_execution_by_codex", "status": PASS, "value": NO, "details": "Preparation package only."}],
        CHECK_FIELDS,
    )
    write_csv_rows(repo_path(outputs["label_merge_plan"]), label_merge_plan_rows(config, NOT_RUN_YET), LABEL_MERGE_PLAN_FIELDS)
    write_csv_rows(
        repo_path(outputs["stability_summary"]),
        [{"record_type": NOT_RUN_YET, "cell_id": "", "hour_sgt": "", "metric": NOT_RUN_YET, "value": "", "status": NOT_RUN_YET, "details": "Stability waits for label merge after manual execution."}],
        STABILITY_FIELDS,
    )


def prepare(config_path: Path) -> PrepareResult:
    """Load config and write the F5 N150 multi-forcing package."""
    config = read_config(repo_path(config_path))
    ensure_scope_is_preparation_only(config)
    outputs = config["outputs"]
    repo_path(outputs["out_dir"]).mkdir(parents=True, exist_ok=True)

    manifest_rows = build_manifest_rows(config)
    precheck_rows = build_precheck_rows(config, manifest_rows)
    ready_count = sum(1 for row in precheck_rows if row["run_ready"] == YES)
    unique_cell_count = len({row["cell_id"] for row in manifest_rows})
    local_log = Path(str(config["local_run_log_path"]))
    postrun_status = NOT_RUN_YET if not local_log.exists() else "RUN_LOG_PRESENT_VALIDATE_NEXT"
    decision = READY_FOR_HUMAN_N150_MULTIFORCING if ready_count == int(config["expected_run_count"]) and not local_log.exists() else BLOCKED_PRECHECK
    if local_log.exists() and ready_count == int(config["expected_run_count"]):
        decision = READY_FOR_HUMAN_N150_MULTIFORCING
    raster_status = NOT_RUN_YET
    label_status = NOT_RUN_YET
    stability_status = NOT_RUN_YET
    risk_rows = execution_risk_register_rows(config)

    write_csv_rows(repo_path(outputs["manifest"]), manifest_rows, manifest_fieldnames())
    write_csv_rows(repo_path(outputs["pre_execution_asset_check"]), precheck_rows, precheck_fieldnames())
    write_csv_rows(repo_path(outputs["expected_run_log_schema"]), expected_run_log_schema_rows(), ["column_name", "dtype", "required", "allowed_values_or_format", "description"])
    write_csv_rows(repo_path(outputs["postrun_validation"]), postrun_placeholder_rows(manifest_rows, local_log), postrun_fieldnames())
    write_initial_downstream_placeholders(config, manifest_rows)
    write_csv_rows(repo_path(outputs["execution_risk_register"]), risk_rows, RISK_REGISTER_FIELDS)
    write_manual_instructions(repo_path(outputs["manual_qgis_run_instructions"]), config, decision, ready_count)
    write_cn_doc(repo_path(outputs["canonical_note_cn"]), config, decision, ready_count, postrun_status, raster_status, label_status, stability_status)
    write_report(repo_path(outputs["report"]), config, decision, ready_count, postrun_status, raster_status, label_status, stability_status, risk_rows)
    write_status(
        repo_path(outputs["status"]),
        config,
        decision,
        len(manifest_rows),
        unique_cell_count,
        ready_count,
        postrun_status,
        raster_status,
        label_status,
        stability_status,
        "Prepared only; no QGIS/SOLWEIG execution by Codex/Python.",
    )

    return PrepareResult(
        decision_status=decision,
        manifest_run_count=len(manifest_rows),
        unique_cell_count=unique_cell_count,
        pre_execution_ready_count=ready_count,
        postrun_status=postrun_status,
        raster_qa_status=raster_status,
        label_merge_status=label_status,
        stability_status=stability_status,
        local_run_log_path=local_log,
        files_created=all_lane_paths(config),
    )


def print_result(result: PrepareResult) -> None:
    """Print the compact result block expected by the lane."""
    print(f"Status: {result.decision_status}")
    print(f"Manifest run count: {result.manifest_run_count}")
    print(f"Unique cell count: {result.unique_cell_count}")
    print(f"Pre-execution ready count: {result.pre_execution_ready_count}")
    print(f"Postrun status: {result.postrun_status}")
    print(f"Raster QA status: {result.raster_qa_status}")
    print(f"Label merge status: {result.label_merge_status}")
    print(f"Stability status: {result.stability_status}")
    print(f"Local run log path expected: {result.local_run_log_path.as_posix()}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("B9 status: blocked")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")


def main() -> int:
    """Parse CLI arguments and prepare the F5 N150 multi-forcing package."""
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the B8.5-F5 N150 / 3000-run multi-forcing package. "
            "Does not run QGIS/SOLWEIG or open raster/SVF contents."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F5 YAML config path.")
    args = parser.parse_args()
    try:
        result = prepare(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print_result(result)
    return 0 if result.decision_status == READY_FOR_HUMAN_N150_MULTIFORCING else 2


if __name__ == "__main__":
    raise SystemExit(main())
