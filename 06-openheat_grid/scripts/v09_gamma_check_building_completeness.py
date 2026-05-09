"""
OpenHeat v0.9-gamma QA: quantify building DSM completeness against
OpenStreetMap building footprints.

For each of the 6 SOLWEIG tile buffers, compares:
- the building footprint area implied by the HDB3D+URA-derived building
  DSM (pixels with DSM > 0.5 m)
- the OSM building footprint area (way[building=*] polygons)

Outputs per-tile completeness ratio + missing area estimate.

Usage:
    python scripts/v09_gamma_check_building_completeness.py
"""
from __future__ import annotations

import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.features import shapes
from shapely.geometry import shape, Polygon, MultiPolygon

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
]

REQUEST_HEADERS = {
    "User-Agent": "OpenHeat-ToaPayoh-research/0.9 (Singapore urban heat-stress study)",
    "Accept": "application/json",
}

OVERPASS_QUERY = """
[out:json][timeout:120];
(
  way["building"]({bbox});
  relation["building"]({bbox});
);
out geom;
"""

TILE_ROOT = Path("data/solweig/v09_tiles_overhead_aware")
TILES_BUFFERED = TILE_ROOT / "v09_solweig_tiles_overhead_aware_buffered.geojson"
OUT_DIR = Path("outputs/v09_gamma_qa")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BUILDING_DSM_THRESHOLD_M = 0.5  # pixels above this height counted as building


def fetch_osm_buildings(bbox_4326: tuple) -> gpd.GeoDataFrame:
    south, west, north, east = bbox_4326
    bbox_str = f"{south},{west},{north},{east}"
    query = OVERPASS_QUERY.format(bbox=bbox_str)
    print(f"[INFO] Overpass bbox: {bbox_str}")

    last_err = None
    for url in OVERPASS_ENDPOINTS:
        try:
            print(f"[INFO] trying {url}")
            t0 = time.time()
            r = requests.post(url, data={"data": query}, headers=REQUEST_HEADERS, timeout=180)
            elapsed = time.time() - t0
            print(f"[INFO]   {elapsed:.1f}s, status={r.status_code}")
            if r.status_code == 200:
                payload = r.json()
                rows = []
                for el in payload.get("elements", []):
                    if el.get("type") == "way" and el.get("geometry"):
                        coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
                        if len(coords) < 3:
                            continue
                        if coords[0] != coords[-1]:
                            coords.append(coords[0])
                        try:
                            poly = Polygon(coords)
                            if not poly.is_valid:
                                poly = poly.buffer(0)
                            if poly.is_empty or poly.area == 0:
                                continue
                            rows.append({
                                "osm_id": el["id"],
                                "osm_type": "way",
                                "name": el.get("tags", {}).get("name"),
                                "building_type": el.get("tags", {}).get("building"),
                                "geometry": poly,
                            })
                        except Exception:
                            continue
                if not rows:
                    return gpd.GeoDataFrame(
                        columns=["osm_id", "osm_type", "name", "building_type", "geometry"],
                        crs="EPSG:4326"
                    )
                return gpd.GeoDataFrame(rows, crs="EPSG:4326")
            last_err = f"HTTP {r.status_code}"
        except requests.exceptions.RequestException as e:
            last_err = repr(e)
            print(f"[WARN] {url} failed: {e!r}")
            continue
    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_err}")


def building_area_from_dsm(dsm_path: Path, tile_geom_3414, threshold_m: float) -> float:
    """Compute building footprint area (m^2) from DSM where dsm > threshold,
    clipped to tile geometry."""
    if not dsm_path.exists():
        return 0.0
    with rasterio.open(dsm_path) as src:
        # Read whole DSM (tiles are small, ~700m x 700m)
        arr = src.read(1)
        transform = src.transform
        nodata = src.nodata
        valid = np.isfinite(arr)
        if nodata is not None:
            valid &= arr != nodata
        building_mask = valid & (arr > threshold_m)

        # Convert mask to vector polygons
        polygons = []
        for shp, val in shapes(building_mask.astype(np.uint8), mask=building_mask, transform=transform):
            if val == 1:
                polygons.append(shape(shp))

    if not polygons:
        return 0.0

    dsm_buildings = gpd.GeoDataFrame(geometry=polygons, crs=src.crs)
    if dsm_buildings.crs.to_epsg() != 3414:
        dsm_buildings = dsm_buildings.to_crs(3414)

    # Intersect with tile geometry
    tile_gdf = gpd.GeoDataFrame(geometry=[tile_geom_3414], crs="EPSG:3414")
    inter = gpd.overlay(dsm_buildings, tile_gdf, how="intersection")
    return float(inter.area.sum())


def main() -> None:
    if not TILES_BUFFERED.exists():
        raise FileNotFoundError(f"Tiles buffered geojson missing: {TILES_BUFFERED}")

    tiles = gpd.read_file(TILES_BUFFERED)
    print(f"[INFO] {len(tiles)} tiles loaded")

    # Compute combined bbox in WGS84 for OSM query
    tiles_4326 = tiles.to_crs("EPSG:4326")
    minx, miny, maxx, maxy = tiles_4326.total_bounds
    bbox = (miny, minx, maxy, maxx)

    osm_buildings = fetch_osm_buildings(bbox)
    print(f"[INFO] {len(osm_buildings)} OSM buildings in AOI bbox")
    if osm_buildings.empty:
        print("[WARN] No OSM buildings found.")
        return

    osm_buildings_3414 = osm_buildings.to_crs("EPSG:3414")

    # Save OSM features for QGIS visualization
    osm_buildings_3414.to_file(
        OUT_DIR / "v09_osm_buildings.geojson", driver="GeoJSON"
    )
    print(f"[OK] {OUT_DIR / 'v09_osm_buildings.geojson'}")

    rows = []
    for _, t in tiles.iterrows():
        tile_id = t["tile_id"]
        tile_geom = t.geometry  # in EPSG:3414
        tile_area = float(tile_geom.area)

        # OSM building area within tile
        osm_in_tile = osm_buildings_3414[osm_buildings_3414.intersects(tile_geom)]
        if osm_in_tile.empty:
            osm_area = 0.0
        else:
            osm_clip = gpd.overlay(
                osm_in_tile,
                gpd.GeoDataFrame(geometry=[tile_geom], crs="EPSG:3414"),
                how="intersection"
            )
            osm_area = float(osm_clip.area.sum())

        # DSM-implied building area
        dsm_path = TILE_ROOT / tile_id / "dsm_buildings_tile.tif"
        dsm_area = building_area_from_dsm(dsm_path, tile_geom, BUILDING_DSM_THRESHOLD_M)

        # Completeness statistics
        completeness_pct = 100.0 * (dsm_area / osm_area) if osm_area > 0 else float("nan")
        missing_area = max(0.0, osm_area - dsm_area)
        missing_pct_of_tile = 100.0 * missing_area / tile_area

        rows.append({
            "tile_id": tile_id,
            "tile_area_m2": round(tile_area, 0),
            "osm_n_buildings": len(osm_in_tile),
            "osm_building_area_m2": round(osm_area, 0),
            "dsm_building_area_m2": round(dsm_area, 0),
            "dsm_pct_of_osm": round(completeness_pct, 1),
            "missing_area_m2": round(missing_area, 0),
            "missing_pct_of_tile": round(missing_pct_of_tile, 2),
        })

    summary = pd.DataFrame(rows)
    summary_csv = OUT_DIR / "v09_building_completeness_per_tile.csv"
    summary.to_csv(summary_csv, index=False)

    print()
    print("=" * 80)
    print("Building DSM completeness vs OSM (per tile, EPSG:3414)")
    print("=" * 80)
    print(summary.to_string(index=False))
    print()
    print(f"[OK] {summary_csv}")

    # Aggregate diagnostic
    overall_dsm_area = summary["dsm_building_area_m2"].sum()
    overall_osm_area = summary["osm_building_area_m2"].sum()
    overall_pct = 100.0 * overall_dsm_area / overall_osm_area if overall_osm_area > 0 else float("nan")

    print(f"\n[AGGREGATE] Across all 6 tile buffers:")
    print(f"  OSM total building area: {overall_osm_area:,.0f} m²")
    print(f"  DSM total building area: {overall_dsm_area:,.0f} m²")
    print(f"  DSM captures {overall_pct:.1f}% of OSM-mapped buildings")
    print(f"  Missing (OSM - DSM): {overall_osm_area - overall_dsm_area:,.0f} m² "
          f"({100.0 * (overall_osm_area - overall_dsm_area) / overall_osm_area:.1f}%)")
    print()
    print("Caveats:")
    print("  - OSM is itself incomplete; this is a lower bound on missing structures")
    print("  - 'Missing' includes: structures present in OSM but not HDB3D+URA")
    print("  - 'Excess' (DSM > OSM): possible if HDB3D includes structures OSM lacks")


if __name__ == "__main__":
    main()
