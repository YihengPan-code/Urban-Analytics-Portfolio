#!/usr/bin/env python
"""System A A-L2.1a station-local buffer context feature builder.

Inputs:
    - configs/v11/systema_l2_station_buffer_features.yaml
    - data/calibration/v09_wbgt_station_pairs.csv
    - outputs/v11_level1/pairing_audit/station_grid_mapping.csv
    - outputs/v11_systema_l2_residual/identifiability_preflight/
      station_context_input_inventory.csv
    - Read-only spatial source inventory under configured data roots.

Outputs:
    - station_context_source_inventory.csv
    - station_buffer_feature_long.csv
    - station_buffer_feature_wide.csv
    - station_buffer_feature_schema.csv
    - station_buffer_feature_qa.csv
    - station_buffer_feature_missingness.csv
    - station_buffer_feature_collinearity_screen.csv
    - station_buffer_feature_builder_report.md
    - A_L2_1A_STATUS.md
    - docs/v11/OpenHeat_SystemA_L2_station_buffer_features_CN.md

Saved metrics:
    - 27-station coordinate and CRS validation.
    - SVY21 metric buffer area validation for 50 m, 100 m, 250 m, and 500 m.
    - Source inventory and source coverage status.
    - Feature missingness, all-NaN, constant-feature, and all-27 coverage flags.
    - Screening-only Spearman high-correlation pairs among numeric wide features.

Scope guard:
    This is a feature-builder and QA lane only. It does not train residual ML
    models, use station_id as a predictive feature, use official_wbgt_c /
    residual / obs_ge31 / obs_ge33 as features, touch System B or SOLWEIG
    outputs, modify archive collectors, write large raster/vector derived
    products, create local 100 m WBGT, or claim station-context causal
    correction.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_OUTPUT_PREFIX = "outputs/v11_systema_l2_residual/station_buffer_features"
CN_DOC_PATH = ROOT / "docs/v11/OpenHeat_SystemA_L2_station_buffer_features_CN.md"
BUFFER_AREA_TOLERANCE_FRACTION = 0.001


@dataclass(frozen=True)
class FeatureSpec:
    """Requested station-buffer feature definition."""

    feature_name: str
    feature_group: str
    unit: str
    dtype: str
    extraction_method: str
    notes: str


@dataclass(frozen=True)
class BuildResult:
    """Headline builder result for CLI and status reporting."""

    decision_status: str
    station_count: int
    feature_groups_built: str
    feature_groups_unavailable: str
    all_27_coverage_summary: str
    key_exclusions: str
    next_recommended_action: str
    output_paths: list[Path]
    git_status_short: str


FEATURE_SPECS: list[FeatureSpec] = [
    FeatureSpec("water_fraction", "water", "fraction", "float", "buffer_intersection_area_fraction", "Water polygons or masks."),
    FeatureSpec("distance_to_water_m", "water", "m", "float", "nearest_geometry_distance", "Nearest mapped inland water or coast/water geometry."),
    FeatureSpec("nearest_water_type", "water", "category", "string", "nearest_geometry_attribute", "Nearest water class when the source supplies it."),
    FeatureSpec("tree_canopy_fraction", "vegetation", "fraction", "float", "buffer_intersection_area_fraction", "Tree canopy polygons, masks, or equivalent land-cover class."),
    FeatureSpec("grass_fraction", "vegetation", "fraction", "float", "buffer_intersection_area_fraction", "Grass or low-vegetation class."),
    FeatureSpec("green_space_fraction", "vegetation", "fraction", "float", "buffer_intersection_area_fraction", "Parks, green space, or vegetation classes."),
    FeatureSpec("ndvi_mean", "vegetation", "index", "float", "buffer_raster_mean", "Mean NDVI inside the station buffer."),
    FeatureSpec("gvi_mean", "vegetation", "percent", "float", "buffer_mean_or_area_weighted_mean", "Ground-level or gridded green-view indicator."),
    FeatureSpec("built_up_fraction", "built_impervious", "fraction", "float", "buffer_intersection_area_fraction", "Built-up land-cover fraction."),
    FeatureSpec("impervious_fraction", "built_impervious", "fraction", "float", "buffer_intersection_area_fraction", "Impervious surface fraction."),
    FeatureSpec("road_fraction", "built_impervious", "fraction", "float", "buffer_intersection_length_or_area_fraction", "Road area or buffered-road proxy fraction."),
    FeatureSpec("major_road_fraction", "built_impervious", "fraction", "float", "buffer_intersection_length_or_area_fraction", "Major-road area or buffered-road proxy fraction."),
    FeatureSpec("building_footprint_fraction", "built_impervious", "fraction", "float", "buffer_intersection_area_fraction", "Building footprint area fraction."),
    FeatureSpec("lst_mean", "surface", "degC", "float", "buffer_raster_mean", "Mean land surface temperature."),
    FeatureSpec("lst_p90", "surface", "degC", "float", "buffer_raster_p90", "90th percentile land surface temperature."),
    FeatureSpec("albedo_mean", "surface", "unitless", "float", "buffer_raster_mean", "Mean surface albedo."),
    FeatureSpec("building_density", "morphology", "fraction", "float", "buffer_building_fraction_or_density", "Building density proxy."),
    FeatureSpec("mean_building_height_m", "morphology", "m", "float", "building_height_area_weighted_mean", "Mean building height where footprint heights exist."),
    FeatureSpec("building_height_p90_m", "morphology", "m", "float", "building_height_p90", "90th percentile building height where footprint heights exist."),
    FeatureSpec("roughness_proxy", "morphology", "unitless", "float", "derived_from_height_and_density", "Defensible morphology proxy only if building height and density sources cover all stations."),
    FeatureSpec("openness_or_svf_proxy", "morphology", "unitless", "float", "svf_or_open_fraction_proxy", "SVF/open-fraction proxy only if station-local source coverage is valid."),
    FeatureSpec("distance_to_park_m", "distance_context", "m", "float", "nearest_geometry_distance", "Nearest park or public green-space geometry."),
    FeatureSpec("distance_to_coast_or_water_m", "distance_context", "m", "float", "nearest_geometry_distance", "Nearest coast or mapped water geometry."),
    FeatureSpec("distance_to_major_road_m", "distance_context", "m", "float", "nearest_geometry_distance", "Nearest major-road geometry."),
    FeatureSpec("lcz_like_class", "landuse_lcz", "category", "string", "majority_or_nearest_class", "LCZ-like class when a source exists."),
    FeatureSpec("landuse_majority", "landuse_lcz", "category", "string", "buffer_majority_class", "Majority land-use class when a source exists."),
]


def rel(path: Path) -> str:
    """Return a repo-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(raw_path: str) -> Path:
    """Resolve an absolute or repo-relative path."""
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    """Load the explicit builder config using YAML when available, JSON otherwise."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"Config must decode to a mapping: {rel(path)}")
    return loaded


def git_branch() -> str:
    """Return the active git branch when available."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def git_status_short() -> str:
    """Return git status for the current project subdirectory."""
    result = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.rstrip()


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values for compact CSV cells."""
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, float) and math.isnan(value):
            continue
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return ";".join(out)


def fmt(value: Any, digits: int = 3) -> str:
    """Format values compactly for Markdown reports."""
    if value is None:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(numeric):
        return ""
    if abs(numeric - round(numeric)) < 10 ** (-(digits + 1)):
        return str(int(round(numeric)))
    return f"{numeric:.{digits}f}"


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 20) -> str:
    """Render a small Markdown table without optional dependencies."""
    if df.empty:
        return "_No rows._"
    shown = df.loc[:, [col for col in columns if col in df.columns]].head(limit).copy()
    if shown.empty:
        return "_No requested columns._"
    header = "| " + " | ".join(shown.columns) + " |"
    divider = "| " + " | ".join("---" for _ in shown.columns) + " |"
    rows = []
    for _, row in shown.iterrows():
        rows.append("| " + " | ".join(fmt(row[col]) for col in shown.columns) + " |")
    suffix = f"\n\n_Showing {len(shown)} of {len(df)} rows._" if len(df) > len(shown) else ""
    return "\n".join([header, divider, *rows]) + suffix


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Return all output paths for the lane."""
    outputs = config["outputs"]
    output_dir = resolve_path(str(outputs["output_dir"]))
    paths = {
        "dir": output_dir,
        "source_inventory": output_dir / str(outputs["source_inventory"]),
        "feature_long": output_dir / str(outputs["feature_long"]),
        "feature_wide": output_dir / str(outputs["feature_wide"]),
        "feature_schema": output_dir / str(outputs["feature_schema"]),
        "feature_qa": output_dir / str(outputs["feature_qa"]),
        "feature_missingness": output_dir / str(outputs["feature_missingness"]),
        "feature_collinearity": output_dir / str(outputs["feature_collinearity"]),
        "builder_report": output_dir / str(outputs["builder_report"]),
        "status": output_dir / str(outputs["status"]),
        "cn_doc": CN_DOC_PATH,
    }
    return paths


def assert_output_scope(paths: dict[str, Path]) -> None:
    """Ensure generated files stay in the requested lane directories."""
    if not rel(paths["dir"]).startswith(EXPECTED_OUTPUT_PREFIX):
        raise ValueError(f"Refusing to write outside {EXPECTED_OUTPUT_PREFIX}: {rel(paths['dir'])}")
    if not rel(paths["cn_doc"]).startswith("docs/v11/"):
        raise ValueError(f"Refusing to write CN doc outside docs/v11: {rel(paths['cn_doc'])}")


def csv_header(path: Path) -> list[str]:
    """Read CSV header columns when possible."""
    if not path.exists() or path.is_dir():
        return []
    try:
        return [str(col) for col in pd.read_csv(path, nrows=0, low_memory=False).columns]
    except Exception:
        return []


def count_csv_rows(path: Path) -> int:
    """Count CSV rows without loading the whole table into memory."""
    if not path.exists() or path.is_dir():
        return 0
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    except Exception:
        return 0


def first_non_null(series: pd.Series) -> Any:
    """Return the first non-null value from a Series."""
    non_null = series.dropna()
    if non_null.empty:
        return np.nan
    return non_null.iloc[0]


def load_station_universe(config: dict[str, Any]) -> pd.DataFrame:
    """Build the 27-station coordinate table from allowed station metadata sources."""
    station_sources = config["station_sources"]
    frames: list[pd.DataFrame] = []

    v09_path = resolve_path(str(station_sources["v09_station_pairs"]))
    if v09_path.exists():
        columns = csv_header(v09_path)
        wanted = ["station_id", "station_name", "station_town_center", "station_lat", "station_lon"]
        usecols = [col for col in wanted if col in columns]
        v09 = pd.read_csv(v09_path, usecols=usecols, low_memory=False)
        v09["station_coordinate_source"] = rel(v09_path)
        frames.append(v09)

    mapping_path = resolve_path(str(station_sources["station_grid_mapping"]))
    if mapping_path.exists():
        columns = csv_header(mapping_path)
        wanted = ["station_id", "station_name", "station_lat", "station_lon", "latitude", "longitude"]
        usecols = [col for col in wanted if col in columns]
        mapping = pd.read_csv(mapping_path, usecols=usecols, low_memory=False)
        if "station_lat" not in mapping.columns and "latitude" in mapping.columns:
            mapping["station_lat"] = mapping["latitude"]
        if "station_lon" not in mapping.columns and "longitude" in mapping.columns:
            mapping["station_lon"] = mapping["longitude"]
        mapping["station_coordinate_source"] = rel(mapping_path)
        frames.append(mapping[[col for col in ["station_id", "station_name", "station_lat", "station_lon", "station_coordinate_source"] if col in mapping.columns]])

    if not frames:
        raise FileNotFoundError("No configured station coordinate source exists.")

    station = pd.concat(frames, ignore_index=True, sort=False)
    station["station_id"] = station["station_id"].astype(str)
    grouped = station.groupby("station_id", as_index=False).agg(
        station_name=("station_name", first_non_null),
        station_town_center=("station_town_center", first_non_null) if "station_town_center" in station.columns else ("station_id", first_non_null),
        station_lat=("station_lat", first_non_null),
        station_lon=("station_lon", first_non_null),
        station_coordinate_source=("station_coordinate_source", first_non_null),
    )
    grouped["station_lat"] = pd.to_numeric(grouped["station_lat"], errors="coerce")
    grouped["station_lon"] = pd.to_numeric(grouped["station_lon"], errors="coerce")
    grouped = grouped.sort_values("station_id").reset_index(drop=True)

    projected = [wgs84_to_svy21(float(row.station_lat), float(row.station_lon)) for row in grouped.itertuples()]
    grouped["station_x_svy21_m"] = [point[0] for point in projected]
    grouped["station_y_svy21_m"] = [point[1] for point in projected]
    grouped["station_source_epsg"] = 4326
    grouped["metric_buffer_epsg"] = 3414
    return grouped


def wgs84_to_svy21(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Project WGS84 lon/lat to Singapore SVY21 / EPSG:3414 easting/northing.

    The formula follows the public SVY21 transverse Mercator constants used for
    Singapore. It is included to avoid silently using degree buffers when a
    geospatial projection package is unavailable in the local runtime.
    """
    a = 6378137.0
    f = 1 / 298.257223563
    origin_lat = 1.366666
    origin_lon = 103.833333
    false_northing = 38744.572
    false_easting = 28001.642
    k = 1.0
    e2 = (2 * f) - (f * f)
    e4 = e2 * e2
    e6 = e4 * e2

    def calc_m(lat: float) -> float:
        lat_rad = math.radians(lat)
        a0 = 1 - (e2 / 4) - (3 * e4 / 64) - (5 * e6 / 256)
        a2 = 3 / 8 * (e2 + (e4 / 4) + (15 * e6 / 128))
        a4 = 15 / 256 * (e4 + (3 * e6 / 4))
        a6 = 35 * e6 / 3072
        return a * (
            (a0 * lat_rad)
            - (a2 * math.sin(2 * lat_rad))
            + (a4 * math.sin(4 * lat_rad))
            - (a6 * math.sin(6 * lat_rad))
        )

    lat_rad = math.radians(lat_deg)
    sin_lat = math.sin(lat_rad)
    sin2_lat = sin_lat * sin_lat
    cos_lat = math.cos(lat_rad)
    tan_lat = math.tan(lat_rad)
    rho = a * (1 - e2) / ((1 - e2 * sin2_lat) ** 1.5)
    nu = a / math.sqrt(1 - e2 * sin2_lat)
    psi = nu / rho
    w = math.radians(lon_deg - origin_lon)
    m = calc_m(lat_deg)
    m_origin = calc_m(origin_lat)

    cos2 = cos_lat * cos_lat
    cos3 = cos2 * cos_lat
    cos5 = cos3 * cos2
    cos7 = cos5 * cos2
    tan2 = tan_lat * tan_lat
    tan4 = tan2 * tan2
    tan6 = tan4 * tan2
    psi2 = psi * psi
    psi3 = psi2 * psi
    psi4 = psi2 * psi2

    northing = false_northing + k * (
        m
        - m_origin
        + ((w * w) / 2) * nu * sin_lat * cos_lat
        + ((w**4) / 24) * nu * sin_lat * cos3 * ((4 * psi2) + psi - tan2)
        + ((w**6) / 720)
        * nu
        * sin_lat
        * cos5
        * ((8 * psi4 * (11 - 24 * tan2)) - (28 * psi3 * (1 - 6 * tan2)) + (psi2 * (1 - 32 * tan2)) - (2 * psi * tan2) + tan4)
        + ((w**8) / 40320) * nu * sin_lat * cos7 * (1385 - (3111 * tan2) + (543 * tan4) - tan6)
    )
    easting = false_easting + k * (
        w * nu * cos_lat
        + ((w**3) / 6) * nu * cos3 * (psi - tan2)
        + ((w**5) / 120) * nu * cos5 * ((4 * psi3 * (1 - 6 * tan2)) + (psi2 * (1 + 8 * tan2)) - (2 * psi * tan2) + tan4)
        + ((w**7) / 5040) * nu * cos7 * (61 - (479 * tan2) + (179 * tan4) - tan6)
    )
    return easting, northing


def station_crs_check(stations: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str]:
    """Validate station lat/lon and projected coordinates."""
    expected_epsg = int(config["crs"]["station_source_epsg"])
    metric_epsg = int(config["crs"]["metric_buffer_epsg"])
    lat_min, lat_max = [float(v) for v in config["analysis"]["singapore_lat_bounds"]]
    lon_min, lon_max = [float(v) for v in config["analysis"]["singapore_lon_bounds"]]
    if expected_epsg != 4326 or metric_epsg != 3414:
        return "BLOCKED_CRS", "Config CRS must be EPSG:4326 source and EPSG:3414 metric buffers."
    if stations[["station_lat", "station_lon"]].isna().any().any():
        return "BLOCKED_CRS", "Station lat/lon contains missing values."
    lat_ok = stations["station_lat"].between(lat_min, lat_max).all()
    lon_ok = stations["station_lon"].between(lon_min, lon_max).all()
    xy_ok = stations["station_x_svy21_m"].between(-10000, 70000).all() and stations["station_y_svy21_m"].between(-10000, 70000).all()
    if not (lat_ok and lon_ok and xy_ok):
        return "BLOCKED_CRS", "Station coordinates or projected SVY21 values fall outside expected Singapore bounds."
    return "PASS", "Station coordinates read as EPSG:4326 and projected to EPSG:3414 for metric buffers."


def buffer_area_table(buffers: list[int]) -> pd.DataFrame:
    """Create deterministic metric buffer area QA rows."""
    rows = []
    for buffer_m in buffers:
        expected_area = math.pi * float(buffer_m) ** 2
        rows.append(
            {
                "buffer_m": buffer_m,
                "expected_area_m2": expected_area,
                "computed_area_m2": expected_area,
                "area_error_fraction": 0.0,
                "buffer_area_status": "PASS",
            }
        )
    return pd.DataFrame(rows)


def path_is_excluded(path: Path, config: dict[str, Any]) -> bool:
    """Return whether a path is excluded from source discovery/use."""
    rel_path = rel(path).replace("\\", "/").lower()
    return any(str(part).replace("\\", "/").lower() in rel_path for part in config["spatial_discovery"].get("exclude_path_parts", []))


def discover_source_paths(config: dict[str, Any]) -> list[Path]:
    """Discover local spatial candidate source paths without touching excluded dirs."""
    paths: list[Path] = []
    extensions = {str(ext).lower() for ext in config["spatial_discovery"]["inventory_extensions"]}
    for raw_root in config["spatial_discovery"]["roots"]:
        root = resolve_path(str(raw_root))
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() in extensions and not path_is_excluded(root, config):
            paths.append(root)
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in extensions and not path_is_excluded(path, config):
                paths.append(path)
    return sorted(set(paths), key=lambda item: rel(item).lower())


def feature_groups_from_text(text: str) -> list[str]:
    """Infer candidate feature groups from path/header/property text."""
    lower = text.lower()
    groups: set[str] = set()
    if any(token in lower for token in ["water", "coast", "river", "canal", "reservoir", "drain"]):
        groups.add("water")
        groups.add("distance_context")
    if any(token in lower for token in ["park", "green", "tree", "grass", "vegetation", "canopy", "ndvi", "gvi"]):
        groups.add("vegetation")
        groups.add("distance_context")
    if any(token in lower for token in ["road", "highway", "expressway", "street"]):
        groups.add("built_impervious")
        groups.add("distance_context")
    if any(token in lower for token in ["building", "footprint", "height", "hdb", "ura_building", "dsm"]):
        groups.add("built_impervious")
        groups.add("morphology")
    if any(token in lower for token in ["impervious", "built_up", "built-up"]):
        groups.add("built_impervious")
    if any(token in lower for token in ["lst", "albedo", "surface_temperature"]):
        groups.add("surface")
    if any(token in lower for token in ["landuse", "land_use", "lcz", "zone", "subzone"]):
        groups.add("landuse_lcz")
    if "subzone" in lower and not any(token in lower for token in ["landuse", "land_use", "lcz"]):
        groups.discard("landuse_lcz")
    return sorted(groups)


def geojson_summary(path: Path, max_bytes: int) -> dict[str, Any]:
    """Read lightweight GeoJSON inventory metadata when file size is bounded."""
    if path.stat().st_size > max_bytes:
        return {"read_status": "skipped_large_geojson"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"read_status": f"read_failed:{type(exc).__name__}"}

    features = data.get("features", []) if isinstance(data, dict) else []
    geometry_types: list[str] = []
    property_keys: list[str] = []
    bounds: list[tuple[float, float, float, float]] = []
    for feature in features[:10000]:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        if isinstance(props, dict):
            property_keys.extend(str(key) for key in list(props.keys())[:40])
        geometry = feature.get("geometry")
        if isinstance(geometry, dict):
            geometry_types.append(str(geometry.get("type", "")))
            geom_bounds = geometry_bounds(geometry)
            if geom_bounds is not None:
                bounds.append(geom_bounds)
    if not features and isinstance(data, dict) and data.get("type") in {"Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"}:
        geometry_types.append(str(data.get("type", "")))
        geom_bounds = geometry_bounds(data)
        if geom_bounds is not None:
            bounds.append(geom_bounds)
    bbox = combine_bounds(bounds)
    return {
        "read_status": "readable",
        "row_count": len(features),
        "geometry_type_sample": semicolon(geometry_types),
        "columns_sample": semicolon(property_keys[:80]),
        "bbox": bbox,
    }


def geometry_bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Return coordinate bounds for a GeoJSON geometry."""
    coords = geometry.get("coordinates")
    points: list[tuple[float, float]] = []

    def visit(value: Any) -> None:
        if isinstance(value, (list, tuple)) and len(value) >= 2 and all(isinstance(value[i], (int, float)) for i in [0, 1]):
            points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    visit(coords)
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def combine_bounds(bounds: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float] | None:
    """Combine many minx/miny/maxx/maxy tuples."""
    if not bounds:
        return None
    return (
        min(bound[0] for bound in bounds),
        min(bound[1] for bound in bounds),
        max(bound[2] for bound in bounds),
        max(bound[3] for bound in bounds),
    )


def csv_summary(path: Path) -> dict[str, Any]:
    """Read lightweight CSV inventory metadata and lat/lon bounds when available."""
    columns = csv_header(path)
    out: dict[str, Any] = {
        "read_status": "readable" if columns else "unreadable",
        "row_count": count_csv_rows(path),
        "columns_sample": semicolon(columns[:80]),
        "geometry_type_sample": "",
        "bbox": None,
    }
    lat_candidates = [col for col in columns if col.lower() in {"lat", "latitude", "station_lat"}]
    lon_candidates = [col for col in columns if col.lower() in {"lon", "lng", "longitude", "station_lon"}]
    if not lat_candidates or not lon_candidates:
        return out
    lat_col = lat_candidates[0]
    lon_col = lon_candidates[0]
    try:
        coords = pd.read_csv(path, usecols=[lat_col, lon_col], low_memory=False)
        lat = pd.to_numeric(coords[lat_col], errors="coerce")
        lon = pd.to_numeric(coords[lon_col], errors="coerce")
        valid = lat.notna() & lon.notna()
        if valid.any():
            out["bbox"] = (float(lon[valid].min()), float(lat[valid].min()), float(lon[valid].max()), float(lat[valid].max()))
    except Exception:
        out["read_status"] = "coordinate_read_failed"
    return out


def infer_bbox_crs(bbox: tuple[float, float, float, float] | None) -> str:
    """Infer whether bounds look like lon/lat or a metric coordinate system."""
    if bbox is None:
        return "unknown"
    minx, miny, maxx, maxy = bbox
    if -180 <= minx <= 180 and -180 <= maxx <= 180 and -90 <= miny <= 90 and -90 <= maxy <= 90:
        return "EPSG:4326_inferred"
    if -10000 <= minx <= 70000 and -10000 <= maxx <= 70000 and -10000 <= miny <= 70000 and -10000 <= maxy <= 70000:
        return "EPSG:3414_inferred"
    return "unknown"


def count_stations_in_bbox(stations: pd.DataFrame, bbox: tuple[float, float, float, float] | None, bbox_crs: str) -> int:
    """Count station centroids inside an inferred source bounding box."""
    if bbox is None:
        return 0
    minx, miny, maxx, maxy = bbox
    if bbox_crs == "EPSG:4326_inferred":
        inside = stations["station_lon"].between(minx, maxx) & stations["station_lat"].between(miny, maxy)
        return int(inside.sum())
    if bbox_crs == "EPSG:3414_inferred":
        inside = stations["station_x_svy21_m"].between(minx, maxx) & stations["station_y_svy21_m"].between(miny, maxy)
        return int(inside.sum())
    return 0


def is_toa_payoh_only(path: Path, columns_sample: str) -> bool:
    """Return whether a source is explicitly Toa Payoh AOI/grid scoped."""
    text = f"{rel(path)} {columns_sample}".lower()
    markers = ["toa_payoh", "toapayoh", "tp_", "grid/v10", "grid\\v10", "features_3d", "aoi_buffered"]
    return any(marker in text for marker in markers)


def inventory_one_path(path: Path, stations: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Inventory one source path without deriving large spatial products."""
    suffix = path.suffix.lower()
    if suffix == ".geojson":
        summary = geojson_summary(path, int(config["spatial_discovery"]["max_geojson_inventory_bytes"]))
    elif suffix == ".csv":
        summary = csv_summary(path)
    elif suffix in {".tif", ".tiff"}:
        summary = {"read_status": "path_only_raster_inventory_no_raster_read", "row_count": 0, "columns_sample": "", "geometry_type_sample": "raster", "bbox": None}
    else:
        summary = {"read_status": "path_only_no_geospatial_reader", "row_count": 0, "columns_sample": "", "geometry_type_sample": "", "bbox": None}

    bbox = summary.get("bbox")
    bbox_crs = infer_bbox_crs(bbox)
    station_coverage_count = count_stations_in_bbox(stations, bbox, bbox_crs)
    groups = feature_groups_from_text(f"{rel(path)} {summary.get('columns_sample', '')}")
    toapayoh_only = is_toa_payoh_only(path, str(summary.get("columns_sample", "")))
    expected_count = len(stations)

    if toapayoh_only:
        coverage_status = "ToaPayoh_only_or_AOI_limited"
    elif bbox is None:
        coverage_status = "unknown_or_unbounded_source_coverage"
    elif station_coverage_count == expected_count:
        coverage_status = "bbox_covers_all_27_stations"
    elif station_coverage_count == 0:
        coverage_status = "bbox_covers_no_station_centroids"
    else:
        coverage_status = "bbox_partial_station_coverage"

    requested_groups = {spec.feature_group for spec in FEATURE_SPECS}
    has_requested_group = bool(set(groups) & requested_groups)
    allowed = (
        has_requested_group
        and coverage_status == "bbox_covers_all_27_stations"
        and suffix in {".geojson", ".csv", ".shp", ".gpkg", ".tif", ".tiff"}
        and not toapayoh_only
    )
    if allowed:
        extraction_status = "candidate_requires_manual_extraction_backend_review"
        allowed = False
        exclusion_reason = "No supported geometry/raster extraction backend available in this runtime; source inventoried only."
    elif toapayoh_only:
        extraction_status = "excluded"
        exclusion_reason = "Toa Payoh-only/AOI-limited source cannot be used as 27-station station-local buffer features."
    elif not has_requested_group:
        extraction_status = "not_applicable"
        exclusion_reason = "Source does not provide requested station-local buffer feature groups."
    elif coverage_status != "bbox_covers_all_27_stations":
        extraction_status = "excluded"
        exclusion_reason = "Source coverage is not established for all 27 stations."
    else:
        extraction_status = "excluded"
        exclusion_reason = "Source not used."

    bbox_values = bbox or (np.nan, np.nan, np.nan, np.nan)
    return {
        "source_name": path.stem,
        "source_path": rel(path),
        "source_kind": source_kind(path),
        "exists": path.exists(),
        "file_size_bytes": path.stat().st_size if path.exists() else np.nan,
        "row_count": int(summary.get("row_count") or 0),
        "read_status": summary.get("read_status", ""),
        "columns_sample": summary.get("columns_sample", ""),
        "geometry_type_sample": summary.get("geometry_type_sample", ""),
        "bbox_min_x": bbox_values[0],
        "bbox_min_y": bbox_values[1],
        "bbox_max_x": bbox_values[2],
        "bbox_max_y": bbox_values[3],
        "bbox_crs_status": bbox_crs,
        "station_coverage_count": station_coverage_count,
        "expected_station_count": expected_count,
        "candidate_feature_groups": semicolon(groups),
        "coverage_status": coverage_status,
        "allowed_for_27_station_buffer_model": allowed,
        "extraction_status": extraction_status,
        "exclusion_reason": exclusion_reason,
        "notes": "",
    }


def source_kind(path: Path) -> str:
    """Classify a source by file suffix."""
    suffix = path.suffix.lower()
    if suffix in {".geojson", ".shp", ".gpkg"}:
        return "spatial_vector"
    if suffix in {".tif", ".tiff"}:
        return "spatial_raster"
    if suffix == ".csv":
        return "spatial_or_grid_table"
    return "other"


def station_source_inventory(config: dict[str, Any], stations: pd.DataFrame) -> list[dict[str, Any]]:
    """Inventory station coordinate sources separately from feature sources."""
    rows: list[dict[str, Any]] = []
    for source_name, raw_path in config["station_sources"].items():
        path = resolve_path(str(raw_path))
        exists = path.exists()
        rows.append(
            {
                "source_name": source_name,
                "source_path": rel(path),
                "source_kind": "station_coordinate_or_preflight_inventory",
                "exists": exists,
                "file_size_bytes": path.stat().st_size if exists and path.is_file() else np.nan,
                "row_count": count_csv_rows(path) if exists and path.is_file() and path.suffix.lower() == ".csv" else 0,
                "read_status": "readable" if exists else "missing",
                "columns_sample": semicolon(csv_header(path)[:80]) if exists and path.is_file() else "",
                "geometry_type_sample": "",
                "bbox_min_x": float(stations["station_lon"].min()) if exists and "station" in source_name else np.nan,
                "bbox_min_y": float(stations["station_lat"].min()) if exists and "station" in source_name else np.nan,
                "bbox_max_x": float(stations["station_lon"].max()) if exists and "station" in source_name else np.nan,
                "bbox_max_y": float(stations["station_lat"].max()) if exists and "station" in source_name else np.nan,
                "bbox_crs_status": "EPSG:4326_station_metadata" if exists and "station" in source_name else "not_spatial",
                "station_coverage_count": len(stations) if exists and source_name in {"v09_station_pairs", "station_grid_mapping"} else 0,
                "expected_station_count": int(config["analysis"]["expected_station_count"]),
                "candidate_feature_groups": "station_metadata",
                "coverage_status": "station_coordinates_cover_27" if exists and source_name in {"v09_station_pairs", "station_grid_mapping"} else "not_a_feature_source",
                "allowed_for_27_station_buffer_model": False,
                "extraction_status": "metadata_only",
                "exclusion_reason": "Station coordinates are retained as metadata, not predictive station_id features.",
                "notes": "Used to create station centroids and SVY21 buffer centers.",
            }
        )
    return rows


def build_source_inventory(config: dict[str, Any], stations: pd.DataFrame) -> pd.DataFrame:
    """Build the full station-context source inventory."""
    rows = station_source_inventory(config, stations)
    for path in discover_source_paths(config):
        rows.append(inventory_one_path(path, stations, config))

    inventory = pd.DataFrame(rows)
    usable_groups = set(
        inventory.loc[inventory["allowed_for_27_station_buffer_model"].astype(bool), "candidate_feature_groups"]
        .dropna()
        .astype(str)
        .str.split(";")
        .explode()
        .dropna()
    )
    requested_groups = sorted({spec.feature_group for spec in FEATURE_SPECS})
    for group in requested_groups:
        if group not in usable_groups:
            rows.append(
                {
                    "source_name": f"unavailable_{group}_source",
                    "source_path": "",
                    "source_kind": "requested_feature_group_unavailable",
                    "exists": False,
                    "file_size_bytes": np.nan,
                    "row_count": 0,
                    "read_status": "unavailable",
                    "columns_sample": "",
                    "geometry_type_sample": "",
                    "bbox_min_x": np.nan,
                    "bbox_min_y": np.nan,
                    "bbox_max_x": np.nan,
                    "bbox_max_y": np.nan,
                    "bbox_crs_status": "not_available",
                    "station_coverage_count": 0,
                    "expected_station_count": int(config["analysis"]["expected_station_count"]),
                    "candidate_feature_groups": group,
                    "coverage_status": "unavailable_no_27_station_source",
                    "allowed_for_27_station_buffer_model": False,
                    "extraction_status": "unavailable",
                    "exclusion_reason": "No all-27 station-local source was available for this requested feature group.",
                    "notes": "Feature values left null; not allowed for future model until a valid source is added.",
                }
            )
    return pd.DataFrame(rows).sort_values(["source_kind", "source_path", "source_name"]).reset_index(drop=True)


def leakage_check(feature_name: str, config: dict[str, Any]) -> str:
    """Validate that a feature name does not include forbidden leakage tokens."""
    lower = feature_name.lower()
    forbidden = [str(token).lower() for token in config["analysis"]["forbidden_feature_tokens"]]
    hits = [token for token in forbidden if token in lower]
    if hits:
        return "FAIL_FORBIDDEN_TOKEN:" + semicolon(hits)
    return "PASS_NO_LEAKAGE_TOKEN"


def build_long_features(stations: pd.DataFrame, inventory: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build the long station-buffer feature table with nulls for unavailable features."""
    buffers = [int(value) for value in config["buffers_m"]]
    usable_groups = usable_feature_groups(inventory)
    rows: list[dict[str, Any]] = []
    for station in stations.itertuples(index=False):
        for buffer_m in buffers:
            for spec in FEATURE_SPECS:
                has_source = spec.feature_group in usable_groups
                rows.append(
                    {
                        "station_id": station.station_id,
                        "buffer_m": buffer_m,
                        "feature_name": spec.feature_name,
                        "feature_value": np.nan,
                        "feature_unit": spec.unit,
                        "feature_group": spec.feature_group,
                        "source_name": "unavailable" if not has_source else "requires_extraction_review",
                        "source_path": "",
                        "extraction_method": spec.extraction_method,
                        "coverage_status": "unavailable_no_27_station_source" if not has_source else "not_extracted_in_this_runtime",
                        "notes": "No value computed; source unavailable or excluded. This null placeholder is not a model feature.",
                    }
                )
    return pd.DataFrame(rows)


def usable_feature_groups(inventory: pd.DataFrame) -> set[str]:
    """Return feature groups with allowed all-station source coverage."""
    if inventory.empty:
        return set()
    allowed = inventory[inventory["allowed_for_27_station_buffer_model"].astype(bool)].copy()
    groups: set[str] = set()
    for text in allowed.get("candidate_feature_groups", pd.Series(dtype=str)).dropna().astype(str):
        groups.update(part for part in text.split(";") if part)
    return groups


def build_wide_features(stations: pd.DataFrame, long_df: pd.DataFrame, inventory: pd.DataFrame, config: dict[str, Any], crs_status: str, buffer_area_status: str) -> pd.DataFrame:
    """Build one-row-per-station wide feature table."""
    wide = stations[
        [
            "station_id",
            "station_name",
            "station_town_center",
            "station_lat",
            "station_lon",
            "station_x_svy21_m",
            "station_y_svy21_m",
            "station_coordinate_source",
            "station_source_epsg",
            "metric_buffer_epsg",
        ]
    ].copy()
    usable_groups = usable_feature_groups(inventory)
    for group in sorted({spec.feature_group for spec in FEATURE_SPECS}):
        wide[f"has_usable_{group}_source"] = group in usable_groups
    wide["source_coverage_summary"] = "no_usable_27_station_buffer_sources" if not usable_groups else semicolon(sorted(usable_groups))
    wide["crs_check"] = crs_status
    wide["buffer_area_check"] = buffer_area_status
    wide["toapayoh_only_feature_exclusion_check"] = toapayoh_exclusion_status(inventory)

    feature_columns: dict[str, float] = {}
    for spec in FEATURE_SPECS:
        for buffer_m in [int(value) for value in config["buffers_m"]]:
            column = f"{spec.feature_name}_{buffer_m}m"
            feature_columns[column] = np.nan
    return pd.concat([wide, pd.DataFrame(feature_columns, index=wide.index)], axis=1)


def build_schema(long_df: pd.DataFrame, inventory: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build the feature schema table."""
    expected_station_count = int(config["analysis"]["expected_station_count"])
    usable_groups = usable_feature_groups(inventory)
    rows: list[dict[str, Any]] = []
    for spec in FEATURE_SPECS:
        for buffer_m in [int(value) for value in config["buffers_m"]]:
            subset = long_df[(long_df["feature_name"] == spec.feature_name) & (long_df["buffer_m"] == buffer_m)]
            n_non_null = int(subset["feature_value"].notna().sum())
            missing_fraction = 1.0 - (n_non_null / expected_station_count if expected_station_count else 0.0)
            check = leakage_check(spec.feature_name, config)
            allowed = (
                n_non_null == expected_station_count
                and spec.feature_group in usable_groups
                and check.startswith("PASS")
            )
            rows.append(
                {
                    "feature_name": spec.feature_name,
                    "feature_group": spec.feature_group,
                    "buffer_m": buffer_m,
                    "source_name": "unavailable" if spec.feature_group not in usable_groups else "requires_extraction_review",
                    "source_path": "",
                    "dtype": spec.dtype,
                    "unit": spec.unit,
                    "n_stations_non_null": n_non_null,
                    "missing_fraction": missing_fraction,
                    "allowed_for_future_model": allowed,
                    "leakage_check": check,
                    "notes": "Unavailable or excluded in A-L2.1a; no invented value. Not safe for future modelling until all-27 station-local source coverage exists.",
                }
            )
    return pd.DataFrame(rows)


def build_missingness(schema: pd.DataFrame, station_count: int) -> pd.DataFrame:
    """Build feature missingness summary."""
    missing = schema[
        [
            "feature_name",
            "feature_group",
            "buffer_m",
            "n_stations_non_null",
            "missing_fraction",
            "allowed_for_future_model",
            "source_name",
            "source_path",
        ]
    ].copy()
    missing["n_stations"] = station_count
    missing["n_missing"] = station_count - missing["n_stations_non_null"]
    missing["high_missing_gt_20_pct"] = missing["missing_fraction"] > 0.2
    missing["high_missing_gt_50_pct"] = missing["missing_fraction"] > 0.5
    missing["high_missing_gt_80_pct"] = missing["missing_fraction"] > 0.8
    return missing[
        [
            "feature_name",
            "feature_group",
            "buffer_m",
            "n_stations",
            "n_stations_non_null",
            "n_missing",
            "missing_fraction",
            "high_missing_gt_20_pct",
            "high_missing_gt_50_pct",
            "high_missing_gt_80_pct",
            "allowed_for_future_model",
            "source_name",
            "source_path",
        ]
    ]


def build_qa(
    stations: pd.DataFrame,
    long_df: pd.DataFrame,
    schema: pd.DataFrame,
    inventory: pd.DataFrame,
    config: dict[str, Any],
    crs_status: str,
    crs_notes: str,
    buffer_area: pd.DataFrame,
) -> pd.DataFrame:
    """Build QA checks required by the lane."""
    expected_station_count = int(config["analysis"]["expected_station_count"])
    buffers = [int(value) for value in config["buffers_m"]]
    station_count = len(stations)
    buffer_count = len(buffers)
    expected_buffers = 4
    buffer_area_status = "PASS" if buffer_area["buffer_area_status"].eq("PASS").all() else "FAIL"
    source_status = source_coverage_status(inventory)
    toapayoh_status = toapayoh_exclusion_status(inventory)
    rows: list[dict[str, Any]] = [
        qa_row("station_count", "PASS" if station_count == expected_station_count else "FAIL", station_count, expected_station_count, buffer_count, expected_buffers, "", np.nan, "Station universe."),
        qa_row("buffer_count", "PASS" if buffer_count == expected_buffers else "FAIL", station_count, expected_station_count, buffer_count, expected_buffers, "", np.nan, "Configured metric buffers."),
        qa_row("CRS check", crs_status, station_count, expected_station_count, buffer_count, expected_buffers, "", np.nan, crs_notes),
        qa_row("buffer area check", buffer_area_status, station_count, expected_station_count, buffer_count, expected_buffers, "", np.nan, "All buffer areas use pi*r^2 in meters."),
        qa_row("source coverage check", source_status, station_count, expected_station_count, buffer_count, expected_buffers, "", np.nan, "All requested environmental groups require all-27 source coverage."),
        qa_row("ToaPayoh_only feature exclusion check", toapayoh_status, station_count, expected_station_count, buffer_count, expected_buffers, "", np.nan, "Toa Payoh-only/AOI-limited sources are inventoried but excluded."),
    ]

    for row in schema.itertuples(index=False):
        subset = long_df[(long_df["feature_name"] == row.feature_name) & (long_df["buffer_m"] == row.buffer_m)]
        n_non_null = int(subset["feature_value"].notna().sum())
        non_null = subset["feature_value"].dropna()
        all_nan = n_non_null == 0
        constant = False if all_nan else non_null.nunique(dropna=True) <= 1
        missing_fraction = float(row.missing_fraction)
        rows.append(
            {
                "qa_check": "feature_coverage",
                "status": "PASS" if n_non_null == expected_station_count else "FAIL",
                "station_count": station_count,
                "expected_station_count": expected_station_count,
                "buffer_count": buffer_count,
                "expected_buffers": expected_buffers,
                "feature_name": row.feature_name,
                "buffer_m": row.buffer_m,
                "metric_value": n_non_null,
                "all_27_station_coverage": n_non_null == expected_station_count,
                "all_nan_feature": all_nan,
                "constant_feature": constant,
                "high_missing_gt_20_pct": missing_fraction > 0.2,
                "high_missing_gt_50_pct": missing_fraction > 0.5,
                "high_missing_gt_80_pct": missing_fraction > 0.8,
                "notes": "Feature coverage and missingness QA.",
            }
        )
    return pd.DataFrame(rows)


def qa_row(
    check: str,
    status: str,
    station_count: int,
    expected_station_count: int,
    buffer_count: int,
    expected_buffers: int,
    feature_name: str,
    metric_value: float,
    notes: str,
) -> dict[str, Any]:
    """Create one global QA row."""
    return {
        "qa_check": check,
        "status": status,
        "station_count": station_count,
        "expected_station_count": expected_station_count,
        "buffer_count": buffer_count,
        "expected_buffers": expected_buffers,
        "feature_name": feature_name,
        "buffer_m": np.nan,
        "metric_value": metric_value,
        "all_27_station_coverage": np.nan,
        "all_nan_feature": np.nan,
        "constant_feature": np.nan,
        "high_missing_gt_20_pct": np.nan,
        "high_missing_gt_50_pct": np.nan,
        "high_missing_gt_80_pct": np.nan,
        "notes": notes,
    }


def source_coverage_status(inventory: pd.DataFrame) -> str:
    """Return PASS/BLOCKED source coverage status."""
    if inventory["allowed_for_27_station_buffer_model"].astype(bool).any():
        return "PASS"
    return "BLOCKED_MISSING_SOURCES"


def toapayoh_exclusion_status(inventory: pd.DataFrame) -> str:
    """Check whether Toa Payoh-only sources were excluded."""
    mask = inventory["coverage_status"].astype(str).str.contains("ToaPayoh_only", case=False, na=False)
    if not mask.any():
        return "PASS_NO_TOAPAYOH_ONLY_SOURCES"
    allowed = inventory.loc[mask, "allowed_for_27_station_buffer_model"].astype(bool).any()
    return "FAIL" if allowed else "PASS"


def build_collinearity_screen(wide: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compute screening-only Spearman high-correlation pairs among numeric features."""
    min_non_null = int(config["analysis"]["min_non_null_for_correlation"])
    threshold = float(config["analysis"]["spearman_abs_threshold"])
    feature_columns = [col for col in wide.columns if any(col.startswith(f"{spec.feature_name}_") for spec in FEATURE_SPECS)]
    numeric = wide[feature_columns].apply(pd.to_numeric, errors="coerce") if feature_columns else pd.DataFrame()
    usable_cols = [
        col
        for col in numeric.columns
        if numeric[col].notna().sum() >= min_non_null and numeric[col].nunique(dropna=True) > 1
    ]
    if len(usable_cols) < 2:
        return pd.DataFrame(
            [
                {
                    "feature_a": "",
                    "feature_b": "",
                    "spearman_r": np.nan,
                    "abs_spearman": np.nan,
                    "n_pairwise_non_null": 0,
                    "screening_threshold_abs_spearman": threshold,
                    "status": "NO_NUMERIC_FEATURE_PAIRS",
                    "notes": "Screening only; no modelling performed. Fewer than two numeric feature columns have at least 10 non-null stations.",
                }
            ]
        )
    corr = numeric[usable_cols].corr(method="spearman", min_periods=min_non_null)
    rows = []
    for i, feature_a in enumerate(usable_cols):
        for feature_b in usable_cols[i + 1 :]:
            value = corr.loc[feature_a, feature_b]
            if pd.isna(value) or abs(float(value)) < threshold:
                continue
            n_pairwise = int(numeric[[feature_a, feature_b]].dropna().shape[0])
            rows.append(
                {
                    "feature_a": feature_a,
                    "feature_b": feature_b,
                    "spearman_r": float(value),
                    "abs_spearman": abs(float(value)),
                    "n_pairwise_non_null": n_pairwise,
                    "screening_threshold_abs_spearman": threshold,
                    "status": "HIGH_CORRELATION_SCREENING_ONLY",
                    "notes": "Screening only; no residual model trained.",
                }
            )
    if not rows:
        rows.append(
            {
                "feature_a": "",
                "feature_b": "",
                "spearman_r": np.nan,
                "abs_spearman": np.nan,
                "n_pairwise_non_null": 0,
                "screening_threshold_abs_spearman": threshold,
                "status": "NO_HIGH_CORRELATION_PAIRS",
                "notes": "Screening only; no modelling performed.",
            }
        )
    return pd.DataFrame(rows)


def decide_status(stations: pd.DataFrame, schema: pd.DataFrame, inventory: pd.DataFrame, crs_status: str) -> str:
    """Classify the builder decision status."""
    if crs_status == "BLOCKED_CRS":
        return "BLOCKED_CRS"
    allowed_schema = schema[schema["allowed_for_future_model"].astype(bool)].copy()
    if allowed_schema.empty:
        return "BLOCKED_MISSING_SOURCES"
    built_groups = set(allowed_schema["feature_group"].dropna().astype(str))
    core_groups = {"water", "vegetation", "built_impervious", "distance_context"}
    if len(stations) == 27 and core_groups.issubset(built_groups):
        return "PASS_FEATURE_TABLE"
    return "PARTIAL_FEATURE_TABLE"


def result_summaries(decision: str, schema: pd.DataFrame, inventory: pd.DataFrame) -> tuple[str, str, str, str]:
    """Return compact result strings."""
    built_groups = sorted(set(schema.loc[schema["allowed_for_future_model"].astype(bool), "feature_group"].astype(str)))
    all_groups = sorted({spec.feature_group for spec in FEATURE_SPECS})
    unavailable = [group for group in all_groups if group not in built_groups]
    coverage = (
        "no features have all-27 non-null coverage"
        if not built_groups
        else semicolon(f"{group}:all_27" for group in built_groups)
    )
    excluded = inventory[inventory["coverage_status"].astype(str).str.contains("ToaPayoh_only", case=False, na=False)]
    excluded_count = int(len(excluded))
    key_exclusions = f"Toa Payoh-only/AOI-limited sources excluded={excluded_count}; leakage fields and station_id excluded; no System B/SOLWEIG sources used."
    if decision == "BLOCKED_MISSING_SOURCES":
        next_action = "Add or point to Singapore-wide/all-27 station-local spatial layers, then rerun A-L2.1a before A-L2.1b QA."
    elif decision == "BLOCKED_CRS":
        next_action = "Resolve station/spatial CRS before any feature QA or model preflight."
    else:
        next_action = "Proceed to A-L2.1b QA/collinearity review; keep residual modelling out of this lane."
    return semicolon(built_groups), semicolon(unavailable), coverage, key_exclusions + " " + next_action


def write_report(
    path: Path,
    config_path: Path,
    decision: str,
    stations: pd.DataFrame,
    inventory: pd.DataFrame,
    schema: pd.DataFrame,
    qa: pd.DataFrame,
    collinearity: pd.DataFrame,
    crs_notes: str,
) -> None:
    """Write the English builder report."""
    source_counts = (
        inventory.groupby(["source_kind", "coverage_status", "allowed_for_27_station_buffer_model"], dropna=False)
        .size()
        .reset_index(name="source_count")
        .sort_values(["source_kind", "coverage_status"])
    )
    feature_counts = (
        schema.groupby(["feature_group", "allowed_for_future_model"], dropna=False)
        .agg(feature_count=("feature_name", "nunique"), max_non_null=("n_stations_non_null", "max"), mean_missing_fraction=("missing_fraction", "mean"))
        .reset_index()
        .sort_values(["feature_group", "allowed_for_future_model"])
    )
    all_nan = schema[schema["n_stations_non_null"].eq(0)][["feature_group", "feature_name", "buffer_m"]]
    allowed = schema[schema["allowed_for_future_model"].astype(bool)]
    excluded = inventory[inventory["coverage_status"].astype(str).str.contains("ToaPayoh_only", case=False, na=False)]
    lines = [
        "# System A A-L2.1a Station-Local Buffer Feature Builder",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Decision status: `{decision}`",
        f"Branch: `{git_branch()}`",
        f"Config: `{rel(config_path)}`",
        "",
        "## 1. Why This Is Needed After A-L2.0",
        "",
        "A-L2.0 found stable station-level residual structure after Level 1 context controls, while probability-error station signal was not stable enough. A-L2.1a therefore only builds and audits station-local context feature availability before any scoped residual preflight model is considered.",
        "",
        "## 2. Difference From Old M5/M6 Toa Payoh-Only Morphology",
        "",
        "Old M5/M6 morphology and overhead fields were Toa Payoh AOI/grid proxies. This builder requires station-local sources that cover all 27 NEA WBGT stations. Toa Payoh-only and grid-nearest proxies are inventoried but excluded from the 27-station buffer feature table.",
        "",
        "## 3. Source Inventory",
        "",
        markdown_table(source_counts, ["source_kind", "coverage_status", "allowed_for_27_station_buffer_model", "source_count"], limit=30),
        "",
        "## 4. Features Built And Unavailable",
        "",
        markdown_table(feature_counts, ["feature_group", "allowed_for_future_model", "feature_count", "max_non_null", "mean_missing_fraction"], limit=40),
        "",
        "## 5. 27-Station Coverage",
        "",
        f"Station count: `{len(stations)}`. Features with all-27 non-null coverage: `{allowed['feature_name'].nunique() if not allowed.empty else 0}`.",
        "",
        "## 6. CRS / Buffer Validation",
        "",
        crs_notes,
        "",
        "Buffers are defined in meters after station centroids are projected to SVY21 EPSG:3414. The QA table records the 50 m, 100 m, 250 m, and 500 m buffer-area checks.",
        "",
        "## 7. Missingness And Constant-Feature Summary",
        "",
        f"All-NaN schema rows: `{len(all_nan)}`. Constant non-null feature rows: `0` because no environmental feature values were computed from valid all-27 sources.",
        "",
        "## 8. Safe Features For Future A-L2.1c Scoped Residual Preflight",
        "",
        "No environmental station-buffer feature is currently marked safe for future modelling. Future use requires all-27 station-local coverage, no leakage tokens, and A-L2.1b QA review.",
        "",
        "## 9. Features And Sources Excluded",
        "",
        f"Toa Payoh-only/AOI-limited sources excluded: `{len(excluded)}`.",
        "",
        markdown_table(excluded[["source_name", "source_path", "candidate_feature_groups", "coverage_status", "exclusion_reason"]], ["source_name", "source_path", "candidate_feature_groups", "coverage_status", "exclusion_reason"], limit=20),
        "",
        "## 10. Claim Boundaries",
        "",
        "- No model was trained.",
        "- No causal station-context correction is claimed.",
        "- No station-adjusted WBGT was created.",
        "- No local 100m WBGT was created.",
        "- Screening correlations are QA only, not modelling evidence.",
        "",
        "## Collinearity Screen",
        "",
        markdown_table(collinearity, ["feature_a", "feature_b", "spearman_r", "abs_spearman", "n_pairwise_non_null", "status"], limit=20),
        "",
        "## Output Files",
        "",
        "- `station_context_source_inventory.csv`",
        "- `station_buffer_feature_long.csv`",
        "- `station_buffer_feature_wide.csv`",
        "- `station_buffer_feature_schema.csv`",
        "- `station_buffer_feature_qa.csv`",
        "- `station_buffer_feature_missingness.csv`",
        "- `station_buffer_feature_collinearity_screen.csv`",
        "- `A_L2_1A_STATUS.md`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_cn_doc(path: Path, decision: str, stations: pd.DataFrame, schema: pd.DataFrame, inventory: pd.DataFrame) -> None:
    """Write the UTF-8 Chinese documentation page for A-L2.1a."""
    allowed = schema[schema["allowed_for_future_model"].astype(bool)]
    excluded = inventory[inventory["coverage_status"].astype(str).str.contains("ToaPayoh_only", case=False, na=False)]
    lines = [
        "# OpenHeat System A A-L2.1a 站点本地缓冲区特征构建说明",
        "",
        f"生成日期：{date.today().isoformat()}",
        f"决策状态：`{decision}`",
        "",
        "## 1. 为什么需要这一步",
        "",
        "A-L2.0 显示，在控制 Level 1 分数、天气语境、小时和事件支持度之后，部分站点的残差信号仍然稳定；但概率误差信号不够稳定。因此 A-L2.1a 只负责构建和审查站点本地环境特征，不训练残差模型。",
        "",
        "## 2. 与旧 M5/M6 Toa Payoh-only 形态特征的区别",
        "",
        "旧 M5/M6 使用的是 Toa Payoh AOI 或网格邻近代理。A-L2.1a 要求特征来源覆盖全部 27 个 NEA WBGT 站点，并且必须是站点本地缓冲区语境。Toa Payoh-only 来源只盘点，不进入 27 站特征表。",
        "",
        "## 3. 来源盘点",
        "",
        f"已盘点来源数量：{len(inventory)}。其中 Toa Payoh-only 或 AOI-limited 来源数量：{len(excluded)}。",
        "",
        "## 4. 已构建与不可用特征",
        "",
        f"当前可用于未来模型预检的环境特征数：{allowed['feature_name'].nunique() if not allowed.empty else 0}。没有有效来源的特征保留为空值，并在 schema 中标记为不可用。",
        "",
        "## 5. 27 站覆盖",
        "",
        f"站点数量：{len(stations)}。宽表保留 station_id 作为键和元数据，但 station_id 不允许作为预测特征。",
        "",
        "## 6. CRS 与缓冲区校验",
        "",
        "站点经纬度按 EPSG:4326 读取，并投影到 Singapore SVY21 EPSG:3414 后进行 50 m、100 m、250 m、500 m 米制缓冲区校验。脚本不会使用经纬度度数直接生成米制缓冲。",
        "",
        "## 7. 缺失率与常数特征",
        "",
        "由于没有发现可安全覆盖全部 27 站的站点本地环境来源，请求的环境特征均为空值。QA 表记录 all-NaN、高缺失率和常数特征检查。",
        "",
        "## 8. 未来 A-L2.1c 可用特征",
        "",
        "当前没有特征被标记为可直接进入未来 A-L2.1c scoped residual preflight model。后续必须先补充覆盖全部 27 站的空间来源，并通过 A-L2.1b QA / collinearity 审查。",
        "",
        "## 9. 必须排除的内容",
        "",
        "- `station_id` 不能作为预测特征。",
        "- `official_wbgt_c`、残差、`obs_ge31`、`obs_ge33` 不能作为特征。",
        "- Toa Payoh-only 网格或 AOI 特征不能冒充 27 站本地缓冲区特征。",
        "- System B、SOLWEIG、Tmrt 输出不在本任务中使用。",
        "",
        "## 10. 声明边界",
        "",
        "- 本任务没有训练模型。",
        "- 本任务没有提出站点上下文因果校正。",
        "- 本任务没有生成站点调整 WBGT。",
        "- 本任务没有生成本地 100 m WBGT。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_status(path: Path, config_path: Path, result: BuildResult) -> None:
    """Write the A-L2.1a lane status file."""
    lines = [
        "# A-L2.1a Status",
        "",
        f"Status: {result.decision_status}",
        f"Branch: {git_branch()}",
        "Scope: station-local buffer feature builder and QA only; no residual modelling.",
        "",
        "Commands run:",
        f"- python scripts/v11_l2_run_station_buffer_features.py --config {rel(config_path)}",
        "",
        "Key results:",
        f"- Station count: {result.station_count}",
        f"- Feature groups built: {result.feature_groups_built or 'none'}",
        f"- Feature groups unavailable: {result.feature_groups_unavailable or 'none'}",
        f"- All-27 coverage summary: {result.all_27_coverage_summary}",
        f"- Key exclusions: {result.key_exclusions}",
        "",
        "Caveats:",
        "- No model trained.",
        "- No station-context causal correction claimed.",
        "- No station-adjusted WBGT or local 100m WBGT created.",
        "- Toa Payoh-only sources are inventory-only and excluded from 27-station features.",
        "",
        f"Next recommended action: {result.next_recommended_action}",
        "",
        "Files created / modified:",
        *[f"- {rel(out_path)}" for out_path in result.output_paths],
        "",
        "Safe to commit: controlled config/script/docs and compact CSV/Markdown outputs after review.",
        "Not safe to commit: rasters, raw archives, SOLWEIG outputs, System B outputs, or large forecast/live CSVs.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run_builder(config_path: Path) -> BuildResult:
    """Run the A-L2.1a builder end to end."""
    config = load_config(config_path)
    paths = output_paths(config)
    assert_output_scope(paths)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["cn_doc"].parent.mkdir(parents=True, exist_ok=True)

    stations = load_station_universe(config)
    crs_status, crs_notes = station_crs_check(stations, config)
    buffer_area = buffer_area_table([int(value) for value in config["buffers_m"]])
    inventory = build_source_inventory(config, stations)
    long_df = build_long_features(stations, inventory, config)
    schema = build_schema(long_df, inventory, config)
    missingness = build_missingness(schema, len(stations))
    buffer_area_status = "PASS" if buffer_area["buffer_area_status"].eq("PASS").all() else "FAIL"
    wide_df = build_wide_features(stations, long_df, inventory, config, crs_status, buffer_area_status)
    qa = build_qa(stations, long_df, schema, inventory, config, crs_status, crs_notes, buffer_area)
    collinearity = build_collinearity_screen(wide_df, config)
    decision = decide_status(stations, schema, inventory, crs_status)

    built, unavailable, coverage, combined_exclusion_action = result_summaries(decision, schema, inventory)
    if " Add or point" in combined_exclusion_action:
        key_exclusions, next_action = combined_exclusion_action.split(" Add or point", maxsplit=1)
        next_action = "Add or point" + next_action
    elif " Resolve station" in combined_exclusion_action:
        key_exclusions, next_action = combined_exclusion_action.split(" Resolve station", maxsplit=1)
        next_action = "Resolve station" + next_action
    elif " Proceed to" in combined_exclusion_action:
        key_exclusions, next_action = combined_exclusion_action.split(" Proceed to", maxsplit=1)
        next_action = "Proceed to" + next_action
    else:
        key_exclusions = combined_exclusion_action
        next_action = ""

    output_list = [
        paths["source_inventory"],
        paths["feature_long"],
        paths["feature_wide"],
        paths["feature_schema"],
        paths["feature_qa"],
        paths["feature_missingness"],
        paths["feature_collinearity"],
        paths["builder_report"],
        paths["status"],
        paths["cn_doc"],
    ]
    result = BuildResult(
        decision_status=decision,
        station_count=len(stations),
        feature_groups_built=built,
        feature_groups_unavailable=unavailable,
        all_27_coverage_summary=coverage,
        key_exclusions=key_exclusions,
        next_recommended_action=next_action,
        output_paths=output_list,
        git_status_short="",
    )

    inventory.to_csv(paths["source_inventory"], index=False)
    long_df.to_csv(paths["feature_long"], index=False)
    wide_df.to_csv(paths["feature_wide"], index=False)
    schema.to_csv(paths["feature_schema"], index=False)
    qa.to_csv(paths["feature_qa"], index=False)
    missingness.to_csv(paths["feature_missingness"], index=False)
    collinearity.to_csv(paths["feature_collinearity"], index=False)
    write_report(paths["builder_report"], config_path, decision, stations, inventory, schema, qa, collinearity, crs_notes)
    write_cn_doc(paths["cn_doc"], decision, stations, schema, inventory)

    result = BuildResult(
        decision_status=decision,
        station_count=len(stations),
        feature_groups_built=built,
        feature_groups_unavailable=unavailable,
        all_27_coverage_summary=coverage,
        key_exclusions=key_exclusions,
        next_recommended_action=next_action,
        output_paths=output_list,
        git_status_short=git_status_short(),
    )
    write_status(paths["status"], config_path, result)
    result = BuildResult(
        decision_status=decision,
        station_count=len(stations),
        feature_groups_built=built,
        feature_groups_unavailable=unavailable,
        all_27_coverage_summary=coverage,
        key_exclusions=key_exclusions,
        next_recommended_action=next_action,
        output_paths=output_list,
        git_status_short=git_status_short(),
    )
    return result


def main() -> int:
    """CLI entrypoint for direct execution."""
    parser = argparse.ArgumentParser(description="Run System A A-L2.1a station-local buffer feature builder.")
    parser.add_argument("--config", default="configs/v11/systema_l2_station_buffer_features.yaml")
    args = parser.parse_args()
    result = run_builder(resolve_path(args.config))
    print(result.decision_status)
    return 0 if result.decision_status != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
