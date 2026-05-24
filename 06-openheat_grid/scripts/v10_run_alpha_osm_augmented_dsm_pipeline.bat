@echo off
setlocal

REM OpenHeat v1.0-alpha OSM-first augmented DSM pipeline
REM Run from project root: 06-openheat_grid

set CONFIG=configs\v10\v10_alpha_augmented_dsm_config.example.json

echo ==========================================================
echo Step 1/6: Extract OSM buildings via Overpass
echo ==========================================================
python scripts\v10_extract_osm_buildings.py --config %CONFIG%
if errorlevel 1 goto :fail

echo ==========================================================
echo Step 2/6: Standardize HDB3D / URA / OSM sources
echo ==========================================================
python scripts\v10_standardize_building_sources.py --config %CONFIG%
if errorlevel 1 goto :fail

echo ==========================================================
echo Step 3/6: Deduplicate building footprints
echo ==========================================================
python scripts\v10_deduplicate_building_footprints.py --config %CONFIG%
if errorlevel 1 goto :fail

echo ==========================================================
echo Step 4/6: Assign building heights
echo ==========================================================
python scripts\v10_assign_building_heights.py --config %CONFIG%
if errorlevel 1 goto :fail

echo ==========================================================
echo Step 5/6: Rasterize augmented DSM
echo ==========================================================
python scripts\v10_rasterize_augmented_dsm.py --config %CONFIG%
if errorlevel 1 goto :fail

echo ==========================================================
echo Step 6/6: Completeness audit
echo ==========================================================
python scripts\v10_building_completeness_audit.py --config %CONFIG%
if errorlevel 1 goto :fail

echo ==========================================================
echo [OK] v1.0-alpha OSM-first augmented DSM pipeline complete.
echo ==========================================================
goto :end

:fail
echo [ERROR] Pipeline failed. Check the last script output.
exit /b 1

:end
endlocal
