@echo off
setlocal
set CONFIG=configs\v10\v10_gamma_umep_config.example.json

echo ============================================================
echo OpenHeat v10-gamma POST-UMEP morphology pipeline
echo Config: %CONFIG%
echo ============================================================

echo [1/2] Aggregate UMEP SVF/shadow rasters to grid...
python scripts\v10_gamma_zonal_umep_to_grid.py --config %CONFIG%
if errorlevel 1 goto error

echo [2/2] Merge v10 UMEP morphology into forecast grid...
python scripts\v10_gamma_merge_umep_morphology_to_grid.py --config %CONFIG%
if errorlevel 1 goto error

echo.
echo [OK] v10-gamma morphology grid ready:
echo data\grid\v10\toa_payoh_grid_v10_features_umep_with_veg.csv
goto end

:error
echo [ERROR] v10-gamma post-UMEP morphology pipeline failed.
exit /b 1

:end
endlocal
