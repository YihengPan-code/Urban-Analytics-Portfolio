"""Sprint B3 N24 SOLWEIG runner for QGIS Python Console.

Run only inside a QGIS Python environment with Processing and UMEP loaded.

Inputs:
  - configs/v12/v12_solweig_n24_execution_config.example.json
  - configs/v12/v12_solweig_n24_run_matrix.csv
  - local DSM/vector/forcing inputs declared by the config.

Outputs:
  - data/solweig/v12_n24_tiles/<cell_id>/... raw raster/SOLWEIG artifacts
  - outputs/v12_solweig_n24_execution/n24_solweig_run_log.csv
  - outputs/v12_solweig_n24_execution/qgis_algorithm_resolution.md
  - outputs/v12_solweig_n24_execution/n24_effective_solweig_parameters.json
  - outputs/v12_solweig_n24_execution/n24_effective_solweig_parameters.md

Saved metrics:
  - per-run status, elapsed seconds, algorithm id, key input/output paths, and
    error message.

Scope:
  System B SOLWEIG-derived Tmrt execution only. This does not compute local WBGT,
  hazard_score, risk_score, surrogate models, or System A/B coupling.
"""

from __future__ import annotations

import csv
import json
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid")
CONFIG_PATH = PROJECT_ROOT / "configs/v12/v12_solweig_n24_execution_config.example.json"
DEFAULT_WALL_ALGORITHM_ID = "umep:Urban Geometry: Wall Height and Aspect"
DEFAULT_SVF_ALGORITHM_ID = "umep:Urban Geometry: Sky View Factor"

try:
    import processing  # type: ignore
    from qgis.core import QgsApplication  # type: ignore
except Exception as exc:  # pragma: no cover - this is for direct non-QGIS invocation.
    print("BLOCKED_QGIS_ENVIRONMENT_MISSING")
    print("This script must be run inside QGIS Python Console / QGIS Python.")
    print(exc)
    raise SystemExit(2)

try:
    import geopandas as gpd
    import numpy as np
    import pandas as pd
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.features import rasterize
    from rasterio.mask import mask
    from rasterio.transform import from_origin
    from rasterio.warp import reproject
except Exception as exc:
    print("BLOCKED_QGIS_PYTHON_DEPENDENCY_MISSING")
    print("QGIS was available, but this runner also needs pandas/geopandas/numpy/rasterio in the QGIS Python environment.")
    print(exc)
    raise SystemExit(2)


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
    """Return an absolute, QGIS-friendly path string."""
    return repo_path(value).as_posix()


def algorithm_by_id(algorithm_id: str):
    registry = QgsApplication.processingRegistry()
    try:
        alg = registry.algorithmById(algorithm_id)
        if alg is not None:
            return alg
    except Exception:
        pass
    for alg in registry.algorithms():
        if alg.id() == algorithm_id:
            return alg
    return None


def algorithm_param_names(algorithm_id: str) -> list[str]:
    alg = algorithm_by_id(algorithm_id)
    if alg is None:
        return []
    return [p.name() for p in alg.parameterDefinitions()]


def algorithm_matches() -> list[dict]:
    keywords = ["solweig", "mean radiant", "outdoor thermal comfort"]
    rows = []
    registry = QgsApplication.processingRegistry()
    for alg in registry.algorithms():
        text = f"{alg.id()} {alg.displayName()} {alg.group()} {alg.provider().name()}".lower()
        if any(k in text for k in keywords):
            rows.append(
                {
                    "id": alg.id(),
                    "display_name": alg.displayName(),
                    "group": alg.group(),
                    "provider": alg.provider().name(),
                    "parameters": [p.name() for p in alg.parameterDefinitions()],
                }
            )
    return rows


def resolve_solweig_algorithm(out_dir: Path) -> str | None:
    matches = algorithm_matches()
    preferred = None
    for row in matches:
        if row["id"] == "umep:Outdoor Thermal Comfort: SOLWEIG":
            preferred = row
            break
    if preferred is None and matches:
        for row in matches:
            if "solweig" in row["id"].lower() or "solweig" in row["display_name"].lower():
                preferred = row
                break
    lines = ["# QGIS SOLWEIG Algorithm Resolution", ""]
    if preferred:
        lines.append("Status: **PASS**")
        lines.append("")
        lines.append(f"- selected_algorithm_id: `{preferred['id']}`")
        lines.append(f"- selected_display_name: `{preferred['display_name']}`")
    else:
        lines.append("Status: **BLOCKED_SOLWEIG_PROVIDER_MISSING**")
        lines.append("")
        lines.append("No SOLWEIG / Mean radiant temperature / Outdoor Thermal Comfort algorithm was found in the QGIS Processing registry.")
    lines.append("")
    lines.append("## Candidates")
    lines.append("")
    if matches:
        for row in matches:
            lines.append(f"- `{row['id']}` | {row['display_name']} | provider={row['provider']}")
    else:
        lines.append("_None._")
    (out_dir / "qgis_algorithm_resolution.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return preferred["id"] if preferred else None


def resolve_preprocess_algorithms(cfg: dict, out_dir: Path) -> tuple[str | None, str | None]:
    """Resolve verified UMEP preprocessing algorithms and write a mapping report."""
    pre = cfg.get("preprocess", {})
    wall_id = str(pre.get("wall_algorithm_id", DEFAULT_WALL_ALGORITHM_ID))
    svf_id = str(pre.get("svf_algorithm_id", DEFAULT_SVF_ALGORITHM_ID))
    wall_alg = algorithm_by_id(wall_id)
    svf_alg = algorithm_by_id(svf_id)

    lines = ["# QGIS Preprocess Algorithm Resolution", ""]
    if wall_alg is not None and svf_alg is not None:
        lines.append("Status: **PASS**")
    else:
        lines.append("Status: **BLOCKED_ALGORITHM_MISSING**")
    lines += [
        "",
        f"- wall_algorithm_id: `{wall_id}`",
        f"- wall_found: `{wall_alg is not None}`",
        f"- svf_algorithm_id: `{svf_id}`",
        f"- svf_found: `{svf_alg is not None}`",
        "",
        "## Verified Parameter Mapping",
        "",
        "Wall Height and Aspect:",
        "",
        "```text",
        "INPUT -> building DSM tile",
        "INPUT_LIMIT -> 3.0 m",
        "OUTPUT_HEIGHT -> wall_height.tif",
        "OUTPUT_ASPECT -> wall_aspect.tif",
        "```",
        "",
        "Sky View Factor:",
        "",
        "```text",
        "INPUT_DSM -> building DSM tile",
        "INPUT_CDSM -> scenario vegetation DSM",
        "TRANS_VEG -> 3",
        "INPUT_TDSM -> None",
        "INPUT_THEIGHT -> 25.0",
        "ANISO -> True",
        "WALL_SCHEME -> False",
        "KMEANS -> True",
        "CLUSTERS -> 5",
        "INPUT_DEM -> None",
        "INPUT_SVFHEIGHT -> 1.0",
        "OUTPUT_DIR -> svf_<scenario>/",
        "OUTPUT_FILE -> svf_<scenario>/svf.tif",
        "expected zip -> svf_<scenario>/svfs.zip",
        "```",
        "",
        "## Registry Parameters Seen",
        "",
        f"- wall_parameters: `{', '.join(algorithm_param_names(wall_id))}`",
        f"- svf_parameters: `{', '.join(algorithm_param_names(svf_id))}`",
    ]
    (out_dir / "qgis_preprocess_algorithm_resolution.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return (wall_id if wall_alg is not None else None, svf_id if svf_alg is not None else None)


def write_raster(path: Path, arr: np.ndarray, transform, crs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype("float32"), 1)


def raster_to_bounds(src_path: Path, bounds: tuple[float, float, float, float], res: float, crs) -> tuple[np.ndarray, object]:
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


def infer_overhead_height(row, defaults: dict[str, float]) -> float:
    for col in ["height_m", "manual_height_m", "height"]:
        if col in row and pd.notna(row[col]):
            val = float(row[col])
            if val > 0:
                return val
    typ = str(row.get("overhead_type", "unknown_overhead")).lower()
    return float(defaults.get(typ, defaults.get("unknown_overhead", 5.0)))


def cell_geometry_from_centroid(x: float, y: float, cell_size: float):
    from shapely.geometry import box

    half = cell_size / 2.0
    return box(x - half, y - half, x + half, y + half)


def prepare_tile(cfg: dict, grid_row, overhead_gdf) -> dict[str, str]:
    cell_id = str(grid_row["cell_id"])
    crs = cfg.get("crs", "EPSG:3414")
    cell_size = float(cfg.get("focus_cell_size_m", 100))
    buffer_m = float(cfg.get("tile_buffer_m", 100))
    res = float(cfg.get("raster_resolution_m", 2))
    raw_root = repo_path(cfg["raw_output_root"])
    tile_dir = raw_root / cell_id
    tile_dir.mkdir(parents=True, exist_ok=True)

    focus = cell_geometry_from_centroid(float(grid_row["centroid_x_svy21"]), float(grid_row["centroid_y_svy21"]), cell_size)
    tile_geom = focus.buffer(buffer_m)
    bounds = tile_geom.bounds
    building_dsm = repo_path(cfg["building_dsm_path"])
    vegetation_dsm = repo_path(cfg["vegetation_dsm_path"])

    b_arr, transform = raster_to_bounds(building_dsm, bounds, res, crs)
    v_arr, _ = raster_to_bounds(vegetation_dsm, bounds, res, crs)
    dem = np.zeros_like(b_arr, dtype="float32")

    defaults = {"covered_walkway": 3.0, "pedestrian_bridge": 5.0, "elevated_rail": 8.0, "elevated_road": 8.0, "viaduct": 8.0, "unknown_overhead": 5.0}
    oh_arr = np.zeros_like(b_arr, dtype="float32")
    if overhead_gdf is not None and len(overhead_gdf):
        oh = overhead_gdf[overhead_gdf.geometry.intersects(tile_geom)].copy()
        shapes = []
        for _, row in oh.iterrows():
            geom = row.geometry.intersection(tile_geom)
            if geom is not None and not geom.is_empty:
                shapes.append((geom, infer_overhead_height(row, defaults)))
        if shapes:
            oh_arr = rasterize(shapes, out_shape=b_arr.shape, transform=transform, fill=0.0, dtype="float32")
    v_oh = np.maximum(v_arr, oh_arr)

    paths = {
        "tile_dir": str(tile_dir),
        "focus_geojson": str(tile_dir / "focus_cell.geojson"),
        "input_dsm": str(tile_dir / "dsm_buildings_tile.tif"),
        "input_dem": str(tile_dir / "dsm_dem_flat_tile.tif"),
        "input_vegetation_base": str(tile_dir / "dsm_vegetation_tile_base.tif"),
        "input_overhead_canopy": str(tile_dir / "dsm_overhead_canopy_tile.tif"),
        "input_vegetation_overhead_as_canopy": str(tile_dir / "dsm_vegetation_tile_overhead_as_canopy.tif"),
        "wall_height": str(tile_dir / "wall_height.tif"),
        "wall_aspect": str(tile_dir / "wall_aspect.tif"),
        "svf_base": str(tile_dir / "svf_base"),
        "svf_overhead_as_canopy": str(tile_dir / "svf_overhead_as_canopy"),
    }
    if not Path(paths["input_dsm"]).exists():
        write_raster(Path(paths["input_dsm"]), b_arr, transform, crs)
    if not Path(paths["input_dem"]).exists():
        write_raster(Path(paths["input_dem"]), dem, transform, crs)
    if not Path(paths["input_vegetation_base"]).exists():
        write_raster(Path(paths["input_vegetation_base"]), v_arr, transform, crs)
    if not Path(paths["input_overhead_canopy"]).exists():
        write_raster(Path(paths["input_overhead_canopy"]), oh_arr, transform, crs)
    if not Path(paths["input_vegetation_overhead_as_canopy"]).exists():
        write_raster(Path(paths["input_vegetation_overhead_as_canopy"]), v_oh, transform, crs)
    gpd.GeoDataFrame({"cell_id": [cell_id]}, geometry=[focus], crs=crs).to_file(paths["focus_geojson"], driver="GeoJSON")
    return paths


def wall_outputs_exist(paths: dict[str, str]) -> bool:
    return Path(paths["wall_height"]).exists() and Path(paths["wall_aspect"]).exists()


def scenario_vegetation_path(paths: dict[str, str], scenario: str) -> Path:
    if scenario == "base":
        return Path(paths["input_vegetation_base"])
    if scenario == "overhead_as_canopy":
        return Path(paths["input_vegetation_overhead_as_canopy"])
    raise ValueError(f"Unknown scenario: {scenario}")


def svf_dir(paths: dict[str, str], scenario: str) -> Path:
    return Path(paths[f"svf_{scenario}"])


def svf_zip(paths: dict[str, str], scenario: str) -> Path:
    return svf_dir(paths, scenario) / "svfs.zip"


def make_wall_params(paths: dict[str, str], cfg: dict) -> dict:
    pre = cfg.get("preprocess", {})
    return {
        "INPUT": qgis_path(paths["input_dsm"]),
        "INPUT_LIMIT": float(pre.get("wall_input_limit_m", 3.0)),
        "OUTPUT_HEIGHT": qgis_path(paths["wall_height"]),
        "OUTPUT_ASPECT": qgis_path(paths["wall_aspect"]),
    }


def make_svf_params(paths: dict[str, str], scenario: str, cfg: dict) -> dict:
    pre = cfg.get("preprocess", {})
    out_dir = svf_dir(paths, scenario)
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "INPUT_DSM": qgis_path(paths["input_dsm"]),
        "INPUT_CDSM": qgis_path(scenario_vegetation_path(paths, scenario)),
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


def run_preprocess(paths: dict[str, str], scenario: str, cfg: dict, wall_alg: str, svf_alg: str) -> str:
    """Prepare or reuse wall H/A and scenario-specific SVF outputs."""
    pre = cfg.get("preprocess", {})
    overwrite_wall = bool(pre.get("overwrite_wall", False))
    overwrite_svf = bool(pre.get("overwrite_svf", False))

    input_dsm = Path(paths["input_dsm"])
    input_cdsm = scenario_vegetation_path(paths, scenario)
    if not input_dsm.exists():
        raise FileNotFoundError(f"Missing preprocess input_dsm: {input_dsm}")
    if not input_cdsm.exists():
        raise FileNotFoundError(f"Missing preprocess input_cdsm for {scenario}: {input_cdsm}")

    messages = []
    if wall_outputs_exist(paths) and not overwrite_wall:
        messages.append("wall_height/wall_aspect reused")
    else:
        print("  [WALL]", wall_alg)
        processing.run(wall_alg, make_wall_params(paths, cfg))
        if not wall_outputs_exist(paths):
            raise RuntimeError(
                "Wall H/A completed but expected outputs are missing: "
                f"{paths['wall_height']}; {paths['wall_aspect']}"
            )
        messages.append("wall_height/wall_aspect generated")

    svf_dir(paths, scenario).mkdir(parents=True, exist_ok=True)
    if svf_zip(paths, scenario).exists() and not overwrite_svf:
        messages.append(f"{scenario} svfs.zip reused")
    else:
        print("  [SVF]", svf_alg, scenario)
        result = processing.run(svf_alg, make_svf_params(paths, scenario, cfg))
        if not svf_zip(paths, scenario).exists():
            raise RuntimeError(
                f"SVF completed but svfs.zip is missing: {svf_zip(paths, scenario)}. "
                f"Processing result: {result}"
            )
        messages.append(f"{scenario} svfs.zip generated")
    return "; ".join(messages)


def tmrt_output_exists(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with rasterio.open(path) as src:
            return src.count >= 1 and src.width > 0 and src.height > 0
    except Exception:
        return False


def find_tmrt_output(output_dir: Path) -> Path:
    preferred = output_dir / "Tmrt_average.tif"
    if preferred.exists():
        return preferred
    matches = sorted(output_dir.glob("*Tmrt*.tif"))
    return matches[0] if matches else preferred


def make_params(cfg: dict, algorithm_id: str, row: dict, paths: dict[str, str]) -> dict:
    scenario = row["scenario"]
    hour = int(row["hour"])
    output_dir = repo_path(cfg["raw_output_root"]) / row["cell_id"] / f"solweig_{scenario}" / f"solweig_outputs_h{hour:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    input_vegetation = paths["input_vegetation_base"] if scenario == "base" else paths["input_vegetation_overhead_as_canopy"]
    forcing = repo_path(cfg["forcing_paths_by_hour"][str(hour)])
    return {
        "INPUT_DSM": qgis_path(paths["input_dsm"]),
        "INPUT_SVF": qgis_path(svf_zip(paths, scenario)),
        "INPUT_HEIGHT": qgis_path(paths["wall_height"]),
        "INPUT_ASPECT": qgis_path(paths["wall_aspect"]),
        "INPUT_CDSM": qgis_path(input_vegetation),
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
        "INPUTMET": qgis_path(forcing),
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


def validate_pre_solweig_inputs(params: dict) -> list[str]:
    missing = []
    required = [
        ("input_dsm", "INPUT_DSM"),
        ("input_svf", "INPUT_SVF"),
        ("input_vegetation", "INPUT_CDSM"),
        ("input_dem", "INPUT_DEM"),
        ("inputmet", "INPUTMET"),
        ("wall_height", "INPUT_HEIGHT"),
        ("wall_aspect", "INPUT_ASPECT"),
    ]
    for label, key in required:
        path = Path(str(params.get(key, "")))
        if not path.exists():
            missing.append(f"missing {label}: {path}")
    output_dir = Path(str(params.get("OUTPUT_DIR", "")))
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        missing.append(f"cannot create output_dir: {output_dir} ({exc})")
    return missing


def write_effective_parameters(out_dir: Path, algorithm_id: str) -> None:
    params = {
        "qgis_algorithm_id": algorithm_id,
        "scenario_design": "paired base vs overhead_as_canopy comparison; not absolute truth",
        "INPUTMET_key": "INPUTMET",
        "LEAF_START": 1,
        "LEAF_END": 366,
        "UTC": 8,
        "TRANS_VEG": 3,
        "INPUT_THEIGHT": 25.0,
        "OUTPUT_TMRT": True,
        "tmrt_output_filename_note": "SOLWEIG may write Tmrt_average.tif; hour is parsed from parent folder solweig_outputs_hHH.",
    }
    write_json(out_dir / "n24_effective_solweig_parameters.json", params)
    lines = ["# N24 Effective SOLWEIG Parameters", ""]
    for key, value in params.items():
        lines.append(f"- `{key}`: `{value}`")
    (out_dir / "n24_effective_solweig_parameters.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def archive_existing_log(log_path: Path, attempt_id: str) -> Path | None:
    """Move any previous run log aside so a new manual run starts clean."""
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
        "hour",
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


def normalize_error(message: str) -> str:
    text = " ".join(str(message).replace("\\", "/").split())
    return text[:220]


def write_runtime_stop_report(out_dir: Path, attempt_id: str, reason: str, counts: Counter) -> None:
    lines = [
        "# Sprint B3.1 Runtime Stop Report",
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
    (out_dir / "n24_runtime_stop_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked_algorithm_log(log_path: Path, run_matrix, attempt_id: str, run_started_at: str, message: str) -> None:
    for _, rr in run_matrix.iterrows():
        row = rr.to_dict()
        append_log(
            log_path,
            {
                "attempt_id": attempt_id,
                "run_started_at": run_started_at,
                "run_id": row.get("run_id", ""),
                "cell_id": row.get("cell_id", ""),
                "scenario": row.get("scenario", ""),
                "hour": row.get("hour", ""),
                "status": "blocked_algorithm_missing",
                "started_at": now_iso(),
                "completed_at": now_iso(),
                "elapsed_seconds": 0,
                "qgis_algorithm_id": "",
                "error_message": message,
            },
        )


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
    grid = pd.read_csv(repo_path(cfg["grid_feature_path"]))
    grid["cell_id"] = grid["cell_id"].astype(str)
    run_matrix = pd.read_csv(repo_path(cfg["run_matrix_path"]))
    run_matrix["cell_id"] = run_matrix["cell_id"].astype(str)
    log_path = out_dir / "n24_solweig_run_log.csv"
    attempt_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_started_at = now_iso()
    archived_log = archive_existing_log(log_path, attempt_id)

    algorithm_id = resolve_solweig_algorithm(out_dir)
    wall_alg, svf_alg = resolve_preprocess_algorithms(cfg, out_dir)

    print("=" * 72)
    print("Sprint B3.1 N24 SOLWEIG QGIS Console runner")
    print(f"attempt_id: {attempt_id}")
    print(f"expected main runs: {len(run_matrix)}")
    print(f"SOLWEIG algorithm: {algorithm_id}")
    print(f"Wall algorithm: {wall_alg}")
    print(f"SVF algorithm: {svf_alg}")
    if archived_log:
        print(f"archived previous run log: {archived_log}")
    print("=" * 72)

    if not algorithm_id:
        message = "SOLWEIG algorithm missing from QGIS Processing registry."
        print("BLOCKED_ALGORITHM_MISSING:", message)
        write_blocked_algorithm_log(log_path, run_matrix, attempt_id, run_started_at, message)
        print_summary(len(run_matrix), Counter({"blocked_algorithm_missing": len(run_matrix)}))
        return
    if not wall_alg or not svf_alg:
        message = "Required UMEP preprocessing algorithm missing from QGIS Processing registry."
        print("BLOCKED_ALGORITHM_MISSING:", message)
        write_blocked_algorithm_log(log_path, run_matrix, attempt_id, run_started_at, message)
        print_summary(len(run_matrix), Counter({"blocked_algorithm_missing": len(run_matrix)}))
        return

    write_effective_parameters(out_dir, algorithm_id)

    overhead_path = repo_path(cfg["overhead_vector_path"])
    overhead = gpd.read_file(overhead_path).to_crs(cfg.get("crs", "EPSG:3414")) if overhead_path.exists() else None

    first_10_non_skipped = 0
    first_10_failures: Counter = Counter()
    stop_limit = int(cfg.get("stop_if_first_10_failure_count_gt", 5))
    cached_tiles: dict[str, dict[str, str]] = {}
    total = len(run_matrix)
    status_counts: Counter = Counter()

    for idx, rr in enumerate(run_matrix.itertuples(index=False), start=1):
        rr_dict = rr._asdict()
        row = rr_dict
        started = now_iso()
        t0 = time.time()
        cell_id = row["cell_id"]
        scenario = row["scenario"]
        hour = int(row["hour"])
        status = "failed_preprocess"
        error_message = ""
        params = {}
        phase = "preprocess"
        print(f"\n[{idx:03d}/{total:03d}] {row.get('run_id')} {cell_id} {scenario} h{hour:02d}")
        try:
            if cell_id not in cached_tiles:
                g = grid[grid["cell_id"] == cell_id]
                if g.empty:
                    raise RuntimeError(f"selected cell not found in grid feature file: {cell_id}")
                cached_tiles[cell_id] = prepare_tile(cfg, g.iloc[0], overhead)
            paths = cached_tiles[cell_id]
            params = make_params(cfg, algorithm_id, row, paths)
            tmrt_path = find_tmrt_output(Path(params["OUTPUT_DIR"]))
            if cfg.get("skip_completed", True) and tmrt_output_exists(tmrt_path):
                status = "skipped_completed"
            else:
                preprocess_message = run_preprocess(paths, scenario, cfg, wall_alg, svf_alg)
                missing = validate_pre_solweig_inputs(params)
                if missing:
                    raise FileNotFoundError("; ".join(missing))
                print(f"  [PREPROCESS OK] {preprocess_message}")
                phase = "solweig"
                processing.run(algorithm_id, params)
                phase = "post_solweig"
                tmrt_path = find_tmrt_output(Path(params["OUTPUT_DIR"]))
                status = "success" if tmrt_output_exists(tmrt_path) else "failed_solweig"
                if status == "failed_solweig":
                    error_message = "SOLWEIG completed but readable Tmrt output was not found."
        except Exception as exc:
            status = "failed_solweig" if phase == "solweig" else "failed_preprocess"
            error_message = f"{exc}\n{traceback.format_exc()}"[:5000]
        finally:
            completed = now_iso()
            elapsed = round(time.time() - t0, 3)
            tmrt_path = find_tmrt_output(Path(params.get("OUTPUT_DIR", repo_path(cfg["raw_output_root"]) / cell_id / f"solweig_{scenario}" / f"solweig_outputs_h{hour:02d}")))
            append_log(
                log_path,
                {
                    "attempt_id": attempt_id,
                    "run_started_at": run_started_at,
                    "run_id": row.get("run_id", ""),
                    "cell_id": cell_id,
                    "scenario": scenario,
                    "hour": hour,
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
