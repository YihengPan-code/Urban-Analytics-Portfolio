@echo off
setlocal
set CONFIG=configs\v10\v10_delta_overhead_config.example.json
set GRID=data\grid\v10\toa_payoh_grid_v10_features_overhead_sensitivity.csv
set OUTDIR=outputs\v10_delta_overhead_forecast_live

echo ============================================================
echo OpenHeat v10-delta overhead-shade forecast + comparison
echo Grid: %GRID%
echo Output: %OUTDIR%
echo ============================================================

echo.
echo [1/2] Run live forecast using overhead-sensitivity grid...
python scripts\run_live_forecast_v06.py --mode live --grid %GRID% --out-dir %OUTDIR%
if errorlevel 1 goto :error

echo.
echo [2/2] Compare base v10 vs overhead-shade sensitivity ranking...
python scripts\v10_delta_compare_base_vs_overhead.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [OK] v10-delta overhead forecast comparison completed.
exit /b 0

:error
echo.
echo [ERROR] v10-delta overhead forecast comparison failed.
exit /b 1
