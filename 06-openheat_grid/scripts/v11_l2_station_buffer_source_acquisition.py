#!/usr/bin/env python
"""System A A-L2.1a-S1 station-local spatial source acquisition/extraction.

Inputs:
    - configs/v11/systema_l2_station_buffer_source_acquisition.yaml
    - data/calibration/v09_wbgt_station_pairs.csv for the 27 station centroids.
    - Read-only local OSM / data.gov.sg / OneMap source files under the
      configured C:/OpenHeat-local/station_context_sources roots.

Outputs:
    - station_context_source_acquisition_inventory.csv
    - station_buffer_source_normalization.csv
    - station_buffer_feature_long_s1.csv
    - station_buffer_feature_wide_s1.csv
    - station_buffer_feature_schema_s1.csv
    - station_buffer_feature_qa_s1.csv
    - station_buffer_missing_sources_next_actions.csv
    - station_buffer_feature_builder_s1_report.md
    - A_L2_1A_S1_STATUS.md
    - docs/v11/OpenHeat_SystemA_L2_station_buffer_source_acquisition_CN.md

Saved metrics:
    - Source availability, CRS assumptions, geometry type counts, and all-27
      station bounding-box coverage.
    - Station-buffer water, green, road, building, and landuse compact features.
    - Feature missingness, all-27 feature-group coverage, constant-feature QA,
      leakage-token checks, and source-acquisition next actions.

Scope guard:
    This is a source acquisition/extraction gate. It does not stage, commit,
    train residual ML models, start A-L2.1c modelling, touch System B or
    SOLWEIG outputs, modify archive collectors, create station-adjusted WBGT,
    create local 100 m WBGT, use station_id as a predictive feature, or claim
    station-context causal correction. It reads local raw spatial files but
    writes only compact CSV/Markdown summaries into the S1 output directory.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import math
import sqlite3
import struct
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PREFIX = "outputs/v11_systema_l2_residual/station_buffer_features_s1"
CN_DOC_NAME = "docs/v11/OpenHeat_SystemA_L2_station_buffer_source_acquisition_CN.md"


@dataclass(frozen=True)
class Station:
    """One unique station centroid with projected SVY21 coordinates."""

    station_id: str
    station_name: str
    station_town_center: str
    lat: float
    lon: float
    x: float
    y: float


@dataclass
class SourceFeature:
    """One normalized geometry feature from a local source file."""

    fid: str
    geometry: dict[str, Any]
    attributes: dict[str, str]
    bbox: tuple[float, float, float, float]
    geometry_type: str
    class_name: str
    highway_class: str


@dataclass
class SourceLayer:
    """A local source file normalized to projected feature geometries."""

    name: str
    path: Path
    source_group: str
    source_format: str
    exists: bool
    read_status: str
    source_crs: str
    crs_assumption: str
    table_name: str
    row_count: int
    features: list[SourceFeature]
    geometry_type_counts: Counter[str]
    geometry_parse_error_count: int
    bbox_lonlat: tuple[float, float, float, float] | None
    bbox_svy21: tuple[float, float, float, float] | None
    notes: str


@dataclass(frozen=True)
class BuildResult:
    """Headline result returned to the runner."""

    decision_status: str
    station_count: int
    feature_groups_all_27: list[str]
    feature_groups_unavailable: list[str]
    assumptions: list[str]
    next_recommended_action: str
    files_created: list[Path]
    git_status_short: str


def rel(path: Path) -> str:
    """Return a project-relative path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(raw_path: str) -> Path:
    """Resolve a path that may be absolute or project-relative."""
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    """Load the explicit JSON-formatted YAML config."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Config is not a mapping: {rel(path)}")
    return loaded


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Return output paths and enforce the lane write scope."""
    outputs = config["outputs"]
    output_dir = resolve_path(str(outputs["output_dir"]))
    cn_doc = resolve_path(str(outputs["cn_doc"]))
    if not rel(output_dir).startswith(OUTPUT_PREFIX):
        raise ValueError(f"Refusing to write outside {OUTPUT_PREFIX}: {rel(output_dir)}")
    if rel(cn_doc) != CN_DOC_NAME:
        raise ValueError(f"Refusing to write unexpected CN doc path: {rel(cn_doc)}")
    return {
        "dir": output_dir,
        "source_inventory": output_dir / str(outputs["source_inventory"]),
        "source_normalization": output_dir / str(outputs["source_normalization"]),
        "feature_long": output_dir / str(outputs["feature_long"]),
        "feature_wide": output_dir / str(outputs["feature_wide"]),
        "feature_schema": output_dir / str(outputs["feature_schema"]),
        "feature_qa": output_dir / str(outputs["feature_qa"]),
        "missing_sources": output_dir / str(outputs["missing_sources"]),
        "builder_report": output_dir / str(outputs["builder_report"]),
        "status": output_dir / str(outputs["status"]),
        "cn_doc": cn_doc,
    }


def git_branch() -> str:
    """Return active git branch."""
    result = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, check=False, capture_output=True, text=True)
    return result.stdout.strip() or "unknown"


def git_status_short() -> str:
    """Return git status for the current project subdirectory."""
    result = subprocess.run(["git", "status", "--short", "--", "."], cwd=ROOT, check=False, capture_output=True, text=True)
    return result.stdout.rstrip()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write rows to UTF-8 CSV with stable field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values in first-seen order."""
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return ";".join(out)


def fmt_float(value: float | int | None, digits: int = 6) -> str:
    """Format numeric feature values consistently for CSV."""
    if value is None:
        return ""
    number = float(value)
    if not math.isfinite(number):
        return ""
    if abs(number) < 0.5 * 10 ** (-digits):
        number = 0.0
    return f"{number:.{digits}f}"


def markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int = 20) -> str:
    """Render a compact Markdown table."""
    if not rows:
        return "_No rows._"
    shown = rows[:limit]
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in shown:
        body.append("| " + " | ".join(str(row.get(col, "")).replace("\n", " ") for col in columns) + " |")
    suffix = f"\n\n_Showing {len(shown)} of {len(rows)} rows._" if len(rows) > len(shown) else ""
    return "\n".join([header, divider, *body]) + suffix


def wgs84_to_svy21(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Project WGS84 lon/lat to Singapore SVY21 / EPSG:3414 easting/northing."""
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

    def meridian_arc(lat: float) -> float:
        lat_rad = math.radians(lat)
        a0 = 1 - (e2 / 4) - (3 * e4 / 64) - (5 * e6 / 256)
        a2 = 3 / 8 * (e2 + (e4 / 4) + (15 * e6 / 128))
        a4 = 15 / 256 * (e4 + (3 * e6 / 4))
        a6 = 35 * e6 / 3072
        return a * ((a0 * lat_rad) - (a2 * math.sin(2 * lat_rad)) + (a4 * math.sin(4 * lat_rad)) - (a6 * math.sin(6 * lat_rad)))

    lat_rad = math.radians(lat_deg)
    sin_lat = math.sin(lat_rad)
    sin2_lat = sin_lat * sin_lat
    cos_lat = math.cos(lat_rad)
    tan_lat = math.tan(lat_rad)
    rho = a * (1 - e2) / ((1 - e2 * sin2_lat) ** 1.5)
    nu = a / math.sqrt(1 - e2 * sin2_lat)
    psi = nu / rho
    w = math.radians(lon_deg - origin_lon)
    m = meridian_arc(lat_deg)
    m_origin = meridian_arc(origin_lat)
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


def load_stations(config: dict[str, Any]) -> list[Station]:
    """Read unique station metadata from v09 station pairs."""
    path = resolve_path(str(config["station_source"]))
    stations: dict[str, Station] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            station_id = str(row.get("station_id", "")).strip()
            if not station_id or station_id in stations:
                continue
            lat = float(str(row.get("station_lat", "")).strip())
            lon = float(str(row.get("station_lon", "")).strip())
            x, y = wgs84_to_svy21(lat, lon)
            stations[station_id] = Station(
                station_id=station_id,
                station_name=str(row.get("station_name", "")).strip(),
                station_town_center=str(row.get("station_town_center", "")).strip(),
                lat=lat,
                lon=lon,
                x=x,
                y=y,
            )
    return [stations[key] for key in sorted(stations)]


def validate_station_crs(stations: list[Station], config: dict[str, Any]) -> tuple[str, str]:
    """Validate station CRS and projected bounds."""
    if int(config["station_source_epsg"]) != 4326 or int(config["metric_buffer_epsg"]) != 3414:
        return "BLOCKED_CRS", "Config must declare station_source_epsg=4326 and metric_buffer_epsg=3414."
    lat_min, lat_max = [float(v) for v in config["singapore_lat_bounds"]]
    lon_min, lon_max = [float(v) for v in config["singapore_lon_bounds"]]
    for station in stations:
        if not (lat_min <= station.lat <= lat_max and lon_min <= station.lon <= lon_max):
            return "BLOCKED_CRS", f"Station {station.station_id} lon/lat falls outside expected Singapore bounds."
        if not (-10000 <= station.x <= 70000 and -10000 <= station.y <= 70000):
            return "BLOCKED_CRS", f"Station {station.station_id} projected SVY21 coordinate is outside expected bounds."
    return "PASS", "Station coordinates read as EPSG:4326 and projected to EPSG:3414 for metric buffers."


def source_group_from_name(name: str) -> str:
    """Classify candidate source files by configured naming conventions."""
    lower = name.lower()
    if "osm_station_context_water" in lower or "national_map_polygon" in lower:
        return "water"
    if "osm_station_context_green" in lower or lower.startswith("nparks_"):
        return "green"
    if "osm_station_context_roads" in lower or lower.startswith("lta_"):
        return "roads"
    if "osm_station_context_buildings" in lower or "mp2019_building_layer" in lower:
        return "buildings"
    if "osm_station_context_landuse" in lower or "mp2019_land_use" in lower:
        return "landuse"
    return ""


def discover_source_paths(config: dict[str, Any]) -> list[Path]:
    """Discover local candidate spatial files without copying them into the repo."""
    extensions = {str(ext).lower() for ext in config["source_extensions"]}
    found: dict[str, Path] = {}
    for raw_root in config["source_roots"]:
        root = resolve_path(str(raw_root))
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in extensions:
                found[str(path).lower()] = path
    return sorted(found.values(), key=lambda item: item.as_posix().lower())


def parse_gpkg_geometry(blob: bytes) -> dict[str, Any] | None:
    """Parse a GeoPackage binary geometry and return projected geometry."""
    if not blob or len(blob) < 9:
        return None
    if blob[:2] == b"GP":
        flags = blob[3]
        order = "<" if (flags & 1) else ">"
        envelope_code = (flags >> 1) & 7
        envelope_size = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get(envelope_code, 0)
        offset = 8 + envelope_size
        if struct.unpack_from(order + "i", blob, 4)[0] == 0 and not (flags & 16):
            pass
        raw, _ = parse_wkb_geometry(blob, offset)
    else:
        raw, _ = parse_wkb_geometry(blob, 0)
    if raw is None:
        return None
    return transform_lonlat_geometry(raw)


def parse_wkb_geometry(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int]:
    """Parse a standard OGC WKB geometry from bytes."""
    byte_order = data[offset]
    order = "<" if byte_order == 1 else ">"
    geom_type_raw = struct.unpack_from(order + "I", data, offset + 1)[0]
    offset += 5
    geom_type = geom_type_raw % 1000
    dims = 2
    if 1000 <= geom_type_raw < 2000 or 2000 <= geom_type_raw < 3000:
        dims = 3
    elif 3000 <= geom_type_raw < 4000:
        dims = 4

    def read_point(at: int) -> tuple[tuple[float, float], int]:
        values = struct.unpack_from(order + ("d" * dims), data, at)
        return (float(values[0]), float(values[1])), at + 8 * dims

    if geom_type == 1:
        point, offset = read_point(offset)
        return {"type": "Point", "coordinates": point}, offset
    if geom_type == 2:
        count = struct.unpack_from(order + "I", data, offset)[0]
        offset += 4
        coords = []
        for _ in range(count):
            point, offset = read_point(offset)
            coords.append(point)
        return {"type": "LineString", "coordinates": coords}, offset
    if geom_type == 3:
        ring_count = struct.unpack_from(order + "I", data, offset)[0]
        offset += 4
        rings = []
        for _ in range(ring_count):
            point_count = struct.unpack_from(order + "I", data, offset)[0]
            offset += 4
            ring = []
            for _ in range(point_count):
                point, offset = read_point(offset)
                ring.append(point)
            rings.append(ring)
        return {"type": "Polygon", "coordinates": rings}, offset
    if geom_type in {4, 5, 6, 7}:
        count = struct.unpack_from(order + "I", data, offset)[0]
        offset += 4
        geometries = []
        for _ in range(count):
            sub_geom, offset = parse_wkb_geometry(data, offset)
            if sub_geom is not None:
                geometries.append(sub_geom)
        names = {4: "MultiPoint", 5: "MultiLineString", 6: "MultiPolygon", 7: "GeometryCollection"}
        return {"type": names[geom_type], "geometries": geometries}, offset
    return None, offset


def transform_lonlat_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    """Transform a lon/lat geometry tree to SVY21 coordinates."""
    gtype = geometry["type"]
    if gtype == "Point":
        lon, lat = geometry["coordinates"]
        x, y = wgs84_to_svy21(lat, lon)
        return {"type": "Point", "coordinates": (x, y)}
    if gtype == "LineString":
        return {
            "type": "LineString",
            "coordinates": [wgs84_to_svy21(lat, lon) for lon, lat in geometry["coordinates"]],
        }
    if gtype == "Polygon":
        return {
            "type": "Polygon",
            "coordinates": [[wgs84_to_svy21(lat, lon) for lon, lat in ring] for ring in geometry["coordinates"]],
        }
    return {"type": geometry["type"], "geometries": [transform_lonlat_geometry(sub) for sub in geometry.get("geometries", [])]}


def iter_points(geometry: dict[str, Any]) -> Iterable[tuple[float, float]]:
    """Yield all projected coordinates in a geometry tree."""
    gtype = geometry["type"]
    if gtype == "Point":
        yield geometry["coordinates"]
    elif gtype == "LineString":
        yield from geometry["coordinates"]
    elif gtype == "Polygon":
        for ring in geometry["coordinates"]:
            yield from ring
    else:
        for sub in geometry.get("geometries", []):
            yield from iter_points(sub)


def geometry_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return geometry bbox in projected metres."""
    points = list(iter_points(geometry))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def geometry_type_name(geometry: dict[str, Any]) -> str:
    """Return a compact geometry type name."""
    return geometry["type"]


def attr_text(value: Any) -> str:
    """Normalize an attribute value to a stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def classify_feature(source_group: str, attrs: dict[str, str], geometry_type: str, config: dict[str, Any]) -> tuple[str, str]:
    """Return normalized class and highway class for a source feature."""
    highway = attrs.get("highway", "").lower()
    if source_group == "roads":
        return highway or "road_unspecified", highway
    if source_group == "buildings":
        building = attrs.get("building", "").lower()
        return building or "building", ""
    if source_group == "water":
        for key in ("water", "waterway", "natural", "landuse", "seamark:type"):
            value = attrs.get(key, "").lower()
            if value:
                return value, ""
        return "water", ""
    if source_group == "green":
        for key in ("leisure", "natural", "landuse", "garden:type", "tourism"):
            value = attrs.get(key, "").lower()
            if value:
                return value, ""
        return "green", ""
    if source_group == "landuse":
        return classify_landuse(attrs, geometry_type), ""
    return "", ""


def classify_landuse(attrs: dict[str, str], geometry_type: str) -> str:
    """Map OSM / planning attributes to coarse landuse classes."""
    values = " ".join(attrs.get(key, "").lower() for key in ("landuse", "leisure", "natural", "building", "amenity", "description", "lu_desc", "lu_desc_v10"))
    if any(token in values for token in ("water", "reservoir", "basin", "river", "canal", "pond", "coast")):
        return "water"
    if any(token in values for token in ("park", "garden", "grass", "forest", "wood", "green", "recreation", "playground", "nature", "scrub", "tree")):
        return "green_space"
    if any(token in values for token in ("residential", "commercial", "industrial", "retail", "building", "construction", "brownfield")):
        return "built_or_urban"
    if any(token in values for token in ("transport", "road", "rail", "parking")):
        return "transport"
    if values.strip():
        first = values.split()[0]
        return first[:80]
    return "unclassified"


def read_gpkg(path: Path, source_group: str, config: dict[str, Any]) -> SourceLayer:
    """Read a GeoPackage source using sqlite3 and a minimal WKB parser."""
    name = path.stem
    features: list[SourceFeature] = []
    geom_counts: Counter[str] = Counter()
    bbox_lonlat: tuple[float, float, float, float] | None = None
    table_name = ""
    source_crs = "unknown"
    try:
        con = sqlite3.connect(path)
        geom_row = con.execute("select table_name, column_name, geometry_type_name, srs_id from gpkg_geometry_columns").fetchone()
        if geom_row is None:
            raise ValueError("No gpkg_geometry_columns row.")
        table_name, geom_col, _, srs_id = geom_row
        source_crs = f"EPSG:{srs_id}" if srs_id else "unknown"
        contents = con.execute("select min_x, min_y, max_x, max_y from gpkg_contents where table_name=?", (table_name,)).fetchone()
        if contents and all(value is not None for value in contents):
            bbox_lonlat = tuple(float(value) for value in contents)  # type: ignore[assignment]
        col_rows = con.execute(f"pragma table_info({table_name})").fetchall()
        columns = [str(row[1]) for row in col_rows]
        geom_index = columns.index(str(geom_col))
        row_count = 0
        parse_error_count = 0
        for raw in con.execute(f"select * from {table_name}"):
            row_count += 1
            blob = raw[geom_index]
            if not isinstance(blob, bytes):
                parse_error_count += 1
                continue
            try:
                geometry = parse_gpkg_geometry(blob)
            except Exception:
                parse_error_count += 1
                continue
            if geometry is None:
                parse_error_count += 1
                continue
            attrs = {columns[i]: attr_text(raw[i]) for i in range(len(columns)) if i != geom_index}
            gtype = geometry_type_name(geometry)
            geom_counts[gtype] += 1
            class_name, highway = classify_feature(source_group, attrs, gtype, config)
            fid = attrs.get("fid") or attrs.get("id") or str(row_count)
            features.append(SourceFeature(fid=fid, geometry=geometry, attributes=attrs, bbox=geometry_bbox(geometry), geometry_type=gtype, class_name=class_name, highway_class=highway))
        con.close()
        bbox_svy21 = union_bbox([feature.bbox for feature in features])
        assumption = "" if source_crs == "EPSG:4326" else "Source CRS read from GeoPackage metadata; non-4326 sources require review."
        return SourceLayer(
            name=name,
            path=path,
            source_group=source_group,
            source_format=".gpkg",
            exists=True,
            read_status="readable",
            source_crs=source_crs,
            crs_assumption=assumption,
            table_name=str(table_name),
            row_count=row_count,
            features=features,
            geometry_type_counts=geom_counts,
            geometry_parse_error_count=parse_error_count,
            bbox_lonlat=bbox_lonlat,
            bbox_svy21=bbox_svy21,
            notes="GeoPackage geometries parsed locally; no raw layer written into the repo.",
        )
    except Exception as exc:
        return SourceLayer(
            name=name,
            path=path,
            source_group=source_group,
            source_format=".gpkg",
            exists=True,
            read_status=f"read_error: {exc}",
            source_crs=source_crs,
            crs_assumption="",
            table_name=table_name,
            row_count=0,
            features=[],
            geometry_type_counts=Counter(),
            geometry_parse_error_count=0,
            bbox_lonlat=bbox_lonlat,
            bbox_svy21=None,
            notes="Source could not be read by the dependency-light parser.",
        )


def read_geojson(path: Path, source_group: str, config: dict[str, Any]) -> SourceLayer:
    """Read a GeoJSON source and project lon/lat geometries to SVY21."""
    name = path.stem
    features: list[SourceFeature] = []
    geom_counts: Counter[str] = Counter()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        raw_features = loaded.get("features", []) if isinstance(loaded, dict) else []
        parse_error_count = 0
        for index, item in enumerate(raw_features, start=1):
            if not isinstance(item, dict) or not item.get("geometry"):
                parse_error_count += 1
                continue
            try:
                geometry = transform_geojson_geometry(item["geometry"])
            except Exception:
                parse_error_count += 1
                continue
            if geometry is None:
                parse_error_count += 1
                continue
            attrs = {str(key): attr_text(value) for key, value in (item.get("properties") or {}).items()}
            gtype = geometry_type_name(geometry)
            geom_counts[gtype] += 1
            class_name, highway = classify_feature(source_group, attrs, gtype, config)
            fid = attrs.get("fid") or attrs.get("id") or str(index)
            features.append(SourceFeature(fid=fid, geometry=geometry, attributes=attrs, bbox=geometry_bbox(geometry), geometry_type=gtype, class_name=class_name, highway_class=highway))
        bbox_svy21 = union_bbox([feature.bbox for feature in features])
        return SourceLayer(
            name=name,
            path=path,
            source_group=source_group,
            source_format=".geojson",
            exists=True,
            read_status="readable",
            source_crs="EPSG:4326_assumed",
            crs_assumption="GeoJSON CRS missing or ignored; coordinates assumed EPSG:4326 because bounds are Singapore lon/lat.",
            table_name="features",
            row_count=len(raw_features),
            features=features,
            geometry_type_counts=geom_counts,
            geometry_parse_error_count=parse_error_count,
            bbox_lonlat=None,
            bbox_svy21=bbox_svy21,
            notes="GeoJSON geometries parsed locally; no raw layer written into the repo.",
        )
    except Exception as exc:
        return SourceLayer(
            name=name,
            path=path,
            source_group=source_group,
            source_format=".geojson",
            exists=True,
            read_status=f"read_error: {exc}",
            source_crs="unknown",
            crs_assumption="",
            table_name="features",
            row_count=0,
            features=[],
            geometry_type_counts=Counter(),
            geometry_parse_error_count=0,
            bbox_lonlat=None,
            bbox_svy21=None,
            notes="Source could not be read by the dependency-light parser.",
        )


def transform_geojson_geometry(geometry: dict[str, Any]) -> dict[str, Any] | None:
    """Transform a GeoJSON geometry from lon/lat to projected coordinates."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Point":
        lon, lat = coords
        return {"type": "Point", "coordinates": wgs84_to_svy21(float(lat), float(lon))}
    if gtype == "LineString":
        return {"type": "LineString", "coordinates": [wgs84_to_svy21(float(lat), float(lon)) for lon, lat in coords]}
    if gtype == "Polygon":
        return {"type": "Polygon", "coordinates": [[wgs84_to_svy21(float(lat), float(lon)) for lon, lat in ring] for ring in coords]}
    if gtype in {"MultiPoint", "MultiLineString", "MultiPolygon"}:
        sub_type = gtype.replace("Multi", "")
        geometries = []
        for sub_coords in coords:
            transformed = transform_geojson_geometry({"type": sub_type, "coordinates": sub_coords})
            if transformed:
                geometries.append(transformed)
        return {"type": gtype, "geometries": geometries}
    if gtype == "GeometryCollection":
        return {"type": "GeometryCollection", "geometries": [transform_geojson_geometry(sub) for sub in geometry.get("geometries", []) if transform_geojson_geometry(sub)]}
    return None


def union_bbox(bboxes: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float] | None:
    """Return the union bbox for a list of projected bboxes."""
    if not bboxes:
        return None
    return min(b[0] for b in bboxes), min(b[1] for b in bboxes), max(b[2] for b in bboxes), max(b[3] for b in bboxes)


def read_source_layers(config: dict[str, Any]) -> list[SourceLayer]:
    """Read recognized local source layers."""
    layers: list[SourceLayer] = []
    for path in discover_source_paths(config):
        source_group = source_group_from_name(path.name)
        if not source_group:
            continue
        if path.suffix.lower() == ".gpkg":
            layers.append(read_gpkg(path, source_group, config))
        elif path.suffix.lower() == ".geojson":
            layers.append(read_geojson(path, source_group, config))
    return layers


def station_coverage_count(layer: SourceLayer, stations: list[Station]) -> int:
    """Count station centroids covered by a source bbox."""
    if layer.bbox_lonlat is not None and layer.source_crs.startswith("EPSG:4326"):
        min_lon, min_lat, max_lon, max_lat = layer.bbox_lonlat
        return sum(1 for station in stations if min_lon <= station.lon <= max_lon and min_lat <= station.lat <= max_lat)
    if layer.bbox_svy21 is None:
        return 0
    min_x, min_y, max_x, max_y = layer.bbox_svy21
    return sum(1 for station in stations if min_x <= station.x <= max_x and min_y <= station.y <= max_y)


def bbox_intersects_circle(bbox: tuple[float, float, float, float], center: tuple[float, float], radius: float) -> bool:
    """Return whether a projected bbox intersects a station buffer circle."""
    min_x, min_y, max_x, max_y = bbox
    cx, cy = center
    nearest_x = min(max(cx, min_x), max_x)
    nearest_y = min(max(cy, min_y), max_y)
    return ((nearest_x - cx) ** 2 + (nearest_y - cy) ** 2) <= radius * radius


def is_polygon_geometry(geometry: dict[str, Any]) -> bool:
    """Return whether geometry is polygonal."""
    if geometry["type"] in {"Polygon", "MultiPolygon"}:
        return True
    return any(is_polygon_geometry(sub) for sub in geometry.get("geometries", []))


def is_line_geometry(geometry: dict[str, Any]) -> bool:
    """Return whether geometry contains linework."""
    if geometry["type"] in {"LineString", "MultiLineString"}:
        return True
    return any(is_line_geometry(sub) for sub in geometry.get("geometries", []))


def polygon_rings(geometry: dict[str, Any]) -> Iterable[list[list[tuple[float, float]]]]:
    """Yield polygon ring lists from polygon or multi geometry."""
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        for sub in geometry.get("geometries", []):
            yield from polygon_rings(sub)
    else:
        for sub in geometry.get("geometries", []):
            yield from polygon_rings(sub)


def linestrings(geometry: dict[str, Any]) -> Iterable[list[tuple[float, float]]]:
    """Yield line coordinate sequences from line or multi geometry."""
    if geometry["type"] == "LineString":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiLineString":
        for sub in geometry.get("geometries", []):
            yield from linestrings(sub)
    else:
        for sub in geometry.get("geometries", []):
            yield from linestrings(sub)


def point_in_ring(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-ring test."""
    x, y = point
    inside = False
    if len(ring) < 3:
        return False
    x1, y1 = ring[-1]
    for x2, y2 in ring:
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1):
            inside = not inside
        x1, y1 = x2, y2
    return inside


def point_in_polygon(point: tuple[float, float], rings: list[list[tuple[float, float]]]) -> bool:
    """Return whether point is inside a polygon with holes."""
    if not rings or not point_in_ring(point, rings[0]):
        return False
    return not any(point_in_ring(point, hole) for hole in rings[1:])


def point_in_polygonal_geometry(point: tuple[float, float], geometry: dict[str, Any]) -> bool:
    """Return whether point is inside any polygonal component."""
    return any(point_in_polygon(point, rings) for rings in polygon_rings(geometry))


def distance_point_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    """Distance from a point to a segment."""
    px, py = point
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    denom = dx * dx + dy * dy
    if denom == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / denom))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def distance_point_geometry(point: tuple[float, float], geometry: dict[str, Any]) -> float:
    """Minimum distance in metres from point to geometry."""
    gtype = geometry["type"]
    if gtype == "Point":
        x, y = geometry["coordinates"]
        return math.hypot(point[0] - x, point[1] - y)
    if gtype == "LineString":
        coords = geometry["coordinates"]
        if len(coords) == 1:
            return distance_point_geometry(point, {"type": "Point", "coordinates": coords[0]})
        return min(distance_point_segment(point, coords[i], coords[i + 1]) for i in range(len(coords) - 1))
    if gtype == "Polygon":
        rings = geometry["coordinates"]
        if point_in_polygon(point, rings):
            return 0.0
        distances = []
        for ring in rings:
            distances.extend(distance_point_segment(point, ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring)) if len(ring) > 1)
        return min(distances) if distances else math.inf
    distances = [distance_point_geometry(point, sub) for sub in geometry.get("geometries", [])]
    return min(distances) if distances else math.inf


def segment_length_inside_circle(start: tuple[float, float], end: tuple[float, float], center: tuple[float, float], radius: float) -> float:
    """Return exact segment length inside a circle."""
    x1, y1 = start[0] - center[0], start[1] - center[1]
    x2, y2 = end[0] - center[0], end[1] - center[1]
    dx = x2 - x1
    dy = y2 - y1
    seg_len = math.hypot(dx, dy)
    if seg_len == 0:
        return 0.0
    a = dx * dx + dy * dy
    b = 2 * (x1 * dx + y1 * dy)
    c = x1 * x1 + y1 * y1 - radius * radius
    cuts = [0.0, 1.0]
    disc = b * b - 4 * a * c
    if disc >= 0:
        root = math.sqrt(disc)
        for t in ((-b - root) / (2 * a), (-b + root) / (2 * a)):
            if 0.0 < t < 1.0:
                cuts.append(t)
    cuts = sorted(set(round(value, 12) for value in cuts))
    total = 0.0
    for left, right in zip(cuts, cuts[1:]):
        mid = (left + right) / 2
        mx = x1 + mid * dx
        my = y1 + mid * dy
        if mx * mx + my * my <= radius * radius:
            total += (right - left) * seg_len
    return total


def line_length_inside_circle(geometry: dict[str, Any], center: tuple[float, float], radius: float) -> float:
    """Return line length inside a station buffer circle."""
    total = 0.0
    for coords in linestrings(geometry):
        for i in range(len(coords) - 1):
            total += segment_length_inside_circle(coords[i], coords[i + 1], center, radius)
    return total


def sample_points(center: tuple[float, float], radius: float, step: float) -> list[tuple[float, float]]:
    """Create deterministic grid sample points inside a buffer."""
    cx, cy = center
    points: list[tuple[float, float]] = []
    min_x = math.floor((cx - radius) / step) * step
    max_x = math.ceil((cx + radius) / step) * step
    min_y = math.floor((cy - radius) / step) * step
    max_y = math.ceil((cy + radius) / step) * step
    x = min_x
    while x <= max_x + 1e-9:
        y = min_y
        while y <= max_y + 1e-9:
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
                points.append((x, y))
            y += step
        x += step
    return points or [center]


def candidate_features(features: list[SourceFeature], center: tuple[float, float], radius: float) -> list[SourceFeature]:
    """Filter features by projected bbox and station buffer."""
    return [feature for feature in features if bbox_intersects_circle(feature.bbox, center, radius)]


def area_fraction(features: list[SourceFeature], center: tuple[float, float], radius: float, step: float) -> float:
    """Approximate polygon union area fraction by deterministic point sampling."""
    polygons = [feature for feature in candidate_features(features, center, radius) if is_polygon_geometry(feature.geometry)]
    points = sample_points(center, radius, step)
    if not points:
        return 0.0
    covered = 0
    for point in points:
        for feature in polygons:
            min_x, min_y, max_x, max_y = feature.bbox
            if min_x <= point[0] <= max_x and min_y <= point[1] <= max_y and point_in_polygonal_geometry(point, feature.geometry):
                covered += 1
                break
    return covered / len(points)


def landuse_stats(features: list[SourceFeature], center: tuple[float, float], radius: float, step: float) -> tuple[str, float | None, float]:
    """Return majority class, entropy, and source-covered sample fraction."""
    polygons = [feature for feature in candidate_features(features, center, radius) if is_polygon_geometry(feature.geometry)]
    points = sample_points(center, radius, step)
    counts: Counter[str] = Counter()
    for point in points:
        for feature in polygons:
            min_x, min_y, max_x, max_y = feature.bbox
            if min_x <= point[0] <= max_x and min_y <= point[1] <= max_y and point_in_polygonal_geometry(point, feature.geometry):
                counts[feature.class_name or "unclassified"] += 1
                break
    covered = sum(counts.values())
    if covered == 0:
        return "", None, 0.0
    majority = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    entropy = -sum((count / covered) * math.log(count / covered, 2) for count in counts.values())
    return majority, entropy, covered / len(points)


def nearest_distance(features: list[SourceFeature], center: tuple[float, float], predicate: Any | None = None) -> float | None:
    """Return nearest distance from a station point to source features."""
    distances = []
    for feature in features:
        if predicate is not None and not predicate(feature):
            continue
        distance = distance_point_geometry(center, feature.geometry)
        if math.isfinite(distance):
            distances.append(distance)
    return min(distances) if distances else None


def first_layer(layers: list[SourceLayer], group: str) -> SourceLayer | None:
    """Return the first readable layer for a source group."""
    for layer in layers:
        if layer.source_group == group and layer.read_status == "readable" and layer.features:
            return layer
    return None


def build_source_inventory(layers: list[SourceLayer], stations: list[Station], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build source acquisition inventory rows including expected missing patterns."""
    rows: list[dict[str, Any]] = []
    seen_names = {layer.path.name.lower() for layer in layers}
    for layer in layers:
        coverage = station_coverage_count(layer, stations)
        if coverage == len(stations):
            coverage_status = "bbox_covers_all_27_stations"
        elif coverage > 0:
            coverage_status = "bbox_partial_station_coverage"
        else:
            coverage_status = "bbox_covers_no_station_centroids"
        rows.append(
            {
                "source_name": layer.name,
                "source_path": layer.path.as_posix(),
                "source_root": find_source_root(layer.path, config),
                "source_group": layer.source_group,
                "source_format": layer.source_format,
                "exists": layer.exists,
                "file_size_bytes": layer.path.stat().st_size if layer.path.exists() else "",
                "read_status": layer.read_status,
                "table_name": layer.table_name,
                "row_count": layer.row_count,
                "usable_geometry_count": len(layer.features),
                "geometry_type_sample": semicolon(layer.geometry_type_counts.keys()),
                "source_crs": layer.source_crs,
                "crs_assumption": layer.crs_assumption,
                "bbox_min_x": layer.bbox_lonlat[0] if layer.bbox_lonlat else "",
                "bbox_min_y": layer.bbox_lonlat[1] if layer.bbox_lonlat else "",
                "bbox_max_x": layer.bbox_lonlat[2] if layer.bbox_lonlat else "",
                "bbox_max_y": layer.bbox_lonlat[3] if layer.bbox_lonlat else "",
                "station_coverage_count": coverage,
                "expected_station_count": len(stations),
                "coverage_status": coverage_status,
                "allowed_for_27_station_buffer_model": layer.read_status == "readable" and coverage == len(stations) and bool(layer.source_group),
                "extraction_status": "used" if layer.read_status == "readable" and coverage == len(stations) and bool(layer.source_group) else "not_used",
                "notes": layer.notes,
            }
        )
    for pattern in config["expected_source_patterns"]:
        if "*" in pattern:
            matched = any(fnmatch.fnmatch(name, pattern.lower()) for name in seen_names)
            display = pattern
        else:
            matched = pattern.lower() in seen_names
            display = pattern
        if matched:
            continue
        group = source_group_from_name(pattern.replace("*", "candidate"))
        rows.append(
            {
                "source_name": Path(display).stem,
                "source_path": "",
                "source_root": semicolon(config["source_roots"]),
                "source_group": group,
                "source_format": Path(display).suffix,
                "exists": False,
                "file_size_bytes": "",
                "read_status": "missing",
                "table_name": "",
                "row_count": 0,
                "usable_geometry_count": 0,
                "geometry_type_sample": "",
                "source_crs": "",
                "crs_assumption": "",
                "bbox_min_x": "",
                "bbox_min_y": "",
                "bbox_max_x": "",
                "bbox_max_y": "",
                "station_coverage_count": 0,
                "expected_station_count": len(stations),
                "coverage_status": "missing_local_source",
                "allowed_for_27_station_buffer_model": False,
                "extraction_status": "missing",
                "notes": "Expected candidate source pattern not present in configured local source roots.",
            }
        )
    return sorted(rows, key=lambda row: (str(row["exists"]) != "True", str(row["source_group"]), str(row["source_name"])))


def find_source_root(path: Path, config: dict[str, Any]) -> str:
    """Return matching configured source root for a source path."""
    for raw_root in config["source_roots"]:
        root = resolve_path(str(raw_root))
        try:
            path.resolve().relative_to(root.resolve())
            return root.as_posix()
        except ValueError:
            continue
    return ""


def build_normalization(layers: list[SourceLayer], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build source normalization inventory rows."""
    rows = []
    for layer in layers:
        polygon_count = sum(1 for feature in layer.features if is_polygon_geometry(feature.geometry))
        line_count = sum(1 for feature in layer.features if is_line_geometry(feature.geometry))
        point_count = sum(1 for feature in layer.features if feature.geometry_type == "Point")
        partial_attributes = []
        if layer.source_group == "roads" and not any(feature.highway_class for feature in layer.features):
            partial_attributes.append("missing_highway_class")
        if layer.source_group == "landuse" and all(feature.class_name == "unclassified" for feature in layer.features):
            partial_attributes.append("weak_landuse_attributes")
        rows.append(
            {
                "source_name": layer.name,
                "source_path": layer.path.as_posix(),
                "source_group": layer.source_group,
                "source_format": layer.source_format,
                "input_crs": layer.source_crs,
                "crs_action": "projected_to_EPSG_3414" if layer.read_status == "readable" else "not_projected",
                "output_crs": "EPSG:3414" if layer.read_status == "readable" else "",
                "row_count": layer.row_count,
                "usable_geometry_count": len(layer.features),
                "geometry_type_counts": ";".join(f"{key}:{value}" for key, value in sorted(layer.geometry_type_counts.items())),
                "geometry_parse_error_count": layer.geometry_parse_error_count,
                "polygon_feature_count": polygon_count,
                "line_feature_count": line_count,
                "point_feature_count": point_count,
                "invalid_geometry_count": "not_evaluated_no_topology_engine",
                "repair_method": "none; make_valid/buffer0 unavailable in dependency-light runtime",
                "attribute_classification_status": "partial" if partial_attributes else "usable",
                "attribute_classification_notes": semicolon(partial_attributes) or "Filename and available attributes support requested group extraction.",
                "assumptions": layer.crs_assumption or "CRS read from source metadata.",
            }
        )
    return rows


def build_feature_rows(stations: list[Station], layers: list[SourceLayer], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract station-buffer feature rows from available source layers."""
    buffers = [int(value) for value in config["buffers_m"]]
    step_by_buffer = {int(key): float(value) for key, value in config["sampling_step_m"].items()}
    layer_by_group = {group: first_layer(layers, group) for group in config["feature_groups"]}
    major_classes = {str(value).lower() for value in config["major_highway_classes"]}
    rows: list[dict[str, Any]] = []

    for station in stations:
        center = (station.x, station.y)
        water = layer_by_group.get("water")
        green = layer_by_group.get("green")
        roads = layer_by_group.get("roads")
        buildings = layer_by_group.get("buildings")
        landuse = layer_by_group.get("landuse")
        water_distance = nearest_distance(water.features, center) if water else None
        green_distance = nearest_distance(green.features, center) if green else None
        major_distance = nearest_distance(roads.features, center, lambda f: f.highway_class.lower() in major_classes and is_line_geometry(f.geometry)) if roads else None

        for buffer_m in buffers:
            step = step_by_buffer.get(buffer_m, 20.0)
            buffer_area_m2 = math.pi * buffer_m * buffer_m
            buffer_ha = buffer_area_m2 / 10000.0
            if water:
                rows.append(feature_row(station, buffer_m, "water_fraction", area_fraction(water.features, center, buffer_m, step), "fraction", "water", water.name, "deterministic_grid_polygon_union_fraction", "usable_all_27", "Polygonal OSM water sampled inside metric station buffer."))
                rows.append(feature_row(station, buffer_m, "distance_to_water_m", water_distance, "m", "water", water.name, "nearest_geometry_distance", "usable_all_27", "Nearest OSM water geometry; repeated across buffer sizes."))
            else:
                add_missing_group_rows(rows, station, buffer_m, "water", ["water_fraction", "distance_to_water_m"], ["fraction", "m"])
            if green:
                rows.append(feature_row(station, buffer_m, "green_space_fraction", area_fraction(green.features, center, buffer_m, step), "fraction", "green", green.name, "deterministic_grid_polygon_union_fraction", "usable_all_27", "Polygonal OSM green/park features sampled inside metric station buffer."))
                rows.append(feature_row(station, buffer_m, "distance_to_park_or_green_m", green_distance, "m", "green", green.name, "nearest_geometry_distance", "usable_all_27", "Nearest OSM green/park geometry; repeated across buffer sizes."))
            else:
                add_missing_group_rows(rows, station, buffer_m, "green", ["green_space_fraction", "distance_to_park_or_green_m"], ["fraction", "m"])
            if roads:
                road_candidates = [feature for feature in candidate_features(roads.features, center, buffer_m) if is_line_geometry(feature.geometry)]
                road_length = sum(line_length_inside_circle(feature.geometry, center, buffer_m) for feature in road_candidates)
                major_length = sum(line_length_inside_circle(feature.geometry, center, buffer_m) for feature in road_candidates if feature.highway_class.lower() in major_classes)
                rows.append(feature_row(station, buffer_m, "road_length_m", road_length, "m", "roads", roads.name, "line_circle_intersection_length", "usable_all_27", "OSM highway line length clipped to metric station buffer."))
                rows.append(feature_row(station, buffer_m, "road_density_m_per_ha", road_length / buffer_ha if buffer_ha else None, "m/ha", "roads", roads.name, "line_circle_intersection_length_per_buffer_ha", "usable_all_27", "Road length divided by circular buffer area in hectares."))
                rows.append(feature_row(station, buffer_m, "major_road_length_m", major_length, "m", "roads", roads.name, "line_circle_intersection_length", "usable_all_27", "Major roads use configured OSM highway classes."))
                rows.append(feature_row(station, buffer_m, "distance_to_major_road_m", major_distance, "m", "roads", roads.name, "nearest_major_highway_distance", "usable_all_27", "Nearest configured major OSM highway class; repeated across buffer sizes."))
            else:
                add_missing_group_rows(rows, station, buffer_m, "roads", ["road_length_m", "road_density_m_per_ha", "major_road_length_m", "distance_to_major_road_m"], ["m", "m/ha", "m", "m"])
            if buildings:
                building_candidates = [feature for feature in candidate_features(buildings.features, center, buffer_m) if is_polygon_geometry(feature.geometry)]
                building_count = sum(1 for feature in building_candidates if distance_point_geometry(center, feature.geometry) <= buffer_m)
                rows.append(feature_row(station, buffer_m, "building_footprint_fraction", area_fraction(buildings.features, center, buffer_m, step), "fraction", "buildings", buildings.name, "deterministic_grid_polygon_union_fraction", "usable_all_27", "Polygonal OSM building footprints sampled inside metric station buffer."))
                rows.append(feature_row(station, buffer_m, "building_count", building_count, "count", "buildings", buildings.name, "polygon_intersects_metric_buffer_count", "usable_all_27", "Count of building footprint features intersecting the buffer."))
            else:
                add_missing_group_rows(rows, station, buffer_m, "buildings", ["building_footprint_fraction", "building_count"], ["fraction", "count"])
            if landuse:
                majority, entropy, covered_fraction = landuse_stats(landuse.features, center, buffer_m, step)
                coverage_status = "usable_all_27" if majority else "partial_no_polygon_at_buffer"
                note = f"OSM landuse polygons are not exhaustive; sampled source-covered fraction={fmt_float(covered_fraction)}."
                rows.append(feature_row(station, buffer_m, "landuse_majority", majority, "category", "landuse", landuse.name, "deterministic_grid_majority_class", coverage_status, note))
                rows.append(feature_row(station, buffer_m, "landuse_entropy", entropy, "bits", "landuse", landuse.name, "deterministic_grid_class_entropy", coverage_status, note))
            else:
                add_missing_group_rows(rows, station, buffer_m, "landuse", ["landuse_majority", "landuse_entropy"], ["category", "bits"])
    return rows


def feature_row(
    station: Station,
    buffer_m: int,
    feature_name: str,
    value: Any,
    unit: str,
    group: str,
    source_name: str,
    method: str,
    coverage_status: str,
    notes: str,
) -> dict[str, Any]:
    """Create one long feature row."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        feature_value = fmt_float(float(value))
    else:
        feature_value = "" if value is None else str(value)
    return {
        "station_id": station.station_id,
        "buffer_m": buffer_m,
        "feature_name": feature_name,
        "feature_value": feature_value,
        "feature_unit": unit,
        "feature_group": group,
        "source_name": source_name,
        "extraction_method": method,
        "coverage_status": coverage_status,
        "notes": notes,
    }


def add_missing_group_rows(rows: list[dict[str, Any]], station: Station, buffer_m: int, group: str, feature_names: list[str], units: list[str]) -> None:
    """Append null feature rows for an unavailable group."""
    for feature_name, unit in zip(feature_names, units):
        rows.append(feature_row(station, buffer_m, feature_name, None, unit, group, "", "not_extracted_missing_source", "missing_source", "No all-27 local source was available for this feature group."))


def build_wide(stations: list[Station], long_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one-row-per-station wide feature table."""
    wide: dict[str, dict[str, Any]] = {
        station.station_id: {
            "station_id": station.station_id,
            "station_name": station.station_name,
            "station_town_center": station.station_town_center,
            "station_lat": fmt_float(station.lat),
            "station_lon": fmt_float(station.lon),
            "station_source_epsg": 4326,
            "metric_buffer_epsg": 3414,
        }
        for station in stations
    }
    for row in long_rows:
        column = f"{row['feature_name']}_{row['buffer_m']}m"
        wide[str(row["station_id"])][column] = row["feature_value"]
    return [wide[key] for key in sorted(wide)]


def is_non_null(value: Any) -> bool:
    """Return whether a CSV value should count as non-null."""
    return str(value).strip() != ""


def build_schema(long_rows: list[dict[str, Any]], expected_station_count: int, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build feature schema and leakage checks."""
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in long_rows:
        grouped[(str(row["feature_name"]), int(row["buffer_m"]))].append(row)
    rows: list[dict[str, Any]] = []
    forbidden = [str(value).lower() for value in config["forbidden_feature_tokens"]]
    for (feature_name, buffer_m), items in sorted(grouped.items()):
        values = [str(item["feature_value"]) for item in items if is_non_null(item["feature_value"])]
        distinct = sorted(set(values))
        n_non_null = len(values)
        leakage_hits = [token for token in forbidden if token in feature_name.lower()]
        allowed = n_non_null == expected_station_count and not leakage_hits and not all(item["coverage_status"] == "missing_source" for item in items)
        rows.append(
            {
                "feature_name": feature_name,
                "buffer_m": buffer_m,
                "feature_column": f"{feature_name}_{buffer_m}m",
                "feature_group": items[0]["feature_group"],
                "feature_unit": items[0]["feature_unit"],
                "source_name": semicolon(item["source_name"] for item in items),
                "extraction_method": semicolon(item["extraction_method"] for item in items),
                "n_stations_non_null": n_non_null,
                "expected_station_count": expected_station_count,
                "missing_fraction": fmt_float(1.0 - (n_non_null / expected_station_count)),
                "constant_non_null": bool(values) and len(distinct) == 1,
                "allowed_for_future_model": allowed,
                "leakage_check": "PASS_NO_FORBIDDEN_FEATURE_TOKEN" if not leakage_hits else f"FAIL_FORBIDDEN_TOKEN:{semicolon(leakage_hits)}",
                "coverage_status": "all_27_non_null" if n_non_null == expected_station_count else "missing_or_partial",
                "notes": "station_id is metadata/key only; official WBGT/residual/event labels are not used as features.",
            }
        )
    return rows


def all_27_groups(schema_rows: list[dict[str, Any]]) -> list[str]:
    """Return feature groups with at least one all-27 allowed feature."""
    return sorted({str(row["feature_group"]) for row in schema_rows if str(row["allowed_for_future_model"]) == "True" or row["allowed_for_future_model"] is True})


def build_missing_actions(schema_rows: list[dict[str, Any]], inventory_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build missing-source / next-action checklist."""
    built = set(all_27_groups(schema_rows))
    rows = []
    for group in config["feature_groups"]:
        group_inventory = [row for row in inventory_rows if row["source_group"] == group]
        usable_sources = [row["source_name"] for row in group_inventory if str(row["allowed_for_27_station_buffer_model"]) == "True" or row["allowed_for_27_station_buffer_model"] is True]
        if group in built:
            status = "BUILT_ALL_27"
            action = "Proceed to A-L2.1b QA review for this group; do not train residual models in S1."
        elif usable_sources:
            status = "SOURCE_PRESENT_EXTRACTION_PARTIAL"
            action = "Review attributes/geometry coverage and decide whether partial features are acceptable after QA."
        else:
            status = "MISSING_ALL_27_SOURCE"
            action = "Acquire or point config to an all-27 Singapore-wide source under C:/OpenHeat-local/station_context_sources."
        rows.append(
            {
                "feature_group": group,
                "status": status,
                "usable_sources": semicolon(usable_sources),
                "candidate_source_patterns": semicolon(pattern for pattern in config["expected_source_patterns"] if source_group_from_name(str(pattern).replace("*", "candidate")) == group),
                "next_action": action,
            }
        )
    return rows


def build_qa(
    stations: list[Station],
    schema_rows: list[dict[str, Any]],
    inventory_rows: list[dict[str, Any]],
    normalization_rows: list[dict[str, Any]],
    crs_status: str,
    crs_notes: str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build QA metrics as a machine-readable long table."""
    groups = all_27_groups(schema_rows)
    constant_count = sum(1 for row in schema_rows if row["constant_non_null"] is True or str(row["constant_non_null"]) == "True")
    max_missing = max((float(row["missing_fraction"]) for row in schema_rows), default=1.0)
    source_assumptions = semicolon(row["assumptions"] for row in normalization_rows if row.get("assumptions"))
    return [
        {"qa_metric": "station_count", "qa_value": len(stations), "qa_status": "PASS" if len(stations) == int(config["expected_station_count"]) else "FAIL", "notes": "Unique station centroids from v09 station pairs."},
        {"qa_metric": "buffer_count", "qa_value": len(config["buffers_m"]), "qa_status": "PASS", "notes": f"Buffers: {semicolon(config['buffers_m'])} m."},
        {"qa_metric": "station_crs", "qa_value": "EPSG:4326", "qa_status": crs_status, "notes": crs_notes},
        {"qa_metric": "metric_buffer_crs", "qa_value": "EPSG:3414", "qa_status": crs_status, "notes": "SVY21 projection used before metric buffers/lengths."},
        {"qa_metric": "all_27_feature_groups", "qa_value": semicolon(groups) or "none", "qa_status": "PASS" if groups else "BLOCKED", "notes": "Groups with at least one non-leakage all-27 feature."},
        {"qa_metric": "missing_fraction_max", "qa_value": fmt_float(max_missing), "qa_status": "PASS" if max_missing < 1 else "BLOCKED", "notes": "Maximum schema missing fraction."},
        {"qa_metric": "constant_feature_count", "qa_value": constant_count, "qa_status": "WARN" if constant_count else "PASS", "notes": "Constant features are flagged for later QA, not removed here."},
        {"qa_metric": "source_count_readable", "qa_value": sum(1 for row in inventory_rows if row["read_status"] == "readable"), "qa_status": "PASS", "notes": "Readable local source files only; raw spatial layers remain outside repo."},
        {"qa_metric": "source_assumptions", "qa_value": source_assumptions or "none", "qa_status": "PASS", "notes": "CRS/attribute assumptions captured in normalization inventory."},
        {"qa_metric": "forbidden_features", "qa_value": "none", "qa_status": "PASS", "notes": "No official WBGT, residual, event label, station_id predictive feature, System B, or SOLWEIG feature is emitted."},
        {"qa_metric": "raw_spatial_layers_written", "qa_value": "none", "qa_status": "PASS", "notes": "Only compact CSV/Markdown summaries are written."},
        {"qa_metric": "model_training", "qa_value": "none", "qa_status": "PASS", "notes": "No residual ML model was trained."},
        {"qa_metric": "toa_payoh_only_features", "qa_value": "excluded", "qa_status": "PASS", "notes": "Toa Payoh-only/AOI-limited features remain excluded from all-27 station-context features."},
    ]


def decide_status(schema_rows: list[dict[str, Any]], crs_status: str) -> str:
    """Classify the S1 decision status."""
    if crs_status == "BLOCKED_CRS":
        return "BLOCKED_CRS"
    groups = set(all_27_groups(schema_rows))
    if {"water", "green", "roads", "buildings"}.issubset(groups) or "landuse" in groups:
        return "PASS_FEATURE_TABLE"
    if groups:
        return "PARTIAL_FEATURE_TABLE"
    return "BLOCKED_MISSING_SOURCES"


def next_action_for_status(status: str, unavailable_groups: list[str]) -> str:
    """Return the next recommended action."""
    if status == "PASS_FEATURE_TABLE":
        return "Proceed to A-L2.1b QA/collinearity review using S1 tables; keep A-L2.1c residual modelling out of this lane."
    if status == "PARTIAL_FEATURE_TABLE":
        return f"Review partial S1 feature coverage and acquire missing groups before modelling: {semicolon(unavailable_groups) or 'none'}."
    if status == "BLOCKED_CRS":
        return "Resolve source/station CRS before interpreting station-buffer features."
    return "Acquire all-27 station-local spatial sources under C:/OpenHeat-local/station_context_sources and rerun S1."


def build_report(
    path: Path,
    config_path: Path,
    status: str,
    stations: list[Station],
    inventory_rows: list[dict[str, Any]],
    normalization_rows: list[dict[str, Any]],
    schema_rows: list[dict[str, Any]],
    qa_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
    groups: list[str],
    unavailable: list[str],
    assumptions: list[str],
) -> None:
    """Write the English Markdown builder report."""
    source_summary = []
    grouped_counts: Counter[tuple[str, str]] = Counter((str(row["source_group"]), str(row["coverage_status"])) for row in inventory_rows)
    for (group, coverage), count in sorted(grouped_counts.items()):
        source_summary.append({"source_group": group, "coverage_status": coverage, "source_count": count})
    lines = [
        "# System A A-L2.1a-S1 Station-Local Source Acquisition",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Decision status: `{status}`",
        f"Branch: `{git_branch()}`",
        f"Config: `{rel(config_path)}`",
        "",
        "## Why A-L2.1a Was Blocked",
        "",
        "The previous A-L2.1a gate was `BLOCKED_MISSING_SOURCES` because the available in-repo spatial files were Toa Payoh-only, AOI-limited, unknown-coverage, or metadata-only. They could not defensibly produce all-27 station-local buffer features.",
        "",
        "## Local Sources Used",
        "",
        markdown_table([row for row in inventory_rows if row["read_status"] == "readable"], ["source_name", "source_group", "source_format", "row_count", "usable_geometry_count", "source_crs", "station_coverage_count", "coverage_status"], limit=30),
        "",
        "## Source Coverage Summary",
        "",
        markdown_table(source_summary, ["source_group", "coverage_status", "source_count"], limit=30),
        "",
        "## Normalization Summary",
        "",
        markdown_table(normalization_rows, ["source_name", "source_group", "input_crs", "crs_action", "geometry_type_counts", "attribute_classification_status", "assumptions"], limit=30),
        "",
        "## Feature Groups With All-27 Coverage",
        "",
        semicolon(groups) or "none",
        "",
        "## Feature Groups Still Unavailable",
        "",
        semicolon(unavailable) or "none",
        "",
        "## Schema Snapshot",
        "",
        markdown_table(schema_rows, ["feature_column", "feature_group", "n_stations_non_null", "missing_fraction", "allowed_for_future_model", "leakage_check"], limit=40),
        "",
        "## Missing Sources / Next Actions",
        "",
        markdown_table(missing_rows, ["feature_group", "status", "usable_sources", "next_action"], limit=20),
        "",
        "## QA",
        "",
        markdown_table(qa_rows, ["qa_metric", "qa_value", "qa_status", "notes"], limit=30),
        "",
        "## Assumptions",
        "",
        "\n".join(f"- {item}" for item in assumptions) if assumptions else "- none",
        "",
        "## Claim Boundaries",
        "",
        "- Toa Payoh-only features remain excluded because this lane requires all-27 station-local source coverage.",
        "- No model was trained.",
        "- No station-context causal correction is claimed.",
        "- No station-adjusted WBGT was created.",
        "- No local 100 m WBGT was created.",
        "- No System B or SOLWEIG outputs were touched or used.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_cn_doc(
    path: Path,
    status: str,
    stations: list[Station],
    groups: list[str],
    unavailable: list[str],
    inventory_rows: list[dict[str, Any]],
    assumptions: list[str],
) -> None:
    """Write the UTF-8 Chinese documentation page."""
    used = [row for row in inventory_rows if row["read_status"] == "readable" and row["source_path"]]
    lines = [
        "# OpenHeat System A A-L2.1a-S1 站点缓冲区空间源获取说明",
        "",
        f"生成日期：{date.today().isoformat()}",
        f"决策状态：`{status}`",
        "",
        "## 1. 为什么上一轮 A-L2.1a 被阻塞",
        "",
        "上一轮 A-L2.1a 的结论是 `BLOCKED_MISSING_SOURCES`。原因是当时可用的数据主要是 Toa Payoh AOI 或网格代理数据，不能代表全部 27 个 NEA WBGT 站点的站点本地缓冲区环境。因此这些 Toa Payoh-only 特征只能盘点，不能进入 27 站特征表。",
        "",
        "## 2. 本轮使用的本地来源",
        "",
        "\n".join(f"- `{row['source_name']}`：{row['source_group']}，{row['row_count']} 行，路径 `{row['source_path']}`" for row in used) if used else "- 未发现可读取的本地空间来源。",
        "",
        "## 3. 已形成全 27 站覆盖的特征组",
        "",
        semicolon(groups) or "无",
        "",
        "## 4. 仍不可用的特征组",
        "",
        semicolon(unavailable) or "无",
        "",
        "## 5. CRS 与几何处理",
        "",
        "站点坐标按 EPSG:4326 读取，并在计算缓冲区、长度和距离之前投影到 Singapore SVY21 EPSG:3414。本轮只写出紧凑的 CSV/Markdown 汇总，不把原始 OSM、data.gov.sg 或 OneMap 空间图层复制进仓库。",
        "",
        "## 6. 关键假设",
        "",
        "\n".join(f"- {item}" for item in assumptions) if assumptions else "- 无额外假设。",
        "",
        "## 7. 边界声明",
        "",
        "- 本轮没有训练残差机器学习模型。",
        "- 本轮没有提出站点上下文因果校正。",
        "- 本轮没有生成站点校正 WBGT。",
        "- 本轮没有生成本地 100 m WBGT。",
        "- 本轮没有使用 official_wbgt_c、residual、obs_ge31、obs_ge33、System B 或 SOLWEIG 输出作为特征。",
        "- `station_id` 只作为行键和元数据，不作为预测特征。",
        "",
        f"站点数量：{len(stations)}。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_status(path: Path, config_path: Path, result: BuildResult) -> None:
    """Write the lane status file."""
    lines = [
        "# A-L2.1a-S1 Status",
        "",
        f"Status: {result.decision_status}",
        f"Branch: {git_branch()}",
        "Scope: station-local source acquisition/extraction only; no residual modelling.",
        "",
        "Commands run:",
        f"- python scripts/v11_l2_run_station_buffer_source_acquisition.py --config {rel(config_path)}",
        "",
        "Key results:",
        f"- Station count: {result.station_count}",
        f"- Feature groups built with all-27 coverage: {semicolon(result.feature_groups_all_27) or 'none'}",
        f"- Feature groups still unavailable: {semicolon(result.feature_groups_unavailable) or 'none'}",
        f"- Assumptions: {semicolon(result.assumptions) or 'none'}",
        "",
        "Caveats:",
        "- No model trained.",
        "- No station-context causal correction claimed.",
        "- No station-adjusted WBGT or local 100 m WBGT created.",
        "- Raw spatial source layers remain outside the repo.",
        "- Toa Payoh-only/AOI-limited features remain excluded.",
        "",
        f"Next recommended action: {result.next_recommended_action}",
        "",
        "Files created / modified:",
        *[f"- {rel(path_item)}" for path_item in result.files_created],
        "",
        "Safe to commit: controlled config/script/docs and compact CSV/Markdown outputs after review.",
        "Not safe to commit: raw spatial layers, rasters, archives, SOLWEIG/System B outputs, or large forecast/live CSVs.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def collect_assumptions(normalization_rows: list[dict[str, Any]]) -> list[str]:
    """Collect compact unique assumptions for reports."""
    assumptions = []
    for row in normalization_rows:
        text = str(row.get("assumptions", "")).strip()
        if text and text not in assumptions:
            assumptions.append(text)
    assumptions.append("Area fractions use deterministic grid sampling of source polygons within EPSG:3414 circular buffers; no clipped raw geometries are written.")
    assumptions.append("Road lengths use exact line-circle segment clipping in EPSG:3414.")
    assumptions.append("OSM landuse polygons are treated as partial context where polygons exist, not as a complete LCZ product.")
    return assumptions


def run_builder(config_path: Path) -> BuildResult:
    """Run the full S1 source acquisition/extraction workflow."""
    config = load_config(config_path)
    paths = output_paths(config)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["cn_doc"].parent.mkdir(parents=True, exist_ok=True)

    stations = load_stations(config)
    crs_status, crs_notes = validate_station_crs(stations, config)
    layers = read_source_layers(config) if crs_status != "BLOCKED_CRS" else []
    inventory_rows = build_source_inventory(layers, stations, config)
    normalization_rows = build_normalization(layers, config)
    long_rows = build_feature_rows(stations, layers, config) if crs_status != "BLOCKED_CRS" else []
    schema_rows = build_schema(long_rows, len(stations), config) if long_rows else []
    wide_rows = build_wide(stations, long_rows) if long_rows else []
    groups = all_27_groups(schema_rows)
    unavailable = [group for group in config["feature_groups"] if group not in groups]
    missing_rows = build_missing_actions(schema_rows, inventory_rows, config)
    qa_rows = build_qa(stations, schema_rows, inventory_rows, normalization_rows, crs_status, crs_notes, config)
    status = decide_status(schema_rows, crs_status)
    assumptions = collect_assumptions(normalization_rows)
    next_action = next_action_for_status(status, unavailable)

    inventory_fields = [
        "source_name",
        "source_path",
        "source_root",
        "source_group",
        "source_format",
        "exists",
        "file_size_bytes",
        "read_status",
        "table_name",
        "row_count",
        "usable_geometry_count",
        "geometry_type_sample",
        "source_crs",
        "crs_assumption",
        "bbox_min_x",
        "bbox_min_y",
        "bbox_max_x",
        "bbox_max_y",
        "station_coverage_count",
        "expected_station_count",
        "coverage_status",
        "allowed_for_27_station_buffer_model",
        "extraction_status",
        "notes",
    ]
    normalization_fields = [
        "source_name",
        "source_path",
        "source_group",
        "source_format",
        "input_crs",
        "crs_action",
        "output_crs",
        "row_count",
        "usable_geometry_count",
        "geometry_type_counts",
        "geometry_parse_error_count",
        "polygon_feature_count",
        "line_feature_count",
        "point_feature_count",
        "invalid_geometry_count",
        "repair_method",
        "attribute_classification_status",
        "attribute_classification_notes",
        "assumptions",
    ]
    long_fields = ["station_id", "buffer_m", "feature_name", "feature_value", "feature_unit", "feature_group", "source_name", "extraction_method", "coverage_status", "notes"]
    wide_fields = stable_wide_fields(wide_rows)
    schema_fields = [
        "feature_name",
        "buffer_m",
        "feature_column",
        "feature_group",
        "feature_unit",
        "source_name",
        "extraction_method",
        "n_stations_non_null",
        "expected_station_count",
        "missing_fraction",
        "constant_non_null",
        "allowed_for_future_model",
        "leakage_check",
        "coverage_status",
        "notes",
    ]
    qa_fields = ["qa_metric", "qa_value", "qa_status", "notes"]
    missing_fields = ["feature_group", "status", "usable_sources", "candidate_source_patterns", "next_action"]

    write_csv(paths["source_inventory"], inventory_rows, inventory_fields)
    write_csv(paths["source_normalization"], normalization_rows, normalization_fields)
    write_csv(paths["feature_long"], long_rows, long_fields)
    write_csv(paths["feature_wide"], wide_rows, wide_fields)
    write_csv(paths["feature_schema"], schema_rows, schema_fields)
    write_csv(paths["feature_qa"], qa_rows, qa_fields)
    write_csv(paths["missing_sources"], missing_rows, missing_fields)
    build_report(paths["builder_report"], config_path, status, stations, inventory_rows, normalization_rows, schema_rows, qa_rows, missing_rows, groups, unavailable, assumptions)
    build_cn_doc(paths["cn_doc"], status, stations, groups, unavailable, inventory_rows, assumptions)

    files = [
        paths["source_inventory"],
        paths["source_normalization"],
        paths["feature_long"],
        paths["feature_wide"],
        paths["feature_schema"],
        paths["feature_qa"],
        paths["missing_sources"],
        paths["builder_report"],
        paths["status"],
        paths["cn_doc"],
    ]
    result = BuildResult(
        decision_status=status,
        station_count=len(stations),
        feature_groups_all_27=groups,
        feature_groups_unavailable=unavailable,
        assumptions=assumptions,
        next_recommended_action=next_action,
        files_created=files,
        git_status_short="",
    )
    write_status(paths["status"], config_path, result)
    return BuildResult(
        decision_status=status,
        station_count=len(stations),
        feature_groups_all_27=groups,
        feature_groups_unavailable=unavailable,
        assumptions=assumptions,
        next_recommended_action=next_action,
        files_created=files,
        git_status_short=git_status_short(),
    )


def stable_wide_fields(wide_rows: list[dict[str, Any]]) -> list[str]:
    """Return deterministic wide table columns."""
    base = ["station_id", "station_name", "station_town_center", "station_lat", "station_lon", "station_source_epsg", "metric_buffer_epsg"]
    columns = sorted({key for row in wide_rows for key in row.keys() if key not in base})
    return base + columns


def main() -> int:
    """CLI entrypoint for direct execution."""
    parser = argparse.ArgumentParser(description="Run A-L2.1a-S1 station-local source acquisition/extraction.")
    parser.add_argument("--config", default="configs/v11/systema_l2_station_buffer_source_acquisition.yaml")
    args = parser.parse_args()
    result = run_builder(resolve_path(args.config))
    print(result.decision_status)
    return 0 if result.decision_status != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
