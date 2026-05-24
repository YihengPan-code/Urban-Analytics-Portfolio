@echo off
setlocal
set CONFIG=configs\v10\v10_gamma_robustness_config.example.json

echo ============================================================
echo OpenHeat v10-gamma robustness audit
echo Config: %CONFIG%
echo ============================================================

python scripts\v10_gamma_robustness_audit.py --config %CONFIG%
if errorlevel 1 (
    echo.
    echo [ERROR] v10-gamma robustness audit failed.
    exit /b 1
)

echo.
echo [OK] v10-gamma robustness audit completed.
echo Review: outputs\v10_gamma_robustness\v10_gamma_robustness_audit_report.md
endlocal
