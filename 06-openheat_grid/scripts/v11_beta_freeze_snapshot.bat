@echo off
REM ============================================================================
REM v11_beta_freeze_snapshot.bat — OpenHeat v1.1-β.1 fourth audit (3.2)
REM
REM PURPOSE: Lock the v11 archive at a specific moment, then re-run all
REM   formal-pass experiments on the snapshot. Eliminates the v2.1 issue where
REM   archive growth between runs created the "5,724 = 5,724 row coincidence"
REM   in the all_stations vs no_S142 comparison (v2.1 §6.9).
REM
REM USAGE: From repo root
REM     scripts\v11_beta_freeze_snapshot.bat [LABEL]
REM
REM   LABEL is optional; defaults to "14d_formal" + today's date.
REM   Example:  scripts\v11_beta_freeze_snapshot.bat 14d_formal
REM             ->  data\calibration\v11\snapshots\v11_pairs_14d_formal_20260524.csv
REM             ->  data\calibration\v11\snapshots\v11_pairs_14d_formal_20260524_v091.csv
REM
REM AFTER RUNNING: edit configs/v11/v11_beta_calibration_config_v091*.json so
REM   "paths.paired_dataset_csv" points at the snapshot CSV (not the live one).
REM   All baseline / ablation / hourly / threshold-scan runs from that point on
REM   will derive from the same frozen rows -> controlled comparisons.
REM
REM This script does NOT touch the archive collector loop.
REM ============================================================================
setlocal EnableDelayedExpansion

REM --- arg parsing -----------------------------------------------------------
set "LABEL=%~1"
if "%LABEL%"=="" set "LABEL=14d_formal"

REM Today's date as YYYYMMDD (Windows-locale-safe via wmic)
for /f "skip=1" %%D in ('wmic os get LocalDateTime /value ^| find "="') do (
    set "_LDT=%%D"
)
REM _LDT looks like LocalDateTime=20260524103022.123456+480
for /f "tokens=2 delims==" %%X in ("%_LDT%") do set "_LDT=%%X"
set "TODAY=%_LDT:~0,8%"
set "STAMP=%LABEL%_%TODAY%"

REM --- paths -----------------------------------------------------------------
set "RAW_INPUT=data\calibration\v11\v11_station_weather_pairs.csv"
set "SNAPSHOT_DIR=data\calibration\v11\snapshots"
set "SNAPSHOT_RAW=%SNAPSHOT_DIR%\v11_pairs_%STAMP%.csv"
set "SNAPSHOT_V091=%SNAPSHOT_DIR%\v11_pairs_%STAMP%_v091.csv"

REM --- preflight checks ------------------------------------------------------
if not exist "%RAW_INPUT%" (
    echo [ERROR] raw archive not found: %RAW_INPUT%
    echo         Are you running from repo root?
    exit /b 2
)

if not exist "%SNAPSHOT_DIR%" (
    echo [INFO] creating snapshot dir: %SNAPSHOT_DIR%
    mkdir "%SNAPSHOT_DIR%"
)

if exist "%SNAPSHOT_RAW%" (
    echo [WARN] snapshot already exists: %SNAPSHOT_RAW%
    echo        Delete it manually if you want a fresh snapshot.
    echo        Aborting to avoid overwriting frozen reference data.
    exit /b 3
)

REM --- snapshot the raw pairs ------------------------------------------------
echo.
echo ============================================================================
echo [step 1/3] Freezing raw archive snapshot
echo ============================================================================
echo   source:  %RAW_INPUT%
echo   target:  %SNAPSHOT_RAW%
copy /Y "%RAW_INPUT%" "%SNAPSHOT_RAW%" > nul
if errorlevel 1 (
    echo [ERROR] copy failed
    exit /b 4
)

REM Show row count for confirmation
for /f %%C in ('find /c /v "" ^< "%SNAPSHOT_RAW%"') do set "RAW_ROWS=%%C"
echo   rows:    %RAW_ROWS%  (including header)

REM --- run build_features on snapshot ----------------------------------------
echo.
echo ============================================================================
echo [step 2/3] Building v0.9 proxy + lag features + retrospective flags
echo ============================================================================
python scripts\v11_beta_build_features.py ^
    --input "%SNAPSHOT_RAW%" ^
    --output "%SNAPSHOT_V091%"
if errorlevel 1 (
    echo [ERROR] build_features failed on snapshot
    exit /b 5
)

REM --- print next-step instructions ------------------------------------------
echo.
echo ============================================================================
echo [step 3/3] Snapshot ready. Manual config edits required.
echo ============================================================================
echo.
echo Edit the following config files so paths.paired_dataset_csv points at:
echo   %SNAPSHOT_V091%
echo.
echo Files to edit:
echo   configs\v11\v11_beta_calibration_config_v091.json
echo   configs\v11\v11_beta_calibration_config_v091_no_S142.json
echo   configs\v11\v11_beta_calibration_config_v091_hourly_mean.json
echo   configs\v11\v11_beta_calibration_config_v091_hourly_max.json
echo.
echo Then re-run aggregator + baselines + ablations + hourly + threshold scan.
echo All runs will derive from the same frozen %RAW_ROWS%-row snapshot.
echo.
echo Snapshot label: %STAMP%
echo Recorded at:    %_LDT:~0,4%-%_LDT:~4,2%-%_LDT:~6,2% %_LDT:~8,2%:%_LDT:~10,2%:%_LDT:~12,2%
echo.

endlocal
exit /b 0
