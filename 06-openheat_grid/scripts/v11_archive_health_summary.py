#!/usr/bin/env python3
"""Generate a compact OpenHeat v1.1 archive health summary.

The script is intentionally schema-tolerant because the archive has evolved
across v0.9/v10 migrated segments and fresh v11 rows. It supports either:

1. wide rows with columns such as `station_id`, `timestamp`, `official_wbgt_c`; or
2. long rows with `station_id`, `timestamp`, `variable`, `value` where variable is WBGT.

Examples
--------

    python scripts/v11_archive_health_summary.py \
      --input data/calibration/v11/v11_station_weather_pairs.csv \
      --output-md outputs/v11_archive_ops/gha_health_latest.md \
      --output-json outputs/v11_archive_ops/gha_health_latest.json \
      --expected-stations 27
"""

from __future__ import annotations

import argparse
import glob
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

TIMESTAMP_CANDIDATES = (
    "timestamp", "valid_timestamp", "valid_time", "obs_time", "observation_time",
    "datetime", "time", "date_time", "forecast_valid_time", "timestamp_sgt",
    "timestamp_utc", "valid_time_sgt", "valid_time_sgt_hour",
)
STATION_CANDIDATES = ("station_id", "station", "station_code", "nea_station_id")
WBGT_CANDIDATES = ("official_wbgt_c", "wbgt_c", "wbgt", "WBGT", "value")

@dataclass(frozen=True)
class ArchiveHealth:
    total_rows: int
    wbgt_rows: int
    unique_stations: int
    unique_timestamps: int
    first_obs: str | None
    last_obs: str | None
    span_hours: float | None
    rows_last_24h: int
    rows_last_7d: int
    nat_timestamp_rows: int
    stations_last_24h: int
    rows_per_station_last_24h_min: int | None
    rows_per_station_last_24h_max: int | None
    verdict: str


def expand_inputs(patterns: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matched = [Path(p) for p in glob.glob(pattern)]
        if matched:
            paths.extend(matched)
        else:
            p = Path(pattern)
            if p.exists():
                paths.append(p)
    # Preserve deterministic order and drop duplicates.
    return sorted(set(paths))


def read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)


def first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def normalize_wbgt_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str | None]]:
    timestamp_col = first_existing(df.columns, TIMESTAMP_CANDIDATES)
    station_col = first_existing(df.columns, STATION_CANDIDATES)
    wbgt_col = first_existing(df.columns, WBGT_CANDIDATES)
    variable_col = first_existing(df.columns, ("variable", "metric", "observed_variable"))

    meta = {"timestamp_col": timestamp_col, "station_col": station_col, "wbgt_col": wbgt_col, "variable_col": variable_col}
    if timestamp_col is None or station_col is None:
        raise ValueError(f"Could not infer timestamp/station columns from {list(df.columns)[:30]}")

    work = df.copy()
    if variable_col is not None:
        mask = work[variable_col].astype(str).str.contains("WBGT", case=False, na=False)
        if mask.any():
            work = work.loc[mask].copy()
            wbgt_col = wbgt_col or first_existing(work.columns, ("value", "reading", "obs_value"))
            meta["wbgt_col"] = wbgt_col

    work["_timestamp"] = pd.to_datetime(work[timestamp_col], errors="coerce", utc=True)
    work["_station_id"] = work[station_col].astype(str)
    if wbgt_col is not None and wbgt_col in work.columns:
        work["_wbgt_c"] = pd.to_numeric(work[wbgt_col], errors="coerce")
    else:
        work["_wbgt_c"] = pd.NA
    return work, meta


def compute_health(df: pd.DataFrame, expected_stations: int) -> tuple[ArchiveHealth, pd.DataFrame]:
    nat_rows = int(df["_timestamp"].isna().sum())
    valid = df.dropna(subset=["_timestamp"]).copy()
    wbgt_rows = valid[valid["_wbgt_c"].notna()].copy()
    if wbgt_rows.empty:
        wbgt_rows = valid.copy()

    if wbgt_rows.empty:
        health = ArchiveHealth(
            total_rows=len(df), wbgt_rows=0, unique_stations=0, unique_timestamps=0,
            first_obs=None, last_obs=None, span_hours=None, rows_last_24h=0, rows_last_7d=0,
            nat_timestamp_rows=nat_rows, stations_last_24h=0,
            rows_per_station_last_24h_min=None, rows_per_station_last_24h_max=None, verdict="RED",
        )
        return health, pd.DataFrame()

    first = wbgt_rows["_timestamp"].min()
    last = wbgt_rows["_timestamp"].max()
    span_hours = (last - first).total_seconds() / 3600 if pd.notna(first) and pd.notna(last) else None
    last_24 = wbgt_rows[wbgt_rows["_timestamp"] >= last - pd.Timedelta(hours=24)]
    last_7d = wbgt_rows[wbgt_rows["_timestamp"] >= last - pd.Timedelta(days=7)]
    station_counts_24 = last_24.groupby("_station_id").size()

    verdict = "GREEN"
    if nat_rows > 0 or wbgt_rows["_station_id"].nunique() < expected_stations:
        verdict = "YELLOW"
    if wbgt_rows.empty or wbgt_rows["_station_id"].nunique() == 0:
        verdict = "RED"

    per_day = (
        wbgt_rows.assign(date=wbgt_rows["_timestamp"].dt.tz_convert("Asia/Singapore").dt.date)
        .groupby("date")
        .agg(
            rows=("_station_id", "size"),
            stations=("_station_id", "nunique"),
            max_wbgt=("_wbgt_c", "max"),
            ge31=("_wbgt_c", lambda s: int((pd.to_numeric(s, errors="coerce") >= 31).sum())),
            ge33=("_wbgt_c", lambda s: int((pd.to_numeric(s, errors="coerce") >= 33).sum())),
        )
        .reset_index()
        .sort_values("date", ascending=False)
    )

    health = ArchiveHealth(
        total_rows=len(df),
        wbgt_rows=len(wbgt_rows),
        unique_stations=int(wbgt_rows["_station_id"].nunique()),
        unique_timestamps=int(wbgt_rows["_timestamp"].nunique()),
        first_obs=str(first),
        last_obs=str(last),
        span_hours=round(float(span_hours), 2) if span_hours is not None else None,
        rows_last_24h=int(len(last_24)),
        rows_last_7d=int(len(last_7d)),
        nat_timestamp_rows=nat_rows,
        stations_last_24h=int(last_24["_station_id"].nunique()),
        rows_per_station_last_24h_min=int(station_counts_24.min()) if not station_counts_24.empty else None,
        rows_per_station_last_24h_max=int(station_counts_24.max()) if not station_counts_24.empty else None,
        verdict=verdict,
    )
    return health, per_day


def write_markdown(path: Path, health: ArchiveHealth, per_day: pd.DataFrame, schema_meta: dict[str, str | None], input_paths: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    day_table = "```text\n" + per_day.head(10).to_string(index=False) + "\n```" if not per_day.empty else "(no per-day rows)"
    text = f"""
# OpenHeat v1.1 archive health summary

Generated by `scripts/v11_archive_health_summary.py`.

## Inputs

{chr(10).join(f'- `{p}`' for p in input_paths)}

## Schema inference

```json
{json.dumps(schema_meta, ensure_ascii=False, indent=2)}
```

## Summary

| Metric | Value |
|---|---:|
| Verdict | {health.verdict} |
| Total rows | {health.total_rows:,} |
| WBGT rows | {health.wbgt_rows:,} |
| Unique stations | {health.unique_stations:,} |
| Unique timestamps | {health.unique_timestamps:,} |
| First obs | {health.first_obs} |
| Last obs | {health.last_obs} |
| Span hours | {health.span_hours} |
| Rows last 24h | {health.rows_last_24h:,} |
| Rows last 7d | {health.rows_last_7d:,} |
| NaT timestamp rows | {health.nat_timestamp_rows:,} |
| Stations last 24h | {health.stations_last_24h:,} |
| Rows/station last 24h min | {health.rows_per_station_last_24h_min} |
| Rows/station last 24h max | {health.rows_per_station_last_24h_max} |

## Per-day WBGT counts

{day_table}

## Cadence caveat

GitHub Actions scheduled runs are best-effort and can have latency. This summary monitors effective cadence; it should not be described as strict sensor-grade 15-minute cadence.
""".strip() + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, help="Input CSV/CSV.GZ/Parquet path or glob. Can be repeated.")
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--expected-stations", type=int, default=27)
    args = parser.parse_args()

    input_paths = expand_inputs(args.input)
    if not input_paths:
        raise FileNotFoundError(f"No input paths matched: {args.input}")

    frames = [read_any(p) for p in input_paths]
    df = pd.concat(frames, ignore_index=True, sort=False)
    normalized, meta = normalize_wbgt_frame(df)
    health, per_day = compute_health(normalized, expected_stations=args.expected_stations)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(asdict(health), ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.output_md, health, per_day, meta, input_paths)
    print(json.dumps(asdict(health), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
