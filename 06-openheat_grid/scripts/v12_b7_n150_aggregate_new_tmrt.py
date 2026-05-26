"""Aggregate Sprint B7 N150 new-run-only SOLWEIG Tmrt outputs.

Inputs:
  - outputs/v12_solweig_n150_execution/n150_new_solweig_run_log.csv
  - configs/v12/v12_solweig_n150_execution_config.example.json
  - focus-cell centroids from the configured grid feature CSV.

Outputs:
  - outputs/v12_solweig_n150_execution/n150_new_focus_tmrt_summary.csv
  - outputs/v12_solweig_n150_execution/n150_new_base_vs_overhead_delta.csv
  - outputs/v12_solweig_n150_execution/n150_new_tmrt_aggregation_report.md

Saved metrics:
  - focus-cell pixel count, valid-pixel count, mean, p50/p75/p90/p95/max Tmrt.
  - percent of focus-cell pixels with Tmrt >= 40/45/50/55 C.
  - paired overhead_as_canopy minus base deltas for each new cell/hour.

Run:
  C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\\v12_b7_n150_aggregate_new_tmrt.py
"""

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
from shapely.geometry import box


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs/v12/v12_solweig_n150_execution_config.example.json"
METRICS = [
    "tmrt_mean_c",
    "tmrt_p75_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "pct_pixels_tmrt_ge_40",
    "pct_pixels_tmrt_ge_45",
    "pct_pixels_tmrt_ge_50",
    "pct_pixels_tmrt_ge_55",
]


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def focus_geom(row: pd.Series, size_m: float):
    half = size_m / 2.0
    return box(
        float(row["centroid_x_svy21"]) - half,
        float(row["centroid_y_svy21"]) - half,
        float(row["centroid_x_svy21"]) + half,
        float(row["centroid_y_svy21"]) + half,
    )


def stats_for_raster(path: Path, geom, geom_crs: str) -> dict[str, float | int]:
    with rasterio.open(path) as src:
        geom_proj = gpd.GeoSeries([geom], crs=geom_crs).to_crs(src.crs).iloc[0] if src.crs else geom
        out, _ = mask(src, [geom_proj], crop=True, filled=False)
        arr = out[0]
        all_pixels = arr.compressed() if np.ma.isMaskedArray(arr) else arr.reshape(-1)
        n_pixels = int(len(all_pixels))
        vals = all_pixels[np.isfinite(all_pixels)]
        if src.nodata is not None:
            vals = vals[vals != src.nodata]
        vals = vals[(vals > -50) & (vals < 120)]
        if len(vals) == 0:
            return {
                "n_pixels": n_pixels,
                "valid_pixel_count": 0,
                "tmrt_mean_c": np.nan,
                "tmrt_p50_c": np.nan,
                "tmrt_p75_c": np.nan,
                "tmrt_p90_c": np.nan,
                "tmrt_p95_c": np.nan,
                "tmrt_max_c": np.nan,
                "pct_pixels_tmrt_ge_40": np.nan,
                "pct_pixels_tmrt_ge_45": np.nan,
                "pct_pixels_tmrt_ge_50": np.nan,
                "pct_pixels_tmrt_ge_55": np.nan,
            }
        valid = float(len(vals))
        return {
            "n_pixels": n_pixels,
            "valid_pixel_count": int(len(vals)),
            "tmrt_mean_c": float(np.mean(vals)),
            "tmrt_p50_c": float(np.percentile(vals, 50)),
            "tmrt_p75_c": float(np.percentile(vals, 75)),
            "tmrt_p90_c": float(np.percentile(vals, 90)),
            "tmrt_p95_c": float(np.percentile(vals, 95)),
            "tmrt_max_c": float(np.max(vals)),
            "pct_pixels_tmrt_ge_40": float((vals >= 40).sum() / valid * 100.0),
            "pct_pixels_tmrt_ge_45": float((vals >= 45).sum() / valid * 100.0),
            "pct_pixels_tmrt_ge_50": float((vals >= 50).sum() / valid * 100.0),
            "pct_pixels_tmrt_ge_55": float((vals >= 55).sum() / valid * 100.0),
        }


def resolve_tmrt_path(row: pd.Series) -> Path | None:
    value = str(row.get("tmrt_output_path", "") or "").strip()
    if value:
        direct = repo_path(value)
        if direct.exists():
            return direct
    out_value = str(row.get("output_dir", "") or "").strip()
    out_dir = repo_path(out_value) if out_value else Path()
    preferred = out_dir / "Tmrt_average.tif"
    if preferred.exists():
        return preferred
    matches = sorted(out_dir.glob("*Tmrt*.tif")) if out_dir.exists() else []
    return matches[0] if matches else None


def build_delta(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    base = summary[summary["scenario"].eq("base")].copy()
    over = summary[summary["scenario"].eq("overhead_as_canopy")].copy()
    keep = ["cell_id", "hour_sgt", *METRICS]
    b = base[keep].rename(columns={m: f"{m}_base" for m in METRICS})
    o = over[keep].rename(columns={m: f"{m}_overhead_as_canopy" for m in METRICS})
    delta = b.merge(o, on=["cell_id", "hour_sgt"], how="inner", validate="one_to_one")
    rename_map = {
        "tmrt_mean_c": "delta_tmrt_mean_c",
        "tmrt_p75_c": "delta_tmrt_p75_c",
        "tmrt_p90_c": "delta_tmrt_p90_c",
        "tmrt_p95_c": "delta_tmrt_p95_c",
        "tmrt_max_c": "delta_tmrt_max_c",
        "pct_pixels_tmrt_ge_40": "delta_pct_pixels_ge_40",
        "pct_pixels_tmrt_ge_45": "delta_pct_pixels_ge_45",
        "pct_pixels_tmrt_ge_50": "delta_pct_pixels_ge_50",
        "pct_pixels_tmrt_ge_55": "delta_pct_pixels_ge_55",
    }
    for metric, delta_col in rename_map.items():
        delta[delta_col] = delta[f"{metric}_overhead_as_canopy"] - delta[f"{metric}_base"]
    delta["source"] = "solweig_b7_new"
    return delta.sort_values(["cell_id", "hour_sgt"])


def write_report(out_dir: Path, summary: pd.DataFrame, delta: pd.DataFrame, expected_runs: int, expected_delta_rows: int) -> None:
    lines = ["# Sprint B7 N150 New Tmrt Aggregation Report", ""]
    status = "PASS" if len(summary) == expected_runs and len(delta) == expected_delta_rows else "PARTIAL"
    lines += [
        f"- status: `{status}`",
        f"- new focus summary rows: `{len(summary)}`",
        f"- expected new focus summary rows: `{expected_runs}`",
        f"- new base-vs-overhead delta rows: `{len(delta)}`",
        f"- expected new delta rows: `{expected_delta_rows}`",
    ]
    if len(summary):
        lines += [
            f"- unique cells: `{summary['cell_id'].nunique()}`",
            f"- valid pixel min/median/max: `{summary['valid_pixel_count'].min()}` / `{summary['valid_pixel_count'].median()}` / `{summary['valid_pixel_count'].max()}`",
            f"- threshold-area metrics available: `{all(c in summary.columns for c in ['pct_pixels_tmrt_ge_40', 'pct_pixels_tmrt_ge_45', 'pct_pixels_tmrt_ge_50', 'pct_pixels_tmrt_ge_55'])}`",
        ]
    lines += [
        "",
        "These are SOLWEIG-derived Tmrt summaries only. They are not local WBGT, hazard_score, risk_score, surrogate output, or System A/B coupling.",
    ]
    (out_dir / "n150_new_tmrt_aggregation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate B7 N150 new-run-only SOLWEIG Tmrt rasters into focus-cell summaries and paired deltas.",
        epilog="Writes CSV summaries plus a Markdown aggregation report. Does not compute local WBGT, hazard_score, risk_score, surrogate models, or System A/B coupling.",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="B7 execution config JSON.")
    args = parser.parse_args()
    cfg = read_json(repo_path(args.config))
    out_dir = repo_path(cfg["summary_output_dir"])
    log_path = out_dir / "n150_new_solweig_run_log.csv"
    if not log_path.exists():
        raise FileNotFoundError(f"B7 SOLWEIG run log not found: {log_path}")

    log = pd.read_csv(log_path)
    if "hour_sgt" not in log.columns and "hour" in log.columns:
        log["hour_sgt"] = log["hour"]
    log["cell_id"] = log["cell_id"].astype(str)
    log["hour_sgt"] = log["hour_sgt"].astype(int)
    usable = log[log["status"].isin(["success", "skipped_completed"])].copy()

    grid = pd.read_csv(repo_path(cfg["grid_feature_path"]))
    grid["cell_id"] = grid["cell_id"].astype(str)
    geom_by_cell = {
        row["cell_id"]: focus_geom(row, float(cfg.get("focus_cell_size_m", 100)))
        for _, row in grid[grid["cell_id"].isin(usable["cell_id"].unique())].iterrows()
    }

    rows = []
    for _, row in usable.iterrows():
        tmrt_path = resolve_tmrt_path(row)
        cell_id = str(row["cell_id"])
        if tmrt_path is None or cell_id not in geom_by_cell:
            continue
        stats = stats_for_raster(tmrt_path, geom_by_cell[cell_id], cfg.get("crs", "EPSG:3414"))
        rows.append(
            {
                "run_id": row["run_id"],
                "cell_id": cell_id,
                "scenario": row["scenario"],
                "hour_sgt": int(row["hour_sgt"]),
                "tmrt_output_path": str(tmrt_path),
                "source": "solweig_b7_new",
                "target_version": cfg["target_version"],
                "reference_domain_version": cfg["reference_domain_version"],
                **stats,
            }
        )

    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary = summary.sort_values(["cell_id", "scenario", "hour_sgt"])
    summary.to_csv(out_dir / "n150_new_focus_tmrt_summary.csv", index=False)
    delta = build_delta(summary)
    delta.to_csv(out_dir / "n150_new_base_vs_overhead_delta.csv", index=False)
    write_report(
        out_dir,
        summary,
        delta,
        int(cfg.get("expected_new_runs", 1260)),
        int(cfg.get("expected_new_delta_rows", 630)),
    )
    print(f"[OK] wrote {out_dir / 'n150_new_focus_tmrt_summary.csv'} rows={len(summary)}")
    print(f"[OK] wrote {out_dir / 'n150_new_base_vs_overhead_delta.csv'} rows={len(delta)}")


if __name__ == "__main__":
    main()
