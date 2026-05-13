@echo off
setlocal
set CONFIG=configs\v11\v11_alpha_archive_config.example.json

echo ============================================================
echo OpenHeat v1.1-alpha archive QA + pairing pipeline
echo Config: %CONFIG%
echo ============================================================

echo [1/4] Inventory archive files...
python scripts\v11_alpha_archive_inventory.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [2/4] Build station-weather paired dataset...
python scripts\v11_alpha_build_pairs.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [3/4] Run archive/event/missingness QA...
python scripts\v11_alpha_archive_qa.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [4/4] Create CV split plan...
python scripts\v11_alpha_make_cv_splits.py --config %CONFIG%
if errorlevel 1 goto :fail

echo.
echo [OK] v1.1-alpha archive QA pipeline completed.
echo Review: outputs\v11_alpha_archive\v11_archive_QA_report.md
exit /b 0

:fail
echo.
echo [ERROR] v1.1-alpha archive QA pipeline failed.
exit /b 1
