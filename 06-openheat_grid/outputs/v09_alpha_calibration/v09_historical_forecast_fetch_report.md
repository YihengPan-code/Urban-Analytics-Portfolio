# OpenHeat v0.9-alpha Open-Meteo historical forcing fetch report

API used: **historical_forecast**
Date range: **2026-05-07 → 2026-05-08**
Stations: **27**
Rows: **1296**
Output: `data\calibration\v09_historical_forecast_by_station_hourly.csv`

## Variables
temperature_2m, relative_humidity_2m, wind_speed_10m, shortwave_radiation, direct_radiation, diffuse_radiation, cloud_cover

## Notes
- Historical Forecast API is preferred for forecast-like calibration. Historical Weather API is used only as fallback.
- Radiation variables available may differ between APIs; check missing columns before modelling.