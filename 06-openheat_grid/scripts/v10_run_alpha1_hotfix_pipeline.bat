@echo off
setlocal enabledelayedexpansion

REM OpenHeat v1.0-alpha.1 hotfix pipeline
REM Run from project root: 06-openheat_grid

set CONFIG=configs\v10\v10_alpha_augmented_dsm_config.example.json

echo ============================================================
echo OpenHeat v1.0-alpha.1 hotfix pipeline
echo Config: %CONFIG%
echo ============================================================

echo.
echo [1/4] Deduplicate footprints with OSM height/levels promotion...
python scripts\v10_deduplicate_building_footprints.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [2/4] Assign building heights with provenance...
python scripts\v10_assign_building_heights.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [3/4] Rasterize augmented DSM with nodata=None...
python scripts\v10_rasterize_augmented_dsm.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [4/4] Re-run completeness audit...
python scripts\v10_building_completeness_audit.py --config %CONFIG%
if errorlevel 1 goto :error

echo.
echo [OK] v1.0-alpha.1 hotfix pipeline completed.
echo Key reports:
echo   outputs\v10_dsm_audit\v10_dedup_QA_report.md
echo   outputs\v10_dsm_audit\v10_height_imputation_QA.md
echo   outputs\v10_dsm_audit\v10_rasterize_augmented_dsm_QA.md
echo   outputs\v10_dsm_audit\v10_completeness_gain_report.md
exit /b 0

:error
echo.
echo [ERROR] v1.0-alpha.1 hotfix pipeline failed.
exit /b 1
