@echo off
setlocal
set CONFIG=configs\v11\v11_beta_calibration_config.example.json

echo ============================================================
echo OpenHeat v1.1-beta calibration baseline + threshold pipeline
echo Config: %CONFIG%
echo ============================================================

echo [1/2] Run calibration baselines M0-M6...
python scripts\v11_beta_calibration_baselines.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [2/2] Run threshold scan...
python scripts\v11_beta_threshold_scan.py --config %CONFIG%
if errorlevel 1 goto :fail

echo.
echo [OK] v1.1-beta calibration pipeline completed.
echo Review: outputs\v11_beta_calibration\v11_beta_calibration_baseline_report.md
echo Review: outputs\v11_beta_calibration\v11_beta_threshold_scan_report.md
exit /b 0

:fail
echo.
echo [ERROR] v1.1-beta calibration pipeline failed.
exit /b 1
