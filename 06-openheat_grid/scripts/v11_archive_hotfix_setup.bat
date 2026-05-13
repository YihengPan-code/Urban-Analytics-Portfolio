@echo off
setlocal
set CONFIG=configs\v11\v11_longterm_archive_config.example.json

echo ============================================================
echo OpenHeat v11 archive collector hotfix setup
echo Config: %CONFIG%
echo ============================================================

echo [1/3] Migrating legacy v09/v10 NEA archive into v11 long archive...
python scripts\v11_archive_migrate_legacy.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [2/3] Cleaning old raw JSON folders according to config retention...
python scripts\v11_archive_cleanup_raw_json.py --config %CONFIG%
if errorlevel 1 goto :fail

echo [3/3] Preflight check...
python scripts\v11_archive_preflight.py --config %CONFIG%
if errorlevel 1 goto :fail

echo.
echo [OK] v11 archive hotfix setup complete.
echo Next: scripts\v11_archive_collect_once.bat
exit /b 0

:fail
echo.
echo [ERROR] v11 archive hotfix setup failed.
exit /b 1
