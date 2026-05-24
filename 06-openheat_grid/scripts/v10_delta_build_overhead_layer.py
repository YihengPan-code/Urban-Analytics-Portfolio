"""Build v10 overhead infrastructure layer from OSM/QA/manual sources.

This is the patched version of the v10-delta patch script.

Fixes vs original:
  1. IoU-based deduplication across the four overhead source layers.
     The original concat-only approach lets v09_overhead_footprints,
     v09_overhead_structures, and the v10 manual QA candidates contribute
     overlapping geometries for the same physical structure (e.g., the same
     elevated road represented as both a polygon footprint AND a buffered
     line). Without dedup, gpd.overlay in the cell-metrics step would
     double-count `inter_area_m2` per (cell, candidate) pair, inflating
     `overhead_fraction_total` and biasing the sensitivity ranking.

     Dedup strategy: priority order is
       v09_overhead_footprints > v09_overhead_structures
       > v10_manual_overhead_candidates > v10_manual_extra_overhead.
     For each candidate (in priority order), if it overlaps any already-
     accepted feature with IoU >= 0.5, it is dropped but its source label is
     appended to `dup_sources` on the kept feature, preserving provenance.

  2. Dedup stats are written to the QA report so reviewers can see how many
     features were merged.

This script still does NOT add overhead structures to the ground-up building DSM.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import geopandas as gpd
import pandas as pd

try:
    from shapely.validation import make_valid
except ImportError:  # shapely < 2
    make_valid = None


# Lower number = higher priority. Used to decide which feature is kept on overlap.
SOURCE_PRIORITY = {
    "v09_overhead_footprints": 0,
    "v09_overhead_structures": 1,
    "v10_manual_overhead_candidates": 2,
    "v10_manual_extra_overhead": 3,
}

DEDUP_IOU_THRESHOLD = 0.5  # If IoU >= this, treat as the same physical structure.

VALID_OVERHEAD_TYPES = {
    "covered_walkway", "pedestrian_bridge", "station_canopy",
    "elevated_rail", "elevated_road", "viaduct", "unknown_overhead",
}


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def clean_geom(geom):
    if geom is None or geom.is_empty:
        return geom
    try:
        if not geom.is_valid:
            geom = make_valid(geom) if make_valid else geom.buffer(0)
        if geom.geom_type == "GeometryCollection":
            parts = []
            for g in geom.geoms:
                if g.geom_type in ["Polygon", "MultiPolygon", "LineString",
                                    "MultiLineString", "Point", "MultiPoint"] and not g.is_empty:
                    parts.append(g)
            if len(parts) == 1:
                geom = parts[0]
            elif len(parts) > 1:
                polys = [g for g in parts if g.geom_type in ["Polygon", "MultiPolygon"]]
                geom = polys[0] if polys else parts[0]
        return geom
    except Exception:
        return geom.buffer(0)


def row_text(row: pd.Series) -> str:
    vals = []
    for k, v in row.items():
        if k == "geometry":
            continue
        if pd.isna(v):
            continue
        vals.append(str(v))
    return " ".join(vals).lower()


def infer_type(row: pd.Series) -> str:
    for col in ["overhead_type", "type", "structure_type", "qa_type", "manual_type"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            val = str(row[col]).strip().lower().replace(" ", "_")
            if val in VALID_OVERHEAD_TYPES:
                return val
    txt = row_text(row)
    if any(x in txt for x in ["covered walkway", "linkway", "covered_walkway", "shelter", "walkway"]):
        return "covered_walkway"
    if any(x in txt for x in ["pedestrian bridge", "footbridge", "overhead bridge"]):
        return "pedestrian_bridge"
    if any(x in txt for x in ["station canopy", "canopy", "platform roof", "station roof"]):
        return "station_canopy"
    if any(x in txt for x in ["rail", "mrt", "lrt", "viaduct rail", "elevated rail"]):
        return "elevated_rail"
    if any(x in txt for x in ["viaduct", "flyover"]):
        return "viaduct"
    if any(x in txt for x in ["motorway", "expressway", "elevated road", "road bridge",
                                "bridge", "highway", "road"]):
        return "elevated_road"
    return "unknown_overhead"


def footprint_geom(geom, overhead_type: str, width_lookup: Dict[str, float], default_width: float):
    geom = clean_geom(geom)
    if geom is None or geom.is_empty:
        return geom
    width = float(width_lookup.get(overhead_type, default_width))
    if geom.geom_type in ["Polygon", "MultiPolygon"]:
        return geom
    if geom.geom_type in ["LineString", "MultiLineString"]:
        return geom.buffer(width / 2.0, cap_style=2, join_style=2)
    if geom.geom_type in ["Point", "MultiPoint"]:
        return geom.buffer(width / 2.0)
    return geom.buffer(width / 2.0)


def read_optional(path: Path, source_label: str, crs: str) -> gpd.GeoDataFrame:
    if not path.exists():
        return gpd.GeoDataFrame(columns=["source_layer", "geometry"], geometry="geometry", crs=crs)
    gdf = gpd.read_file(path)
    if gdf.empty:
        return gpd.GeoDataFrame(columns=["source_layer", "geometry"], geometry="geometry", crs=crs)
    if gdf.crs is None:
        gdf = gdf.set_crs(crs)
    gdf = gdf.to_crs(crs)
    gdf["source_layer"] = source_label
    return gdf


def dedup_by_iou(gdf: gpd.GeoDataFrame, iou_threshold: float) -> tuple[gpd.GeoDataFrame, Dict[str, int]]:
    """Greedy IoU-based dedup, traversing in source-priority order.

    Returns (deduped_gdf, stats_dict).
    On overlap (IoU >= threshold), the higher-priority feature is kept and the
    lower-priority feature's source_layer is appended to the kept feature's
    `dup_sources` field for provenance.
    """
    if gdf.empty:
        return gdf, {"input": 0, "kept": 0, "dropped_as_duplicate": 0}

    df = gdf.copy()
    df["_priority"] = df["source_layer"].map(SOURCE_PRIORITY).fillna(99).astype(int)
    df = df.sort_values("_priority", kind="stable").reset_index(drop=True)

    kept_rows: List[Dict[str, Any]] = []
    kept_geoms: List[Any] = []
    n_dropped = 0

    # Build STR tree once via geopandas sindex for kept geoms.
    # Since kept_geoms grows incrementally, rebuild sindex periodically.
    # For typical Toa Payoh overhead counts (< few hundred), naive O(N^2) is fine.
    for _, row in df.iterrows():
        g = row.geometry
        if g is None or g.is_empty:
            continue

        merged_into: int | None = None
        for kept_idx, kg in enumerate(kept_geoms):
            if not g.intersects(kg):
                continue
            inter_area = g.intersection(kg).area
            if inter_area == 0:
                continue
            union_area = g.union(kg).area
            iou = inter_area / union_area if union_area > 0 else 0.0
            if iou >= iou_threshold:
                merged_into = kept_idx
                break

        if merged_into is not None:
            existing_dup = kept_rows[merged_into].get("dup_sources", "")
            new_label = str(row.get("source_layer", "?"))
            kept_rows[merged_into]["dup_sources"] = (
                f"{existing_dup};{new_label}" if existing_dup else new_label
            )
            kept_rows[merged_into]["n_source_candidates"] = int(
                kept_rows[merged_into].get("n_source_candidates", 1)
            ) + 1
            n_dropped += 1
        else:
            rec = {col: row[col] for col in df.columns if col != "_priority"}
            rec["dup_sources"] = ""
            rec["n_source_candidates"] = 1
            kept_rows.append(rec)
            kept_geoms.append(g)

    out = gpd.GeoDataFrame(kept_rows, geometry="geometry", crs=gdf.crs)
    stats = {
        "input": int(len(df)),
        "kept": int(len(out)),
        "dropped_as_duplicate": int(n_dropped),
    }
    return out, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_delta_overhead_config.example.json")
    args = ap.parse_args()

    cfg = read_json(Path(args.config))
    crs = cfg.get("crs", "EPSG:3414")
    inp = cfg["inputs"]
    out = cfg["outputs"]
    cls = cfg.get("classification", {})
    widths = cls.get("type_width_m", {})
    default_width = float(cls.get("default_width_m", 5.0))
    opacities = cls.get("type_opacity", {})

    sources = [
        (Path(inp.get("v09_overhead_footprints_geojson", "")), "v09_overhead_footprints"),
        (Path(inp.get("v09_overhead_structures_geojson", "")), "v09_overhead_structures"),
        (Path(inp.get("v10_overhead_candidates_geojson", "")), "v10_manual_overhead_candidates"),
        (Path(inp.get("manual_overhead_candidates_geojson", "")), "v10_manual_extra_overhead"),
    ]

    frames: List[gpd.GeoDataFrame] = []
    loaded = []
    for path, label in sources:
        if not str(path):
            continue
        gdf = read_optional(path, label, crs)
        if not gdf.empty:
            loaded.append((label, str(path), len(gdf)))
            frames.append(gdf)

    if not frames:
        raise FileNotFoundError(
            "No overhead source layers found. Check config input paths or "
            "create manual_overhead_candidates_v10.geojson."
        )

    raw = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True, sort=False),
                            geometry="geometry", crs=crs)
    raw = raw[raw.geometry.notna() & (~raw.geometry.is_empty)].copy()
    raw["overhead_type"] = raw.apply(infer_type, axis=1)
    raw["opacity"] = raw["overhead_type"].map(lambda t: float(opacities.get(t, 0.6)))
    raw["width_m_used"] = raw["overhead_type"].map(lambda t: float(widths.get(t, default_width)))
    raw["geometry_raw_type"] = raw.geometry.geom_type
    raw["geometry"] = [
        footprint_geom(g, t, widths, default_width)
        for g, t in zip(raw.geometry, raw["overhead_type"])
    ]
    raw = raw[raw.geometry.notna() & (~raw.geometry.is_empty)].copy()

    n_pre_dedup = len(raw)
    print(f"[INFO] {n_pre_dedup} candidate features pre-dedup")

    # ---- NEW: IoU-based dedup ----
    deduped, dedup_stats = dedup_by_iou(raw, DEDUP_IOU_THRESHOLD)
    print(
        f"[INFO] dedup IoU>={DEDUP_IOU_THRESHOLD}: kept={dedup_stats['kept']}, "
        f"dropped_as_duplicate={dedup_stats['dropped_as_duplicate']}"
    )

    deduped["overhead_id"] = [f"ovh_{i+1:05d}" for i in range(len(deduped))]
    deduped["area_m2"] = deduped.geometry.area

    keep_cols = [
        "overhead_id", "overhead_type", "opacity", "width_m_used",
        "source_layer", "dup_sources", "n_source_candidates",
        "geometry_raw_type", "area_m2", "geometry",
    ]
    for c in ["name", "highway", "railway", "bridge", "covered", "layer",
                "building_id", "manual_notes", "notes"]:
        if c in deduped.columns and c not in keep_cols:
            keep_cols.insert(-1, c)
    overhead = deduped[[c for c in keep_cols if c in deduped.columns]].copy()

    out_path = Path(out["overhead_structures_geojson"])
    ensure_dir(out_path)
    overhead.to_file(out_path, driver="GeoJSON")

    type_counts = overhead.groupby("overhead_type", dropna=False).size().reset_index(name="n")
    source_counts = overhead.groupby("source_layer", dropna=False).size().reset_index(name="n")
    multi_source = int((overhead["n_source_candidates"] > 1).sum())

    report_path = Path(out["overhead_layer_report"])
    ensure_dir(report_path)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# v10-delta overhead layer QA report\n\n")
        f.write("This layer is for overhead-infrastructure sensitivity. It is **not** "
                "merged into the ground-up building DSM.\n\n")
        f.write(f"Output layer: `{out_path}`\n\n")
        f.write(f"Features (after dedup): **{len(overhead)}**\n")
        f.write(f"Total footprint area: **{overhead.geometry.area.sum():.1f} m²**\n\n")
        f.write("## Dedup statistics\n\n```text\n")
        f.write(f"input candidates:        {dedup_stats['input']}\n")
        f.write(f"kept canonical features: {dedup_stats['kept']}\n")
        f.write(f"dropped as duplicate:    {dedup_stats['dropped_as_duplicate']}\n")
        f.write(f"IoU threshold:           {DEDUP_IOU_THRESHOLD}\n")
        f.write(f"multi-source canonical:  {multi_source}\n")
        f.write("```\n\n")
        f.write("## Loaded sources\n\n")
        if loaded:
            f.write("```text\n")
            for label, path, n in loaded:
                f.write(f"{label}: {n} features from {path}\n")
            f.write("```\n\n")
        f.write("## Overhead type counts (after dedup)\n\n```text\n")
        f.write(type_counts.to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Source counts (kept canonical only)\n\n```text\n")
        f.write(source_counts.to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Interpretation\n")
        f.write("- Elevated roads/rail/canopies are represented as separate overhead footprints.\n")
        f.write("- Each canonical feature carries `dup_sources` and `n_source_candidates` for "
                "provenance auditing.\n")
        f.write("- IoU-based dedup ensures `overhead_fraction_total` per cell is not "
                "double-counted across overlapping source layers.\n")
        f.write("- The next step is cell-level overhead metrics and shade-sensitivity analysis.\n")

    print(f"[OK] overhead layer: {out_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
