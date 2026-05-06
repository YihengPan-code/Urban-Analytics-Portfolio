"""Thermal index utilities for OpenHeat v0.5.

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

    v0.5 logic:
    - Tair is adjusted by built density, road fraction and greenery.
    - Wind is reduced by urban enclosure and SVF.
    - Tmrt is approximated from shortwave radiation, shade fraction and SVF.

    This is for prioritisation/prototyping only. Replace with SOLWEIG/UMEP in v0.8+.
    """
    f = forecast_df.copy()
    g = grid_df.copy()
    f['_key'] = 1
    g['_key'] = 1
    df = f.merge(g, on='_key').drop(columns='_key')

    gvi_norm = np.clip(df['gvi_percent'] / 40.0, 0, 1)
    park_cooling = np.clip((800 - df['park_distance_m']) / 800.0, 0, 1)
    shortwave_norm = np.clip(df['shortwave_radiation'] / 900.0, 0, 1)

    df['tair_local_c'] = (
        df['temperature_2m']
        + 1.15 * df['building_density']
        + 0.85 * df['road_fraction']
        - 0.75 * gvi_norm
        - 0.35 * park_cooling
    )

    df['wind_local_ms'] = (
        df['wind_speed_10m_ms']
        * (0.35 + 0.75 * df['svf'])
        * (1.00 - 0.35 * df['building_density'])
    ).clip(lower=0.15)

    df['tmrt_proxy_c'] = (
        df['tair_local_c']
        + 22.0 * shortwave_norm * (1 - df['shade_fraction']) * (0.45 + 0.75 * df['svf'])
        - 1.2 * gvi_norm
    )

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
