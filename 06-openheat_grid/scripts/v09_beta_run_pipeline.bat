@echo off
setlocal

echo ==========================================================
echo OpenHeat v0.9-beta WBGT calibration pipeline
echo ==========================================================

python scripts\v09_beta_fit_calibration_models.py --config configs\v09_beta_config.example.json

if errorlevel 1 (
  echo [ERROR] v0.9-beta calibration failed.
  exit /b 1
)

echo [OK] v0.9-beta calibration complete.
echo Report: outputs\v09_beta_calibration\v09_beta_calibration_report.md
