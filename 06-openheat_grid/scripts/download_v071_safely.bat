@echo off
echo === v0.7.1 safe download (with rate-limit cooldowns) ===
echo.
echo Initial cooldown 120s for the previous 429...
timeout /t 120 /nobreak

set DATASETS=bus_stops mrt_exits hawker_centres sport_facilities preschools eldercare_services

for %%D in (%DATASETS%) do (
    echo.
    echo === Downloading %%D ===
    python scripts\v071_download_risk_exposure_data.py --datasets %%D
    if errorlevel 1 (
        echo [WARN] %%D failed, retrying once after 90s...
        timeout /t 90 /nobreak
        python scripts\v071_download_risk_exposure_data.py --datasets %%D
    )
    timeout /t 60 /nobreak
)

echo.
echo === Download phase complete ===
echo Listing downloaded files:
dir data\raw\poi\*.geojson