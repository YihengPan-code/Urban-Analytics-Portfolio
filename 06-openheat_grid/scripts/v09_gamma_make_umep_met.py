"""
OpenHeat v0.9-gamma: generate UMEP SOLWEIG met forcing file.

Reads the alpha-stage Open-Meteo historical forecast CSV, filters to a single
station and date, and writes a UMEP-format met file with the 5 target hours
(10:00, 12:00, 13:00, 15:00, 16:00 SGT).

Usage:
    python scripts/v09_gamma_make_umep_met.py
    python scripts/v09_gamma_make_umep_met.py --station S128 --date 2026-05-07
    python scripts/v09_gamma_make_umep_met.py --hours 10,12,13,15,16
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/calibration/v09_historical_forecast_by_station_hourly.csv",
    )
    parser.add_argument(
        "--station",
        default="S128",
        help="Station to use as forcing source. S128 Bishan is closest local proxy to Toa Payoh.",
    )
    parser.add_argument("--date", default="2026-05-07", help="Date in YYYY-MM-DD (must exist in archive)")
    parser.add_argument("--hours", default="10,12,13,15,16", help="Comma-separated hours SGT")
    parser.add_argument(
        "--out",
        default="data/solweig/v09_met_forcing_2026_05_07_S128.txt",
    )
    args = parser.parse_args()

    hours = [int(h) for h in args.hours.split(",")]

    df = pd.read_csv(args.input)
    if "time_sgt" not in df.columns or "station_id" not in df.columns:
        raise KeyError(
            f"Input file does not look like alpha forecast CSV. Got columns: {df.columns.tolist()[:10]}"
        )
    df["time_sgt"] = pd.to_datetime(df["time_sgt"])
    sub = df[df["station_id"].astype(str).eq(args.station)].copy()
    if sub.empty:
        avail = sorted(df["station_id"].astype(str).unique().tolist())
        raise ValueError(f"Station {args.station} not found. Available stations: {avail[:10]} ...")

    sub = sub[sub["time_sgt"].dt.date.astype(str).eq(args.date)]
    sub = sub[sub["time_sgt"].dt.hour.isin(hours)]
    sub = sub.sort_values("time_sgt").reset_index(drop=True)

    if sub.empty:
        raise ValueError(f"No rows for station {args.station} on {args.date} hours {hours}")
    if len(sub) != len(hours):
        print(
            f"[WARN] Found {len(sub)} hours, requested {len(hours)}. Hours found: "
            f"{sub['time_sgt'].dt.hour.tolist()}"
        )

    # Build UMEP met file rows
    out = pd.DataFrame(
        {
            "iy": sub["time_sgt"].dt.year,
            "id": sub["time_sgt"].dt.dayofyear,  # DOY 127 for May 7
            "it": sub["time_sgt"].dt.hour,
            "imin": 0,
            "qn": -999,
            "qh": -999,
            "qe": -999,
            "qs": -999,
            "qf": -999,
            "U": sub["wind_speed_10m"].clip(lower=0.5),  # SOLWEIG doesn't like wind=0
            "RH": sub["relative_humidity_2m"].round(1),
            "Tair": sub["temperature_2m"].round(2),
            "pres": 1010,  # Singapore sea level
            "rain": 0,
            "kdown": sub["shortwave_radiation"].round(1),
            "snow": 0,
            "ldown": -999,  # let SOLWEIG estimate from cloud + Tair + RH
            "fcld": (sub["cloud_cover"] / 100.0).round(3),
            "wuh": -999,
            "xsmd": -999,
            "lai_hr": -999,
            "Kdiff": sub["diffuse_radiation"].round(1),
            "Kdir": sub["direct_radiation"].round(1),
            "Wd": 270,  # placeholder west wind (no forecast field for direction)
        }
    )

    header = (
        "%iy id it imin qn qh qe qs qf U RH Tair pres rain kdown snow ldown "
        "fcld wuh xsmd lai_hr Kdiff Kdir Wd"
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(header + "\n")
        out.to_csv(f, sep=" ", index=False, header=False, float_format="%.3f")

    print(f"[OK] wrote {out_path}: {len(out)} rows")
    print()
    print("Preview of forcing values:")
    print(
        out[["iy", "id", "it", "Tair", "RH", "U", "kdown", "Kdir", "Kdiff", "fcld"]].to_string(
            index=False
        )
    )
    print()
    print("Use this file as the 'Meteorological forcing' input in UMEP SOLWEIG.")


if __name__ == "__main__":
    main()
