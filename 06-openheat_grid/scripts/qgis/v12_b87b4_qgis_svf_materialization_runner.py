"""QGIS/UMEP local materialization runner for B8.7b.4.

Run only inside QGIS Desktop Python Console with Processing and UMEP loaded.
Repo copy defaults to RUN_ENABLED=False and DRY_RUN=True.

Inputs:
  - configs/v12/systemb_b87b4_b87c_materialization_package.yaml
  - b87c_manifest.csv and B87B candidate/source-lock CSVs named in config
  - locked DSM/CDSM/grid/overhead sources

Outputs, local-only:
  - C:/OpenHeat-local/solweig/b87c_n300/assets/<cell_id>/focus_cell.geojson
  - dsm_buildings_tile.tif, dsm_vegetation_tile_base.tif,
    dsm_overhead_canopy_tile.tif, dsm_vegetation_tile_overhead_as_canopy.tif,
    dsm_dem_flat_tile.tif
  - wall_height.tif, wall_aspect.tif
  - svf_base/svfs.zip and svf_overhead_as_canopy/svfs.zip
  - C:/OpenHeat-local/solweig/b87c_n300/run_logs/b87b4_qgis_materialization_log.csv

Saved metrics:
  Per-cell/scenario materialization status, generated local paths, elapsed seconds,
  QGIS algorithm ids, and error messages.

This runner does not run SOLWEIG and never writes rasters/SVF into the Git
worktree. Base and overhead_as_canopy SVF are generated separately.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path


RUN_ENABLED = False
DRY_RUN = True
LOCAL_CONTEXT = False
FORCE_PARTIAL = False
STAGE = "full_150"

REPO_ROOT = Path(r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid")
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs/v12/systemb_b87b4_b87c_materialization_package.yaml"


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
    print("QGIS Python needs geopandas, numpy, and rasterio for materialization.")
    print(exc)
    if RUN_ENABLED:
        raise SystemExit(2)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def repo_path(cfg: dict, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def append_log(path: Path, row: dict) -> None:
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


def algorithm_by_id(algorithm_id: str):
    registry = QgsApplication.processingRegistry()
    return registry.algorithmById(algorithm_id)


def ensure_algorithms(cfg: dict) -> tuple[str, str]:
    wall = str(cfg["qgis_wall_algorithm_id"])
    svf = str(cfg["qgis_svf_algorithm_id"])
    missing = [alg for alg in [wall, svf] if algorithm_by_id(alg) is None]
    if missing:
        raise RuntimeError("Missing QGIS/UMEP algorithms: " + ", ".join(missing))
    return wall, svf


def assert_local_path(cfg: dict, path: Path) -> None:
    root = Path(cfg["local_root"]).resolve()
    if not path.resolve().is_relative_to(root):
        raise RuntimeError(f"Refusing to write outside approved local root: {path}")
    if path.resolve().is_relative_to(REPO_ROOT.resolve()):
        raise RuntimeError(f"Refusing to write materialized asset inside Git worktree: {path}")


def source_path_map(cfg: dict) -> dict[str, str]:
    rows = read_rows(repo_path(cfg, cfg["b87b3_source_lock_path"]))
    out = {row["source_kind"]: row.get("canonical_path", "") for row in rows if row.get("canonical_path")}
    overhead = read_rows(repo_path(cfg, cfg["b87b3_overhead_source_path"]))
    for row in overhead:
        if row.get("overhead_source_path"):
            out["overhead_vector"] = row["overhead_source_path"]
            break
    return out


def candidates(cfg: dict) -> list[str]:
    rows = read_rows(repo_path(cfg, cfg["b87b_new_candidate_sample_index_path"]))
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        cell_id = str(row.get("cell_id", "")).strip()
        if cell_id and cell_id not in seen:
            seen.add(cell_id)
            out.append(cell_id)
    return out


def stage_cells(cfg: dict) -> list[str]:
    all_cells = candidates(cfg)
    stage_counts = {"smoke": 1, "pilot_5": 5, "pilot_20": 20, "full_150": int(cfg["expected_new_candidate_count"])}
    if STAGE not in stage_counts:
        raise RuntimeError(f"Unknown STAGE {STAGE!r}")
    return all_cells[: stage_counts[STAGE]]


def asset_paths(cfg: dict, cell_id: str) -> dict[str, Path]:
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


def write_raster(path: Path, arr, transform, crs) -> None:
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


def raster_to_bounds(src_path: Path, bounds: tuple[float, float, float, float], res: float, crs: str):
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


def infer_overhead_height(row) -> float:
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
    return defaults.get(str(row.get("overhead_type", "unknown_overhead")).lower(), 5.0)


def materialize_rasters(cfg: dict, cell_id: str, grid, overhead) -> dict[str, Path]:
    paths = asset_paths(cfg, cell_id)
    for path in paths.values():
        if isinstance(path, Path):
            if path.suffix:
                assert_local_path(cfg, path.parent)
            else:
                assert_local_path(cfg, path)
    paths["asset_folder"].mkdir(parents=True, exist_ok=True)
    paths["svf_base"].mkdir(parents=True, exist_ok=True)
    paths["svf_overhead"].mkdir(parents=True, exist_ok=True)

    source = source_path_map(cfg)
    crs = str(cfg.get("working_crs", "EPSG:3414"))
    res = float(cfg["raster_resolution_m"])
    focus = grid[grid["cell_id"].astype(str).eq(cell_id)].copy()
    if focus.empty:
        raise RuntimeError(f"Missing cell in locked grid: {cell_id}")
    focus.to_file(paths["focus"], driver="GeoJSON")
    tile_geom = focus.geometry.iloc[0].buffer(float(cfg["tile_buffer_m"]))
    gpd.GeoDataFrame({"cell_id": [cell_id]}, geometry=[tile_geom], crs=crs).to_file(paths["tile"], driver="GeoJSON")

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
    write_raster(paths["dsm"], b_arr, transform, crs)
    write_raster(paths["dem"], np.zeros_like(b_arr, dtype="float32"), transform, crs)
    write_raster(paths["cdsm_base"], v_arr, transform, crs)
    write_raster(paths["overhead_canopy"], oh_arr, transform, crs)
    write_raster(paths["cdsm_overhead"], np.maximum(v_arr, oh_arr), transform, crs)
    return paths


def make_wall_params(paths: dict[str, Path], cfg: dict) -> dict:
    pre = cfg["qgis_preprocess"]
    return {
        "INPUT": qgis_path(paths["dsm"]),
        "INPUT_LIMIT": float(pre.get("wall_input_limit_m", 3.0)),
        "OUTPUT_HEIGHT": qgis_path(paths["wall_height"]),
        "OUTPUT_ASPECT": qgis_path(paths["wall_aspect"]),
    }


def scenario_cdsm(paths: dict[str, Path], scenario: str) -> Path:
    return paths["cdsm_base"] if scenario == "base" else paths["cdsm_overhead"]


def scenario_svf_dir(paths: dict[str, Path], scenario: str) -> Path:
    return paths["svf_base"] if scenario == "base" else paths["svf_overhead"]


def scenario_svf_zip(paths: dict[str, Path], scenario: str) -> Path:
    return paths["svf_base_zip"] if scenario == "base" else paths["svf_overhead_zip"]


def make_svf_params(paths: dict[str, Path], scenario: str, cfg: dict) -> dict:
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


def run_wall_and_svf(paths: dict[str, Path], scenario: str, cfg: dict, wall_alg: str, svf_alg: str) -> str:
    pre = cfg["qgis_preprocess"]
    messages: list[str] = []
    if paths["wall_height"].exists() and paths["wall_aspect"].exists() and not pre.get("overwrite_wall", False):
        messages.append("wall reused")
    else:
        processing.run(wall_alg, make_wall_params(paths, cfg))
        if not paths["wall_height"].exists() or not paths["wall_aspect"].exists():
            raise RuntimeError("Wall height/aspect outputs missing after wall algorithm.")
        messages.append("wall generated")
    svf_zip = scenario_svf_zip(paths, scenario)
    if svf_zip.exists() and not pre.get("overwrite_svf", False):
        messages.append(f"{scenario} svfs.zip reused")
    else:
        processing.run(svf_alg, make_svf_params(paths, scenario, cfg))
        if not svf_zip.exists():
            raise RuntimeError(f"SVF algorithm finished but svfs.zip is missing: {svf_zip}")
        messages.append(f"{scenario} svfs.zip generated")
    return "; ".join(messages)


def main() -> int:
    if not QGIS_READY or not GEOSPATIAL_READY:
        print("BLOCKED_QGIS_OR_GEOSPATIAL_RUNTIME")
        return 2
    cfg = read_json_config(DEFAULT_CONFIG_PATH)
    if not LOCAL_CONTEXT:
        print("REPO_RUNNER_CONTEXT: localize this runner before enabling writes.")
    if not RUN_ENABLED:
        print("RUN_ENABLED is false; this is a dry safety pass.")
    if DRY_RUN:
        print("DRY_RUN is true; no QGIS processing writes will be attempted.")

    cells = stage_cells(cfg)
    expected = {"smoke": 1, "pilot_5": 5, "pilot_20": 20, "full_150": 150}[STAGE]
    if len(cells) != expected:
        raise RuntimeError(f"Stage {STAGE} selected {len(cells)} cells; expected {expected}")

    attempt_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    log_path = Path(cfg["local_run_log_root"]) / "b87b4_qgis_materialization_log.csv"
    source = source_path_map(cfg)
    grid = gpd.read_file(source["grid_geometry"]).to_crs(cfg.get("working_crs", "EPSG:3414"))
    overhead_path = Path(source.get("overhead_vector", ""))
    overhead = gpd.read_file(overhead_path).to_crs(cfg.get("working_crs", "EPSG:3414")) if overhead_path.exists() else None
    wall_alg, svf_alg = ensure_algorithms(cfg)

    for idx, cell_id in enumerate(cells, start=1):
        for scenario in cfg["expected_scenarios"]:
            started = now_iso()
            t0 = time.time()
            status = "dry_run" if DRY_RUN or not RUN_ENABLED else "failed"
            error = ""
            message = ""
            paths = asset_paths(cfg, cell_id)
            try:
                print(f"[{idx}/{len(cells)}] {cell_id} {scenario}")
                if RUN_ENABLED and not DRY_RUN:
                    paths = materialize_rasters(cfg, cell_id, grid, overhead)
                    message = run_wall_and_svf(paths, scenario, cfg, wall_alg, svf_alg)
                    status = "success"
                else:
                    message = "dry run only; set RUN_ENABLED=True and DRY_RUN=False in local copy"
            except Exception as exc:
                status = "failed"
                error = f"{exc}\n{traceback.format_exc()}"[:5000]
            finally:
                append_log(
                    log_path,
                    {
                        "attempt_id": attempt_id,
                        "cell_id": cell_id,
                        "scenario": scenario,
                        "status": status,
                        "started_at": started,
                        "completed_at": now_iso(),
                        "elapsed_seconds": round(time.time() - t0, 3),
                        "dsm_path": qgis_path(paths["dsm"]),
                        "cdsm_path": qgis_path(scenario_cdsm(paths, scenario)),
                        "dem_path": qgis_path(paths["dem"]),
                        "svf_path_or_zip": qgis_path(scenario_svf_zip(paths, scenario)),
                        "wall_height_path": qgis_path(paths["wall_height"]),
                        "wall_aspect_path": qgis_path(paths["wall_aspect"]),
                        "message": message,
                        "error_message": error.replace("\r", " ").replace("\n", " | "),
                    },
                )
    print(f"Materialization log: {log_path}")
    return 0


if __name__ == "__console__" or __name__ == "__main__":
    raise SystemExit(main())
