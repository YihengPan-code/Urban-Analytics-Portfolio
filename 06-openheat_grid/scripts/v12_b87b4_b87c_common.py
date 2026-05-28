"""Shared helpers for the B8.7b.4/B87C local materialization package.

Inputs:
  - configs/v12/systemb_b87b4_b87c_materialization_package.yaml
  - B8.7b.3 source-lock CSVs and B8.7b N300 precheck CSVs named in config.
  - Optional local-only root C:/OpenHeat-local/solweig/b87c_n300.

Outputs:
  - Compact CSV/Markdown/Python package artifacts under
    outputs/v12_surrogate/b8_7b4_b87c_materialization_package/.
  - Local-only folders, focus-cell GeoJSONs, forcing text files, runner copies,
    and manifest copies under C:/OpenHeat-local/solweig/b87c_n300.

Saved metrics:
  - input/source-lock inventory, tile spec, materialization task/audit status,
    manifest row counts, runner inventory, readiness matrices, and git hygiene
    guard rows.

This module does not run QGIS, UMEP, or SOLWEIG. It never writes raster/SVF
assets into the Git worktree and never creates AOI/B9/WBGT/risk outputs.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import shutil
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


CLAIM_BOUNDARY = (
    "B8.7b.4/B87C local-only materialization package; no repo raster writes; "
    "no AOI/B9; no WBGT/risk/hazard/exposure/vulnerability outputs; "
    "no observed truth; no causal feature-importance claims."
)
UMEP_HEADER = (
    "%iy id it imin qn qh qe qs qf U RH Tair pres rain kdown snow ldown "
    "fcld wuh xsmd lai_hr Kdiff Kdir Wd"
)
UMEP_COLUMNS = (
    "iy",
    "id",
    "it",
    "imin",
    "qn",
    "qh",
    "qe",
    "qs",
    "qf",
    "U",
    "RH",
    "Tair",
    "pres",
    "rain",
    "kdown",
    "snow",
    "ldown",
    "fcld",
    "wuh",
    "xsmd",
    "lai_hr",
    "Kdiff",
    "Kdir",
    "Wd",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict[str, Any]:
    """Load the JSON-compatible YAML config with stdlib only."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_repo_path(cfg: dict[str, Any], value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root() / path


def output_dir(cfg: dict[str, Any]) -> Path:
    path = resolve_repo_path(cfg, cfg["output_dir"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def slash(path: str | Path) -> str:
    return Path(path).as_posix()


def local_path(cfg: dict[str, Any], key: str) -> Path:
    return Path(str(cfg[key]))


def approved_local_root(cfg: dict[str, Any], path: Path) -> bool:
    try:
        root = local_path(cfg, "local_root").resolve()
        return path.resolve().is_relative_to(root)
    except Exception:
        return False


def geospatial_dependency_status() -> dict[str, str]:
    deps = ["rasterio", "geopandas", "shapely", "numpy"]
    return {dep: ("available" if importlib.util.find_spec(dep) else "missing") for dep in deps}


def geospatial_ready() -> bool:
    return all(status == "available" for status in geospatial_dependency_status().values())


def candidate_rows(cfg: dict[str, Any]) -> list[dict[str, str]]:
    rows = read_rows(resolve_repo_path(cfg, cfg["b87b_new_candidate_sample_index_path"]))
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for row in rows:
        cell_id = str(row.get("cell_id", "")).strip()
        if cell_id and cell_id not in seen:
            seen.add(cell_id)
            unique.append(row)
    return unique


def source_lock_rows(cfg: dict[str, Any]) -> list[dict[str, str]]:
    return read_rows(resolve_repo_path(cfg, cfg["b87b3_source_lock_path"]))


def source_path_map(cfg: dict[str, Any]) -> dict[str, str]:
    rows = source_lock_rows(cfg)
    out: dict[str, str] = {}
    for row in rows:
        kind = str(row.get("source_kind", ""))
        path = str(row.get("canonical_path", ""))
        if path:
            out[kind] = path
    overhead_rows = read_rows(resolve_repo_path(cfg, cfg["b87b3_overhead_source_path"]))
    for row in overhead_rows:
        path = str(row.get("overhead_source_path", ""))
        if path:
            out["overhead_vector"] = path
            break
    return out


def asset_paths(cfg: dict[str, Any], cell_id: str) -> dict[str, Path]:
    root = local_path(cfg, "local_asset_root") / cell_id
    return {
        "asset_folder": root,
        "focus_cell_geojson": root / "focus_cell.geojson",
        "tile_boundary_buffered_geojson": root / "tile_boundary_buffered.geojson",
        "dsm": root / "dsm_buildings_tile.tif",
        "dem": root / "dsm_dem_flat_tile.tif",
        "cdsm_base": root / "dsm_vegetation_tile_base.tif",
        "overhead_canopy": root / "dsm_overhead_canopy_tile.tif",
        "cdsm_overhead": root / "dsm_vegetation_tile_overhead_as_canopy.tif",
        "wall_height": root / "wall_height.tif",
        "wall_aspect": root / "wall_aspect.tif",
        "svf_base_dir": root / "svf_base",
        "svf_base_zip": root / "svf_base" / "svfs.zip",
        "svf_overhead_dir": root / "svf_overhead_as_canopy",
        "svf_overhead_zip": root / "svf_overhead_as_canopy" / "svfs.zip",
    }


def scenario_cdsm_path(paths: dict[str, Path], scenario: str) -> Path:
    return paths["cdsm_base"] if scenario == "base" else paths["cdsm_overhead"]


def scenario_svf_zip(paths: dict[str, Path], scenario: str) -> Path:
    return paths["svf_base_zip"] if scenario == "base" else paths["svf_overhead_zip"]


def forcing_slots(cfg: dict[str, Any]) -> list[dict[str, str]]:
    preview_path = resolve_repo_path(cfg, cfg["b87b_run_plan_preview_path"])
    rows = read_rows(preview_path)
    seen: set[tuple[str, str, str]] = set()
    slots: list[dict[str, str]] = []
    for row in rows:
        key = (
            str(row.get("forcing_day_id", "")),
            str(row.get("date", "")),
            str(row.get("hour_sgt", "")),
        )
        if all(key) and key not in seen:
            seen.add(key)
            slots.append(
                {
                    "forcing_day_id": key[0],
                    "date": key[1],
                    "hour_sgt": key[2],
                }
            )
    return sorted(slots, key=lambda r: (r["forcing_day_id"], int(r["hour_sgt"])))


def source_exists(path_text: str) -> bool:
    return bool(path_text) and Path(path_text).exists()


def path_metadata(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "exists": bool_text(exists),
        "is_file": bool_text(path.is_file()) if exists else "false",
        "is_dir": bool_text(path.is_dir()) if exists else "false",
        "size_bytes": path.stat().st_size if exists and path.is_file() else "",
    }


def write_input_inventory(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    path_items = [
        ("b87b3_source_lock_path", "required_repo_csv"),
        ("b87b3_version_lock_path", "required_repo_csv"),
        ("b87b3_svf_model_path", "required_repo_csv"),
        ("b87b3_overhead_source_path", "required_repo_csv"),
        ("b87b_new_candidate_sample_index_path", "required_repo_csv"),
        ("b87b_run_plan_preview_path", "required_repo_csv"),
        ("b87b_expected_run_count_path", "required_repo_csv"),
        ("b86g3_design_path", "required_repo_csv"),
        ("f5_pairwise_label_path", "required_repo_csv"),
        ("forcing_source_csv", "forcing_source_csv"),
    ]
    rows: list[dict[str, Any]] = []
    for key, role in path_items:
        path = resolve_repo_path(cfg, cfg[key])
        meta = path_metadata(path)
        rows.append(
            {
                "input_key": key,
                "role": role,
                "path": slash(path),
                "status": "PASS" if path.exists() else "MISSING",
                **meta,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    for dep, status in geospatial_dependency_status().items():
        rows.append(
            {
                "input_key": f"python_dependency_{dep}",
                "role": "optional_local_python_raster_materialization",
                "path": dep,
                "status": status.upper(),
                "exists": bool_text(status == "available"),
                "is_file": "false",
                "is_dir": "false",
                "size_bytes": "",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_rows(
        out / "b87b4_input_inventory.csv",
        rows,
        ["input_key", "role", "path", "status", "exists", "is_file", "is_dir", "size_bytes", "claim_boundary"],
    )
    return rows


def write_source_lock_summary(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    rows = []
    for row in source_lock_rows(cfg):
        path_text = str(row.get("canonical_path", ""))
        rows.append(
            {
                "source_kind": row.get("source_kind", ""),
                "scenario": row.get("scenario", ""),
                "canonical_path": path_text,
                "lock_status": row.get("lock_status", ""),
                "version_status": row.get("version_status", ""),
                "exists_now": bool_text(source_exists(path_text)) if path_text else row.get("exists_by_metadata", ""),
                "required_for": row.get("required_for", ""),
                "b87b4_interpretation": source_lock_interpretation(row),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_rows(
        out / "b87b4_source_lock_summary.csv",
        rows,
        [
            "source_kind",
            "scenario",
            "canonical_path",
            "lock_status",
            "version_status",
            "exists_now",
            "required_for",
            "b87b4_interpretation",
            "claim_boundary",
        ],
    )
    return rows


def source_lock_interpretation(row: dict[str, str]) -> str:
    kind = row.get("source_kind", "")
    status = row.get("lock_status", "")
    if kind == "svf_base_full":
        return "base_full_aoi_svf_source_only_not_per_tile_svfs_zip"
    if kind == "svf_overhead":
        return "must_generate_overhead_scenario_specific_svf"
    if status.startswith("LOCKED"):
        return "usable_source_for_local_only_materialization"
    if status.startswith("NOT_APPLICABLE"):
        return "handled_by_local_convention"
    return "review_required"


def setup_local_roots(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    keys = [
        "local_root",
        "local_asset_root",
        "local_output_root",
        "local_run_log_root",
        "local_runner_root",
        "local_manifest_root",
        "local_forcing_root",
    ]
    rows = []
    for key in keys:
        path = local_path(cfg, key)
        status = "CREATED_OR_EXISTS"
        note = ""
        if not approved_local_root(cfg, path):
            status = "REFUSED_OUTSIDE_APPROVED_LOCAL_ROOT"
            note = "path is not under configured local_root"
        else:
            path.mkdir(parents=True, exist_ok=True)
        rows.append(
            {
                "local_key": key,
                "path": slash(path),
                "status": status,
                "exists_after": bool_text(path.exists()),
                "repo_side": "false",
                "note": note,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_rows(
        out / "b87b4_local_root_setup.csv",
        rows,
        ["local_key", "path", "status", "exists_after", "repo_side", "note", "claim_boundary"],
    )
    return rows


def write_tile_specs(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    candidates = candidate_rows(cfg)
    cell_size = float(cfg["focus_cell_size_m"])
    buffer_m = float(cfg["tile_buffer_m"])
    res = float(cfg["raster_resolution_m"])
    tile_width = cell_size + 2 * buffer_m
    pixels = int(math.ceil(tile_width / res))
    rows = []
    for idx, cand in enumerate(candidates, start=1):
        cell_id = cand["cell_id"]
        paths = asset_paths(cfg, cell_id)
        rows.append(
            {
                "candidate_order": idx,
                "cell_id": cell_id,
                "focus_cell_size_m": cell_size,
                "tile_buffer_m": buffer_m,
                "tile_width_m": tile_width,
                "raster_resolution_m": res,
                "expected_tile_pixels_x": pixels,
                "expected_tile_pixels_y": pixels,
                "tile_spec_status": "RECOVERED_FROM_V12_N24_N150_CONVENTION",
                "tile_bounds_status": "PENDING_QGIS_OR_RASTERIO_DERIVATION_FROM_LOCKED_GRID",
                "focus_cell_geojson": slash(paths["focus_cell_geojson"]),
                "asset_folder": slash(paths["asset_folder"]),
                "convention_source": cfg["tile_spec_convention_source"],
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_rows(
        out / "b87b4_tile_spec_by_cell.csv",
        rows,
        [
            "candidate_order",
            "cell_id",
            "focus_cell_size_m",
            "tile_buffer_m",
            "tile_width_m",
            "raster_resolution_m",
            "expected_tile_pixels_x",
            "expected_tile_pixels_y",
            "tile_spec_status",
            "tile_bounds_status",
            "focus_cell_geojson",
            "asset_folder",
            "convention_source",
            "claim_boundary",
        ],
    )
    return rows


def write_materialization_plan(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    out = output_dir(cfg)
    scenario_rows = []
    task_rows = []
    for cand in candidate_rows(cfg):
        cell_id = cand["cell_id"]
        paths = asset_paths(cfg, cell_id)
        for scenario in cfg["expected_scenarios"]:
            cdsm = scenario_cdsm_path(paths, scenario)
            svf = scenario_svf_zip(paths, scenario)
            scenario_rows.append(
                {
                    "cell_id": cell_id,
                    "scenario": scenario,
                    "asset_folder": slash(paths["asset_folder"]),
                    "dsm_path": slash(paths["dsm"]),
                    "cdsm_path": slash(cdsm),
                    "dem_path": slash(paths["dem"]),
                    "wall_height_path": slash(paths["wall_height"]),
                    "wall_aspect_path": slash(paths["wall_aspect"]),
                    "svf_path_or_zip": slash(svf),
                    "asset_plan_status": "LOCAL_ONLY_PLANNED",
                    "svf_rule": "scenario_specific_svfs_zip_required",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
            for asset_name, asset_path in [
                ("focus_cell_geojson", paths["focus_cell_geojson"]),
                ("dsm_buildings_tile", paths["dsm"]),
                ("flat_dem_tile", paths["dem"]),
                ("scenario_cdsm_tile", cdsm),
                ("wall_height", paths["wall_height"]),
                ("wall_aspect", paths["wall_aspect"]),
                ("scenario_svf_svfs_zip", svf),
            ]:
                task_rows.append(
                    {
                        "cell_id": cell_id,
                        "scenario": scenario,
                        "task_name": asset_name,
                        "target_path": slash(asset_path),
                        "required_runtime": task_runtime(asset_name),
                        "planned_status": task_planned_status(asset_name),
                        "repo_write_allowed": "false",
                        "local_write_allowed": "true",
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                )
    write_rows(
        out / "b87b4_scenario_asset_plan.csv",
        scenario_rows,
        [
            "cell_id",
            "scenario",
            "asset_folder",
            "dsm_path",
            "cdsm_path",
            "dem_path",
            "wall_height_path",
            "wall_aspect_path",
            "svf_path_or_zip",
            "asset_plan_status",
            "svf_rule",
            "claim_boundary",
        ],
    )
    write_rows(
        out / "b87b4_materialization_task_plan.csv",
        task_rows,
        [
            "cell_id",
            "scenario",
            "task_name",
            "target_path",
            "required_runtime",
            "planned_status",
            "repo_write_allowed",
            "local_write_allowed",
            "claim_boundary",
        ],
    )
    return scenario_rows, task_rows


def task_runtime(asset_name: str) -> str:
    if asset_name == "focus_cell_geojson":
        return "stdlib_python"
    if asset_name == "scenario_svf_svfs_zip":
        return "qgis_umep_processing"
    if asset_name in {"wall_height", "wall_aspect"}:
        return "qgis_umep_wall_algorithm"
    return "rasterio_or_qgis_python"


def task_planned_status(asset_name: str) -> str:
    if asset_name == "focus_cell_geojson":
        return "CREATE_IN_CODEX_LOCAL_ONLY"
    if asset_name == "scenario_svf_svfs_zip":
        return "PENDING_QGIS_SVF_GENERATION"
    if asset_name in {"wall_height", "wall_aspect"}:
        return "PENDING_QGIS_WALL_PREPROCESS"
    return "CREATE_WITH_RASTERIO_IF_AVAILABLE_ELSE_QGIS"


def write_focus_cells(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    source_paths = source_path_map(cfg)
    grid_path = Path(source_paths["grid_geometry"])
    geo = json.loads(grid_path.read_text(encoding="utf-8-sig"))
    features = geo.get("features", [])
    by_cell = {str(feat.get("properties", {}).get("cell_id", "")): feat for feat in features}
    rows = []
    crs = geo.get("crs")
    for cand in candidate_rows(cfg):
        cell_id = cand["cell_id"]
        paths = asset_paths(cfg, cell_id)
        paths["asset_folder"].mkdir(parents=True, exist_ok=True)
        paths["svf_base_dir"].mkdir(parents=True, exist_ok=True)
        paths["svf_overhead_dir"].mkdir(parents=True, exist_ok=True)
        feature = by_cell.get(cell_id)
        if feature:
            collection: dict[str, Any] = {"type": "FeatureCollection", "features": [feature]}
            if crs:
                collection["crs"] = crs
            paths["focus_cell_geojson"].write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
            status = "CREATED_OR_REFRESHED"
            note = "focus cell vector copied from locked grid source"
        else:
            status = "MISSING_GRID_FEATURE"
            note = "cell_id not found in locked grid GeoJSON"
        rows.append(
            {
                "cell_id": cell_id,
                "asset": "focus_cell_geojson",
                "path": slash(paths["focus_cell_geojson"]),
                "status": status,
                "note": note,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def write_local_forcing_files(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    forcing_root = local_path(cfg, "local_forcing_root")
    forcing_root.mkdir(parents=True, exist_ok=True)
    source = resolve_repo_path(cfg, cfg["forcing_source_csv"])
    station = str(cfg.get("forcing_station_id", "S128"))
    slots = forcing_slots(cfg)
    weather_rows = read_rows(source)
    rows = []
    for slot in slots:
        hour = int(slot["hour_sgt"])
        out_dir = forcing_root / slot["forcing_day_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"b87c_{slot['forcing_day_id']}_{station}_h{hour:02d}.txt"
        weather = find_weather(weather_rows, station, slot["date"], hour)
        if weather is None:
            rows.append(
                {
                    "forcing_day_id": slot["forcing_day_id"],
                    "date": slot["date"],
                    "hour_sgt": hour,
                    "forcing_path": slash(out_path),
                    "status": "MISSING_WEATHER_ROW",
                    "station_id": station,
                    "note": "no matching forcing_source_csv row",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
            continue
        record = build_umep_record(weather, slot["date"], hour)
        line = " ".join(format_umep_value(record[col]) for col in UMEP_COLUMNS)
        out_path.write_text(f"{UMEP_HEADER}\n{line}\n{line}\n", encoding="utf-8")
        rows.append(
            {
                "forcing_day_id": slot["forcing_day_id"],
                "date": slot["date"],
                "hour_sgt": hour,
                "forcing_path": slash(out_path),
                "status": "CREATED_OR_REFRESHED",
                "station_id": station,
                "note": "single-hour two-row UMEP file generated locally from compact forecast CSV",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def find_weather(rows: list[dict[str, str]], station: str, date_text: str, hour: int) -> dict[str, str] | None:
    hour_text = f"{hour:02d}:"
    for row in rows:
        if str(row.get("station_id", "")) != station:
            continue
        time_text = str(row.get("time_sgt") or row.get("timestamp_sgt") or "")
        if date_text in time_text and f" {hour_text}" in time_text:
            return row
    return None


def number(row: dict[str, str], key: str, fallback: float = -999.0) -> float:
    try:
        value = row.get(key, "")
        return fallback if value == "" else float(value)
    except Exception:
        return fallback


def build_umep_record(row: dict[str, str], date_text: str, hour: int) -> dict[str, float | int]:
    dt = datetime.strptime(date_text, "%Y-%m-%d")
    wind = max(number(row, "wind_speed_10m", 0.5), 0.5)
    cloud = number(row, "cloud_cover", -999.0)
    return {
        "iy": dt.year,
        "id": date(dt.year, dt.month, dt.day).timetuple().tm_yday,
        "it": hour,
        "imin": 0,
        "qn": -999,
        "qh": -999,
        "qe": -999,
        "qs": -999,
        "qf": -999,
        "U": wind,
        "RH": number(row, "relative_humidity_2m"),
        "Tair": number(row, "temperature_2m"),
        "pres": 1010,
        "rain": number(row, "rain", 0.0),
        "kdown": number(row, "shortwave_radiation"),
        "snow": 0,
        "ldown": -999,
        "fcld": -999 if cloud == -999 else round(cloud / 100.0, 3),
        "wuh": -999,
        "xsmd": -999,
        "lai_hr": -999,
        "Kdiff": number(row, "diffuse_radiation"),
        "Kdir": number(row, "direct_radiation"),
        "Wd": 270,
    }


def format_umep_value(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{float(value):.3f}"


def try_python_raster_materialization(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    if not geospatial_ready():
        return []
    # Optional path for machines with rasterio/geopandas. The current Codex
    # runtime may not have these packages; QGIS runner remains the authoritative
    # fallback.
    import geopandas as gpd  # type: ignore
    import numpy as np  # type: ignore
    import rasterio  # type: ignore
    from rasterio.enums import Resampling  # type: ignore
    from rasterio.features import rasterize  # type: ignore
    from rasterio.transform import from_origin  # type: ignore
    from rasterio.warp import reproject  # type: ignore

    def write_raster(path: Path, arr: Any, transform: Any, crs: Any) -> None:
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

    def raster_to_bounds(src_path: Path, bounds: tuple[float, float, float, float], res: float, crs: str) -> tuple[Any, Any]:
        minx, miny, maxx, maxy = bounds
        width = int(math.ceil((maxx - minx) / res))
        height = int(math.ceil((maxy - miny) / res))
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

    source_paths = source_path_map(cfg)
    crs = str(cfg.get("working_crs", "EPSG:3414"))
    grid = gpd.read_file(source_paths["grid_geometry"]).to_crs(crs)
    grid["cell_id"] = grid["cell_id"].astype(str)
    overhead_path = Path(source_paths.get("overhead_vector", ""))
    overhead = gpd.read_file(overhead_path).to_crs(crs) if overhead_path.exists() else None
    res = float(cfg["raster_resolution_m"])
    buffer_m = float(cfg["tile_buffer_m"])
    building = Path(source_paths["dsm"])
    vegetation = Path(source_paths["cdsm_base_vegetation"])
    rows = []
    for cand in candidate_rows(cfg):
        cell_id = cand["cell_id"]
        match = grid[grid["cell_id"].eq(cell_id)]
        if match.empty:
            rows.append({"cell_id": cell_id, "status": "MISSING_GRID_FEATURE", "note": ""})
            continue
        paths = asset_paths(cfg, cell_id)
        focus = match.iloc[[0]].copy()
        tile_geom = focus.geometry.iloc[0].buffer(buffer_m)
        bounds = tile_geom.bounds
        b_arr, transform = raster_to_bounds(building, bounds, res, crs)
        v_arr, _ = raster_to_bounds(vegetation, bounds, res, crs)
        oh_arr = np.zeros_like(b_arr, dtype="float32")
        if overhead is not None and len(overhead):
            shapes = []
            for _, row in overhead[overhead.geometry.intersects(tile_geom)].iterrows():
                geom = row.geometry.intersection(tile_geom)
                if geom is not None and not geom.is_empty:
                    shapes.append((geom, infer_overhead_height(row)))
            if shapes:
                oh_arr = rasterize(shapes, out_shape=b_arr.shape, transform=transform, fill=0.0, dtype="float32")
        dem = np.zeros_like(b_arr, dtype="float32")
        write_raster(paths["dsm"], b_arr, transform, crs)
        write_raster(paths["dem"], dem, transform, crs)
        write_raster(paths["cdsm_base"], v_arr, transform, crs)
        write_raster(paths["overhead_canopy"], oh_arr, transform, crs)
        write_raster(paths["cdsm_overhead"], np.maximum(v_arr, oh_arr), transform, crs)
        focus.to_file(paths["focus_cell_geojson"], driver="GeoJSON")
        gpd.GeoDataFrame({"cell_id": [cell_id]}, geometry=[tile_geom], crs=crs).to_file(
            paths["tile_boundary_buffered_geojson"], driver="GeoJSON"
        )
        rows.append({"cell_id": cell_id, "status": "NON_SVF_RASTERS_CREATED", "note": "python_rasterio_path"})
    return rows


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
        try:
            val = row.get(col)
            if val is not None and not math.isnan(float(val)) and float(val) > 0:
                return float(val)
        except Exception:
            pass
    try:
        typ = str(row.get("overhead_type", "unknown_overhead")).lower()
    except Exception:
        typ = "unknown_overhead"
    return float(defaults.get(typ, defaults["unknown_overhead"]))


def run_materialization_driver(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    setup_local_roots(cfg)
    log_rows: list[dict[str, Any]] = []
    focus_rows = write_focus_cells(cfg)
    forcing_rows = write_local_forcing_files(cfg)
    raster_rows = try_python_raster_materialization(cfg) if cfg.get("allow_local_raster_write", False) else []
    raster_created = {row["cell_id"] for row in raster_rows if row.get("status") == "NON_SVF_RASTERS_CREATED"}
    for row in focus_rows:
        log_rows.append(
            {
                "cell_id": row["cell_id"],
                "scenario": "all",
                "task_name": row["asset"],
                "target_path": row["path"],
                "status": row["status"],
                "runtime_used": "stdlib_python",
                "note": row["note"],
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    for row in forcing_rows:
        log_rows.append(
            {
                "cell_id": "all",
                "scenario": "all",
                "task_name": "local_umep_forcing",
                "target_path": row["forcing_path"],
                "status": row["status"],
                "runtime_used": "stdlib_python",
                "note": row["note"],
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    for cand in candidate_rows(cfg):
        cell_id = cand["cell_id"]
        paths = asset_paths(cfg, cell_id)
        for name, path in [
            ("dsm_buildings_tile", paths["dsm"]),
            ("flat_dem_tile", paths["dem"]),
            ("cdsm_base_vegetation_tile", paths["cdsm_base"]),
            ("overhead_canopy_tile", paths["overhead_canopy"]),
            ("cdsm_overhead_as_canopy_tile", paths["cdsm_overhead"]),
        ]:
            if cell_id in raster_created and path.exists():
                status = "CREATED_BY_PYTHON_RASTERIO"
                runtime = "python_rasterio"
                note = ""
            elif path.exists():
                status = "EXISTS_LOCAL"
                runtime = "audit"
                note = ""
            else:
                status = "PENDING_QGIS_RASTER_MATERIALIZATION"
                runtime = "qgis_runner_required"
                note = "Codex runtime lacks rasterio/geopandas or raster materialization was not safe here"
            log_rows.append(
                {
                    "cell_id": cell_id,
                    "scenario": "all" if "overhead" not in name else "overhead_as_canopy",
                    "task_name": name,
                    "target_path": slash(path),
                    "status": status,
                    "runtime_used": runtime,
                    "note": note,
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
        for scenario, svf_path in [
            ("base", paths["svf_base_zip"]),
            ("overhead_as_canopy", paths["svf_overhead_zip"]),
        ]:
            log_rows.append(
                {
                    "cell_id": cell_id,
                    "scenario": scenario,
                    "task_name": "scenario_svf_svfs_zip",
                    "target_path": slash(svf_path),
                    "status": "READY" if svf_path.exists() else "PENDING_QGIS_SVF_GENERATION",
                    "runtime_used": "qgis_umep_processing",
                    "note": "Do not fabricate svfs.zip from full-AOI SVF",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    write_rows(
        out / "b87b4_materialization_execution_log.csv",
        log_rows,
        ["cell_id", "scenario", "task_name", "target_path", "status", "runtime_used", "note", "claim_boundary"],
    )
    write_materialization_audit(cfg)
    return log_rows


def asset_inventory_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for cand in candidate_rows(cfg):
        cell_id = cand["cell_id"]
        paths = asset_paths(cfg, cell_id)
        asset_defs = [
            ("focus_cell_geojson", "vector", paths["focus_cell_geojson"], "all"),
            ("tile_boundary_buffered_geojson", "vector", paths["tile_boundary_buffered_geojson"], "all"),
            ("dsm_buildings_tile", "raster", paths["dsm"], "all"),
            ("flat_dem_tile", "raster", paths["dem"], "all"),
            ("cdsm_base_vegetation_tile", "raster", paths["cdsm_base"], "base"),
            ("overhead_canopy_tile", "raster", paths["overhead_canopy"], "overhead_as_canopy"),
            ("cdsm_overhead_as_canopy_tile", "raster", paths["cdsm_overhead"], "overhead_as_canopy"),
            ("wall_height", "raster", paths["wall_height"], "all"),
            ("wall_aspect", "raster", paths["wall_aspect"], "all"),
            ("svfs_zip_base", "svf_zip", paths["svf_base_zip"], "base"),
            ("svfs_zip_overhead_as_canopy", "svf_zip", paths["svf_overhead_zip"], "overhead_as_canopy"),
        ]
        for asset_name, asset_type, path, scenario in asset_defs:
            meta = path_metadata(path)
            rows.append(
                {
                    "cell_id": cell_id,
                    "scenario": scenario,
                    "asset_name": asset_name,
                    "asset_type": asset_type,
                    "path": slash(path),
                    "exists": meta["exists"],
                    "size_bytes": meta["size_bytes"],
                    "local_only": "true",
                    "repo_side_forbidden": "true" if asset_type in {"raster", "svf_zip"} else "false",
                    "status": "READY" if meta["exists"] == "true" else missing_asset_status(asset_name),
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return rows


def missing_asset_status(asset_name: str) -> str:
    if asset_name.startswith("svfs_zip"):
        return "PENDING_QGIS_SVF_GENERATION"
    if asset_name in {"wall_height", "wall_aspect"}:
        return "PENDING_QGIS_WALL_PREPROCESS"
    if asset_name.endswith("geojson"):
        return "MISSING_VECTOR_ASSET"
    return "PENDING_QGIS_OR_RASTERIO_MATERIALIZATION"


def readiness_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for cand in candidate_rows(cfg):
        cell_id = cand["cell_id"]
        paths = asset_paths(cfg, cell_id)
        focus_ready = paths["focus_cell_geojson"].exists()
        dsm_ready = paths["dsm"].exists()
        dem_ready = paths["dem"].exists()
        base_cdsm_ready = paths["cdsm_base"].exists()
        overhead_cdsm_ready = paths["cdsm_overhead"].exists()
        wall_ready = paths["wall_height"].exists() and paths["wall_aspect"].exists()
        base_svf_ready = paths["svf_base_zip"].exists()
        overhead_svf_ready = paths["svf_overhead_zip"].exists()
        base_ready = all([focus_ready, dsm_ready, dem_ready, base_cdsm_ready, wall_ready, base_svf_ready])
        overhead_ready = all([focus_ready, dsm_ready, dem_ready, overhead_cdsm_ready, wall_ready, overhead_svf_ready])
        rows.append(
            {
                "cell_id": cell_id,
                "focus_cell_ready": bool_text(focus_ready),
                "dsm_ready": bool_text(dsm_ready),
                "dem_ready": bool_text(dem_ready),
                "base_cdsm_ready": bool_text(base_cdsm_ready),
                "overhead_cdsm_ready": bool_text(overhead_cdsm_ready),
                "wall_height_aspect_ready": bool_text(wall_ready),
                "base_svf_ready": bool_text(base_svf_ready),
                "overhead_svf_ready": bool_text(overhead_svf_ready),
                "base_asset_ready": bool_text(base_ready),
                "overhead_asset_ready": bool_text(overhead_ready),
                "cell_materialization_status": cell_status(base_ready, overhead_ready, dsm_ready, dem_ready, base_cdsm_ready, overhead_cdsm_ready),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def cell_status(base_ready: bool, overhead_ready: bool, dsm_ready: bool, dem_ready: bool, base_cdsm_ready: bool, overhead_cdsm_ready: bool) -> str:
    if base_ready and overhead_ready:
        return "READY_FOR_B87C_RUN"
    if dsm_ready and dem_ready and base_cdsm_ready and overhead_cdsm_ready:
        return "PENDING_QGIS_WALL_AND_SVF_GENERATION"
    return "PENDING_QGIS_RASTER_AND_SVF_MATERIALIZATION"


def svf_status_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for cand in candidate_rows(cfg):
        cell_id = cand["cell_id"]
        paths = asset_paths(cfg, cell_id)
        for scenario, svf_path in [("base", paths["svf_base_zip"]), ("overhead_as_canopy", paths["svf_overhead_zip"])]:
            rows.append(
                {
                    "cell_id": cell_id,
                    "scenario": scenario,
                    "svf_path_or_zip": slash(svf_path),
                    "exists": bool_text(svf_path.exists()),
                    "status": "READY" if svf_path.exists() else "PENDING_QGIS_SVF_GENERATION",
                    "svf_rule": "scenario_specific; overhead_as_canopy must not reuse base SVF",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return rows


def blocker_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    deps = geospatial_dependency_status()
    rows = []
    missing = [dep for dep, status in deps.items() if status == "missing"]
    readiness = readiness_rows(cfg)
    svf = svf_status_rows(cfg)
    if missing:
        rows.append(
            {
                "blocker_id": "PYTHON_GEOSPATIAL_DEPS_MISSING",
                "severity": "PENDING_QGIS_ACTION",
                "status": "OPEN",
                "scope": "non_svf_raster_materialization_in_codex",
                "details": "Missing optional packages: " + ",".join(missing),
                "resolution_path": "Run scripts/qgis/v12_b87b4_qgis_svf_materialization_runner.py from QGIS Desktop Python Console.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    if any(row["status"] != "READY" for row in svf):
        rows.append(
            {
                "blocker_id": "QGIS_UMEP_SVF_REQUIRED",
                "severity": "PENDING_QGIS_ACTION",
                "status": "OPEN",
                "scope": "scenario_specific_svfs_zip",
                "details": "At least one scenario-specific svfs.zip is missing.",
                "resolution_path": "Run the QGIS SVF materialization stage; do not reuse base full-AOI SVF for overhead.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    if any(row["cell_materialization_status"] == "PENDING_QGIS_RASTER_AND_SVF_MATERIALIZATION" for row in readiness):
        rows.append(
            {
                "blocker_id": "LOCAL_NON_SVF_RASTERS_PENDING",
                "severity": "PENDING_QGIS_ACTION",
                "status": "OPEN",
                "scope": "dsm_cdsm_dem_wall_assets",
                "details": "One or more local raster/wall assets are not present under C:/OpenHeat-local.",
                "resolution_path": "Run QGIS materialization runner before SOLWEIG runner.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    if not rows:
        rows.append(
            {
                "blocker_id": "NONE",
                "severity": "INFO",
                "status": "CLOSED",
                "scope": "all",
                "details": "No open materialization blockers detected.",
                "resolution_path": "",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def write_materialization_audit(cfg: dict[str, Any]) -> None:
    out = output_dir(cfg)
    inventory = asset_inventory_rows(cfg)
    readiness = readiness_rows(cfg)
    svf = svf_status_rows(cfg)
    blockers = blocker_rows(cfg)
    write_rows(
        out / "b87b4_materialized_asset_inventory.csv",
        inventory,
        [
            "cell_id",
            "scenario",
            "asset_name",
            "asset_type",
            "path",
            "exists",
            "size_bytes",
            "local_only",
            "repo_side_forbidden",
            "status",
            "claim_boundary",
        ],
    )
    write_rows(
        out / "b87b4_materialized_asset_readiness_by_cell.csv",
        readiness,
        [
            "cell_id",
            "focus_cell_ready",
            "dsm_ready",
            "dem_ready",
            "base_cdsm_ready",
            "overhead_cdsm_ready",
            "wall_height_aspect_ready",
            "base_svf_ready",
            "overhead_svf_ready",
            "base_asset_ready",
            "overhead_asset_ready",
            "cell_materialization_status",
            "claim_boundary",
        ],
    )
    write_rows(
        out / "b87b4_svf_materialization_status.csv",
        svf,
        ["cell_id", "scenario", "svf_path_or_zip", "exists", "status", "svf_rule", "claim_boundary"],
    )
    write_rows(
        out / "b87b4_materialization_blocker_register.csv",
        blockers,
        ["blocker_id", "severity", "status", "scope", "details", "resolution_path", "claim_boundary"],
    )


def build_manifest_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = {row["cell_id"]: row for row in readiness_rows(cfg)}
    slots = forcing_slots(cfg)
    rows = []
    for cand in candidate_rows(cfg):
        cell_id = cand["cell_id"]
        paths = asset_paths(cfg, cell_id)
        cell_readiness = readiness[cell_id]
        for slot in slots:
            for scenario in cfg["expected_scenarios"]:
                output_dir_path = local_path(cfg, "local_output_root") / slot["forcing_day_id"] / cell_id / scenario / f"h{int(slot['hour_sgt']):02d}"
                cdsm = scenario_cdsm_path(paths, scenario)
                svf_zip = scenario_svf_zip(paths, scenario)
                ready = cell_readiness["base_asset_ready"] == "true" if scenario == "base" else cell_readiness["overhead_asset_ready"] == "true"
                if ready:
                    mat_status = "READY"
                    run_status = "pending_run"
                elif all([paths["dsm"].exists(), paths["dem"].exists(), cdsm.exists(), paths["wall_height"].exists(), paths["wall_aspect"].exists()]) and not svf_zip.exists():
                    mat_status = "PENDING_QGIS_SVF_GENERATION"
                    run_status = "not_ready"
                else:
                    mat_status = "PENDING_QGIS_RASTER_AND_SVF_MATERIALIZATION"
                    run_status = "not_ready"
                run_id = f"B87C_{slot['forcing_day_id']}_{cell_id}_{scenario}_h{int(slot['hour_sgt']):02d}"
                rows.append(
                    {
                        "run_id": run_id,
                        "cell_id": cell_id,
                        "forcing_day_id": slot["forcing_day_id"],
                        "date": slot["date"],
                        "hour_sgt": int(slot["hour_sgt"]),
                        "scenario": scenario,
                        "asset_folder": slash(paths["asset_folder"]),
                        "dsm_path": slash(paths["dsm"]),
                        "cdsm_path": slash(cdsm),
                        "dem_path": slash(paths["dem"]),
                        "svf_path_or_zip": slash(svf_zip),
                        "output_dir": slash(output_dir_path),
                        "expected_tmrt_path": slash(output_dir_path / "Tmrt_average.tif"),
                        "qgis_algorithm_id": cfg["qgis_solweig_algorithm_id"],
                        "run_status_initial": run_status,
                        "resume_key": f"{cell_id}|{slot['forcing_day_id']}|h{int(slot['hour_sgt']):02d}|{scenario}",
                        "materialization_status": mat_status,
                        "notes": "SOLWEIG Tmrt only; no WBGT/risk/AOI/B9; local-only paths may reference rasters outside Git.",
                    }
                )
    return rows


def write_manifest(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    rows = build_manifest_rows(cfg)
    fields = [
        "run_id",
        "cell_id",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "asset_folder",
        "dsm_path",
        "cdsm_path",
        "dem_path",
        "svf_path_or_zip",
        "output_dir",
        "expected_tmrt_path",
        "qgis_algorithm_id",
        "run_status_initial",
        "resume_key",
        "materialization_status",
        "notes",
    ]
    write_rows(out / "b87c_manifest.csv", rows, fields)
    write_run_batches(cfg, rows)
    write_resume_strategy(cfg, rows)
    write_manifest_audit(cfg, rows)
    write_qgis_instructions(cfg)
    write_postrun_package_files(cfg)
    return rows


def write_run_batches(cfg: dict[str, Any], manifest_rows: list[dict[str, Any]]) -> None:
    out = output_dir(cfg)
    candidates = [row["cell_id"] for row in candidate_rows(cfg)]
    rows = []
    for batch in cfg["run_batches"]:
        count = int(batch["cell_count"])
        cells = candidates[:count]
        run_count = sum(1 for row in manifest_rows if row["cell_id"] in set(cells))
        rows.append(
            {
                "stage": batch["stage"],
                "cell_count": count,
                "run_count": run_count,
                "expected_run_count": batch["run_count"],
                "cell_selection_rule": f"first_{count}_candidate_order",
                "cell_ids_preview": ",".join(cells[:10]) + ("..." if len(cells) > 10 else ""),
                "status": "PASS" if run_count == int(batch["run_count"]) else "COUNT_MISMATCH",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_rows(out / "b87c_run_batches.csv", rows, ["stage", "cell_count", "run_count", "expected_run_count", "cell_selection_rule", "cell_ids_preview", "status", "claim_boundary"])


def write_resume_strategy(cfg: dict[str, Any], manifest_rows: list[dict[str, Any]]) -> None:
    out = output_dir(cfg)
    rows = [
        {
            "resume_rule": "skip_completed_tmrt",
            "field_or_path": "expected_tmrt_path",
            "action": "Runner skips when readable Tmrt_average.tif exists unless SKIP_COMPLETED is false.",
            "default": "true",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "resume_rule": "stable_resume_key",
            "field_or_path": "resume_key",
            "action": "Use cell_id|forcing_day_id|hour|scenario for deterministic restart and failure grouping.",
            "default": "required",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "resume_rule": "stage_filter",
            "field_or_path": "STAGE",
            "action": "Run smoke, pilot_5, pilot_20, or full_150 by candidate order.",
            "default": "smoke in repo runner; user may set full_150 in local copy",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "resume_rule": "not_ready_guard",
            "field_or_path": "materialization_status",
            "action": "Refuse not_ready rows unless FORCE_PARTIAL is explicitly enabled in the local runner.",
            "default": "FORCE_PARTIAL=false",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    write_rows(out / "b87c_resume_strategy.csv", rows, ["resume_rule", "field_or_path", "action", "default", "claim_boundary"])


def write_manifest_audit(cfg: dict[str, Any], manifest_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    rows = manifest_rows or read_rows(out / "b87c_manifest.csv")
    counts = Counter(row["scenario"] for row in rows)
    cells = {row["cell_id"] for row in rows}
    days = {row["forcing_day_id"] for row in rows}
    hours = {row["hour_sgt"] for row in rows}
    not_ready = sum(1 for row in rows if str(row.get("run_status_initial")) == "not_ready")
    repo_heavy = [
        row
        for row in rows
        for key in ["dsm_path", "cdsm_path", "dem_path", "svf_path_or_zip", "output_dir", "expected_tmrt_path"]
        if path_inside_repo(resolve_repo_path(cfg, row[key]))
    ]
    audit_rows = [
        audit_row("manifest_row_count", len(rows), cfg["expected_total_runs"], len(rows) == int(cfg["expected_total_runs"])),
        audit_row("candidate_count", len(cells), cfg["expected_new_candidate_count"], len(cells) == int(cfg["expected_new_candidate_count"])),
        audit_row("forcing_day_count", len(days), cfg["expected_forcing_days"], len(days) == int(cfg["expected_forcing_days"])),
        audit_row("hour_count", len(hours), cfg["expected_hours_per_day"], len(hours) == int(cfg["expected_hours_per_day"])),
        audit_row("base_run_count", counts.get("base", 0), 1500, counts.get("base", 0) == 1500),
        audit_row("overhead_run_count", counts.get("overhead_as_canopy", 0), 1500, counts.get("overhead_as_canopy", 0) == 1500),
        audit_row("not_ready_rows", not_ready, 0, not_ready == 0, "Rows may be not_ready until QGIS materialization has run."),
        audit_row("repo_heavy_path_references", len(repo_heavy), 0, len(repo_heavy) == 0, "Manifest must reference local-only heavy paths."),
    ]
    write_rows(out / "b87c_manifest_audit.csv", audit_rows, ["check_name", "observed", "expected", "status", "note", "claim_boundary"])
    return audit_rows


def path_inside_repo(path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(repo_root().resolve())
    except Exception:
        return False


def audit_row(name: str, observed: Any, expected: Any, passed: bool, note: str = "") -> dict[str, Any]:
    return {
        "check_name": name,
        "observed": observed,
        "expected": expected,
        "status": "PASS" if passed else "REVIEW",
        "note": note,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def localize_runners(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    setup_local_roots(cfg)
    runner_root = local_path(cfg, "local_runner_root")
    manifest_root = local_path(cfg, "local_manifest_root")
    runner_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    rows = []
    copies = [
        (repo_root() / "scripts/qgis/v12_b87b4_qgis_svf_materialization_runner.py", runner_root / "v12_b87b4_qgis_svf_materialization_runner_LOCAL.py"),
        (repo_root() / "scripts/qgis/v12_b87c_qgis_solweig_n300_runner.py", runner_root / "v12_b87c_qgis_solweig_n300_runner_LOCAL.py"),
    ]
    for src, dst in copies:
        text = src.read_text(encoding="utf-8")
        text = text.replace("LOCAL_CONTEXT = False", "LOCAL_CONTEXT = True")
        text = text.replace("RUN_ENABLED = False", "RUN_ENABLED = False")
        text = text.replace("DRY_RUN = True", "DRY_RUN = True")
        dst.write_text(text, encoding="utf-8")
        rows.append(
            {
                "runner_item": dst.name,
                "repo_source": slash(src),
                "local_path": slash(dst),
                "status": "LOCAL_COPY_CREATED",
                "run_enabled_default": "false",
                "dry_run_default": "true",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    for src, name in [
        (resolve_repo_path(cfg, "configs/v12/systemb_b87b4_b87c_materialization_package.yaml"), "systemb_b87b4_b87c_materialization_package.local.yaml"),
        (out / "b87c_manifest.csv", "b87c_manifest.local.csv"),
        (out / "b87c_qgis_console_execution_snippet.py", "b87c_qgis_console_execution_snippet.py"),
    ]:
        dst = manifest_root / name if name.endswith(".csv") or name.endswith(".yaml") else runner_root / name
        shutil.copyfile(src, dst)
        rows.append(
            {
                "runner_item": name,
                "repo_source": slash(src),
                "local_path": slash(dst),
                "status": "LOCAL_COPY_CREATED",
                "run_enabled_default": "",
                "dry_run_default": "",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_rows(
        out / "b87c_local_runner_inventory.csv",
        rows,
        ["runner_item", "repo_source", "local_path", "status", "run_enabled_default", "dry_run_default", "claim_boundary"],
    )
    return rows


def write_qgis_instructions(cfg: dict[str, Any]) -> None:
    out = output_dir(cfg)
    snippet = f"""from pathlib import Path
import os
import sys

runner = Path(r"{local_path(cfg, 'local_runner_root') / 'v12_b87b4_qgis_svf_materialization_runner_LOCAL.py'}")
code = runner.read_text(encoding="utf-8-sig")
globals()["__file__"] = str(runner)
sys.argv = [str(runner)]
os.chdir(str(runner.parent))
exec(compile(code, str(runner), "exec"), globals())
"""
    write_text(out / "b87c_qgis_console_execution_snippet.py", snippet)
    instructions = f"""# B87C QGIS execution instructions

Status: package created, SOLWEIG not run by Codex.

1. Run `scripts/v12_b87c_runner_localizer.py --config configs/v12/systemb_b87b4_b87c_materialization_package.yaml` if the local runner copies need refreshing.
2. Open QGIS Desktop with UMEP installed.
3. In the QGIS Python Console, paste the snippet from `b87c_qgis_console_execution_snippet.py`.
4. First run the local materialization runner:
   `{local_path(cfg, 'local_runner_root') / 'v12_b87b4_qgis_svf_materialization_runner_LOCAL.py'}`
5. Keep `DRY_RUN=True` for the first pass. Then set `RUN_ENABLED=True` and `DRY_RUN=False` inside the local copy.
6. After materialization, re-run `scripts/v12_b87c_manifest_builder.py` and then `scripts/v12_b87c_runner_localizer.py` so ready/not_ready statuses and the local manifest copy refresh.
7. Run `scripts/v12_b87c_manifest_audit.py` and confirm there are no `not_ready` rows.
8. Run the local SOLWEIG runner:
   `{local_path(cfg, 'local_runner_root') / 'v12_b87c_qgis_solweig_n300_runner_LOCAL.py'}`
9. Use stages in order: `smoke`, `pilot_5`, `pilot_20`, then `full_150`.

Safety boundaries:

- Local-only raster/SVF writes under `{cfg['local_root']}` only.
- No repo raster writes.
- No AOI/B9/WBGT/risk/hazard/exposure/vulnerability outputs.
- `overhead_as_canopy` must use its own `svfs.zip`; do not reuse base SVF.
"""
    write_text(out / "b87c_qgis_execution_instructions.md", instructions)


def write_postrun_package_files(cfg: dict[str, Any]) -> None:
    out = output_dir(cfg)
    qa_rows = [
        ("manifest_row_count", "b87c_manifest.csv", "expect 3000 rows"),
        ("run_log_status_counts", "local run log", "success/skipped/failed counts"),
        ("missing_tmrt_outputs", "expected_tmrt_path", "list missing outputs"),
        ("per_cell_scenario_counts", "manifest + outputs", "expect 20 runs per cell"),
        ("local_storage_summary", "C:/OpenHeat-local", "summarise local-only size; do not copy rasters"),
        ("git_hygiene", "git status", "no repo-side heavy files"),
    ]
    write_rows(
        out / "b87c_postrun_qa_plan.csv",
        [
            {"qa_check": a, "source": b, "expected": c, "claim_boundary": CLAIM_BOUNDARY}
            for a, b, c in qa_rows
        ],
        ["qa_check", "source", "expected", "claim_boundary"],
    )
    schema_rows = [
        ("run_id", "string", "B87C run id"),
        ("cell_id", "string", "TP_xxxx"),
        ("forcing_day_id", "string", "FD01/FD02 forcing day id"),
        ("date", "YYYY-MM-DD", "local SGT date"),
        ("hour_sgt", "integer", "10/12/13/15/16"),
        ("scenario", "string", "base or overhead_as_canopy"),
        ("expected_tmrt_path", "path", "local Tmrt_average.tif"),
        ("status", "string", "success/skipped_completed/failed_*"),
        ("error_message", "string", "runner error text"),
    ]
    write_rows(
        out / "b87c_expected_outputs_schema.csv",
        [{"column": a, "type": b, "description": c, "claim_boundary": CLAIM_BOUNDARY} for a, b, c in schema_rows],
        ["column", "type", "description", "claim_boundary"],
    )
    ps1 = f"""param(
  [string]$LocalRoot = "{cfg['local_root']}",
  [string]$RepoPacketDir = "{slash(out / 'postrun_review_packet')}"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $RepoPacketDir | Out-Null
Copy-Item -Force "{slash(out / 'b87c_manifest.csv')}" (Join-Path $RepoPacketDir "b87c_manifest.csv")
Copy-Item -Force "{slash(out / 'b87c_manifest_audit.csv')}" (Join-Path $RepoPacketDir "b87c_manifest_audit.csv")
Get-ChildItem -Path (Join-Path $LocalRoot "run_logs") -Filter "*.csv" -ErrorAction SilentlyContinue |
  Copy-Item -Destination $RepoPacketDir -Force
Write-Host "Review packet refreshed at $RepoPacketDir"
Write-Host "No rasters or svfs.zip are copied by this script."
"""
    write_text(out / "b87c_postrun_packet_script.ps1", ps1)
    write_rows(
        out / "b87c_git_hygiene_guard.csv",
        git_guard_rows(),
        ["guard_item", "pattern", "status", "observed", "note", "claim_boundary"],
    )
    write_text(
        out / "b87c_codex_prompt_POSTRUN_QA.md",
        "# Codex prompt: B87C postrun QA\n\nRun postrun QA on compact B87C logs and manifest only. Do not copy rasters or svfs.zip into Git. Report run counts, missing Tmrt outputs, failure signatures, local storage summary, and claim boundaries.\n",
    )
    write_text(
        out / "b87c_codex_prompt_B87D_label_integration.md",
        "# Codex prompt: B87D label integration\n\nIntegrate completed B87C SOLWEIG Tmrt outputs as System B labels only after postrun QA passes. Do not create WBGT/risk/AOI/B9 outputs and do not claim observed truth or causal feature importance.\n",
    )


def git_guard_rows() -> list[dict[str, Any]]:
    # This guard is repo-path based; it is intentionally compact and does not
    # inspect local-only C:/OpenHeat-local assets.
    forbidden = [
        ("repo_raster_ext", "*.tif/*.tiff/*.vrt/*.asc/*.img/*.nc/*.grib/svfs.zip"),
        ("repo_data_solweig", "data/solweig"),
        ("repo_data_rasters", "data/rasters"),
        ("repo_data_archive", "data/archive"),
        ("forecast_live_hourly_csv", "outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv"),
    ]
    return [
        {
            "guard_item": name,
            "pattern": pattern,
            "status": "CHECK_WITH_GIT_STATUS",
            "observed": "",
            "note": "Forbidden for new/staged lane files; local-only assets belong under C:/OpenHeat-local.",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for name, pattern in forbidden
    ]


def write_readiness_decision(cfg: dict[str, Any]) -> str:
    out = output_dir(cfg)
    readiness = readiness_rows(cfg)
    manifest_rows = read_rows(out / "b87c_manifest.csv") if (out / "b87c_manifest.csv").exists() else []
    runner_inventory = read_rows(out / "b87c_local_runner_inventory.csv") if (out / "b87c_local_runner_inventory.csv").exists() else []
    base_ready = sum(1 for row in readiness if row["base_asset_ready"] == "true")
    overhead_ready = sum(1 for row in readiness if row["overhead_asset_ready"] == "true")
    focus_ready = sum(1 for row in readiness if row["focus_cell_ready"] == "true")
    svf_ready = sum(
        1
        for row in svf_status_rows(cfg)
        if row["status"] == "READY"
    )
    if base_ready == 150 and overhead_ready == 150 and len(manifest_rows) == 3000 and runner_inventory:
        status = "B87B4_MATERIALIZATION_COMPLETE_READY_FOR_B87C_RUN"
    elif focus_ready == 150 and len(manifest_rows) == 3000 and runner_inventory:
        status = "B87B4_DIAGNOSTIC_ONLY"
    elif len(manifest_rows) == 3000 and runner_inventory:
        status = "B87C_PACKAGE_READY_NOT_RUN"
    else:
        status = "B87B4_BLOCKED_ASSET_CREATION"
    matrix = [
        ("source_lock", "PASS", "B8.7b.3 source lock loaded"),
        ("candidate_count", "PASS" if len(readiness) == 150 else "REVIEW", str(len(readiness))),
        ("focus_cell_vectors", "PASS" if focus_ready == 150 else "REVIEW", str(focus_ready)),
        ("base_asset_ready_cells", "PASS" if base_ready == 150 else "PENDING_QGIS", str(base_ready)),
        ("overhead_asset_ready_cells", "PASS" if overhead_ready == 150 else "PENDING_QGIS", str(overhead_ready)),
        ("svf_ready_cell_scenarios", "PASS" if svf_ready == 300 else "PENDING_QGIS", str(svf_ready)),
        ("manifest_rows", "PASS" if len(manifest_rows) == 3000 else "REVIEW", str(len(manifest_rows))),
        ("runner_localizer", "PASS" if runner_inventory else "REVIEW", str(len(runner_inventory))),
        ("aoi_preflight", "AOI_PREFLIGHT_BLOCKED", "not in this lane"),
        ("b9", "B9_BLOCKED", "not in this lane"),
    ]
    write_rows(
        out / "b87c_readiness_matrix.csv",
        [{"item": a, "status": b, "detail": c, "claim_boundary": CLAIM_BOUNDARY} for a, b, c in matrix],
        ["item", "status", "detail", "claim_boundary"],
    )
    next_rows = [
        {
            "decision_status": status,
            "meaning": "Current primary lane decision",
            "recommended_next_action": recommended_action(status),
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "decision_status": "AOI_PREFLIGHT_BLOCKED",
            "meaning": "AOI-wide prediction is out of scope",
            "recommended_next_action": "Do not start AOI/B9 in this lane.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "decision_status": "B9_BLOCKED",
            "meaning": "B9 integration is out of scope",
            "recommended_next_action": "Wait until B87C postrun QA passes.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    write_rows(out / "b87c_next_lane_decision_matrix.csv", next_rows, ["decision_status", "meaning", "recommended_next_action", "claim_boundary"])
    write_status_docs(cfg, status)
    return status


def recommended_action(status: str) -> str:
    if status == "B87B4_MATERIALIZATION_COMPLETE_READY_FOR_B87C_RUN":
        return "Run QGIS SOLWEIG runner smoke, pilot_5, pilot_20, then full_150."
    if status == "B87B4_DIAGNOSTIC_ONLY":
        return "Run QGIS materialization runner first; then re-audit manifest readiness."
    if status == "B87C_PACKAGE_READY_NOT_RUN":
        return "Review not_ready rows and runner inventory before QGIS execution."
    return "Review blocker register before proceeding."


def write_status_docs(cfg: dict[str, Any], status: str) -> None:
    out = output_dir(cfg)
    source_summary = read_rows(out / "b87b4_source_lock_summary.csv") if (out / "b87b4_source_lock_summary.csv").exists() else []
    readiness = readiness_rows(cfg)
    manifest_rows = read_rows(out / "b87c_manifest.csv") if (out / "b87c_manifest.csv").exists() else []
    focus_ready = sum(1 for row in readiness if row["focus_cell_ready"] == "true")
    base_ready = sum(1 for row in readiness if row["base_asset_ready"] == "true")
    overhead_ready = sum(1 for row in readiness if row["overhead_asset_ready"] == "true")
    svf_ready = sum(1 for row in svf_status_rows(cfg) if row["status"] == "READY")
    headline = source_lock_headline(source_summary)
    status_md = f"""# B8.7b.4/B87C Status

Status: `{status}`

- source lock headline: {headline}
- new candidate count: `{len(readiness)}`
- local asset root: `{cfg['local_asset_root']}`
- materialized focus-cell count: `{focus_ready}`
- base asset readiness count: `{base_ready}`
- overhead asset readiness count: `{overhead_ready}`
- SVF/svfs readiness count: `{svf_ready}/300`
- manifest row count: `{len(manifest_rows)}`
- AOI/B9 status: `AOI_PREFLIGHT_BLOCKED`; `B9_BLOCKED`

Claim boundaries: local-only raster writes are allowed under `C:/OpenHeat-local` only; no repo raster writes; no AOI/B9; no WBGT/risk; no observed truth; no causal claims.
"""
    write_text(out / "B8_7B4_B87C_STATUS.md", status_md)
    report = build_report(cfg, status, headline, readiness, manifest_rows)
    write_text(out / "b87b4_b87c_report.md", report)


def source_lock_headline(rows: list[dict[str, str]]) -> str:
    bits = []
    for key in ["dsm", "cdsm_base_vegetation", "grid_geometry", "svf_base_full", "svf_overhead"]:
        match = [row for row in rows if row.get("source_kind") == key]
        if match:
            bits.append(f"{key}={match[0].get('lock_status')}")
    return "; ".join(bits)


def build_report(cfg: dict[str, Any], status: str, headline: str, readiness: list[dict[str, str]], manifest_rows: list[dict[str, str]]) -> str:
    base_ready = sum(1 for row in readiness if row["base_asset_ready"] == "true")
    overhead_ready = sum(1 for row in readiness if row["overhead_asset_ready"] == "true")
    svf_ready = sum(1 for row in svf_status_rows(cfg) if row["status"] == "READY")
    runner_inv = read_rows(output_dir(cfg) / "b87c_local_runner_inventory.csv") if (output_dir(cfg) / "b87c_local_runner_inventory.csv").exists() else []
    return f"""# B8.7b.4 + B87C Materialization Execution Package Report

Status: `{status}`

## 1. Why this follows B8.7b.3

B8.7b.3 locked the full-AOI raster/vector sources and concluded that B87C was blocked until local per-cell assets and an execution package existed. This lane converts that source lock into a local-only asset plan, manifest, QGIS materialization runner, SOLWEIG runner, resume logic, and postrun QA packet.

## 2. Source lock summary

{headline}

## 3. Materialized local asset readiness

- Candidate cells: `{len(readiness)}`
- Local asset root: `{cfg['local_asset_root']}`
- Base ready cells: `{base_ready}`
- Overhead ready cells: `{overhead_ready}`
- Current non-ready assets are documented in `b87b4_materialization_blocker_register.csv`.

## 4. SVF materialization status

SVF/svfs.zip ready cell-scenarios: `{svf_ready}/300`. Base and overhead SVF are scenario-specific. The overhead scenario must not reuse base SVF.

## 5. Manifest status

`b87c_manifest.csv` rows: `{len(manifest_rows)}`. Rows remain `not_ready` until required local rasters, wall rasters, and scenario-specific `svfs.zip` exist.

## 6. Runner/localizer status

Local runner inventory rows: `{len(runner_inv)}`. Repo runners default to `RUN_ENABLED=False` and `DRY_RUN=True`; local copies are created under `{cfg['local_runner_root']}`.

## 7. QGIS full-stage execution

Run QGIS materialization first, then rebuild the manifest and localize the refreshed manifest copy. After manifest audit shows no `not_ready` rows, run SOLWEIG stages in order: `smoke`, `pilot_5`, `pilot_20`, `full_150`.

## 8. Resume/failure plan

Use `resume_key` and `expected_tmrt_path`. The runner skips existing readable Tmrt outputs and writes compact logs under `{cfg['local_run_log_root']}`.

## 9. Postrun QA

Run `scripts/v12_b87c_postrun_qa.py --config configs/v12/systemb_b87b4_b87c_materialization_package.yaml` after QGIS execution, then refresh the compact review packet with `b87c_postrun_packet_script.ps1`.

## 10. Git hygiene

No raster, `svfs.zip`, data/solweig, data/rasters, data/archive, or hourly forecast CSV outputs should be staged from the repo. Heavy execution assets stay under `C:/OpenHeat-local`.

## 11. Claim boundaries

Local-only raster writes are allowed under `C:/OpenHeat-local` only. This lane creates no repo raster writes, no AOI/B9, no WBGT/risk/hazard/exposure/vulnerability output, no observed truth claim, and no causal feature-importance claim.
"""


def run_postrun_qa(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = output_dir(cfg)
    manifest_path = out / "b87c_manifest.csv"
    manifest = read_rows(manifest_path) if manifest_path.exists() else []
    missing_tmrt = [row for row in manifest if not Path(row["expected_tmrt_path"]).exists()]
    status_counts: Counter[str] = Counter()
    for log_path in local_path(cfg, "local_run_log_root").glob("*.csv"):
        for row in read_rows(log_path):
            status_counts[str(row.get("status", ""))] += 1
    rows = [
        {"qa_item": "manifest_rows", "observed": len(manifest), "status": "PASS" if len(manifest) == int(cfg["expected_total_runs"]) else "REVIEW", "note": ""},
        {"qa_item": "missing_tmrt_outputs", "observed": len(missing_tmrt), "status": "PASS" if not missing_tmrt else "REVIEW", "note": "Expected before SOLWEIG run."},
        {"qa_item": "run_log_status_counts", "observed": json.dumps(status_counts, sort_keys=True), "status": "INFO", "note": ""},
        {"qa_item": "git_hygiene", "observed": "see b87c_git_hygiene_guard.csv", "status": "CHECK", "note": "Do not copy heavy local assets to Git."},
    ]
    write_rows(out / "b87c_postrun_qa_summary.csv", rows, ["qa_item", "observed", "status", "note"])
    return rows


def run_named_step(step: str, config_path: Path) -> int:
    cfg = load_config(config_path)
    if step == "input_inventory":
        write_input_inventory(cfg)
    elif step == "source_lock_loader":
        write_source_lock_summary(cfg)
    elif step == "local_root_setup":
        setup_local_roots(cfg)
    elif step == "tile_spec_builder":
        write_tile_specs(cfg)
    elif step == "materialization_plan":
        write_materialization_plan(cfg)
    elif step == "materialization_driver":
        run_materialization_driver(cfg)
    elif step == "materialization_audit":
        write_materialization_audit(cfg)
    elif step == "manifest_builder":
        write_manifest(cfg)
    elif step == "runner_localizer":
        localize_runners(cfg)
    elif step == "manifest_audit":
        write_manifest_audit(cfg)
    elif step == "postrun_qa":
        run_postrun_qa(cfg)
    elif step == "readiness_decision":
        write_readiness_decision(cfg)
    elif step == "run_package":
        run_package(cfg)
    else:
        raise ValueError(f"Unknown step: {step}")
    return 0


def run_package(cfg: dict[str, Any]) -> str:
    write_input_inventory(cfg)
    write_source_lock_summary(cfg)
    setup_local_roots(cfg)
    write_tile_specs(cfg)
    write_materialization_plan(cfg)
    run_materialization_driver(cfg)
    write_manifest(cfg)
    write_qgis_instructions(cfg)
    localize_runners(cfg)
    write_manifest_audit(cfg)
    run_postrun_qa(cfg)
    status = write_readiness_decision(cfg)
    return status


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default="configs/v12/systemb_b87b4_b87c_materialization_package.yaml")
    return parser
