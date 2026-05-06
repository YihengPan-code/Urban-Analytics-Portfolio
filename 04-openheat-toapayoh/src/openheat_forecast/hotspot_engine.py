"""Hotspot ranking engine for OpenHeat v0.5."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .thermal_indices import (
    estimate_local_microclimate,
    calculate_utci_or_proxy,
    wbgt_screening_proxy,
    classify_wbgt_sg,
    classify_utci,
)


def run_grid_forecast(forecast_df: pd.DataFrame, grid_df: pd.DataFrame) -> pd.DataFrame:
    df = estimate_local_microclimate(forecast_df, grid_df)
    df['utci_c'] = calculate_utci_or_proxy(
        df['tair_local_c'], df['tmrt_proxy_c'], df['wind_local_ms'], df['relative_humidity_2m']
    )
    df['wbgt_proxy_c'] = wbgt_screening_proxy(
        df['tair_local_c'], df['tmrt_proxy_c'], df['wind_local_ms'], df['relative_humidity_2m']
    )
    df['wbgt_category_sg'] = df['wbgt_proxy_c'].apply(classify_wbgt_sg)
    df['utci_category'] = df['utci_c'].apply(classify_utci)
    # Useful binary flags
    df['wbgt_moderate_or_high'] = df['wbgt_proxy_c'] >= 31
    df['wbgt_high'] = df['wbgt_proxy_c'] >= 33
    df['utci_strong_or_higher'] = df['utci_c'] >= 32
    return df


def summarize_hotspots(grid_forecast_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse hourly grid forecast to hotspot ranking per cell."""
    g = grid_forecast_df.groupby('cell_id', as_index=False).agg(
        lat=('lat', 'first'),
        lon=('lon', 'first'),
        land_use_hint=('land_use_hint', 'first'),
        max_utci_c=('utci_c', 'max'),
        mean_utci_c=('utci_c', 'mean'),
        max_wbgt_proxy_c=('wbgt_proxy_c', 'max'),
        moderate_wbgt_hours=('wbgt_moderate_or_high', 'sum'),
        high_wbgt_hours=('wbgt_high', 'sum'),
        strong_utci_hours=('utci_strong_or_higher', 'sum'),
        gvi_percent=('gvi_percent', 'first'),
        svf=('svf', 'first'),
        shade_fraction=('shade_fraction', 'first'),
        building_density=('building_density', 'first'),
        road_fraction=('road_fraction', 'first'),
        elderly_proxy=('elderly_proxy', 'first'),
        outdoor_exposure_proxy=('outdoor_exposure_proxy', 'first'),
    )
    # Hazard component: scaled from hours and intensity
    g['hazard_score'] = (
        0.45 * np.clip((g['max_wbgt_proxy_c'] - 29.5) / 4.0, 0, 1)
        + 0.35 * np.clip(g['moderate_wbgt_hours'] / 18.0, 0, 1)
        + 0.20 * np.clip(g['strong_utci_hours'] / 24.0, 0, 1)
    )
    g['vulnerability_score'] = g['elderly_proxy'].rank(pct=True)
    g['exposure_score'] = g['outdoor_exposure_proxy'].rank(pct=True)
    g['risk_priority_score'] = (
        0.62 * g['hazard_score']
        + 0.23 * g['vulnerability_score']
        + 0.15 * g['exposure_score']
    )
    g = g.sort_values('risk_priority_score', ascending=False)
    g['rank'] = range(1, len(g) + 1)
    return g


def detect_event_windows(grid_forecast_df: pd.DataFrame) -> pd.DataFrame:
    """Summarise heat-stress event timing across the neighbourhood."""
    h = grid_forecast_df.groupby('time', as_index=False).agg(
        max_wbgt_proxy_c=('wbgt_proxy_c', 'max'),
        p90_wbgt_proxy_c=('wbgt_proxy_c', lambda x: x.quantile(0.9)),
        cells_moderate_or_high=('wbgt_moderate_or_high', 'sum'),
        cells_high=('wbgt_high', 'sum'),
        max_utci_c=('utci_c', 'max'),
        cells_strong_utci=('utci_strong_or_higher', 'sum'),
    )
    h['neighbourhood_alert'] = np.select(
        [h['cells_high'] > 0, h['cells_moderate_or_high'] >= 8],
        ['high', 'moderate'],
        default='low'
    )
    return h
