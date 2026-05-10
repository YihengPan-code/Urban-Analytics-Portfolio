from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


def read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def safe_float(x: Any, default: float = np.nan) -> float:
    try:
        return float(x)
    except Exception:
        return default


def raster_stats_for_grid(
    grid: gpd.GeoDataFrame,
    raster_path: Path,
    prefix: str,
    building_threshold_m: float = 0.5,
    all_touched: bool = False,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not raster_path.exists():
        raise FileNotFoundError(f"Raster not found: {raster_path}")

    with rasterio.open(raster_path) as src:
        r_crs = src.crs
        g = grid.to_crs(r_crs) if grid.crs != r_crs else grid.copy()
        pixel_area = abs(src.res[0] * src.res[1])
        nodata = src.nodata

        for _, row in g.iterrows():
            cell_id = row["cell_id"]
            geom = row.geometry
            cell_area = safe_float(geom.area, np.nan)
            try:
                out, _ = mask(src, [geom], crop=True, filled=False, all_touched=all_touched)
                arr_ma = out[0]
                if hasattr(arr_ma, "compressed"):
                    vals = arr_ma.compressed().astype("float64")
                else:
                    vals = np.asarray(arr_ma).ravel().astype("float64")
                    if nodata is not None:
                        vals = vals[vals != nodata]
            except ValueError:
                vals = np.array([], dtype="float64")

            vals = vals[np.isfinite(vals)]
            n_valid = int(vals.size)
            if n_valid == 0:
                bvals = np.array([], dtype="float64")
            else:
                bvals = vals[vals > building_threshold_m]
            n_building = int(bvals.size)
            b_area = float(n_building * pixel_area)
            density = b_area / cell_area if cell_area and cell_area > 0 else np.nan
            open_frac = 1.0 - (n_building / n_valid) if n_valid else np.nan

            d: dict[str, Any] = {
                "cell_id": cell_id,
                f"{prefix}_valid_pixel_count": n_valid,
                f"{prefix}_building_pixel_count": n_building,
                f"{prefix}_building_area_m2": b_area,
                f"{prefix}_building_density": density,
                f"{prefix}_open_pixel_fraction": open_frac,
                f"{prefix}_dsm_mean_all_m": float(np.mean(vals)) if n_valid else np.nan,
                f"{prefix}_dsm_max_all_m": float(np.max(vals)) if n_valid else np.nan,
                f"{prefix}_building_height_mean_m": float(np.mean(bvals)) if n_building else 0.0,
                f"{prefix}_building_height_max_m": float(np.max(bvals)) if n_building else 0.0,
                f"{prefix}_building_height_p50_m": float(np.percentile(bvals, 50)) if n_building else 0.0,
                f"{prefix}_building_height_p90_m": float(np.percentile(bvals, 90)) if n_building else 0.0,
            }
            rows.append(d)

    return pd.DataFrame(rows)


def pick_context_cols(df: pd.DataFrame) -> list[str]:
    wanted = [
        "cell_id", "lat", "lon", "land_use_hint",
        "road_fraction", "gvi_percent", "tree_canopy_fraction", "ndvi_mean",
        "shade_fraction", "svf", "building_density", "mean_building_height_m",
        "max_building_height_m", "risk_priority_score", "hazard_score"
    ]
    return [c for c in wanted if c in df.columns]


def make_report(df: pd.DataFrame, cfg: dict[str, Any], out: Path) -> None:
    lines: list[str] = []
    lines.append("# v10-beta basic morphology QA report")
    lines.append("")
    lines.append("This report compares old v08/current-DSM building morphology with the v10 reviewed augmented DSM.")
    lines.append("")
    lines.append(f"Rows: **{len(df)}**")
    lines.append("")

    key_cols = [
        "old_building_area_m2", "v10_building_area_m2", "delta_building_area_m2",
        "old_building_density", "v10_building_density", "delta_building_density",
        "old_open_pixel_fraction", "v10_open_pixel_fraction", "delta_open_pixel_fraction",
        "old_building_height_mean_m", "v10_building_height_mean_m", "delta_building_height_mean_m",
        "old_building_height_max_m", "v10_building_height_max_m", "delta_building_height_max_m",
    ]
    present = [c for c in key_cols if c in df.columns]
    if present:
        lines.append("## Summary statistics")
        lines.append("```text")
        lines.append(df[present].describe().to_string())
        lines.append("```")
        lines.append("")

    critical = cfg.get("critical_cells", [])
    if critical:
        sub = df[df["cell_id"].isin(critical)].copy()
        if not sub.empty:
            cols = ["cell_id"] + [c for c in [
                "old_building_density", "v10_building_density", "delta_building_density",
                "old_building_area_m2", "v10_building_area_m2", "delta_building_area_m2",
                "old_building_height_mean_m", "v10_building_height_mean_m",
                "old_open_pixel_fraction", "v10_open_pixel_fraction"
            ] if c in sub.columns]
            lines.append("## Critical cells")
            lines.append("```text")
            lines.append(sub[cols].to_string(index=False))
            lines.append("```")
            lines.append("")

    top_gain = df.sort_values("delta_building_area_m2", ascending=False).head(30)
    cols = ["cell_id", "old_building_area_m2", "v10_building_area_m2", "delta_building_area_m2", "old_building_density", "v10_building_density"]
    cols = [c for c in cols if c in top_gain.columns]
    lines.append("## Top building-area gains")
    lines.append("```text")
    lines.append(top_gain[cols].to_string(index=False))
    lines.append("```")
    lines.append("")

    lines.append("## Interpretation")
    lines.append("- This is a building-only morphology recomputation. It does not yet recompute UMEP SVF/shadow.")
    lines.append("- Use it to audit whether old high-hazard cells were driven by building DSM gaps.")
    lines.append("- Do not treat any interim morphology score as final heat-hazard ranking until v10 SVF/shadow are recomputed.")

    ensure_parent(out)
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute v10 basic building morphology per grid cell.")
    parser.add_argument("--config", default="configs/v10/v10_beta_morphology_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    paths = cfg["paths"]
    outs = cfg["outputs"]
    raster_cfg = cfg.get("raster", {})
    threshold = float(raster_cfg.get("building_threshold_m", 0.5))
    all_touched = bool(raster_cfg.get("all_touched", False))

    grid_path = Path(paths["grid_geojson"])
    old_dsm = Path(paths["old_dsm"])
    v10_dsm = Path(paths["reviewed_dsm"])
    out_csv = Path(outs["basic_morphology_csv"])
    out_geojson = Path(outs["basic_morphology_geojson"])
    out_report = Path(outs["basic_morphology_report"])

    grid = gpd.read_file(grid_path)
    if "cell_id" not in grid.columns:
        raise KeyError("grid_geojson must contain cell_id")
    if grid.crs is None:
        raise ValueError("grid_geojson has no CRS")

    old_stats = raster_stats_for_grid(grid, old_dsm, "old", threshold, all_touched)
    v10_stats = raster_stats_for_grid(grid, v10_dsm, "v10", threshold, all_touched)
    df = old_stats.merge(v10_stats, on="cell_id", how="outer")

    # Add cell geometry-derived area in grid CRS.
    grid_area = grid[["cell_id", "geometry"]].copy()
    if grid_area.crs and grid_area.crs.is_geographic:
        grid_area = grid_area.to_crs("EPSG:3414")
    grid_area["cell_area_m2"] = grid_area.geometry.area
    df = df.merge(grid_area[["cell_id", "cell_area_m2"]], on="cell_id", how="left")

    # Deltas.
    delta_pairs = [
        ("building_area_m2", "delta_building_area_m2"),
        ("building_density", "delta_building_density"),
        ("open_pixel_fraction", "delta_open_pixel_fraction"),
        ("building_height_mean_m", "delta_building_height_mean_m"),
        ("building_height_max_m", "delta_building_height_max_m"),
        ("building_height_p50_m", "delta_building_height_p50_m"),
        ("building_height_p90_m", "delta_building_height_p90_m"),
    ]
    for base, outcol in delta_pairs:
        old_col = f"old_{base}"
        new_col = f"v10_{base}"
        if old_col in df.columns and new_col in df.columns:
            df[outcol] = df[new_col] - df[old_col]

    # Optional context from v08 grid.
    context_path = Path(paths.get("context_grid_csv", ""))
    if context_path.exists():
        ctx = pd.read_csv(context_path)
        ctx_cols = pick_context_cols(ctx)
        if ctx_cols:
            df = df.merge(ctx[ctx_cols].drop_duplicates("cell_id"), on="cell_id", how="left", suffixes=("", "_context"))

    ensure_parent(out_csv)
    df.to_csv(out_csv, index=False)

    # GeoJSON output.
    g_out = grid[["cell_id", "geometry"]].merge(df, on="cell_id", how="left")
    ensure_parent(out_geojson)
    g_out.to_file(out_geojson, driver="GeoJSON")

    make_report(df, cfg, out_report)
    print("[OK] basic morphology CSV:", out_csv)
    print("[OK] basic morphology GeoJSON:", out_geojson)
    print("[OK] report:", out_report)


if __name__ == "__main__":
    main()
