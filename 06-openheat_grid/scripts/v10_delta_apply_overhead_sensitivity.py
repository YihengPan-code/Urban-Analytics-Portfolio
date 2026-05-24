"""Apply cell-level overhead shade sensitivity to v10-gamma grid features.

This is the patched version of the v10-delta patch script.

Fix vs original: scope alignment between shade_fraction and overhead_proxy.
  shade_fraction (from v10-gamma UMEP zonal stats) is defined relative to
  OPEN PIXELS only — i.e., "of the non-building pixels in this cell, what
  fraction are in shadow at 10:00–16:00".

  overhead_shade_proxy (from cell metrics) was defined relative to TOTAL
  CELL AREA — i.e., "what fraction of the whole cell is under overhead
  infrastructure, weighted by opacity".

  The original multiplicative combine
      shade_new = 1 - (1 - shade_open) * (1 - overhead_proxy_total_cell)
  treats both inputs as if they shared the same denominator. They don't,
  so the formula systematically UNDER-stated overhead's shading effect on
  open pixels by a factor of (1 / open_pixel_fraction) ≈ 1.25 in v10
  (mean open_pixel_fraction = 0.797).

  Patched: rescale overhead proxy from cell-area scope to open-pixel scope
  before the multiplicative combine:
      overhead_proxy_open = overhead_proxy_total / open_pixel_fraction
      shade_new = 1 - (1 - shade_open) * (1 - overhead_proxy_open)

  If `open_pixel_fraction_v10` is missing from the grid (e.g., because the
  grid was built before v10-gamma morphology), we fall back to the old
  cell-level proxy with a warning, so this script never silently fails.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import geopandas as gpd
import pandas as pd


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_delta_overhead_config.example.json")
    args = ap.parse_args()

    cfg = read_json(Path(args.config))
    inp = cfg["inputs"]
    out = cfg["outputs"]
    sens = cfg.get("sensitivity", {})

    grid_path = Path(inp["v10_grid_csv"])
    overhead_path = Path(out["overhead_per_cell_csv"])
    if not grid_path.exists():
        raise FileNotFoundError(f"v10 grid CSV not found: {grid_path}")
    if not overhead_path.exists():
        raise FileNotFoundError(
            f"overhead per-cell CSV not found: {overhead_path}. "
            "Run v10_delta_cell_overhead_metrics.py first."
        )

    grid = pd.read_csv(grid_path)
    overhead = pd.read_csv(overhead_path)
    if "cell_id" not in grid.columns or "cell_id" not in overhead.columns:
        raise KeyError("Both grid and overhead CSVs must contain cell_id")

    base_shade_col = sens.get("base_shade_column", "shade_fraction")
    if base_shade_col not in grid.columns:
        raise KeyError(f"Base shade column not found in grid: {base_shade_col}")

    keep_cols = [c for c in overhead.columns if c != "cell_area_m2"]
    outdf = grid.merge(overhead[keep_cols], on="cell_id", how="left")
    for c in ["overhead_fraction_total", "overhead_shade_proxy",
                "pedestrian_shelter_fraction", "transport_deck_fraction"]:
        if c not in outdf.columns:
            outdf[c] = 0.0
        outdf[c] = pd.to_numeric(outdf[c], errors="coerce").fillna(0).clip(0, 1)
    if "overhead_confounding_flag" not in outdf.columns:
        outdf["overhead_confounding_flag"] = "clean_or_minor"
    if "overhead_interpretation" not in outdf.columns:
        outdf["overhead_interpretation"] = "minor_or_none"

    base_shade = pd.to_numeric(outdf[base_shade_col], errors="coerce").fillna(0).clip(0, 1)
    overhead_proxy_cell = pd.to_numeric(outdf["overhead_shade_proxy"], errors="coerce").fillna(0)
    if sens.get("clip_overhead_shade_proxy", True):
        overhead_proxy_cell = overhead_proxy_cell.clip(0, 1)

    # ---- NEW: scope alignment ----
    # shade_fraction is open-pixel-scope; overhead proxy is cell-scope; rescale.
    open_frac_col = "open_pixel_fraction_v10"
    if open_frac_col in outdf.columns:
        open_frac = pd.to_numeric(outdf[open_frac_col], errors="coerce")
        # Fallback for missing/zero values: treat as fully open (1.0). This avoids
        # division-by-zero in fully-built cells while still being conservative.
        open_frac = open_frac.fillna(1.0).clip(0.01, 1.0)
        overhead_proxy_open = (overhead_proxy_cell / open_frac).clip(0, 1)
        scope_note = (
            "overhead proxy rescaled from cell-area scope to open-pixel scope "
            f"using `{open_frac_col}`."
        )
        scope_method = "open_pixel_scope"
    else:
        # Fall back to original (cell-level) behaviour with a clear warning.
        print(
            f"[WARN] {open_frac_col} not found in v10 grid CSV. Falling back to "
            "cell-level overhead proxy. Sensitivity may under-state overhead "
            "shading effect by ~25% (factor 1/open_pixel_fraction)."
        )
        overhead_proxy_open = overhead_proxy_cell
        scope_note = (
            f"WARNING: `{open_frac_col}` not present in v10 grid. Using cell-level "
            "overhead proxy directly. Result systematically UNDER-states overhead "
            "shading effect on open pixels."
        )
        scope_method = "cell_scope_fallback"

    # Carry both scopes for transparency/debugging.
    outdf["overhead_shade_proxy_cell_scope"] = overhead_proxy_cell
    outdf["overhead_shade_proxy_open_scope"] = overhead_proxy_open
    outdf["overhead_shade_scope_method"] = scope_method

    out_col = sens.get("output_shade_column", "shade_fraction_overhead_sens")
    outdf[f"{base_shade_col}_base_v10"] = base_shade
    outdf[out_col] = (1.0 - (1.0 - base_shade) * (1.0 - overhead_proxy_open)).clip(0, 1)
    outdf["delta_shade_overhead_sens_minus_base"] = outdf[out_col] - base_shade

    if sens.get("replace_shade_fraction", True):
        outdf["shade_fraction_without_overhead_sens"] = outdf[base_shade_col]
        outdf[base_shade_col] = outdf[out_col]
        outdf["shade_fraction_source_v10_delta"] = "v10_umep_plus_overhead_shade_sensitivity_open_scope"

    outdf["overhead_sensitivity_note"] = (
        "Overhead shade sensitivity: adjusts ground-level shade proxy only "
        "(open-pixel scope). Elevated transport-deck heat is not modelled as "
        "pedestrian heat exposure."
    )

    csv_path = Path(out["overhead_sensitivity_grid_csv"])
    ensure_dir(csv_path)
    outdf.to_csv(csv_path, index=False)

    geo_path = Path(out["overhead_sensitivity_grid_geojson"])
    v10_geo_str = inp.get("v10_grid_geojson", "")
    v10_geo = Path(v10_geo_str) if v10_geo_str else None
    if v10_geo is not None and v10_geo.is_file():
        geom = gpd.read_file(v10_geo)
        if "cell_id" in geom.columns:
            gcols = ["cell_id", "geometry"]
            gout = geom[gcols].merge(outdf, on="cell_id", how="right")
            gout = gpd.GeoDataFrame(gout, geometry="geometry", crs=geom.crs)
            gout = gout[gout.geometry.notna()].copy()
            ensure_dir(geo_path)
            gout.to_file(geo_path, driver="GeoJSON")

    report_path = Path(out["overhead_sensitivity_report"])
    ensure_dir(report_path)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# v10-delta overhead shade sensitivity grid report\n\n")
        f.write(f"Input grid: `{grid_path}`\n\n")
        f.write(f"Output sensitivity grid: `{csv_path}`\n\n")
        f.write("## Scope alignment\n\n")
        f.write(f"- {scope_note}\n")
        f.write(f"- Method: `{scope_method}`\n\n")
        f.write("## Shade sensitivity summary\n\n```text\n")
        cols = [
            base_shade_col, f"{base_shade_col}_base_v10", out_col,
            "overhead_shade_proxy_cell_scope", "overhead_shade_proxy_open_scope",
            "delta_shade_overhead_sens_minus_base", "overhead_fraction_total",
        ]
        cols = [c for c in cols if c in outdf.columns]
        f.write(outdf[cols].describe().to_string())
        f.write("\n```\n\n")
        f.write("## Top cells by overhead shade increment\n\n```text\n")
        show_cols = [
            "cell_id", f"{base_shade_col}_base_v10", out_col,
            "delta_shade_overhead_sens_minus_base", "overhead_fraction_total",
            "overhead_shade_proxy_cell_scope", "overhead_shade_proxy_open_scope",
            "overhead_confounding_flag", "overhead_interpretation",
        ]
        show_cols = [c for c in show_cols if c in outdf.columns]
        f.write(outdf.sort_values("delta_shade_overhead_sens_minus_base",
                                   ascending=False)[show_cols].head(30).to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Interpretation\n")
        f.write("- This grid is an overhead-shade sensitivity scenario, not a final "
                "overhead-aware physical model.\n")
        f.write("- Use it to test whether ground-level overhead shading materially "
                "changes hotspot ranking.\n")
        f.write("- Transport deck heat is not represented; elevated expressway/rail "
                "cells should be flagged separately.\n")
        f.write("- The overhead proxy is rescaled to open-pixel scope to match the "
                "scope of the UMEP shade fraction it modifies.\n")

    print(f"[OK] sensitivity grid CSV: {csv_path}")
    print(f"[OK] report: {report_path}")
    print(f"[INFO] scope method: {scope_method}")


if __name__ == "__main__":
    main()
