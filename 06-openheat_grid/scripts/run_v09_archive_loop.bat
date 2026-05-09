@echo off
setlocal enabledelayedexpansion

REM ==========================================================
REM OpenHeat v0.9 long-format NEA archive collector
REM Keeps the archive in long format. Stops if old wide format is detected.
REM ==========================================================

set PROJECT_DIR=C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid
set CONDA_ENV=openheat
set INTERVAL_SECONDS=900
set MAX_ROUNDS=96
set ARCHIVE_FILE=data\archive\nea_realtime_observations.csv
set GRID_FILE=data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv
set FORECAST_SNAPSHOT_EVERY_N_ROUNDS=4
set ENABLE_FORECAST_SNAPSHOT=1

cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo [ERROR] Cannot enter project directory: %PROJECT_DIR%
    pause
    exit /b 1
)

if not exist logs mkdir logs
if not exist data mkdir data
if not exist data\archive mkdir data\archive
if not exist data\archive\openmeteo_forecast_snapshots mkdir data\archive\openmeteo_forecast_snapshots

call conda activate %CONDA_ENV%
if errorlevel 1 (
    echo [ERROR] Failed to activate conda environment: %CONDA_ENV%
    pause
    exit /b 1
)

REM Preflight archive format check
python -c "import pandas as pd, pathlib, sys; p=pathlib.Path(r'%ARCHIVE_FILE%'); print('[CHECK] archive:', p); sys.exit(0) if not p.exists() else None; cols=pd.read_csv(p,nrows=0).columns.tolist(); print('[CHECK] columns:', cols[:12]); sys.exit(2) if 'variable' not in cols or 'value' not in cols else print('[OK] existing archive is long format')"
if errorlevel 2 (
    echo [STOP] Existing archive is not long format. Back it up and delete it before continuing.
    echo Example:
    echo copy %ARCHIVE_FILE% data\archive\nea_realtime_observations_old_wide_backup.csv
    echo del %ARCHIVE_FILE%
    pause
    exit /b 2
)

echo ==========================================================
echo OpenHeat v0.9 archive collector started
echo Project: %PROJECT_DIR%
echo Archive: %ARCHIVE_FILE%
echo Interval: %INTERVAL_SECONDS% seconds
echo Rounds: %MAX_ROUNDS%
echo Forecast snapshots enabled: %ENABLE_FORECAST_SNAPSHOT%
echo ==========================================================

for /l %%i in (1,1,%MAX_ROUNDS%) do (
    echo.
    echo ----------------------------------------------------------
    echo Round %%i / %MAX_ROUNDS% at %date% %time%
    echo ----------------------------------------------------------

    python scripts\archive_nea_observations.py --mode live --api-version v2 --archive %ARCHIVE_FILE% >> logs\v09_archive_loop.log 2>&1
    if errorlevel 1 (
        echo [WARNING] NEA archive failed at round %%i. See logs\v09_archive_loop.log
        echo [WARNING] NEA archive failed at round %%i at %date% %time% >> logs\v09_archive_loop_errors.log
    ) else (
        echo [OK] NEA archive completed at round %%i
    )

    REM Optional: store a live Open-Meteo forecast snapshot every N rounds.
    if "%ENABLE_FORECAST_SNAPSHOT%"=="1" (
        set /a MOD=%%i %% %FORECAST_SNAPSHOT_EVERY_N_ROUNDS%
        if !MOD!==0 (
            for /f "tokens=1-4 delims=/.: " %%a in ("%date% %time%") do set STAMP=round_%%i
            set SNAPDIR=data\archive\openmeteo_forecast_snapshots\round_%%i
            if exist "%GRID_FILE%" (
                python scripts\run_live_forecast_v06.py --mode live --grid "%GRID_FILE%" --out-dir "!SNAPDIR!" >> logs\v09_forecast_snapshot_loop.log 2>&1
                if errorlevel 1 (
                    echo [WARNING] Forecast snapshot failed at round %%i.
                ) else (
                    echo [OK] Forecast snapshot saved: !SNAPDIR!
                )
            ) else (
                echo [INFO] Forecast snapshot skipped; grid file not found: %GRID_FILE%
            )
        )
    )

    python -c "import pandas as pd, pathlib; p=pathlib.Path(r'%ARCHIVE_FILE%'); df=pd.read_csv(p) if p.exists() else pd.DataFrame(); print('[SUMMARY] rows:', len(df)); print(df.groupby(['api_name','variable']).size().to_string() if len(df) and {'api_name','variable'}.issubset(df.columns) else '[SUMMARY] archive not ready')"

    timeout /t %INTERVAL_SECONDS% /nobreak > nul
)

echo [DONE] v0.9 archive loop finished.
pause
