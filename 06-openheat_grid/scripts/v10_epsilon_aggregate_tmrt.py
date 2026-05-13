"""v10-epsilon SOLWEIG Tmrt aggregator (patched).

Patch vs original:
  SOLWEIG v2025a outputs `Tmrt_average.tif` (period-averaged across forcing
  hours) — the filename does NOT contain the hour. Our v10-epsilon design
  uses one forcing file per hour (`_h10.txt` ... `_h16.txt`) and writes each
  run's output into a dedicated subfolder `solweig_outputs_h<HH>/` to
  isolate them. Therefore the hour label must be read from the **parent
  folder name** (e.g. `solweig_outputs_h13`), not from the filename.

  This patched script:
    1. Tries parent-folder hour parsing first (e.g. solweig_outputs_h13 → 1300)
    2. Falls back to filename parsing for backward compatibility
    3. Reports time_label="unknown" only when both fail

How to use: drop in scripts/v10_epsilon_aggregate_tmrt.py replacing the
original. Then run:
    python scripts/v10_epsilon_aggregate_tmrt.py --config configs/v10/v10_epsilon_solweig_config.example.json
"""
from __future__ import annotations

import argparse
import json
import re
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


def parse_time_label(path: Path) -> str:
    """Extract a 4-digit HHMM label.

    Priority:
      1. Parent folder name (e.g. `solweig_outputs_h13` → '1300').
         Matches v10-epsilon nested layout where each hour has its own folder.
      2. Filename embedded hour (e.g. `Tmrt_2026_5_7_1300D.tif` → '1300').
         Backward compatible with v0.9-style outputs.
      3. Returns 'unknown' if neither matches.
    """
    # ---- Priority 1: parent folder ----
    parent_name = path.parent.name  # e.g. solweig_outputs_h13
    m = re.search(r"_h(\d{1,2})$", parent_name)
    if m:
        hour = int(m.group(1))
        return f"{hour:02d}00"  # e.g. '1300'

    # ---- Priority 2: embedded hour in filename ----
    name, stem = path.name, path.stem
    for target in [stem, name]:
        m = re.search(r"_(\d{4})[A-Za-z]?(?:\.tif)?$", target)
        if m:
            return m.group(1)
        m = re.search(r"(?<!\d)([01]\d|2[0-3])([0-5]\d)(?!\d)", target)
        if m:
            return f"{m.group(1)}{m.group(2)}"

    return "unknown"


def stats_for_geom(path: Path, geom) -> dict[str, float | int]:
    with rasterio.open(path) as src:
        geom_proj = (
            gpd.GeoSeries([geom], crs="EPSG:3414").to_crs(src.crs).iloc[0]
            if src.crs
            else geom
        )
        try:
            out, _ = mask(src, [geom_proj], crop=True, filled=False)
        except ValueError:
            return {
                "n_pixels": 0,
                "tmrt_mean_c": np.nan,
                "tmrt_p10_c": np.nan,
                "tmrt_p50_c": np.nan,
                "tmrt_p90_c": np.nan,
            }
        arr = out[0]
        vals = arr.compressed() if np.ma.isMaskedArray(arr) else arr[np.isfinite(arr)]
        vals = vals[np.isfinite(vals)]
        if src.nodata is not None:
            vals = vals[vals != src.nodata]
        # Filter physically implausible values (SOLWEIG occasionally emits sentinels)
        vals = vals[(vals > -50) & (vals < 120)]
        if len(vals) == 0:
            return {
                "n_pixels": 0,
                "tmrt_mean_c": np.nan,
                "tmrt_p10_c": np.nan,
                "tmrt_p50_c": np.nan,
                "tmrt_p90_c": np.nan,
            }
        return {
            "n_pixels": int(len(vals)),
            "tmrt_mean_c": float(np.mean(vals)),
            "tmrt_p10_c": float(np.percentile(vals, 10)),
            "tmrt_p50_c": float(np.percentile(vals, 50)),
            "tmrt_p90_c": float(np.percentile(vals, 90)),
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config", default="configs/v10/v10_epsilon_solweig_config.example.json"
    )
    args = ap.parse_args()
    cfg = read_json(Path(args.config))
    paths = cfg["paths"]
    sol = cfg.get("solweig", {})
    pattern = sol.get("tmrt_glob_pattern", "**/*Tmrt*.tif")
    scenarios = {
        "base": sol.get("base_folder", "solweig_base"),
        "overhead": sol.get("overhead_folder", "solweig_overhead"),
    }
    tile_root = Path(paths["tile_root"])
    out_root = Path(paths["output_root"])
    out_root.mkdir(parents=True, exist_ok=True)
    meta = pd.read_csv(tile_root / "v10_epsilon_tile_metadata.csv")
    grid = gpd.read_file(paths["grid_geojson"]).to_crs(cfg.get("crs", "EPSG:3414"))

    rows = []
    missing_rows = []
    for _, row in meta.iterrows():
        tile_id = row["tile_id"]
        cid = row["cell_id"]
        role = row["role"]
        tile_dir = Path(row["tile_dir"])
        focus = grid[grid["cell_id"].astype(str) == str(cid)]
        if focus.empty:
            raise ValueError(f"focus cell missing from grid: {cid}")
        geom = focus.geometry.iloc[0]
        for scenario, folder_name in scenarios.items():
            folder = tile_dir / folder_name
            files = sorted(folder.glob(pattern))
            if not files:
                missing_rows.append(
                    {"tile_id": tile_id, "scenario": scenario, "folder": str(folder)}
                )
            for fp in files:
                label = parse_time_label(fp)
                hour = int(label[:2]) if label.isdigit() and len(label) == 4 else np.nan
                rows.append(
                    {
                        "tile_id": tile_id,
                        "cell_id": cid,
                        "role": role,
                        "scenario": scenario,
                        "tmrt_raster": str(fp),
                        "tmrt_time_label": label,
                        "tmrt_hour_sgt": hour,
                        **stats_for_geom(fp, geom),
                    }
                )
    df = pd.DataFrame(rows)
    out_csv = out_root / "v10_epsilon_focus_tmrt_summary.csv"
    df.to_csv(out_csv, index=False)
    pd.DataFrame(missing_rows).to_csv(
        out_root / "v10_epsilon_missing_tmrt_outputs.csv", index=False
    )
    lines = [
        "# v10-epsilon SOLWEIG Tmrt aggregation report",
        "",
        f"Rows: **{len(df)}**",
        "",
    ]
    if len(df):
        lines += [
            "## Scenario/time counts",
            "```text",
            df.groupby(["tile_id", "scenario"])["tmrt_raster"]
            .nunique()
            .reset_index(name="n_tmrt_rasters")
            .to_string(index=False),
            "```",
        ]
        lines += [
            "\n## Focus-cell Tmrt",
            "```text",
            df[
                [
                    "tile_id",
                    "cell_id",
                    "role",
                    "scenario",
                    "tmrt_time_label",
                    "tmrt_mean_c",
                    "tmrt_p90_c",
                    "n_pixels",
                ]
            ]
            .sort_values(["tile_id", "scenario", "tmrt_time_label"])
            .to_string(index=False),
            "```",
        ]

        # Diagnostic: any rows still 'unknown'?
        n_unknown = int((df["tmrt_time_label"] == "unknown").sum())
        if n_unknown:
            lines += [
                "\n## ⚠️ Time-label parsing warnings",
                f"`{n_unknown}` rows have `tmrt_time_label='unknown'` — neither parent "
                "folder nor filename contained an hour token. Check the layout.\n",
            ]

    if missing_rows:
        lines += [
            "\n## Missing scenario folders / outputs",
            "```text",
            pd.DataFrame(missing_rows).to_string(index=False),
            "```",
        ]
    report = out_root / "v10_epsilon_aggregate_tmrt_report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] focus Tmrt summary: {out_csv}")
    print(f"[OK] report: {report}")
    if len(df):
        n_unknown = int((df["tmrt_time_label"] == "unknown").sum())
        if n_unknown:
            print(f"[WARN] {n_unknown}/{len(df)} rows have tmrt_time_label='unknown'")


if __name__ == "__main__":
    main()
