"""
OpenHeat v0.9-gamma: consolidate per-hour SOLWEIG outputs into the
canonical Tmrt_<year>_<DOY>_<HHMM>D.tif convention expected by the
v0.9-gamma aggregator.

After running SOLWEIG once per (tile, hour) with single-hour met files,
the outputs are scattered across solweig_outputs_h<HH>/ subfolders, each
containing only Tmrt_average.tif. This script copies/renames them into
each tile's main solweig_outputs/ folder using the standard naming.

Usage:
    python scripts/v09_gamma_consolidate_per_hour_tmrt.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

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
DOY = 127  # May 7, 2026


def main() -> None:
    n_ok, n_missing = 0, 0
    for tile in TILES:
        tile_dir = TILE_ROOT / tile
        if not tile_dir.exists():
            print(f"[SKIP] {tile}: tile folder missing")
            continue

        consolidated = tile_dir / "solweig_outputs"
        consolidated.mkdir(exist_ok=True)

        print(f"\n[INFO] {tile}")
        for hh in HOURS:
            src_dir = tile_dir / f"solweig_outputs_h{hh:02d}"
            src_fp = src_dir / "Tmrt_average.tif"
            if not src_fp.exists():
                print(f"   [MISS] hour {hh:02d}: {src_fp} (did SOLWEIG run for this hour?)")
                n_missing += 1
                continue

            # Canonical name expected by the aggregator
            dst_name = f"Tmrt_{YEAR}_{DOY}_{hh:02d}00D.tif"
            dst_fp = consolidated / dst_name
            shutil.copy2(src_fp, dst_fp)
            size_kb = dst_fp.stat().st_size / 1024
            print(f"   [OK] hour {hh:02d}: {dst_name} ({size_kb:.0f} KB)")
            n_ok += 1

    print(f"\n[DONE] consolidated {n_ok} files; {n_missing} missing")
    print(f"Aggregator can now find them in each tile's solweig_outputs/ folder.")


if __name__ == "__main__":
    main()
