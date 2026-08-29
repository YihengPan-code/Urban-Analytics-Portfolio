#!/usr/bin/env python3
"""Formal snapshot diagnostics for OpenHeat v1.1-beta-formal.

This script is additive: it does not replace the existing v11 calibration
pipeline. Use it after freezing the formal snapshot and after building the v091
feature table if available.

Outputs
-------
- `archive_health_summary.json`
- `event_counts_by_day.csv`
- `event_counts_by_station.csv`
- `station_day_completeness.csv`
- `row_attrition_diagnostic.csv` (when v091 columns are available)
- `timestamp_cadence_diagnostic.csv`
- `OpenHeat_17d_archive_diagnostics_summary.md`
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

TIMESTAMP_CANDIDATES = ("timestamp", "valid_timestamp", "valid_time", "obs_time", "observation_time", "datetime", "time")
STATION_CANDIDATES = ("station_id", "station", "station_code", "nea_station_id")
WBGT_CANDIDATES = ("official_wbgt_c", "wbgt_c", "WBGT", "wbgt", "value")

@dataclass(frozen=True)
class FormalHealth:
    rows: int
    wbgt_rows: int
    unique_stations: int
    unique_timestamps: int
    first_obs: str | None
    last_obs: str | None
    span_days: float | None
    nat_rows: int


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)


def first_existing(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    timestamp_col = first_existing(df, TIMESTAMP_CANDIDATES)
    station_col = first_existing(df, STATION_CANDIDATES)
    wbgt_col = first_existing(df, WBGT_CANDIDATES)
    variable_col = first_existing(df, ("variable", "metric", "observed_variable"))
    if timestamp_col is None or station_col is None:
        raise ValueError("Could not infer timestamp/station columns")
    out = df.copy()
    if variable_col is not None:
        mask = out[variable_col].astype(str).str.contains("WBGT", case=False, na=False)
        if mask.any():
            out = out.loc[mask].copy()
            wbgt_col = wbgt_col or first_existing(out, ("value", "reading", "obs_value"))
    out["_timestamp"] = pd.to_datetime(out[timestamp_col], errors="coerce", utc=True)
    out["_timestamp_sgt"] = out["_timestamp"].dt.tz_convert("Asia/Singapore")
    out["_station_id"] = out[station_col].astype(str)
    out["_wbgt_c"] = pd.to_numeric(out[wbgt_col], errors="coerce") if wbgt_col else pd.NA
    return out


def health(df: pd.DataFrame) -> FormalHealth:
    valid = df.dropna(subset=["_timestamp"])
    wbgt = valid[valid["_wbgt_c"].notna()].copy()
    if wbgt.empty:
        wbgt = valid
    first = wbgt["_timestamp"].min() if not wbgt.empty else None
    last = wbgt["_timestamp"].max() if not wbgt.empty else None
    span_days = None
    if first is not None and last is not None and pd.notna(first) and pd.notna(last):
        span_days = round((last - first).total_seconds() / 86400, 3)
    return FormalHealth(
        rows=len(df),
        wbgt_rows=len(wbgt),
        unique_stations=int(wbgt["_station_id"].nunique()) if not wbgt.empty else 0,
        unique_timestamps=int(wbgt["_timestamp"].nunique()) if not wbgt.empty else 0,
        first_obs=str(first) if first is not None else None,
        last_obs=str(last) if last is not None else None,
        span_days=span_days,
        nat_rows=int(df["_timestamp"].isna().sum()),
    )


def event_counts_by_day(df: pd.DataFrame) -> pd.DataFrame:
    wbgt = df[df["_wbgt_c"].notna()].copy()
    wbgt["date_sgt"] = wbgt["_timestamp_sgt"].dt.date
    return (
        wbgt.groupby("date_sgt")
        .agg(
            rows=("_station_id", "size"),
            stations=("_station_id", "nunique"),
            max_wbgt=("_wbgt_c", "max"),
            ge31=("_wbgt_c", lambda s: int((s >= 31).sum())),
            ge33=("_wbgt_c", lambda s: int((s >= 33).sum())),
        )
        .reset_index()
        .sort_values("date_sgt")
    )


def event_counts_by_station(df: pd.DataFrame) -> pd.DataFrame:
    wbgt = df[df["_wbgt_c"].notna()].copy()
    return (
        wbgt.groupby("_station_id")
        .agg(
            rows=("_timestamp", "size"),
            timestamps=("_timestamp", "nunique"),
            max_wbgt=("_wbgt_c", "max"),
            ge31=("_wbgt_c", lambda s: int((s >= 31).sum())),
            ge33=("_wbgt_c", lambda s: int((s >= 33).sum())),
        )
        .reset_index()
        .rename(columns={"_station_id": "station_id"})
        .sort_values("station_id")
    )


def station_day_completeness(df: pd.DataFrame, expected_per_day: int = 96) -> pd.DataFrame:
    valid = df.dropna(subset=["_timestamp"]).copy()
    valid["date_sgt"] = valid["_timestamp_sgt"].dt.date
    out = (
        valid.groupby(["date_sgt", "_station_id"])
        .size()
        .reset_index(name="rows")
        .rename(columns={"_station_id": "station_id"})
    )
    out["expected_rows_full_day"] = expected_per_day
    out["completeness_ratio_vs_full_day"] = out["rows"] / expected_per_day
    return out.sort_values(["date_sgt", "station_id"])


def row_attrition(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rows.append(("total_rows", len(df)))
    if "pair_used_for_retrospective_calibration" in df.columns:
        retro = df["pair_used_for_retrospective_calibration"].astype(str).str.lower().isin(["true", "1", "yes"])
        rows.append(("retrospective_eligible_rows", int(retro.sum())))
    if "official_wbgt_c" in df.columns:
        rows.append(("official_wbgt_c_non_null", int(df["official_wbgt_c"].notna().sum())))
        rows.append(("official_wbgt_c_missing", int(df["official_wbgt_c"].isna().sum())))
    if "wbgt_proxy_v09_c" in df.columns:
        rows.append(("wbgt_proxy_v09_c_non_null", int(df["wbgt_proxy_v09_c"].notna().sum())))
        rows.append(("wbgt_proxy_v09_c_missing", int(df["wbgt_proxy_v09_c"].isna().sum())))
    if {"official_wbgt_c", "wbgt_proxy_v09_c"}.issubset(df.columns):
        both = df["official_wbgt_c"].notna() & df["wbgt_proxy_v09_c"].notna()
        rows.append(("target_and_proxy_non_null", int(both.sum())))
    return pd.DataFrame(rows, columns=["diagnostic", "rows"])


def cadence(df: pd.DataFrame) -> pd.DataFrame:
    valid = df.dropna(subset=["_timestamp"]).copy()
    timestamps = valid[["_timestamp"]].drop_duplicates().sort_values("_timestamp")
    timestamps["delta_minutes"] = timestamps["_timestamp"].diff().dt.total_seconds() / 60
    bins = pd.cut(timestamps["delta_minutes"], bins=[0, 10, 17, 25, 40, 80, 240, 10_000], include_lowest=True)
    return timestamps.assign(delta_bin=bins.astype(str))


def write_summary(out_dir: Path, h: FormalHealth, day: pd.DataFrame, station: pd.DataFrame, attr: pd.DataFrame) -> None:
    top_days = "```text\n" + day.sort_values("ge31", ascending=False).head(7).to_string(index=False) + "\n```"
    s142 = station.loc[station["station_id"].astype(str).str.upper().eq("S142")]
    s142_text = "```text\n" + s142.to_string(index=False) + "\n```" if not s142.empty else "S142 not present or zero rows."
    attr_text = "```text\n" + attr.to_string(index=False) + "\n```"
    text = f"""
# OpenHeat v1.1-beta-formal archive diagnostics summary

## Archive health

```json
{json.dumps(asdict(h), ensure_ascii=False, indent=2)}
```

## Row attrition diagnostic

{attr_text}

## Top heat-event days by ≥31°C rows

{top_days}

## S142 contribution

{s142_text}

## Interpretation notes

- This diagnostic is for frozen-snapshot formal closeout, not live archive comparison.
- Row attrition must be interpreted before comparing calibration metrics.
- ≥33°C event modeling should remain exploratory if high-tail events are station-concentrated.
- GHA cadence, once enabled, must be described as best-effort scheduled cadence, not strict sensor-grade 15-minute cadence.
""".strip() + "\n"
    (out_dir / "OpenHeat_17d_archive_diagnostics_summary.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True, help="Frozen raw or paired snapshot CSV/Parquet.")
    parser.add_argument("--v091", type=Path, default=None, help="Optional v091 feature table for row attrition diagnostic.")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--expected-per-station-full-day", type=int, default=96)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw = normalize(read_table(args.snapshot))
    h = health(raw)
    day = event_counts_by_day(raw)
    station = event_counts_by_station(raw)
    comp = station_day_completeness(raw, expected_per_day=args.expected_per_station_full_day)
    cad = cadence(raw)

    if args.v091 and args.v091.exists():
        attr_source = read_table(args.v091)
    else:
        attr_source = read_table(args.snapshot)
    attr = row_attrition(attr_source)

    (args.out_dir / "archive_health_summary.json").write_text(json.dumps(asdict(h), ensure_ascii=False, indent=2), encoding="utf-8")
    day.to_csv(args.out_dir / "event_counts_by_day.csv", index=False)
    station.to_csv(args.out_dir / "event_counts_by_station.csv", index=False)
    comp.to_csv(args.out_dir / "station_day_completeness.csv", index=False)
    attr.to_csv(args.out_dir / "row_attrition_diagnostic.csv", index=False)
    cad.to_csv(args.out_dir / "timestamp_cadence_diagnostic.csv", index=False)
    write_summary(args.out_dir, h, day, station, attr)
    print(json.dumps(asdict(h), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
