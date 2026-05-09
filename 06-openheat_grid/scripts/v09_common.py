from __future__ import annotations

import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

SGT = ZoneInfo("Asia/Singapore")


def load_config(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def to_sgt_series(s: pd.Series) -> pd.Series:
    dt = pd.to_datetime(s, errors="coerce")
    # pandas returns object dtype if mixed tz; use elementwise fallback if needed
    try:
        if getattr(dt.dt, "tz", None) is None:
            return dt.dt.tz_localize(SGT)
        return dt.dt.tz_convert(SGT)
    except Exception:
        out = []
        for x in s:
            tx = pd.to_datetime(x, errors="coerce")
            if pd.isna(tx):
                out.append(pd.NaT)
            elif tx.tzinfo is None:
                out.append(tx.tz_localize(SGT))
            else:
                out.append(tx.tz_convert(SGT))
        return pd.Series(out, index=s.index)


def robust_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def station_table_from_archive(archive: pd.DataFrame, variable: str = "official_wbgt_c") -> pd.DataFrame:
    x = archive[archive["variable"].eq(variable)].copy()
    keep = [
        "station_id", "station_name", "station_town_center", "station_lat", "station_lon"
    ]
    keep = [c for c in keep if c in x.columns]
    stations = x[keep].drop_duplicates("station_id").copy()
    stations["station_lat"] = robust_numeric(stations["station_lat"])
    stations["station_lon"] = robust_numeric(stations["station_lon"])
    stations = stations.dropna(subset=["station_id", "station_lat", "station_lon"])
    return stations.reset_index(drop=True)


def stull_wet_bulb_c(t_c, rh_percent):
    """Stull 2011 wet-bulb approximation. Valid for ordinary near-surface conditions."""
    t = np.asarray(t_c, dtype=float)
    rh = np.clip(np.asarray(rh_percent, dtype=float), 1, 100)
    return (
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * np.arctan(0.023101 * rh)
        - 4.686035
    )


def compute_wbgt_proxy_weather_only(df: pd.DataFrame) -> pd.DataFrame:
    """Compute a screening-level WBGT proxy from met forcing.

    This is NOT official WBGT. It is intended as a physics-informed baseline for
    residual calibration against official NEA WBGT.
    """
    out = df.copy()
    t = robust_numeric(out.get("temperature_2m"))
    rh = robust_numeric(out.get("relative_humidity_2m"))
    wind = robust_numeric(out.get("wind_speed_10m")).clip(lower=0.1)
    sw = robust_numeric(out.get("shortwave_radiation")).fillna(0).clip(lower=0)

    twb = stull_wet_bulb_c(t, rh)
    # Conservative globe-temperature proxy. Radiation term is empirical and should be calibrated.
    globe_delta = 0.0045 * sw / np.sqrt(wind + 0.25)
    tg = t + globe_delta
    wbgt = 0.7 * twb + 0.2 * tg + 0.1 * t

    out["wetbulb_stull_c"] = twb
    out["globe_temp_proxy_weather_only_c"] = tg
    out["wbgt_proxy_weather_only_c"] = wbgt
    return out


def add_wbgt_categories(df: pd.DataFrame, value_col: str, out_col: str) -> pd.DataFrame:
    out = df.copy()
    x = robust_numeric(out[value_col])
    out[out_col] = np.select(
        [x >= 33, x >= 31],
        ["High", "Moderate"],
        default="Low",
    )
    out.loc[x.isna(), out_col] = pd.NA
    return out


def metrics(y_true, y_pred):
    y = pd.to_numeric(y_true, errors="coerce")
    p = pd.to_numeric(y_pred, errors="coerce")
    mask = y.notna() & p.notna()
    if mask.sum() == 0:
        return {"n": 0, "bias": np.nan, "mae": np.nan, "rmse": np.nan}
    err = p[mask] - y[mask]
    return {
        "n": int(mask.sum()),
        "bias_pred_minus_obs": float(err.mean()),
        "mae": float(err.abs().mean()),
        "rmse": float(np.sqrt((err ** 2).mean())),
        "p90_abs_error": float(err.abs().quantile(0.9)),
    }
