@echo off
setlocal

REM OpenHeat v0.8-beta UMEP + vegetation forecast workflow
REM Run from project root: 06-openheat_grid

set BASE_GRID=data\grid\toa_payoh_grid_v07_features_beta_final_v071_risk.csv
set UMEP=data\grid\toa_payoh_grid_v08_umep_morphology_with_veg.csv
set OUT_GRID=data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv
set OUT_DIR=outputs\v08_umep_with_veg_forecast_live
set OLD_RANKING=outputs\v07_beta_final_forecast_live\v06_live_hotspot_ranking.csv

python scripts\v08_apply_umep_morphology_with_veg.py --base-grid %BASE_GRID% --umep %UMEP% --out-grid %OUT_GRID%
if errorlevel 1 exit /b 1

python scripts\run_live_forecast_v06.py --mode live --grid %OUT_GRID% --out-dir %OUT_DIR%
if errorlevel 1 exit /b 1

python scripts\v08_finalize_umep_with_veg_forecast_outputs.py --forecast-dir %OUT_DIR% --grid-csv %OUT_GRID% --grid-geojson data\grid\toa_payoh_grid_v07_features.geojson
if errorlevel 1 exit /b 1

python scripts\v08_compare_proxy_vs_umep_with_veg_forecast.py --old-ranking %OLD_RANKING% --new-ranking %OUT_DIR%\v06_live_hotspot_ranking.csv --metric hazard_score
if errorlevel 1 exit /b 1

echo.
echo [OK] v0.8-beta UMEP+vegetation workflow completed.
echo Outputs: %OUT_DIR%
echo Comparison: outputs\v08_umep_with_veg_comparison
pause
