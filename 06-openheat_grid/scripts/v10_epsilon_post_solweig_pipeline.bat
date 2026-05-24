@echo off
setlocal
set CONFIG=configs\v10\v10_epsilon_solweig_config.example.json

echo ============================================================
echo OpenHeat v10-epsilon selected-cell SOLWEIG post-QGIS pipeline
echo Config: %CONFIG%
echo ============================================================

echo.
echo [1/2] Aggregate SOLWEIG Tmrt rasters...
python scripts\v10_epsilon_aggregate_tmrt.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [2/2] Compare base vs overhead Tmrt...
python scripts\v10_epsilon_compare_tmrt.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [OK] v10-epsilon post-SOLWEIG comparison completed.
goto end

:fail
echo.
echo [ERROR] v10-epsilon post-SOLWEIG pipeline failed.
exit /b 1

:end
endlocal
