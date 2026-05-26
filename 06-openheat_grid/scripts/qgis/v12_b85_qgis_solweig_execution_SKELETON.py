"""B8.5-F1 QGIS/SOLWEIG execution skeleton.

DO NOT RUN BLINDLY.

Run only inside a reviewed QGIS Desktop Python environment with Processing and
UMEP loaded. This skeleton reads the B8.5-F1 config, iterates the F0 480-row run
matrix, builds expected output folders from `expected_output_group`, and writes
a run log with one row per `run_id`.

Inputs:
    configs/v12/systemb_b85_f1_execution_package.yaml
    outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv
    Existing local-only raster/SVF/met forcing assets declared by the config.

Outputs:
    outputs/v12_surrogate/b8_5_execution_package/future_b85_f1_qgis_run_log.csv
    When DRY_RUN is manually changed to False inside QGIS, SOLWEIG Tmrt rasters
    are expected under the configured local-only output root outside Git.

Saved metrics:
    One run-log row per run_id with cell, forcing day, date, hour, scenario,
    timestamps, status, error message, QGIS algorithm id, expected Tmrt path,
    and notes.

Default behavior:
    DRY_RUN = True. No SOLWEIG execution happens. To execute later, a human must
    review this file, confirm all local assets, open it inside QGIS, and manually
    change DRY_RUN to False. Never write rasters into Git-tracked paths by
    default.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs/v12/systemb_b85_f1_execution_package.yaml"

# Human review gate: leave True unless executing manually inside QGIS after review.
DRY_RUN = True


def now_iso() -> str:
    """Return a local ISO timestamp."""
    return datetime.now().isoformat(timespec="seconds")


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by the B8.5-F1 config."""
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
    """Read the simple nested YAML shape used by this package config."""
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
    """Load YAML config, preferring PyYAML when the QGIS Python has it."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Config did not parse to a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def repo_path(value: str | Path) -> Path:
    """Resolve repository-relative paths."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read the controlling run matrix."""
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_log_row(log_path: Path, row: dict[str, str]) -> None:
    """Append one run-log row."""
    fieldnames = [
        "run_id",
        "cell_id",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "started_at",
        "completed_at",
        "status",
        "error_message",
        "qgis_algorithm_id",
        "output_tmrt_path",
        "notes",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fieldnames})


def ensure_output_root_outside_git(output_root: Path) -> None:
    """Prevent SOLWEIG raster writes into the Git worktree by default."""
    resolved_root = output_root.resolve()
    resolved_project = PROJECT_ROOT.resolve()
    try:
        resolved_root.relative_to(resolved_project)
    except ValueError:
        return
    raise RuntimeError(
        "Refusing to execute SOLWEIG because manual_local_raw_output_root is inside "
        f"the Git worktree: {resolved_root}"
    )


def scenario_suffix(scenario: str) -> str:
    """Return the path suffix used by older v12 tile folders."""
    if scenario == "base":
        return "base"
    if scenario == "overhead_as_canopy":
        return "overhead_as_canopy"
    raise ValueError(f"Unknown scenario: {scenario}")


def expected_forcing_path(config: dict[str, Any], row: dict[str, str]) -> Path:
    """Build expected met forcing path from the package config."""
    date_yyyymmdd = row["date"].replace("-", "_")
    template = str(config["asset_templates"]["met_forcing_path_template"])
    return repo_path(template.format(date_yyyymmdd=date_yyyymmdd, hour_sgt=int(row["hour_sgt"])))


def expected_tile_paths(config: dict[str, Any], row: dict[str, str]) -> dict[str, Path]:
    """Build expected local input paths for one manifest row."""
    templates = config["asset_templates"]
    cell_root = repo_path(templates["existing_n24_tile_root_reference"]) / row["cell_id"]
    scenario = scenario_suffix(row["scenario"])
    cdsm_name = (
        templates["vegetation_base_name"]
        if row["scenario"] == "base"
        else templates["vegetation_overhead_name"]
    )
    svf_zip = templates["svf_base_zip"] if row["scenario"] == "base" else templates["svf_overhead_zip"]
    return {
        "input_dsm": cell_root / str(templates["dsm_buildings_name"]),
        "input_svf": cell_root / str(svf_zip),
        "input_height": cell_root / str(templates["wall_height_name"]),
        "input_aspect": cell_root / str(templates["wall_aspect_name"]),
        "input_cdsm": cell_root / str(cdsm_name),
        "input_dem": cell_root / str(templates["dem_name"]),
        "inputmet": expected_forcing_path(config, row),
        "focus_cell": cell_root / str(templates["focus_geojson_name"]),
        "scenario_marker": cell_root / f"solweig_{scenario}",
    }


def expected_output_paths(config: dict[str, Any], row: dict[str, str]) -> tuple[Path, Path]:
    """Build the local-only output folder and expected Tmrt path."""
    output_root = Path(str(config["asset_templates"]["manual_local_raw_output_root"]))
    output_dir = output_root / row["expected_output_group"]
    return output_dir, output_dir / "Tmrt_average.tif"


def qgis_path(path: Path) -> str:
    """Return a QGIS-friendly path string."""
    return path.as_posix()


def build_solweig_parameters(config: dict[str, Any], row: dict[str, str], algorithm_id: str) -> dict[str, Any]:
    """Build a SOLWEIG parameter dict based on existing v12 B3/B7 runners."""
    paths = expected_tile_paths(config, row)
    output_dir, _ = expected_output_paths(config, row)
    solweig = config["solweig_parameters"]
    return {
        "QGIS_ALGORITHM_ID_HINT": algorithm_id,
        "INPUT_DSM": qgis_path(paths["input_dsm"]),
        "INPUT_SVF": qgis_path(paths["input_svf"]),
        "INPUT_HEIGHT": qgis_path(paths["input_height"]),
        "INPUT_ASPECT": qgis_path(paths["input_aspect"]),
        "INPUT_CDSM": qgis_path(paths["input_cdsm"]),
        "INPUT_TDSM": None,
        "INPUT_DEM": qgis_path(paths["input_dem"]),
        "INPUT_LC": None,
        "INPUT_ANISO": "",
        "INPUT_WALLSCHEME": "",
        "TRANS_VEG": int(solweig["TRANS_VEG"]),
        "INPUT_THEIGHT": float(solweig["INPUT_THEIGHT"]),
        "LEAF_START": int(solweig["LEAF_START"]),
        "LEAF_END": int(solweig["LEAF_END"]),
        "CONIFER_TREES": False,
        "USE_LC_BUILD": False,
        "SAVE_BUILD": False,
        "WALLTEMP_NETCDF": False,
        "WALL_TYPE": 0,
        "ALBEDO_WALLS": 0.20,
        "ALBEDO_GROUND": 0.15,
        "EMIS_WALLS": 0.90,
        "EMIS_GROUND": 0.95,
        "ABS_S": 0.70,
        "ABS_L": 0.95,
        "POSTURE": 0,
        "CYL": True,
        "INPUTMET": qgis_path(paths["inputmet"]),
        "ONLYGLOBAL": False,
        "UTC": int(solweig["UTC"]),
        "WOI_FILE": None,
        "WOI_FIELD": "",
        "POI_FILE": None,
        "POI_FIELD": "",
        "AGE": 35,
        "ACTIVITY": 80.0,
        "CLO": 0.9,
        "WEIGHT": 75,
        "HEIGHT": 180,
        "SEX": 0,
        "SENSOR_HEIGHT": 10.0,
        "OUTPUT_TMRT": bool(solweig["OUTPUT_TMRT"]),
        "OUTPUT_KDOWN": bool(solweig["OUTPUT_KDOWN"]),
        "OUTPUT_KUP": bool(solweig["OUTPUT_KUP"]),
        "OUTPUT_LDOWN": bool(solweig["OUTPUT_LDOWN"]),
        "OUTPUT_LUP": bool(solweig["OUTPUT_LUP"]),
        "OUTPUT_SH": bool(solweig["OUTPUT_SH"]),
        "OUTPUT_TREEPLANTER": bool(solweig["OUTPUT_TREEPLANTER"]),
        "OUTPUT_DIR": qgis_path(output_dir),
    }


def missing_required_inputs(config: dict[str, Any], row: dict[str, str]) -> list[str]:
    """Return missing expected local inputs for one run."""
    paths = expected_tile_paths(config, row)
    missing = []
    for label, path in paths.items():
        if label == "scenario_marker":
            continue
        if not path.exists():
            missing.append(f"{label}: {path}")
    return missing


def run_one_row(config: dict[str, Any], row: dict[str, str], algorithm_id: str) -> dict[str, str]:
    """Dry-run or execute one SOLWEIG row after manual review."""
    started = now_iso()
    output_dir, tmrt_path = expected_output_paths(config, row)
    status = "dry_run"
    error_message = ""
    notes = "DRY_RUN=True; SOLWEIG not executed."
    try:
        params = build_solweig_parameters(config, row, algorithm_id)
        if not DRY_RUN:
            output_root = Path(str(config["asset_templates"]["manual_local_raw_output_root"]))
            ensure_output_root_outside_git(output_root)
            missing = missing_required_inputs(config, row)
            if missing:
                raise FileNotFoundError("; ".join(missing))
            output_dir.mkdir(parents=True, exist_ok=True)
            import processing  # type: ignore

            processing.run(algorithm_id, params)
            status = "success" if tmrt_path.exists() else "failed"
            notes = "SOLWEIG execution attempted after manual DRY_RUN=False change."
            if status == "failed":
                error_message = "SOLWEIG completed but expected Tmrt_average.tif was not found."
    except Exception as exc:
        status = "blocked" if not DRY_RUN else "dry_run"
        error_message = str(exc)
        notes = "Dry run parameter build raised an error." if DRY_RUN else "Execution blocked or failed."
    completed = now_iso()
    return {
        "run_id": row.get("run_id", ""),
        "cell_id": row.get("cell_id", ""),
        "forcing_day_id": row.get("forcing_day_id", ""),
        "date": row.get("date", ""),
        "hour_sgt": row.get("hour_sgt", ""),
        "scenario": row.get("scenario", ""),
        "started_at": started,
        "completed_at": completed,
        "status": status,
        "error_message": error_message,
        "qgis_algorithm_id": algorithm_id,
        "output_tmrt_path": qgis_path(tmrt_path),
        "notes": notes,
    }


def main() -> None:
    """Iterate the B8.5-F0 run matrix and write a QGIS run log."""
    config = read_config(CONFIG_PATH)
    matrix_path = repo_path(config["inputs"]["f0_run_matrix"])
    log_path = repo_path(config["qgis_execution"]["expected_run_log_path"])
    algorithm_id = str(config["qgis_execution"]["qgis_algorithm_id_hint"])
    rows = read_csv_rows(matrix_path)
    print("B8.5-F1 QGIS/SOLWEIG skeleton")
    print(f"DRY_RUN={DRY_RUN}")
    print(f"Rows: {len(rows)}")
    print(f"Run log: {log_path}")
    if log_path.exists():
        raise RuntimeError(f"Run log already exists; move or archive it before rerunning: {log_path}")
    for idx, row in enumerate(rows, start=1):
        log_row = run_one_row(config, row, algorithm_id)
        write_log_row(log_path, log_row)
        print(f"[{idx:03d}/{len(rows):03d}] {row.get('run_id')} {log_row['status']}")
    print("Complete. Review the run log before any aggregation.")


if __name__ == "__console__" or __name__ == "__main__":
    main()
