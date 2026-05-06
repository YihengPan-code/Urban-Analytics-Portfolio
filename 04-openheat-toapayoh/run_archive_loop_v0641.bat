@echo off
setlocal enabledelayedexpansion

REM ==========================================================
REM OpenHeat-ToaPayoh v0.6.4.1
REM NEA real-time archive collector
REM Long-format archive only
REM ==========================================================

REM === 1. Change this path if your project folder is different ===
set PROJECT_DIR=C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\04-openheat-toapayoh

REM === 2. Conda environment name ===
set CONDA_ENV=openheat

REM === 3. Collection interval ===
REM 900 seconds = 15 minutes
set INTERVAL_SECONDS=900

REM === 4. Number of rounds ===
REM 96 rounds x 15 minutes = 24 hours
set MAX_ROUNDS=96

REM === 5. Archive file ===
set ARCHIVE_FILE=data\archive\nea_realtime_observations.csv

cd /d "%PROJECT_DIR%"

if errorlevel 1 (
    echo [ERROR] Cannot enter project directory:
    echo %PROJECT_DIR%
    pause
    exit /b 1
)

if not exist logs mkdir logs
if not exist data mkdir data
if not exist data\archive mkdir data\archive

echo.
echo ==========================================================
echo OpenHeat NEA Archive Collector v0.6.4.1
echo ==========================================================
echo Project folder: %PROJECT_DIR%
echo Conda env:      %CONDA_ENV%
echo Interval:       %INTERVAL_SECONDS% seconds
echo Max rounds:     %MAX_ROUNDS%
echo Archive file:   %ARCHIVE_FILE%
echo.
echo Press Ctrl+C to stop manually.
echo ==========================================================
echo.

call conda activate %CONDA_ENV%

if errorlevel 1 (
    echo [ERROR] Failed to activate conda environment: %CONDA_ENV%
    echo Please open Anaconda Prompt and check:
    echo conda activate %CONDA_ENV%
    pause
    exit /b 1
)

REM ==========================================================
REM Preflight check: make sure this is v0.6.4.1-style archive
REM If an old wide-format archive exists, stop and ask user to backup.
REM ==========================================================

python -c "import pandas as pd, pathlib, sys; p=pathlib.Path(r'%ARCHIVE_FILE%'); print('[CHECK] archive path:', p); sys.exit(0) if not p.exists() else None; cols=pd.read_csv(p,nrows=0).columns.tolist(); print('[CHECK] existing columns:', cols[:12]); sys.exit(2) if 'variable' not in cols else print('[OK] existing archive is long format')"

if errorlevel 2 (
    echo.
    echo [STOP] Existing archive is NOT long format.
    echo It is probably an old wide-format archive.
    echo.
    echo Please run these commands once:
    echo copy %ARCHIVE_FILE% data\archive\nea_realtime_observations_old_wide_backup.csv
    echo del %ARCHIVE_FILE%
    echo.
    echo Then run this script again.
    echo.
    pause
    exit /b 2
)

REM ==========================================================
REM Main collection loop
REM ==========================================================

for /l %%i in (1,1,%MAX_ROUNDS%) do (
    echo.
    echo ----------------------------------------------------------
    echo Round %%i / %MAX_ROUNDS%
    echo Local time: %date% %time%
    echo ----------------------------------------------------------

    python scripts\archive_nea_observations.py --mode live --api-version v2 --archive %ARCHIVE_FILE% >> logs\archive_loop.log 2>&1

    if errorlevel 1 (
        echo [WARNING] Archive failed at round %%i. Check logs\archive_loop.log
        echo [WARNING] Round %%i failed at %date% %time% >> logs\archive_loop_errors.log
    ) else (
        echo [OK] Archive completed at round %%i
        echo [OK] Round %%i completed at %date% %time% >> logs\archive_loop_status.log
    )

    REM Quick archive summary after each round
    python -c "import pandas as pd, pathlib; p=pathlib.Path(r'%ARCHIVE_FILE%'); df=pd.read_csv(p) if p.exists() else pd.DataFrame(); print('[SUMMARY] rows:', len(df)); print(df.groupby(['api_name','variable']).size().to_string() if len(df) and {'api_name','variable'}.issubset(df.columns) else '[SUMMARY] archive not ready')"

    echo.
    echo Waiting %INTERVAL_SECONDS% seconds before next round...
    timeout /t %INTERVAL_SECONDS% /nobreak > nul
)

echo.
echo ==========================================================
echo Archive loop finished.
echo Archive file:
echo %ARCHIVE_FILE%
echo Logs:
echo logs\archive_loop.log
echo logs\archive_loop_status.log
echo logs\archive_loop_errors.log
echo ==========================================================
pause