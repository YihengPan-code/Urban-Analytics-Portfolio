@echo off
setlocal enabledelayedexpansion
set CONFIG=configs\v10\v10_final_figures_config.v2.json

echo ============================================================
echo OpenHeat v10 final figure/map pipeline v2
echo Config: %CONFIG%
echo ============================================================

echo.
echo [1/4] Build final interpretation layer...
python scripts\figures_v2\v10_build_final_interpretation_layer_v2.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [2/4] Make final maps...
python scripts\figures_v2\v10_make_final_maps_v2.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [3/4] Make final charts...
python scripts\figures_v2\v10_make_final_charts_v2.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [4/4] Make workflow schematic...
python scripts\figures_v2\v10_make_workflow_schematic_v2.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [OK] v10 final figure/map pipeline v2 completed.
echo Outputs: outputs\v10_final_figures_v2
exit /b 0

:error
echo.
echo [ERROR] v10 final figure/map pipeline v2 failed.
exit /b 1
