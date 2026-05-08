from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from .geospatial import SVY21, WGS84, aoi_from_bbox_wgs84, clean_geometries, read_vector


def load_aoi(config: dict) -> gpd.GeoDataFrame:
    """Load AOI from path or bbox in config.

    Config options:
    - aoi_path: vector file path, any CRS
    - bbox_wgs84: [min_lon, min_lat, max_lon, max_lat]
    """
    aoi_path = config.get("aoi_path")
    if aoi_path:
        aoi = read_vector(aoi_path, target_crs=SVY21)
        aoi["aoi_id"] = aoi.get("aoi_id", "aoi_file")
        return aoi[["aoi_id", "geometry"]]
    bbox = config.get("bbox_wgs84")
    if not bbox or len(bbox) != 4:
        raise ValueError("Config needs either aoi_path or bbox_wgs84: [min_lon, min_lat, max_lon, max_lat]")
    return aoi_from_bbox_wgs84(*map(float, bbox))


def make_square_grid(aoi: gpd.GeoDataFrame, cell_size_m: float = 100.0, prefix: str = "TP") -> gpd.GeoDataFrame:
    """Generate a square grid covering AOI in SVY21 and clipped by centroid-inside AOI.

    The geometry remains a full square cell. We retain cells whose centroid falls
    inside the AOI. This avoids edge slivers and keeps the forecast grid simple.
    """
    aoi = aoi.to_crs(SVY21)
    union = aoi.geometry.unary_union
    minx, miny, maxx, maxy = union.bounds
    start_x = math.floor(minx / cell_size_m) * cell_size_m
    start_y = math.floor(miny / cell_size_m) * cell_size_m
    end_x = math.ceil(maxx / cell_size_m) * cell_size_m
    end_y = math.ceil(maxy / cell_size_m) * cell_size_m

    cells = []
    ids = []
    idx = 1
    y = start_y
    while y < end_y:
        x = start_x
        while x < end_x:
            geom = box(x, y, x + cell_size_m, y + cell_size_m)
            if geom.centroid.within(union):
                ids.append(f"{prefix}_{idx:04d}")
                cells.append(geom)
                idx += 1
            x += cell_size_m
        y += cell_size_m
    grid = gpd.GeoDataFrame({"cell_id": ids}, geometry=cells, crs=SVY21)
    grid["cell_area_m2"] = grid.geometry.area
    cent = grid.geometry.centroid
    grid["centroid_x_svy21"] = cent.x
    grid["centroid_y_svy21"] = cent.y
    cent_gdf = gpd.GeoDataFrame({"cell_id": grid["cell_id"]}, geometry=cent, crs=SVY21).to_crs(WGS84)
    grid["lon"] = cent_gdf.geometry.x.to_numpy()
    grid["lat"] = cent_gdf.geometry.y.to_numpy()
    return grid


def write_grid_outputs(grid: gpd.GeoDataFrame, out_geojson: str | Path, out_csv: str | Path) -> None:
    out_geojson = Path(out_geojson)
    out_csv = Path(out_csv)
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    grid.to_crs(WGS84).to_file(out_geojson, driver="GeoJSON")
    cols = [c for c in grid.columns if c != "geometry"]
    grid[cols].to_csv(out_csv, index=False)
