@echo off
setlocal

REM ==========================================================
REM OpenHeat v0.9-alpha calibration data pipeline
REM Run from project root: 06-openheat_grid
REM ==========================================================

set CONFIG=configs\v09_alpha_config.example.json

if not exist %CONFIG% (
  echo [ERROR] Config not found: %CONFIG%
  pause
  exit /b 1
)

if not exist data\archive\nea_realtime_observations.csv (
  echo [ERROR] Missing data\archive\nea_realtime_observations.csv
  echo Copy your 24h NEA archive there before running this pipeline.
  pause
  exit /b 1
)

python scripts\v09_archive_qa.py --config %CONFIG%
if errorlevel 1 goto :error

python scripts\v09_fetch_historical_forecast_for_archive.py --config %CONFIG% --api auto
if errorlevel 1 goto :error

python scripts\v09_build_wbgt_station_pairs.py --config %CONFIG%
if errorlevel 1 goto :error

python scripts\v09_evaluate_wbgt_pairs_baseline.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [OK] v0.9-alpha pipeline completed.
echo Check outputs\v09_alpha_calibration\
echo and data\calibration\v09_wbgt_station_pairs.csv
exit /b 0

:error
echo.
echo [ERROR] v0.9-alpha pipeline failed.
pause
exit /b 1
