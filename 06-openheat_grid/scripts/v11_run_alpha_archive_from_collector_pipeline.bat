@echo off
setlocal

set CONFIG=configs\v11\v11_alpha_archive_config.example.json

echo ============================================================
echo OpenHeat v1.1-alpha archive QA from collector authoritative pairs
echo Config: %CONFIG%
echo ============================================================
echo This pipeline assumes the v11 collector has already written:
echo   data\calibration\v11\v11_station_weather_pairs.csv
echo It intentionally SKIPS legacy v11_alpha_build_pairs.py.
echo ============================================================

echo [1/3] Archive inventory...
python scripts\v11_alpha_archive_inventory.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [2/3] Archive QA on collector paired dataset...
python scripts\v11_alpha_archive_qa.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [3/3] Make CV splits...
python scripts\v11_alpha_make_cv_splits.py --config %CONFIG%
if errorlevel 1 goto :fail

echo.
echo [OK] v1.1-alpha collector-based QA pipeline completed.
exit /b 0

:fail
echo.
echo [ERROR] v1.1-alpha collector-based QA pipeline failed.
exit /b 1
