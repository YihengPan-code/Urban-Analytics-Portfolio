from __future__ import annotations

"""Optional OSM extractor for v0.7 roads/water.

Requires pyrosm, which can be tricky on Windows. If installation is painful,
use QGIS instead to export `osm_roads_toa_payoh.geojson` and
`osm_water_toa_payoh.geojson` manually.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import geopandas as gpd

from openheat_grid.grid import load_aoi
from openheat_grid.geospatial import SVY21, WGS84, clip_to_aoi


def main():
    parser = argparse.ArgumentParser(description="Extract roads/water from Singapore OSM PBF for OpenHeat v0.7")
    parser.add_argument("--pbf", required=True, help="Path to singapore-latest.osm.pbf")
    parser.add_argument("--config", default=str(ROOT / "configs/v07_grid_features_config.example.json"))
    parser.add_argument("--out-dir", default=str(ROOT / "data/raw"))
    args = parser.parse_args()

    try:
        from pyrosm import OSM
    except Exception as e:
        raise SystemExit("pyrosm is not installed. Try `pip install pyrosm` or use QGIS to export roads/water manually.") from e

    import json
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    aoi = load_aoi(cfg)
    bbox_wgs = aoi.to_crs(WGS84).total_bounds  # minx,miny,maxx,maxy
    osm = OSM(args.pbf, bounding_box=list(bbox_wgs))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[INFO] extracting roads")
    roads = osm.get_network(network_type="driving")
    if roads is None or roads.empty:
        roads = gpd.GeoDataFrame(geometry=[], crs=WGS84)
    roads = clip_to_aoi(roads.to_crs(SVY21), aoi, buffer_m=200).to_crs(WGS84)
    roads.to_file(out_dir / "osm_roads_toa_payoh.geojson", driver="GeoJSON")
    print(f"[OK] roads: {len(roads)} -> {out_dir / 'osm_roads_toa_payoh.geojson'}")

    print("[INFO] extracting water polygons")
    water = osm.get_data_by_custom_criteria(
        custom_filter={"natural": ["water"], "waterway": ["riverbank", "dock"], "landuse": ["reservoir", "basin"]},
        filter_type="keep",
        keep_nodes=False,
        keep_ways=True,
        keep_relations=True,
    )
    if water is None or water.empty:
        water = gpd.GeoDataFrame(geometry=[], crs=WGS84)
    water = water[water.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    if not water.empty:
        water = clip_to_aoi(water.to_crs(SVY21), aoi, buffer_m=2000).to_crs(WGS84)
    water.to_file(out_dir / "osm_water_toa_payoh.geojson", driver="GeoJSON")
    print(f"[OK] water: {len(water)} -> {out_dir / 'osm_water_toa_payoh.geojson'}")


if __name__ == "__main__":
    main()
