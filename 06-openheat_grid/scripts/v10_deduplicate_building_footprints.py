"""
OpenHeat v1.0-alpha.1 hotfix
Conservative canonical building-footprint deduplication with height/level promotion.

Inputs (default):
  data/features_3d/v10/canonical_candidates/all_building_candidates_v10.geojson
Outputs:
  data/features_3d/v10/canonical/canonical_buildings_v10.geojson
  data/features_3d/v10/canonical/canonical_buildings_v10_conflicts.geojson
  outputs/v10_dsm_audit/v10_dedup_QA_report.md
  outputs/v10_dsm_audit/v10_dedup_status_counts.csv
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry.base import BaseGeometry

DEFAULT_CONFIG = {
    "crs": "EPSG:3414",
    "dedup": {
        "min_area_m2": 10.0,
        "min_area_ml_source_m2": 20.0,
        "iou_duplicate_threshold": 0.35,
        "candidate_overlap_duplicate_threshold": 0.60,
        "existing_overlap_duplicate_threshold": 0.30,
        "candidate_overlap_new_threshold": 0.20,
        "centroid_duplicate_distance_m": 8.0,
        "area_ratio_min": 0.5,
        "area_ratio_max": 2.0
    },
    "paths": {
        "all_candidates": "data/features_3d/v10/canonical_candidates/all_building_candidates_v10.geojson",
        "canonical_buildings": "data/features_3d/v10/canonical/canonical_buildings_v10.geojson",
        "canonical_conflicts": "data/features_3d/v10/canonical/canonical_buildings_v10_conflicts.geojson",
        "dedup_report": "outputs/v10_dsm_audit/v10_dedup_QA_report.md",
        "dedup_status_counts": "outputs/v10_dsm_audit/v10_dedup_status_counts.csv"
    },
    "source_priority": {
        "hdb3d": 1,
        "ura": 2,
        "osm": 3,
        "microsoft": 4,
        "google": 5,
        "google_open_buildings": 5,
        "unknown": 9
    }
}

HEIGHT_KEYS = [
    "height_m_original", "height_m", "height", "building:height", "building_height",
    "osm_height_m", "HEIGHT", "Height"
]
LEVEL_KEYS = [
    "levels_original", "building:levels", "building_levels", "osm_levels", "levels", "Levels"
]
TYPE_KEYS = [
    "building_type_original", "building", "building_tag", "osm_building", "type", "class"
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


def safe_float(x: Any) -> Optional[float]:
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
        s = str(x).strip().lower().replace("metres", "").replace("meters", "").replace("meter", "").replace("m", "").strip()
        try:
            val = float(s)
        except Exception:
            return None
    if not math.isfinite(val):
        return None
    return val


def get_first_valid(row: Dict[str, Any], keys: Iterable[str]) -> Tuple[Optional[str], Optional[Any]]:
    for key in keys:
        if key in row:
            v = row.get(key)
            try:
                if pd.isna(v):
                    continue
            except Exception:
                pass
            if v is not None and str(v).strip() not in ["", "nan", "None"]:
                return key, v
    return None, None


def promote_height_fields(canon: Dict[str, Any], cand: Dict[str, Any]) -> Dict[str, Any]:
    """Promote useful height/level/type info from a duplicate candidate.

    This fixes the v10-alpha issue where an OSM candidate with building:levels
    could be merged into an earlier URA/HDB canonical footprint but its height
    tags were only recorded in provenance, then lost before height assignment.
    """
    promoted = []
    for key_group, suffix in [(HEIGHT_KEYS, "height"), (LEVEL_KEYS, "levels"), (TYPE_KEYS, "type")]:
        c_key, c_val = get_first_valid(canon, key_group)
        cand_key, cand_val = get_first_valid(cand, key_group)
        if cand_key is not None and c_key is None:
            target_key = cand_key
            canon[target_key] = cand_val
            canon[f"{suffix}_promoted_from_source"] = cand.get("source_name", "unknown")
            canon[f"{suffix}_promoted_from_id"] = cand.get("source_building_id", "")
            promoted.append(f"{suffix}:{cand_key}")
    if promoted:
        prev = str(canon.get("promoted_fields", "") or "")
        canon["promoted_fields"] = ";".join([x for x in [prev, ",".join(promoted)] if x])
    return canon


def clean_geometries(gdf: gpd.GeoDataFrame, crs: str) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        print(f"[WARN] Input candidates have no CRS. Assuming {crs}.")
        gdf = gdf.set_crs(crs)
    else:
        gdf = gdf.to_crs(crs)
    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()
    try:
        gdf["geometry"] = gdf.geometry.make_valid()
    except Exception:
        gdf["geometry"] = gdf.geometry.buffer(0)
    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()
    gdf["area_m2"] = gdf.geometry.area
    return gdf


def source_priority(name: Any, cfg: Dict[str, Any]) -> int:
    s = str(name).lower().strip() if name is not None else "unknown"
    pr = cfg.get("source_priority", {})
    if s in pr:
        return int(pr[s])
    for k, v in pr.items():
        if k in s:
            return int(v)
    return 9


def match_candidate(cand_geom: BaseGeometry, canon_gdf: gpd.GeoDataFrame, dedup: Dict[str, Any]) -> Tuple[Optional[int], str, Dict[str, float]]:
    if canon_gdf.empty:
        return None, "accepted_new", {}
    possible_idx = list(canon_gdf.sindex.query(cand_geom, predicate="intersects"))
    if not possible_idx:
        return None, "accepted_new", {"best_iou": 0.0, "best_candidate_overlap": 0.0, "best_existing_overlap": 0.0}

    cand_area = cand_geom.area
    best = {"idx": None, "iou": 0.0, "candidate_overlap": 0.0, "existing_overlap": 0.0, "area_ratio": np.nan, "centroid_distance": np.inf}
    cand_cent = cand_geom.centroid
    for idx in possible_idx:
        ex_geom = canon_gdf.iloc[idx].geometry
        if ex_geom is None or ex_geom.is_empty:
            continue
        inter = cand_geom.intersection(ex_geom).area
        if inter <= 0:
            continue
        ex_area = ex_geom.area
        union = cand_area + ex_area - inter
        iou = inter / union if union > 0 else 0.0
        co = inter / cand_area if cand_area > 0 else 0.0
        eo = inter / ex_area if ex_area > 0 else 0.0
        ar = cand_area / ex_area if ex_area > 0 else np.inf
        cd = cand_cent.distance(ex_geom.centroid)
        score = (iou, co, eo, -cd)
        best_score = (best["iou"], best["candidate_overlap"], best["existing_overlap"], -best["centroid_distance"])
        if score > best_score:
            best.update({"idx": idx, "iou": iou, "candidate_overlap": co, "existing_overlap": eo, "area_ratio": ar, "centroid_distance": cd})

    if best["idx"] is None:
        return None, "accepted_new", {"best_iou": 0.0, "best_candidate_overlap": 0.0, "best_existing_overlap": 0.0}

    duplicate = (
        best["iou"] >= dedup["iou_duplicate_threshold"]
        or (best["candidate_overlap"] >= dedup["candidate_overlap_duplicate_threshold"] and best["existing_overlap"] >= dedup["existing_overlap_duplicate_threshold"])
        or (best["centroid_distance"] <= dedup["centroid_duplicate_distance_m"] and dedup["area_ratio_min"] <= best["area_ratio"] <= dedup["area_ratio_max"])
    )
    if duplicate:
        return int(best["idx"]), "merged_duplicate", best

    if best["candidate_overlap"] < dedup["candidate_overlap_new_threshold"]:
        return None, "accepted_new", best

    return int(best["idx"]), "conflict_review", best



def resolve_min_area(dedup: Dict[str, Any], row: Dict[str, Any]) -> float:
    """Resolve minimum footprint area threshold for a candidate row.

    Supports both legacy numeric config:
        "min_area_m2": 10

    and source-specific config:
        "min_area_m2": {"default": 10, "osm": 10, "microsoft": 20, "google": 20}

    ML-derived sources may also use:
        "min_area_ml_source_m2": 20
    or a source-specific dict.
    """
    source = str(row.get("source_name", "unknown") or "unknown").lower()
    is_ml_source = bool(row.get("is_ml_source", False))

    def _coerce_float(value: Any, fallback: float) -> float:
        try:
            if value is None:
                return float(fallback)
            return float(value)
        except (TypeError, ValueError):
            return float(fallback)

    def _from_cfg(cfg: Any, fallback: float) -> float:
        if isinstance(cfg, dict):
            # Try exact source first, then common aliases, then default.
            for key in (source, source.replace("_", ""), "default"):
                if key in cfg:
                    return _coerce_float(cfg.get(key), fallback)
            return float(fallback)
        return _coerce_float(cfg, fallback)

    base_cfg = dedup.get("min_area_m2", 10.0)
    base = _from_cfg(base_cfg, 10.0)

    if is_ml_source and "min_area_ml_source_m2" in dedup:
        return _from_cfg(dedup.get("min_area_ml_source_m2"), base)

    return base

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_alpha_augmented_dsm_config.example.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    paths = cfg["paths"]
    crs = cfg.get("crs", "EPSG:3414")
    dedup = {**DEFAULT_CONFIG["dedup"], **cfg.get("dedup", {})}

    in_fp = Path(paths["all_candidates"])
    if not in_fp.exists():
        raise FileNotFoundError(f"Candidate file not found: {in_fp}")
    candidates = gpd.read_file(in_fp)
    candidates = clean_geometries(candidates, crs)

    # Ensure expected columns exist.
    if "source_name" not in candidates.columns:
        candidates["source_name"] = "unknown"
    if "source_building_id" not in candidates.columns:
        candidates["source_building_id"] = [f"src_{i:06d}" for i in range(len(candidates))]
    candidates["source_priority"] = candidates["source_name"].apply(lambda x: source_priority(x, cfg))
    candidates["is_ml_source"] = candidates["source_name"].str.lower().str.contains("microsoft|google", regex=True, na=False)

    # Sort official/high-confidence sources first, then larger geometries first.
    candidates = candidates.sort_values(["source_priority", "area_m2"], ascending=[True, False]).reset_index(drop=True)

    canonical_rows: List[Dict[str, Any]] = []
    conflict_rows: List[Dict[str, Any]] = []
    status_counts: Dict[str, int] = {}

    for i, rec in candidates.iterrows():
        row = rec.drop(labels="geometry").to_dict()
        geom = rec.geometry
        min_area = resolve_min_area(dedup, row)
        if geom.area < min_area:
            status_counts["rejected_tiny"] = status_counts.get("rejected_tiny", 0) + 1
            continue

        canon_gdf = gpd.GeoDataFrame(canonical_rows, geometry="geometry", crs=crs) if canonical_rows else gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=crs)
        match_idx, status, metrics = match_candidate(geom, canon_gdf, dedup)
        status_counts[status] = status_counts.get(status, 0) + 1

        if status == "accepted_new":
            row["geometry"] = geom
            row["dedup_status"] = "accepted_new"
            row["source_candidates"] = str(row.get("source_name", "unknown"))
            row["source_candidate_ids"] = str(row.get("source_building_id", f"candidate_{i}"))
            row["n_source_candidates"] = 1
            row["best_iou"] = metrics.get("iou", metrics.get("best_iou", 0.0))
            canonical_rows.append(row)
        elif status == "merged_duplicate" and match_idx is not None:
            canon = canonical_rows[match_idx]
            canon["source_candidates"] = f"{canon.get('source_candidates','')};{row.get('source_name','unknown')}".strip(";")
            canon["source_candidate_ids"] = f"{canon.get('source_candidate_ids','')};{row.get('source_building_id', f'candidate_{i}')}".strip(";")
            canon["n_source_candidates"] = int(canon.get("n_source_candidates", 1) or 1) + 1
            canon["best_iou"] = max(float(canon.get("best_iou", 0.0) or 0.0), float(metrics.get("iou", 0.0) or 0.0))
            canonical_rows[match_idx] = promote_height_fields(canon, row)
        elif status == "conflict_review":
            row["geometry"] = geom
            row["dedup_status"] = "conflict_review"
            row["matched_canonical_idx"] = match_idx
            for k, v in metrics.items():
                row[f"match_{k}"] = v
            conflict_rows.append(row)

    canonical = gpd.GeoDataFrame(canonical_rows, geometry="geometry", crs=crs)
    canonical = canonical.reset_index(drop=True)
    canonical["building_id"] = [f"v10_bldg_{i:06d}" for i in range(len(canonical))]
    # Put building_id first.
    cols = ["building_id"] + [c for c in canonical.columns if c != "building_id"]
    canonical = canonical[cols]

    conflicts = gpd.GeoDataFrame(conflict_rows, geometry="geometry", crs=crs) if conflict_rows else gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=crs)

    out_fp = Path(paths["canonical_buildings"])
    conflict_fp = Path(paths["canonical_conflicts"])
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    conflict_fp.parent.mkdir(parents=True, exist_ok=True)
    canonical.to_file(out_fp, driver="GeoJSON")
    conflicts.to_file(conflict_fp, driver="GeoJSON")

    status_df = pd.DataFrame([{"dedup_status": k, "n": v} for k, v in sorted(status_counts.items())])
    status_counts_fp = Path(paths["dedup_status_counts"])
    status_counts_fp.parent.mkdir(parents=True, exist_ok=True)
    status_df.to_csv(status_counts_fp, index=False)

    geom_counts = canonical["source_name"].value_counts(dropna=False).rename_axis("geometry_source").reset_index(name="n") if "source_name" in canonical.columns else pd.DataFrame()
    promoted_n = int(canonical.get("promoted_fields", pd.Series(dtype=str)).fillna("").astype(str).str.len().gt(0).sum()) if "promoted_fields" in canonical.columns else 0

    report = []
    report.append("# v1.0-alpha.1 footprint deduplication QA")
    report.append("")
    report.append(f"Input candidates: **{len(candidates)}**")
    report.append(f"Canonical buildings: **{len(canonical)}**")
    report.append(f"Conflict review candidates: **{len(conflicts)}**")
    report.append(f"Canonical buildings with promoted height/level/type fields: **{promoted_n}**")
    report.append("")
    report.append("## Dedup status counts")
    report.append("```text")
    report.append(status_df.to_string(index=False))
    report.append("```")
    report.append("")
    if not geom_counts.empty:
        report.append("## Canonical geometry source counts")
        report.append("```text")
        report.append(geom_counts.to_string(index=False))
        report.append("```")
        report.append("")
    report.append("## Hotfix notes")
    report.append("- Duplicate candidates now promote useful OSM height / level / building-type fields into canonical records when the existing canonical record lacks them.")
    report.append("- Conflict-review candidates are still excluded from canonical output to avoid double-counting.")
    report.append("- This implementation is conservative and prioritizes provenance clarity over maximal footprint union.")

    report_fp = Path(paths["dedup_report"])
    report_fp.parent.mkdir(parents=True, exist_ok=True)
    report_fp.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] canonical: {out_fp}")
    print(f"[OK] conflicts: {conflict_fp}")
    print(f"[OK] report: {report_fp}")


if __name__ == "__main__":
    main()
