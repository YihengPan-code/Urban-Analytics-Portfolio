@echo off
setlocal
set CONFIG=configs\v10\v10_alpha3_manual_qa_config.example.json

echo ============================================================
echo OpenHeat v1.0-alpha.3 manual QA reviewed DSM pipeline
echo Config: %CONFIG%
echo ============================================================

echo.
echo [1/3] Apply manual QA decisions...
python scripts\v10_alpha3_apply_manual_qa_decisions.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [2/3] Rasterize reviewed augmented DSM...
python scripts\v10_rasterize_reviewed_dsm.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [3/3] Reviewed completeness audit...
python scripts\v10_alpha3_reviewed_completeness_audit.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [OK] v1.0-alpha.3 manual QA pipeline completed.
goto end

:fail
echo.
echo [ERROR] v1.0-alpha.3 manual QA pipeline failed.
exit /b 1

:end
endlocal
