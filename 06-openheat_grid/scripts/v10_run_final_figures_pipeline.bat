@echo off
setlocal
set CONFIG=configs\v10\v10_final_figures_config.example.json

echo ============================================================
echo OpenHeat v10 final figures/maps pipeline
echo Config: %CONFIG%
echo ============================================================

echo.
echo [1/4] Build final hotspot interpretation layer...
python scripts\figures\v10_build_final_interpretation_layer.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [2/4] Generate maps...
python scripts\figures\v10_make_final_maps.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [3/4] Generate charts...
python scripts\figures\v10_make_final_charts.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [4/4] Generate workflow schematic...
python scripts\figures\v10_make_workflow_schematic.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [OK] v10 final figures/maps generated.
echo Output: outputs\v10_final_figures
goto :eof

:error
echo.
echo [ERROR] v10 final figures/maps pipeline failed.
exit /b 1
