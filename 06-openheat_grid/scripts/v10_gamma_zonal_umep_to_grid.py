from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_hhmm(path: Path) -> int | None:
    """Parse HHMM from UMEP shadow filenames such as Shadow_20260320_1300_LST.tif."""
    name = path.name
    patterns = [
        r"_(\d{4})_LST\.tif$",
        r"_(\d{4})[A-Za-z]?\.tif$",
        r"(?<!\d)([01]\d|2[0-3])([0-5]\d)(?!\d)",
    ]
    for pat in patterns:
        m = re.search(pat, name)
        if not m:
            continue
        if len(m.groups()) == 1:
            return int(m.group(1))
        if len(m.groups()) >= 2:
            return int(f"{m.group(1)}{m.group(2)}")
    return None


def safe_stats(arr: np.ndarray) -> dict[str, float]:
    vals = arr[np.isfinite(arr)]
    if vals.size == 0:
        return {"mean": np.nan, "p10": np.nan, "p50": np.nan, "p90": np.nan, "max": np.nan, "min": np.nan}
    return {
        "mean": float(np.nanmean(vals)),
        "p10": float(np.nanpercentile(vals, 10)),
        "p50": float(np.nanpercentile(vals, 50)),
        "p90": float(np.nanpercentile(vals, 90)),
        "max": float(np.nanmax(vals)),
        "min": float(np.nanmin(vals)),
    }


def masked_array_for_geom(src: rasterio.io.DatasetReader, geom) -> np.ndarray:
    arr, _ = mask(src, [geom], crop=True, filled=True)
    out = arr[0].astype("float64")
    if src.nodata is not None:
        out[out == src.nodata] = np.nan
    return out


def shade_mask(arr: np.ndarray, interpretation: str, threshold: float) -> np.ndarray:
    if interpretation == "zero_is_shade":
        return np.isfinite(arr) & (arr <= threshold)
    if interpretation == "one_is_shade":
        return np.isfinite(arr) & (arr >= threshold)
    raise ValueError(f"Unknown shade_interpretation: {interpretation}")


def mean_for_hours(row: dict, prefix: str, hours: Iterable[int]) -> float:
    vals = []
    for h in hours:
        k = f"{prefix}_{h:04d}_open_v10"
        if k in row and pd.notna(row[k]):
            vals.append(float(row[k]))
    if not vals:
        return np.nan
    return float(np.mean(vals))


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate v10 UMEP SVF/shadow rasters to 100m grid cells.")
    parser.add_argument("--config", default="configs/v10/v10_gamma_umep_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    paths = cfg["paths"]
    st = cfg.get("settings", {})
    building_thr = float(st.get("building_height_threshold_m", 0.5))
    shade_interpretation = st.get("shade_interpretation", "zero_is_shade")
    shade_threshold = float(st.get("shade_threshold", 0.5))

    grid_path = Path(paths["grid_geojson"])
    bldg_path = Path(paths["v10_building_dsm"])
    svf_path = Path(paths["umep_svf_raster"])
    shadow_dir = Path(paths["umep_shadow_dir"])
    out_csv = Path(paths["v10_morphology_csv"])
    out_geojson = Path(paths["v10_morphology_geojson"])
    out_dir = Path(paths["output_morphology_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_geojson.parent.mkdir(parents=True, exist_ok=True)

    if not grid_path.exists():
        raise FileNotFoundError(grid_path)
    if not bldg_path.exists():
        raise FileNotFoundError(bldg_path)
    if not svf_path.exists():
        raise FileNotFoundError(f"SVF raster not found: {svf_path}")
    if not shadow_dir.exists():
        raise FileNotFoundError(f"Shadow dir not found: {shadow_dir}")

    shadow_glob = st.get("shadow_file_glob", "Shadow*.tif")
    shadow_paths = sorted(shadow_dir.glob(shadow_glob))
    if not shadow_paths:
        raise FileNotFoundError(f"No shadow rasters matching {shadow_glob} in {shadow_dir}")

    shadow_by_hour: dict[int, Path] = {}
    unknown_shadow_files = []
    for p in shadow_paths:
        hhmm = parse_hhmm(p)
        if hhmm is None:
            unknown_shadow_files.append(p.name)
            continue
        shadow_by_hour[hhmm] = p

    if not shadow_by_hour:
        raise RuntimeError("No parseable shadow HHMM labels found. Check file names.")

    with rasterio.open(bldg_path) as bsrc:
        raster_crs = bsrc.crs
        pixel_area = abs(bsrc.transform.a * bsrc.transform.e)
        if bsrc.nodata is not None:
            print(f"[WARN] Building DSM nodata is {bsrc.nodata}; reviewed DSM should normally have nodata=None.")

    grid = gpd.read_file(grid_path)
    if "cell_id" not in grid.columns:
        raise KeyError("Grid must contain cell_id")
    grid_r = grid.to_crs(raster_crs)

    rows = []
    with rasterio.open(bldg_path) as bsrc, rasterio.open(svf_path) as svfsrc:
        # Open all shadow rasters once.
        shadow_srcs = {h: rasterio.open(p) for h, p in shadow_by_hour.items()}
        try:
            for idx, g in grid_r[["cell_id", "geometry"]].iterrows():
                geom = g.geometry
                cell_id = g.cell_id
                row: dict = {"cell_id": cell_id}

                b = masked_array_for_geom(bsrc, geom)
                valid = np.isfinite(b)
                building_mask = valid & (b > building_thr)
                open_mask = valid & (~building_mask)
                n_total = int(valid.sum())
                n_building = int(building_mask.sum())
                n_open = int(open_mask.sum())

                row["n_total_pixels_v10"] = n_total
                row["n_building_pixels_v10"] = n_building
                row["n_open_pixels_v10"] = n_open
                row["building_pixel_fraction_v10"] = float(n_building / n_total) if n_total else np.nan
                row["open_pixel_fraction_v10"] = float(n_open / n_total) if n_total else np.nan
                row["building_area_m2_v10"] = float(n_building * pixel_area)

                if n_building:
                    hstats = safe_stats(b[building_mask])
                else:
                    hstats = {"mean": np.nan, "p10": np.nan, "p50": np.nan, "p90": np.nan, "max": np.nan, "min": np.nan}
                row["dsm_building_height_mean_m_v10"] = hstats["mean"]
                row["dsm_building_height_p50_m_v10"] = hstats["p50"]
                row["dsm_building_height_p90_m_v10"] = hstats["p90"]
                row["dsm_building_height_max_m_v10"] = hstats["max"]

                svf = masked_array_for_geom(svfsrc, geom)
                # Align shapes if mask crops differ very slightly; use min common shape.
                if svf.shape != b.shape:
                    rr = min(svf.shape[0], b.shape[0]); cc = min(svf.shape[1], b.shape[1])
                    svf2 = svf[:rr, :cc]
                    open2 = open_mask[:rr, :cc]
                    valid2 = valid[:rr, :cc]
                else:
                    svf2 = svf
                    open2 = open_mask
                    valid2 = valid
                open_svf_stats = safe_stats(svf2[open2])
                all_svf_stats = safe_stats(svf2[valid2])
                row["svf_umep_mean_open_v10"] = open_svf_stats["mean"]
                row["svf_umep_p10_open_v10"] = open_svf_stats["p10"]
                row["svf_umep_p90_open_v10"] = open_svf_stats["p90"]
                row["svf_umep_mean_all_v10"] = all_svf_stats["mean"]

                shade_vals_for_peak = []
                for h, ssrc in shadow_srcs.items():
                    sh = masked_array_for_geom(ssrc, geom)
                    if sh.shape != b.shape:
                        rr = min(sh.shape[0], b.shape[0]); cc = min(sh.shape[1], b.shape[1])
                        sh2 = sh[:rr, :cc]
                        open3 = open_mask[:rr, :cc]
                    else:
                        sh2 = sh
                        open3 = open_mask
                    if open3.sum() == 0:
                        frac = np.nan
                    else:
                        shade = shade_mask(sh2, shade_interpretation, shade_threshold)
                        frac = float((shade & open3).sum() / open3.sum())
                    row[f"shade_fraction_umep_{h:04d}_open_v10"] = frac
                    if pd.notna(frac):
                        shade_vals_for_peak.append(frac)

                row["shade_fraction_umep_10_16_open_v10"] = mean_for_hours(row, "shade_fraction_umep", st.get("shade_hours_10_16", [1000,1100,1200,1300,1400,1500,1600]))
                row["shade_fraction_umep_13_15_open_v10"] = mean_for_hours(row, "shade_fraction_umep", st.get("shade_hours_13_15", [1300,1400,1500]))
                row["shade_fraction_umep_peak_open_v10"] = float(np.nanmax(shade_vals_for_peak)) if shade_vals_for_peak else np.nan

                rows.append(row)
        finally:
            for s in shadow_srcs.values():
                s.close()

    df = pd.DataFrame(rows)
    df["umep_morphology_version"] = "v10_reviewed_dsm_with_veg"
    df["umep_includes_vegetation"] = bool(st.get("umep_includes_vegetation", True))
    df["veg_transmissivity_pct"] = st.get("vegetation_transmissivity_pct", 3)
    df["veg_trunk_zone_pct"] = st.get("vegetation_trunk_zone_pct", 25)
    df["umep_shadow_date"] = st.get("umep_shadow_date", "")
    df["shade_interpretation"] = shade_interpretation

    df.to_csv(out_csv, index=False)

    if st.get("copy_geometry_to_outputs", True):
        gout = grid[["cell_id", "geometry"]].merge(df, on="cell_id", how="inner")
        gout = gpd.GeoDataFrame(gout, geometry="geometry", crs=grid.crs)
        gout.to_file(out_geojson, driver="GeoJSON")

    # QA report
    report = []
    report.append("# v10-gamma UMEP zonal morphology QA report\n")
    report.append(f"Rows: **{len(df)}**\n")
    report.append("## Parsed shadow hours\n")
    report.append("```text")
    report.append(", ".join(str(h) for h in sorted(shadow_by_hour.keys())))
    report.append("```\n")
    if unknown_shadow_files:
        report.append("## Shadow files with unknown time label\n")
        report.append("```text")
        report.extend(unknown_shadow_files)
        report.append("```\n")
    report.append("## Feature summaries\n")
    cols = [
        "svf_umep_mean_open_v10",
        "shade_fraction_umep_10_16_open_v10",
        "shade_fraction_umep_13_15_open_v10",
        "building_pixel_fraction_v10",
        "open_pixel_fraction_v10",
        "dsm_building_height_mean_m_v10",
        "dsm_building_height_max_m_v10",
    ]
    report.append("```text")
    report.append(df[[c for c in cols if c in df.columns]].describe().to_string())
    report.append("```\n")
    report.append("## Notes\n")
    report.append("- This is v10 reviewed-building-DSM + vegetation UMEP morphology, not final SOLWEIG/Tmrt.\n")
    report.append("- Final hazard reranking should use this table merged into the forecast grid, then rerun the forecast/hazard engine.\n")
    report_path = out_dir / "v10_gamma_zonal_umep_morphology_QA_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] v10 morphology CSV: {out_csv}")
    print(f"[OK] v10 morphology GeoJSON: {out_geojson}")
    print(f"[OK] QA report: {report_path}")


if __name__ == "__main__":
    main()
