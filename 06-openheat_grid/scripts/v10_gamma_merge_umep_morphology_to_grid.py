from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def preserve_and_replace(df: pd.DataFrame, old_col: str, new_series: pd.Series, backup_col: str) -> None:
    if old_col in df.columns and backup_col not in df.columns:
        df[backup_col] = df[old_col]
    df[old_col] = new_series


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge v10 UMEP morphology into forecast grid and replace model-input svf/shade/building features.")
    parser.add_argument("--config", default="configs/v10/v10_gamma_umep_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    paths = cfg["paths"]

    base_grid = Path(paths["base_grid_csv"])
    morphology_csv = Path(paths["v10_morphology_csv"])
    basic_morph_csv = Path(paths.get("v10_basic_morphology_csv", ""))
    out_csv = Path(paths["v10_grid_csv"])
    out_geojson = Path(paths["v10_grid_geojson"])
    grid_geojson = Path(paths["grid_geojson"])
    out_dir = Path(paths["output_morphology_dir"])

    if not base_grid.exists():
        raise FileNotFoundError(base_grid)
    if not morphology_csv.exists():
        raise FileNotFoundError(morphology_csv)

    grid = pd.read_csv(base_grid)
    morph = pd.read_csv(morphology_csv)
    if "cell_id" not in grid.columns or "cell_id" not in morph.columns:
        raise KeyError("Both base grid and morphology CSV must contain cell_id")

    # Avoid duplicate stale v10 cols before merge.
    drop_cols = [c for c in morph.columns if c in grid.columns and c != "cell_id"]
    if drop_cols:
        grid = grid.drop(columns=drop_cols)

    out = grid.merge(morph, on="cell_id", how="left")

    # Replace the core model-input morphology fields with v10 UMEP values.
    if "svf_umep_mean_open_v10" not in out.columns:
        raise KeyError("Missing svf_umep_mean_open_v10 in morphology table")
    if "shade_fraction_umep_10_16_open_v10" not in out.columns:
        raise KeyError("Missing shade_fraction_umep_10_16_open_v10 in morphology table")

    preserve_and_replace(out, "svf", out["svf_umep_mean_open_v10"], "svf_v08_umep_veg")
    preserve_and_replace(out, "shade_fraction", out["shade_fraction_umep_10_16_open_v10"], "shade_fraction_v08_umep_veg")

    # Merge v10 basic building morphology and replace building_density / heights where available.
    if basic_morph_csv.exists():
        bm = pd.read_csv(basic_morph_csv)
        keep = [
            "cell_id",
            "v10_building_density",
            "v10_building_area_m2",
            "v10_open_pixel_fraction",
            "v10_building_height_mean_m",
            "v10_building_height_max_m",
            "v10_building_height_p50_m",
            "v10_building_height_p90_m",
        ]
        keep = [c for c in keep if c in bm.columns]
        # Drop stale if exists.
        stale = [c for c in keep if c in out.columns and c != "cell_id"]
        if stale:
            out = out.drop(columns=stale)
        out = out.merge(bm[keep], on="cell_id", how="left")

        if "v10_building_density" in out.columns:
            preserve_and_replace(out, "building_density", out["v10_building_density"], "building_density_v08")
        if "v10_building_height_mean_m" in out.columns:
            if "mean_building_height_m" in out.columns and "mean_building_height_m_v08" not in out.columns:
                out["mean_building_height_m_v08"] = out["mean_building_height_m"]
            out["mean_building_height_m"] = out["v10_building_height_mean_m"]
        if "v10_building_height_max_m" in out.columns:
            if "max_building_height_m" in out.columns and "max_building_height_m_v08" not in out.columns:
                out["max_building_height_m_v08"] = out["max_building_height_m"]
            out["max_building_height_m"] = out["v10_building_height_max_m"]

    out["svf_source_v10"] = "UMEP_SVF_reviewed_building_DSM_with_vegetation"
    out["shade_source_v10"] = "UMEP_shadow_reviewed_building_DSM_with_vegetation"
    out["building_source_v10"] = "reviewed_augmented_HDB3D_URA_OSM_manual_DSM"
    out["umep_morphology_version"] = "v10_reviewed_dsm_with_veg"
    out["delta_svf_v10_minus_v08"] = out["svf"] - out.get("svf_v08_umep_veg", pd.NA)
    out["delta_shade_v10_minus_v08"] = out["shade_fraction"] - out.get("shade_fraction_v08_umep_veg", pd.NA)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)

    if grid_geojson.exists():
        geom = gpd.read_file(grid_geojson)[["cell_id", "geometry"]]
        gout = geom.merge(out, on="cell_id", how="inner")
        gout = gpd.GeoDataFrame(gout, geometry="geometry", crs=gpd.read_file(grid_geojson).crs)
        gout.to_file(out_geojson, driver="GeoJSON")

    # QA report.
    out_dir.mkdir(parents=True, exist_ok=True)
    report = []
    report.append("# v10-gamma grid merge QA report\n")
    report.append(f"Base grid: `{base_grid}`\n")
    report.append(f"Morphology CSV: `{morphology_csv}`\n")
    report.append(f"Output grid CSV: `{out_csv}`\n")
    report.append("## Key column summaries\n")
    cols = [
        "svf", "svf_v08_umep_veg", "delta_svf_v10_minus_v08",
        "shade_fraction", "shade_fraction_v08_umep_veg", "delta_shade_v10_minus_v08",
        "building_density", "building_density_v08", "v10_building_density",
        "mean_building_height_m", "mean_building_height_m_v08",
    ]
    cols = [c for c in cols if c in out.columns]
    report.append("```text")
    report.append(out[cols].describe().to_string())
    report.append("```\n")
    report.append("## Missing values\n")
    report.append("```text")
    report.append(out[["svf", "shade_fraction", "building_density"]].isna().sum().to_string())
    report.append("```\n")
    report_path = out_dir / "v10_gamma_grid_merge_QA_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] v10 grid CSV: {out_csv}")
    print(f"[OK] v10 grid GeoJSON: {out_geojson}")
    print(f"[OK] QA report: {report_path}")


if __name__ == "__main__":
    main()
