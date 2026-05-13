from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime

import rasterio
import geopandas as gpd


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_file(path: Path, required: bool = True) -> str:
    if path.exists():
        return "OK"
    if required:
        return "MISSING"
    return "missing_optional"


def raster_summary(path: Path) -> dict:
    with rasterio.open(path) as src:
        return {
            "path": str(path),
            "exists": True,
            "crs": str(src.crs),
            "shape": f"{src.height} x {src.width}",
            "resolution": f"{src.res[0]} x {src.res[1]}",
            "bounds": tuple(round(v, 3) for v in src.bounds),
            "nodata": src.nodata,
            "dtype": src.dtypes[0],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare/check v10-gamma UMEP input folders.")
    parser.add_argument("--config", default="configs/v10/v10_gamma_umep_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    paths = cfg["paths"]
    settings = cfg.get("settings", {})

    required_files = [
        "grid_geojson",
        "base_grid_csv",
        "v10_basic_morphology_csv",
        "v10_building_dsm",
        "vegetation_dsm",
    ]

    missing = []
    file_rows = []
    for key in required_files:
        p = Path(paths[key])
        status = check_file(p, True)
        file_rows.append((key, p, status))
        if status == "MISSING":
            missing.append((key, p))

    # Create required output / UMEP folders.
    for key in ["umep_svf_dir", "umep_shadow_dir", "output_morphology_dir", "forecast_dir", "comparison_dir"]:
        Path(paths[key]).mkdir(parents=True, exist_ok=True)
    for key in ["v10_morphology_csv", "v10_morphology_geojson", "v10_grid_csv", "v10_grid_geojson"]:
        Path(paths[key]).parent.mkdir(parents=True, exist_ok=True)

    reports_dir = Path(paths["output_morphology_dir"])
    report_path = reports_dir / "v10_gamma_prepare_umep_inputs_report.md"
    manual_steps_path = Path(paths["umep_svf_dir"]).parent / "V10_GAMMA_UMEP_MANUAL_STEPS.txt"

    lines = []
    lines.append("# v10-gamma UMEP input preparation report\n")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n")
    lines.append("## Required input files\n")
    lines.append("```text")
    for key, p, status in file_rows:
        lines.append(f"{key:32s} {status:8s} {p}")
    lines.append("```\n")

    if not missing:
        lines.append("## Raster summaries\n")
        for key in ["v10_building_dsm", "vegetation_dsm"]:
            p = Path(paths[key])
            s = raster_summary(p)
            lines.append(f"### {key}\n")
            lines.append("```text")
            for k, v in s.items():
                lines.append(f"{k}: {v}")
            lines.append("```\n")

        # Basic grid sanity.
        try:
            grid = gpd.read_file(paths["grid_geojson"])
            lines.append("## Grid summary\n")
            lines.append("```text")
            lines.append(f"rows: {len(grid)}")
            lines.append(f"crs: {grid.crs}")
            lines.append(f"has cell_id: {'cell_id' in grid.columns}")
            lines.append("```\n")
        except Exception as e:
            lines.append(f"[WARN] Could not read grid GeoJSON: {e}\n")

    lines.append("## UMEP output folders to use\n")
    lines.append("```text")
    lines.append(f"SVF output folder:    {paths['umep_svf_dir']}")
    lines.append(f"Shadow output folder: {paths['umep_shadow_dir']}")
    lines.append("```\n")

    lines.append("## Manual UMEP instruction summary\n")
    lines.append("1. In QGIS/UMEP, run Sky View Factor using the reviewed building DSM and vegetation DSM. Save outputs to the SVF folder above. Ensure `SkyViewFactor.tif`, `svfs.zip`, and preferably `shadowmats.npz` are present.\n")
    lines.append("2. Run the UMEP shadow workflow using the same reviewed building DSM + vegetation DSM. Save `Shadow_YYYYMMDD_HHMM_LST.tif` rasters to the shadow folder above.\n")
    lines.append("3. Keep vegetation settings consistent with v08 unless intentionally doing sensitivity: transmissivity = 3%, trunk zone = 25%.\n")
    lines.append("4. After UMEP outputs exist, run `python scripts/v10_gamma_zonal_umep_to_grid.py --config configs/v10/v10_gamma_umep_config.example.json`.\n")

    if missing:
        lines.append("\n## Blocking missing inputs\n")
        for key, p in missing:
            lines.append(f"- `{key}`: `{p}`")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    manual_lines = [
        "OpenHeat v10-gamma UMEP manual steps",
        "====================================",
        "",
        "Goal: replicate v08 UMEP morphology using the v10 reviewed augmented building DSM.",
        "",
        f"Reviewed building DSM: {paths['v10_building_dsm']}",
        f"Vegetation DSM:        {paths['vegetation_dsm']}",
        f"SVF output folder:     {paths['umep_svf_dir']}",
        f"Shadow output folder:  {paths['umep_shadow_dir']}",
        "",
        "Recommended settings:",
        "- Vegetation transmissivity: 3%",
        "- Trunk zone: 25%",
        "- Shadow date: same as v08 baseline unless sensitivity is intended, e.g. 2026-03-20",
        "- Shadow hours: 08:00-19:00 if matching v08; v10 script summarises 10:00-16:00 and 13:00-15:00.",
        "",
        "After running UMEP:",
        "python scripts\\v10_gamma_zonal_umep_to_grid.py --config configs\\v10\\v10_gamma_umep_config.example.json",
        "python scripts\\v10_gamma_merge_umep_morphology_to_grid.py --config configs\\v10\\v10_gamma_umep_config.example.json",
        "python scripts\\run_live_forecast_v06.py --mode live --grid data\\grid\\v10\\toa_payoh_grid_v10_features_umep_with_veg.csv --out-dir outputs\\v10_gamma_forecast_live",
        "python scripts\\v10_gamma_finalize_forecast_outputs.py --config configs\\v10\\v10_gamma_umep_config.example.json",
        "python scripts\\v10_gamma_compare_v08_v10_rankings.py --config configs\\v10\\v10_gamma_umep_config.example.json",
    ]
    manual_steps_path.write_text("\n".join(manual_lines), encoding="utf-8")

    print(f"[OK] report: {report_path}")
    print(f"[OK] manual steps: {manual_steps_path}")
    if missing:
        print("[WARN] Missing required inputs:")
        for key, p in missing:
            print(f"  - {key}: {p}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
