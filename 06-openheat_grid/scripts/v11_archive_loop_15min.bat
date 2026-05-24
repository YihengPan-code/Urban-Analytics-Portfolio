@echo off
setlocal
set CONFIG=configs\v11\v11_longterm_archive_config.example.json
set INTERVAL_SECONDS=900

echo ============================================================
echo OpenHeat v1.1 long-term archive loop
echo Config: %CONFIG%
echo Interval: %INTERVAL_SECONDS% seconds

echo NOTE: For production, Windows Task Scheduler is cleaner.
echo This loop is useful for manual overnight collection.
echo ============================================================

:loop
echo.
echo [%date% %time%] Collecting archive snapshot...
python scripts\v11_archive_collect_once.py --config %CONFIG%
if errorlevel 1 (
  echo [%date% %time%] [WARN] Snapshot failed. Continuing after interval.
) else (
  echo [%date% %time%] [OK] Snapshot completed.
)
echo Waiting %INTERVAL_SECONDS% seconds...
timeout /t %INTERVAL_SECONDS% /nobreak >nul
goto :loop
