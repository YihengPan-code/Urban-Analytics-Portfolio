@echo off
REM ============================================================
REM v11_archive_loop.bat
REM   Long-running archive collector loop.
REM   Runs scripts\v11_archive_collect_once.py at a fixed interval.
REM
REM Usage:
REM   conda activate openheat
REM   cd <project root>
REM   scripts\v11_archive_loop.bat
REM
REM Stop:    Ctrl+C in this window, or close the window.
REM Restart: Re-run scripts\v11_archive_loop.bat.
REM
REM For unattended collection across sleep / logoff, prefer
REM Windows Task Scheduler. See:
REM   scripts\v11_archive_make_task_scheduler_commands.bat
REM ============================================================

setlocal enabledelayedexpansion

set "CONFIG=configs\v11\v11_longterm_archive_config.example.json"
set "INTERVAL_SECONDS=900"
set "RUN_COUNT=0"
set "LOG_FILE=outputs\v11_archive_longterm\loop_runs.log"

if not exist outputs\v11_archive_longterm mkdir outputs\v11_archive_longterm 2>nul

echo ============================================================
echo OpenHeat v1.1 archive long-running loop
echo Config:   %CONFIG%
echo Cadence:  %INTERVAL_SECONDS% seconds (15 min)
echo Log file: %LOG_FILE%
echo Stop:     Ctrl+C  (or close this window)
echo Started:  %date% %time%
echo ============================================================

:loop
set /a RUN_COUNT=!RUN_COUNT! + 1
echo.
echo --- Run #!RUN_COUNT! at %date% %time% ---
python scripts\v11_archive_collect_once.py --config %CONFIG%
set "EXIT_CODE=!ERRORLEVEL!"
if !EXIT_CODE! EQU 0 (
  echo [%date% %time%] [OK]   Run #!RUN_COUNT! completed.
) else (
  echo [%date% %time%] [WARN] Run #!RUN_COUNT! failed with exit code !EXIT_CODE!. Continuing.
)
echo [%date% %time%] Run #!RUN_COUNT! exit_code=!EXIT_CODE! >> "%LOG_FILE%"
echo Sleeping %INTERVAL_SECONDS% seconds. Press Ctrl+C to stop.
timeout /t %INTERVAL_SECONDS% /nobreak >nul
goto :loop
