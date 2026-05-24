from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


def resolve_path(value: Any) -> Path:
    """Resolve a path-like manifest value relative to the current repo root.

    The script is intended to be run from `06-openheat_grid`. Relative paths in
    manifests are therefore interpreted relative to the current working directory.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return Path("")
    p = Path(str(value))
    return p if p.is_absolute() else Path(".") / p


def manifest_path(row: pd.Series, col: str) -> Path | None:
    if col not in row.index:
        return None
    value = row.get(col)
    if value is None or (isinstance(value, float) and np.isnan(value)) or str(value).strip() == "":
        return None
    return resolve_path(value)


def infer_tmrt_path(row: pd.Series) -> Path:
    """Support both Wave 0 and Wave 1 manifest schemas.

    Wave 0 manifest has:
      tmrt_raster_path

    Wave 1 manifest has:
      output_dir

    In the latter case, SOLWEIG writes `Tmrt_average.tif` inside output_dir.
    """
    p = manifest_path(row, "tmrt_raster_path")
    if p is not None:
        return p

    out_dir = manifest_path(row, "output_dir")
    if out_dir is not None:
        return out_dir / "Tmrt_average.tif"

    raise KeyError("Manifest must include either `tmrt_raster_path` or `output_dir`.")


def infer_focus_geojson(row: pd.Series) -> Path:
    """Support manifests with explicit focus cell path or tile_dir.

    Wave 0 manifest has:
      focus_cell_geojson

    Wave 1 manifest has:
      tile_dir

    In the latter case, the focus cell is expected at `tile_dir/focus_cell.geojson`.
    """
    p = manifest_path(row, "focus_cell_geojson")
    if p is not None:
        return p

    tile_dir = manifest_path(row, "tile_dir")
    if tile_dir is not None:
        return tile_dir / "focus_cell.geojson"

    raise KeyError("Manifest must include either `focus_cell_geojson` or `tile_dir`.")


def summarize_raster(tmrt_path: Path, focus_geojson: Path) -> dict[str, Any]:
    if not tmrt_path.exists():
        return {
            "exists": False,
            "tmrt_raster_path_resolved": tmrt_path.as_posix(),
            "focus_cell_geojson_resolved": focus_geojson.as_posix(),
        }

    if not focus_geojson.exists():
        return {
            "exists": True,
            "focus_exists": False,
            "tmrt_raster_path_resolved": tmrt_path.as_posix(),
            "focus_cell_geojson_resolved": focus_geojson.as_posix(),
        }

    focus = gpd.read_file(focus_geojson)
    with rasterio.open(tmrt_path) as src:
        focus = focus.to_crs(src.crs)
        out, _ = mask(src, list(focus.geometry), crop=True, filled=False)
        arr = out[0]
        if np.ma.isMaskedArray(arr):
            values = arr.compressed()
        else:
            values = arr[np.isfinite(arr)]

    values = values[np.isfinite(values)]
    if values.size == 0:
        return {
            "exists": True,
            "focus_exists": True,
            "n_valid_pixels": 0,
            "tmrt_raster_path_resolved": tmrt_path.as_posix(),
            "focus_cell_geojson_resolved": focus_geojson.as_posix(),
        }

    return {
        "exists": True,
        "focus_exists": True,
        "n_valid_pixels": int(values.size),
        "tmrt_mean_c": float(np.mean(values)),
        "tmrt_p50_c": float(np.percentile(values, 50)),
        "tmrt_p75_c": float(np.percentile(values, 75)),
        "tmrt_p90_c": float(np.percentile(values, 90)),
        "tmrt_p95_c": float(np.percentile(values, 95)),
        "tmrt_max_c": float(np.max(values)),
        "tmrt_min_c": float(np.min(values)),
        "tmrt_raster_path_resolved": tmrt_path.as_posix(),
        "focus_cell_geojson_resolved": focus_geojson.as_posix(),
    }


def add_reference_and_modifiers(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df, pd.DataFrame(), pd.DataFrame()

    if "scenario_id" not in df.columns or "hour_sgt" not in df.columns:
        return df, pd.DataFrame(), pd.DataFrame()

    group_cols = ["scenario_id", "hour_sgt"]
    refs: list[dict[str, Any]] = []
    norms: list[dict[str, Any]] = []
    out_parts: list[pd.DataFrame] = []

    for keys, g in df.groupby(group_cols, dropna=False):
        scenario_id, hour_sgt = keys
        valid = g[g["tmrt_p90_c"].notna()].copy() if "tmrt_p90_c" in g.columns else pd.DataFrame()
        if valid.empty:
            out_parts.append(g)
            continue

        ref = float(valid["tmrt_p90_c"].median())
        deltas = valid["tmrt_p90_c"] - ref
        p05 = float(np.percentile(deltas, 5))
        p50 = float(np.percentile(deltas, 50))
        p95 = float(np.percentile(deltas, 95))
        dmin = float(deltas.min())
        dmax = float(deltas.max())

        refs.append({
            "reference_domain_id": "current_manifest_batch",
            "scenario_id": scenario_id,
            "hour_sgt": hour_sgt,
            "reference_method": "same_hour_same_scenario_median_tmrt_p90",
            "n_reference_cells": int(len(valid)),
            "tmrt_ref_p90_c": ref,
            "delta_p05_c": p05,
            "delta_p50_c": p50,
            "delta_p95_c": p95,
            "notes": "Computed over available rows in current manifest batch.",
        })

        norms.append({
            "reference_domain_id": "current_manifest_batch",
            "scenario_id": scenario_id,
            "hour_sgt": hour_sgt,
            "normalization_method": "percentile_rank_and_robust01_p05_p95",
            "delta_min_c": dmin,
            "delta_p05_c": p05,
            "delta_p50_c": p50,
            "delta_p95_c": p95,
            "delta_max_c": dmax,
            "n_cells": int(len(valid)),
            "notes": "Computed over available rows in current manifest batch.",
        })

        gg = g.copy()
        gg["reference_method"] = "same_hour_same_scenario_median_tmrt_p90"
        gg["reference_domain_id"] = "current_manifest_batch"
        gg["tmrt_ref_p90_c"] = ref
        gg["delta_tmrt_p90_c"] = gg["tmrt_p90_c"] - ref

        gg["m_rad_pct"] = gg["delta_tmrt_p90_c"].rank(pct=True, method="average")
        denom = p95 - p05
        if denom == 0:
            gg["m_rad_robust01"] = 0.5
            if "qa_notes" not in gg.columns:
                gg["qa_notes"] = ""
            gg["qa_notes"] = gg["qa_notes"].astype(str) + "; degenerate robust normalization"
        else:
            gg["m_rad_robust01"] = ((gg["delta_tmrt_p90_c"] - p05) / denom).clip(0, 1)

        out_parts.append(gg)

    out = pd.concat(out_parts, ignore_index=True) if out_parts else df
    return out, pd.DataFrame(refs), pd.DataFrame(norms)


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate SOLWEIG Tmrt rasters to cell-level v12 modifier summaries.")
    ap.add_argument("--manifest", default="configs/v12/v12_solweig_wave0_reuse_v10_manifest.csv")
    ap.add_argument("--out-dir", default="outputs/v12_solweig_typology_pilot")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(args.manifest)
    rows: list[dict[str, Any]] = []

    for _, row in manifest.iterrows():
        tmrt_path = infer_tmrt_path(row)
        focus_path = infer_focus_geojson(row)
        s = summarize_raster(tmrt_path, focus_path)

        record = row.to_dict()
        record["tmrt_raster_path"] = tmrt_path.as_posix()
        record["focus_cell_geojson"] = focus_path.as_posix()
        record["tmrt_raster_exists"] = bool(s.get("exists", False))
        record["focus_cell_exists"] = bool(s.get("focus_exists", False))

        for key, val in s.items():
            if key not in {"exists", "focus_exists"}:
                record[key] = val

        if "n_valid_pixels" in record and pd.notna(record["n_valid_pixels"]) and record["n_valid_pixels"]:
            # Default expected focus cell is 100m x 100m at 2m res = 2500 pixels.
            record["valid_pixel_fraction"] = float(record["n_valid_pixels"]) / 2500.0
        else:
            record["valid_pixel_fraction"] = np.nan

        record["qa_status"] = (
            "ok"
            if record["tmrt_raster_exists"] and record["focus_cell_exists"] and record.get("n_valid_pixels", 0) > 0
            else "missing_or_empty"
        )
        record["qa_notes"] = ""
        rows.append(record)

    df = pd.DataFrame(rows)
    df2, ref, norm = add_reference_and_modifiers(df)

    summary_path = out_dir / "tmrt_cell_summary_long.csv"
    target_path = out_dir / "modifier_targets_long.csv"
    ref_path = out_dir / "modifier_reference_table.csv"
    norm_path = out_dir / "modifier_normalization_params.csv"

    df.to_csv(summary_path, index=False)
    df2.to_csv(target_path, index=False)
    ref.to_csv(ref_path, index=False)
    norm.to_csv(norm_path, index=False)

    report = "# v12 SOLWEIG typology aggregation report\n\n"
    report += f"- Manifest: `{args.manifest}`\n"
    report += f"- Rows: `{len(df)}`\n"
    report += f"- Raster exists: `{int(df['tmrt_raster_exists'].sum())}` / `{len(df)}`\n"
    report += f"- Focus cell exists: `{int(df['focus_cell_exists'].sum())}` / `{len(df)}`\n\n"

    if len(df2):
        cols = [
            c for c in [
                "run_id",
                "cell_id",
                "hour_sgt",
                "scenario_id",
                "tmrt_mean_c",
                "tmrt_p90_c",
                "tmrt_max_c",
                "delta_tmrt_p90_c",
                "m_rad_pct",
                "qa_status",
            ]
            if c in df2.columns
        ]
        report += df2[cols].to_markdown(index=False)
    (out_dir / "v12_solweig_typology_aggregation_report.md").write_text(report, encoding="utf-8")

    print("[write]", summary_path)
    print("[write]", target_path)
    print("[write]", ref_path)
    print("[write]", norm_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
