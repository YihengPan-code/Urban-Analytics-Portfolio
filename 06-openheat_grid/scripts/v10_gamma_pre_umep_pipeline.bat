@echo off
setlocal
set CONFIG=configs\v10\v10_gamma_umep_config.example.json

echo ============================================================
echo OpenHeat v10-gamma PRE-UMEP pipeline
echo Config: %CONFIG%
echo ============================================================

python scripts\v10_gamma_prepare_umep_inputs.py --config %CONFIG%
if errorlevel 1 goto error

echo.
echo [OK] Pre-UMEP checks complete.
echo Next: run QGIS/UMEP SVF + shadow manually using the paths in:
echo data\rasters\v10\V10_GAMMA_UMEP_MANUAL_STEPS.txt
goto end

:error
echo [ERROR] v10-gamma pre-UMEP pipeline failed.
exit /b 1

:end
endlocal
