from __future__ import annotations

from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

WGS84 = "EPSG:4326"
SVY21 = "EPSG:3414"


def read_vector(path: str | Path, layer: str | None = None, target_crs: str = SVY21) -> gpd.GeoDataFrame:
    """Read a vector file, fix invalid geometries, and project to target CRS.

    The function intentionally accepts common vector formats supported by GeoPandas:
    GeoJSON, GPKG, Shapefile, FlatGeobuf, etc. CRS-less files are assumed WGS84
    because most Singapore open-data GeoJSON files are in lon/lat.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Vector file not found: {path}")
    if layer:
        gdf = gpd.read_file(path, layer=layer)
    else:
        gdf = gpd.read_file(path)
    if gdf.empty:
        return gpd.GeoDataFrame(gdf, geometry="geometry", crs=target_crs)
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    gdf = clean_geometries(gdf)
    return gdf.to_crs(target_crs)


def clean_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop empty geometries and fix common invalid polygons with buffer(0)."""
    gdf = gdf.copy()
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.empty:
        return gdf
    # buffer(0) is the simplest portable invalid-polygon repair for this MVP.
    try:
        invalid = ~gdf.geometry.is_valid
        if invalid.any():
            gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)
            gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    except Exception:
        pass
    return gdf


def aoi_from_bbox_wgs84(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> gpd.GeoDataFrame:
    """Create a one-feature AOI polygon from WGS84 bbox and project to SVY21."""
    gdf = gpd.GeoDataFrame({"aoi_id": ["aoi_bbox"]}, geometry=[box(min_lon, min_lat, max_lon, max_lat)], crs=WGS84)
    return gdf.to_crs(SVY21)


def clip_to_aoi(gdf: gpd.GeoDataFrame, aoi: gpd.GeoDataFrame, buffer_m: float = 0) -> gpd.GeoDataFrame:
    """Clip a layer to AOI, optionally with a projected buffer."""
    if gdf.empty:
        return gdf.copy()
    aoi_proj = aoi.to_crs(gdf.crs)
    geom = aoi_proj.geometry.unary_union
    if buffer_m:
        geom = geom.buffer(buffer_m)
    try:
        return gpd.clip(gdf, geom)
    except Exception:
        return gdf[gdf.intersects(geom)].copy()


def standardise_id_column(grid: gpd.GeoDataFrame, id_col: str = "cell_id") -> gpd.GeoDataFrame:
    if id_col not in grid.columns:
        raise ValueError(f"Grid missing required id column: {id_col}")
    grid = grid.copy()
    grid[id_col] = grid[id_col].astype(str)
    return grid


def ensure_required_columns(df: pd.DataFrame, cols: Iterable[str], context: str = "dataframe") -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{context} missing required columns: {missing}")
