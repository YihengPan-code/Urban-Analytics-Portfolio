"""QGIS/UMEP local missing-only materialization runner for B8.7b.4/B87C.

Run inside QGIS Desktop Python Console with Processing and UMEP loaded for
enabled writes. The repo copy defaults to RUN_ENABLED=False and DRY_RUN=True.

Inputs:
  - configs/v12/systemb_b87b4_b87c_materialization_package.yaml
  - B87B candidate/source-lock CSVs named in config
  - locked DSM/CDSM/grid/overhead sources

Outputs, local-only:
  - C:/OpenHeat-local/solweig/b87c_n300/assets/<cell_id>/focus_cell.geojson
  - dsm_buildings_tile.tif, dsm_vegetation_tile_base.tif,
    dsm_overhead_canopy_tile.tif, dsm_vegetation_tile_overhead_as_canopy.tif,
    dsm_dem_flat_tile.tif
  - wall_height.tif, wall_aspect.tif
  - svf_base/svfs.zip and svf_overhead_as_canopy/svfs.zip
  - compact progress/log CSVs under C:/OpenHeat-local/solweig/b87c_n300/run_logs

Saved metrics:
  Per-cell shared/wall/base-SVF/overhead-SVF readiness, skipped existing files,
  newly created files, failures, elapsed seconds, and error messages.

This runner does not run SOLWEIG and never writes raster/SVF assets into the
Git worktree. Shared DSM/DEM/CDSM/wall assets are materialized once per cell.
Base and overhead_as_canopy SVF are generated separately and never reused across
scenarios.
"""

from __future__ import annotations

import csv
import json
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


RUN_ENABLED = False
DRY_RUN = True
LOCAL_CONTEXT = False
FORCE_PARTIAL = False
STAGE = "remaining"

REPO_ROOT = Path(r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid")
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs/v12/systemb_b87b4_b87c_materialization_package.yaml"
CLAIM_BOUNDARY = (
    "B8.7b.4/B87C local-only missing-only materialization; no repo raster "
    "writes; no AOI/B9; no WBGT/risk/hazard/exposure/vulnerability outputs."
)


try:
    import processing  # type: ignore
    from qgis.core import QgsApplication  # type: ignore

    QGIS_READY = True
except Exception as exc:  # pragma: no cover - QGIS-only guard.
    QGIS_READY = False
    print("BLOCKED_QGIS_ENVIRONMENT_MISSING")
    print("Run enabled writes inside QGIS Desktop Python Console with UMEP loaded.")
    print(exc)

try:
    import geopandas as gpd  # type: ignore
    import numpy as np  # type: ignore
    import rasterio  # type: ignore
    from rasterio.enums import Resampling  # type: ignore
    from rasterio.features import rasterize  # type: ignore
    from rasterio.transform import from_origin  # type: ignore
    from rasterio.warp import reproject  # type: ignore

    GEOSPATIAL_READY = True
except Exception as exc:  # pragma: no cover - QGIS dependency guard.
    GEOSPATIAL_READY = False
    print("BLOCKED_QGIS_PYTHON_DEPENDENCY_MISSING")
    print("Enabled materialization needs geopandas, numpy, and rasterio in QGIS Python.")
    print(exc)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def repo_path(cfg: dict[str, Any], value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def append_log(path: Path, row: dict[str, Any]) -> None:
    fields = [
        "attempt_id",
        "cell_id",
        "scenario",
        "status",
        "started_at",
        "completed_at",
        "elapsed_seconds",
        "dsm_path",
        "cdsm_path",
        "dem_path",
        "svf_path_or_zip",
        "wall_height_path",
        "wall_aspect_path",
        "message",
        "error_message",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fields})


def qgis_path(value: str | Path) -> str:
    return Path(value).as_posix()


def file_ready(path: Path) -> bool:
    try:
        return path.exists() and path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def file_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    if file_ready(path):
        return "ready"
    return "needs_review"


def runtime_switches(cfg: dict[str, Any]) -> tuple[bool, bool]:
    cfg_run_enabled = bool(cfg.get("run_enabled", False))
    cfg_dry_run = bool(cfg.get("dry_run", True))
    enabled = RUN_ENABLED and cfg_run_enabled
    dry_run = DRY_RUN or cfg_dry_run or not enabled
    return enabled, dry_run


def overwrite_existing(cfg: dict[str, Any], key: str | None = None) -> bool:
    pre = cfg.get("qgis_preprocess", {})
    specific = bool(pre.get(key, False)) if key else False
    return bool(cfg.get("overwrite_existing_assets", False)) or specific


def selected_scenarios(cfg: dict[str, Any]) -> list[str]:
    scenarios = cfg.get("scenarios") or cfg.get("expected_scenarios") or ["base", "overhead_as_canopy"]
    allowed = {"base", "overhead_as_canopy"}
    out = [str(scenario) for scenario in scenarios if str(scenario) in allowed]
    return out or ["base", "overhead_as_canopy"]


def algorithm_by_id(algorithm_id: str):
    registry = QgsApplication.processingRegistry()
    return registry.algorithmById(algorithm_id)


def ensure_algorithms(cfg: dict[str, Any]) -> tuple[str, str]:
    wall = str(cfg["qgis_wall_algorithm_id"])
    svf = str(cfg["qgis_svf_algorithm_id"])
    missing = [alg for alg in [wall, svf] if algorithm_by_id(alg) is None]
    if missing:
        raise RuntimeError("Missing QGIS/UMEP algorithms: " + ", ".join(missing))
    return wall, svf


def assert_local_path(cfg: dict[str, Any], path: Path) -> None:
    root = Path(cfg["local_root"]).resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise RuntimeError(f"Refusing to write outside approved local root: {path}")
    if resolved.is_relative_to(REPO_ROOT.resolve()):
        raise RuntimeError(f"Refusing to write materialized asset inside Git worktree: {path}")


def assert_runner_context(enabled: bool) -> None:
    if enabled and not LOCAL_CONTEXT:
        raise RuntimeError("Refusing enabled run from repo copy. Use the localized runner under C:/OpenHeat-local.")


def source_path_map(cfg: dict[str, Any]) -> dict[str, str]:
    rows = read_rows(repo_path(cfg, cfg["b87b3_source_lock_path"]))
    out = {row["source_kind"]: row.get("canonical_path", "") for row in rows if row.get("canonical_path")}
    overhead = read_rows(repo_path(cfg, cfg["b87b3_overhead_source_path"]))
    for row in overhead:
        if row.get("overhead_source_path"):
            out["overhead_vector"] = row["overhead_source_path"]
            break
    return out


def candidates(cfg: dict[str, Any]) -> list[str]:
    rows = read_rows(repo_path(cfg, cfg["b87b_new_candidate_sample_index_path"]))
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        cell_id = str(row.get("cell_id", "")).strip()
        if cell_id and cell_id not in seen:
            seen.add(cell_id)
            out.append(cell_id)
    return out


def asset_paths(cfg: dict[str, Any], cell_id: str) -> dict[str, Path]:
    root = Path(cfg["local_asset_root"]) / cell_id
    return {
        "asset_folder": root,
        "focus": root / "focus_cell.geojson",
        "tile": root / "tile_boundary_buffered.geojson",
        "dsm": root / "dsm_buildings_tile.tif",
        "dem": root / "dsm_dem_flat_tile.tif",
        "cdsm_base": root / "dsm_vegetation_tile_base.tif",
        "overhead_canopy": root / "dsm_overhead_canopy_tile.tif",
        "cdsm_overhead": root / "dsm_vegetation_tile_overhead_as_canopy.tif",
        "wall_height": root / "wall_height.tif",
        "wall_aspect": root / "wall_aspect.tif",
        "svf_base": root / "svf_base",
        "svf_base_zip": root / "svf_base" / "svfs.zip",
        "svf_overhead": root / "svf_overhead_as_canopy",
        "svf_overhead_zip": root / "svf_overhead_as_canopy" / "svfs.zip",
    }


def scenario_cdsm(paths: dict[str, Path], scenario: str) -> Path:
    return paths["cdsm_base"] if scenario == "base" else paths["cdsm_overhead"]


def scenario_svf_dir(paths: dict[str, Path], scenario: str) -> Path:
    return paths["svf_base"] if scenario == "base" else paths["svf_overhead"]


def scenario_svf_zip(paths: dict[str, Path], scenario: str) -> Path:
    return paths["svf_base_zip"] if scenario == "base" else paths["svf_overhead_zip"]


def shared_asset_files(paths: dict[str, Path]) -> list[Path]:
    return [
        paths["focus"],
        paths["dsm"],
        paths["dem"],
        paths["cdsm_base"],
        paths["overhead_canopy"],
        paths["cdsm_overhead"],
    ]


def wall_files(paths: dict[str, Path]) -> list[Path]:
    return [paths["wall_height"], paths["wall_aspect"]]


def all_required_files(paths: dict[str, Path]) -> list[Path]:
    return shared_asset_files(paths) + wall_files(paths) + [paths["svf_base_zip"], paths["svf_overhead_zip"]]


def group_status(files: list[Path]) -> str:
    states = [file_state(path) for path in files]
    if all(state == "ready" for state in states):
        return "ready"
    if any(state == "needs_review" for state in states):
        return "needs_review"
    return "missing"


def cell_all_ready(cfg: dict[str, Any], cell_id: str) -> bool:
    paths = asset_paths(cfg, cell_id)
    return all(file_ready(path) for path in all_required_files(paths))


def stage_cells(cfg: dict[str, Any]) -> list[str]:
    all_cells = candidates(cfg)
    subset = [str(cell_id) for cell_id in cfg.get("cell_id_subset", []) if str(cell_id)]
    if subset:
        wanted = set(subset)
        all_cells = [cell_id for cell_id in all_cells if cell_id in wanted]
    stage_counts = {
        "smoke": 1,
        "pilot_5": 5,
        "pilot_20": 20,
        "full_150": int(cfg["expected_new_candidate_count"]),
    }
    if STAGE == "remaining":
        selected = [cell_id for cell_id in all_cells if not cell_all_ready(cfg, cell_id)]
    elif STAGE == "all":
        selected = all_cells
    elif STAGE in stage_counts:
        selected = all_cells[: stage_counts[STAGE]]
    else:
        raise RuntimeError(f"Unknown STAGE {STAGE!r}")
    max_cells = cfg.get("max_cells")
    if max_cells is not None:
        selected = selected[: int(max_cells)]
    return selected


def write_raster(path: Path, arr: Any, transform: Any, crs: str) -> None:
    profile = {
        "driver": "GTiff",
        "height": arr.shape[0],
        "width": arr.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        "nodata": -9999.0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype("float32"), 1)


def raster_to_bounds(src_path: Path, bounds: tuple[float, float, float, float], res: float, crs: str) -> tuple[Any, Any]:
    minx, miny, maxx, maxy = bounds
    width = int(np.ceil((maxx - minx) / res))
    height = int(np.ceil((maxy - miny) / res))
    transform = from_origin(minx, maxy, res, res)
    dst = np.zeros((height, width), dtype="float32")
    with rasterio.open(src_path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=crs,
            resampling=Resampling.nearest,
            dst_nodata=0.0,
        )
    dst[~np.isfinite(dst)] = 0.0
    return dst, transform


def infer_overhead_height(row: Any) -> float:
    defaults = {
        "covered_walkway": 3.0,
        "pedestrian_bridge": 5.0,
        "elevated_rail": 8.0,
        "elevated_road": 8.0,
        "viaduct": 8.0,
        "unknown_overhead": 5.0,
    }
    for col in ["height_m", "manual_height_m", "height"]:
        if col in row and row[col] is not None:
            try:
                value = float(row[col])
                if value > 0:
                    return value
            except Exception:
                pass
    return float(defaults.get(str(row.get("overhead_type", "unknown_overhead")).lower(), 5.0))


def target_names(paths: dict[str, Path], targets: dict[str, Path]) -> list[str]:
    del paths
    return [name for name, path in targets.items() if file_state(path) == "missing"]


def materialize_shared_assets_once(
    cfg: dict[str, Any],
    cell_id: str,
    grid: Any,
    overhead: Any,
    dry_run: bool,
) -> dict[str, Any]:
    paths = asset_paths(cfg, cell_id)
    for path in [paths["asset_folder"], paths["svf_base"], paths["svf_overhead"]]:
        assert_local_path(cfg, path)
    targets = {
        "focus_cell.geojson": paths["focus"],
        "tile_boundary_buffered.geojson": paths["tile"],
        "dsm_buildings_tile.tif": paths["dsm"],
        "dsm_dem_flat_tile.tif": paths["dem"],
        "dsm_vegetation_tile_base.tif": paths["cdsm_base"],
        "dsm_overhead_canopy_tile.tif": paths["overhead_canopy"],
        "dsm_vegetation_tile_overhead_as_canopy.tif": paths["cdsm_overhead"],
    }
    overwrite = overwrite_existing(cfg)
    states = {name: file_state(path) for name, path in targets.items()}
    skipped = sum(1 for state in states.values() if state == "ready" and not overwrite)
    if any(state == "needs_review" for state in states.values()) and not overwrite:
        review = [name for name, state in states.items() if state == "needs_review"]
        return {
            "asset_group": "shared_assets",
            "scenario": "all",
            "status": "needs_review",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": len(review),
            "message": "needs_review: " + ",".join(review),
            "error_message": "",
        }
    create_names = [name for name, state in states.items() if overwrite or state == "missing"]
    if not create_names:
        return {
            "asset_group": "shared_assets",
            "scenario": "all",
            "status": "already_exists",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 0,
            "message": "shared assets already exist",
            "error_message": "",
        }
    if dry_run:
        return {
            "asset_group": "shared_assets",
            "scenario": "all",
            "status": "dry_run",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 0,
            "message": "would create missing shared assets: " + ",".join(create_names),
            "error_message": "",
        }

    paths["asset_folder"].mkdir(parents=True, exist_ok=True)
    paths["svf_base"].mkdir(parents=True, exist_ok=True)
    paths["svf_overhead"].mkdir(parents=True, exist_ok=True)
    source = source_path_map(cfg)
    crs = str(cfg.get("working_crs", "EPSG:3414"))
    res = float(cfg["raster_resolution_m"])
    focus = grid[grid["cell_id"].astype(str).eq(cell_id)].copy()
    if focus.empty:
        raise RuntimeError(f"Missing cell in locked grid: {cell_id}")
    tile_geom = focus.geometry.iloc[0].buffer(float(cfg["tile_buffer_m"]))

    created = 0
    if overwrite or file_state(paths["focus"]) == "missing":
        focus.to_file(paths["focus"], driver="GeoJSON")
        created += int(file_ready(paths["focus"]))
    if overwrite or file_state(paths["tile"]) == "missing":
        gpd.GeoDataFrame({"cell_id": [cell_id]}, geometry=[tile_geom], crs=crs).to_file(paths["tile"], driver="GeoJSON")
        created += int(file_ready(paths["tile"]))

    raster_targets = {
        "dsm_buildings_tile.tif": paths["dsm"],
        "dsm_dem_flat_tile.tif": paths["dem"],
        "dsm_vegetation_tile_base.tif": paths["cdsm_base"],
        "dsm_overhead_canopy_tile.tif": paths["overhead_canopy"],
        "dsm_vegetation_tile_overhead_as_canopy.tif": paths["cdsm_overhead"],
    }
    if any(overwrite or file_state(path) == "missing" for path in raster_targets.values()):
        b_arr, transform = raster_to_bounds(Path(source["dsm"]), tile_geom.bounds, res, crs)
        v_arr, _ = raster_to_bounds(Path(source["cdsm_base_vegetation"]), tile_geom.bounds, res, crs)
        oh_arr = np.zeros_like(b_arr, dtype="float32")
        if overhead is not None and len(overhead):
            shapes = []
            for _, row in overhead[overhead.geometry.intersects(tile_geom)].iterrows():
                geom = row.geometry.intersection(tile_geom)
                if geom is not None and not geom.is_empty:
                    shapes.append((geom, infer_overhead_height(row)))
            if shapes:
                oh_arr = rasterize(shapes, out_shape=b_arr.shape, transform=transform, fill=0.0, dtype="float32")
        payloads = {
            paths["dsm"]: b_arr,
            paths["dem"]: np.zeros_like(b_arr, dtype="float32"),
            paths["cdsm_base"]: v_arr,
            paths["overhead_canopy"]: oh_arr,
            paths["cdsm_overhead"]: np.maximum(v_arr, oh_arr),
        }
        for path, arr in payloads.items():
            if overwrite or file_state(path) == "missing":
                write_raster(path, arr, transform, crs)
                created += int(file_ready(path))

    failed = sum(1 for path in targets.values() if not file_ready(path))
    return {
        "asset_group": "shared_assets",
        "scenario": "all",
        "status": "success" if failed == 0 else "failed",
        "skipped_existing_count": skipped,
        "newly_created_count": created,
        "failed_count": failed,
        "message": "created missing shared assets: " + ",".join(create_names),
        "error_message": "",
    }


def make_wall_params(paths: dict[str, Path], cfg: dict[str, Any]) -> dict[str, Any]:
    pre = cfg["qgis_preprocess"]
    return {
        "INPUT": qgis_path(paths["dsm"]),
        "INPUT_LIMIT": float(pre.get("wall_input_limit_m", 3.0)),
        "OUTPUT_HEIGHT": qgis_path(paths["wall_height"]),
        "OUTPUT_ASPECT": qgis_path(paths["wall_aspect"]),
    }


def materialize_wall_once(
    cfg: dict[str, Any],
    cell_id: str,
    dry_run: bool,
    wall_alg: str,
) -> dict[str, Any]:
    paths = asset_paths(cfg, cell_id)
    overwrite = overwrite_existing(cfg, "overwrite_wall")
    states = {path.name: file_state(path) for path in wall_files(paths)}
    skipped = sum(1 for state in states.values() if state == "ready" and not overwrite)
    if all(state == "ready" for state in states.values()) and not overwrite:
        return {
            "asset_group": "wall",
            "scenario": "all",
            "status": "already_exists",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 0,
            "message": "wall height/aspect already exist",
            "error_message": "",
        }
    if any(state == "needs_review" for state in states.values()) and not overwrite:
        review = [name for name, state in states.items() if state == "needs_review"]
        return {
            "asset_group": "wall",
            "scenario": "all",
            "status": "needs_review",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": len(review),
            "message": "needs_review: " + ",".join(review),
            "error_message": "",
        }
    if any(state == "ready" for state in states.values()) and any(state == "missing" for state in states.values()) and not overwrite:
        return {
            "asset_group": "wall",
            "scenario": "all",
            "status": "needs_review",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 1,
            "message": "partial wall pair present; not overwriting existing wall asset in missing-only mode",
            "error_message": "",
        }
    if not file_ready(paths["dsm"]):
        return {
            "asset_group": "wall",
            "scenario": "all",
            "status": "failed",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 1,
            "message": "wall generation blocked because dsm_buildings_tile.tif is not ready",
            "error_message": "",
        }
    if dry_run:
        missing = [name for name, state in states.items() if state == "missing"]
        return {
            "asset_group": "wall",
            "scenario": "all",
            "status": "dry_run",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 0,
            "message": "would create wall assets: " + ",".join(missing),
            "error_message": "",
        }

    before = {path: file_ready(path) for path in wall_files(paths)}
    processing.run(wall_alg, make_wall_params(paths, cfg))
    after_ready = {path: file_ready(path) for path in wall_files(paths)}
    created = sum(1 for path, ready in after_ready.items() if ready and not before[path])
    failed = sum(1 for ready in after_ready.values() if not ready)
    return {
        "asset_group": "wall",
        "scenario": "all",
        "status": "success" if failed == 0 else "failed",
        "skipped_existing_count": skipped,
        "newly_created_count": created,
        "failed_count": failed,
        "message": "wall height/aspect generated once per cell",
        "error_message": "",
    }


def make_svf_params(paths: dict[str, Path], scenario: str, cfg: dict[str, Any]) -> dict[str, Any]:
    pre = cfg["qgis_preprocess"]
    out_dir = scenario_svf_dir(paths, scenario)
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "INPUT_DSM": qgis_path(paths["dsm"]),
        "INPUT_CDSM": qgis_path(scenario_cdsm(paths, scenario)),
        "TRANS_VEG": int(pre.get("trans_veg", 3)),
        "INPUT_TDSM": None,
        "INPUT_THEIGHT": float(pre.get("input_theight", 25.0)),
        "ANISO": bool(pre.get("aniso", True)),
        "WALL_SCHEME": bool(pre.get("wall_scheme", False)),
        "KMEANS": bool(pre.get("kmeans", True)),
        "CLUSTERS": int(pre.get("clusters", 5)),
        "INPUT_DEM": None,
        "INPUT_SVFHEIGHT": float(pre.get("input_svfheight", 1.0)),
        "OUTPUT_DIR": qgis_path(out_dir),
        "OUTPUT_FILE": qgis_path(out_dir / "svf.tif"),
    }


def materialize_svf_missing_only(
    cfg: dict[str, Any],
    cell_id: str,
    scenario: str,
    dry_run: bool,
    svf_alg: str,
) -> dict[str, Any]:
    paths = asset_paths(cfg, cell_id)
    svf_zip = scenario_svf_zip(paths, scenario)
    overwrite = overwrite_existing(cfg, "overwrite_svf")
    state = file_state(svf_zip)
    skipped = 1 if state == "ready" and not overwrite else 0
    if state == "ready" and not overwrite:
        return {
            "asset_group": "svf",
            "scenario": scenario,
            "status": "already_exists",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 0,
            "message": f"{scenario} svfs.zip already exists",
            "error_message": "",
        }
    if state == "needs_review" and not overwrite:
        return {
            "asset_group": "svf",
            "scenario": scenario,
            "status": "needs_review",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 1,
            "message": f"{scenario} svfs.zip exists but is empty or not a file",
            "error_message": "",
        }
    missing_inputs = [
        name
        for name, path in {
            "dsm_buildings_tile.tif": paths["dsm"],
            "scenario_cdsm_tile": scenario_cdsm(paths, scenario),
        }.items()
        if not file_ready(path)
    ]
    if missing_inputs:
        return {
            "asset_group": "svf",
            "scenario": scenario,
            "status": "failed",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 1,
            "message": f"{scenario} SVF blocked by missing inputs: " + ",".join(missing_inputs),
            "error_message": "",
        }
    if dry_run:
        return {
            "asset_group": "svf",
            "scenario": scenario,
            "status": "dry_run",
            "skipped_existing_count": skipped,
            "newly_created_count": 0,
            "failed_count": 0,
            "message": f"would create {scenario} scenario-specific svfs.zip",
            "error_message": "",
        }

    before_ready = file_ready(svf_zip)
    processing.run(svf_alg, make_svf_params(paths, scenario, cfg))
    after_ready = file_ready(svf_zip)
    return {
        "asset_group": "svf",
        "scenario": scenario,
        "status": "success" if after_ready else "failed",
        "skipped_existing_count": skipped,
        "newly_created_count": 1 if after_ready and not before_ready else 0,
        "failed_count": 0 if after_ready else 1,
        "message": f"{scenario} scenario-specific svfs.zip generated",
        "error_message": "" if after_ready else f"SVF algorithm finished but svfs.zip is missing: {svf_zip}",
    }


def progress_row(cfg: dict[str, Any], attempt_id: str, stage: str, cell_id: str, counts: Counter[str]) -> dict[str, Any]:
    paths = asset_paths(cfg, cell_id)
    all_files = all_required_files(paths)
    return {
        "attempt_id": attempt_id,
        "stage": stage,
        "cell_id": cell_id,
        "shared_assets_status": group_status(shared_asset_files(paths)),
        "wall_status": group_status(wall_files(paths)),
        "base_svf_status": group_status([paths["svf_base_zip"]]),
        "overhead_svf_status": group_status([paths["svf_overhead_zip"]]),
        "all_ready": "true" if all(file_ready(path) for path in all_files) else "false",
        "skipped_existing_count": int(counts["skipped_existing_count"]),
        "newly_created_count": int(counts["newly_created_count"]),
        "failed_count": int(counts["failed_count"]),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def write_progress_files(cfg: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    fields = [
        "attempt_id",
        "stage",
        "cell_id",
        "shared_assets_status",
        "wall_status",
        "base_svf_status",
        "overhead_svf_status",
        "all_ready",
        "skipped_existing_count",
        "newly_created_count",
        "failed_count",
        "claim_boundary",
    ]
    log_root = Path(cfg["local_run_log_root"])
    write_rows(log_root / "b87b4_qgis_materialization_progress_latest.csv", rows, fields)
    out_dir = repo_path(cfg, cfg["output_dir"])
    write_rows(out_dir / "b87b4_materialization_progress_by_cell.csv", rows, fields)


def print_stage_counts(progress: list[dict[str, Any]]) -> None:
    cells_total = len(progress)
    shared_assets_ready = sum(1 for row in progress if row["shared_assets_status"] == "ready")
    wall_ready = sum(1 for row in progress if row["wall_status"] == "ready")
    base_svf_ready = sum(1 for row in progress if row["base_svf_status"] == "ready")
    overhead_svf_ready = sum(1 for row in progress if row["overhead_svf_status"] == "ready")
    cells_all_ready = sum(1 for row in progress if row["all_ready"] == "true")
    skipped_existing = sum(int(row["skipped_existing_count"]) for row in progress)
    newly_created = sum(int(row["newly_created_count"]) for row in progress)
    failed = sum(int(row["failed_count"]) for row in progress)
    print(f"cells_total: {cells_total}")
    print(f"shared_assets_ready: {shared_assets_ready}")
    print(f"wall_ready: {wall_ready}")
    print(f"base_svf_ready: {base_svf_ready}")
    print(f"overhead_svf_ready: {overhead_svf_ready}")
    print(f"cells_all_ready: {cells_all_ready}")
    print(f"skipped_existing: {skipped_existing}")
    print(f"newly_created: {newly_created}")
    print(f"failed: {failed}")


def log_result(
    cfg: dict[str, Any],
    log_path: Path,
    attempt_id: str,
    cell_id: str,
    result: dict[str, Any],
    started: str,
    elapsed: float,
) -> None:
    paths = asset_paths(cfg, cell_id)
    scenario = str(result["scenario"])
    append_log(
        log_path,
        {
            "attempt_id": attempt_id,
            "cell_id": cell_id,
            "scenario": scenario,
            "status": result["status"],
            "started_at": started,
            "completed_at": now_iso(),
            "elapsed_seconds": round(elapsed, 3),
            "dsm_path": qgis_path(paths["dsm"]),
            "cdsm_path": qgis_path(scenario_cdsm(paths, scenario)) if scenario in {"base", "overhead_as_canopy"} else "",
            "dem_path": qgis_path(paths["dem"]),
            "svf_path_or_zip": qgis_path(scenario_svf_zip(paths, scenario)) if scenario in {"base", "overhead_as_canopy"} else "",
            "wall_height_path": qgis_path(paths["wall_height"]),
            "wall_aspect_path": qgis_path(paths["wall_aspect"]),
            "message": result.get("message", ""),
            "error_message": str(result.get("error_message", "")).replace("\r", " ").replace("\n", " | ")[:5000],
        },
    )


def main() -> int:
    cfg = read_json_config(DEFAULT_CONFIG_PATH)
    enabled, dry_run = runtime_switches(cfg)
    assert_runner_context(enabled)
    if not LOCAL_CONTEXT:
        print("REPO_RUNNER_CONTEXT: localize this runner before enabling writes.")
    if not enabled:
        print("RUN_ENABLED is false at runner or config level; this is a dry safety pass.")
    if dry_run:
        print("DRY_RUN is true at runner or config level; no QGIS processing writes will be attempted.")
    if enabled and not dry_run and (not QGIS_READY or not GEOSPATIAL_READY):
        print("BLOCKED_QGIS_OR_GEOSPATIAL_RUNTIME")
        return 2

    cells = stage_cells(cfg)
    attempt_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    log_path = Path(cfg["local_run_log_root"]) / "b87b4_qgis_materialization_log.csv"
    grid = None
    overhead = None
    wall_alg = ""
    svf_alg = ""
    if enabled and not dry_run:
        source = source_path_map(cfg)
        crs = str(cfg.get("working_crs", "EPSG:3414"))
        grid = gpd.read_file(source["grid_geometry"]).to_crs(crs)
        overhead_path = Path(source.get("overhead_vector", ""))
        overhead = gpd.read_file(overhead_path).to_crs(crs) if overhead_path.exists() else None
        wall_alg, svf_alg = ensure_algorithms(cfg)

    progress_rows: list[dict[str, Any]] = []
    scenarios = selected_scenarios(cfg)
    for idx, cell_id in enumerate(cells, start=1):
        print(f"[{idx}/{len(cells)}] {cell_id} materialization")
        cell_counts: Counter[str] = Counter()
        results: list[dict[str, Any]] = []
        for runner in [
            lambda: materialize_shared_assets_once(cfg, cell_id, grid, overhead, dry_run),
            lambda: materialize_wall_once(cfg, cell_id, dry_run, wall_alg),
        ]:
            started = now_iso()
            t0 = time.time()
            try:
                result = runner()
            except Exception as exc:
                result = {
                    "asset_group": "cell",
                    "scenario": "all",
                    "status": "failed",
                    "skipped_existing_count": 0,
                    "newly_created_count": 0,
                    "failed_count": 1,
                    "message": str(exc),
                    "error_message": traceback.format_exc(),
                }
            results.append(result)
            log_result(cfg, log_path, attempt_id, cell_id, result, started, time.time() - t0)
        for scenario in scenarios:
            started = now_iso()
            t0 = time.time()
            try:
                result = materialize_svf_missing_only(cfg, cell_id, scenario, dry_run, svf_alg)
            except Exception as exc:
                result = {
                    "asset_group": "svf",
                    "scenario": scenario,
                    "status": "failed",
                    "skipped_existing_count": 0,
                    "newly_created_count": 0,
                    "failed_count": 1,
                    "message": str(exc),
                    "error_message": traceback.format_exc(),
                }
            results.append(result)
            log_result(cfg, log_path, attempt_id, cell_id, result, started, time.time() - t0)
        for result in results:
            cell_counts["skipped_existing_count"] += int(result.get("skipped_existing_count", 0))
            cell_counts["newly_created_count"] += int(result.get("newly_created_count", 0))
            cell_counts["failed_count"] += int(result.get("failed_count", 0))
        progress_rows.append(progress_row(cfg, attempt_id, STAGE, cell_id, cell_counts))

    write_progress_files(cfg, progress_rows)
    print_stage_counts(progress_rows)
    print(f"Materialization log: {log_path}")
    return 0


if __name__ == "__console__" or __name__ == "__main__":
    main()
