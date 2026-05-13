#!/usr/bin/env python
"""OpenHeat v1.1-beta.1 feature builder.

Reads v11 collector pairs CSV, ports v0.9 production WBGT proxy and time-aware
thermal-inertia features (lifted from scripts/v09_common.py and
scripts/v09_beta_fit_calibration_models.py).

Solves friend's audit items 5.1 (time-aware lag features) and 5.4 (production
proxy replacement) in a single pass.

Output: augmented pairs CSV ready for v11_beta_calibration_baselines.py.

Usage:
    python scripts/v11_beta_build_features.py \\
        --input data/calibration/v11/v11_station_weather_pairs.csv \\
        --output data/calibration/v11/v11_station_weather_pairs_v091.csv

This script does NOT touch:
- The collector or its config
- The cumulative long table
- archive_state.json
- Any data/archive/v11_longterm/ files

It only reads the canonical pairs CSV and writes a new augmented version.
The collector loop can keep running uninterrupted.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# v0.9 production WBGT proxy (lifted from scripts/v09_common.py)
# ---------------------------------------------------------------------------

def stull_wet_bulb_c(t_c, rh_percent):
    """Stull 2011 wet-bulb approximation. Lifted verbatim from v09_common.py."""
    t = np.asarray(t_c, dtype=float)
    rh = np.clip(np.asarray(rh_percent, dtype=float), 1, 100)
    return (
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * np.arctan(0.023101 * rh)
        - 4.686035
    )


def compute_v09_production_proxy(df: pd.DataFrame, output_col: str = "wbgt_proxy_v09_c") -> pd.DataFrame:
    """Compute v0.9 production WBGT proxy from Open-Meteo weather forcing.

    Lifted from v09_common.compute_wbgt_proxy_weather_only.

    Pure weather inputs. Adds three columns:
    - wetbulb_stull_c_v09:        Stull wet-bulb (overwrites if collector wrote one)
    - globe_temp_proxy_v09_c:     globe temperature proxy with wind-attenuated radiation
    - <output_col>:               final WBGT proxy (default: wbgt_proxy_v09_c)
    - proxy_source:               provenance tag

    Formula:
      Twb           = stull_wet_bulb_c(t, rh)
      globe_delta   = 0.0045 * sw / sqrt(wind + 0.25)
      Tg            = t + globe_delta
      WBGT          = 0.7 * Twb + 0.2 * Tg + 0.1 * t
                   = 0.7 * Twb + 0.3 * t + 0.0009 * sw / sqrt(wind + 0.25)
    """
    out = df.copy()
    required = {"temperature_2m", "relative_humidity_2m", "wind_speed_10m", "shortwave_radiation"}
    missing = required - set(out.columns)
    if missing:
        raise SystemExit(
            f"[ERROR] missing Open-Meteo columns required for v0.9 proxy: {sorted(missing)}. "
            f"Columns present: {list(out.columns)[:20]}..."
        )

    t = pd.to_numeric(out["temperature_2m"], errors="coerce")
    rh = pd.to_numeric(out["relative_humidity_2m"], errors="coerce")
    wind = pd.to_numeric(out["wind_speed_10m"], errors="coerce").clip(lower=0.1)
    sw = pd.to_numeric(out["shortwave_radiation"], errors="coerce").fillna(0).clip(lower=0)

    twb = stull_wet_bulb_c(t, rh)
    globe_delta = 0.0045 * sw / np.sqrt(wind + 0.25)
    tg = t + globe_delta
    wbgt = 0.7 * twb + 0.2 * tg + 0.1 * t

    out["wetbulb_stull_c_v09"] = twb
    out["globe_temp_proxy_v09_c"] = tg
    out[output_col] = wbgt
    out["proxy_source"] = "openheat_v09_weather_only"
    return out


# ---------------------------------------------------------------------------
# v0.9 thermal-inertia + period features
# (lifted from scripts/v09_beta_fit_calibration_models.add_time_and_inertia_features)
# ---------------------------------------------------------------------------

def classify_period(h: float) -> str:
    """v0.9 period classification used by M1b PeriodBiasModel."""
    if 7 <= h < 12:
        return "morning"
    if 12 <= h < 16:
        return "peak"
    if 16 <= h < 19:
        return "shoulder"
    return "night"


def add_v09_inertia_features(
    df: pd.DataFrame,
    ts_col: str = "timestamp_sgt",
    station_col: str = "station_id",
    proxy_col: str = "wbgt_proxy_v09_c",
) -> pd.DataFrame:
    """Add time + thermal-inertia features per (station, date) group.

    Lifted from v09_beta_fit_calibration_models.add_time_and_inertia_features.

    Lag features assume 15-min cadence (4 rows = 1h, 8 = 2h, 12 = 3h).
    Uses groupby([station, date]) so lags do NOT leak across midnight or stations.
    Fold-boundary NaNs filled with current-row values to avoid model crashes.

    Adds:
    - hour_sgt_numeric, date_sgt_derived
    - hour_sin_v09, hour_cos_v09
    - is_daytime_v09, is_peak_heat_v09, is_nighttime_v09
    - period_v09 (string: morning/peak/shoulder/night)
    - direct_fraction, diffuse_fraction, shortwave_positive
    - shortwave_lag_1h, shortwave_lag_2h, shortwave_3h_mean
    - cumulative_day_shortwave_whm2 (per-day cumulative, in W*h/m^2)
    - temperature_lag_1h, dTair_dt_1h
    - proxy_lag_1h, proxy_3h_mean
    """
    df = df.copy()
    if ts_col not in df.columns:
        # Fall back to "timestamp" if collector pairs use different name
        if "timestamp" in df.columns:
            ts_col = "timestamp"
        else:
            raise SystemExit(f"[ERROR] no timestamp column found ({ts_col} or timestamp)")

    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    n_before = len(df)
    df = df[df[ts_col].notna()].copy()
    if len(df) < n_before:
        print(f"[WARN] dropped {n_before - len(df)} rows with NaT timestamp")

    # Time features
    df["hour_sgt_numeric"] = df[ts_col].dt.hour + df[ts_col].dt.minute / 60.0
    df["date_sgt_derived"] = df[ts_col].dt.strftime("%Y-%m-%d")
    df["hour_sin_v09"] = np.sin(2 * np.pi * df["hour_sgt_numeric"] / 24.0)
    df["hour_cos_v09"] = np.cos(2 * np.pi * df["hour_sgt_numeric"] / 24.0)
    df["is_daytime_v09"] = ((df["hour_sgt_numeric"] >= 7) & (df["hour_sgt_numeric"] < 19)).astype(int)
    df["is_peak_heat_v09"] = ((df["hour_sgt_numeric"] >= 12) & (df["hour_sgt_numeric"] < 16)).astype(int)
    df["is_nighttime_v09"] = ((df["hour_sgt_numeric"] < 7) | (df["hour_sgt_numeric"] >= 19)).astype(int)
    df["period_v09"] = df["hour_sgt_numeric"].apply(classify_period)

    # Robust numeric cast on weather columns
    weather_cols = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m",
                    "shortwave_radiation", "direct_radiation", "diffuse_radiation",
                    "cloud_cover", "official_wbgt_c"]
    for c in weather_cols + [proxy_col]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Direct/diffuse fractions (regime features)
    sw = df.get("shortwave_radiation", pd.Series(0.0, index=df.index)).fillna(0)
    direct = df.get("direct_radiation", pd.Series(0.0, index=df.index)).fillna(0)
    diffuse = df.get("diffuse_radiation", pd.Series(0.0, index=df.index)).fillna(0)
    # Avoid division by tiny values
    df["direct_fraction"] = np.where(sw > 1, direct / sw.replace(0, np.nan), 0.0)
    df["diffuse_fraction"] = np.where(sw > 1, diffuse / sw.replace(0, np.nan), 0.0)
    df["direct_fraction"] = pd.to_numeric(df["direct_fraction"], errors="coerce").fillna(0).clip(0, 1)
    df["diffuse_fraction"] = pd.to_numeric(df["diffuse_fraction"], errors="coerce").fillna(0).clip(0, 1)
    df["shortwave_positive"] = (sw > 20).astype(int)

    # Sort by (station, date, ts) and groupby (station, date) for lag features
    sort_cols = [station_col, "date_sgt_derived", ts_col]
    df = df.sort_values(sort_cols).reset_index(drop=True)
    grp_cols = [station_col, "date_sgt_derived"]
    grp = df.groupby(grp_cols, sort=False, group_keys=False)

    # 15-min cadence: 4 rows = 1h, 8 = 2h, 12 = 3h
    df["shortwave_lag_1h"] = grp["shortwave_radiation"].shift(4)
    df["shortwave_lag_2h"] = grp["shortwave_radiation"].shift(8)
    df["shortwave_3h_mean"] = grp["shortwave_radiation"].apply(
        lambda s: s.rolling(window=12, min_periods=1).mean()
    )
    # Per-day cumulative shortwave: each 15-min row contributes 0.25 hours of energy
    df["cumulative_day_shortwave_whm2"] = grp["shortwave_radiation"].apply(
        lambda s: s.fillna(0).cumsum() * 0.25
    )
    df["temperature_lag_1h"] = grp["temperature_2m"].shift(4)
    df["dTair_dt_1h"] = df["temperature_2m"] - df["temperature_lag_1h"]

    if proxy_col in df.columns:
        df["proxy_lag_1h"] = grp[proxy_col].shift(4)
        df["proxy_3h_mean"] = grp[proxy_col].apply(
            lambda s: s.rolling(window=12, min_periods=1).mean()
        )

    # Fill fold-boundary NaNs with current-row values (avoid imputer drops)
    for c in ["shortwave_lag_1h", "shortwave_lag_2h", "shortwave_3h_mean"]:
        if c in df.columns:
            df[c] = df[c].fillna(df.get("shortwave_radiation", 0))
    if "temperature_lag_1h" in df.columns:
        df["temperature_lag_1h"] = df["temperature_lag_1h"].fillna(df.get("temperature_2m", np.nan))
    if "dTair_dt_1h" in df.columns:
        df["dTair_dt_1h"] = df["dTair_dt_1h"].fillna(0)
    if "proxy_lag_1h" in df.columns:
        df["proxy_lag_1h"] = df["proxy_lag_1h"].fillna(df[proxy_col])
    if "proxy_3h_mean" in df.columns:
        df["proxy_3h_mean"] = df["proxy_3h_mean"].fillna(df[proxy_col])

    # Residual diagnostic for downstream reports
    if "official_wbgt_c" in df.columns and proxy_col in df.columns:
        df["residual_official_minus_v09_proxy_c"] = df["official_wbgt_c"] - df[proxy_col]

    return df


# ---------------------------------------------------------------------------
# Pairing flag derivation (β.1 post-mortem fix)
# ---------------------------------------------------------------------------

def derive_pairing_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Derive properly-scoped pairing flags for retrospective calibration.

    Background: the collector-level `pair_used_for_calibration` flag is defined as
        pair_used_for_calibration = has_weather_match & (abs_issue_age_hours <= 72)

    This conflates two semantics:
      (a) Valid-time alignment: does weather forcing exist at the observation
          timestamp? (required for ANY calibration)
      (b) Forecast issue freshness: was the forecast issued within 72h of the
          observation? (only required for OPERATIONAL evaluation)

    For RETROSPECTIVE calibration (v1.1-beta and beta.1), only (a) matters.
    Open-Meteo hindcast returns the best estimate at valid_time regardless of
    when the forecast was issued; issue age is a property of the forecast
    delivery pipeline, not of the valid_time vs obs_time alignment.

    For OPERATIONAL forecast evaluation (future v1.1-delta), both (a) and (b)
    matter (we ask: "given a forecast we'd have in real-time, how accurate?").

    This function adds two properly-scoped flags:
      - pair_used_for_retrospective_calibration: just has_weather_match +
        non-null core weather columns
      - is_migrated_archive: True for rows from v0.9/v10 archive migration
        (used in ablation experiments)
    """
    out = df.copy()

    # 1. Retrospective calibration eligibility = valid-time alignment only
    core_weather = ["temperature_2m", "relative_humidity_2m",
                    "wind_speed_10m", "shortwave_radiation"]
    weather_ok = pd.Series(True, index=out.index)
    for c in core_weather:
        if c in out.columns:
            weather_ok = weather_ok & out[c].notna()
        else:
            print(f"[WARN] core weather column {c} missing from pairs; "
                  f"retrospective flag will be False for all rows")
            weather_ok = pd.Series(False, index=out.index)
            break

    has_match = out.get("has_weather_match", pd.Series(True, index=out.index))
    if not pd.api.types.is_bool_dtype(has_match):
        has_match = has_match.fillna(False).astype(bool)
    out["pair_used_for_retrospective_calibration"] = (has_match & weather_ok).values

    # 2. Migration source flag (for stale-dilution ablation)
    if "archive_run_id" in out.columns:
        run_id = out["archive_run_id"].astype(str)
        # Fresh v11 collector rows have archive_run_id like "v11_YYYYMMDD_HHMMSSZ"
        out["is_migrated_archive"] = ~run_id.str.startswith("v11_", na=False)
    else:
        out["is_migrated_archive"] = False

    # Diagnostic comparison with collector's existing flag
    n_total = len(out)
    n_retro = int(out["pair_used_for_retrospective_calibration"].sum())
    n_migrated = int(out["is_migrated_archive"].sum())
    print(f"  retrospective_calibration eligible:  {n_retro:>6,} / {n_total:,} ({n_retro*100.0/max(n_total,1):.1f}%)")
    print(f"  migrated archive rows:               {n_migrated:>6,} / {n_total:,} ({n_migrated*100.0/max(n_total,1):.1f}%)")
    if "pair_used_for_calibration" in out.columns:
        n_old = int(out["pair_used_for_calibration"].sum())
        print(f"  collector pair_used_for_calibration: {n_old:>6,} / {n_total:,} ({n_old*100.0/max(n_total,1):.1f}%)")
        gained = n_retro - n_old
        print(f"  retrospective − collector_pair_used: {gained:+,}  (rows recovered by relaxing issue_age filter)")

    return out

def proxy_diagnostic(df: pd.DataFrame) -> None:
    """Compare v0.9 production proxy vs collector's existing fallback proxies."""
    target = "official_wbgt_c"
    if target not in df.columns:
        print("[INFO] no official_wbgt_c column; skipping proxy comparison")
        return

    candidates = [
        ("wbgt_proxy_v09_c", "v0.9 production (Stull + globe-T with wind attenuation)"),
        ("raw_proxy_wbgt_radiative_fallback_c", "v1.1 collector fallback (linear SW + linear wind cooling)"),
        ("raw_proxy_wbgt_fallback_c", "v1.1 collector fallback (Stull only, no SW)"),
    ]
    rows = []
    for col, label in candidates:
        if col not in df.columns:
            continue
        valid = df[target].notna() & df[col].notna()
        if valid.sum() < 10:
            continue
        diff = df.loc[valid, col] - df.loc[valid, target]
        rows.append({
            "proxy_col": col,
            "label": label,
            "n": int(valid.sum()),
            "bias_c": diff.mean(),
            "mae_c": diff.abs().mean(),
            "rmse_c": np.sqrt((diff ** 2).mean()),
        })
    if not rows:
        return

    print()
    print("[diagnostic] proxy comparison vs official_wbgt_c:")
    print(f"  {'column':<45} {'n':>6} {'bias':>9} {'mae':>9} {'rmse':>9}")
    for r in rows:
        print(f"  {r['proxy_col']:<45} {r['n']:>6,} {r['bias_c']:>+8.3f}°C {r['mae_c']:>8.3f}°C {r['rmse_c']:>8.3f}°C")
    print()
    print("  (Lower MAE/RMSE is better. Negative bias = proxy under-predicts.")
    print("   v0.9 baseline expected to have larger negative bias but tighter regime response.)")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build v0.9-style production proxy + lag features on v11 collector pairs."
    )
    parser.add_argument(
        "--input",
        default="data/calibration/v11/v11_station_weather_pairs.csv",
        help="path to v11 collector pairs CSV",
    )
    parser.add_argument(
        "--output",
        default="data/calibration/v11/v11_station_weather_pairs_v091.csv",
        help="output augmented pairs CSV",
    )
    parser.add_argument(
        "--proxy-col",
        default="wbgt_proxy_v09_c",
        help="output column name for v0.9 production proxy",
    )
    parser.add_argument(
        "--ts-col",
        default="timestamp_sgt",
        help="timestamp column name (try this first; falls back to 'timestamp')",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        print(f"[ERROR] input not found: {in_path}", file=sys.stderr)
        return 2

    print(f"[load] {in_path}")
    df = pd.read_csv(in_path, low_memory=False)
    print(f"       {len(df):,} rows × {len(df.columns)} cols")

    print()
    print("[step 1/2] computing v0.9 production WBGT proxy (weather-only)...")
    df = compute_v09_production_proxy(df, output_col=args.proxy_col)

    print()
    print("[step 2/3] computing v0.9 thermal-inertia + period features...")
    df = add_v09_inertia_features(df, ts_col=args.ts_col, proxy_col=args.proxy_col)

    print()
    print("[step 3/3] deriving retrospective_calibration + migration flags...")
    df = derive_pairing_flags(df)

    proxy_diagnostic(df)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[write] {out_path}")
    df.to_csv(out_path, index=False)
    print(f"        {len(df):,} rows × {len(df.columns)} cols")
    print()
    print("[DONE] v0.9 features added. New columns include:")
    print(f"       {args.proxy_col}, wetbulb_stull_c_v09, globe_temp_proxy_v09_c,")
    print(f"       hour_sin_v09, hour_cos_v09, period_v09,")
    print(f"       shortwave_lag_1h, shortwave_lag_2h, shortwave_3h_mean,")
    print(f"       cumulative_day_shortwave_whm2, temperature_lag_1h, dTair_dt_1h,")
    print(f"       proxy_lag_1h, proxy_3h_mean, direct_fraction, diffuse_fraction")
    print()
    print("Next: run v11_beta_calibration_baselines.py with config that points to this CSV")
    print("       and uses raw_proxy_col = '" + args.proxy_col + "'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
