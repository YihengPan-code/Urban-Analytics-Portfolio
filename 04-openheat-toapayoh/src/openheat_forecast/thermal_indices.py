"""Thermal index utilities for OpenHeat.

The functions here are intentionally labelled as screening-level approximations
unless official WBGT or physically simulated Tmrt is available.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

try:
    from pythermalcomfort.models import utci as _utci
except Exception:  # pragma: no cover
    _utci = None


def stull_wetbulb_c(t_c: np.ndarray | float, rh_percent: np.ndarray | float) -> np.ndarray:
    """Approximate wet-bulb temperature in Celsius using Stull (2011).

    Valid for typical near-surface meteorological ranges. This is not a
    substitute for natural wet-bulb temperature in official WBGT measurement.
    """
    T = np.asarray(t_c, dtype=float)
    RH = np.asarray(rh_percent, dtype=float)
    return (
        T * np.arctan(0.151977 * np.sqrt(RH + 8.313659))
        + np.arctan(T + RH)
        - np.arctan(RH - 1.676331)
        + 0.00391838 * RH ** 1.5 * np.arctan(0.023101 * RH)
        - 4.686035
    )


def estimate_local_microclimate(forecast_df: pd.DataFrame, grid_df: pd.DataFrame) -> pd.DataFrame:
    """Cross-join weather forecast and grid features, then estimate local Tair/Tmrt/wind.

    This is a physics-informed screening model, not a substitute for SOLWEIG,
    ENVI-met, CFD, or local sensor calibration. v0.6.4.1 tightens several
    empirical assumptions flagged in source-code review:
    - use pandas cross join instead of a temporary key;
    - keep high-GVI areas distinguishable up to roughly 60%;
    - use faster exponential park-cooling decay rather than an 800 m linear ramp;
    - cap local wind so the simple enclosure factor does not exceed background wind;
    - add a small low-SVF wall longwave term for dense canyon/HDB-cluster screening.
    """
    f = forecast_df.copy()
    g = grid_df.copy()
    try:
        df = f.merge(g, how="cross")
    except TypeError:  # pragma: no cover - compatibility with very old pandas
        f["_key"] = 1
        g["_key"] = 1
        df = f.merge(g, on="_key").drop(columns="_key")

    gvi_norm = np.clip(pd.to_numeric(df["gvi_percent"], errors="coerce") / 60.0, 0, 1)
    park_distance = pd.to_numeric(df["park_distance_m"], errors="coerce").clip(lower=0).fillna(9999)
    park_cooling = np.exp(-park_distance / 250.0).clip(0, 1)
    shortwave_norm = np.clip(pd.to_numeric(df["shortwave_radiation"], errors="coerce") / 900.0, 0, 1)

    df["tair_local_c"] = (
        pd.to_numeric(df["temperature_2m"], errors="coerce")
        + 1.15 * pd.to_numeric(df["building_density"], errors="coerce")
        + 0.85 * pd.to_numeric(df["road_fraction"], errors="coerce")
        - 0.75 * gvi_norm
        - 0.35 * park_cooling
    )

    ref_wind = pd.to_numeric(df["wind_speed_10m_ms"], errors="coerce").clip(lower=0)
    wind_raw = (
        ref_wind
        * (0.35 + 0.75 * pd.to_numeric(df["svf"], errors="coerce"))
        * (1.00 - 0.35 * pd.to_numeric(df["building_density"], errors="coerce"))
    )
    # In this simple screening model, urban morphology should not accelerate wind
    # above the background 10 m wind. A minimum keeps UTCI/WBGT calculations stable.
    df["wind_local_ms"] = np.minimum(wind_raw.clip(lower=0.15), ref_wind.clip(lower=0.15))

    svf = pd.to_numeric(df["svf"], errors="coerce")
    shade = pd.to_numeric(df["shade_fraction"], errors="coerce")
    sky_shortwave_gain = 22.0 * shortwave_norm * (1 - shade) * (0.45 + 0.75 * svf)
    wall_longwave_gain = 0.4 * (1 - svf) * np.maximum(df["tair_local_c"] - 26.0, 0)

    df["tmrt_proxy_c"] = (
        df["tair_local_c"]
        + sky_shortwave_gain
        + wall_longwave_gain
        - 1.2 * gvi_norm
    )

    # Expose diagnostic components so future reviewers can see what the proxy did.
    df["gvi_norm_for_screening"] = gvi_norm
    df["park_cooling_exp250"] = park_cooling
    df["tmrt_sky_shortwave_gain_c"] = sky_shortwave_gain
    df["tmrt_wall_longwave_gain_c"] = wall_longwave_gain

    return df


def calculate_utci_or_proxy(tair_c, tmrt_c, wind_ms, rh_percent):
    """Calculate UTCI using pythermalcomfort if present; otherwise return a proxy.

    The fallback proxy preserves ranking behaviour for demonstrations, not publication.
    """
    tair = np.asarray(tair_c, dtype=float)
    tmrt = np.asarray(tmrt_c, dtype=float)
    wind = np.asarray(wind_ms, dtype=float)
    rh = np.asarray(rh_percent, dtype=float)

    if _utci is not None:
        try:
            res = _utci(tdb=tair, tr=tmrt, v=np.maximum(wind, 0.5), rh=rh)
            # pythermalcomfort returns an object in recent versions
            return np.asarray(getattr(res, 'utci', res), dtype=float)
        except Exception:
            pass
    # fallback: intentionally simple heat-stress ranking proxy
    return tair + 0.46 * (tmrt - tair) + 0.055 * (rh - 50) - 1.15 * np.log1p(wind)


def wbgt_screening_proxy(tair_c, tmrt_c, wind_ms, rh_percent):
    """Screening-level outdoor WBGT proxy.

    Official WBGT requires natural wet-bulb and black-globe temperature measured
    or modelled properly. This approximation is only for hotspot prioritisation
    before calibration against official Singapore WBGT observations.
    """
    tair = np.asarray(tair_c, dtype=float)
    tmrt = np.asarray(tmrt_c, dtype=float)
    wind = np.asarray(wind_ms, dtype=float)
    rh = np.asarray(rh_percent, dtype=float)
    tw = stull_wetbulb_c(tair, rh)
    globe_proxy = tair + 0.32 * (tmrt - tair) - 0.55 * np.log1p(wind)
    return 0.7 * tw + 0.2 * globe_proxy + 0.1 * tair


def classify_wbgt_sg(wbgt_c: float) -> str:
    """Singapore-style public heat stress categories."""
    if wbgt_c < 31:
        return 'low'
    if wbgt_c < 33:
        return 'moderate'
    return 'high'


def classify_utci(utci_c: float) -> str:
    if utci_c < 26:
        return 'no heat stress'
    if utci_c < 32:
        return 'moderate heat stress'
    if utci_c < 38:
        return 'strong heat stress'
    if utci_c < 46:
        return 'very strong heat stress'
    return 'extreme heat stress'
