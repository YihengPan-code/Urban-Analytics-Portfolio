from __future__ import annotations

from pathlib import Path
from typing import Sequence

import geopandas as gpd
import numpy as np
import pandas as pd

from .geospatial import SVY21, clip_to_aoi, clean_geometries, ensure_required_columns


def _empty_feature(grid: gpd.GeoDataFrame, name: str, value=0.0) -> pd.DataFrame:
    return pd.DataFrame({"cell_id": grid["cell_id"].astype(str), name: value})


def _overlay_area_sum(grid: gpd.GeoDataFrame, features: gpd.GeoDataFrame, out_col: str) -> pd.DataFrame:
    if features is None or features.empty:
        return _empty_feature(grid, out_col, 0.0)
    g = grid[["cell_id", "cell_area_m2", "geometry"]].to_crs(SVY21).copy()
    f = clean_geometries(features.to_crs(SVY21))
    if f.empty:
        return _empty_feature(grid, out_col, 0.0)
    try:
        inter = gpd.overlay(g, f[["geometry"]], how="intersection", keep_geom_type=False)
    except Exception:
        # fallback via spatial prefilter
        f = f[f.intersects(g.geometry.unary_union)].copy()
        if f.empty:
            return _empty_feature(grid, out_col, 0.0)
        inter = gpd.overlay(g, f[["geometry"]], how="intersection", keep_geom_type=False)
    if inter.empty:
        return _empty_feature(grid, out_col, 0.0)
    inter["_area"] = inter.geometry.area
    out = inter.groupby("cell_id", as_index=False)["_area"].sum()
    out = g[["cell_id", "cell_area_m2"]].merge(out, on="cell_id", how="left").fillna({"_area": 0})
    out[out_col] = (out["_area"] / out["cell_area_m2"]).clip(0, 1)
    return out[["cell_id", out_col]]


def building_density(grid: gpd.GeoDataFrame, buildings: gpd.GeoDataFrame | None) -> pd.DataFrame:
    return _overlay_area_sum(grid, buildings, "building_density")


def road_fraction(grid: gpd.GeoDataFrame, roads: gpd.GeoDataFrame | None, buffer_m: float = 7.0) -> pd.DataFrame:
    if roads is None or roads.empty:
        return _empty_feature(grid, "road_fraction", 0.0)
    roads = roads.to_crs(SVY21).copy()
    geom_types = set(roads.geometry.geom_type.dropna().unique())
    if geom_types & {"LineString", "MultiLineString"}:
        roads["geometry"] = roads.geometry.buffer(buffer_m, cap_style=2)
    return _overlay_area_sum(grid, roads, "road_fraction")


def nearest_polygon_distance(
    grid: gpd.GeoDataFrame,
    polygons: gpd.GeoDataFrame | None,
    out_col: str,
    name_col_candidates: Sequence[str] = ("NAME", "name", "Name"),
    max_distance_if_missing: float = 9999.0,
) -> pd.DataFrame:
    grid = grid.to_crs(SVY21).copy()
    centroids = grid.geometry.centroid
    if polygons is None or polygons.empty:
        return pd.DataFrame({"cell_id": grid["cell_id"], out_col: max_distance_if_missing, f"nearest_{out_col.replace('_distance_m','')}_name": None})
    polys = clean_geometries(polygons.to_crs(SVY21))
    if polys.empty:
        return pd.DataFrame({"cell_id": grid["cell_id"], out_col: max_distance_if_missing, f"nearest_{out_col.replace('_distance_m','')}_name": None})
    name_col = next((c for c in name_col_candidates if c in polys.columns), None)
    distances = []
    names = []
    for pt in centroids:
        d = polys.geometry.distance(pt)
        if d.empty:
            distances.append(max_distance_if_missing)
            names.append(None)
        else:
            i = d.idxmin()
            distances.append(float(d.loc[i]))
            names.append(str(polys.loc[i, name_col]) if name_col else None)
    return pd.DataFrame({"cell_id": grid["cell_id"].astype(str), out_col: distances, f"nearest_{out_col.replace('_distance_m','')}_name": names})


def park_distances(grid: gpd.GeoDataFrame, parks: gpd.GeoDataFrame | None, large_park_threshold_ha: float = 10.0) -> pd.DataFrame:
    if parks is None or parks.empty:
        out = pd.DataFrame({"cell_id": grid["cell_id"].astype(str), "park_distance_m": 9999.0, "large_park_distance_m": 9999.0, "nearest_park_name": None, "nearest_large_park_name": None})
        return out
    parks = parks.to_crs(SVY21).copy()
    parks["_area_ha"] = parks.geometry.area / 10000.0
    allp = nearest_polygon_distance(grid, parks, "park_distance_m")
    large = parks[parks["_area_ha"] >= large_park_threshold_ha].copy()
    lg = nearest_polygon_distance(grid, large, "large_park_distance_m")
    out = allp.merge(lg, on="cell_id", how="left")
    # Clean generated names.
    out = out.rename(columns={"nearest_park_name": "nearest_park_name", "nearest_large_park_name": "nearest_large_park_name"})
    return out


def land_use_majority(
    grid: gpd.GeoDataFrame,
    land_use: gpd.GeoDataFrame | None,
    lu_col: str = "LU_DESC",
    gpr_col: str = "GPR",
) -> pd.DataFrame:
    grid = grid.to_crs(SVY21).copy()
    if land_use is None or land_use.empty:
        return pd.DataFrame({"cell_id": grid["cell_id"].astype(str), "land_use_hint": "unknown", "land_use_raw": "unknown", "land_use_fraction": 0.0, "gpr_area_weighted": np.nan})
    lu = clean_geometries(land_use.to_crs(SVY21)).copy()
    if lu_col not in lu.columns:
        # fallback to first likely text column
        for c in ["LU_DESC", "Description", "Name", "landuse", "land_use"]:
            if c in lu.columns:
                lu_col = c
                break
    if lu_col not in lu.columns:
        lu[lu_col] = "unknown"
    keep = [lu_col, "geometry"] + ([gpr_col] if gpr_col in lu.columns else [])
    inter = gpd.overlay(grid[["cell_id", "cell_area_m2", "geometry"]], lu[keep], how="intersection", keep_geom_type=False)
    if inter.empty:
        return pd.DataFrame({"cell_id": grid["cell_id"].astype(str), "land_use_hint": "unknown", "land_use_raw": "unknown", "land_use_fraction": 0.0, "gpr_area_weighted": np.nan})
    inter["_area"] = inter.geometry.area
    inter["_lu"] = inter[lu_col].astype(str).str.upper().str.strip()
    by = inter.groupby(["cell_id", "_lu"], as_index=False)["_area"].sum()
    idx = by.groupby("cell_id")["_area"].idxmax()
    maj = by.loc[idx].copy()
    maj = maj.merge(grid[["cell_id", "cell_area_m2"]], on="cell_id", how="left")
    maj["land_use_fraction"] = maj["_area"] / maj["cell_area_m2"]
    maj["land_use_raw"] = maj["_lu"]
    maj["land_use_hint"] = maj["_lu"].map(simplify_land_use).fillna("other")
    out = maj[["cell_id", "land_use_hint", "land_use_raw", "land_use_fraction"]]
    if gpr_col in inter.columns:
        tmp = inter[["cell_id", "_area", gpr_col]].copy()
        tmp["_gpr"] = pd.to_numeric(tmp[gpr_col].replace({"EVA": np.nan, "-": np.nan, "": np.nan}), errors="coerce")
        tmp["_wx"] = tmp["_area"] * tmp["_gpr"]
        gpr = tmp.groupby("cell_id", as_index=False).agg(_wx=("_wx", "sum"), _area=("_area", "sum"))
        gpr["gpr_area_weighted"] = gpr["_wx"] / gpr["_area"]
        out = out.merge(gpr[["cell_id", "gpr_area_weighted"]], on="cell_id", how="left")
    else:
        out["gpr_area_weighted"] = np.nan
    # Include every grid cell.
    out = grid[["cell_id"]].merge(out, on="cell_id", how="left")
    out["land_use_hint"] = out["land_use_hint"].fillna("unknown")
    out["land_use_raw"] = out["land_use_raw"].fillna("unknown")
    out["land_use_fraction"] = out["land_use_fraction"].fillna(0.0)
    return out


def simplify_land_use(x: str) -> str:
    x = str(x).upper()
    if any(s in x for s in ["RESIDENTIAL", "HOUSING"]):
        return "residential"
    if any(s in x for s in ["COMMERCIAL", "BUSINESS", "WHITE"]):
        return "commercial"
    if any(s in x for s in ["PARK", "OPEN SPACE", "BEACH", "NATURE"]):
        return "park_open_space"
    if any(s in x for s in ["ROAD", "TRANSPORT", "MRT", "RAIL", "RAPID TRANSIT", "BUS"]):
        return "transport"
    if any(s in x for s in ["WATER", "RESERVOIR", "DRAINAGE"]):
        return "water"
    if any(s in x for s in ["CIVIC", "COMMUNITY", "EDUCATIONAL", "HEALTH", "SPORT", "PLACE OF WORSHIP", "UTILITY"]):
        return "civic_institutional"
    return "other"


def merge_optional_feature_csv(base: pd.DataFrame, path: str | Path | None, required_value_cols: Sequence[str]) -> pd.DataFrame:
    if not path:
        return base
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Optional feature CSV not found: {path}")
    df = pd.read_csv(path)
    ensure_required_columns(df, ["cell_id", *required_value_cols], str(path))
    return base.merge(df[["cell_id", *required_value_cols]], on="cell_id", how="left")


def apply_height_proxy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "mean_building_height_m" not in df.columns:
        base = 4 + 42 * df.get("building_density", 0).fillna(0)
        lu = df.get("land_use_hint", pd.Series("unknown", index=df.index)).astype(str)
        base += np.where(lu.eq("commercial"), 8, 0)
        base += np.where(lu.eq("residential"), 4, 0)
        base = np.where(lu.isin(["park_open_space", "water"]), 2.0, base)
        df["mean_building_height_m"] = np.clip(base, 2, 55)
        df["height_source"] = "empirical_proxy_from_density_land_use"
    else:
        df["mean_building_height_m"] = pd.to_numeric(df["mean_building_height_m"], errors="coerce")
        df["height_source"] = df.get("height_source", "external_height_csv_or_raster")
    if "max_building_height_m" not in df.columns:
        df["max_building_height_m"] = np.clip(df["mean_building_height_m"] * 1.65, 3, 85)
    return df


def derive_greenery_proxy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "tree_canopy_fraction" not in df.columns:
        # Coarse fallback from park distance and land use. Replace with Dynamic World/NDVI in v0.7-beta.
        pdist = pd.to_numeric(df.get("park_distance_m", 9999), errors="coerce").fillna(9999)
        lu = df.get("land_use_hint", pd.Series("unknown", index=df.index)).astype(str)
        tree = 0.05 + 0.35 * np.exp(-pdist / 300.0)
        tree += np.where(lu.eq("park_open_space"), 0.25, 0)
        tree += np.where(lu.eq("residential"), 0.05, 0)
        df["tree_canopy_fraction"] = np.clip(tree, 0.02, 0.75)
        df["tree_canopy_source"] = "proxy_from_park_distance_land_use"
    else:
        df["tree_canopy_fraction"] = pd.to_numeric(df["tree_canopy_fraction"], errors="coerce").clip(0, 1)
        df["tree_canopy_source"] = df.get("tree_canopy_source", "external_tree_canopy_csv")
    if "gvi_percent" not in df.columns:
        df["gvi_percent"] = np.clip(60 * df["tree_canopy_fraction"], 0, 70)
        df["gvi_source"] = "proxy_60x_tree_canopy_fraction"
    return df


def derive_morphology_proxies(df: pd.DataFrame, cell_size_m: float = 100.0) -> pd.DataFrame:
    """Derive v0.7 screening-level morphology features.

    These are NOT UMEP/SOLWEIG-grade SVF or shade. They are deliberately named
    proxies internally but output as `svf` and `shade_fraction` because the v0.6
    forecast engine expects those column names.
    """
    df = df.copy()
    bd = pd.to_numeric(df.get("building_density", 0), errors="coerce").fillna(0).clip(0, 1)
    h = pd.to_numeric(df.get("mean_building_height_m", 10), errors="coerce").fillna(10).clip(0, 80)
    road = pd.to_numeric(df.get("road_fraction", 0), errors="coerce").fillna(0).clip(0, 1)
    tree = pd.to_numeric(df.get("tree_canopy_fraction", 0), errors="coerce").fillna(0).clip(0, 1)
    height_term = h / max(cell_size_m, 1)
    svf = 1.0 / (1.0 + 0.55 * height_term + 1.8 * bd)
    svf += 0.10 * road  # open roads increase sky exposure in this coarse proxy.
    df["svf"] = np.clip(svf, 0.18, 0.98)
    shade = 0.08 + 0.55 * bd + 0.28 * np.clip(h / 40.0, 0, 1) + 0.25 * tree - 0.15 * road
    df["shade_fraction"] = np.clip(shade, 0.04, 0.90)
    lu = df.get("land_use_hint", pd.Series("unknown", index=df.index)).astype(str)
    imperv = bd + road + np.where(lu.isin(["commercial", "transport", "civic_institutional"]), 0.25, 0.10)
    imperv -= 0.35 * tree
    df["impervious_fraction"] = np.clip(imperv, 0.0, 1.0)
    # v0.7 placeholder risk proxies; replace in v0.7.1.
    if "elderly_proxy" not in df.columns:
        df["elderly_proxy"] = np.where(lu.eq("residential"), 0.55, 0.35)
        df["elderly_proxy_source"] = "placeholder_from_land_use_v07_alpha"
    if "outdoor_exposure_proxy" not in df.columns:
        exp = 0.35 + 0.25 * road + np.where(lu.eq("commercial"), 0.35, 0) + np.where(lu.eq("park_open_space"), 0.25, 0) + np.where(lu.eq("transport"), 0.25, 0)
        df["outdoor_exposure_proxy"] = np.clip(exp, 0.05, 1.0)
        df["outdoor_exposure_source"] = "placeholder_from_land_use_road_v07_alpha"
    return df


def final_forecast_grid_columns(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "cell_id", "lat", "lon", "building_density", "road_fraction", "gvi_percent", "svf", "shade_fraction",
        "park_distance_m", "elderly_proxy", "outdoor_exposure_proxy", "land_use_hint",
    ]
    for c in required:
        if c not in df.columns:
            if c == "land_use_hint":
                df[c] = "unknown"
            else:
                df[c] = 0.0
    # Keep required first, then extras.
    extra = [c for c in df.columns if c not in required and c != "geometry"]
    return df[required + extra]
