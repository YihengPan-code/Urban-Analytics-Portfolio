"""
OpenHeat v0.9-gamma overhead-aware SOLWEIG tile selection.

This script replaces rank-only tile selection with a constrained design:
- avoid large overhead-infrastructure confounding for clean tiles;
- avoid heavy overlap between selected tiles;
- select a clean hazard tile, risk tiles, an open-paved hotspot, and a clean shaded reference;
- optionally add a diagnostic overhead-confounded hazard tile.

Outputs are written under data/solweig/v09_tiles_overhead_aware/ by default.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def robust01(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    lo, hi = s.quantile(0.05), s.quantile(0.95)
    if pd.isna(lo) or pd.isna(hi) or hi <= lo:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return ((s - lo) / (hi - lo)).clip(0, 1)


def square_around_point(pt, size_m: float):
    half = size_m / 2.0
    return box(pt.x - half, pt.y - half, pt.x + half, pt.y + half)


def add_tile_geometries(candidates: gpd.GeoDataFrame, tile_size_m: float, buffer_m: float) -> gpd.GeoDataFrame:
    out = candidates.copy()
    cent = out.geometry.centroid
    out["tile_geometry"] = [square_around_point(p, tile_size_m) for p in cent]
    out["tile_buffered_geometry"] = [g.buffer(buffer_m, cap_style=3, join_style=2) for g in out["tile_geometry"]]
    out["tile_center_x"] = cent.x
    out["tile_center_y"] = cent.y
    return out


def geom_iou(a, b) -> float:
    if a is None or b is None or a.is_empty or b.is_empty:
        return 0.0
    inter = a.intersection(b).area
    union = a.union(b).area
    return float(inter / union) if union > 0 else 0.0


def center_distance(row, selected_rows: List[pd.Series]) -> float:
    if not selected_rows:
        return np.inf
    p = row.geometry.centroid
    ds = [p.distance(r.geometry.centroid) for r in selected_rows]
    return float(min(ds)) if ds else np.inf


def max_iou_with_selected(row, selected_rows: List[pd.Series], use_buffered: bool = False) -> float:
    if not selected_rows:
        return 0.0
    geom_col = "tile_buffered_geometry" if use_buffered else "tile_geometry"
    g = row[geom_col]
    return max(geom_iou(g, r[geom_col]) for r in selected_rows)


def compute_tile_overhead_fraction(tiles: gpd.GeoDataFrame, overhead_fp: Path, crs: str) -> gpd.GeoDataFrame:
    tiles = tiles.copy()
    tiles["tile_overhead_fraction"] = 0.0
    tiles["tile_overhead_feature_count"] = 0
    if not overhead_fp.exists():
        print(f"[WARN] overhead footprint GeoJSON missing: {overhead_fp}; tile_overhead_fraction set to 0")
        return tiles
    oh = gpd.read_file(overhead_fp).to_crs(crs)
    if len(oh) == 0:
        return tiles
    tile_gdf = gpd.GeoDataFrame(
        tiles[["cell_id", "tile_geometry"]].copy(),
        geometry="tile_geometry",
        crs=crs,
    )
    inter = gpd.overlay(tile_gdf, oh[["geometry"]], how="intersection")
    if len(inter) == 0:
        return tiles
    inter["a"] = inter.geometry.area
    area = tile_gdf.set_index("cell_id").geometry.area.rename("tile_area")
    area_sum = inter.groupby("cell_id")["a"].sum().rename("overhead_area")
    cnt = inter.groupby("cell_id").size().rename("tile_overhead_feature_count")
    stats = pd.concat([area, area_sum, cnt], axis=1).fillna({"overhead_area": 0, "tile_overhead_feature_count": 0}).reset_index()
    stats["tile_overhead_fraction"] = (stats["overhead_area"] / stats["tile_area"]).clip(0, 1)
    tiles = tiles.drop(columns=["tile_overhead_fraction", "tile_overhead_feature_count"], errors="ignore").merge(
        stats[["cell_id", "tile_overhead_fraction", "tile_overhead_feature_count"]], on="cell_id", how="left"
    )
    tiles["tile_overhead_fraction"] = tiles["tile_overhead_fraction"].fillna(0)
    tiles["tile_overhead_feature_count"] = tiles["tile_overhead_feature_count"].fillna(0).astype(int)
    return tiles


def load_ranking(cfg: dict) -> gpd.GeoDataFrame:
    crs = cfg.get("working_crs", "EPSG:3414")
    ranking_geojson = Path(cfg["ranking_geojson"])
    ranking_csv = Path(cfg.get("ranking_csv", ""))
    grid_geojson = Path(cfg.get("grid_geojson", ""))

    if ranking_geojson.exists():
        gdf = gpd.read_file(ranking_geojson).to_crs(crs)
    elif ranking_csv.exists() and grid_geojson.exists():
        df = pd.read_csv(ranking_csv)
        geom = gpd.read_file(grid_geojson).to_crs(crs)[["cell_id", "geometry"]]
        gdf = geom.merge(df, on="cell_id", how="inner")
        gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=crs)
    else:
        raise FileNotFoundError("Could not find ranking_geojson, or ranking_csv + grid_geojson")
    if "cell_id" not in gdf.columns:
        raise KeyError("ranking data must contain cell_id")
    return gdf


def prepare_candidates(cfg: dict) -> gpd.GeoDataFrame:
    crs = cfg.get("working_crs", "EPSG:3414")
    gdf = load_ranking(cfg)
    cell_qa_fp = Path(cfg.get("qa_dir", "outputs/v09_gamma_qa")) / "v09_overhead_structures_per_cell.csv"
    if cell_qa_fp.exists():
        qa = pd.read_csv(cell_qa_fp)
        gdf = gdf.merge(qa[["cell_id", "overhead_fraction_cell", "overhead_confounding_flag"]], on="cell_id", how="left")
    else:
        print(f"[WARN] cell overhead QA missing: {cell_qa_fp}; setting overhead_fraction_cell=0")
        gdf["overhead_fraction_cell"] = 0.0
        gdf["overhead_confounding_flag"] = "unknown"

    gdf["overhead_fraction_cell"] = pd.to_numeric(gdf.get("overhead_fraction_cell", 0), errors="coerce").fillna(0)

    # Ensure rank/score columns exist or create fallbacks.
    if "hazard_rank_true_v08" not in gdf.columns:
        if "hazard_score" in gdf.columns:
            gdf["hazard_rank_true_v08"] = pd.to_numeric(gdf["hazard_score"], errors="coerce").rank(method="min", ascending=False).astype(int)
        elif "rank" in gdf.columns:
            gdf["hazard_rank_true_v08"] = pd.to_numeric(gdf["rank"], errors="coerce")
        else:
            raise KeyError("Need hazard_rank_true_v08, hazard_score, or rank")

    # Useful derived scores.
    for c in ["hazard_score", "road_fraction", "shade_fraction", "svf", "tree_canopy_fraction", "ndvi_mean", "gvi_percent", "risk_priority_score_v08_conditioned", "risk_priority_score_v08_social_conditioned"]:
        if c in gdf.columns:
            gdf[c] = pd.to_numeric(gdf[c], errors="coerce")
    green_cols = [c for c in ["tree_canopy_fraction", "ndvi_mean", "gvi_percent"] if c in gdf.columns]
    if green_cols:
        scaled = [robust01(gdf[c]) for c in green_cols]
        gdf["green_score_for_reference"] = pd.concat(scaled, axis=1).mean(axis=1)
    else:
        gdf["green_score_for_reference"] = 0.0

    if "road_fraction" in gdf.columns:
        road01 = robust01(gdf["road_fraction"])
    else:
        road01 = 0.0
    hazard01 = robust01(-pd.to_numeric(gdf["hazard_rank_true_v08"], errors="coerce"))  # smaller rank = better
    shade_inv = 1 - robust01(gdf["shade_fraction"]) if "shade_fraction" in gdf.columns else 0.0
    green_inv = 1 - gdf["green_score_for_reference"]
    gdf["open_paved_hotspot_score"] = 0.45 * hazard01 + 0.25 * road01 + 0.20 * shade_inv + 0.10 * green_inv

    # Reference score: low hazard rank quality + shade + green + low overhead.
    # Convert high rank number to low hazard score.
    rank = pd.to_numeric(gdf["hazard_rank_true_v08"], errors="coerce")
    gdf["low_hazard_score"] = robust01(rank)
    shade_score = robust01(gdf["shade_fraction"]) if "shade_fraction" in gdf.columns else 0.0
    gdf["reference_score"] = 0.40 * gdf["low_hazard_score"] + 0.30 * shade_score + 0.25 * gdf["green_score_for_reference"] + 0.05 * (1 - robust01(gdf["overhead_fraction_cell"]))

    gdf = add_tile_geometries(gdf, cfg.get("tile_size_m", 500), cfg.get("tile_buffer_m", 100))
    footprint_fp = Path(cfg.get("qa_dir", "outputs/v09_gamma_qa")) / "v09_overhead_structures_footprints.geojson"
    gdf = compute_tile_overhead_fraction(gdf, footprint_fp, crs)
    return gdf


def sort_for_type(df: gpd.GeoDataFrame, tile_type: str) -> gpd.GeoDataFrame:
    d = df.copy()
    if tile_type == "clean_hazard_top":
        return d.sort_values(["hazard_rank_true_v08", "overhead_fraction_cell", "tile_overhead_fraction"])
    if tile_type == "conservative_risk_top":
        col = "risk_rank_v08_conditioned" if "risk_rank_v08_conditioned" in d.columns else "risk_rank_v08_candidate_policy"
        if col in d.columns:
            return d.sort_values([col, "overhead_fraction_cell"])
        return d.sort_values(["hazard_rank_true_v08", "overhead_fraction_cell"])
    if tile_type == "social_risk_top":
        col = "risk_rank_v08_social_conditioned"
        if col in d.columns:
            return d.sort_values([col, "overhead_fraction_cell"])
        return d.sort_values(["hazard_rank_true_v08", "overhead_fraction_cell"])
    if tile_type == "open_paved_hotspot":
        return d.sort_values("open_paved_hotspot_score", ascending=False)
    if tile_type == "clean_shaded_reference":
        return d.sort_values("reference_score", ascending=False)
    if tile_type == "overhead_confounded_hazard_case":
        # High hazard and high overhead, for diagnostic/sensitivity only.
        tmp = d.copy()
        tmp["oh_diag_score"] = robust01(-pd.to_numeric(tmp["hazard_rank_true_v08"], errors="coerce")) * 0.55 + robust01(tmp["overhead_fraction_cell"]) * 0.45
        return tmp.sort_values("oh_diag_score", ascending=False)
    return d


def candidate_filter(df: gpd.GeoDataFrame, cfg: dict, tile_type: str, strictness: int) -> gpd.GeoDataFrame:
    c = df.copy()
    cons = cfg.get("constraints", {})
    # Relax constraints by strictness level.
    clean_focus = cons.get("max_focus_overhead_fraction_clean", 0.02)
    risk_focus = cons.get("max_focus_overhead_fraction_risk", 0.05)
    tile_clean = cons.get("max_tile_overhead_fraction_clean", 0.10)
    tile_ref = cons.get("max_tile_overhead_fraction_reference", 0.05)
    ref_rank = cons.get("reference_min_hazard_rank", 750)

    relax = [1.0, 2.5, 5.0, 999.0][min(strictness, 3)]

    if tile_type in ["clean_hazard_top", "open_paved_hotspot"]:
        c = c[(c["overhead_fraction_cell"] <= clean_focus * relax) & (c["tile_overhead_fraction"] <= tile_clean * relax)]
    elif tile_type in ["conservative_risk_top", "social_risk_top"]:
        c = c[(c["overhead_fraction_cell"] <= risk_focus * relax) & (c["tile_overhead_fraction"] <= max(tile_clean, 0.15) * relax)]
    elif tile_type == "clean_shaded_reference":
        c = c[(c["overhead_fraction_cell"] <= clean_focus * relax) & (c["tile_overhead_fraction"] <= tile_ref * relax)]
        # Require low hazard and high shade/green in strict rounds.
        if strictness <= 1:
            c = c[pd.to_numeric(c["hazard_rank_true_v08"], errors="coerce") >= ref_rank]
            if "shade_fraction" in c.columns:
                q = df["shade_fraction"].quantile(cons.get("reference_min_shade_quantile", 0.75))
                c = c[c["shade_fraction"] >= q]
            if "green_score_for_reference" in c.columns:
                qg = df["green_score_for_reference"].quantile(cons.get("reference_min_green_quantile", 0.75))
                c = c[c["green_score_for_reference"] >= qg]
    elif tile_type == "overhead_confounded_hazard_case":
        c = c[c["overhead_fraction_cell"] >= 0.10]
    return c


def pick_one(df: gpd.GeoDataFrame, cfg: dict, tile_type: str, selected: List[pd.Series]) -> Tuple[Optional[pd.Series], str]:
    min_dist = cfg.get("min_center_distance_m", 550)
    max_iou = cfg.get("max_tile_iou", 0.20)
    sorted_df = sort_for_type(df, tile_type)
    for strictness in range(4):
        candidates = candidate_filter(sorted_df, cfg, tile_type, strictness)
        for _, row in candidates.iterrows():
            if any(row["cell_id"] == r["cell_id"] for r in selected):
                continue
            dist = center_distance(row, selected)
            iou = max_iou_with_selected(row, selected, use_buffered=False)
            # Relax separation on final fallback.
            if strictness < 3 and (dist < min_dist or iou > max_iou):
                continue
            status = ["strict", "relaxed_overhead", "very_relaxed_overhead", "fallback_any_unselected"][strictness]
            return row, status
    return None, "not_found"


def select_tiles(cfg: dict) -> dict:
    out_dir = Path(cfg.get("out_dir", "data/solweig/v09_tiles_overhead_aware"))
    out_dir.mkdir(parents=True, exist_ok=True)
    qa_dir = Path(cfg.get("qa_dir", "outputs/v09_gamma_qa"))
    qa_dir.mkdir(parents=True, exist_ok=True)
    crs = cfg.get("working_crs", "EPSG:3414")

    df = prepare_candidates(cfg)
    selected = []
    rows = []
    tile_types = cfg.get("selection", {}).get("tile_types", [])
    if cfg.get("selection", {}).get("include_overhead_confounded_diagnostic_tile", False):
        tile_types = tile_types + ["overhead_confounded_hazard_case"]

    for i, tt in enumerate(tile_types, start=1):
        row, status = pick_one(df, cfg, tt, selected)
        if row is None:
            print(f"[WARN] no tile found for {tt}")
            continue
        selected.append(row)
        tile_id = f"T{i:02d}_{tt}"
        rec = row.to_dict()
        rec["tile_id"] = tile_id
        rec["tile_type"] = tt
        rec["selection_status"] = status
        rec["min_center_distance_to_previous_m"] = center_distance(row, selected[:-1])
        rec["max_iou_with_previous"] = max_iou_with_selected(row, selected[:-1], use_buffered=False)
        rows.append(rec)
        print(f"[OK] selected {tile_id}: cell={row['cell_id']} status={status} overhead_focus={row['overhead_fraction_cell']:.3f} tile_overhead={row['tile_overhead_fraction']:.3f}")

    if not rows:
        raise RuntimeError("No tiles selected")

    meta = pd.DataFrame(rows)
    # Geometry outputs.
    tiles = gpd.GeoDataFrame(meta.copy(), geometry="tile_geometry", crs=crs)
    tiles_buf = gpd.GeoDataFrame(meta.copy(), geometry="tile_buffered_geometry", crs=crs)

    # Keep only serialisable columns for GeoJSON.
    drop_cols = [c for c in ["geometry", "tile_geometry", "tile_buffered_geometry"] if c in tiles.columns]
    keep_cols = [c for c in tiles.columns if c not in ["geometry", "tile_buffered_geometry"]]
    tiles_out = gpd.GeoDataFrame(tiles[keep_cols], geometry="tile_geometry", crs=crs).rename_geometry("geometry")
    keep_cols_b = [c for c in tiles_buf.columns if c not in ["geometry", "tile_geometry"]]
    tiles_buf_out = gpd.GeoDataFrame(tiles_buf[keep_cols_b], geometry="tile_buffered_geometry", crs=crs).rename_geometry("geometry")

    tiles_fp = out_dir / "v09_solweig_tiles_overhead_aware.geojson"
    tiles_buf_fp = out_dir / "v09_solweig_tiles_overhead_aware_buffered.geojson"
    meta_fp = out_dir / "v09_solweig_tile_metadata_overhead_aware.csv"
    report_fp = out_dir / "v09_solweig_tile_selection_overhead_aware_QA_report.md"

    tiles_out.to_file(tiles_fp, driver="GeoJSON")
    tiles_buf_out.to_file(tiles_buf_fp, driver="GeoJSON")

    # CSV cannot store geometries neatly.
    meta_csv = meta.drop(columns=[c for c in ["geometry", "tile_geometry", "tile_buffered_geometry"] if c in meta.columns], errors="ignore")
    meta_csv.to_csv(meta_fp, index=False)

    warnings = []
    for _, r in meta_csv.iterrows():
        if r.get("selection_status") != "strict":
            warnings.append(f"- {r['tile_id']} selected with `{r['selection_status']}` constraints.")
        if r.get("tile_type") == "clean_shaded_reference" and float(r.get("tile_overhead_fraction", 0)) > cfg.get("constraints", {}).get("max_tile_overhead_fraction_reference", 0.05):
            warnings.append(f"- Reference tile {r['tile_id']} has tile_overhead_fraction={r.get('tile_overhead_fraction'):.3f}; inspect manually.")

    report = "# v0.9-gamma overhead-aware tile selection QA report\n\n"
    report += f"Selected tiles: **{len(meta_csv)}**\n\n"
    report += "## Selected tile summary\n\n"
    summary_cols = ["tile_id", "tile_type", "cell_id", "hazard_rank_true_v08", "risk_rank_v08_conditioned", "risk_rank_v08_social_conditioned", "overhead_fraction_cell", "tile_overhead_fraction", "selection_status", "min_center_distance_to_previous_m", "max_iou_with_previous"]
    summary_cols = [c for c in summary_cols if c in meta_csv.columns]
    report += meta_csv[summary_cols].to_string(index=False) + "\n\n"
    report += "## Warnings\n\n"
    report += "\n".join(warnings) if warnings else "No major warnings.\n"
    report += "\n\n## Interpretation\n\n"
    report += "- Clean tiles are selected with overhead and spatial-separation constraints.\n"
    report += "- `overhead_confounded_hazard_case`, if present, is diagnostic only and should not be interpreted as a clean radiant-exposure tile.\n"
    report += "- Always inspect selected tiles in QGIS before running SOLWEIG.\n"
    report_fp.write_text(report, encoding="utf-8")

    print(f"[OK] tiles: {tiles_fp}")
    print(f"[OK] buffered tiles: {tiles_buf_fp}")
    print(f"[OK] metadata: {meta_fp}")
    print(f"[OK] report: {report_fp}")
    return {"tiles": str(tiles_fp), "buffered": str(tiles_buf_fp), "metadata": str(meta_fp), "report": str(report_fp)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v09_gamma_overhead_aware_config.example.json")
    args = parser.parse_args()
    cfg = load_config(args.config)
    select_tiles(cfg)


if __name__ == "__main__":
    main()
