@echo off
setlocal
set TASK_NAME=OpenHeat_v11_archive_15min
set PROJECT_DIR=%CD%
set BAT_PATH=%PROJECT_DIR%\scripts\v11_archive_collect_once.bat

echo ============================================================
echo Windows Task Scheduler command for OpenHeat v1.1 archive

echo This prints the command only. Copy/paste into an Administrator CMD.
echo ============================================================
echo.
echo schtasks /Create /TN "%TASK_NAME%" /SC MINUTE /MO 15 /TR "cmd /c cd /d %PROJECT_DIR% ^&^& %BAT_PATH%" /F
echo.
echo To delete the task later:
echo schtasks /Delete /TN "%TASK_NAME%" /F
echo.
pause
