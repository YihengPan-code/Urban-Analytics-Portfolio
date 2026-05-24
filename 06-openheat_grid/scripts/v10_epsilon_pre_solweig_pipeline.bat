@echo off
setlocal
set CONFIG=configs\v10\v10_epsilon_solweig_config.example.json

echo ============================================================
echo OpenHeat v10-epsilon selected-cell SOLWEIG pre-QGIS pipeline
echo Config: %CONFIG%
echo ============================================================

echo.
echo [1/2] Select cells and create tile folders...
python scripts\v10_epsilon_select_cells.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [2/2] Prepare building / vegetation / overhead rasters...
python scripts\v10_epsilon_prepare_rasters.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [OK] v10-epsilon pre-SOLWEIG setup completed.
echo Next: run QGIS/UMEP SOLWEIG manually for each tile/scenario.
goto end

:fail
echo.
echo [ERROR] v10-epsilon pre-SOLWEIG pipeline failed.
exit /b 1

:end
endlocal
