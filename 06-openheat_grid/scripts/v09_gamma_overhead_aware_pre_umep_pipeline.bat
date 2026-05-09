@echo off
setlocal

REM OpenHeat v0.9-gamma overhead-aware tile pre-UMEP workflow
REM Run from project root: 06-openheat_grid

set CONFIG=configs\v09_gamma_overhead_aware_config.example.json

echo ============================================================
echo v0.9-gamma overhead-aware pre-UMEP pipeline
echo ============================================================

echo [1/3] Build per-cell overhead QA...
python scripts\v09_gamma_build_overhead_cell_qa.py --config %CONFIG%
if errorlevel 1 goto :error

echo [2/3] Select overhead-aware SOLWEIG tiles...
python scripts\v09_gamma_select_tiles_overhead_aware.py --config %CONFIG%
if errorlevel 1 goto :error

echo [3/3] Clip DSM rasters for selected tiles...
python scripts\v09_gamma_clip_tiles_overhead_aware.py --config %CONFIG%
if errorlevel 1 goto :error

echo ============================================================
echo DONE. Inspect:
echo data\solweig\v09_tiles_overhead_aware\v09_solweig_tile_selection_overhead_aware_QA_report.md
echo Then run SOLWEIG in QGIS/UMEP for each selected tile.
echo ============================================================
goto :eof

:error
echo [ERROR] Pipeline failed. Check the messages above.
exit /b 1
