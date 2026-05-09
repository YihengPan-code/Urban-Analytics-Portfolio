"""
OpenHeat v0.9-gamma: per-hour Tmrt sanity check for SOLWEIG selected tiles.

Reads consolidated per-hour Tmrt_<year>_<DOY>_<HHMM>D.tif rasters from
each tile's solweig_outputs/ folder and prints a diurnal cycle summary
(mean / max / p90 / p10) per tile.

Usage:
    python scripts/v09_gamma_check_per_hour_tmrt.py
    python scripts/v09_gamma_check_per_hour_tmrt.py --tile T01
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rasterio


TILE_ROOT = Path("data/solweig/v09_tiles_overhead_aware")

TILES = [
    "T01_clean_hazard_top",
    "T02_conservative_risk_top",
    "T03_social_risk_top",
    "T04_open_paved_hotspot",
    "T05_clean_shaded_reference",
    "T06_overhead_confounded_hazard_case",
]

HOURS = [10, 12, 13, 15, 16]
YEAR = 2026
DOY = 127


def stats_one(fp: Path) -> dict:
    with rasterio.open(fp) as src:
        arr = src.read(1).astype("float64")
        nodata = src.nodata
        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {}
    return {
        "mean": float(np.mean(finite)),
        "max": float(np.max(finite)),
        "p90": float(np.percentile(finite, 90)),
        "p10": float(np.percentile(finite, 10)),
    }


def report_tile(tile: str) -> None:
    out_dir = TILE_ROOT / tile / "solweig_outputs"
    if not out_dir.exists():
        print(f"[SKIP] {tile}: solweig_outputs folder missing")
        return

    print(f"\n=== {tile} ===")
    print(f"{'hour':<8} {'mean':>7} {'max':>7} {'p90':>7} {'p10':>7}")
    print("-" * 40)

    found_any = False
    for hh in HOURS:
        fp = out_dir / f"Tmrt_{YEAR}_{DOY}_{hh:02d}00D.tif"
        if not fp.exists():
            print(f"h{hh:02d}:00   [missing]  {fp.name}")
            continue
        s = stats_one(fp)
        if s:
            print(f"h{hh:02d}:00   {s['mean']:>7.1f} {s['max']:>7.1f} {s['p90']:>7.1f} {s['p10']:>7.1f}")
            found_any = True

    avg_fp = out_dir / "Tmrt_average.tif"
    if avg_fp.exists():
        s = stats_one(avg_fp)
        if s:
            print("-" * 40)
            print(f"5h_avg   {s['mean']:>7.1f} {s['max']:>7.1f} {s['p90']:>7.1f} {s['p10']:>7.1f}   (original 5h run)")

    if not found_any:
        print(f"[WARN] No per-hour Tmrt files found in {out_dir}")
        print("Did you run v09_gamma_consolidate_per_hour_tmrt.py?")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tile",
        default=None,
        help="Restrict to one tile (e.g. T01). Default: all tiles with solweig_outputs.",
    )
    args = parser.parse_args()

    if args.tile:
        match = [t for t in TILES if t.startswith(args.tile)]
        if not match:
            raise SystemExit(f"No tile matching prefix '{args.tile}'. Known tiles: {TILES}")
        for t in match:
            report_tile(t)
    else:
        for t in TILES:
            report_tile(t)


if __name__ == "__main__":
    main()
