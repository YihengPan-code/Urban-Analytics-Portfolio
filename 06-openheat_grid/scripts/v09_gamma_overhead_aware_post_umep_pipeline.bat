@echo off
setlocal

REM OpenHeat v0.9-gamma overhead-aware post-UMEP workflow
REM Run after placing SOLWEIG Tmrt rasters inside each selected tile folder.

set CONFIG=configs\v09_gamma_overhead_aware_config.example.json

echo ============================================================
echo v0.9-gamma overhead-aware post-UMEP pipeline
echo ============================================================

echo [1/1] Aggregate SOLWEIG Tmrt rasters to grid...
python scripts\v09_gamma_aggregate_solweig_tmrt_overhead_aware.py --config %CONFIG%
if errorlevel 1 goto :error

echo ============================================================
echo DONE. Inspect:
echo outputs\v09_solweig\v09_solweig_tmrt_grid_summary_overhead_aware.csv
echo outputs\v09_solweig\v09_solweig_tmrt_grid_summary_overhead_aware_report.md
echo ============================================================
goto :eof

:error
echo [ERROR] Pipeline failed. Check the messages above.
exit /b 1
