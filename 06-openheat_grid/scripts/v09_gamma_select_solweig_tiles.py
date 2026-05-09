"""
OpenHeat v0.9-gamma hotfix
Select representative SOLWEIG tiles from v0.8 risk scenarios.

Hotfixes:
- reference tile is selected using low hazard + high shade/NDVI preference
- emits QA warning if reference tile is not in the intended low-hazard tail
- removes previous dead-code pattern by centralising ranking-column lookup
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import numpy as np
import pandas as pd

WORKING_CRS = "EPSG:3414"
DEFAULT_CONFIG = "configs/v09_gamma_solweig_config.example.json"
DEFAULT_RANKING_GEOJSON = "outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_rankings.geojson"
DEFAULT_OUT_DIR = "data/solweig/v09_tiles"
TILE_SIZE_M = 500
BUFFER_M = 100
MIN_REFERENCE_RANK = 750

SCENARIOS = [
    ("T01", "hazard_top", "hazard_rank_true_v08"),
    ("T02", "conservative_risk_top", "risk_rank_v08_conditioned"),
    ("T03", "social_risk_top", "risk_rank_v08_social_conditioned"),
    ("T04", "candidate_policy_top", "risk_rank_v08_candidate_policy"),
]


def read_json(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def get_path(cfg: Dict[str, Any], *keys: str, default: str) -> str:
    paths = cfg.get("paths", {}) if isinstance(cfg, dict) else {}
    for key in keys:
        if key in paths and paths[key]:
            return str(paths[key])
        if key in cfg and cfg[key]:
            return str(cfg[key])
    return default


def square_around_point(pt, size_m: float):
    half = size_m / 2.0
    return pt.buffer(half, cap_style=3)  # square


def pick_top_unused(df: gpd.GeoDataFrame, rank_col: str, used: set) -> pd.Series:
    if rank_col not in df.columns:
        raise KeyError(f"Missing rank column: {rank_col}")
    cand = df[~df["cell_id"].isin(used)].copy()
    cand = cand.sort_values(rank_col, ascending=True)
    if cand.empty:
        raise ValueError("No unused cells available for tile selection")
    return cand.iloc[0]


def pick_reference(df: gpd.GeoDataFrame, used: set, min_rank: int) -> pd.Series:
    work = df[~df["cell_id"].isin(used)].copy()
    if "hazard_rank_true_v08" not in work.columns:
        raise KeyError("hazard_rank_true_v08 is required for reference selection")
    # Preferred: low hazard tail + high shade + high NDVI/GVI.
    pref = work[work["hazard_rank_true_v08"] >= min_rank].copy()
    if not pref.empty:
        for col in ["shade_fraction", "ndvi_mean", "gvi_percent"]:
            if col not in pref.columns:
                pref[col] = 0.0
        pref["reference_score"] = (
            0.50 * pref["hazard_rank_true_v08"].rank(pct=True)
            + 0.30 * pref["shade_fraction"].rank(pct=True)
            + 0.15 * pref["ndvi_mean"].rank(pct=True)
            + 0.05 * pref["gvi_percent"].rank(pct=True)
        )
        return pref.sort_values("reference_score", ascending=False).iloc[0]
    # Fallback: least hazardous unused cell.
    return work.sort_values("hazard_rank_true_v08", ascending=False).iloc[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--ranking-geojson", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--tile-size-m", type=float, default=None)
    parser.add_argument("--buffer-m", type=float, default=None)
    parser.add_argument("--min-reference-rank", type=int, default=None)
    args = parser.parse_args()

    cfg = read_json(args.config)
    ranking_fp = Path(args.ranking_geojson or get_path(cfg, "risk_scenario_geojson", "ranking_geojson", default=DEFAULT_RANKING_GEOJSON))
    out_dir = Path(args.out_dir or get_path(cfg, "tile_root", "tile_dir", "tiles_dir", default=DEFAULT_OUT_DIR))
    tile_size = args.tile_size_m or float(cfg.get("tile_size_m", TILE_SIZE_M))
    buffer_m = args.buffer_m or float(cfg.get("tile_buffer_m", BUFFER_M))
    min_ref = args.min_reference_rank or int(cfg.get("min_reference_hazard_rank", MIN_REFERENCE_RANK))

    if not ranking_fp.exists():
        raise FileNotFoundError(f"Ranking GeoJSON not found: {ranking_fp}")
    gdf = gpd.read_file(ranking_fp)
    if gdf.crs is None:
        gdf = gdf.set_crs(WORKING_CRS)
    else:
        gdf = gdf.to_crs(WORKING_CRS)
    if "cell_id" not in gdf.columns:
        raise KeyError("cell_id column is required")

    used: set = set()
    rows: List[Dict[str, Any]] = []
    tile_geoms = []
    buffered_geoms = []

    for tile_id, tile_type, rank_col in SCENARIOS:
        row = pick_top_unused(gdf, rank_col, used)
        used.add(row["cell_id"])
        pt = row.geometry.centroid
        geom = square_around_point(pt, tile_size)
        buf = geom.buffer(buffer_m)
        rec = {c: row[c] for c in gdf.columns if c != "geometry"}
        rec.update({
            "tile_id": tile_id,
            "tile_type": tile_type,
            "focus_cell_id": row["cell_id"],
            "selection_rank_column": rank_col,
            "tile_size_m": tile_size,
            "tile_buffer_m": buffer_m,
            "reference_selection_status": "not_reference",
            "reference_warning": "",
        })
        rows.append(rec)
        tile_geoms.append(geom)
        buffered_geoms.append(buf)

    ref_row = pick_reference(gdf, used, min_ref)
    pt = ref_row.geometry.centroid
    ref_geom = square_around_point(pt, tile_size)
    ref_buf = ref_geom.buffer(buffer_m)
    ref_rank = float(ref_row.get("hazard_rank_true_v08", np.nan))
    status = "preferred_low_hazard_reference" if ref_rank >= min_ref else "fallback_reference_not_low_hazard_tail"
    warning = "" if ref_rank >= min_ref else f"Reference hazard rank {ref_rank} is below requested minimum {min_ref}; inspect manually."
    rec = {c: ref_row[c] for c in gdf.columns if c != "geometry"}
    rec.update({
        "tile_id": "T05",
        "tile_type": "shaded_reference",
        "focus_cell_id": ref_row["cell_id"],
        "selection_rank_column": "hazard_rank_true_v08 + shade/NDVI preference",
        "tile_size_m": tile_size,
        "tile_buffer_m": buffer_m,
        "reference_selection_status": status,
        "reference_warning": warning,
    })
    rows.append(rec)
    tile_geoms.append(ref_geom)
    buffered_geoms.append(ref_buf)

    meta = pd.DataFrame(rows)
    tiles = gpd.GeoDataFrame(meta.copy(), geometry=tile_geoms, crs=WORKING_CRS)
    tiles_buf = gpd.GeoDataFrame(meta.copy(), geometry=buffered_geoms, crs=WORKING_CRS)

    out_dir.mkdir(parents=True, exist_ok=True)
    meta_fp = out_dir / "v09_solweig_tile_metadata.csv"
    tiles_fp = out_dir / "v09_solweig_tiles.geojson"
    tiles_buf_fp = out_dir / "v09_solweig_tiles_buffered.geojson"
    meta.to_csv(meta_fp, index=False)
    tiles.to_file(tiles_fp, driver="GeoJSON")
    tiles_buf.to_file(tiles_buf_fp, driver="GeoJSON")

    print(f"[OK] metadata: {meta_fp}")
    print(f"[OK] tiles: {tiles_fp}")
    print(f"[OK] buffered tiles: {tiles_buf_fp}")
    print(meta[["tile_id", "tile_type", "focus_cell_id", "hazard_rank_true_v08", "reference_selection_status", "reference_warning"]].to_string(index=False))
    if warning:
        print(f"[WARN] {warning}")


if __name__ == "__main__":
    main()
