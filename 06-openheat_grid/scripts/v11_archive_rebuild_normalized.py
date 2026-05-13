#!/usr/bin/env python
"""Rebuild normalized + pairs from the cumulative long table without making any API calls.

Use this after applying a normalize_nea_tables patch (e.g. the timestamp
fallback to record_updated_timestamp). It overwrites the normalized WBGT,
station-weather wide, and paired-dataset CSVs, ensuring stale NaT rows from
pre-patch runs are removed.

This script does NOT touch:
- The cumulative long table (read-only).
- Open-Meteo forecast snapshots (read-only).
- archive_state.json.

Usage:
    python scripts/v11_archive_rebuild_normalized.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make sibling collect_once script importable.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd

from v11_archive_collect_once import (
    read_json,
    ensure_dir,
    normalize_nea_tables,
    build_pairs,
)


def main() -> int:
    cfg_path = Path("configs/v11/v11_longterm_archive_config.example.json")
    if not cfg_path.exists():
        print(f"[ERROR] config not found: {cfg_path}", file=sys.stderr)
        return 2
    cfg = read_json(cfg_path)
    acfg = cfg.get("archive", {})
    pcfg = cfg.get("pairing", {})
    root = Path(acfg.get("root_dir", "data/archive/v11_longterm"))
    tz_name = acfg.get("timezone", "Asia/Singapore")

    long_path = root / "long" / "nea_realtime_observations_v11_longterm.csv"
    norm_dir = ensure_dir(root / "normalized")
    wbgt_path = norm_dir / "nea_wbgt_v11_longterm_normalized.csv"
    weather_path = norm_dir / "nea_station_weather_v11_longterm_wide.csv"
    om_path = norm_dir / "openmeteo_forecast_snapshots_v11_longterm.csv"

    if not long_path.exists():
        print(f"[ERROR] long table missing: {long_path}", file=sys.stderr)
        return 2

    print(f"[load] {long_path}")
    df_long = pd.read_csv(long_path, low_memory=False)
    print(f"       {len(df_long):,} long rows")

    print("[normalize] running patched normalize_nea_tables...")
    wbgt, weather = normalize_nea_tables(df_long, tz_name)
    nat_count = int((wbgt["timestamp_sgt"].astype(str) == "NaT").sum()) if not wbgt.empty else 0
    print(f"           WBGT rows: {len(wbgt):,} (NaT remaining: {nat_count})")
    print(f"           weather rows: {len(weather):,}")

    if nat_count > 0:
        print("[WARN] some rows still have NaT timestamps after fallback. "
              "Check that normalize_nea_tables in v11_archive_collect_once.py "
              "includes the record_updated_timestamp fallback patch.")

    print(f"[write] {wbgt_path}")
    wbgt.to_csv(wbgt_path, index=False)
    print(f"[write] {weather_path}")
    weather.to_csv(weather_path, index=False)

    # Rebuild pairs from refreshed WBGT + existing Open-Meteo snapshots.
    if om_path.exists():
        print(f"[load] {om_path}")
        om = pd.read_csv(om_path, low_memory=False)
        print(f"       {len(om):,} Open-Meteo rows")
        print("[pairs] rebuilding from refreshed WBGT...")
        pairs = build_pairs(wbgt, om, cfg)
        if pairs is None or pairs.empty:
            print("[WARN] build_pairs returned empty.")
        else:
            print(f"       {len(pairs):,} paired rows")
            op_pairs_path = Path(pcfg.get(
                "output_operational_pairs_csv",
                "data/archive/v11_longterm/paired/v11_operational_station_weather_pairs.csv",
            ))
            latest_pairs_path = Path(pcfg.get(
                "output_latest_pairs_csv",
                "data/calibration/v11/v11_station_weather_pairs.csv",
            ))
            ensure_dir(op_pairs_path.parent)
            ensure_dir(latest_pairs_path.parent)
            print(f"[write] {op_pairs_path}")
            pairs.to_csv(op_pairs_path, index=False)
            print(f"[write] {latest_pairs_path}")
            pairs.to_csv(latest_pairs_path, index=False)
    else:
        print(f"[skip] no Open-Meteo file at {om_path}; pairs not rebuilt.")

    print("\n[DONE] rebuild complete. Re-run alpha pipeline to verify NaT is gone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
