#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenHeat v1.0-alpha.2 QA target generator.

Purpose
-------
Generate a focused manual-QA target set after v1.0-alpha.1 augmented DSM:
  1) large / low-confidence buildings,
  2) suspected transport / shelter / overhead-like structures,
  3) conflict-review footprints,
  4) negative-gain cells,
  5) old v0.8/v0.9 high-hazard cells whose ranking may have been driven by DSM gaps,
  6) v0.9 critical tiles T01/T05/T06 and other selected-tile context.

Outputs
-------
outputs/v10_dsm_audit/alpha2_qa_targets/
  - v10_alpha2_building_QA_targets.csv
  - v10_alpha2_building_QA_targets.geojson
  - v10_alpha2_conflict_QA_targets.csv
  - v10_alpha2_conflict_QA_targets.geojson
  - v10_alpha2_cell_QA_targets.csv
  - v10_alpha2_cell_QA_targets.geojson
  - v10_alpha2_manual_review_template.csv
  - v10_alpha2_QA_report.md

Notes
-----
This script does not edit the canonical building layer. It creates a review list.
After manual QA, use the review table to decide which buildings should be:
  - kept in building DSM,
  - moved to an overhead/transport DSM,
  - removed,
  - height-adjusted,
  - merged / manually digitised.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

try:
    import geopandas as gpd
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "geopandas is required for v10_alpha2_generate_qa_targets.py. "
        "Install with: conda install -c conda-forge geopandas pyogrio shapely"
    ) from e


WORKING_CRS = "EPSG:3414"


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def exists(path: str | Path) -> bool:
    return Path(path).exists()


def load_gdf(path: str | Path, name: str, required: bool = True) -> Optional[gpd.GeoDataFrame]:
    p = Path(path)
    if not p.exists():
        if required:
            raise FileNotFoundError(f"{name} not found: {p}")
        print(f"[WARN] Optional {name} not found: {p}")
        return None
    gdf = gpd.read_file(p)
    if gdf.crs is None:
        print(f"[WARN] {name} has no CRS. Assuming {WORKING_CRS}.")
        gdf = gdf.set_crs(WORKING_CRS)
    else:
        gdf = gdf.to_crs(WORKING_CRS)
    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()
    return gdf


def load_csv(path: str | Path, name: str, required: bool = True) -> Optional[pd.DataFrame]:
    p = Path(path)
    if not p.exists():
        if required:
            raise FileNotFoundError(f"{name} not found: {p}")
        print(f"[WARN] Optional {name} not found: {p}")
        return None
    return pd.read_csv(p)


def col_first(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def as_num(s: pd.Series, default: float = np.nan) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(default)


def contains_any(row: pd.Series, patterns: Iterable[str]) -> bool:
    text = " ".join("" if pd.isna(v) else str(v) for v in row.values).lower()
    return any(re.search(p, text) for p in patterns)


def add_manual_fields(df: pd.DataFrame, fields: Dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    for k, v in fields.items():
        if k not in out.columns:
            out[k] = v
    return out


def make_priority(df: pd.DataFrame, kind: str) -> pd.Series:
    """Heuristic priority score for sorting manual QA targets."""
    score = pd.Series(0.0, index=df.index)

    if "area_m2" in df.columns:
        score += np.minimum(as_num(df["area_m2"], 0) / 1000.0, 10.0)

    if "qa_category" in df.columns:
        cat = df["qa_category"].astype(str)
        score += cat.str.contains("large_low_conf", case=False, na=False).astype(float) * 8
        score += cat.str.contains("transport|shelter|overhead", case=False, na=False).astype(float) * 7
        score += cat.str.contains("conflict", case=False, na=False).astype(float) * 6
        score += cat.str.contains("critical_tile", case=False, na=False).astype(float) * 5
        score += cat.str.contains("negative_gain", case=False, na=False).astype(float) * 5
        score += cat.str.contains("old_top_hazard", case=False, na=False).astype(float) * 5

    if "old_hazard_rank" in df.columns:
        r = as_num(df["old_hazard_rank"], np.nan)
        score += np.where(r.notna(), np.maximum(0, (100 - r) / 10), 0)

    if "coverage_gain_vs_osm" in df.columns:
        score += np.minimum(np.abs(as_num(df["coverage_gain_vs_osm"], 0)) * 3, 5)

    if "new_minus_old_dsm_area_m2" in df.columns:
        score += np.minimum(np.abs(as_num(df["new_minus_old_dsm_area_m2"], 0)) / 500.0, 8)

    return score.round(3)


def infer_transport_or_shelter_flags(gdf: gpd.GeoDataFrame) -> pd.Series:
    patterns = [
        r"transport", r"mrt", r"rail", r"road", r"bridge", r"viaduct",
        r"shelter", r"covered", r"canopy", r"station", r"bus", r"carpark",
        r"parking", r"platform", r"depot"
    ]
    return gdf.apply(lambda row: contains_any(row, patterns), axis=1)


def prepare_building_targets(
    buildings: gpd.GeoDataFrame,
    tiles: Optional[gpd.GeoDataFrame],
    thresholds: Dict[str, Any],
    manual_fields: Dict[str, Any],
) -> gpd.GeoDataFrame:
    b = buildings.copy()
    if "area_m2" not in b.columns:
        b["area_m2"] = b.geometry.area
    b["area_m2"] = as_num(b["area_m2"], 0)

    if "height_confidence" not in b.columns:
        b["height_confidence"] = ""
    if "height_source" not in b.columns:
        b["height_source"] = ""
    if "height_warning" not in b.columns:
        b["height_warning"] = ""

    # Tag overlap with v09 tiles, if available.
    b["intersects_v09_tile"] = False
    b["v09_tile_types"] = ""
    b["v09_tile_ids"] = ""
    if tiles is not None and len(tiles) > 0:
        tile_cols = [c for c in ["tile_id", "tile_type", "focus_cell_id", "cell_id"] if c in tiles.columns]
        joined = gpd.sjoin(
            b[["building_id", "geometry"]] if "building_id" in b.columns else b.reset_index()[["index", "geometry"]].rename(columns={"index": "building_id"}),
            tiles[tile_cols + ["geometry"]],
            how="left",
            predicate="intersects",
        )
        if "building_id" in joined.columns:
            tile_summary = (
                joined.dropna(subset=["index_right"])
                .groupby("building_id")
                .agg(
                    v09_tile_ids=("tile_id", lambda x: ";".join(sorted(set(map(str, x)))) if "tile_id" in joined.columns else ""),
                    v09_tile_types=("tile_type", lambda x: ";".join(sorted(set(map(str, x)))) if "tile_type" in joined.columns else ""),
                )
                .reset_index()
            )
            if len(tile_summary):
                b = b.merge(tile_summary, on="building_id", how="left", suffixes=("", "_joined"))
                for c in ["v09_tile_ids", "v09_tile_types"]:
                    if f"{c}_joined" in b.columns:
                        b[c] = b[f"{c}_joined"].combine_first(b.get(c, ""))
                        b.drop(columns=[f"{c}_joined"], inplace=True)
                b["v09_tile_ids"] = b["v09_tile_ids"].fillna("")
                b["v09_tile_types"] = b["v09_tile_types"].fillna("")
                b["intersects_v09_tile"] = b["v09_tile_ids"].astype(str).str.len() > 0

    low_conf = b["height_confidence"].astype(str).str.lower().isin(["low", "medium_low"])
    large_low = b[(b["area_m2"] >= thresholds["large_low_conf_area_m2"]) & low_conf].copy()
    large_low["qa_category"] = "large_low_confidence_building"

    # Very large default-height buildings, even if medium confidence.
    height_source = b["height_source"].astype(str).str.lower()
    default_height = height_source.str.contains("default|unknown|lu_default|area_default|type_default", na=False)
    very_large = b[(b["area_m2"] >= thresholds["very_large_default_area_m2"]) & default_height].copy()
    very_large["qa_category"] = "very_large_default_height_building"

    transport_like = b[infer_transport_or_shelter_flags(b) & (b["area_m2"] >= 100)].copy()
    transport_like["qa_category"] = "transport_shelter_overhead_candidate"

    critical_tile = b[b.get("intersects_v09_tile", False).astype(bool) & (low_conf | default_height | infer_transport_or_shelter_flags(b))].copy()
    critical_tile["qa_category"] = "critical_tile_building_review"

    targets = pd.concat([large_low, very_large, transport_like, critical_tile], ignore_index=True, sort=False)
    if len(targets) == 0:
        return gpd.GeoDataFrame(columns=list(b.columns) + ["qa_category"], geometry="geometry", crs=b.crs)

    # Deduplicate targets by building_id if available, combining categories.
    id_col = "building_id" if "building_id" in targets.columns else None
    if id_col:
        non_geom_cols = [c for c in targets.columns if c != "geometry"]
        cat_summary = (
            targets.groupby(id_col)
            .agg({c: "first" for c in non_geom_cols if c not in [id_col, "qa_category"]})
            .reset_index()
        )
        cats = targets.groupby(id_col)["qa_category"].apply(lambda x: ";".join(sorted(set(map(str, x))))).reset_index()
        geom = targets.drop_duplicates(id_col)[[id_col, "geometry"]]
        targets = cat_summary.merge(cats, on=id_col, how="left").merge(geom, on=id_col, how="left")
        targets = gpd.GeoDataFrame(targets, geometry="geometry", crs=b.crs)

    targets["qa_target_type"] = "building"
    targets["qa_priority_score"] = make_priority(targets, "building")
    targets = add_manual_fields(targets, manual_fields)
    targets = targets.sort_values("qa_priority_score", ascending=False)

    max_n = int(thresholds.get("max_building_targets", 250))
    return targets.head(max_n).copy()


def prepare_conflict_targets(
    conflicts: Optional[gpd.GeoDataFrame],
    thresholds: Dict[str, Any],
    manual_fields: Dict[str, Any],
) -> Optional[gpd.GeoDataFrame]:
    if conflicts is None or len(conflicts) == 0:
        return None
    c = conflicts.copy()
    if "area_m2" not in c.columns:
        c["area_m2"] = c.geometry.area
    c["area_m2"] = as_num(c["area_m2"], 0)
    c = c[c["area_m2"] >= thresholds["conflict_area_m2"]].copy()
    if len(c) == 0:
        return c
    c["qa_category"] = "conflict_review_large_candidate"
    c["qa_target_type"] = "conflict_building"
    c["qa_priority_score"] = make_priority(c, "conflict")
    c = add_manual_fields(c, manual_fields)
    c = c.sort_values("qa_priority_score", ascending=False)
    return c.head(int(thresholds.get("max_conflict_targets", 100))).copy()


def prepare_cell_targets(
    grid: gpd.GeoDataFrame,
    per_cell: Optional[pd.DataFrame],
    neg: Optional[pd.DataFrame],
    risk: Optional[gpd.GeoDataFrame],
    thresholds: Dict[str, Any],
    manual_fields: Dict[str, Any],
) -> gpd.GeoDataFrame:
    g = grid.copy()
    if "cell_id" not in g.columns:
        raise KeyError("grid_geojson must contain cell_id")
    base_cols = ["cell_id", "geometry"]
    out = g[base_cols].copy()

    if per_cell is not None and "cell_id" in per_cell.columns:
        out = out.merge(per_cell, on="cell_id", how="left")

    # Merge old hazard ranks if available.
    if risk is not None and "cell_id" in risk.columns:
        rank_cols = [c for c in [
            "cell_id",
            "hazard_rank_true_v08",
            "risk_rank_v08_conditioned",
            "risk_rank_v08_social_conditioned",
            "hazard_score",
            "max_utci_c",
        ] if c in risk.columns]
        out = out.merge(pd.DataFrame(risk[rank_cols].drop(columns="geometry", errors="ignore")), on="cell_id", how="left")

    # Negative-gain cells.
    cat_parts = []
    if "new_minus_old_dsm_area_m2" in out.columns:
        neg_flag = as_num(out["new_minus_old_dsm_area_m2"], 0) < float(thresholds["negative_gain_area_m2"])
    else:
        neg_flag = pd.Series(False, index=out.index)

    # Old high hazard + low old completeness / high gain.
    old_rank_col = col_first(out, ["hazard_rank_true_v08", "old_hazard_rank", "rank_proxy_v07_hazard_score"])
    if old_rank_col:
        old_top = as_num(out[old_rank_col], np.inf) <= float(thresholds.get("old_hazard_top_n", 50))
    else:
        old_top = pd.Series(False, index=out.index)

    low_old_comp = (
        as_num(out.get("old_vs_osm_completeness", pd.Series(np.nan, index=out.index)), np.nan)
        < float(thresholds.get("low_old_completeness_threshold", 0.2))
    )
    high_gain = (
        as_num(out.get("coverage_gain_vs_osm", pd.Series(0, index=out.index)), 0)
        >= float(thresholds.get("high_coverage_gain_threshold", 0.5))
    )

    selected = out[neg_flag | (old_top & (low_old_comp | high_gain))].copy()
    if len(selected) == 0:
        return gpd.GeoDataFrame(columns=list(out.columns) + ["qa_category"], geometry="geometry", crs=g.crs)

    def cell_category(row: pd.Series) -> str:
        cats = []
        if "new_minus_old_dsm_area_m2" in row.index and pd.notna(row["new_minus_old_dsm_area_m2"]) and row["new_minus_old_dsm_area_m2"] < thresholds["negative_gain_area_m2"]:
            cats.append("negative_gain_cell")
        if old_rank_col and pd.notna(row.get(old_rank_col)) and row.get(old_rank_col) <= thresholds.get("old_hazard_top_n", 50):
            cats.append("old_top_hazard_cell")
        if pd.notna(row.get("old_vs_osm_completeness")) and row.get("old_vs_osm_completeness") < thresholds.get("low_old_completeness_threshold", 0.2):
            cats.append("low_old_completeness")
        if pd.notna(row.get("coverage_gain_vs_osm")) and row.get("coverage_gain_vs_osm") >= thresholds.get("high_coverage_gain_threshold", 0.5):
            cats.append("high_coverage_gain")
        return ";".join(cats) if cats else "cell_review"

    selected["qa_category"] = selected.apply(cell_category, axis=1)
    selected["qa_target_type"] = "cell"
    selected["old_hazard_rank"] = selected[old_rank_col] if old_rank_col else np.nan
    selected["qa_priority_score"] = make_priority(selected, "cell")
    selected = add_manual_fields(selected, manual_fields)
    selected = selected.sort_values("qa_priority_score", ascending=False)
    return selected.head(int(thresholds.get("max_cell_targets", 150))).copy()


def write_gdf(gdf: gpd.GeoDataFrame, csv_path: Path, geojson_path: Path) -> None:
    # CSV without geometry, but include WKT centroid for quick identification.
    df = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore"))
    if len(gdf) and "geometry" in gdf:
        cent = gdf.geometry.centroid
        df["centroid_x_svy21"] = cent.x
        df["centroid_y_svy21"] = cent.y
    df.to_csv(csv_path, index=False)
    if len(gdf):
        gdf.to_file(geojson_path, driver="GeoJSON")
    else:
        # Write empty CSV only; empty GeoJSON can be awkward for some tooling.
        print(f"[WARN] No rows for {geojson_path.name}; GeoJSON not written.")


def write_report(
    out_dir: Path,
    building_targets: gpd.GeoDataFrame,
    conflict_targets: Optional[gpd.GeoDataFrame],
    cell_targets: gpd.GeoDataFrame,
    cfg: Dict[str, Any],
) -> None:
    lines = []
    lines.append("# v1.0-alpha.2 manual QA target report")
    lines.append("")
    lines.append("This report prioritises manual QA targets before v10 morphology/ranking rerun.")
    lines.append("")
    lines.append("## Inputs")
    for k, v in cfg.get("inputs", {}).items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")

    lines.append("## Target counts")
    lines.append(f"- Building QA targets: **{len(building_targets)}**")
    lines.append(f"- Conflict QA targets: **{0 if conflict_targets is None else len(conflict_targets)}**")
    lines.append(f"- Cell QA targets: **{len(cell_targets)}**")
    lines.append("")

    if len(building_targets):
        lines.append("## Building target categories")
        lines.append("```text")
        lines.append(building_targets["qa_category"].astype(str).value_counts().to_string())
        lines.append("```")
        lines.append("")
        cols = [c for c in ["building_id", "qa_category", "qa_priority_score", "source_name", "geometry_source", "area_m2", "height_m", "height_source", "height_confidence", "height_warning", "lu_desc_v10", "v09_tile_types"] if c in building_targets.columns]
        lines.append("## Top building targets")
        lines.append("```text")
        lines.append(pd.DataFrame(building_targets[cols].head(30)).to_string(index=False))
        lines.append("```")
        lines.append("")

    if conflict_targets is not None and len(conflict_targets):
        lines.append("## Top conflict-review targets")
        cols = [c for c in ["source_name", "source_building_id", "qa_priority_score", "area_m2", "height_m_original", "levels_original", "building_type_original"] if c in conflict_targets.columns]
        lines.append("```text")
        lines.append(pd.DataFrame(conflict_targets[cols].head(30)).to_string(index=False))
        lines.append("```")
        lines.append("")

    if len(cell_targets):
        lines.append("## Cell target categories")
        lines.append("```text")
        lines.append(cell_targets["qa_category"].astype(str).value_counts().to_string())
        lines.append("```")
        cols = [c for c in ["cell_id", "qa_category", "qa_priority_score", "old_hazard_rank", "old_vs_osm_completeness", "new_vs_osm_completeness", "coverage_gain_vs_osm", "new_minus_old_dsm_area_m2"] if c in cell_targets.columns]
        lines.append("")
        lines.append("## Top cell targets")
        lines.append("```text")
        lines.append(pd.DataFrame(cell_targets[cols].head(30)).to_string(index=False))
        lines.append("```")
        lines.append("")

    lines.append("## Recommended manual decisions")
    lines.append("- `keep_building_dsm`: valid ground-up building, keep in v10 building DSM.")
    lines.append("- `move_to_overhead_dsm`: roof / canopy / elevated structure; remove from building DSM and reserve for overhead DSM.")
    lines.append("- `height_adjust`: keep footprint but change `height_m`.")
    lines.append("- `remove`: likely false positive / non-building.")
    lines.append("- `merge_conflict`: real building excluded by conservative dedup; merge into canonical.")
    lines.append("- `no_action`: target checked, no change required.")
    lines.append("")
    lines.append("## Next step")
    lines.append("Use QGIS to inspect the GeoJSON layers. Fill `manual_decision`, `manual_height_m`, and `manual_notes` in the review template before modifying the canonical building layer.")
    lines.append("")
    (out_dir / "v10_alpha2_QA_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v10/v10_alpha2_qa_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    inputs = cfg["inputs"]
    outputs = cfg.get("outputs", {})
    thresholds = cfg.get("thresholds", {})
    manual_fields = cfg.get("manual_review_fields", {})

    out_dir = Path(outputs.get("out_dir", "outputs/v10_dsm_audit/alpha2_qa_targets"))
    ensure_dir(out_dir)

    print("[INFO] Loading inputs...")
    buildings = load_gdf(inputs["canonical_buildings_height"], "canonical_buildings_height", required=True)
    conflicts = load_gdf(inputs.get("canonical_conflicts", ""), "canonical_conflicts", required=False)
    grid = load_gdf(inputs["grid_geojson"], "grid_geojson", required=True)
    tiles = load_gdf(inputs.get("v09_tiles_buffered", ""), "v09_tiles_buffered", required=False)
    risk = load_gdf(inputs.get("v08_risk_scenario_geojson", ""), "v08_risk_scenario_geojson", required=False)

    per_cell = load_csv(inputs.get("per_cell_completeness", ""), "per_cell_completeness", required=False)
    neg = load_csv(inputs.get("negative_gain_cells", ""), "negative_gain_cells", required=False)

    print("[INFO] Building QA targets...")
    building_targets = prepare_building_targets(buildings, tiles, thresholds, manual_fields)
    write_gdf(
        building_targets,
        out_dir / "v10_alpha2_building_QA_targets.csv",
        out_dir / "v10_alpha2_building_QA_targets.geojson",
    )

    print("[INFO] Conflict QA targets...")
    conflict_targets = prepare_conflict_targets(conflicts, thresholds, manual_fields)
    if conflict_targets is not None:
        write_gdf(
            conflict_targets,
            out_dir / "v10_alpha2_conflict_QA_targets.csv",
            out_dir / "v10_alpha2_conflict_QA_targets.geojson",
        )
    else:
        pd.DataFrame().to_csv(out_dir / "v10_alpha2_conflict_QA_targets.csv", index=False)

    print("[INFO] Cell QA targets...")
    cell_targets = prepare_cell_targets(grid, per_cell, neg, risk, thresholds, manual_fields)
    write_gdf(
        cell_targets,
        out_dir / "v10_alpha2_cell_QA_targets.csv",
        out_dir / "v10_alpha2_cell_QA_targets.geojson",
    )

    print("[INFO] Manual review template...")
    all_tables = []
    if len(building_targets):
        b = pd.DataFrame(building_targets.drop(columns="geometry", errors="ignore"))
        b["review_layer"] = "building"
        all_tables.append(b)
    if conflict_targets is not None and len(conflict_targets):
        c = pd.DataFrame(conflict_targets.drop(columns="geometry", errors="ignore"))
        c["review_layer"] = "conflict"
        all_tables.append(c)
    if len(cell_targets):
        c2 = pd.DataFrame(cell_targets.drop(columns="geometry", errors="ignore"))
        c2["review_layer"] = "cell"
        all_tables.append(c2)

    if all_tables:
        review = pd.concat(all_tables, ignore_index=True, sort=False)
        # Put key columns first.
        first_cols = [c for c in ["review_layer", "qa_target_type", "qa_category", "qa_priority_score", "building_id", "cell_id", "source_name", "area_m2", "height_m", "height_source", "height_confidence", "height_warning", "review_status", "manual_decision", "manual_height_m", "manual_notes"] if c in review.columns]
        rest = [c for c in review.columns if c not in first_cols]
        review = review[first_cols + rest]
    else:
        review = pd.DataFrame()
    review.to_csv(out_dir / "v10_alpha2_manual_review_template.csv", index=False)

    write_report(out_dir, building_targets, conflict_targets, cell_targets, cfg)

    print("[OK] v1.0-alpha.2 QA targets generated")
    print("out_dir:", out_dir)
    print("building targets:", len(building_targets))
    print("conflict targets:", 0 if conflict_targets is None else len(conflict_targets))
    print("cell targets:", len(cell_targets))
    print("report:", out_dir / "v10_alpha2_QA_report.md")


if __name__ == "__main__":
    main()
