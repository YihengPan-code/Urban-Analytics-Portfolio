#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenHeat v1.0-beta.1: targeted height / geometry correction.

Purpose
-------
Apply manual pre-UMEP height/geometry corrections before v10-gamma UMEP rerun.

Default correction logic:
  - v10_bldg_000001: keep footprint but set height to 30m.
  - v10_bldg_000002: remove original block-complex footprint and replace it with
    manually digitised split polygons in manual_split_buildings_v10.geojson.

This script is deliberately conservative:
  - It does not overwrite the reviewed v10-alpha.3 canonical layer.
  - It writes a new height-QA canonical layer.
  - It preserves provenance fields where possible.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry.base import BaseGeometry


DEFAULT_CONFIG = Path("configs/v10/v10_beta1_height_geometry_config.example.json")
TARGET_CRS = "EPSG:3414"


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def clean_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def to_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    if x is None:
        return default
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return default
    # handle values like "30 m"
    s = s.replace("m", "").replace("M", "").strip()
    try:
        return float(s)
    except Exception:
        return default


def boolish_contains(series: pd.Series, patterns: List[str]) -> pd.Series:
    text = series.fillna("").astype(str).str.lower()
    out = pd.Series(False, index=series.index)
    for p in patterns:
        out |= text.str.contains(p.lower(), regex=False)
    return out


def make_valid_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    try:
        # Shapely 2 / GeoPandas make_valid when available
        gdf["geometry"] = gdf.geometry.make_valid()
    except Exception:
        gdf["geometry"] = gdf.geometry.buffer(0)
    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()
    return gdf


def load_corrections(cfg: Dict[str, Any]) -> pd.DataFrame:
    corr_path = Path(cfg["inputs"].get("height_geometry_corrections_csv", ""))
    if corr_path.exists():
        corr = pd.read_csv(corr_path)
    else:
        corr = pd.DataFrame(cfg.get("default_corrections", []))
        ensure_parent(corr_path)
        corr.to_csv(corr_path, index=False, encoding="utf-8-sig")
        print(f"[INFO] Correction CSV not found; wrote default template: {corr_path}")

    required = ["target_type", "target_id", "manual_decision"]
    for col in required:
        if col not in corr.columns:
            raise KeyError(f"Correction CSV missing required column: {col}")

    if "manual_height_m" not in corr.columns:
        corr["manual_height_m"] = ""
    if "manual_notes" not in corr.columns:
        corr["manual_notes"] = ""

    corr["target_type"] = corr["target_type"].fillna("building").astype(str)
    corr["target_id"] = corr["target_id"].astype(str)
    corr["manual_decision"] = corr["manual_decision"].fillna("").astype(str)
    corr["manual_notes"] = corr["manual_notes"].fillna("").astype(str)
    return corr


def find_id_col(gdf: gpd.GeoDataFrame) -> str:
    for c in ["building_id", "manual_id", "source_building_id", "id"]:
        if c in gdf.columns:
            return c
    raise KeyError("No building id column found. Expected one of: building_id, manual_id, source_building_id, id")


def update_height(row: pd.Series, new_height: float, notes: str) -> pd.Series:
    old_height = row.get("height_m", None)
    row["height_m_before_beta1"] = old_height
    row["height_m"] = float(new_height)
    row["height_source_before_beta1"] = row.get("height_source", "")
    row["height_source"] = "manual_height_adjust_beta1"
    row["height_confidence_before_beta1"] = row.get("height_confidence", "")
    row["height_confidence"] = "manual_medium"
    row["height_warning"] = clean_str(row.get("height_warning", ""))
    if row["height_warning"]:
        row["height_warning"] += ";manual_height_adjusted_beta1"
    else:
        row["height_warning"] = "manual_height_adjusted_beta1"
    row["manual_beta1_notes"] = notes
    return row


def infer_split_height(split_row: pd.Series, defaults: Dict[str, Any]) -> float:
    # Prefer explicit manual_height_m / height_m in the split layer.
    for col in ["manual_height_m", "height_m", "height", "manual_height"]:
        if col in split_row.index:
            val = to_float(split_row.get(col), None)
            if val is not None and val > 0:
                return float(val)

    part_type = ""
    for col in ["part_type", "split_type", "building_part", "type"]:
        if col in split_row.index:
            part_type = clean_str(split_row.get(col)).lower()
            break

    if "tower" in part_type or "high" in part_type:
        return float(defaults.get("tower_height_m", 93.7))
    if "podium" in part_type or "base" in part_type or "low" in part_type:
        return float(defaults.get("podium_height_m", 15))
    return float(defaults.get("unknown_part_height_m", 30))


def load_manual_split(cfg: Dict[str, Any], parent_id: str) -> gpd.GeoDataFrame:
    path = Path(cfg["inputs"].get("manual_split_buildings_geojson", ""))
    if not path.exists():
        raise FileNotFoundError(
            f"manual_split_buildings_geojson not found: {path}\n"
            "Create it in QGIS before using split_complex correction."
        )

    split = gpd.read_file(path)
    if split.empty:
        raise ValueError(f"manual split layer is empty: {path}")
    if split.crs is None:
        print(f"[WARN] manual split layer has no CRS; assigning {cfg.get('crs', TARGET_CRS)}")
        split = split.set_crs(cfg.get("crs", TARGET_CRS))
    split = split.to_crs(cfg.get("crs", TARGET_CRS))
    split = make_valid_gdf(split)

    # If parent_building_id exists, filter to the parent. If not, assume all polygons are for v10_bldg_000002.
    parent_cols = [c for c in ["parent_building_id", "parent_id", "source_parent_id"] if c in split.columns]
    if parent_cols:
        pcol = parent_cols[0]
        subset = split[split[pcol].fillna("").astype(str).eq(parent_id)].copy()
        if len(subset) > 0:
            split = subset
        else:
            print(f"[WARN] No split geometries matched {pcol}={parent_id}; using all split geometries.")
            split["parent_building_id"] = parent_id
    else:
        split["parent_building_id"] = parent_id

    if len(split) == 0:
        raise ValueError(f"No manual split geometries available for {parent_id}")
    return split


def build_split_records(
    split: gpd.GeoDataFrame,
    canonical_columns: List[str],
    parent_row: pd.Series,
    defaults: Dict[str, Any],
) -> gpd.GeoDataFrame:
    rows: List[Dict[str, Any]] = []
    parent_id = clean_str(parent_row.get("building_id", defaults.get("parent_building_id", "v10_bldg_000002")))

    for i, r in split.reset_index(drop=True).iterrows():
        rec: Dict[str, Any] = {}
        for col in canonical_columns:
            if col == "geometry":
                continue
            rec[col] = None

        manual_id = clean_str(r.get("manual_id", "")) or clean_str(r.get("building_id", "")) or f"{parent_id}_split_{i+1:02d}"
        part_type = clean_str(r.get("part_type", r.get("split_type", "manual_split"))) or "manual_split"
        h = infer_split_height(r, defaults)

        # Preserve parent context where useful.
        rec.update({
            "building_id": manual_id,
            "source_name": "manual_split",
            "geometry_source": "manual_split",
            "source_building_id": manual_id,
            "source_candidates": f"manual_split_from:{parent_id}",
            "source_candidate_ids": manual_id,
            "n_source_candidates": 1,
            "parent_building_id": parent_id,
            "part_type": part_type,
            "height_m": float(h),
            "height_source": "manual_split_height_beta1",
            "height_confidence": clean_str(r.get("height_confidence", "manual_medium")) or "manual_medium",
            "height_warning": "manual_split_geometry_beta1",
            "manual_beta1_notes": clean_str(r.get("manual_notes", r.get("notes", ""))) or f"Manual split replacement for {parent_id}",
            "area_m2": float(r.geometry.area),
        })

        # Keep land-use context from parent if these fields exist.
        for col in ["lu_desc_v10", "land_use_hint", "land_use_raw"]:
            if col in canonical_columns:
                rec[col] = parent_row.get(col, rec.get(col))

        rec["geometry"] = r.geometry
        rows.append(rec)

    return gpd.GeoDataFrame(rows, geometry="geometry", crs=split.crs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to config JSON")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    crs = cfg.get("crs", TARGET_CRS)
    inp = cfg["inputs"]
    out = cfg["outputs"]

    canonical_path = Path(inp["reviewed_canonical_geojson"])
    if not canonical_path.exists():
        raise FileNotFoundError(f"reviewed canonical not found: {canonical_path}")

    b = gpd.read_file(canonical_path)
    if b.crs is None:
        b = b.set_crs(crs)
    b = b.to_crs(crs)
    b = make_valid_gdf(b)

    id_col = find_id_col(b)
    if id_col != "building_id":
        b["building_id"] = b[id_col].astype(str)
    else:
        b["building_id"] = b["building_id"].astype(str)

    b["height_m"] = pd.to_numeric(b.get("height_m", pd.Series(index=b.index, dtype=float)), errors="coerce")
    b["area_m2"] = pd.to_numeric(b.get("area_m2", b.geometry.area), errors="coerce").fillna(b.geometry.area)

    corrections = load_corrections(cfg)
    applied: List[Dict[str, Any]] = []
    removed_original_rows: List[pd.Series] = []
    split_records: List[gpd.GeoDataFrame] = []

    # Work on a mutable copy.
    b2 = b.copy()

    for _, c in corrections.iterrows():
        target_id = clean_str(c.get("target_id"))
        decision = clean_str(c.get("manual_decision")).lower()
        notes = clean_str(c.get("manual_notes"))
        manual_height = to_float(c.get("manual_height_m"), None)

        if not target_id or not decision:
            continue

        match = b2["building_id"].astype(str).eq(target_id)
        if not match.any():
            applied.append({
                "target_id": target_id,
                "manual_decision": decision,
                "status": "not_found_in_canonical",
                "notes": notes,
            })
            print(f"[WARN] {target_id} not found in canonical; skipped.")
            continue

        idx = b2.index[match][0]
        old_height = b2.at[idx, "height_m"]

        if decision == "height_adjust":
            if manual_height is None:
                raise ValueError(f"height_adjust for {target_id} requires manual_height_m")
            b2.loc[idx] = update_height(b2.loc[idx], manual_height, notes)
            applied.append({
                "target_id": target_id,
                "manual_decision": decision,
                "old_height_m": old_height,
                "new_height_m": manual_height,
                "status": "applied_height_adjust",
                "notes": notes,
            })

        elif decision == "split_complex":
            parent_row = b2.loc[idx].copy()
            removed_original_rows.append(parent_row)
            split = load_manual_split(cfg, parent_id=target_id)
            split_gdf = build_split_records(
                split=split,
                canonical_columns=list(b2.columns),
                parent_row=parent_row,
                defaults=cfg.get("split_defaults", {}),
            )
            split_records.append(split_gdf)
            b2 = b2.drop(index=idx)
            applied.append({
                "target_id": target_id,
                "manual_decision": decision,
                "old_height_m": old_height,
                "new_height_m": "split_geometry",
                "n_split_polygons": len(split_gdf),
                "status": "applied_split_complex",
                "notes": notes,
            })

        else:
            applied.append({
                "target_id": target_id,
                "manual_decision": decision,
                "old_height_m": old_height,
                "status": "unsupported_decision_skipped",
                "notes": notes,
            })
            print(f"[WARN] Unsupported decision for beta1 script: {decision} ({target_id}); skipped.")

    if split_records:
        # Align all split records to canonical columns, allowing new parent/part fields.
        split_all = pd.concat(split_records, ignore_index=True)
        b2 = pd.concat([b2, split_all], ignore_index=True, sort=False)
        b2 = gpd.GeoDataFrame(b2, geometry="geometry", crs=crs)

    b2 = make_valid_gdf(b2)
    b2["area_m2"] = pd.to_numeric(b2.get("area_m2", b2.geometry.area), errors="coerce").fillna(b2.geometry.area)
    b2["height_m"] = pd.to_numeric(b2["height_m"], errors="coerce")

    heightqa_path = Path(out["heightqa_canonical_geojson"])
    ensure_parent(heightqa_path)
    b2.to_file(heightqa_path, driver="GeoJSON")

    applied_df = pd.DataFrame(applied)
    applied_path = Path(out["applied_corrections_csv"])
    ensure_parent(applied_path)
    applied_df.to_csv(applied_path, index=False, encoding="utf-8-sig")

    replaced_path = Path(out.get("split_replaced_originals_geojson", "data/features_3d/v10/manual_qa/split_replaced_originals_beta1.geojson"))
    ensure_parent(replaced_path)
    if removed_original_rows:
        repl = gpd.GeoDataFrame(removed_original_rows, geometry="geometry", crs=crs)
        repl.to_file(replaced_path, driver="GeoJSON")
    else:
        # write an empty file with at least geometry if possible
        gpd.GeoDataFrame({"note": []}, geometry=[], crs=crs).to_file(replaced_path, driver="GeoJSON")

    # QA report
    report_path = Path(out["heightqa_report"])
    ensure_parent(report_path)
    before_count = len(b)
    after_count = len(b2)
    null_h = int(b2["height_m"].isna().sum())
    stats = b2["height_m"].describe().to_string()
    source_counts = b2.get("height_source", pd.Series("", index=b2.index)).fillna("missing").value_counts().to_string()

    with report_path.open("w", encoding="utf-8") as f:
        f.write("# v10-beta.1 height / geometry correction QA report\n\n")
        f.write(f"Input canonical buildings: **{before_count}**\n")
        f.write(f"Output height-QA canonical buildings: **{after_count}**\n")
        f.write(f"Applied corrections: **{len(applied_df)}**\n")
        f.write(f"Null heights after correction: **{null_h}**\n\n")
        f.write("## Correction decisions applied\n\n")
        if len(applied_df):
            f.write("```text\n")
            f.write(applied_df.to_string(index=False))
            f.write("\n```\n\n")
        f.write("## Height source counts after beta1 correction\n\n")
        f.write("```text\n")
        f.write(source_counts)
        f.write("\n```\n\n")
        f.write("## Height statistics after beta1 correction\n\n")
        f.write("```text\n")
        f.write(stats)
        f.write("\n```\n\n")
        f.write("## Outputs\n\n")
        f.write(f"- height-QA canonical: `{heightqa_path}`\n")
        f.write(f"- split replaced originals: `{replaced_path}`\n")
        f.write(f"- applied corrections CSV: `{applied_path}`\n")

    print(f"[OK] height-QA canonical: {heightqa_path}")
    print(f"[OK] applied corrections: {applied_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
