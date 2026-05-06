"""Operational v0.6 pipeline entry points."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from .hotspot_engine import run_grid_forecast, summarize_hotspots, detect_event_windows
from .live_api import (
    fetch_openmeteo_forecast,
    fetch_air_temperature,
    fetch_relative_humidity,
    fetch_wind_speed,
    fetch_official_wbgt,
    merge_latest_station_observations,
    attach_nearest_station,
)

TOA_PAYOH_CENTRE_LAT = 1.3343
TOA_PAYOH_CENTRE_LON = 103.8563


def run_forecast_from_openmeteo(grid_csv: str | Path, *, out_dir: str | Path = "outputs", lat: float = TOA_PAYOH_CENTRE_LAT, lon: float = TOA_PAYOH_CENTRE_LON, forecast_days: int = 4) -> dict[str, Path]:
    """Fetch Open-Meteo and run the Toa Payoh grid hotspot engine."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    grid = pd.read_csv(grid_csv)
    forecast = fetch_openmeteo_forecast(lat, lon, forecast_days=forecast_days)
    hourly = run_grid_forecast(forecast, grid)
    ranking = summarize_hotspots(hourly)
    events = detect_event_windows(hourly)
    files = {
        "raw_forecast": out_path / "v06_live_openmeteo_forecast_raw.csv",
        "forecast": out_path / "v06_live_hourly_grid_heatstress_forecast.csv",
        "hotspots": out_path / "v06_live_hotspot_ranking.csv",
        "events": out_path / "v06_live_event_windows.csv",
    }
    forecast.to_csv(files["raw_forecast"], index=False)
    hourly.to_csv(files["forecast"], index=False)
    ranking.to_csv(files["hotspots"], index=False)
    events.to_csv(files["events"], index=False)
    return files


def run_offline_sample_forecast(forecast_csv: str | Path, grid_csv: str | Path, *, out_dir: str | Path = "outputs", prefix: str = "v06_offline") -> dict[str, Path]:
    """Run the v0.6 engine using local sample CSVs so the repo is reproducible offline."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    forecast = pd.read_csv(forecast_csv)
    grid = pd.read_csv(grid_csv)
    hourly = run_grid_forecast(forecast, grid)
    ranking = summarize_hotspots(hourly)
    events = detect_event_windows(hourly)
    files = {
        "forecast": out_path / f"{prefix}_hourly_grid_heatstress_forecast.csv",
        "hotspots": out_path / f"{prefix}_hotspot_ranking.csv",
        "events": out_path / f"{prefix}_event_windows.csv",
    }
    hourly.to_csv(files["forecast"], index=False)
    ranking.to_csv(files["hotspots"], index=False)
    events.to_csv(files["events"], index=False)
    return files


def fetch_latest_nea_observation_bundle(**kwargs) -> pd.DataFrame:
    """Fetch latest NEA air temperature/RH/wind/WBGT and merge by station."""
    air = fetch_air_temperature(**kwargs)
    rh = fetch_relative_humidity(**kwargs)
    wind = fetch_wind_speed(**kwargs)
    wbgt = fetch_official_wbgt(**kwargs)
    return merge_latest_station_observations(air, rh, wind, wbgt)


def attach_nearest_nea_stations_to_grid(grid_csv: str | Path, observations_df: pd.DataFrame) -> pd.DataFrame:
    grid = pd.read_csv(grid_csv)
    return attach_nearest_station(grid, observations_df)
