"""
OpenHeat v1.0-alpha.1 hotfix
Assign building heights with provenance after canonical deduplication.

Inputs:
  data/features_3d/v10/canonical/canonical_buildings_v10.geojson
  data/raw/ura_masterplan2019_land_use.geojson (optional, for LU defaults)
Outputs:
  data/features_3d/v10/height_imputed/canonical_buildings_v10_height.geojson
  data/features_3d/v10/height_imputed/height_imputation_QA.csv
  outputs/v10_dsm_audit/v10_height_imputation_QA.md
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd

DEFAULT_CONFIG = {
    "crs": "EPSG:3414",
    "paths": {
        "canonical_buildings": "data/features_3d/v10/canonical/canonical_buildings_v10.geojson",
        "land_use": "data/raw/ura_masterplan2019_land_use.geojson",
        "canonical_buildings_height": "data/features_3d/v10/height_imputed/canonical_buildings_v10_height.geojson",
        "height_qa_csv": "data/features_3d/v10/height_imputed/height_imputation_QA.csv",
        "height_report": "outputs/v10_dsm_audit/v10_height_imputation_QA.md"
    }
}

HEIGHT_KEYS = ["height_m_original", "height_m", "height", "building:height", "building_height", "osm_height_m", "HEIGHT", "Height"]
LEVEL_KEYS = ["levels_original", "building:levels", "building_levels", "osm_levels", "levels", "Levels"]
TYPE_KEYS = ["building_type_original", "building", "building_tag", "osm_building", "type", "class"]

LU_DEFAULTS = [
    ("HOSPITAL", 24.0, "lu_default:HOSPITAL"),
    ("HEALTH", 18.0, "lu_default:HEALTH"),
    ("HOTEL", 30.0, "lu_default:HOTEL"),
    ("BUSINESS PARK", 24.0, "lu_default:BUSINESS PARK"),
    ("COMMERCIAL", 20.0, "lu_default:COMMERCIAL"),
    ("MASS RAPID TRANSIT", 12.0, "lu_default:TRANSPORT"),
    ("TRANSPORT", 8.0, "lu_default:TRANSPORT"),
    ("ROAD", 8.0, "lu_default:TRANSPORT"),
    ("EDUCATIONAL", 12.0, "lu_default:EDUCATIONAL"),
    ("CIVIC", 12.0, "lu_default:CIVIC"),
    ("COMMUNITY", 12.0, "lu_default:CIVIC"),
    ("PLACE OF WORSHIP", 10.0, "lu_default:PLACE OF WORSHIP"),
    ("INDUSTRIAL", 10.0, "lu_default:INDUSTRIAL"),
    ("UTILITY", 8.0, "lu_default:UTILITY"),
    ("PARK", 6.0, "lu_default:PARK"),
    ("SPORT", 9.0, "lu_default:SPORTS"),
    ("RESIDENTIAL", 15.0, "lu_default:RESIDENTIAL"),
]


def load_config(path: Optional[str]) -> Dict[str, Any]:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path and Path(path).exists():
        user = json.loads(Path(path).read_text(encoding="utf-8"))
        def deep_update(a, b):
            for k, v in b.items():
                if isinstance(v, dict) and isinstance(a.get(k), dict):
                    deep_update(a[k], v)
                else:
                    a[k] = v
        deep_update(cfg, user)
    return cfg


def parse_number(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    if isinstance(x, (int, float, np.number)):
        val = float(x)
    else:
        s = str(x).strip().lower()
        # handle common height strings like "12 m", "12.5m", "12;14"
        m = re.search(r"[-+]?\d*\.?\d+", s)
        if not m:
            return None
        try:
            val = float(m.group(0))
        except Exception:
            return None
    if not np.isfinite(val):
        return None
    return val


def first_valid(row: pd.Series, keys: list[str]) -> Tuple[Optional[str], Optional[Any]]:
    for k in keys:
        if k in row.index:
            v = row[k]
            try:
                if pd.isna(v):
                    continue
            except Exception:
                pass
            if v is not None and str(v).strip() not in ["", "nan", "None"]:
                return k, v
    return None, None


def infer_lu_desc(buildings: gpd.GeoDataFrame, land_use_path: str, crs: str) -> gpd.GeoDataFrame:
    buildings = buildings.copy()
    if "lu_desc" in buildings.columns:
        buildings["lu_desc_v10"] = buildings["lu_desc"]
        return buildings
    if "LU_DESC" in buildings.columns:
        buildings["lu_desc_v10"] = buildings["LU_DESC"]
        return buildings
    p = Path(land_use_path)
    if not p.exists():
        buildings["lu_desc_v10"] = "UNKNOWN"
        return buildings
    lu = gpd.read_file(p)
    if lu.crs is None:
        lu = lu.set_crs("EPSG:4326")
    lu = lu.to_crs(crs)
    desc_col = None
    for c in ["LU_DESC", "lu_desc", "LANDUSE", "land_use", "description"]:
        if c in lu.columns:
            desc_col = c
            break
    if desc_col is None:
        buildings["lu_desc_v10"] = "UNKNOWN"
        return buildings
    # Majority-by-area overlay; fallback to centroid join for missing.
    b = buildings[["building_id", "geometry"]].copy() if "building_id" in buildings.columns else buildings.reset_index()[["index", "geometry"]].rename(columns={"index": "building_id"})
    try:
        inter = gpd.overlay(b, lu[[desc_col, "geometry"]], how="intersection")
        inter["inter_area"] = inter.geometry.area
        best = inter.sort_values("inter_area").groupby("building_id").tail(1)[["building_id", desc_col]]
        buildings = buildings.merge(best.rename(columns={desc_col: "lu_desc_v10"}), on="building_id", how="left")
    except Exception as e:
        print(f"[WARN] land-use overlay failed: {e}. Falling back to centroid join.")
        cent = b.copy()
        cent["geometry"] = cent.geometry.centroid
        sj = gpd.sjoin(cent, lu[[desc_col, "geometry"]], predicate="within", how="left")
        buildings = buildings.merge(sj[["building_id", desc_col]].rename(columns={desc_col: "lu_desc_v10"}), on="building_id", how="left")
    buildings["lu_desc_v10"] = buildings["lu_desc_v10"].fillna("UNKNOWN")
    return buildings


def height_from_lu(lu_desc: Any, area_m2: float, type_text: str) -> Tuple[float, str, str, str]:
    text = f"{lu_desc} {type_text}".upper()
    if any(k in text for k in ["SHELTER", "ROOF", "COVERED", "CANOPY"]):
        return 4.0, "type_default_shelter", "medium_low", "possible_shelter_not_ground_up_building"
    for keyword, height, source in LU_DEFAULTS:
        if keyword in text:
            return height, source, "medium", ""
    if area_m2 < 50:
        return 5.0, "area_default:unknown_small", "low", ""
    if area_m2 > 1000:
        return 12.0, "area_default:unknown_large", "low", "manual_review_large_unknown_height"
    return 10.0, "area_default:unknown_normal", "low", ""


def assign_height(row: pd.Series) -> pd.Series:
    source_text = str(row.get("source_name", "")) + ";" + str(row.get("source_candidates", ""))
    source_text_low = source_text.lower()
    area = float(row.get("area_m2", row.geometry.area if row.geometry is not None else 0.0) or 0.0)

    # 1) HDB3D/source explicit height, high confidence.
    h_key, h_val = first_valid(row, HEIGHT_KEYS)
    h = parse_number(h_val)
    if h is not None and 2 <= h <= 180:
        if "hdb3d" in source_text_low or h_key in ["height_m_original", "height_m"]:
            row["height_m"] = h
            row["height_source"] = "height_m" if "hdb3d" in source_text_low else f"explicit:{h_key}"
            row["height_confidence"] = "high" if "hdb3d" in source_text_low else "medium_high"
            row["height_warning"] = ""
            return row

    # 2) explicit OSM height tag if present.
    if h is not None and 2 <= h <= 180:
        row["height_m"] = h
        row["height_source"] = f"osm_height_tag:{h_key}"
        row["height_confidence"] = "medium_high"
        row["height_warning"] = ""
        return row

    # 3) OSM levels.
    l_key, l_val = first_valid(row, LEVEL_KEYS)
    lev = parse_number(l_val)
    if lev is not None and 1 <= lev <= 60:
        row["height_m"] = float(lev) * 3.0
        row["height_source"] = f"osm_levels_x_3m:{l_key}"
        row["height_confidence"] = "medium_high"
        row["height_warning"] = ""
        return row

    # 4) land-use / type / area defaults.
    type_text = " ".join(str(row.get(k, "")) for k in TYPE_KEYS if k in row.index)
    lu_desc = row.get("lu_desc_v10", "UNKNOWN")
    height, src, conf, warn = height_from_lu(lu_desc, area, type_text)
    row["height_m"] = height
    row["height_source"] = src
    row["height_confidence"] = conf
    row["height_warning"] = warn
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_alpha_augmented_dsm_config.example.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    paths = cfg["paths"]
    crs = cfg.get("crs", "EPSG:3414")

    in_fp = Path(paths["canonical_buildings"])
    if not in_fp.exists():
        raise FileNotFoundError(f"Canonical file not found: {in_fp}")
    b = gpd.read_file(in_fp)
    if b.crs is None:
        b = b.set_crs(crs)
    else:
        b = b.to_crs(crs)
    b = b[b.geometry.notna() & (~b.geometry.is_empty)].copy()
    b["area_m2"] = b.geometry.area
    if "building_id" not in b.columns:
        b["building_id"] = [f"v10_bldg_{i:06d}" for i in range(len(b))]

    b = infer_lu_desc(b, paths.get("land_use", ""), crs)
    # Apply row-wise height assignment.
    b = b.apply(assign_height, axis=1)
    b = gpd.GeoDataFrame(b, geometry="geometry", crs=crs)
    b["height_m"] = pd.to_numeric(b["height_m"], errors="coerce")
    b["height_m"] = b["height_m"].clip(lower=3.0, upper=180.0)

    out_fp = Path(paths["canonical_buildings_height"])
    qa_csv = Path(paths["height_qa_csv"])
    report_fp = Path(paths["height_report"])
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    qa_csv.parent.mkdir(parents=True, exist_ok=True)
    report_fp.parent.mkdir(parents=True, exist_ok=True)
    b.to_file(out_fp, driver="GeoJSON")

    qa_cols = ["building_id", "source_name", "area_m2", "height_m", "height_source", "height_confidence", "height_warning", "lu_desc_v10"]
    qa_cols = [c for c in qa_cols if c in b.columns]
    b[qa_cols].to_csv(qa_csv, index=False)

    height_source_counts = b["height_source"].value_counts(dropna=False).rename_axis("height_source").reset_index(name="n")
    height_conf_counts = b["height_confidence"].value_counts(dropna=False).rename_axis("height_confidence").reset_index(name="n")
    large_low = b[(b["area_m2"] > 1000) & (b["height_confidence"].isin(["low", "medium_low"]))].copy()
    large_low_cols = ["building_id", "source_name", "area_m2", "height_m", "height_source", "lu_desc_v10", "height_warning"]
    large_low_cols = [c for c in large_low_cols if c in large_low.columns]

    report = []
    report.append("# v1.0-alpha.1 height imputation QA")
    report.append("")
    report.append(f"Buildings: **{len(b)}**")
    report.append(f"Null heights: **{int(b['height_m'].isna().sum())}**")
    report.append("")
    report.append("## Height source counts")
    report.append("```text")
    report.append(height_source_counts.to_string(index=False))
    report.append("```")
    report.append("")
    report.append("## Height confidence counts")
    report.append("```text")
    report.append(height_conf_counts.to_string(index=False))
    report.append("```")
    report.append("")
    report.append("## Height statistics")
    report.append("```text")
    report.append(b["height_m"].describe().to_string())
    report.append("```")
    report.append("")
    report.append("## Large low-confidence buildings")
    report.append("```text")
    report.append(large_low[large_low_cols].head(30).to_string(index=False) if len(large_low) else "None")
    report.append("```")
    report.append("")
    report.append("## Notes")
    report.append("- Duplicate OSM height / level tags promoted during deduplication can now be used here.")
    report.append("- Large low-confidence buildings should be manually inspected before UMEP/SOLWEIG reruns.")
    report_fp.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] height buildings: {out_fp}")
    print(f"[OK] QA csv: {qa_csv}")
    print(f"[OK] report: {report_fp}")


if __name__ == "__main__":
    main()
