"""Human-controlled B8.5-F3b QGIS/SOLWEIG one-cell full-slice runner.

DO NOT RUN FULL 480.
DO NOT CHANGE SCIENTIFIC TARGET.
DO NOT COMMIT RASTERS.
ONE-CELL FULL SLICE ONLY.

Inputs:
    configs/v12/systemb_b85_f3b_onecell_fullslice.yaml
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_onecell_manifest.csv
    Existing local raster/SVF/met forcing assets declared by the config.

Outputs:
    C:/OpenHeat-local/solweig/b85_f3b_onecell/run_logs/b85_f3b_onecell_qgis_run_log.csv
    SOLWEIG outputs only under C:/OpenHeat-local/solweig/b85_f1_tiles/...

Saved metrics:
    One run-log row per run_id with status, timestamps, error_message,
    expected output paths, and notes.

Default behavior:
    DRY_RUN = True. The repo-tracked copy must stay dry-run only. To execute,
    a human must copy this script to C:/OpenHeat-local/solweig/b85_f3b_onecell,
    manually change DRY_RUN to False in that local-only copy, confirm the
    20-row manifest, and run inside QGIS Desktop with UMEP available.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = Path(
    "C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid"
)
PROJECT_ROOT = Path(os.environ.get("OPENHEAT_PROJECT_ROOT", DEFAULT_PROJECT_ROOT)).resolve()
GIT_WORKTREE_ROOT = PROJECT_ROOT.parent.resolve()
CONFIG_PATH = PROJECT_ROOT / "configs/v12/systemb_b85_f3b_onecell_fullslice.yaml"

# DO NOT RUN FULL 480.
# DO NOT CHANGE SCIENTIFIC TARGET.
# DO NOT COMMIT RASTERS.
# ONE-CELL FULL SLICE ONLY.
# Human review gate: the repo-tracked copy must remain True.
DRY_RUN = True


def now_iso() -> str:
    """Return a local ISO timestamp."""
    return datetime.now().isoformat(timespec="seconds")


def parse_inline_list(text: str) -> list[Any]:
    """Parse a small YAML inline list."""
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    return [parse_scalar(part.strip()) for part in inner.split(",")]


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by the F3b config."""
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
    """Read the simple nested YAML shape used by the F3b config."""
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
    """Load YAML config, preferring PyYAML when available in QGIS Python."""
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
    """Read CSV rows."""
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_log_row(log_path: Path, row: dict[str, str]) -> None:
    """Append one QGIS run-log row."""
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
        "expected_output_dir",
        "expected_tmrt_path",
        "expected_output_paths",
        "notes",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fieldnames})


def is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is below parent."""
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def onecell(config: dict[str, Any]) -> dict[str, Any]:
    """Return the one-cell full-slice config section."""
    return config["onecell_fullslice"]


def ensure_manual_execution_context(config: dict[str, Any]) -> None:
    """Require a local-only copied script before real SOLWEIG execution."""
    if DRY_RUN:
        return
    script_path = Path(__file__).resolve()
    local_copy_root = Path(str(onecell(config)["local_runner_copy_root"]))
    if is_relative_to(script_path, GIT_WORKTREE_ROOT):
        raise RuntimeError(
            "Refusing to execute from inside the Git worktree. Copy this script to "
            f"{local_copy_root.as_posix()} and change DRY_RUN=False only in that local-only copy."
        )
    if not is_relative_to(script_path, local_copy_root):
        raise RuntimeError(f"Refusing to execute outside approved local runner root: {local_copy_root}")


def ensure_output_root_allowed(config: dict[str, Any], output_dir: Path) -> None:
    """Prevent SOLWEIG raster writes outside the approved local-only root."""
    allowed_root = Path(str(onecell(config)["local_solweig_output_root"]))
    if not is_relative_to(output_dir, allowed_root):
        raise RuntimeError(f"Expected output dir is outside approved local output root: {output_dir}")
    if is_relative_to(output_dir, GIT_WORKTREE_ROOT):
        raise RuntimeError(f"Refusing to write SOLWEIG outputs inside the Git worktree: {output_dir}")


def assert_onecell_manifest(config: dict[str, Any], rows: list[dict[str, str]]) -> None:
    """Refuse anything other than the requested 20-row F3b slice."""
    section = onecell(config)
    expected_count = int(section["expected_run_count"])
    if len(rows) != expected_count:
        raise RuntimeError(f"DO NOT RUN FULL 480. Manifest has {len(rows)} rows, expected {expected_count}.")
    expected_days = set(section["forcing_days"])
    expected_hours = {str(int(hour)) for hour in section["hours_sgt"]}
    expected_scenarios = set(section["scenarios"])
    expected_cell = str(section["cell_id"])
    for row in rows:
        if row.get("cell_id") != expected_cell:
            raise RuntimeError(f"ONE-CELL FULL SLICE ONLY. Unexpected cell_id: {row.get('cell_id')}")
        if row.get("forcing_day_id") not in expected_days:
            raise RuntimeError(f"Unexpected forcing day in F3b manifest: {row.get('forcing_day_id')}")
        if str(int(row.get("hour_sgt", "-1"))) not in expected_hours:
            raise RuntimeError(f"Unexpected hour_sgt in F3b manifest: {row.get('hour_sgt')}")
        if row.get("scenario") not in expected_scenarios:
            raise RuntimeError(f"Unexpected scenario in F3b manifest: {row.get('scenario')}")
        ensure_output_root_allowed(config, Path(row["expected_output_dir"]))


def qgis_path(path: Path) -> str:
    """Return a QGIS-friendly path string."""
    return path.as_posix()


def scenario_svf_name(config: dict[str, Any], scenario: str) -> str:
    """Return the scenario-specific SVF zip relative path."""
    templates = config["asset_templates"]
    if scenario == "base":
        return str(templates["svf_base_zip"])
    if scenario == "overhead_as_canopy":
        return str(templates["svf_overhead_zip"])
    raise ValueError(f"Unknown scenario: {scenario}")


def scenario_cdsm_name(config: dict[str, Any], scenario: str) -> str:
    """Return the scenario-specific vegetation DSM filename."""
    templates = config["asset_templates"]
    if scenario == "base":
        return str(templates["vegetation_base_name"])
    if scenario == "overhead_as_canopy":
        return str(templates["vegetation_overhead_name"])
    raise ValueError(f"Unknown scenario: {scenario}")


def met_forcing_path(config: dict[str, Any], row: dict[str, str]) -> Path:
    """Return the configured met forcing path for one forcing day/hour."""
    templates = config["met_forcing_templates"]
    template = str(templates[row["forcing_day_id"]])
    return repo_path(template.format(hour=int(row["hour_sgt"])))


def expected_input_paths(config: dict[str, Any], row: dict[str, str]) -> dict[str, Path]:
    """Build expected local input paths without opening their contents."""
    templates = config["asset_templates"]
    cell_root = Path(str(templates["geometry_raster_svf_root"])) / row["cell_id"]
    return {
        "input_dsm": cell_root / str(templates["dsm_buildings_name"]),
        "input_svf": cell_root / scenario_svf_name(config, row["scenario"]),
        "input_height": cell_root / str(templates["wall_height_name"]),
        "input_aspect": cell_root / str(templates["wall_aspect_name"]),
        "input_cdsm": cell_root / scenario_cdsm_name(config, row["scenario"]),
        "input_dem": cell_root / str(templates["dem_name"]),
        "inputmet": met_forcing_path(config, row),
        "focus_cell": cell_root / str(templates["focus_geojson_name"]),
    }


def missing_required_inputs(config: dict[str, Any], row: dict[str, str]) -> list[str]:
    """Return missing expected local inputs for one run without opening them."""
    missing: list[str] = []
    for label, path in expected_input_paths(config, row).items():
        if not path.exists():
            missing.append(f"{label}: {path.as_posix()}")
    return missing


def build_solweig_parameters(config: dict[str, Any], row: dict[str, str], algorithm_id: str) -> dict[str, Any]:
    """Build a SOLWEIG parameter dict based on the B8.5-F1 skeleton contract."""
    paths = expected_input_paths(config, row)
    output_dir = Path(row["expected_output_dir"])
    ensure_output_root_allowed(config, output_dir)
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


def run_one_row(config: dict[str, Any], row: dict[str, str], algorithm_id: str) -> dict[str, str]:
    """Dry-run or manually execute one SOLWEIG row."""
    started = now_iso()
    status = "dry_run"
    error_message = ""
    notes = "DRY_RUN=True; SOLWEIG not executed."
    try:
        params = build_solweig_parameters(config, row, algorithm_id)
        if not DRY_RUN:
            ensure_manual_execution_context(config)
            missing = missing_required_inputs(config, row)
            if missing:
                raise FileNotFoundError("; ".join(missing))
            output_dir = Path(row["expected_output_dir"])
            output_dir.mkdir(parents=True, exist_ok=True)
            import processing  # type: ignore

            processing.run(algorithm_id, params)
            tmrt_path = Path(row["expected_tmrt_path"])
            status = "success" if tmrt_path.exists() and tmrt_path.stat().st_size > 0 else "failed"
            notes = "SOLWEIG execution attempted after human local-copy DRY_RUN=False change."
            if status == "failed":
                error_message = "SOLWEIG completed but expected Tmrt_average.tif is missing or zero size."
    except Exception as exc:
        status = "blocked" if not DRY_RUN else "dry_run"
        error_message = str(exc)
        notes = "Dry-run parameter build raised an error." if DRY_RUN else "Execution blocked or failed."
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
        "expected_output_dir": row.get("expected_output_dir", ""),
        "expected_tmrt_path": row.get("expected_tmrt_path", ""),
        "expected_output_paths": row.get("expected_output_paths", row.get("expected_tmrt_path", "")),
        "notes": notes,
    }


def main() -> None:
    """Iterate the 20-row F3b manifest and write a local-only run log."""
    config = read_config(CONFIG_PATH)
    manifest_path = repo_path(config["outputs"]["manifest"])
    log_path = Path(str(onecell(config)["local_run_log_path"]))
    algorithm_id = str(config["qgis_execution"]["qgis_algorithm_id_hint"])
    rows = read_csv_rows(manifest_path)
    assert_onecell_manifest(config, rows)
    if not DRY_RUN:
        ensure_manual_execution_context(config)
    print("B8.5-F3b QGIS/SOLWEIG one-cell full-slice runner")
    print("DO NOT RUN FULL 480.")
    print("DO NOT CHANGE SCIENTIFIC TARGET.")
    print("DO NOT COMMIT RASTERS.")
    print("ONE-CELL FULL SLICE ONLY.")
    print(f"DRY_RUN={DRY_RUN}")
    print(f"Rows: {len(rows)}")
    print(f"Run log: {log_path.as_posix()}")
    if log_path.exists():
        raise RuntimeError(f"Run log already exists; move or archive it before rerunning: {log_path}")
    for idx, row in enumerate(rows, start=1):
        log_row = run_one_row(config, row, algorithm_id)
        write_log_row(log_path, log_row)
        print(f"[{idx:02d}/{len(rows):02d}] {row.get('run_id')} {log_row['status']}")
    print("Complete. Run the F3b postrun validator before raster-content QA.")


if __name__ == "__console__" or __name__ == "__main__":
    main()
