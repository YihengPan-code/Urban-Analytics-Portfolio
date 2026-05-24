#!/usr/bin/env python
"""Migrate legacy v0.9/v10 NEA archive files into the v1.1/v11 archive layout.

This is a one-time hotfix helper. It reads existing long-format NEA archive CSVs,
merges them with any existing v11 long table, de-duplicates observations, and
rebuilds the normalized WBGT / station-weather tables used by the v11 collector.

Run before starting the long-term v11 collector if you already have:
- data/archive/nea_realtime_observations.csv
- data/archive/nea_realtime_observations_v10_longterm.csv
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from v11_archive_collect_once import read_json, ensure_dir, normalize_nea_tables


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[INFO] missing, skip: {path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        df["_source_file"] = str(path)
        print(f"[INFO] loaded {len(df):,} rows: {path}")
        return df
    except Exception as e:
        print(f"[WARN] failed to read {path}: {e}")
        return pd.DataFrame()


def choose_dedup_keys(df: pd.DataFrame) -> List[str]:
    base = ["timestamp", "station_id", "variable"]
    if all(c in df.columns for c in base + ["api_name"]):
        return ["timestamp", "station_id", "variable", "api_name"]
    return [c for c in base if c in df.columns]


def sort_for_keep_last(df: pd.DataFrame) -> pd.DataFrame:
    sort_cols = []
    for c in ["fetch_timestamp_utc", "archive_run_utc", "timestamp", "_source_file"]:
        if c in df.columns:
            sort_cols.append(c)
    if sort_cols:
        return df.sort_values(sort_cols, na_position="first")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy OpenHeat NEA archive into v11 archive layout.")
    parser.add_argument("--config", default="configs/v11/v11_longterm_archive_config.example.json")
    parser.add_argument("--legacy", action="append", default=None,
                        help="Legacy long-format archive CSV to include. Can be repeated. Defaults to v09/v10 known paths.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    acfg = cfg.get("archive", {})
    root = Path(acfg.get("root_dir", "data/archive/v11_longterm"))
    tz_name = acfg.get("timezone", "Asia/Singapore")

    long_dir = ensure_dir(root / "long")
    norm_dir = ensure_dir(root / "normalized")
    outputs_dir = ensure_dir(acfg.get("outputs_dir", "outputs/v11_archive_longterm"))

    out_long = long_dir / "nea_realtime_observations_v11_longterm.csv"
    out_wbgt = norm_dir / "nea_wbgt_v11_longterm_normalized.csv"
    out_weather = norm_dir / "nea_station_weather_v11_longterm_wide.csv"

    legacy_paths = [Path(p) for p in (args.legacy or [
        "data/archive/nea_realtime_observations.csv",
        "data/archive/nea_realtime_observations_v10_longterm.csv",
    ])]
    # Include current v11 long file if it already exists, so migration is idempotent.
    if out_long.exists():
        legacy_paths.append(out_long)

    frames = [read_csv_if_exists(p) for p in legacy_paths]
    frames = [f for f in frames if not f.empty]
    if not frames:
        print("[WARN] no legacy archive rows found. Nothing to migrate.")
        return

    combined = pd.concat(frames, ignore_index=True, sort=False)
    before = len(combined)
    keys = choose_dedup_keys(combined)
    if keys:
        combined = sort_for_keep_last(combined)
        combined = combined.drop_duplicates(keys, keep="last")
    after = len(combined)
    combined = combined.drop(columns=["_source_file"], errors="ignore")

    wbgt, weather = normalize_nea_tables(combined, tz_name)

    report_lines = [
        "# v11 archive legacy migration report",
        "",
        f"Run time: {datetime.now().isoformat(timespec='seconds')}",
        f"Config: `{args.config}`",
        "",
        "## Inputs",
    ]
    for p in legacy_paths:
        report_lines.append(f"- `{p}` — {'exists' if p.exists() else 'missing'}")
    report_lines += [
        "",
        "## Result",
        f"- Combined rows before dedupe: **{before:,}**",
        f"- Dedup keys: **{keys}**",
        f"- Long rows after dedupe: **{after:,}**",
        f"- Normalized WBGT rows: **{len(wbgt):,}**",
        f"- Normalized station-weather rows: **{len(weather):,}**",
        "",
        "## Outputs",
        f"- `{out_long}`",
        f"- `{out_wbgt}`",
        f"- `{out_weather}`",
    ]
    report = "\n".join(report_lines)

    if args.dry_run:
        print(report)
        print("[DRY-RUN] no files written")
        return

    if out_long.exists():
        backup = out_long.with_suffix(out_long.suffix + f".bak_before_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        out_long.replace(backup)
        print(f"[INFO] existing v11 long table backed up to: {backup}")

    combined.to_csv(out_long, index=False)
    wbgt.to_csv(out_wbgt, index=False)
    weather.to_csv(out_weather, index=False)
    report_path = outputs_dir / "v11_archive_legacy_migration_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"[OK] migrated long table: {out_long} ({len(combined):,} rows)")
    print(f"[OK] normalized WBGT: {out_wbgt} ({len(wbgt):,} rows)")
    print(f"[OK] normalized weather: {out_weather} ({len(weather):,} rows)")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
