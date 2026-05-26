"""Prepare the B8.5-F1 QGIS/SOLWEIG execution package.

Inputs:
    configs/v12/systemb_b85_f1_execution_package.yaml
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/selected_forcing_days.csv
    outputs/v12_surrogate/b8_5_multiforcing_preflight/n24_cell_set_for_multiforcing.csv
    Existing v10/v12 grid, raster-path, QGIS-runner, and SOLWEIG manifest
    references declared in the config.

Outputs:
    docs/v12/OpenHeat_SystemB_B8_5_execution_package_CN.md
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_manifest_validation.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_required_asset_inventory.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_qgis_parameter_contract.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_expected_run_log_schema.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_expected_aggregation_contract.csv
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_execution_readme.md
    outputs/v12_surrogate/b8_5_execution_package/B8_5_F1_STATUS.md

Saved metrics:
    Manifest row/cell/day/hour/scenario counts, run_id and expected_output_group
    uniqueness checks, solweig_execute_now status, required asset inventory,
    QGIS parameter contract, expected run-log schema, expected aggregation
    contract, and package readiness status.

This script prepares execution control artifacts only. It does not run QGIS,
run SOLWEIG, create rasters, copy rasters, create local WBGT, create hazard or
risk scores, create System A/B coupling outputs, stage files, or commit files.
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
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f1_execution_package.yaml"
PASS = "PASS"
PARTIAL = "PARTIAL"
BLOCKED = "BLOCKED"
FAILED = "FAILED"
READY = "READY"
YES = "yes"
NO = "no"


@dataclass(frozen=True)
class PackageResult:
    """Compact result for the execution package preparation run."""

    status: str
    manifest_row_count: int
    asset_readiness_status: str
    qgis_solweig_executed: str
    next_recommended_action: str
    files_created: list[Path]


def repo_path(value: str | Path) -> Path:
    """Resolve a config path relative to the OpenHeat project directory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    """Return a repository-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by this package config."""
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
    """Read the simple nested YAML shape used by this config."""
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
    """Load YAML config, preferring PyYAML but keeping a no-dependency fallback."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Config did not parse to a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV into dictionaries, preserving values as strings."""
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write a compact CSV artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def clean(value: Any) -> str:
    """Return a compact string for report cells."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def report_value(value: Any) -> str:
    """Format report values without leaking local repo absolute paths."""
    if isinstance(value, Path):
        return rel(value)
    return clean(value)


def sorted_unique(values: Iterable[Any]) -> list[str]:
    """Return sorted unique non-empty strings."""
    return sorted({clean(value) for value in values if clean(value) != ""})


def normalize_no_yes(value: Any) -> str:
    """Normalize YAML/CSV no/yes values without boolean surprises."""
    if isinstance(value, bool):
        return YES if value else NO
    return clean(value).lower()


def status_row(check_name: str, status: str, expected: Any, observed: Any, detail: str = "") -> dict[str, str]:
    """Build one manifest-validation row."""
    return {
        "section": "manifest",
        "check_name": check_name,
        "status": status,
        "expected": report_value(expected),
        "observed": report_value(observed),
        "detail": clean(detail),
    }


def validate_manifest(config: dict[str, Any]) -> tuple[list[dict[str, str]], int, bool]:
    """Validate the F0 run matrix contract without executing rows."""
    expected = config["expected_manifest"]
    matrix_path = repo_path(config["inputs"]["f0_run_matrix"])
    selected_days_path = repo_path(config["inputs"]["selected_forcing_days"])
    n24_path = repo_path(config["inputs"]["n24_cell_set"])
    rows: list[dict[str, str]] = []
    if not matrix_path.exists():
        rows.append(status_row("run_matrix_exists", BLOCKED, matrix_path, "missing"))
        return rows, 0, False
    if not selected_days_path.exists():
        rows.append(status_row("selected_forcing_days_exists", BLOCKED, selected_days_path, "missing"))
        return rows, 0, False
    if not n24_path.exists():
        rows.append(status_row("n24_cell_set_exists", BLOCKED, n24_path, "missing"))
        return rows, 0, False

    manifest = read_csv_rows(matrix_path)
    selected_days = read_csv_rows(selected_days_path)
    n24_cells = read_csv_rows(n24_path)
    expected_hours = [str(int(hour)) for hour in expected["hours_sgt"]]
    expected_scenarios = sorted(str(value) for value in expected["scenarios"])
    expected_execute = normalize_no_yes(expected["solweig_execute_now"])

    run_ids = [row.get("run_id", "") for row in manifest]
    output_groups = [row.get("expected_output_group", "") for row in manifest]
    observed_cells = sorted_unique(row.get("cell_id", "") for row in manifest)
    observed_days = sorted_unique(row.get("forcing_day_id", "") for row in manifest)
    observed_hours = sorted_unique(row.get("hour_sgt", "") for row in manifest)
    observed_scenarios = sorted_unique(row.get("scenario", "") for row in manifest)
    observed_execute = sorted_unique(normalize_no_yes(row.get("solweig_execute_now", "")) for row in manifest)
    n24_unique = sorted_unique(row.get("cell_id", "") for row in n24_cells)

    checks = [
        ("run_matrix_exists", PASS, matrix_path, "exists", ""),
        ("selected_forcing_days_exists", PASS, selected_days_path, "exists", ""),
        ("n24_cell_set_exists", PASS, n24_path, "exists", ""),
        ("planned_rows", PASS if len(manifest) == int(expected["planned_rows"]) else FAILED, expected["planned_rows"], len(manifest), "No rows executed."),
        ("unique_cells", PASS if len(observed_cells) == int(expected["unique_cells"]) else FAILED, expected["unique_cells"], len(observed_cells), ",".join(observed_cells)),
        ("selected_forcing_days_rows", PASS if len(selected_days) == int(expected["forcing_days"]) else FAILED, expected["forcing_days"], len(selected_days), ",".join(row.get("forcing_day_id", "") for row in selected_days)),
        ("manifest_forcing_days", PASS if len(observed_days) == int(expected["forcing_days"]) else FAILED, expected["forcing_days"], len(observed_days), ",".join(observed_days)),
        ("manifest_hours_sgt", PASS if observed_hours == expected_hours else FAILED, ",".join(expected_hours), ",".join(observed_hours), ""),
        ("manifest_scenarios", PASS if observed_scenarios == expected_scenarios else FAILED, ",".join(expected_scenarios), ",".join(observed_scenarios), ""),
        ("source_solweig_execute_now_no", PASS if observed_execute == [expected_execute] else FAILED, expected_execute, ",".join(observed_execute), "All manifest rows must remain execution-disabled."),
        ("run_id_uniqueness", PASS if len(run_ids) == len(set(run_ids)) else FAILED, len(run_ids), len(set(run_ids)), "No duplicate run_id values allowed."),
        ("expected_output_group_uniqueness", PASS if len(output_groups) == len(set(output_groups)) else FAILED, len(output_groups), len(set(output_groups)), "Each row must map to one output group."),
        ("n24_unique_cells", PASS if len(n24_unique) == int(expected["unique_cells"]) else FAILED, expected["unique_cells"], len(n24_unique), "N24 contract supplied by F0."),
    ]
    rows.extend(status_row(*check) for check in checks)
    return rows, len(manifest), all(row["status"] == PASS for row in rows)


def asset_row(
    asset_type: str,
    logical_name: str,
    expected_path: Path | str,
    required_for_execution: bool,
    commit_safe: bool,
    notes: str,
) -> dict[str, str]:
    """Build one required-asset inventory row without copying assets."""
    if isinstance(expected_path, Path):
        path_text = rel(expected_path)
        exists = YES if expected_path.exists() else NO
    else:
        path_text = expected_path
        exists = NO
    return {
        "asset_type": asset_type,
        "logical_name": logical_name,
        "expected_path": path_text,
        "exists": exists,
        "required_for_execution": YES if required_for_execution else NO,
        "commit_safe": YES if commit_safe else NO,
        "notes": notes,
    }


def expected_forcing_path(config: dict[str, Any], forcing_day: dict[str, str], hour_sgt: int) -> Path:
    """Build the expected met forcing path for a forcing day and hour."""
    date_yyyymmdd = forcing_day["date"].replace("-", "_")
    template = str(config["asset_templates"]["met_forcing_path_template"])
    return repo_path(template.format(date_yyyymmdd=date_yyyymmdd, hour_sgt=hour_sgt))


def build_asset_inventory(config: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    """Inventory execution assets, marking missing rasters/SVF as non-fatal."""
    inventory: list[dict[str, str]] = []
    inputs = config["inputs"]
    templates = config["asset_templates"]

    def add(asset_type: str, name: str, path_or_text: Path | str, required: bool, safe: bool, notes: str) -> None:
        inventory.append(asset_row(asset_type, name, path_or_text, required, safe, notes))

    for key in [
        "active_dev_board",
        "f0_status",
        "f0_run_matrix",
        "selected_forcing_days",
        "n24_cell_set",
        "f0_qgis_execution_readme",
        "f0_stability_metrics_protocol",
    ]:
        add("control_file", key, repo_path(inputs[key]), True, True, "Required compact control input for B8.5-F1.")

    for key in ["grid_feature_path", "v12_grid_typology_revised", "v12_grid_typology_candidates", "overhead_vector_path"]:
        add("cell_geometry_or_vector", key, repo_path(inputs[key]), key in {"grid_feature_path", "overhead_vector_path"}, True, "Geometry/vector reference; not copied.")

    for key in ["building_dsm_path", "vegetation_dsm_path"]:
        add("global_raster_reference", key, repo_path(inputs[key]), True, False, "Raster reference only; do not copy or commit.")

    for key in [
        "b3_qgis_runner",
        "b7_qgis_runner",
        "aggregate_tmrt_reference",
        "n24_effective_parameters",
        "n150_effective_parameters",
        "n24_qgis_algorithm_resolution",
        "n24_qgis_preprocess_algorithm_resolution",
        "n150_qgis_algorithm_resolution",
        "n150_qgis_preprocess_algorithm_resolution",
    ]:
        add("reference_script_or_manifest", key, repo_path(inputs[key]), False, True, "Reference for parameter contract or prior execution behavior.")

    add("qgis_algorithm_manual_check", "solweig_algorithm_id_hint", str(config["qgis_execution"]["qgis_algorithm_id_hint"]), True, True, "Must be verified inside QGIS/UMEP before execution; not checked by this package.")
    add("local_output_root", "manual_local_raw_output_root", str(templates["manual_local_raw_output_root"]), True, False, "Local-only placeholder for manual QGIS output; do not execute blindly or commit raster outputs.")

    matrix_path = repo_path(inputs["f0_run_matrix"])
    selected_path = repo_path(inputs["selected_forcing_days"])
    cells = sorted_unique(row.get("cell_id", "") for row in read_csv_rows(matrix_path)) if matrix_path.exists() else []
    selected_days = read_csv_rows(selected_path) if selected_path.exists() else []
    cell_root = repo_path(templates["existing_n24_tile_root_reference"])
    for cell_id in cells:
        root = cell_root / cell_id
        add("cell_geometry", f"{cell_id}_focus_cell", root / str(templates["focus_geojson_name"]), True, False, "Existing N24 tile focus mask location if retained locally.")
        for logical, key in [
            ("dsm_buildings", "dsm_buildings_name"),
            ("dem", "dem_name"),
            ("vegetation_base", "vegetation_base_name"),
            ("vegetation_overhead", "vegetation_overhead_name"),
            ("wall_height", "wall_height_name"),
            ("wall_aspect", "wall_aspect_name"),
        ]:
            add("raster_tile", f"{cell_id}_{logical}", root / str(templates[key]), True, False, "Raster path documented only; missing/untracked is non-fatal for this package.")
        add("svf_zip", f"{cell_id}_svf_base", root / str(templates["svf_base_zip"]), True, False, "SVF zip path documented only; do not copy svfs.zip.")
        add("svf_zip", f"{cell_id}_svf_overhead", root / str(templates["svf_overhead_zip"]), True, False, "SVF zip path documented only; do not copy svfs.zip.")

    for forcing_day in selected_days:
        for hour_sgt in config["expected_manifest"]["hours_sgt"]:
            name = f"{forcing_day.get('forcing_day_id', '')}_h{int(hour_sgt):02d}"
            add("met_forcing_file", name, expected_forcing_path(config, forcing_day, int(hour_sgt)), True, False, "Expected SOLWEIG met forcing text file; inventory only.")

    missing_control = [row for row in inventory if row["required_for_execution"] == YES and row["exists"] == NO and row["asset_type"] == "control_file"]
    missing_raster_or_manual = [
        row
        for row in inventory
        if row["required_for_execution"] == YES
        and row["exists"] == NO
        and row["asset_type"] in {"global_raster_reference", "raster_tile", "svf_zip", "qgis_algorithm_manual_check", "local_output_root", "met_forcing_file"}
    ]
    if missing_control:
        return inventory, BLOCKED
    if missing_raster_or_manual:
        return inventory, PARTIAL
    return inventory, READY


def build_qgis_parameter_contract(config: dict[str, Any]) -> list[dict[str, str]]:
    """Build the SOLWEIG/QGIS parameter contract from B3/B7 conventions."""
    rows = [
        ("algorithm", "qgis_algorithm_id", "", "yes", config["qgis_execution"]["qgis_algorithm_id_hint"], "QGIS Processing registry", "Verify inside QGIS/UMEP before execution."),
        ("path", "run_matrix_path", "", "yes", config["inputs"]["f0_run_matrix"], "Config", "Controlling 480-row manifest."),
        ("path", "output_root", "OUTPUT_DIR", "yes", config["asset_templates"]["manual_local_raw_output_root"], "Config", "Local-only output root outside Git."),
        ("path", "input_dsm", "INPUT_DSM", "yes", "existing_n24_tile_root_reference/<cell_id>/dsm_buildings_tile.tif", "B3/B7 runner", "Raster reference; do not copy."),
        ("path", "input_svf", "INPUT_SVF", "yes", "existing_n24_tile_root_reference/<cell_id>/svf_<scenario>/svfs.zip", "B3/B7 runner", "SVF zip reference; do not copy."),
        ("path", "inputmet", "INPUTMET", "yes", config["asset_templates"]["met_forcing_path_template"], "Config", "Required for each forcing_day_id x hour_sgt."),
        ("constant", "LEAF_START", "LEAF_START", "yes", config["solweig_parameters"]["LEAF_START"], "n24/n150 effective parameters", ""),
        ("constant", "LEAF_END", "LEAF_END", "yes", config["solweig_parameters"]["LEAF_END"], "n24/n150 effective parameters", ""),
        ("constant", "UTC", "UTC", "yes", config["solweig_parameters"]["UTC"], "n24/n150 effective parameters", "Singapore local time."),
        ("constant", "TRANS_VEG", "TRANS_VEG", "yes", config["solweig_parameters"]["TRANS_VEG"], "n24/n150 effective parameters", ""),
        ("constant", "INPUT_THEIGHT", "INPUT_THEIGHT", "yes", config["solweig_parameters"]["INPUT_THEIGHT"], "n24/n150 effective parameters", ""),
        ("constant", "OUTPUT_TMRT", "OUTPUT_TMRT", "yes", config["solweig_parameters"]["OUTPUT_TMRT"], "n24/n150 effective parameters", "Only Tmrt output is required for later aggregation."),
    ]
    return [
        {
            "contract_section": section,
            "parameter_name": name,
            "qgis_parameter_key": qgis_key,
            "required": required,
            "expected_value_or_template": clean(value),
            "source": source,
            "notes": notes,
        }
        for section, name, qgis_key, required, value, source, notes in rows
    ]


def build_run_log_schema() -> list[dict[str, str]]:
    """Build the expected one-row-per-run QGIS run-log schema."""
    fields = [
        ("run_id", "string", "yes", "unique manifest run_id", "Primary run key."),
        ("cell_id", "string", "yes", "TP_####", "Focus cell identifier."),
        ("forcing_day_id", "string", "yes", "FD##_...", "Selected forcing day key."),
        ("date", "date", "yes", "YYYY-MM-DD", "Forcing day date in Singapore local time."),
        ("hour_sgt", "integer", "yes", "10,12,13,15,16", "Execution hour in SGT."),
        ("scenario", "string", "yes", "base|overhead_as_canopy", "SOLWEIG scenario."),
        ("started_at", "datetime", "yes", "ISO-8601 local timestamp", "Attempt start."),
        ("completed_at", "datetime", "yes", "ISO-8601 local timestamp", "Attempt completion."),
        ("status", "string", "yes", "dry_run|success|failed|skipped|blocked", "Execution status; dry_run is default."),
        ("error_message", "string", "no", "free text", "Error text only when status is failed or blocked."),
        ("qgis_algorithm_id", "string", "yes", "umep:Outdoor Thermal Comfort: SOLWEIG", "Resolved or intended QGIS algorithm id."),
        ("output_tmrt_path", "string", "yes", "absolute or local-only path", "Expected or produced Tmrt raster path; not committed."),
        ("notes", "string", "no", "free text", "Execution notes and manual-review comments."),
    ]
    return [
        {"column_name": name, "dtype": dtype, "required": required, "allowed_values_or_format": allowed, "description": description}
        for name, dtype, required, allowed, description in fields
    ]


def build_aggregation_contract(config: dict[str, Any]) -> list[dict[str, str]]:
    """Build the future post-SOLWEIG aggregation contract."""
    domain = config["aggregation_contract"]["reference_domain"]
    rows = [
        ("input", "run_log", "yes", "CSV", "one row per run_id", "Use the expected run log schema."),
        ("input", "tmrt_raster_paths", "yes", "file path", "output_tmrt_path from run log", "Raster paths stay local/uncommitted."),
        ("input", "focus_cell_mask", "yes", "GeoJSON/raster mask", "one focus mask per cell_id", "Clip Tmrt to the 100 m focus cell."),
        ("cell_summary", "tmrt_mean_c", "yes", "float", "mean valid focus-cell pixels", "SOLWEIG Tmrt only; not WBGT."),
        ("cell_summary", "tmrt_p50_c", "yes", "float", "50th percentile valid focus-cell pixels", ""),
        ("cell_summary", "tmrt_p75_c", "yes", "float", "75th percentile valid focus-cell pixels", ""),
        ("cell_summary", "tmrt_p90_c", "yes", "float", "90th percentile valid focus-cell pixels", "Primary System B target family metric."),
        ("cell_summary", "tmrt_p95_c", "yes", "float", "95th percentile valid focus-cell pixels", ""),
        ("cell_summary", "tmrt_max_c", "yes", "float", "max valid focus-cell pixels", ""),
        ("cell_summary", "pct_pixels_tmrt_ge_40", "yes", "float", "100 * count(Tmrt >= 40) / valid pixels", ""),
        ("cell_summary", "pct_pixels_tmrt_ge_45", "yes", "float", "100 * count(Tmrt >= 45) / valid pixels", ""),
        ("cell_summary", "pct_pixels_tmrt_ge_50", "yes", "float", "100 * count(Tmrt >= 50) / valid pixels", ""),
        ("cell_summary", "pct_pixels_tmrt_ge_55", "yes", "float", "100 * count(Tmrt >= 55) / valid pixels", ""),
        ("modifier", "delta_tmrt_p90_c", "yes", "float", f"tmrt_p90_c minus reference within {domain}", "Delta Tmrt is not delta WBGT."),
        ("modifier", "m_rad_pct01", "yes", "float", f"percentile rank within {domain}, scaled 0..1", "Radiative modifier only; not risk."),
        ("stability", "stability_metrics", "yes", "CSV/Markdown", "B8.5-F0 protocol", "No causal heat-risk claims."),
    ]
    return [
        {
            "contract_section": section,
            "field_or_artifact": field,
            "required": required,
            "dtype_or_artifact_type": dtype,
            "grouping_or_formula": formula,
            "notes": notes,
        }
        for section, field, required, dtype, formula, notes in rows
    ]


def artifact_paths(config: dict[str, Any]) -> list[Path]:
    """Return the expected created/modified package paths."""
    outputs = config["outputs"]
    return [
        repo_path("configs/v12/systemb_b85_f1_execution_package.yaml"),
        repo_path("scripts/v12_b85_prepare_execution_package.py"),
        repo_path("scripts/v12_b85_validate_execution_package.py"),
        repo_path(config["qgis_execution"]["skeleton_script"]),
        repo_path(outputs["canonical_note_cn"]),
        repo_path(outputs["manifest_validation"]),
        repo_path(outputs["required_asset_inventory"]),
        repo_path(outputs["qgis_parameter_contract"]),
        repo_path(outputs["expected_run_log_schema"]),
        repo_path(outputs["expected_aggregation_contract"]),
        repo_path(outputs["execution_readme"]),
        repo_path(outputs["status"]),
    ]


def markdown_list(paths: list[Path]) -> str:
    """Render paths as Markdown bullets."""
    return "\n".join(f"- `{rel(path)}`" for path in paths)


def git_output(args: list[str]) -> str:
    """Run a lightweight Git command for status reporting."""
    completed = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def write_execution_readme(path: Path, config: dict[str, Any], manifest_rows: int, asset_status: str) -> None:
    """Write the B8.5-F1 execution package README."""
    text = f"""# B8.5-F1 Execution Package README

Generated: {now_stamp()}

## Status

This package prepares execution only. QGIS was not run. SOLWEIG was not run. No rasters were created or copied. No local WBGT, risk map, hazard score, risk_score, AOI-wide prediction, or System A/B coupling output was created. This package does not approve B9 AOI-wide inference.

## Manifest

- Source manifest: `{config["inputs"]["f0_run_matrix"]}`
- Planned rows: `{manifest_rows}`
- Expected cells: `24`
- Expected forcing days: `2`
- Expected hours SGT: `10,12,13,15,16`
- Expected scenarios: `base`, `overhead_as_canopy`
- Required source flag: `solweig_execute_now=no`

## Asset Readiness

Asset readiness is `{asset_status}`. Missing or untracked raster/SVF paths do not fail this package; they are documented for human checking before QGIS execution. Met forcing files are inventoried for each `forcing_day_id x hour_sgt`.

## Local-Only Output Root

The placeholder `{config["asset_templates"]["manual_local_raw_output_root"]}` is local-only and outside the Git worktree. It is not a blind execution command and no raster output from that path should be committed.

## Human Execution Rule

The next step is human-reviewed QGIS execution using the skeleton and contracts in this package. Do not interpret SOLWEIG Tmrt as WBGT and do not create local WBGT, risk, hazard_score, risk_score, AOI-wide prediction, or System A/B coupling outputs in this lane.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_cn_doc(path: Path, config: dict[str, Any], manifest_rows: int, asset_status: str) -> None:
    """Write the Chinese execution-package note using escaped source text."""
    text = f"""# OpenHeat System B B8.5-F1 \u6267\u884c\u5305\u8bf4\u660e

\u751f\u6210\u65f6\u95f4\uff1a{now_stamp()}

## \u7ed3\u8bba

B8.5-F1 \u53ea\u51c6\u5907\u540e\u7eed QGIS/SOLWEIG \u6267\u884c\u6240\u9700\u7684\u914d\u7f6e\u3001\u6e05\u5355\u3001\u53c2\u6570\u5951\u7ea6\u548c\u65e5\u5fd7/\u805a\u5408\u5951\u7ea6\u3002\u5f53\u524d\u72b6\u6001\u4e3a `PASS`\uff0c\u4f46\u8d44\u4ea7\u5c31\u7eea\u72b6\u6001\u4fdd\u6301\u4e3a `{asset_status}`\u3002\u672c\u9636\u6bb5\u6ca1\u6709\u8fd0\u884c QGIS\uff0c\u6ca1\u6709\u8fd0\u884c SOLWEIG\uff0c\u6ca1\u6709\u521b\u5efa\u6216\u590d\u5236 raster\uff0c\u6ca1\u6709\u521b\u5efa\u672c\u5730 WBGT\uff0c\u6ca1\u6709\u521b\u5efa risk map\u3001hazard_score\u3001risk_score\uff0c\u4e5f\u6ca1\u6709\u521b\u5efa AOI-wide prediction \u6216 System A/B coupling \u8f93\u51fa\u3002\u672c\u5305\u4e0d\u4ee3\u8868 B9 AOI-wide inference \u83b7\u6279\u3002

## \u8303\u56f4

- \u63a7\u5236\u6e05\u5355\uff1a`{config["inputs"]["f0_run_matrix"]}`
- \u8ba1\u5212\u884c\u6570\uff1a`{manifest_rows}`
- \u5355\u5143\u683c\u6570\u91cf\uff1a`24`
- forcing days\uff1a`2`
- \u5c0f\u65f6\uff1a`10,12,13,15,16` SGT
- \u573a\u666f\uff1a`base` \u548c `overhead_as_canopy`
- \u8d44\u4ea7\u5c31\u7eea\u72b6\u6001\uff1a`{asset_status}`
- \u6e90 manifest \u8981\u6c42\uff1a`solweig_execute_now=no`
- QGIS/SOLWEIG executed\uff1a`no`

## \u4ea7\u7269

- manifest validation\uff1a`{config["outputs"]["manifest_validation"]}`
- required asset inventory\uff1a`{config["outputs"]["required_asset_inventory"]}`
- QGIS parameter contract\uff1a`{config["outputs"]["qgis_parameter_contract"]}`
- expected run log schema\uff1a`{config["outputs"]["expected_run_log_schema"]}`
- expected aggregation contract\uff1a`{config["outputs"]["expected_aggregation_contract"]}`
- QGIS skeleton\uff1a`{config["qgis_execution"]["skeleton_script"]}`
- status\uff1a`{config["outputs"]["status"]}`

## \u8def\u5f84\u8bf4\u660e

\u62a5\u544a\u548c CSV \u4e2d\u7684\u4ed3\u5e93\u8d44\u4ea7\u5e94\u4f7f\u7528 repo-relative path\u3002\u539f\u59cb SOLWEIG \u8f93\u51fa\u6839\u76ee\u5f55\u4f7f\u7528\u672c\u5730\u5360\u4f4d\u8def\u5f84 `{config["asset_templates"]["manual_local_raw_output_root"]}`\uff1b\u8be5\u8def\u5f84\u53ea\u8868\u793a\u4eba\u5de5 QGIS \u6267\u884c\u65f6\u7684\u672c\u5730\u8f93\u51fa\u4f4d\u7f6e\uff0c\u4e0d\u80fd\u4f5c\u4e3a\u76f2\u76ee\u6267\u884c\u547d\u4ee4\uff0c\u4e5f\u4e0d\u80fd\u628a raster \u6216 `svfs.zip` \u63d0\u4ea4\u5230\u4ed3\u5e93\u3002

## \u540e\u7eed\u6b65\u9aa4

\u4e0b\u4e00\u6b65\u53ea\u80fd\u662f\u4eba\u5de5\u590d\u6838\u540e\u7684 QGIS \u6267\u884c\u3002\u6267\u884c\u8005\u5e94\u4f7f\u7528\u672c\u5305\u4e2d\u7684 skeleton \u548c\u5951\u7ea6\uff0c\u786e\u8ba4 QGIS/UMEP \u7b97\u6cd5\u3001met forcing \u6587\u4ef6\u3001focus-cell mask\u3001raster/SVF \u8def\u5f84\u548c\u672c\u5730\u8f93\u51fa\u76ee\u5f55\u3002SOLWEIG \u8f93\u51fa\u4ecd\u7136\u53ea\u662f Tmrt \u6d3e\u751f\u7684\u5c40\u5730\u8f90\u5c04\u4fee\u9970\u6807\u7b7e\uff0c\u4e0d\u80fd\u88ab\u89e3\u91ca\u4e3a WBGT\uff0c\u4e5f\u4e0d\u80fd\u5347\u7ea7\u4e3a\u98ce\u9669\u56fe\u6216\u672c\u5730 WBGT \u56fe\u3002
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_status_file(
    path: Path,
    config: dict[str, Any],
    status: str,
    manifest_rows: int,
    asset_status: str,
    files_created: list[Path],
    validation_rows: list[dict[str, str]],
) -> None:
    """Write the B8.5-F1 status report."""
    branch = git_output(["git", "branch", "--show-current"])
    status_short = git_output(["git", "status", "--short", "--", "."])
    failed_checks = [row for row in validation_rows if row["status"] != PASS]
    failed_text = "none" if not failed_checks else ", ".join(row["check_name"] for row in failed_checks)
    text = f"""# B8.5-F1 Status

Generated: {now_stamp()}

## Status

{status}

## Branch

`{branch}`

## Scope

Execution-package preparation only. QGIS was not run. SOLWEIG was not run. No rasters were created or copied. No local WBGT, hazard_score, risk_score, risk map, AOI-wide prediction, or System A/B coupling output was created. No B9 approval is granted by this package.

## Key Results

- Manifest row count: `{manifest_rows}`
- Manifest validation failed checks: `{failed_text}`
- Asset readiness status: `{asset_status}`
- QGIS/SOLWEIG executed: `no`
- Source manifest requires `solweig_execute_now=no`

## Files Created / Modified

{markdown_list(files_created)}

## Local-Only Output Root

`{config["asset_templates"]["manual_local_raw_output_root"]}` is a local-only placeholder for manual QGIS execution outside the Git worktree. It is not a blind execution command, and no raster or `svfs.zip` output from that path should be staged or committed.

## Current Git Status Short

```text
{status_short}
```

## Next Recommended Action

Human review of this package, then manual QGIS execution using the skeleton if the reviewer accepts the contracts and confirms the local raster/SVF/met forcing assets.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def package_status(manifest_ok: bool, asset_status: str) -> str:
    """Return package-level status for compact final reporting."""
    if not manifest_ok or asset_status == BLOCKED:
        return BLOCKED
    return PASS


def prepare(config_path: Path = DEFAULT_CONFIG) -> PackageResult:
    """Prepare all B8.5-F1 execution package artifacts."""
    config = read_config(config_path)
    outputs = config["outputs"]
    repo_path(outputs["out_dir"]).mkdir(parents=True, exist_ok=True)
    validation_rows, manifest_rows, manifest_ok = validate_manifest(config)
    inventory, asset_status = build_asset_inventory(config)
    status = package_status(manifest_ok, asset_status)
    files_created = artifact_paths(config)

    write_csv_rows(repo_path(outputs["manifest_validation"]), validation_rows, ["section", "check_name", "status", "expected", "observed", "detail"])
    write_csv_rows(repo_path(outputs["required_asset_inventory"]), inventory, ["asset_type", "logical_name", "expected_path", "exists", "required_for_execution", "commit_safe", "notes"])
    write_csv_rows(repo_path(outputs["qgis_parameter_contract"]), build_qgis_parameter_contract(config), ["contract_section", "parameter_name", "qgis_parameter_key", "required", "expected_value_or_template", "source", "notes"])
    write_csv_rows(repo_path(outputs["expected_run_log_schema"]), build_run_log_schema(), ["column_name", "dtype", "required", "allowed_values_or_format", "description"])
    write_csv_rows(repo_path(outputs["expected_aggregation_contract"]), build_aggregation_contract(config), ["contract_section", "field_or_artifact", "required", "dtype_or_artifact_type", "grouping_or_formula", "notes"])
    write_execution_readme(repo_path(outputs["execution_readme"]), config, manifest_rows, asset_status)
    write_cn_doc(repo_path(outputs["canonical_note_cn"]), config, manifest_rows, asset_status)
    write_status_file(repo_path(outputs["status"]), config, status, manifest_rows, asset_status, files_created, validation_rows)

    return PackageResult(
        status=status,
        manifest_row_count=manifest_rows,
        asset_readiness_status=asset_status,
        qgis_solweig_executed=NO,
        next_recommended_action="Human-review the package, then execute manually inside QGIS if accepted." if status == PASS else "Resolve blocked manifest/control inputs before any QGIS execution.",
        files_created=files_created,
    )


def main() -> int:
    """Parse CLI arguments and prepare the package."""
    parser = argparse.ArgumentParser(description="Prepare the B8.5-F1 execution package without running QGIS/SOLWEIG.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F1 YAML config path.")
    args = parser.parse_args()
    result = prepare(repo_path(args.config))
    print(f"Status: {result.status}")
    print(f"Manifest row count: {result.manifest_row_count}")
    print(f"Asset readiness status: {result.asset_readiness_status}")
    print(f"QGIS/SOLWEIG executed: {result.qgis_solweig_executed}")
    print(f"Next recommended action: {result.next_recommended_action}")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.status == PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
