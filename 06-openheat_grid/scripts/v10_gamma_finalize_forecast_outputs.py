from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize v10-gamma forecast outputs by merging explanatory grid features and GeoJSON geometry.")
    parser.add_argument("--config", default="configs/v10/v10_gamma_umep_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    paths = cfg["paths"]
    forecast_dir = Path(paths["forecast_dir"])
    ranking_path = forecast_dir / "v06_live_hotspot_ranking.csv"
    grid_csv = Path(paths["v10_grid_csv"])
    grid_geojson = Path(paths["grid_geojson"])

    if not ranking_path.exists():
        raise FileNotFoundError(f"Ranking not found: {ranking_path}. Run run_live_forecast_v06.py first.")
    if not grid_csv.exists():
        raise FileNotFoundError(grid_csv)

    rank = pd.read_csv(ranking_path)
    grid = pd.read_csv(grid_csv)
    if "cell_id" not in rank.columns or "cell_id" not in grid.columns:
        raise KeyError("ranking and grid must contain cell_id")

    explanatory_cols = [
        "cell_id", "svf", "shade_fraction", "svf_v08_umep_veg", "shade_fraction_v08_umep_veg",
        "delta_svf_v10_minus_v08", "delta_shade_v10_minus_v08",
        "building_density", "building_density_v08", "v10_building_density",
        "v10_building_area_m2", "v10_open_pixel_fraction",
        "mean_building_height_m", "mean_building_height_m_v08", "max_building_height_m", "max_building_height_m_v08",
        "tree_canopy_fraction", "ndvi_mean", "gvi_percent", "road_fraction", "impervious_fraction",
        "elderly_pct_65plus", "children_pct_under5", "vulnerability_score_v071", "outdoor_exposure_score_v071",
        "dominant_subzone", "land_use_hint", "umep_morphology_version", "svf_source_v10", "shade_source_v10", "building_source_v10"
    ]
    present = [c for c in explanatory_cols if c in grid.columns]
    missing = [c for c in explanatory_cols if c not in grid.columns and c != "cell_id"]

    # Avoid duplicate columns already in ranking.
    merge_cols = ["cell_id"] + [c for c in present if c != "cell_id" and c not in rank.columns]
    out = rank.merge(grid[merge_cols], on="cell_id", how="left")

    out_csv = forecast_dir / "v10_gamma_hotspot_ranking_with_grid_features.csv"
    out.to_csv(out_csv, index=False)

    geojson_path = forecast_dir / "v10_gamma_hotspot_ranking_with_grid_features.geojson"
    missing_geom = []
    if grid_geojson.exists():
        geom = gpd.read_file(grid_geojson)[["cell_id", "geometry"]].drop_duplicates("cell_id")
        gout = geom.merge(out, on="cell_id", how="inner")
        missing_geom = sorted(set(out["cell_id"]) - set(gout["cell_id"]))
        gout = gpd.GeoDataFrame(gout, geometry="geometry", crs=gpd.read_file(grid_geojson).crs)
        gout = gout[gout.geometry.notna()].copy()
        gout.to_file(geojson_path, driver="GeoJSON")

    report = []
    report.append("# v10-gamma forecast finalisation QA report\n")
    report.append(f"Ranking rows: **{len(rank)}**\n")
    report.append(f"Output rows: **{len(out)}**\n")
    report.append(f"CSV: `{out_csv}`\n")
    report.append(f"GeoJSON: `{geojson_path}`\n")
    report.append("## Missing expected explanatory columns from grid\n")
    report.append("```text")
    report.extend(missing or ["None"])
    report.append("```\n")
    report.append("## GeoJSON diagnostics\n")
    report.append("```text")
    report.append(f"missing_geometry_rows: {len(missing_geom)}")
    if missing_geom[:10]:
        report.append(f"examples: {missing_geom[:10]}")
    report.append("```\n")
    summary_cols = ["max_utci_c", "max_wbgt_proxy_c", "hazard_score", "risk_priority_score", "svf", "shade_fraction", "building_density"]
    summary_cols = [c for c in summary_cols if c in out.columns]
    report.append("## Feature summaries\n")
    report.append("```text")
    report.append(out[summary_cols].describe().to_string())
    report.append("```\n")
    report_path = forecast_dir / "v10_gamma_hotspot_QA_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] CSV: {out_csv}")
    print(f"[OK] GeoJSON: {geojson_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
