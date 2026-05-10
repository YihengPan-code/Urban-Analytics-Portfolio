#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenHeat v1.0-alpha.3: apply manual QA decisions to canonical buildings.

This script is intentionally conservative. It does not overwrite v10-alpha.1 outputs.
It creates a reviewed canonical building layer, an overhead-candidates layer, and an
applied-decisions log.
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
from shapely.geometry import Polygon, MultiPolygon
try:
    from shapely.validation import make_valid
except Exception:  # pragma: no cover
    make_valid = None


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def is_missing(x: Any) -> bool:
    if x is None:
        return True
    try:
        return bool(pd.isna(x))
    except Exception:
        return False


def clean_str(x: Any) -> str:
    if is_missing(x):
        return ""
    return str(x).strip()


def to_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    if is_missing(x):
        return default
    if isinstance(x, str):
        s = x.strip().lower().replace("m", "").replace(",", "")
        if s in {"", "nan", "none", "null"}:
            return default
        try:
            return float(s)
        except Exception:
            return default
    try:
        return float(x)
    except Exception:
        return default


def normalize_confidence(x: Any, default: str = "medium_low") -> str:
    s = clean_str(x).lower().replace("-", "_")
    if s in {"", "none", "nan", "null", "mediem_low"}:
        return default
    if s in {"high", "medium_high", "medium", "medium_low", "low"}:
        return s
    if "medium" in s and "low" in s:
        return "medium_low"
    return default


def normalize_building_type(x: Any) -> str:
    s = clean_str(x).lower().replace(" ", "_")
    if s in {"", "none", "nan", "null"}:
        return "manual_unknown"
    if s in {"school_building", "school"}:
        return "school"
    if s in {"building", "unknown_normal"}:
        return "unknown_normal"
    return s


def fix_geometry(g):
    if g is None or g.is_empty:
        return None
    if g.is_valid:
        return g
    if make_valid is not None:
        try:
            g2 = make_valid(g)
            if g2 is not None and not g2.is_empty:
                return g2
        except Exception:
            pass
    try:
        return g.buffer(0)
    except Exception:
        return g


def read_gdf(path: Path, crs: str) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(crs)
    else:
        gdf = gdf.to_crs(crs)
    gdf["geometry"] = gdf.geometry.apply(fix_geometry)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    return gdf


def load_manual_review(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Normalise common column names from different templates.
    colmap = {}
    for c in df.columns:
        lc = c.lower().strip()
        if lc in {"building_id", "target_id", "source_building_id", "id"} and "target_id" not in colmap.values():
            colmap[c] = "target_id"
        elif lc in {"target_type", "qa_target_type", "type"}:
            colmap[c] = "target_type"
        elif lc in {"manual_decision", "decision"}:
            colmap[c] = "manual_decision"
        elif lc in {"manual_height_m", "height_m_manual", "new_height_m"}:
            colmap[c] = "manual_height_m"
        elif lc in {"manual_notes", "notes"}:
            colmap[c] = "manual_notes"
        elif lc in {"review_status", "status"}:
            colmap[c] = "review_status"
    df = df.rename(columns=colmap)
    if "manual_decision" not in df.columns:
        return pd.DataFrame()
    if "target_id" not in df.columns:
        return pd.DataFrame()
    if "target_type" not in df.columns:
        df["target_type"] = "building"
    if "manual_height_m" not in df.columns:
        df["manual_height_m"] = np.nan
    if "manual_notes" not in df.columns:
        df["manual_notes"] = ""
    df["manual_decision"] = df["manual_decision"].astype(str).str.strip()
    df = df[df["manual_decision"].ne("") & df["manual_decision"].ne("nan")].copy()
    return df


def infer_height_from_row(row: pd.Series) -> Tuple[float, str, str, str]:
    """Return height_m, height_source, confidence, warning for conflict/manual row."""
    mh = to_float(row.get("manual_height_m"), None)
    if mh and 2 <= mh <= 180:
        return mh, "manual_height", "medium", "manual_review_height"

    explicit = to_float(row.get("height_m_original"), None)
    if explicit and explicit > 0 and explicit <= 180:
        return explicit, "conflict_explicit_height", "medium_high", ""

    for key in ["levels_original", "building_levels", "levels"]:
        lv = to_float(row.get(key), None)
        if lv and lv > 0 and lv <= 60:
            return lv * 3.0, f"conflict_{key}_x_3m", "medium_high", ""

    btype = normalize_building_type(row.get("building_type_original", row.get("building_type", "")))
    lu = clean_str(row.get("lu_desc_v10", row.get("lu_desc", ""))).upper()
    area = to_float(row.get("area_m2"), 0) or 0
    if "SCHOOL" in lu or btype == "school":
        return 12.0, "manual_default_school_12m", "medium_low", "manual_default_height"
    if "OFFICE" in lu or btype == "office":
        return 18.0, "manual_default_office_18m", "medium_low", "manual_default_height"
    if "PARKING" in btype or "CARPARK" in lu:
        return 9.0, "manual_default_parking_9m", "medium_low", "manual_default_height"
    if "RESIDENTIAL" in lu or btype == "residential":
        return 12.0, "manual_default_residential_12m", "medium_low", "manual_default_height"
    if "BUSINESS" in lu or "COMMERCIAL" in lu:
        return 12.0 if area < 3000 else 15.0, "manual_default_business_area", "medium_low", "manual_default_height"
    if area > 1000:
        return 12.0, "manual_default_unknown_large_12m", "low", "manual_review_large_unknown_height"
    return 10.0, "manual_default_unknown_10m", "low", "manual_default_height"


def add_common_fields(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if "area_m2" not in gdf.columns:
        gdf["area_m2"] = gdf.geometry.area
    for col, default in {
        "source_name": "manual",
        "geometry_source": "manual",
        "source_candidates": "manual",
        "source_candidate_ids": "manual",
        "n_source_candidates": 1,
        "height_warning": "",
    }.items():
        if col not in gdf.columns:
            gdf[col] = default
    return gdf


def make_manual_missing_layer(path: Path, crs: str, start_index: int) -> gpd.GeoDataFrame:
    if not path.exists():
        return gpd.GeoDataFrame(columns=["building_id", "geometry"], geometry="geometry", crs=crs)
    gdf = read_gdf(path, crs)
    rows = []
    for i, row in gdf.reset_index(drop=True).iterrows():
        h = to_float(row.get("manual_height_m"), None)
        if not h or h <= 0:
            h = 10.0
        conf = normalize_confidence(row.get("height_confidence"), default="medium_low")
        btype = normalize_building_type(row.get("building_type"))
        manual_id = row.get("manual_id")
        if is_missing(manual_id):
            bid = f"v10_manual_missing_{start_index + i:04d}"
        else:
            try:
                bid = f"v10_manual_missing_{int(float(manual_id)):04d}"
            except Exception:
                bid = f"v10_manual_missing_{start_index + i:04d}"
        rows.append({
            "building_id": bid,
            "source_name": "manual_missing",
            "geometry_source": "manual_missing",
            "source_building_id": clean_str(row.get("manual_id")) or bid,
            "source_candidates": "manual_missing",
            "source_candidate_ids": bid,
            "n_source_candidates": 1,
            "building_type_original": btype,
            "building_type_v10": btype,
            "height_m": float(h),
            "height_source": "manual_missing_height",
            "height_confidence": conf,
            "height_warning": "manual_digitised_missing_building",
            "area_m2": row.geometry.area,
            "manual_notes": clean_str(row.get("manual_notes")),
            "source_note": clean_str(row.get("source_note")) or "satellite_manual_digitised",
            "geometry": row.geometry,
        })
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)


def build_conflict_gdf_for_merge(conflicts: gpd.GeoDataFrame, rows_to_merge: pd.DataFrame, crs: str, start_index: int) -> gpd.GeoDataFrame:
    if conflicts.empty or rows_to_merge.empty:
        return gpd.GeoDataFrame(columns=["building_id", "geometry"], geometry="geometry", crs=crs)

    out_rows = []
    # Prepare lookup by source_building_id and by source_name/source_building_id.
    conflicts = conflicts.copy()
    if "source_building_id" not in conflicts.columns:
        raise KeyError("canonical_conflicts_geojson must contain source_building_id")
    for idx, r in rows_to_merge.reset_index(drop=True).iterrows():
        tid = clean_str(r.get("target_id", r.get("source_building_id", "")))
        sub = conflicts[conflicts["source_building_id"].astype(str).eq(tid)]
        if sub.empty and "source_building_id" in r:
            sub = conflicts[conflicts["source_building_id"].astype(str).eq(clean_str(r["source_building_id"]))]
        if sub.empty:
            continue
        c = sub.iloc[0].copy()
        h, hs, hc, hw = infer_height_from_row(pd.concat([c, r], axis=0))
        bid = f"v10_manual_conflict_{start_index + idx:04d}"
        rec = c.to_dict()
        rec.update({
            "building_id": bid,
            "geometry_source": rec.get("source_name", "conflict"),
            "source_candidates": rec.get("source_name", "conflict"),
            "source_candidate_ids": rec.get("source_building_id", tid),
            "n_source_candidates": 1,
            "height_m": h,
            "height_source": hs,
            "height_confidence": hc,
            "height_warning": hw,
            "manual_decision": "merge_conflict",
            "manual_notes": clean_str(r.get("manual_notes")) or "merged from alpha2 conflict review",
            "area_m2": c.geometry.area,
        })
        out_rows.append(rec)
    if not out_rows:
        return gpd.GeoDataFrame(columns=["building_id", "geometry"], geometry="geometry", crs=crs)
    return gpd.GeoDataFrame(out_rows, geometry="geometry", crs=crs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_alpha3_manual_qa_config.example.json")
    args = ap.parse_args()
    cfg = read_json(Path(args.config))
    crs = cfg.get("crs", "EPSG:3414")
    inp = cfg["inputs"]
    out = cfg["outputs"]
    defaults = cfg.get("manual_defaults", {})

    canonical_path = Path(inp["canonical_height_geojson"])
    conflicts_path = Path(inp["canonical_conflicts_geojson"])
    manual_review_path = Path(inp.get("manual_review_csv", ""))
    manual_missing_path = Path(inp.get("manual_missing_buildings_geojson", ""))
    alpha2_conflict_targets_path = Path(inp.get("alpha2_conflict_targets_csv", ""))

    canonical = read_gdf(canonical_path, crs)
    canonical = add_common_fields(canonical)
    conflicts = read_gdf(conflicts_path, crs) if conflicts_path.exists() else gpd.GeoDataFrame(geometry=[], crs=crs)
    review = load_manual_review(manual_review_path)

    applied = []
    overhead_layers = []

    # Built-in default: move known station canopy / overhead building out of building DSM.
    remove_ids = set(str(x) for x in defaults.get("move_to_overhead_building_ids", []))

    # Explicit manual decisions from CSV.
    if not review.empty:
        for _, r in review.iterrows():
            target_id = clean_str(r.get("target_id"))
            dec = clean_str(r.get("manual_decision")).lower()
            ttype = clean_str(r.get("target_type", "building")).lower()
            if not target_id or not dec:
                continue
            if ttype.startswith("building"):
                if dec in {"move_to_overhead_dsm", "remove"}:
                    if target_id in set(canonical["building_id"].astype(str)):
                        if dec == "move_to_overhead_dsm":
                            overhead_layers.append(canonical[canonical["building_id"].astype(str).eq(target_id)].copy())
                        remove_ids.add(target_id)
                        applied.append({"target_type": "building", "target_id": target_id, "manual_decision": dec, "status": "queued"})
                elif dec in {"height_adjust", "keep_building_dsm", "no_action"}:
                    mask = canonical["building_id"].astype(str).eq(target_id)
                    if mask.any():
                        if dec == "height_adjust":
                            mh = to_float(r.get("manual_height_m"), None)
                            if mh and 2 <= mh <= 180:
                                canonical.loc[mask, "height_m"] = mh
                                canonical.loc[mask, "height_source"] = "manual_height_adjust"
                                canonical.loc[mask, "height_confidence"] = "medium"
                        canonical.loc[mask, "manual_decision"] = dec
                        canonical.loc[mask, "manual_notes"] = clean_str(r.get("manual_notes"))
                        applied.append({"target_type": "building", "target_id": target_id, "manual_decision": dec, "status": "applied"})
            elif ttype.startswith("conflict"):
                # handled below by building conflict merge table
                pass

    # Remove/move overhead/remove building IDs from canonical.
    if remove_ids:
        overhead_default = canonical[canonical["building_id"].astype(str).isin(remove_ids)].copy()
        if not overhead_default.empty:
            overhead_default["manual_decision"] = "move_to_overhead_dsm"
            if "manual_notes" not in overhead_default.columns:
                overhead_default["manual_notes"] = ""
            overhead_default["manual_notes"] = overhead_default["manual_notes"].fillna("").astype(str)
            overhead_layers.append(overhead_default)
        canonical = canonical[~canonical["building_id"].astype(str).isin(remove_ids)].copy()
        for bid in sorted(remove_ids):
            applied.append({"target_type": "building", "target_id": bid, "manual_decision": "move_to_overhead_dsm_or_remove", "status": "applied"})

    # Conflict merges: explicit manual conflicts OR top-N default conflict targets.
    conflict_merge_rows = pd.DataFrame()
    if not review.empty:
        tmp = review[review.get("target_type", "").astype(str).str.lower().str.startswith("conflict") & review["manual_decision"].astype(str).str.lower().eq("merge_conflict")].copy()
        if not tmp.empty:
            conflict_merge_rows = tmp
    if conflict_merge_rows.empty and defaults.get("apply_default_conflict_merge_if_no_manual_review", True):
        n = int(defaults.get("merge_top_conflicts_n", 0) or 0)
        if n > 0 and alpha2_conflict_targets_path.exists():
            ctargets = pd.read_csv(alpha2_conflict_targets_path)
            if "qa_priority_score" in ctargets.columns:
                ctargets = ctargets.sort_values("qa_priority_score", ascending=False)
            ctargets = ctargets.head(n).copy()
            ctargets["target_id"] = ctargets.get("source_building_id", ctargets.index.astype(str))
            ctargets["target_type"] = "conflict"
            ctargets["manual_decision"] = "merge_conflict"
            ctargets["manual_notes"] = "auto-merge top conflict target after user manual check"
            conflict_merge_rows = ctargets

    conflict_gdf = build_conflict_gdf_for_merge(conflicts, conflict_merge_rows, crs, start_index=len(canonical) + 1)
    if not conflict_gdf.empty:
        canonical = pd.concat([canonical, conflict_gdf], ignore_index=True, sort=False)
        for _, r in conflict_gdf.iterrows():
            applied.append({"target_type": "conflict", "target_id": r.get("source_building_id", r.get("building_id")), "manual_decision": "merge_conflict", "status": "applied"})

    # Manual missing buildings.
    manual_missing = make_manual_missing_layer(manual_missing_path, crs, start_index=len(canonical) + 1)
    if not manual_missing.empty:
        canonical = pd.concat([canonical, manual_missing], ignore_index=True, sort=False)
        for _, r in manual_missing.iterrows():
            applied.append({"target_type": "manual_missing", "target_id": r.get("building_id"), "manual_decision": "append_manual_missing_building", "status": "applied"})

    canonical = gpd.GeoDataFrame(canonical, geometry="geometry", crs=crs)
    canonical["geometry"] = canonical.geometry.apply(fix_geometry)
    canonical = canonical[canonical.geometry.notna() & ~canonical.geometry.is_empty].copy()
    canonical["area_m2"] = canonical.geometry.area
    canonical["height_m"] = pd.to_numeric(canonical["height_m"], errors="coerce").fillna(10.0)
    canonical["height_m"] = canonical["height_m"].clip(lower=3.0, upper=180.0)

    reviewed_path = Path(out["reviewed_canonical_geojson"])
    ensure_parent(reviewed_path)
    canonical.to_file(reviewed_path, driver="GeoJSON")

    if overhead_layers:
        overhead = gpd.GeoDataFrame(pd.concat(overhead_layers, ignore_index=True, sort=False), geometry="geometry", crs=crs)
        overhead = overhead[overhead.geometry.notna() & ~overhead.geometry.is_empty].copy()
    else:
        overhead = gpd.GeoDataFrame(columns=canonical.columns, geometry="geometry", crs=crs)
    overhead_path = Path(out["overhead_candidates_geojson"])
    ensure_parent(overhead_path)
    overhead.to_file(overhead_path, driver="GeoJSON")

    applied_df = pd.DataFrame(applied).drop_duplicates()
    applied_path = Path(out["applied_decisions_csv"])
    ensure_parent(applied_path)
    applied_df.to_csv(applied_path, index=False)

    report_path = Path(out["manual_qa_report_md"])
    ensure_parent(report_path)
    lines = []
    lines.append("# v1.0-alpha.3 manual QA application report")
    lines.append("")
    lines.append(f"Reviewed canonical buildings: **{len(canonical)}**")
    lines.append(f"Overhead candidates: **{len(overhead)}**")
    lines.append(f"Applied decisions: **{len(applied_df)}**")
    lines.append(f"Manual missing buildings appended: **{len(manual_missing)}**")
    lines.append(f"Conflict candidates merged: **{len(conflict_gdf)}**")
    lines.append("")
    lines.append("## Height source counts")
    lines.append("```text")
    lines.append(canonical["height_source"].value_counts(dropna=False).to_string())
    lines.append("```")
    lines.append("")
    lines.append("## Height confidence counts")
    lines.append("```text")
    lines.append(canonical["height_confidence"].value_counts(dropna=False).to_string())
    lines.append("```")
    lines.append("")
    lines.append("## Notes")
    lines.append("- `v10_bldg_000690` is moved to overhead candidates by default.")
    lines.append("- Top conflict targets can be merged automatically only because the user manually confirmed they are real buildings.")
    lines.append("- Manual missing buildings are appended as medium/low-confidence manual-digitised buildings.")
    lines.append("- This reviewed layer is the recommended input for v10-beta basic morphology recomputation.")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"[OK] reviewed canonical: {reviewed_path}")
    print(f"[OK] overhead candidates: {overhead_path}")
    print(f"[OK] applied decisions: {applied_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
