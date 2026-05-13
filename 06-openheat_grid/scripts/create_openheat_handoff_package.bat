@echo off
REM Create OpenHeat handoff packages from project root.
REM Usage:
REM   scripts\create_openheat_handoff_package.bat
REM   scripts\create_openheat_handoff_package.bat gpt_sources
REM   scripts\create_openheat_handoff_package.bat full_light

set MODE=%1
if "%MODE%"=="" set MODE=docs_scripts

python scripts\create_openheat_handoff_package.py --root . --mode %MODE%
