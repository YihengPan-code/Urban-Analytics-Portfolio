@echo off
setlocal
set CONFIG=configs\v10\v10_beta_morphology_config.example.json

echo ============================================================
echo OpenHeat v1.0-beta basic morphology + DSM-gap audit pipeline
echo Config: %CONFIG%
echo ============================================================
echo.

echo [1/2] Compute old-vs-reviewed DSM building morphology stats...
python scripts\v10_beta_compute_basic_morphology.py --config %CONFIG%
if errorlevel 1 goto fail

echo.
echo [2/2] Audit old hazard cells for DSM-gap false-positive candidates...
REM Prefer the implementation script name, but keep compatibility with the wrapper.
if exist scripts\v10_beta_build_morphology_shift_audit.py (
    python scripts\v10_beta_build_morphology_shift_audit.py --config %CONFIG%
) else (
    python scripts\v10_beta_morphology_shift_audit.py --config %CONFIG%
)
if errorlevel 1 goto fail

echo.
echo [OK] v1.0-beta basic morphology pipeline completed.
goto end

:fail
echo.
echo [ERROR] v1.0-beta basic morphology pipeline failed.
exit /b 1

:end
endlocal
