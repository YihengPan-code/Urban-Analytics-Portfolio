"""
Finalize v0.8-beta UMEP-with-vegetation forecast outputs.

Patch notes (v0.8-beta review hotfix):
- Warns when expected explanatory columns are missing instead of silently skipping.
- Avoids _x/_y collisions when merging grid explanatory columns into ranking.
- Writes QGIS-ready GeoJSON using geometry-safe inner merge and reports missing geometry cells.
- Writes missing-column and missing-geometry diagnostics to the QA report.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None


EXPLANATORY_COLS = [
    "cell_id",
    "lat",
    "lon",
    "land_use_hint",
    "building_density",
    "road_fraction",
    "park_distance_m",
    "large_park_distance_m",
    "gvi_percent",
    "tree_canopy_fraction",
    "grass_fraction",
    "water_fraction",
    "built_up_fraction",
    "ndvi_mean",
    "impervious_fraction",
    "mean_building_height_m",
    "max_building_height_m",
    "svf",
    "shade_fraction",
    "svf_proxy_v07",
    "shade_fraction_proxy_v07",
    "delta_svf_v08_minus_proxy",
    "delta_shade_v08_minus_proxy",
    "svf_umep_mean_open_with_veg",
    "svf_umep_p10_open_with_veg",
    "svf_umep_p90_open_with_veg",
    "shade_fraction_umep_10_16_open_with_veg",
    "shade_fraction_umep_13_15_open_with_veg",
    "shade_fraction_umep_peak_open_with_veg",
    "open_pixel_fraction",
    "building_pixel_fraction",
    "dsm_mean_height_all",
    "dsm_max_height",
    "umep_includes_vegetation",
    "veg_canopy_source",
    "veg_transmissivity_pct",
    "veg_trunk_zone_pct",
    "elderly_pct_65plus",
    "children_pct_under5",
    "vulnerability_score_v071",
    "outdoor_exposure_score_v071",
    "risk_priority_score_v071_conditioned",
    "risk_rank_v071_conditioned",
]

# Alternative columns that may appear in intermediate v0.7.1 outputs.
# These are not forced into canonical names because their semantics can differ;
# they are included for diagnostics and reporting when present.
FALLBACK_EXPLANATORY_COLS = [
    "risk_priority_score_v071",
    "risk_rank_v071",
    "risk_priority_score_v071_additive",
    "risk_priority_score_v071_gated",
    "risk_rank_v071_gated",
]


NUMERIC_QA_COLS = [
    "max_utci_c",
    "max_wbgt_proxy_c",
    "hazard_score",
    "risk_priority_score",
    "risk_priority_score_v071_conditioned",
    "risk_priority_score_v071",
    "svf",
    "shade_fraction",
    "svf_proxy_v07",
    "shade_fraction_proxy_v07",
    "gvi_percent",
    "ndvi_mean",
    "tree_canopy_fraction",
    "road_fraction",
    "building_density",
]


def _print_columns(title: str, cols: Iterable[str]) -> None:
    print(f"\n[{title}]")
    for c in cols:
        print("  -", c)


def _diagnose_columns(grid: pd.DataFrame, ranking: pd.DataFrame) -> dict[str, list[str]]:
    expected = set(EXPLANATORY_COLS) - {"cell_id"}
    present_grid = set(grid.columns)
    present_ranking = set(ranking.columns)
    missing_grid = sorted(expected - present_grid)
    already_in_ranking = sorted(expected & present_ranking)
    fallback_present = sorted([c for c in FALLBACK_EXPLANATORY_COLS if c in present_grid or c in present_ranking])

    if missing_grid:
        print(f"[WARN] Expected explanatory cols missing from grid ({len(missing_grid)}): {missing_grid}")
    else:
        print("[OK] All expected explanatory cols are present in grid.")
    if fallback_present:
        print(f"[INFO] Found fallback / alternative risk columns: {fallback_present}")
    if already_in_ranking:
        print(f"[INFO] Ranking already contains some explanatory cols; will not duplicate: {already_in_ranking}")

    return {
        "missing_grid": missing_grid,
        "already_in_ranking": already_in_ranking,
        "fallback_present": fallback_present,
    }


def _merge_no_collision(ranking: pd.DataFrame, grid: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    diagnostics = _diagnose_columns(grid, ranking)
    desired = EXPLANATORY_COLS + FALLBACK_EXPLANATORY_COLS
    keep = [c for c in desired if c in grid.columns and (c == "cell_id" or c not in ranking.columns)]
    if "cell_id" not in keep:
        keep = ["cell_id"] + keep
    keep = list(dict.fromkeys(keep))  # preserve order, remove duplicates
    out = ranking.merge(grid[keep].drop_duplicates("cell_id"), on="cell_id", how="left")
    return out, diagnostics


def _write_report(out: pd.DataFrame, out_md: Path, diagnostics: dict[str, list[str]], geojson_stats: dict[str, object] | None = None) -> None:
    top = out.nsmallest(20, "rank") if "rank" in out.columns else out.head(20)
    lines = ["# OpenHeat v0.8-beta UMEP-with-vegetation forecast QA", ""]
    lines.append(f"Rows: **{len(out)}**")
    lines.append("")

    lines.append("## Column diagnostics")
    missing = diagnostics.get("missing_grid", [])
    if missing:
        lines.append(f"- Missing expected grid explanatory columns: `{missing}`")
    else:
        lines.append("- Missing expected grid explanatory columns: none")
    alt = diagnostics.get("fallback_present", [])
    lines.append(f"- Alternative / fallback risk columns present: `{alt}`")
    lines.append(f"- Columns already present in ranking and not duplicated: `{diagnostics.get('already_in_ranking', [])}`")
    lines.append("")

    if geojson_stats is not None:
        lines.append("## GeoJSON diagnostics")
        lines.append(f"- Ranking rows: {geojson_stats.get('ranking_rows')}")
        lines.append(f"- Geometry rows matched: {geojson_stats.get('matched_geometry_rows')}")
        lines.append(f"- Ranking rows without geometry: {geojson_stats.get('missing_geometry_count')}")
        if geojson_stats.get("missing_geometry_examples"):
            lines.append(f"- Missing-geometry example cell_ids: `{geojson_stats.get('missing_geometry_examples')}`")
        lines.append("")

    lines.append("## Feature summaries")
    for c in NUMERIC_QA_COLS:
        if c in out.columns:
            s = pd.to_numeric(out[c], errors="coerce")
            t = pd.to_numeric(top[c], errors="coerce")
            lines.append(
                f"- `{c}` all mean={s.mean():.4f}, top20 mean={t.mean():.4f}, "
                f"all median={s.median():.4f}, top20 median={t.median():.4f}, "
                f"missing={int(s.isna().sum())}"
            )
    lines.append("")
    lines.append("## Top 20")
    cols = [
        c
        for c in [
            "rank",
            "cell_id",
            "max_utci_c",
            "max_wbgt_proxy_c",
            "hazard_score",
            "risk_priority_score",
            "svf",
            "shade_fraction",
            "svf_proxy_v07",
            "shade_fraction_proxy_v07",
            "gvi_percent",
            "ndvi_mean",
            "risk_rank_v071_conditioned",
            "risk_priority_score_v071_conditioned",
        ]
        if c in out.columns
    ]
    lines.append(top[cols].to_string(index=False))
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")


def _write_geojson(out: pd.DataFrame, grid_geojson: Path, out_geojson: Path, missing_csv: Path) -> dict[str, object]:
    if gpd is None:
        print("[WARN] geopandas unavailable; skipped GeoJSON")
        return {"ranking_rows": len(out), "matched_geometry_rows": 0, "missing_geometry_count": None, "missing_geometry_examples": []}
    if not grid_geojson.exists():
        print(f"[WARN] grid_geojson missing: {grid_geojson}; skipped GeoJSON")
        return {"ranking_rows": len(out), "matched_geometry_rows": 0, "missing_geometry_count": None, "missing_geometry_examples": []}

    geom = gpd.read_file(grid_geojson)[["cell_id", "geometry"]].drop_duplicates("cell_id")
    geom_ids = set(geom["cell_id"])
    out_ids = set(out["cell_id"])
    missing_ids = sorted(out_ids - geom_ids)
    if missing_ids:
        print(f"[WARN] {len(missing_ids)} ranking cell_ids have no geometry; they will be excluded from GeoJSON.")
        pd.DataFrame({"cell_id": missing_ids}).to_csv(missing_csv, index=False)
        print("missing geometry csv:", missing_csv)

    # Inner merge prevents null-geometry features in the GeoJSON.
    gout = geom.merge(out, on="cell_id", how="inner")
    before = len(gout)
    gout = gout[gout.geometry.notna()].copy()
    after = len(gout)
    if after < before:
        print(f"[WARN] Dropped {before-after} null geometries after inner merge.")
    gout = gpd.GeoDataFrame(gout, geometry="geometry", crs=geom.crs)
    gout.to_file(out_geojson, driver="GeoJSON")
    print("geojson:", out_geojson)

    return {
        "ranking_rows": len(out),
        "matched_geometry_rows": len(gout),
        "missing_geometry_count": len(missing_ids),
        "missing_geometry_examples": missing_ids[:20],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast-dir", default="outputs/v08_umep_with_veg_forecast_live")
    parser.add_argument("--grid-csv", default="data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv")
    parser.add_argument("--grid-geojson", default="data/grid/toa_payoh_grid_v07_features.geojson")
    parser.add_argument("--out-prefix", default="v08_umep_with_veg")
    args = parser.parse_args()

    forecast_dir = Path(args.forecast_dir)
    ranking_path = forecast_dir / "v06_live_hotspot_ranking.csv"
    if not ranking_path.exists():
        raise FileNotFoundError(f"Ranking not found: {ranking_path}")
    grid_csv = Path(args.grid_csv)
    if not grid_csv.exists():
        raise FileNotFoundError(f"Grid CSV not found: {grid_csv}")

    ranking = pd.read_csv(ranking_path)
    grid = pd.read_csv(grid_csv)
    _print_columns("ranking columns", ranking.columns.tolist())
    _print_columns("grid columns", grid.columns.tolist())

    out, diagnostics = _merge_no_collision(ranking, grid)

    out_csv = forecast_dir / f"{args.out_prefix}_hotspot_ranking_with_grid_features.csv"
    out.to_csv(out_csv, index=False)

    out_geojson = forecast_dir / f"{args.out_prefix}_hotspot_ranking_with_grid_features.geojson"
    missing_csv = forecast_dir / f"{args.out_prefix}_missing_geometry_cell_ids.csv"
    geojson_stats = _write_geojson(out, Path(args.grid_geojson), out_geojson, missing_csv)

    out_md = forecast_dir / f"{args.out_prefix}_hotspot_QA_report.md"
    _write_report(out, out_md, diagnostics, geojson_stats)

    print("[OK] Finalized v0.8-beta UMEP-with-veg forecast outputs")
    print("csv:", out_csv)
    print("report:", out_md)


if __name__ == "__main__":
    main()
