@echo off
setlocal
set CONFIG=configs\v10\v10_gamma_umep_config.example.json
set GRID=data\grid\v10\toa_payoh_grid_v10_features_umep_with_veg.csv
set OUTDIR=outputs\v10_gamma_forecast_live

echo ============================================================
echo OpenHeat v10-gamma forecast + comparison pipeline
echo Config: %CONFIG%
echo Grid: %GRID%
echo ============================================================

echo [1/3] Run live forecast/hazard engine using v10 grid...
python scripts\run_live_forecast_v06.py --mode live --grid %GRID% --out-dir %OUTDIR%
if errorlevel 1 goto error

echo [2/3] Finalize forecast outputs with v10 explanatory features...
python scripts\v10_gamma_finalize_forecast_outputs.py --config %CONFIG%
if errorlevel 1 goto error

echo [3/3] Compare v08 vs v10 forecast/ranking...
python scripts\v10_gamma_compare_v08_v10_rankings.py --config %CONFIG%
if errorlevel 1 goto error

echo.
echo [OK] v10-gamma forecast and comparison complete.
goto end

:error
echo [ERROR] v10-gamma forecast/comparison pipeline failed.
exit /b 1

:end
endlocal
