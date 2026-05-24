@echo off
setlocal
set CONFIG=configs\v11\v11_longterm_archive_config.example.json

echo ============================================================
echo OpenHeat v1.1 long-term archive: collect one snapshot
echo Config: %CONFIG%
echo ============================================================

python scripts\v11_archive_collect_once.py --config %CONFIG%
if errorlevel 1 goto :fail

echo.
echo [OK] One archive snapshot completed.
echo Latest report: outputs\v11_archive_longterm\v11_archive_latest_QA_report.md
exit /b 0

:fail
echo.
echo [ERROR] Archive snapshot failed.
exit /b 1
