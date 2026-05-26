"""Sprint B7 N150 new-run-only SOLWEIG runner for QGIS Desktop Python Console.

Run only inside QGIS Desktop Python Console with Processing and UMEP loaded.
Do not run this script from conda Python, PowerShell QGIS imports, or qgis_process.

Inputs:
  - configs/v12/v12_solweig_n150_execution_config.example.json
  - configs/v12/v12_solweig_n150_new_run_matrix.csv
  - outputs/v12_systemb_n150_sample_design/n150_selected_cells.csv
  - static DSM/vector/forcing inputs declared in the config.

Outputs:
  - local-only raw artifacts under data/solweig/v12_n150_tiles/
  - outputs/v12_solweig_n150_execution/n150_new_solweig_run_log.csv
  - outputs/v12_solweig_n150_execution/qgis_algorithm_resolution.md
  - outputs/v12_solweig_n150_execution/qgis_preprocess_algorithm_resolution.md
  - outputs/v12_solweig_n150_execution/n150_effective_solweig_parameters.json
  - outputs/v12_solweig_n150_execution/n150_effective_solweig_parameters.md

Saved metrics:
  - per-run attempt_id, status, elapsed seconds, resolved algorithm id, key
    inputs/outputs, Tmrt output path, and error message.

Scope:
  System B SOLWEIG-derived Tmrt execution only. This does not compute local WBGT,
  hazard_score, risk_score, surrogate models, final maps, or System A/B coupling.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid")
CONFIG_PATH = PROJECT_ROOT / "configs/v12/v12_solweig_n150_execution_config.example.json"
B3_HELPER_PATH = PROJECT_ROOT / "scripts/qgis/v12_b3_n24_run_solweig_from_manifest.py"
EXPECTED_RETAINED_N24 = 24
EXPECTED_NEW_RUNS = 1260


def load_b3_helpers():
    spec = importlib.util.spec_from_file_location("openheat_b3_qgis_helpers", B3_HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load B3 helper module: {B3_HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    b3 = load_b3_helpers()
except SystemExit:
    raise
except Exception as exc:  # pragma: no cover - QGIS-only environment guard.
    print("BLOCKED_QGIS_ENVIRONMENT_MISSING")
    print("This script must be run inside QGIS Desktop Python Console.")
    print(exc)
    raise SystemExit(2)


pd = b3.pd
gpd = b3.gpd
processing = b3.processing


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def qgis_path(value: str | Path) -> str:
    return repo_path(value).as_posix()


def normalize_run_matrix(df):
    out = df.copy()
    if "hour_sgt" not in out.columns and "hour" in out.columns:
        out["hour_sgt"] = out["hour"]
    out["cell_id"] = out["cell_id"].astype(str)
    out["scenario"] = out["scenario"].astype(str)
    out["hour_sgt"] = out["hour_sgt"].astype(int)
    return out


def selected_retained_cells(cfg: dict) -> set[str]:
    selected = pd.read_csv(repo_path(cfg["selected_cells_path"]))
    selected["cell_id"] = selected["cell_id"].astype(str)
    if "selection_status" not in selected.columns:
        return set()
    return set(selected.loc[selected["selection_status"].eq("retained_n24"), "cell_id"].astype(str))


def validate_new_run_only_matrix(cfg: dict, run_matrix) -> list[str]:
    retained = selected_retained_cells(cfg)
    problems: list[str] = []
    if len(retained) != EXPECTED_RETAINED_N24:
        problems.append(f"selected-cell file has {len(retained)} retained_n24 cells; expected {EXPECTED_RETAINED_N24}")
    if len(run_matrix) != int(cfg.get("expected_new_runs", EXPECTED_NEW_RUNS)):
        problems.append(f"new-run-only matrix has {len(run_matrix)} rows; expected {cfg.get('expected_new_runs', EXPECTED_NEW_RUNS)}")
    bad_retained = sorted(set(run_matrix["cell_id"]) & retained)
    if bad_retained:
        problems.append("new-run-only matrix contains retained N24 cells: " + ",".join(bad_retained[:20]))
    bad_reuse = sorted(run_matrix.loc[run_matrix.get("reuse_existing_n24_label", False).astype(str).str.lower().eq("true"), "cell_id"].astype(str).unique()) if "reuse_existing_n24_label" in run_matrix.columns else []
    if bad_reuse:
        problems.append("new-run-only matrix contains reuse_existing_n24_label=True rows: " + ",".join(bad_reuse[:20]))
    return problems


def scenario_vegetation_path(paths: dict[str, str], scenario: str) -> Path:
    if scenario == "base":
        return Path(paths["input_vegetation_base"])
    if scenario == "overhead_as_canopy":
        return Path(paths["input_vegetation_overhead_as_canopy"])
    raise ValueError(f"Unknown scenario: {scenario}")


def svf_zip(paths: dict[str, str], scenario: str) -> Path:
    return Path(paths[f"svf_{scenario}"]) / "svfs.zip"


def make_params(cfg: dict, algorithm_id: str, row: dict, paths: dict[str, str]) -> dict:
    scenario = str(row["scenario"])
    hour = int(row["hour_sgt"])
    output_dir = repo_path(cfg["raw_output_root"]) / str(row["cell_id"]) / f"solweig_{scenario}" / f"solweig_outputs_h{hour:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "INPUT_DSM": qgis_path(paths["input_dsm"]),
        "INPUT_SVF": qgis_path(svf_zip(paths, scenario)),
        "INPUT_HEIGHT": qgis_path(paths["wall_height"]),
        "INPUT_ASPECT": qgis_path(paths["wall_aspect"]),
        "INPUT_CDSM": qgis_path(scenario_vegetation_path(paths, scenario)),
        "INPUT_TDSM": None,
        "INPUT_DEM": qgis_path(paths["input_dem"]),
        "INPUT_LC": None,
        "INPUT_ANISO": "",
        "INPUT_WALLSCHEME": "",
        "TRANS_VEG": 3,
        "INPUT_THEIGHT": 25.0,
        "LEAF_START": 1,
        "LEAF_END": 366,
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
        "INPUTMET": qgis_path(repo_path(cfg["forcing_paths_by_hour"][str(hour)])),
        "ONLYGLOBAL": False,
        "UTC": 8,
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
        "OUTPUT_TMRT": True,
        "OUTPUT_KDOWN": False,
        "OUTPUT_KUP": False,
        "OUTPUT_LDOWN": False,
        "OUTPUT_LUP": False,
        "OUTPUT_SH": False,
        "OUTPUT_TREEPLANTER": False,
        "OUTPUT_DIR": qgis_path(output_dir),
    }


def write_effective_parameters(out_dir: Path, algorithm_id: str) -> None:
    params = {
        "qgis_algorithm_id": algorithm_id,
        "execution_scope": "B7 N150 new-run-only matrix; retained N24 cells are not rerun",
        "scenario_design": "paired base vs overhead_as_canopy comparison; not absolute truth",
        "primary_target": "tmrt_p90_c",
        "primary_modifier_delta": "delta_tmrt_p90_c",
        "normalized_modifier": "m_rad_pct01",
        "reference_domain_version": "n150_training_future",
        "INPUTMET_key": "INPUTMET",
        "LEAF_START": 1,
        "LEAF_END": 366,
        "UTC": 8,
        "TRANS_VEG": 3,
        "INPUT_THEIGHT": 25.0,
        "OUTPUT_TMRT": True,
        "tmrt_output_filename_note": "SOLWEIG may write Tmrt_average.tif; hour is parsed from the parent folder solweig_outputs_hHH.",
    }
    write_json(out_dir / "n150_effective_solweig_parameters.json", params)
    lines = ["# N150 Effective SOLWEIG Parameters", ""]
    for key, value in params.items():
        lines.append(f"- `{key}`: `{value}`")
    (out_dir / "n150_effective_solweig_parameters.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def archive_existing_log(log_path: Path, attempt_id: str) -> Path | None:
    if not log_path.exists():
        return None
    archive_dir = log_path.parent / "archived_run_logs"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{log_path.stem}_{attempt_id}_previous.csv"
    idx = 1
    while archive_path.exists():
        archive_path = archive_dir / f"{log_path.stem}_{attempt_id}_previous_{idx}.csv"
        idx += 1
    log_path.replace(archive_path)
    return archive_path


def append_log(log_path: Path, row: dict) -> None:
    fieldnames = [
        "attempt_id",
        "run_started_at",
        "run_id",
        "cell_id",
        "scenario",
        "hour_sgt",
        "status",
        "started_at",
        "completed_at",
        "elapsed_seconds",
        "qgis_algorithm_id",
        "input_dsm",
        "input_svf",
        "input_vegetation",
        "input_dem",
        "inputmet",
        "output_dir",
        "tmrt_output_path",
        "error_message",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fieldnames})


def write_blocked_log(log_path: Path, run_matrix, attempt_id: str, run_started_at: str, status: str, message: str) -> None:
    for _, rr in run_matrix.iterrows():
        append_log(
            log_path,
            {
                "attempt_id": attempt_id,
                "run_started_at": run_started_at,
                "run_id": rr.get("run_id", ""),
                "cell_id": rr.get("cell_id", ""),
                "scenario": rr.get("scenario", ""),
                "hour_sgt": rr.get("hour_sgt", ""),
                "status": status,
                "started_at": now_iso(),
                "completed_at": now_iso(),
                "elapsed_seconds": 0,
                "qgis_algorithm_id": "",
                "error_message": message,
            },
        )


def normalize_error(message: str) -> str:
    text = " ".join(str(message).replace("\\", "/").split())
    return text[:220]


def write_runtime_stop_report(out_dir: Path, attempt_id: str, reason: str, counts: Counter) -> None:
    lines = [
        "# Sprint B7 Runtime Stop Report",
        "",
        f"- attempt_id: `{attempt_id}`",
        f"- reason: `{reason}`",
        "",
        "## First-10 failure signatures",
        "",
    ]
    if counts:
        for key, count in counts.most_common():
            lines.append(f"- `{count}` x {key}")
    else:
        lines.append("_No failure signatures recorded._")
    (out_dir / "n150_runtime_stop_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(total: int, counts: Counter) -> None:
    success = int(counts.get("success", 0))
    skipped = int(counts.get("skipped_completed", 0))
    failed_preprocess = int(counts.get("failed_preprocess", 0))
    failed_solweig = int(counts.get("failed_solweig", 0))
    blocked = int(counts.get("blocked_environment", 0)) + int(counts.get("blocked_algorithm_missing", 0))
    attempted = success + failed_preprocess + failed_solweig
    print("=" * 72)
    print(
        "SUMMARY "
        f"expected={total} "
        f"attempted={attempted} "
        f"success={success} "
        f"skipped_completed={skipped} "
        f"failed_preprocess={failed_preprocess} "
        f"failed_solweig={failed_solweig} "
        f"blocked={blocked}"
    )
    print("=" * 72)


def main() -> None:
    cfg = read_json(CONFIG_PATH)
    out_dir = repo_path(cfg["summary_output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    run_matrix = normalize_run_matrix(pd.read_csv(repo_path(cfg["run_matrix_path"])))
    log_path = out_dir / "n150_new_solweig_run_log.csv"
    attempt_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_started_at = now_iso()
    archived_log = archive_existing_log(log_path, attempt_id)

    print("=" * 72)
    print("Sprint B7 N150 new-run-only SOLWEIG QGIS Console runner")
    print(f"attempt_id: {attempt_id}")
    print(f"expected new-run-only main runs: {len(run_matrix)}")
    if archived_log:
        print(f"archived previous run log: {archived_log}")
    print("=" * 72)

    matrix_problems = validate_new_run_only_matrix(cfg, run_matrix)
    if matrix_problems:
        message = "BLOCKED_ENVIRONMENT: " + " | ".join(matrix_problems)
        print(message)
        write_blocked_log(log_path, run_matrix, attempt_id, run_started_at, "blocked_environment", message)
        print_summary(len(run_matrix), Counter({"blocked_environment": len(run_matrix)}))
        return

    algorithm_id = b3.resolve_solweig_algorithm(out_dir)
    wall_alg, svf_alg = b3.resolve_preprocess_algorithms(cfg, out_dir)
    print(f"SOLWEIG algorithm: {algorithm_id}")
    print(f"Wall algorithm: {wall_alg}")
    print(f"SVF algorithm: {svf_alg}")

    if not algorithm_id:
        message = "SOLWEIG algorithm missing from QGIS Processing registry."
        print("BLOCKED_ALGORITHM_MISSING:", message)
        write_blocked_log(log_path, run_matrix, attempt_id, run_started_at, "blocked_algorithm_missing", message)
        print_summary(len(run_matrix), Counter({"blocked_algorithm_missing": len(run_matrix)}))
        return
    if not wall_alg or not svf_alg:
        message = "Required UMEP preprocessing algorithm missing from QGIS Processing registry."
        print("BLOCKED_ALGORITHM_MISSING:", message)
        write_blocked_log(log_path, run_matrix, attempt_id, run_started_at, "blocked_algorithm_missing", message)
        print_summary(len(run_matrix), Counter({"blocked_algorithm_missing": len(run_matrix)}))
        return

    write_effective_parameters(out_dir, algorithm_id)

    grid = pd.read_csv(repo_path(cfg["grid_feature_path"]))
    grid["cell_id"] = grid["cell_id"].astype(str)
    overhead_path = repo_path(cfg["overhead_vector_path"])
    overhead = gpd.read_file(overhead_path).to_crs(cfg.get("crs", "EPSG:3414")) if overhead_path.exists() else None

    first_10_non_skipped = 0
    first_10_failures: Counter = Counter()
    stop_limit = int(cfg.get("stop_if_first_10_failure_count_gt", 5))
    cached_tiles: dict[str, dict[str, str]] = {}
    total = len(run_matrix)
    status_counts: Counter = Counter()

    for idx, (_, rr) in enumerate(run_matrix.iterrows(), start=1):
        row = rr.to_dict()
        started = now_iso()
        t0 = time.time()
        cell_id = str(row["cell_id"])
        scenario = str(row["scenario"])
        hour = int(row["hour_sgt"])
        status = "failed_preprocess"
        error_message = ""
        params: dict = {}
        phase = "preprocess"
        print(f"\n[{idx:03d}/{total}] {row.get('run_id')} {cell_id} {scenario} h{hour:02d}")
        try:
            if cell_id not in cached_tiles:
                g = grid[grid["cell_id"].eq(cell_id)]
                if g.empty:
                    raise RuntimeError(f"selected new cell not found in grid feature file: {cell_id}")
                cached_tiles[cell_id] = b3.prepare_tile(cfg, g.iloc[0], overhead)
            paths = cached_tiles[cell_id]
            params = make_params(cfg, algorithm_id, row, paths)
            tmrt_path = b3.find_tmrt_output(Path(params["OUTPUT_DIR"]))
            if cfg.get("skip_completed", True) and b3.tmrt_output_exists(tmrt_path):
                status = "skipped_completed"
            else:
                preprocess_message = b3.run_preprocess(paths, scenario, cfg, wall_alg, svf_alg)
                missing = b3.validate_pre_solweig_inputs(params)
                if missing:
                    raise FileNotFoundError("; ".join(missing))
                print(f"  [PREPROCESS OK] {preprocess_message}")
                phase = "solweig"
                processing.run(algorithm_id, params)
                phase = "post_solweig"
                tmrt_path = b3.find_tmrt_output(Path(params["OUTPUT_DIR"]))
                status = "success" if b3.tmrt_output_exists(tmrt_path) else "failed_solweig"
                if status == "failed_solweig":
                    error_message = "SOLWEIG completed but readable Tmrt output was not found."
        except Exception as exc:
            status = "failed_solweig" if phase == "solweig" else "failed_preprocess"
            error_message = f"{exc}\n{traceback.format_exc()}"[:5000]
        finally:
            completed = now_iso()
            elapsed = round(time.time() - t0, 3)
            fallback_dir = repo_path(cfg["raw_output_root"]) / cell_id / f"solweig_{scenario}" / f"solweig_outputs_h{hour:02d}"
            tmrt_path = b3.find_tmrt_output(Path(params.get("OUTPUT_DIR", fallback_dir)))
            append_log(
                log_path,
                {
                    "attempt_id": attempt_id,
                    "run_started_at": run_started_at,
                    "run_id": row.get("run_id", ""),
                    "cell_id": cell_id,
                    "scenario": scenario,
                    "hour_sgt": hour,
                    "status": status,
                    "started_at": started,
                    "completed_at": completed,
                    "elapsed_seconds": elapsed,
                    "qgis_algorithm_id": algorithm_id,
                    "input_dsm": params.get("INPUT_DSM", ""),
                    "input_svf": params.get("INPUT_SVF", ""),
                    "input_vegetation": params.get("INPUT_CDSM", ""),
                    "input_dem": params.get("INPUT_DEM", ""),
                    "inputmet": params.get("INPUTMET", ""),
                    "output_dir": params.get("OUTPUT_DIR", ""),
                    "tmrt_output_path": str(tmrt_path),
                    "error_message": error_message.replace("\r", " ").replace("\n", " | "),
                },
            )
            print(f"{row.get('run_id')} {status}")
            status_counts[status] += 1

            if status != "skipped_completed" and first_10_non_skipped < 10:
                first_10_non_skipped += 1
                if status in {"failed_preprocess", "failed_solweig"}:
                    signature = f"{status}: {normalize_error(error_message)}"
                    first_10_failures[signature] += 1
                    if first_10_failures[signature] > stop_limit:
                        reason = f"CATASTROPHIC_STOP: more than {stop_limit} of first 10 non-skipped runs failed with the same signature."
                        print(reason)
                        write_runtime_stop_report(out_dir, attempt_id, reason, first_10_failures)
                        break

    print_summary(total, status_counts)


if __name__ == "__console__" or __name__ == "__main__":
    main()
