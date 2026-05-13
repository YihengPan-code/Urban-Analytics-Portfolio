#!/usr/bin/env python
"""OpenHeat v1.1-beta hourly aggregation.

Resolves the 15-min WBGT vs hourly Open-Meteo cadence mismatch by aggregating
WBGT obs to hourly buckets per station. Open-Meteo features are taken as the
hour's representative value (first non-null).

For operational warnings, hourly max/p90 of WBGT is more directly useful than
the mean — predicting "will WBGT >= 31 occur at any moment in the hour" rather
than "will the hourly mean WBGT >= 31".

Solves friend's audit item 5.3.

Usage:
    # On augmented pairs (with v09 features already)
    python scripts/v11_beta_aggregate_hourly.py \\
        --input data/calibration/v11/v11_station_weather_pairs_v091.csv \\
        --output data/calibration/v11/v11_station_weather_pairs_hourly.csv

    # On raw collector pairs (skips v09 features)
    python scripts/v11_beta_aggregate_hourly.py \\
        --input data/calibration/v11/v11_station_weather_pairs.csv \\
        --output data/calibration/v11/v11_station_weather_pairs_hourly_raw.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# Columns to aggregate as the hour's "representative" weather (take first non-null).
# These are constant within an hour because Open-Meteo is hourly and merge_asof
# repeated the value across all 15-min WBGT obs in that hour.
WEATHER_FIRST_COLS = [
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
    "shortwave_radiation", "direct_radiation", "diffuse_radiation",
    "cloud_cover", "precipitation",
    # v09 features (also constant within hour after first-pass aggregation)
    "wbgt_proxy_v09_c", "wetbulb_stull_c_v09", "globe_temp_proxy_v09_c",
    "raw_proxy_wbgt_radiative_fallback_c", "raw_proxy_wbgt_fallback_c",
    "wetbulb_stull_c", "shortwave_lag_1h", "shortwave_lag_2h",
    "shortwave_3h_mean", "cumulative_day_shortwave_whm2",
    "temperature_lag_1h", "dTair_dt_1h",
    "proxy_lag_1h", "proxy_3h_mean",
    "direct_fraction", "diffuse_fraction", "shortwave_positive",
    "hour_sin_v09", "hour_cos_v09", "is_daytime_v09", "is_peak_heat_v09",
    "is_nighttime_v09", "period_v09",
]

# Station metadata (constant within station)
STATION_FIRST_COLS = [
    "station_name", "station_lat", "station_lon", "station_town_center",
]

# Pairing metadata (take first; might vary slightly within hour but representative)
META_FIRST_COLS = [
    "weather_match_mode", "pair_used_for_calibration", "posthoc_weather_match",
    "operational_match", "pair_location_source", "has_weather_match",
    # β.1 post-mortem additions: forward the corrected flags so hourly baselines
    # can apply filter_mode=retrospective_calibration without warning.
    "pair_used_for_retrospective_calibration", "is_migrated_archive",
    "archive_run_id",
]

# β.1 fourth audit (3.1) additions: forward static per-station morphology,
# overhead-infrastructure, and grid-cell columns so M5/M6/M7 hourly evaluation
# no longer depends on these columns being silently dropped by the aggregator.
#
# After this patch, the M5 ≡ M6 ≡ M7 bit-identity in hourly LOSO is justified
# *solely* by network sparsity (only S128 in TP-AOI has v10 morphology populated):
# SimpleImputer median strategy drops all-NaN morph columns when the LOSO test
# fold is S128 (train has no morph), and StandardScaler neutralizes the
# constant imputed-from-S128 morph values in folds where S128 is in train.
# This is a real signal-level mechanism, not a code-path artifact.
#
# Aggregation strategy: "first" is correct because these are static per-station
# (per-cell) properties — values are constant within (station_id, hour_bucket)
# bucket. NaN behavior: pandas .agg("first") takes the first non-null, matching
# the 15-min row contract.
STATIC_FIRST_COLS = [
    # station-to-cell mapping
    "cell_id",
    # v10 morphology (per-cell static; only populated for S128 in current network)
    "morph_svf",
    "morph_building_density",
    "morph_mean_building_height",
    "morph_building_height_p90",
    "morph_road_fraction",
    "morph_gvi_percent",
    "morph_shade_fraction",
    # v10 surface elevation
    "v10_dsm_max_all_m",
    # v10 shade base + overhead sensitivity
    "shade_fraction_base_v10",
    "shade_fraction_overhead_sens",
    "delta_shade_overhead_sens_minus_base",
    # overhead infrastructure (per-cell static)
    "overhead_fraction_elevated_road",
    "overhead_fraction_elevated_rail",
    "overhead_area_pedestrian_bridge_m2",
    "overhead_area_covered_walkway_m2",
    "n_overhead_features",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate v11 pairs to hourly buckets per station.")
    parser.add_argument(
        "--input",
        default="data/calibration/v11/v11_station_weather_pairs_v091.csv",
        help="input pairs CSV (15-min cadence)",
    )
    parser.add_argument(
        "--output",
        default="data/calibration/v11/v11_station_weather_pairs_hourly.csv",
        help="output hourly-aggregated pairs CSV",
    )
    parser.add_argument(
        "--target-col",
        default="official_wbgt_c",
        help="WBGT target column to aggregate as mean/max/p90/min",
    )
    parser.add_argument(
        "--ts-col",
        default="timestamp_sgt",
        help="input timestamp column name",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        print(f"[ERROR] input not found: {in_path}", file=sys.stderr)
        return 2

    print(f"[load] {in_path}")
    df = pd.read_csv(in_path, low_memory=False)
    print(f"       {len(df):,} rows × {len(df.columns)} cols (15-min cadence)")

    # Resolve timestamp column
    ts_col = args.ts_col
    if ts_col not in df.columns:
        if "timestamp" in df.columns:
            ts_col = "timestamp"
        else:
            print(f"[ERROR] no timestamp column ({args.ts_col} or timestamp)", file=sys.stderr)
            return 2

    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    n_before = len(df)
    df = df[df[ts_col].notna()].copy()
    if len(df) < n_before:
        print(f"[WARN] dropped {n_before - len(df)} rows with NaT timestamps")

    # Hour bucket: floor to hour
    df["hour_bucket"] = df[ts_col].dt.floor("h")

    if args.target_col not in df.columns:
        print(f"[ERROR] target column {args.target_col} not in input", file=sys.stderr)
        return 2

    # Build aggregation dictionary
    agg_dict = {
        # WBGT target: mean / max / p90 / min / count
        f"{args.target_col}_mean": (args.target_col, "mean"),
        f"{args.target_col}_max": (args.target_col, "max"),
        f"{args.target_col}_p90": (args.target_col, lambda s: s.quantile(0.9)),
        f"{args.target_col}_min": (args.target_col, "min"),
        f"{args.target_col}_n_obs": (args.target_col, "count"),
    }

    # Weather columns: take first non-null (constant within hour for Open-Meteo)
    available_weather = [c for c in WEATHER_FIRST_COLS if c in df.columns]
    for c in available_weather:
        agg_dict[c] = (c, "first")

    # Station metadata
    available_meta = [c for c in STATION_FIRST_COLS + META_FIRST_COLS if c in df.columns]
    for c in available_meta:
        agg_dict[c] = (c, "first")

    # β.1 fourth audit (3.1): static morph/overhead/grid (per-station static)
    available_static = [c for c in STATIC_FIRST_COLS if c in df.columns]
    for c in available_static:
        agg_dict[c] = (c, "first")

    print()
    print("[aggregate] grouping by (station_id, hour_bucket)...")
    print(f"            target: {args.target_col} → mean/max/p90/min/n_obs")
    print(f"            weather first-of-hour: {len(available_weather)} cols")
    print(f"            metadata first-of-hour: {len(available_meta)} cols")
    print(f"            static morph/overhead/grid first-of-hour: {len(available_static)} cols")
    if available_static:
        print(f"            (forwarded: {', '.join(available_static[:6])}{'...' if len(available_static) > 6 else ''})")
    else:
        print("            (none of STATIC_FIRST_COLS present in input;")
        print("             ensure v11_beta_build_features.py ran before aggregator)")

    hourly = (
        df.groupby(["station_id", "hour_bucket"], dropna=False)
          .agg(**agg_dict)
          .reset_index()
    )

    # β.1 fourth audit (3.1) sanity check: verify static morph/overhead values
    # are constant within station (the assumption that justifies "first" agg).
    # If a station has multiple distinct values for a static column, something
    # upstream is wrong (e.g., build_features ran twice with different cell mapping).
    if available_static:
        sanity_failures = []
        for c in available_static:
            # check distinct non-null count per station; should be ≤ 1
            n_distinct = (
                hourly.groupby("station_id")[c]
                      .apply(lambda s: s.dropna().nunique())
            )
            offenders = n_distinct[n_distinct > 1]
            if len(offenders) > 0:
                sanity_failures.append((c, offenders.to_dict()))
        if sanity_failures:
            print()
            print("[WARN] static-column sanity check failed:")
            for c, off in sanity_failures:
                print(f"  {c}: stations with multiple distinct values: {off}")
            print("       This suggests upstream (build_features) inconsistency.")
            print("       'first' aggregation may have picked an arbitrary value.")
        else:
            n_stations_with_morph = (
                hourly.groupby("station_id")[available_static[0]]
                      .apply(lambda s: s.notna().any())
                      .sum()
            )
            print(f"[sanity] static columns constant-per-station ✓ "
                  f"({n_stations_with_morph} of {hourly['station_id'].nunique()} stations have non-null morph)")

    # Add canonical "timestamp_sgt" alias = hour_bucket so downstream beta scripts work
    hourly["timestamp_sgt"] = hourly["hour_bucket"]
    if "timestamp" not in hourly.columns:
        hourly["timestamp"] = hourly["hour_bucket"]
    hourly["date"] = hourly["hour_bucket"].dt.date.astype(str)
    hourly["hour"] = hourly["hour_bucket"].dt.hour

    # Diagnostic: how many hour buckets are "full" (4 obs) vs partial?
    coverage = hourly[f"{args.target_col}_n_obs"].value_counts().sort_index()
    print()
    print("[coverage] obs per hour bucket:")
    for n_obs, count in coverage.items():
        print(f"  n_obs={n_obs:>2}: {count:>6,} hourly buckets ({count*100/len(hourly):.1f}%)")

    # Add station-day-level cumulative shortwave for hourly inertia features
    if "shortwave_radiation" in hourly.columns:
        hourly = hourly.sort_values(["station_id", "date", "hour"]).reset_index(drop=True)
        hourly["cumulative_day_shortwave_hourly_whm2"] = (
            hourly.groupby(["station_id", "date"], sort=False)["shortwave_radiation"]
                  .cumsum()
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print()
    print(f"[write] {out_path}")
    hourly.to_csv(out_path, index=False)
    print(f"        {len(hourly):,} hourly rows × {len(hourly.columns)} cols")

    # Side-by-side summary
    n_15min = len(df)
    n_hourly = len(hourly)
    print()
    print(f"[summary] 15-min input: {n_15min:>7,} rows")
    print(f"          hourly out:   {n_hourly:>7,} rows  (compression: {n_hourly/n_15min*100:.1f}%)")
    print()
    print("[DONE] Hourly pairs ready.")
    print()
    print("In v11_beta_calibration config, set:")
    print(f"  paired_dataset_csv: {out_path}")
    print(f"  target_col:         {args.target_col}_max  (or _p90 for operational warning use case)")
    print()
    print("WBGT_max captures 'did any moment in the hour exceed threshold' which matches")
    print("operational warning semantics better than hourly mean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
