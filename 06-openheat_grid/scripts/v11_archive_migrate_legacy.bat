@echo off
setlocal
set CONFIG=configs\v11\v11_longterm_archive_config.example.json

echo ============================================================
echo OpenHeat v1.1 / v11 legacy archive migration
echo Config: %CONFIG%
echo ============================================================

python scripts\v11_archive_migrate_legacy.py --config %CONFIG%
if errorlevel 1 goto :fail

echo.
echo [OK] legacy archive migration completed.
exit /b 0

:fail
echo.
echo [ERROR] legacy archive migration failed.
exit /b 1
