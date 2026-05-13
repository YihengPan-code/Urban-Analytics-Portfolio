"""
OpenHeat v1.0-alpha: standardize HDB3D, URA and OSM building sources.

Outputs standardized per-source GeoJSONs and an all-candidates GeoJSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import pandas as pd
from shapely.validation import make_valid


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_geometries(gdf: gpd.GeoDataFrame, crs: str) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs(crs)
    gdf = gdf.to_crs(crs)
    gdf = gdf[~gdf.geometry.isna()].copy()
    gdf["geometry"] = gdf.geometry.apply(lambda g: make_valid(g) if g is not None and not g.is_valid else g)
    gdf = gdf[~gdf.geometry.is_empty].copy()
    # explode multi parts
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    gdf["area_m2"] = gdf.geometry.area
    return gdf


def find_height_col(gdf: gpd.GeoDataFrame) -> Optional[str]:
    candidates = ["height_m", "height", "HEIGHT", "Height", "HGT", "height_mean"]
    for c in candidates:
        if c in gdf.columns:
            return c
    # fuzzy
    for c in gdf.columns:
        if "height" in c.lower() and c != "geometry":
            return c
    return None


def to_numeric_height(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace("m", "", case=False).str.replace("metres", "", case=False).str.strip()
    return pd.to_numeric(s, errors="coerce")


def raw_json(row: pd.Series, max_chars: int = 2000) -> str:
    d = {}
    for k, v in row.items():
        if k == "geometry":
            continue
        try:
            if pd.isna(v):
                continue
        except Exception:
            pass
        d[str(k)] = str(v)
    txt = json.dumps(d, ensure_ascii=False)
    return txt[:max_chars]


def standardize_source(path: Path, source_name: str, priority: int, crs: str, min_area: float) -> gpd.GeoDataFrame:
    if not path.exists():
        print(f"[WARN] source path missing, skipping {source_name}: {path}")
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=crs)
    gdf_raw = gpd.read_file(path)
    gdf = clean_geometries(gdf_raw, crs)
    gdf = gdf[gdf["area_m2"] >= min_area].copy()
    hcol = find_height_col(gdf)

    out = gpd.GeoDataFrame(geometry=gdf.geometry, crs=crs)
    out["source_name"] = source_name
    out["source_priority"] = priority
    out["source_building_id"] = [f"{source_name}_{i}" for i in range(len(gdf))]
    if source_name == "osm" and "osm_id" in gdf.columns:
        out["source_building_id"] = "osm_" + gdf["osm_id"].astype(str)
    elif "building_id" in gdf.columns:
        out["source_building_id"] = source_name + "_" + gdf["building_id"].astype(str)

    out["area_m2"] = gdf["area_m2"].astype(float)
    out["height_m_original"] = to_numeric_height(gdf[hcol]) if hcol else pd.NA
    out["height_source_original"] = hcol if hcol else "none"
    out["levels_original"] = pd.NA
    out["building_type_original"] = pd.NA
    out["confidence_original"] = pd.NA

    if source_name == "osm":
        if "building_levels" in gdf.columns:
            out["levels_original"] = pd.to_numeric(gdf["building_levels"], errors="coerce")
        if "building" in gdf.columns:
            out["building_type_original"] = gdf["building"].astype(str)
        if "height" in gdf.columns:
            osm_h = to_numeric_height(gdf["height"])
            out["height_m_original"] = out["height_m_original"].fillna(osm_h)
            out.loc[osm_h.notna(), "height_source_original"] = "osm_height_tag"
    else:
        # common type columns
        for c in ["BLDG_TYPE", "bldg_type", "TYPE", "building", "osm_building"]:
            if c in gdf.columns:
                out["building_type_original"] = gdf[c].astype(str)
                break

    # keep raw source properties in short JSON for provenance
    out["raw_properties_json"] = [raw_json(r) for _, r in gdf.iterrows()]
    out["candidate_id"] = [f"cand_{source_name}_{i:06d}" for i in range(len(out))]
    out["geometry_source"] = source_name
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_alpha_augmented_dsm_config.example.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    crs = cfg.get("crs", "EPSG:3414")
    out_dir = Path(cfg["outputs"]["source_standardized_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    priorities = cfg.get("dedup", {}).get("source_priority", {"hdb3d": 1, "ura": 2, "osm": 3})
    min_areas = cfg.get("dedup", {}).get("min_area_m2", {"hdb3d": 5, "ura": 5, "osm": 10})

    sources = []
    for name in ["hdb3d", "ura", "osm"]:
        path = Path(cfg["sources"][name])
        g = standardize_source(path, name, int(priorities.get(name, 99)), crs, float(min_areas.get(name, 5)))
        if len(g):
            out_fp = out_dir / f"{name}_standardized.geojson"
            g.to_file(out_fp, driver="GeoJSON")
            print(f"[OK] {name}: {len(g)} features -> {out_fp}")
            sources.append(g)
        else:
            print(f"[WARN] {name}: no features")

    if not sources:
        raise RuntimeError("No standardized sources created.")
    all_g = gpd.GeoDataFrame(pd.concat(sources, ignore_index=True), geometry="geometry", crs=crs)
    all_g["area_m2"] = all_g.geometry.area
    all_out = Path(cfg["outputs"]["all_candidates"])
    all_out.parent.mkdir(parents=True, exist_ok=True)
    all_g.to_file(all_out, driver="GeoJSON")
    print(f"[OK] all candidates: {len(all_g)} -> {all_out}")

    # QA report
    qa_rows = []
    for name, sub in all_g.groupby("source_name"):
        qa_rows.append({
            "source_name": name,
            "n": len(sub),
            "area_sum_m2": float(sub.geometry.area.sum()),
            "area_mean_m2": float(sub.geometry.area.mean()),
            "height_non_null": int(pd.to_numeric(sub["height_m_original"], errors="coerce").notna().sum()),
        })
    qa = pd.DataFrame(qa_rows)
    report = Path(cfg["outputs"]["source_qa_report"])
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# v1.0-alpha source standardization QA", "", f"All candidates: **{len(all_g)}**", "", qa.to_string(index=False)]
    report.write_text("\n".join(lines), encoding="utf-8")
    qa.to_csv(report.with_suffix(".csv"), index=False)
    print(f"[OK] QA report: {report}")


if __name__ == "__main__":
    main()
