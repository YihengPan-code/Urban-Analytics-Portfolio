"""Operational pipeline entry points for OpenHeat."""
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


def run_forecast_from_openmeteo(
    grid_csv: str | Path,
    *,
    out_dir: str | Path = "outputs",
    lat: float = TOA_PAYOH_CENTRE_LAT,
    lon: float = TOA_PAYOH_CENTRE_LON,
    forecast_days: int = 4,
) -> dict[str, Path]:
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


def run_offline_sample_forecast(
    forecast_csv: str | Path,
    grid_csv: str | Path,
    *,
    out_dir: str | Path = "outputs",
    prefix: str = "v06_offline",
) -> dict[str, Path]:
    """Run the engine using local sample CSVs so the repo is reproducible offline."""
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
    """Fetch latest NEA air temperature/RH/wind/WBGT and merge by station.

    This wide table is useful for quick inspection. It is not used for archive in
    v0.6.4 because station coverage differs by API and wide outer merges can
    lose variable-specific timestamps/metadata.
    """
    air = fetch_air_temperature(**kwargs)
    rh = fetch_relative_humidity(**kwargs)
    wind = fetch_wind_speed(**kwargs)
    wbgt = fetch_official_wbgt(**kwargs)
    return merge_latest_station_observations(air, rh, wind, wbgt)


def _standard_archive_columns() -> list[str]:
    return [
        "archive_run_utc",
        "archive_source",
        "archive_status",
        "api_name",
        "variable",
        "value",
        "unit",
        "timestamp",
        "record_updated_timestamp",
        "station_id",
        "device_id",
        "station_name",
        "station_town_center",
        "station_lat",
        "station_lon",
        "heat_stress_category",
        "reading_type",
        "reading_unit",
        "api_version",
        "endpoint_url",
        "fetch_timestamp_utc",
        "value_missing",
    ]


def _col_or_na(df: pd.DataFrame, col: str):
    return df[col] if col in df.columns else pd.Series(pd.NA, index=df.index)


def station_observations_to_long(df: pd.DataFrame, *, variable: str, value_col: str, unit: str) -> pd.DataFrame:
    """Convert one normalised NEA station dataframe to archive-safe long format.

    Each row is one station-variable-timestamp observation. This avoids the
    v0.6.3 problem where WBGT metadata could be dropped when multiple NEA APIs
    were merged into one wide table.
    """
    cols = _standard_archive_columns()
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    d = df.copy()
    if value_col not in d.columns:
        d[value_col] = pd.NA

    out = pd.DataFrame({
        "api_name": _col_or_na(d, "api_name"),
        "variable": variable,
        "value": pd.to_numeric(d[value_col], errors="coerce"),
        "unit": unit,
        "timestamp": _col_or_na(d, "timestamp"),
        "record_updated_timestamp": _col_or_na(d, "record_updated_timestamp"),
        "station_id": _col_or_na(d, "station_id"),
        "device_id": _col_or_na(d, "device_id"),
        "station_name": _col_or_na(d, "station_name"),
        "station_town_center": _col_or_na(d, "station_town_center"),
        "station_lat": pd.to_numeric(_col_or_na(d, "station_lat"), errors="coerce"),
        "station_lon": pd.to_numeric(_col_or_na(d, "station_lon"), errors="coerce"),
        "heat_stress_category": _col_or_na(d, "heat_stress_category"),
        "reading_type": _col_or_na(d, "reading_type"),
        "reading_unit": _col_or_na(d, "reading_unit"),
        "api_version": _col_or_na(d, "api_version"),
        "endpoint_url": _col_or_na(d, "endpoint_url"),
        "fetch_timestamp_utc": _col_or_na(d, "fetch_timestamp_utc"),
        "value_missing": _col_or_na(d, "value_missing"),
    })
    if out["value_missing"].isna().all():
        out["value_missing"] = out["value"].isna()
    else:
        out["value_missing"] = out["value_missing"].fillna(out["value"].isna())
    for c in cols:
        if c not in out.columns:
            out[c] = pd.NA
    return out[cols]


def fetch_latest_nea_observation_long_bundle(**kwargs) -> pd.DataFrame:
    """Fetch latest NEA readings and return archive-safe long-format rows."""
    frames = [
        station_observations_to_long(
            fetch_air_temperature(**kwargs),
            variable="air_temperature_c",
            value_col="air_temperature_c",
            unit="deg C",
        ),
        station_observations_to_long(
            fetch_relative_humidity(**kwargs),
            variable="relative_humidity_percent",
            value_col="relative_humidity_percent",
            unit="percent",
        ),
        station_observations_to_long(
            fetch_wind_speed(**kwargs),
            variable="wind_speed_ms",
            value_col="wind_speed_ms",
            unit="m/s",
        ),
        station_observations_to_long(
            fetch_official_wbgt(**kwargs),
            variable="official_wbgt_c",
            value_col="official_wbgt_c",
            unit="deg C",
        ),
    ]
    non_empty = [x for x in frames if x is not None and not x.empty]
    if not non_empty:
        return pd.DataFrame(columns=_standard_archive_columns())
    return pd.concat(non_empty, ignore_index=True)



def filter_wbgt_station_observations(observations_df: pd.DataFrame) -> pd.DataFrame:
    """Return only station rows that contain official WBGT and station coordinates.

    Calibration nearest-neighbour matching must use the WBGT station network, not
    a merged all-weather-station network, because air temperature/RH/wind stations
    may be more numerous than WBGT stations. Supports both wide parser output and
    v0.6.4+ long-format archive rows.
    """
    if observations_df is None or observations_df.empty:
        return pd.DataFrame()
    df = observations_df.copy()
    if "variable" in df.columns:
        df = df[df["variable"].astype(str).eq("official_wbgt_c")].copy()
        if "official_wbgt_c" not in df.columns and "value" in df.columns:
            df["official_wbgt_c"] = pd.to_numeric(df["value"], errors="coerce")
    elif "official_wbgt_c" not in df.columns:
        return pd.DataFrame()
    required = ["official_wbgt_c", "station_lat", "station_lon"]
    for c in required:
        if c not in df.columns:
            return pd.DataFrame()
    return df.dropna(subset=required).copy()

def attach_nearest_nea_stations_to_grid(grid_csv: str | Path, observations_df: pd.DataFrame) -> pd.DataFrame:
    """Attach nearest official WBGT station to grid cells for calibration.

    Despite the historical function name, v0.6.4.1 filters to WBGT-only rows to
    avoid accidentally selecting a nearer non-WBGT air-temperature station.
    """
    grid = pd.read_csv(grid_csv)
    wbgt_stations = filter_wbgt_station_observations(observations_df)
    if wbgt_stations.empty:
        raise ValueError("No official WBGT station rows with coordinates available for calibration matching.")
    return attach_nearest_station(grid, wbgt_stations)


def attach_nearest_wbgt_station_to_grid(grid_csv: str | Path, wbgt_observations_df: pd.DataFrame) -> pd.DataFrame:
    """Explicit alias for WBGT-only nearest-station matching."""
    return attach_nearest_nea_stations_to_grid(grid_csv, wbgt_observations_df)
