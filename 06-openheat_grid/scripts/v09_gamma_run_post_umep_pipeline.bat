@echo off
setlocal
REM After UMEP/SOLWEIG has been run manually, aggregate Tmrt outputs and compare with proxy.
python scripts\v09_gamma_aggregate_solweig_tmrt.py --config configs\v09_gamma_solweig_config.example.json
if errorlevel 1 exit /b 1
python scripts\v09_gamma_compare_tmrt_proxy_vs_solweig.py
if errorlevel 1 exit /b 1
echo [DONE] v0.9-gamma post-UMEP aggregation complete.
pause
