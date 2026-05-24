@echo off
setlocal enabledelayedexpansion

set CONFIG=configs\v10\v10_beta1_height_geometry_config.example.json

echo ============================================================
echo OpenHeat v10-beta.1 height / geometry correction pipeline
echo Config: %CONFIG%
echo ============================================================

echo.
echo [1/2] Apply manual height / split-complex corrections...
python scripts\v10_beta1_apply_height_geometry_corrections.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [2/2] Rasterize height-QA reviewed DSM...
python scripts\v10_beta1_rasterize_heightqa_dsm.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [OK] v10-beta.1 height / geometry correction completed.
echo Next: use data\rasters\v10\dsm_buildings_2m_augmented_reviewed_heightqa.tif for v10-gamma UMEP.
goto end

:fail
echo.
echo [ERROR] v10-beta.1 pipeline failed.
exit /b 1

:end
endlocal
