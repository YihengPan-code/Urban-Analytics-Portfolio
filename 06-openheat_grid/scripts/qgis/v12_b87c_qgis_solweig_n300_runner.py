"""QGIS/UMEP B87C N300 SOLWEIG runner.

Run only inside QGIS Desktop Python Console with Processing and UMEP loaded.
Repo copy defaults to RUN_ENABLED=False and DRY_RUN=True.

Inputs:
  - b87c_manifest.csv
  - local-only assets under C:/OpenHeat-local/solweig/b87c_n300/assets
  - local forcing files under C:/OpenHeat-local/solweig/b87c_n300/forcing

Outputs, local-only:
  - C:/OpenHeat-local/solweig/b87c_n300/outputs/.../Tmrt_average.tif
  - C:/OpenHeat-local/solweig/b87c_n300/run_logs/b87c_qgis_solweig_run_log.csv

Saved metrics:
  Per-run status, elapsed seconds, input paths, output paths, resolved QGIS
  algorithm id, resume key, and error message.

This runner executes SOLWEIG Tmrt only. It does not create WBGT/risk/AOI/B9
outputs and does not write heavy assets into Git.
"""

from __future__ import annotations

import csv
import json
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path


RUN_ENABLED = False
DRY_RUN = True
LOCAL_CONTEXT = False
FORCE_PARTIAL = False
SKIP_COMPLETED = True
STAGE = "smoke"

REPO_ROOT = Path(r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid")
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs/v12/systemb_b87b4_b87c_materialization_package.yaml"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "outputs/v12_surrogate/b8_7b4_b87c_materialization_package/b87c_manifest.csv"


try:
    import processing  # type: ignore
    from qgis.core import QgsApplication  # type: ignore
    QGIS_READY = True
except Exception as exc:  # pragma: no cover - QGIS-only guard.
    QGIS_READY = False
    print("BLOCKED_QGIS_ENVIRONMENT_MISSING")
    print("Run this file inside QGIS Desktop Python Console, not normal Python.")
    print(exc)
    if RUN_ENABLED:
        raise SystemExit(2)

try:
    import rasterio  # type: ignore
    RASTERIO_READY = True
except Exception as exc:  # pragma: no cover - QGIS dependency guard.
    RASTERIO_READY = False
    print("BLOCKED_QGIS_PYTHON_DEPENDENCY_MISSING")
    print("QGIS Python needs rasterio for output validation.")
    print(exc)
    if RUN_ENABLED:
        raise SystemExit(2)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def qgis_path(value: str | Path) -> str:
    return Path(value).as_posix()


def algorithm_by_id(algorithm_id: str):
    registry = QgsApplication.processingRegistry()
    return registry.algorithmById(algorithm_id)


def assert_runner_context(cfg: dict, manifest_path: Path) -> None:
    local_root = Path(cfg["local_root"]).resolve()
    if not LOCAL_CONTEXT:
        raise RuntimeError("Refusing enabled run from repo copy. Use localized runner under C:/OpenHeat-local.")
    if not manifest_path.resolve().is_relative_to(local_root) and not manifest_path.resolve().is_relative_to(REPO_ROOT.resolve()):
        raise RuntimeError(f"Manifest must be under repo output or local root: {manifest_path}")


def assert_not_repo_heavy(path_text: str) -> None:
    path = Path(path_text).resolve()
    if path.is_relative_to(REPO_ROOT.resolve()):
        raise RuntimeError(f"Heavy input/output path points inside Git worktree: {path}")


def force_path(cfg: dict, row: dict[str, str]) -> Path:
    root = Path(cfg["local_forcing_root"])
    day = row["forcing_day_id"]
    hour = int(row["hour_sgt"])
    station = str(cfg.get("forcing_station_id", "S128"))
    return root / day / f"b87c_{day}_{station}_h{hour:02d}.txt"


def tmrt_output_exists(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with rasterio.open(path) as src:
            return src.count >= 1 and src.width > 0 and src.height > 0
    except Exception:
        return False


def selected_rows(cfg: dict, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    cells = []
    for row in rows:
        cell_id = row["cell_id"]
        if cell_id not in cells:
            cells.append(cell_id)
    stage_counts = {"smoke": 1, "pilot_5": 5, "pilot_20": 20, "full_150": int(cfg["expected_new_candidate_count"])}
    if STAGE not in stage_counts:
        raise RuntimeError(f"Unknown STAGE {STAGE!r}")
    selected = set(cells[: stage_counts[STAGE]])
    return [row for row in rows if row["cell_id"] in selected]


def validate_manifest(cfg: dict, rows: list[dict[str, str]]) -> None:
    if len(rows) > int(cfg["expected_total_runs"]):
        raise RuntimeError("Manifest has more rows than expected_total_runs.")
    all_rows = read_rows(DEFAULT_MANIFEST_PATH) if DEFAULT_MANIFEST_PATH.exists() else rows
    if len(all_rows) != int(cfg["expected_total_runs"]):
        raise RuntimeError(f"Full manifest row count mismatch: {len(all_rows)}")
    not_ready = [row for row in rows if row.get("run_status_initial") == "not_ready" or row.get("materialization_status") != "READY"]
    if not_ready and not FORCE_PARTIAL:
        raise RuntimeError(f"Selected rows include {len(not_ready)} not_ready runs. Run materialization/audit first.")
    for row in rows:
        for key in ["dsm_path", "cdsm_path", "dem_path", "svf_path_or_zip", "output_dir", "expected_tmrt_path"]:
            assert_not_repo_heavy(row[key])
        required = ["dsm_path", "cdsm_path", "dem_path", "svf_path_or_zip"]
        missing = [key for key in required if not Path(row[key]).exists()]
        if missing:
            raise RuntimeError(f"Missing assets for {row['run_id']}: {missing}")


def make_params(cfg: dict, row: dict[str, str]) -> dict:
    hour = int(row["hour_sgt"])
    output_dir = Path(row["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "INPUT_DSM": qgis_path(row["dsm_path"]),
        "INPUT_SVF": qgis_path(row["svf_path_or_zip"]),
        "INPUT_HEIGHT": qgis_path(Path(row["asset_folder"]) / "wall_height.tif"),
        "INPUT_ASPECT": qgis_path(Path(row["asset_folder"]) / "wall_aspect.tif"),
        "INPUT_CDSM": qgis_path(row["cdsm_path"]),
        "INPUT_TDSM": None,
        "INPUT_DEM": qgis_path(row["dem_path"]),
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
        "INPUTMET": qgis_path(force_path(cfg, row)),
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


def append_log(path: Path, row: dict) -> None:
    fields = [
        "attempt_id",
        "run_started_at",
        "run_id",
        "cell_id",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "resume_key",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fields})


def main() -> int:
    if not QGIS_READY or not RASTERIO_READY:
        print("BLOCKED_QGIS_OR_RASTERIO_RUNTIME")
        return 2
    cfg = read_config(DEFAULT_CONFIG_PATH)
    manifest_path = DEFAULT_MANIFEST_PATH
    rows = selected_rows(cfg, read_rows(manifest_path))
    if RUN_ENABLED:
        assert_runner_context(cfg, manifest_path)
    if not RUN_ENABLED:
        print("RUN_ENABLED is false; this is a dry safety pass.")
    if DRY_RUN:
        print("DRY_RUN is true; SOLWEIG will not be executed.")

    algorithm_id = str(cfg["qgis_solweig_algorithm_id"])
    if algorithm_by_id(algorithm_id) is None:
        raise RuntimeError(f"Missing SOLWEIG algorithm in QGIS Processing registry: {algorithm_id}")
    validate_manifest(cfg, rows)

    attempt_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_started = now_iso()
    log_path = Path(cfg["local_run_log_root"]) / "b87c_qgis_solweig_run_log.csv"
    counts: Counter[str] = Counter()

    for idx, row in enumerate(rows, start=1):
        started = now_iso()
        t0 = time.time()
        params = make_params(cfg, row)
        tmrt_path = Path(row["expected_tmrt_path"])
        status = "dry_run" if DRY_RUN or not RUN_ENABLED else "failed_solweig"
        error = ""
        print(f"[{idx}/{len(rows)}] {row['run_id']}")
        try:
            if SKIP_COMPLETED and tmrt_output_exists(tmrt_path):
                status = "skipped_completed"
            elif RUN_ENABLED and not DRY_RUN:
                if not force_path(cfg, row).exists():
                    raise FileNotFoundError(f"Missing local forcing file: {force_path(cfg, row)}")
                processing.run(algorithm_id, params)
                status = "success" if tmrt_output_exists(tmrt_path) else "failed_solweig"
                if status == "failed_solweig":
                    error = "SOLWEIG completed but readable Tmrt output was not found."
        except Exception as exc:
            status = "failed_solweig"
            error = f"{exc}\n{traceback.format_exc()}"[:5000]
        finally:
            counts[status] += 1
            append_log(
                log_path,
                {
                    "attempt_id": attempt_id,
                    "run_started_at": run_started,
                    "run_id": row["run_id"],
                    "cell_id": row["cell_id"],
                    "forcing_day_id": row["forcing_day_id"],
                    "date": row["date"],
                    "hour_sgt": row["hour_sgt"],
                    "scenario": row["scenario"],
                    "resume_key": row["resume_key"],
                    "status": status,
                    "started_at": started,
                    "completed_at": now_iso(),
                    "elapsed_seconds": round(time.time() - t0, 3),
                    "qgis_algorithm_id": algorithm_id,
                    "input_dsm": params["INPUT_DSM"],
                    "input_svf": params["INPUT_SVF"],
                    "input_vegetation": params["INPUT_CDSM"],
                    "input_dem": params["INPUT_DEM"],
                    "inputmet": params["INPUTMET"],
                    "output_dir": params["OUTPUT_DIR"],
                    "tmrt_output_path": qgis_path(tmrt_path),
                    "error_message": error.replace("\r", " ").replace("\n", " | "),
                },
            )
    print("SUMMARY " + " ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    print(f"Run log: {log_path}")
    return 0


if __name__ == "__console__" or __name__ == "__main__":
    raise SystemExit(main())
