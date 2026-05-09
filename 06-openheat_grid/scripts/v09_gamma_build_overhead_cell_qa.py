"""
OpenHeat v0.9-gamma overhead-infrastructure cell QA.

Purpose
-------
Quantify overhead structures (covered walkways, pedestrian bridges,
elevated roads/rail/viaducts) at the 100m grid-cell level. This is used
before SOLWEIG selected-tile runs to avoid interpreting overhead-confounded
cells as clean building+canopy heat-exposure cases.

Inputs are configured in configs/v09_gamma_overhead_aware_config.example.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import geopandas as gpd
import numpy as np
import pandas as pd


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def text_blob(row: pd.Series) -> str:
    vals = []
    for v in row.values:
        if pd.isna(v):
            continue
        vals.append(str(v).lower())
    return " ".join(vals)


def infer_overhead_type(row: pd.Series) -> str:
    s = text_blob(row)
    # Order matters: covered walkways are often ways/path with shelter tags.
    if any(k in s for k in ["covered_walkway", "covered walkway", "shelter", "sheltered", "covered=yes", "covered yes"]):
        return "covered_walkway"
    if any(k in s for k in ["footbridge", "pedestrian bridge", "pedestrian_bridge", "overpass", "overhead bridge"]):
        return "pedestrian_bridge"
    if any(k in s for k in ["mrt", "lrt", "rail", "monorail", "light_rail", "subway", "train"]):
        return "elevated_rail"
    if any(k in s for k in ["motorway", "expressway", "highway=trunk", "flyover", "elevated road", "elevated_road"]):
        return "elevated_road"
    if any(k in s for k in ["viaduct", "bridge=yes", "bridge yes", "bridge"]):
        return "viaduct"
    return "other_overhead"


def footprintise_overhead(oh: gpd.GeoDataFrame, widths: Dict[str, float], crs: str) -> gpd.GeoDataFrame:
    """Convert OSM lines/points/polygons into approximate overhead footprints.

    Lines are buffered using an inferred type-specific width. Polygons are kept.
    Points are buffered using type width / 2, so they can still be counted.
    This is a QA approximation, not a final engineering geometry layer.
    """
    oh = oh.copy().to_crs(crs)
    oh["overhead_type"] = oh.apply(infer_overhead_type, axis=1)
    oh["assumed_width_m"] = oh["overhead_type"].map(widths).fillna(widths.get("other_overhead", 6.0))

    geoms = []
    for _, row in oh.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            geoms.append(geom)
            continue
        gtype = geom.geom_type
        width = float(row["assumed_width_m"])
        if gtype in ["LineString", "MultiLineString"]:
            geoms.append(geom.buffer(width / 2.0, cap_style=2, join_style=2))
        elif gtype in ["Point", "MultiPoint"]:
            geoms.append(geom.buffer(width / 2.0))
        else:
            geoms.append(geom)
    oh["geometry_original_type"] = oh.geometry.geom_type
    oh["geometry"] = geoms
    oh = oh[oh.geometry.notna() & ~oh.geometry.is_empty].copy()
    oh["overhead_area_m2"] = oh.geometry.area
    return gpd.GeoDataFrame(oh, geometry="geometry", crs=crs)


def build_cell_qa(cfg: dict) -> dict:
    crs = cfg.get("working_crs", "EPSG:3414")
    grid_fp = Path(cfg["grid_geojson"])
    overhead_fp = Path(cfg["overhead_geojson"])
    qa_dir = Path(cfg.get("qa_dir", "outputs/v09_gamma_qa"))
    qa_dir.mkdir(parents=True, exist_ok=True)

    if not grid_fp.exists():
        raise FileNotFoundError(f"Grid GeoJSON not found: {grid_fp}")
    if not overhead_fp.exists():
        raise FileNotFoundError(
            f"Overhead GeoJSON not found: {overhead_fp}\n"
            "Run your Overpass overhead detection script first, or update config['overhead_geojson']."
        )

    print(f"[INFO] reading grid: {grid_fp}")
    grid = gpd.read_file(grid_fp).to_crs(crs)
    if "cell_id" not in grid.columns:
        raise KeyError("Grid must contain cell_id")
    grid = grid[["cell_id", "geometry"]].drop_duplicates("cell_id").copy()
    grid["cell_area_m2"] = grid.geometry.area

    print(f"[INFO] reading overhead features: {overhead_fp}")
    oh_raw = gpd.read_file(overhead_fp)
    oh = footprintise_overhead(oh_raw, cfg.get("overhead_type_widths_m", {}), crs)
    print(f"[INFO] overhead features footprintised: {len(oh)}")

    fp_geojson = qa_dir / "v09_overhead_structures_footprints.geojson"
    oh.to_file(fp_geojson, driver="GeoJSON")

    print("[INFO] overlay grid x overhead footprints ...")
    inter = gpd.overlay(
        grid[["cell_id", "cell_area_m2", "geometry"]],
        oh[["overhead_type", "assumed_width_m", "geometry"]],
        how="intersection",
    )

    if len(inter):
        inter["inter_area_m2"] = inter.geometry.area
        area_sum = inter.groupby("cell_id", as_index=False)["inter_area_m2"].sum()
        counts = inter.groupby(["cell_id", "overhead_type"]).size().unstack(fill_value=0).reset_index()
    else:
        area_sum = pd.DataFrame({"cell_id": [], "inter_area_m2": []})
        counts = pd.DataFrame({"cell_id": []})

    summary = grid[["cell_id", "cell_area_m2"]].merge(area_sum, on="cell_id", how="left")
    summary["inter_area_m2"] = summary["inter_area_m2"].fillna(0.0)
    summary["overhead_fraction_cell"] = (summary["inter_area_m2"] / summary["cell_area_m2"]).clip(0, 1)

    if "cell_id" in counts.columns:
        summary = summary.merge(counts, on="cell_id", how="left")
    for t in ["covered_walkway", "pedestrian_bridge", "elevated_rail", "elevated_road", "viaduct", "other_overhead"]:
        if t not in summary.columns:
            summary[t] = 0
        summary[t] = summary[t].fillna(0).astype(int)

    bins = [-0.001, 0.02, 0.10, 1.0]
    labels = ["clean_or_minor", "moderate_confounding", "major_confounding"]
    summary["overhead_confounding_flag"] = pd.cut(summary["overhead_fraction_cell"], bins=bins, labels=labels).astype(str)

    out_csv = qa_dir / "v09_overhead_structures_per_cell.csv"
    summary.to_csv(out_csv, index=False)

    out_geojson = qa_dir / "v09_overhead_structures_per_cell.geojson"
    gsummary = grid.merge(summary.drop(columns=["cell_area_m2"]), on="cell_id", how="left")
    gsummary.to_file(out_geojson, driver="GeoJSON")

    report = qa_dir / "v09_overhead_cell_QA_report.md"
    counts_txt = summary["overhead_confounding_flag"].value_counts().to_string()
    type_sums = summary[["covered_walkway", "pedestrian_bridge", "elevated_rail", "elevated_road", "viaduct", "other_overhead"]].sum().to_string()
    report.write_text(
        "# v0.9-gamma overhead cell QA report\n\n"
        f"Grid cells: **{len(summary)}**\n\n"
        f"Overhead source: `{overhead_fp}`\n\n"
        "## Cell-level confounding flags\n\n"
        f"```text\n{counts_txt}\n```\n\n"
        "## Type-specific intersection counts\n\n"
        f"```text\n{type_sums}\n```\n\n"
        "## Interpretation\n\n"
        "- `overhead_fraction_cell` is an approximate footprint fraction based on buffered OSM/Overpass features.\n"
        "- This is a QA/sensitivity layer, not an engineering-grade transport DSM.\n"
        "- Cells flagged `major_confounding` should not be used as clean SOLWEIG reference/hazard tiles without manual inspection.\n",
        encoding="utf-8",
    )

    print(f"[OK] per-cell QA: {out_csv}")
    print(f"[OK] per-cell GeoJSON: {out_geojson}")
    print(f"[OK] footprint GeoJSON: {fp_geojson}")
    print(f"[OK] report: {report}")
    return {
        "cell_csv": str(out_csv),
        "cell_geojson": str(out_geojson),
        "footprints_geojson": str(fp_geojson),
        "report": str(report),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v09_gamma_overhead_aware_config.example.json")
    args = parser.parse_args()
    cfg = load_config(args.config)
    build_cell_qa(cfg)


if __name__ == "__main__":
    main()
