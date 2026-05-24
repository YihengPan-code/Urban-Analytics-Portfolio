@echo off
setlocal
set CONFIG=configs\v10\v10_delta_overhead_config.example.json

echo ============================================================
echo OpenHeat v10-delta overhead layer + sensitivity grid pipeline
echo Config: %CONFIG%
echo ============================================================

echo.
echo [1/3] Build canonical overhead infrastructure layer...
python scripts\v10_delta_build_overhead_layer.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [2/3] Aggregate overhead metrics to grid cells...
python scripts\v10_delta_cell_overhead_metrics.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [3/3] Create overhead-shade sensitivity grid...
python scripts\v10_delta_apply_overhead_sensitivity.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [OK] v10-delta overhead sensitivity grid prepared.
echo Next: run forecast with data\grid\v10\toa_payoh_grid_v10_features_overhead_sensitivity.csv
echo.
exit /b 0

:error
echo.
echo [ERROR] v10-delta overhead pipeline failed.
exit /b 1
