"""
OpenHeat v1.0-alpha: extract OSM building footprints for the Toa Payoh AOI.

This script uses Overpass API directly via requests, so osmnx is not required.
It saves raw OSM building polygons to data/raw/buildings_v10/osm_buildings_toapayoh.geojson.

Notes:
- OSM is not ground truth; it is used as a gap-filling and audit source.
- This script primarily parses closed ways. Multipolygon relations are logged but not deeply reconstructed in v10-alpha.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Polygon
from shapely.validation import make_valid


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_aoi_bbox_wgs84(cfg: Dict[str, Any]) -> tuple[float, float, float, float]:
    crs = cfg.get("crs", "EPSG:3414")
    aoi_path = Path(cfg.get("aoi_buffered_geojson", ""))
    if aoi_path.exists():
        aoi = gpd.read_file(aoi_path)
    else:
        grid = gpd.read_file(cfg["base_grid_geojson"])
        if grid.crs is None:
            grid = grid.set_crs(crs)
        grid = grid.to_crs(crs)
        # buffer total union, not individual cell polygons, to keep bbox stable
        union = grid.geometry.union_all() if hasattr(grid.geometry, "union_all") else grid.unary_union
        aoi = gpd.GeoDataFrame({"id": [1]}, geometry=[union.buffer(float(cfg.get("aoi_buffer_m", 200)))], crs=crs)
    if aoi.crs is None:
        aoi = aoi.set_crs(crs)
    aoi_wgs = aoi.to_crs("EPSG:4326")
    minx, miny, maxx, maxy = aoi_wgs.total_bounds
    # Overpass bbox order: south, west, north, east
    return float(miny), float(minx), float(maxy), float(maxx)


def build_overpass_query(bbox: tuple[float, float, float, float], include_relations: bool = False) -> str:
    s, w, n, e = bbox
    relation_part = f'relation["building"]({s},{w},{n},{e});' if include_relations else ""
    return f"""
[out:json][timeout:180];
(
  way["building"]({s},{w},{n},{e});
  {relation_part}
);
out tags geom;
""".strip()


def request_overpass(cfg: Dict[str, Any], query: str) -> Dict[str, Any]:
    overpass_cfg = cfg.get("overpass", {})
    endpoints = overpass_cfg.get("endpoints", ["https://overpass-api.de/api/interpreter"])
    timeout = int(overpass_cfg.get("timeout_seconds", 180))
    ua = overpass_cfg.get("user_agent", "OpenHeat-ToaPayoh-v10-alpha/1.0")
    headers = {"User-Agent": ua}
    last_error = None
    for url in endpoints:
        try:
            print(f"[INFO] trying {url}")
            t0 = time.time()
            r = requests.post(url, data={"data": query}, timeout=timeout, headers=headers)
            print(f"[INFO] response in {time.time()-t0:.1f}s, status={r.status_code}")
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[WARN] Overpass endpoint failed: {url}: {exc}")
    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_error}")


def parse_way_polygon(el: Dict[str, Any]) -> Optional[Polygon]:
    geom = el.get("geometry") or []
    if len(geom) < 4:
        return None
    coords = [(float(p["lon"]), float(p["lat"])) for p in geom if "lon" in p and "lat" in p]
    if len(coords) < 4:
        return None
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    try:
        poly = Polygon(coords)
        if poly.is_empty:
            return None
        if not poly.is_valid:
            poly = make_valid(poly)
        if poly.geom_type == "Polygon":
            return poly
        # If make_valid returns MultiPolygon, keep largest part.
        if poly.geom_type == "MultiPolygon":
            return max(list(poly.geoms), key=lambda g: g.area)
    except Exception:
        return None
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_alpha_augmented_dsm_config.example.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    out_path = Path(args.out or cfg["outputs"]["osm_raw"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    bbox = get_aoi_bbox_wgs84(cfg)
    print(f"[INFO] Overpass bbox (S,W,N,E): {bbox}")
    query = build_overpass_query(bbox, include_relations=bool(cfg.get("overpass", {}).get("include_relations", False)))
    payload = request_overpass(cfg, query)
    elements = payload.get("elements", [])
    print(f"[INFO] OSM elements returned: {len(elements)}")

    rows: List[Dict[str, Any]] = []
    skipped_relations = 0
    skipped_invalid = 0
    for el in elements:
        if el.get("type") != "way":
            skipped_relations += 1
            continue
        poly = parse_way_polygon(el)
        if poly is None:
            skipped_invalid += 1
            continue
        tags = el.get("tags", {}) or {}
        row = {
            "osm_id": str(el.get("id")),
            "source_name": "osm",
            "building": tags.get("building"),
            "building_levels": tags.get("building:levels"),
            "height": tags.get("height") or tags.get("building:height"),
            "roof_levels": tags.get("roof:levels"),
            "covered": tags.get("covered"),
            "bridge": tags.get("bridge"),
            "layer": tags.get("layer"),
            "name": tags.get("name"),
            "raw_tags_json": json.dumps(tags, ensure_ascii=False),
            "geometry": poly,
        }
        rows.append(row)

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    if len(gdf):
        gdf = gdf.to_crs(cfg.get("crs", "EPSG:3414"))
        gdf["area_m2"] = gdf.geometry.area
        # basic cleanup
        gdf = gdf[gdf["area_m2"] >= 5].copy()
        gdf = gdf.to_crs("EPSG:4326")

    gdf.to_file(out_path, driver="GeoJSON")
    print(f"[OK] wrote OSM buildings: {out_path}")
    print(f"[INFO] parsed way polygons: {len(gdf)}")
    print(f"[INFO] skipped non-way relations/elements: {skipped_relations}")
    print(f"[INFO] skipped invalid ways: {skipped_invalid}")


if __name__ == "__main__":
    main()
