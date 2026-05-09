@echo off
setlocal
REM Select SOLWEIG tiles and clip DSM rasters. Then run UMEP manually in QGIS.
python scripts\v09_gamma_select_solweig_tiles.py --config configs\v09_gamma_solweig_config.example.json
if errorlevel 1 exit /b 1
python scripts\v09_gamma_clip_tile_rasters.py --config configs\v09_gamma_solweig_config.example.json
if errorlevel 1 exit /b 1
echo.
echo [NEXT] Open QGIS/UMEP. For each tile folder under data\solweig\v09_tiles\,
echo        run SOLWEIG and save Tmrt rasters under a solweig_outputs subfolder.
pause
