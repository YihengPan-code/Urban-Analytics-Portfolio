"""Data-source helpers for OpenHeat.

This module keeps v0.5 function names and re-exports v0.6 live API functions.
"""
from __future__ import annotations
import pandas as pd

from .live_api import fetch_openmeteo_forecast, fetch_official_wbgt, fetch_datagov_realtime_api


def load_sample_forecast(path='data/sample/openmeteo_heatwave_forecast_sample.csv') -> pd.DataFrame:
    return pd.read_csv(path)


def load_sample_grid(path='data/sample/toa_payoh_grid_sample.csv') -> pd.DataFrame:
    return pd.read_csv(path)


def fetch_singapore_realtime_wbgt() -> dict:
    """Backward-compatible raw official WBGT fetcher."""
    return fetch_datagov_realtime_api('wbgt')
