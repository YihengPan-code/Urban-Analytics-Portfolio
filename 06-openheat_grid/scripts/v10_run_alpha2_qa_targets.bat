@echo off
setlocal
set CONFIG=configs\v10\v10_alpha2_qa_config.example.json

echo ============================================================
echo OpenHeat v1.0-alpha.2 QA target generation
echo Config: %CONFIG%
echo ============================================================

python scripts\v10_alpha2_generate_qa_targets.py --config %CONFIG%
if errorlevel 1 (
  echo.
  echo [ERROR] v10-alpha.2 QA target generation failed.
  exit /b 1
)

echo.
echo [OK] v10-alpha.2 QA target generation complete.
echo Outputs: outputs\v10_dsm_audit\alpha2_qa_targets
endlocal
