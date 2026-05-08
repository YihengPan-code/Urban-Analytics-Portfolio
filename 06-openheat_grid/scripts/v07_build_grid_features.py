from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openheat_grid.grid import load_aoi, make_square_grid, write_grid_outputs
from openheat_grid.geospatial import read_vector, clip_to_aoi, SVY21, WGS84
from openheat_grid.features import (
    building_density,
    road_fraction,
    park_distances,
    nearest_polygon_distance,
    land_use_majority,
    merge_optional_feature_csv,
    apply_height_proxy,
    derive_greenery_proxy,
    derive_morphology_proxies,
    final_forecast_grid_columns,
)
from openheat_grid.provenance import write_provenance


def load_config(path: str | Path) -> dict:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def maybe_read_vector(path: str | None, aoi: gpd.GeoDataFrame, buffer_m: float = 1000) -> gpd.GeoDataFrame | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Configured vector path does not exist: {p}")
    gdf = read_vector(p, target_crs=SVY21)
    return clip_to_aoi(gdf, aoi, buffer_m=buffer_m)


def write_feature(df: pd.DataFrame, out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / f"{name}.csv", index=False)


def plot_preview(features_geo: gpd.GeoDataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 7))
    col = "building_density" if "building_density" in features_geo.columns else None
    features_geo.plot(column=col, ax=ax, legend=True, edgecolor="black", linewidth=0.2, cmap="viridis")
    ax.set_title("OpenHeat v0.7 grid feature preview: building_density")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def build_grid_features(config: dict) -> dict:
    out_grid_dir = ROOT / config.get("out_grid_dir", "data/grid")
    out_features_dir = ROOT / config.get("out_features_dir", "data/features")
    out_prov_dir = out_features_dir / "provenance"
    out_outputs_dir = ROOT / config.get("out_outputs_dir", "outputs")
    cell_size_m = float(config.get("cell_size_m", 100))
    prefix = str(config.get("cell_id_prefix", "TP"))

    aoi = load_aoi(config)
    grid = make_square_grid(aoi, cell_size_m=cell_size_m, prefix=prefix)
    write_grid_outputs(grid, out_grid_dir / "toa_payoh_grid_v07.geojson", out_grid_dir / "toa_payoh_grid_v07.csv")

    raw = config.get("raw_paths", {})
    buildings = maybe_read_vector(raw.get("buildings"), aoi, buffer_m=200) if raw.get("buildings") else None
    land_use = maybe_read_vector(raw.get("land_use"), aoi, buffer_m=200) if raw.get("land_use") else None
    parks = maybe_read_vector(raw.get("parks"), aoi, buffer_m=2000) if raw.get("parks") else None
    roads = maybe_read_vector(raw.get("roads"), aoi, buffer_m=200) if raw.get("roads") else None
    water = maybe_read_vector(raw.get("water"), aoi, buffer_m=2000) if raw.get("water") else None

    pieces: list[pd.DataFrame] = [grid[["cell_id", "lat", "lon", "centroid_x_svy21", "centroid_y_svy21", "cell_area_m2"]].copy()]

    bd = building_density(grid, buildings)
    write_feature(bd, out_features_dir, "building_density")
    pieces.append(bd)
    write_provenance(out_prov_dir / "building_density.yaml", feature="building_density", source=raw.get("buildings", "missing; filled as 0"), method="Areal intersection between 100 m SVY21 grid and building footprints; area / cell_area", unit="dimensionless [0,1]", known_issues=["v0.7-alpha uses indicative footprints; no height considered"])

    lu = land_use_majority(grid, land_use, lu_col=config.get("land_use_column", "LU_DESC"), gpr_col=config.get("gpr_column", "GPR"))
    write_feature(lu, out_features_dir, "land_use_hint")
    pieces.append(lu)
    write_provenance(out_prov_dir / "land_use_hint.yaml", feature="land_use_hint", source=raw.get("land_use", "missing; filled as unknown"), method="Area-majority land-use class within each grid cell, simplified to broad categories", unit="categorical", known_issues=["Master Plan land use is planning-zoning information, not observed activity"])

    rf = road_fraction(grid, roads, buffer_m=float(config.get("road_buffer_m", 7.0)))
    write_feature(rf, out_features_dir, "road_fraction")
    pieces.append(rf)
    write_provenance(out_prov_dir / "road_fraction.yaml", feature="road_fraction", source=raw.get("roads", "missing; filled as 0"), method="Road LineStrings buffered then intersected with grid; polygons are intersected directly", unit="dimensionless [0,1]", known_issues=["Buffer width is a v0.7-alpha approximation"])

    pdist = park_distances(grid, parks, large_park_threshold_ha=float(config.get("large_park_threshold_ha", 10.0)))
    write_feature(pdist, out_features_dir, "park_distances")
    pieces.append(pdist)
    write_provenance(out_prov_dir / "park_distance_m.yaml", feature="park_distance_m / large_park_distance_m", source=raw.get("parks", "missing; filled as 9999"), method="Centroid-to-nearest park polygon distance in SVY21; large parks filtered by area threshold", unit="metres", known_issues=["Distance is geometric and does not capture wind direction or park morphology"])

    if water is not None:
        wdist = nearest_polygon_distance(grid, water, "water_distance_m")
    else:
        wdist = pd.DataFrame({"cell_id": grid["cell_id"].astype(str), "water_distance_m": 9999.0, "nearest_water_name": None})
    write_feature(wdist, out_features_dir, "water_distance")
    pieces.append(wdist)

    # Merge base vector features.
    feat = pieces[0]
    for p in pieces[1:]:
        feat = feat.merge(p, on="cell_id", how="left")

    # Optional external CSV features exported from GEE/other tools.
    optional = config.get("optional_feature_csv", {})
    feat = merge_optional_feature_csv(feat, optional.get("height"), ["mean_building_height_m"] if optional.get("height") else [])
    # max height is optional; merge it separately if present in same height CSV.
    if optional.get("height"):
        hdf = pd.read_csv(optional.get("height"))
        optional_cols = [c for c in ["max_building_height_m", "height_source"] if c in hdf.columns]
        if optional_cols:
            feat = feat.merge(hdf[["cell_id", *optional_cols]], on="cell_id", how="left")
    feat = merge_optional_feature_csv(feat, optional.get("vegetation"), ["tree_canopy_fraction"] if optional.get("vegetation") else [])
    if optional.get("vegetation"):
        vdf = pd.read_csv(optional.get("vegetation"))
        optional_cols = [c for c in ["ndvi_mean", "built_up_fraction", "grass_fraction", "water_fraction", "tree_canopy_source"] if c in vdf.columns]
        if optional_cols:
            feat = feat.merge(vdf[["cell_id", *optional_cols]], on="cell_id", how="left")

    feat = apply_height_proxy(feat)
    feat = derive_greenery_proxy(feat)
    feat = derive_morphology_proxies(feat, cell_size_m=cell_size_m)
    feat["forecast_spatial_note"] = "Open-Meteo supplies background meteorology; intra-neighbourhood spatial variation comes from v0.7 grid features/statistical downscaling proxies."

    final_csv = final_forecast_grid_columns(feat)
    out_grid_dir.mkdir(parents=True, exist_ok=True)
    final_csv.to_csv(out_grid_dir / "toa_payoh_grid_v07_features.csv", index=False)

    grid_geo = grid.merge(feat, on=["cell_id", "lat", "lon", "centroid_x_svy21", "centroid_y_svy21", "cell_area_m2"], how="left")
    grid_geo.to_crs(WGS84).to_file(out_grid_dir / "toa_payoh_grid_v07_features.geojson", driver="GeoJSON")
    plot_preview(grid_geo, out_outputs_dir / "v07_grid_feature_preview.png")

    report = make_qa_report(final_csv, config)
    (out_outputs_dir / "v07_grid_features_QA_report.md").write_text(report, encoding="utf-8")

    return {
        "grid_geojson": out_grid_dir / "toa_payoh_grid_v07.geojson",
        "features_csv": out_grid_dir / "toa_payoh_grid_v07_features.csv",
        "features_geojson": out_grid_dir / "toa_payoh_grid_v07_features.geojson",
        "qa_report": out_outputs_dir / "v07_grid_features_QA_report.md",
        "preview_png": out_outputs_dir / "v07_grid_feature_preview.png",
    }


def make_qa_report(df: pd.DataFrame, config: dict) -> str:
    lines = ["# OpenHeat v0.7 grid features QA report", ""]
    lines.append(f"Rows / grid cells: **{len(df)}**")
    lines.append(f"Cell size: **{config.get('cell_size_m', 100)} m**")
    lines.append("")
    for col in ["building_density", "road_fraction", "park_distance_m", "large_park_distance_m", "mean_building_height_m", "svf", "shade_fraction", "gvi_percent", "tree_canopy_fraction", "impervious_fraction"]:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            lines.append(f"- `{col}`: missing={int(s.isna().sum())}, min={s.min():.3f}, mean={s.mean():.3f}, max={s.max():.3f}")
    if "land_use_hint" in df.columns:
        lines.append("")
        lines.append("## land_use_hint counts")
        counts = df["land_use_hint"].value_counts(dropna=False)
        for k, v in counts.items():
            lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Interpretation notes")
    lines.append("- `svf`, `shade_fraction`, and `gvi_percent` are screening-level proxies in v0.7-alpha unless replaced by external UMEP/GVI-derived CSVs.")
    lines.append("- This file is designed to replace `data/sample/toa_payoh_grid_sample.csv` for forecast workflow testing.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build OpenHeat v0.7 real-grid feature table")
    parser.add_argument("--config", default=str(ROOT / "configs/v07_grid_features_config.example.json"))
    args = parser.parse_args()
    cfg = load_config(args.config)
    files = build_grid_features(cfg)
    print("[OK] v0.7 grid features built")
    for k, v in files.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
