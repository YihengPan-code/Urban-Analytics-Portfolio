@echo off
setlocal

set CONFIG=configs\v10\v10_final_figures_config.v4.json

echo ============================================================
echo OpenHeat v10 final figures / maps pipeline v4
echo Config: %CONFIG%
echo ============================================================

echo [0/4] Optional dependency reminder...
echo If you want satellite basemaps, make sure this environment has:
echo   pip install contextily xyzservices

echo [1/4] Build final interpretation layer...
python scripts\figures_v4\v10_build_final_interpretation_layer_v4.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [2/4] Make workflow diagram...
python scripts\figures_v4\v10_make_workflow_schematic_v4.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [3/4] Make maps with satellite basemap support...
python scripts\figures_v4\v10_make_final_maps_v4.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [4/4] Make charts...
python scripts\figures_v4\v10_make_final_charts_v4.py --config %CONFIG%
if errorlevel 1 goto :fail

echo.
echo [OK] v10 final figure pipeline v4 completed.
echo Output: outputs\v10_final_figures_v4
exit /b 0

:fail
echo.
echo [ERROR] v10 final figure pipeline v4 failed.
exit /b 1
