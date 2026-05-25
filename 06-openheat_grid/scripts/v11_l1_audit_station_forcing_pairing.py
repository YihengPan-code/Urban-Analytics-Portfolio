#!/usr/bin/env python
"""Audit station-to-Open-Meteo forcing pairing for System A Level 1 Sprint 1.

Inputs:
    - Primary paired station/forcing CSV, defaulting to the frozen v11 formal
      diagnostic snapshot when available.
    - Optional hourly aggregated CSV for aggregation sanity checks.

Outputs:
    - outputs/v11_level1/pairing_audit/station_openmeteo_pairing_report.md
    - outputs/v11_level1/pairing_audit/station_grid_mapping.csv
    - outputs/v11_level1/pairing_audit/same_timestamp_spatial_variation.csv
    - outputs/v11_level1/pairing_audit/time_alignment_checks.csv

Saved metrics:
    - Station/location coverage, station-to-query coordinate mapping, duplicate
      forcing clusters, same-timestamp spatial variation, timestamp alignment
      checks, and station-hour aggregation checks.

This script does not train models and does not read or write System B/SOLWEIG,
QGIS, raw archive, raster, or v12 paths.
"""
from __future__ import annotations

import argparse
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "v11_level1" / "pairing_audit"
DEFAULT_PRIMARY = ROOT / "outputs" / "v11_beta_formal" / "diagnostics_inputs" / "v11_pairs_14d_formal_20260524_40419_v091_diag.csv"
FALLBACK_PRIMARY = ROOT / "data" / "calibration" / "v11" / "v11_station_weather_pairs_v091.csv"
DEFAULT_HOURLY = ROOT / "data" / "calibration" / "v11" / "v11_station_weather_pairs_hourly.csv"

FORCING_COLS = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
    "wbgt_proxy_v09_c",
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def boolish(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def parse_sgt(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, errors="coerce")
    try:
        if ts.dt.tz is None:
            return ts.dt.tz_localize("Asia/Singapore", nonexistent="shift_forward", ambiguous="NaT")
        return ts.dt.tz_convert("Asia/Singapore")
    except Exception:
        return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_convert("Asia/Singapore")


def parse_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True)


def station_mapping(df: pd.DataFrame, input_path: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for station_id, group in df.groupby("station_id", dropna=False):
        row: dict[str, object] = {"input_file": rel(input_path), "station_id": station_id}
        for col in ["station_name", "station_lat", "station_lon", "latitude", "longitude", "location_id", "location_name", "cell_id"]:
            if col in group.columns:
                vals = group[col].dropna().astype(str if group[col].dtype == object else object)
                row[col] = vals.iloc[0] if len(vals) else np.nan
                row[f"{col}_n_unique"] = group[col].nunique(dropna=True)
        row["n_rows"] = len(group)
        ts_col = "timestamp_sgt" if "timestamp_sgt" in group.columns else "timestamp"
        if ts_col in group.columns:
            row["n_timestamps"] = group[ts_col].nunique(dropna=True)
            row["min_timestamp"] = str(pd.to_datetime(group[ts_col], errors="coerce").min())
            row["max_timestamp"] = str(pd.to_datetime(group[ts_col], errors="coerce").max())
        for col in FORCING_COLS:
            if col in group.columns:
                row[f"{col}_n_nonnull"] = int(group[col].notna().sum())
                row[f"{col}_n_unique"] = int(group[col].nunique(dropna=True))
        rows.append(row)
    mapping = pd.DataFrame(rows)
    if {"station_lat", "station_lon", "latitude", "longitude"}.issubset(mapping.columns):
        lat1 = pd.to_numeric(mapping["station_lat"], errors="coerce")
        lon1 = pd.to_numeric(mapping["station_lon"], errors="coerce")
        lat2 = pd.to_numeric(mapping["latitude"], errors="coerce")
        lon2 = pd.to_numeric(mapping["longitude"], errors="coerce")
        mapping["station_to_openmeteo_coord_delta_deg"] = np.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)
    coord_cols = [c for c in ["latitude", "longitude"] if c in mapping.columns]
    if coord_cols:
        mapping["openmeteo_coord_key"] = mapping[coord_cols].astype(str).apply(lambda row: ",".join(row), axis=1)
        counts = mapping["openmeteo_coord_key"].value_counts(dropna=False).to_dict()
        mapping["n_stations_sharing_openmeteo_coord"] = mapping["openmeteo_coord_key"].map(counts)
    return mapping.sort_values("station_id")


def same_timestamp_variation(df: pd.DataFrame, input_path: Path) -> pd.DataFrame:
    ts_col = "valid_time_sgt_hour" if "valid_time_sgt_hour" in df.columns else "timestamp_sgt"
    if ts_col not in df.columns:
        ts_col = "timestamp"
    work = df.copy()
    work["_audit_timestamp"] = parse_sgt(work[ts_col]).dt.strftime("%Y-%m-%d %H:%M:%S%z")
    available = [c for c in FORCING_COLS if c in work.columns]
    rows: list[dict[str, object]] = []
    for ts, group in work.groupby("_audit_timestamp", dropna=False):
        if pd.isna(ts):
            continue
        row: dict[str, object] = {
            "input_file": rel(input_path),
            "timestamp_key": ts,
            "n_rows": len(group),
            "n_stations": group["station_id"].nunique(dropna=True) if "station_id" in group.columns else np.nan,
        }
        identical_flags = []
        for col in available:
            vals = pd.to_numeric(group[col], errors="coerce")
            row[f"{col}_n_unique"] = int(vals.nunique(dropna=True))
            row[f"{col}_min"] = float(vals.min()) if vals.notna().any() else np.nan
            row[f"{col}_max"] = float(vals.max()) if vals.notna().any() else np.nan
            row[f"{col}_std"] = float(vals.std(ddof=0)) if vals.notna().sum() > 1 else np.nan
            identical_flags.append(row[f"{col}_n_unique"] <= 1)
        if available:
            cluster_keys = group[available].round(6).astype(str).agg("|".join, axis=1)
            row["forcing_cluster_count"] = int(cluster_keys.nunique(dropna=True))
            row["largest_forcing_cluster_station_count"] = int(cluster_keys.value_counts(dropna=False).max())
            row["all_available_forcing_identical"] = bool(all(identical_flags))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["timestamp_key"])


def timestamp_alignment_rows(df: pd.DataFrame, input_path: Path, label: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    base = {
        "input_label": label,
        "input_file": rel(input_path),
        "n_rows": len(df),
        "n_stations": df["station_id"].nunique(dropna=True) if "station_id" in df.columns else np.nan,
    }
    for col in ["timestamp_sgt", "timestamp_utc", "valid_time_sgt", "valid_time_sgt_hour", "hour_bucket"]:
        if col in df.columns:
            parsed = parse_sgt(df[col]) if "sgt" in col or col == "hour_bucket" else parse_utc(df[col]).dt.tz_convert("Asia/Singapore")
            base[f"{col}_nonnull"] = int(df[col].notna().sum())
            base[f"{col}_min_sgt"] = str(parsed.min())
            base[f"{col}_max_sgt"] = str(parsed.max())
            base[f"{col}_n_unique"] = int(parsed.nunique(dropna=True))
    if {"timestamp_sgt", "timestamp_utc"}.issubset(df.columns):
        sgt = parse_sgt(df["timestamp_sgt"])
        utc_as_sgt = parse_utc(df["timestamp_utc"]).dt.tz_convert("Asia/Singapore")
        delta_min = (sgt - utc_as_sgt).dt.total_seconds().abs() / 60.0
        base["timestamp_sgt_vs_utc_abs_delta_min_median"] = float(delta_min.median())
        base["timestamp_sgt_vs_utc_abs_delta_min_max"] = float(delta_min.max())
        base["timestamp_sgt_vs_utc_aligned_zero_delta_rows"] = int((delta_min == 0).sum())
    ts_source = "timestamp_sgt" if "timestamp_sgt" in df.columns else "hour_bucket" if "hour_bucket" in df.columns else None
    if ts_source and "station_id" in df.columns:
        hour = parse_sgt(df[ts_source]).dt.floor("h")
        station_hour_dupes = df.assign(_hour=hour).duplicated(["station_id", "_hour"]).sum()
        unique_station_hours = df.assign(_hour=hour).drop_duplicates(["station_id", "_hour"]).shape[0]
        unique_hours = int(hour.nunique(dropna=True))
        base["unique_hours"] = unique_hours
        base["unique_station_hours"] = int(unique_station_hours)
        base["duplicate_station_hour_rows"] = int(station_hour_dupes)
        base["hour_only_grouping_suspect"] = bool(len(df) == unique_hours and base["n_stations"] > 1)
        base["station_hour_grouping_expected_rows_if_hourly"] = int(unique_station_hours)
    rows.append(base)
    return rows


def write_report(
    primary: Path,
    hourly: Path | None,
    mapping: pd.DataFrame,
    variation: pd.DataFrame,
    alignment: pd.DataFrame,
) -> None:
    all_shared = False
    if not variation.empty and "all_available_forcing_identical" in variation.columns:
        multi_station = variation[pd.to_numeric(variation["n_stations"], errors="coerce") > 1]
        all_shared = bool((not multi_station.empty) and multi_station["all_available_forcing_identical"].all())
    duplicate_coord_stations = int((pd.to_numeric(mapping.get("n_stations_sharing_openmeteo_coord", pd.Series(dtype=float)), errors="coerce") > 1).sum())
    hard_blockers: list[str] = []
    if all_shared:
        hard_blockers.append("All multi-station timestamps share identical available forcing.")
    if "timestamp_sgt_vs_utc_abs_delta_min_max" in alignment.columns:
        max_delta = pd.to_numeric(alignment["timestamp_sgt_vs_utc_abs_delta_min_max"], errors="coerce").max()
        if pd.notna(max_delta) and max_delta > 0:
            hard_blockers.append(f"timestamp_sgt and timestamp_utc are not zero-delta aligned after timezone conversion (max {max_delta:.1f} min).")
    if "hour_only_grouping_suspect" in alignment.columns and alignment["hour_only_grouping_suspect"].astype(bool).any():
        hard_blockers.append("An hourly input appears grouped by hour only rather than station-hour.")

    variation_preview_cols = [c for c in [
        "timestamp_key",
        "n_stations",
        "forcing_cluster_count",
        "largest_forcing_cluster_station_count",
        "temperature_2m_n_unique",
        "relative_humidity_2m_n_unique",
        "wind_speed_10m_n_unique",
        "shortwave_radiation_n_unique",
        "wbgt_proxy_v09_c_n_unique",
        "all_available_forcing_identical",
    ] if c in variation.columns]
    report = [
        "# Station x Open-Meteo Pairing Audit",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Inputs",
        "",
        f"- Primary paired input: `{rel(primary)}`",
        f"- Hourly aggregation input: `{rel(hourly) if hourly else 'not provided/found'}`",
        "",
        "## Coverage",
        "",
        f"- Stations in mapping: {mapping['station_id'].nunique(dropna=True) if 'station_id' in mapping.columns else 'NA'}",
        f"- Rows in primary input: {int(mapping['n_rows'].sum()) if 'n_rows' in mapping.columns else 'NA'}",
        f"- Stations sharing an Open-Meteo coordinate with another station: {duplicate_coord_stations}",
        f"- All stations accidentally share identical forcing at every multi-station timestamp: {'yes' if all_shared else 'no'}",
        "",
        "## Time Alignment And Aggregation",
        "",
        alignment.to_csv(index=False),
        "",
        "## Same-Timestamp Spatial Variation Preview",
        "",
        variation[variation_preview_cols].head(20).to_csv(index=False) if variation_preview_cols else "_No variation columns available._",
        "",
        "## Blocker Status",
        "",
        "\n".join(f"- HARD BLOCKER: {item}" for item in hard_blockers) if hard_blockers else "- No hard blocker found for proceeding to Level 1 reproduction.",
        "",
        "## Caveats",
        "",
        "- This audit checks station-context forcing pairing and temporal grouping only; it does not validate local WBGT prediction.",
        "- Duplicate forcing clusters are expected when Open-Meteo returns the same rounded values for nearby stations or low-variation hours; they are flagged for review rather than treated as automatic failure.",
    ]
    (OUT_DIR / "station_openmeteo_pairing_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit station to Open-Meteo forcing pairing.")
    parser.add_argument("--input", default=str(DEFAULT_PRIMARY if DEFAULT_PRIMARY.exists() else FALLBACK_PRIMARY))
    parser.add_argument("--hourly-input", default=str(DEFAULT_HOURLY if DEFAULT_HOURLY.exists() else ""))
    args = parser.parse_args()

    primary = Path(args.input)
    hourly = Path(args.hourly_input) if args.hourly_input else None
    if not primary.exists():
        raise SystemExit(f"[ERROR] primary input not found: {primary}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = read_csv(primary)
    mapping = station_mapping(df, primary)
    variation = same_timestamp_variation(df, primary)
    alignment_rows = timestamp_alignment_rows(df, primary, "primary")
    if hourly and hourly.exists():
        hdf = read_csv(hourly)
        alignment_rows.extend(timestamp_alignment_rows(hdf, hourly, "hourly"))
    else:
        hourly = None
    alignment = pd.DataFrame(alignment_rows)

    mapping.to_csv(OUT_DIR / "station_grid_mapping.csv", index=False)
    variation.to_csv(OUT_DIR / "same_timestamp_spatial_variation.csv", index=False)
    alignment.to_csv(OUT_DIR / "time_alignment_checks.csv", index=False)
    write_report(primary, hourly, mapping, variation, alignment)
    print(f"[OK] wrote {OUT_DIR / 'station_grid_mapping.csv'}")
    print(f"[OK] wrote {OUT_DIR / 'same_timestamp_spatial_variation.csv'}")
    print(f"[OK] wrote {OUT_DIR / 'time_alignment_checks.csv'}")
    print(f"[OK] wrote {OUT_DIR / 'station_openmeteo_pairing_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
