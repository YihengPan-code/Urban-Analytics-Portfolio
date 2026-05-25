@echo off
setlocal enabledelayedexpansion

REM OpenHeat v12 formal-hotday smoke healthcheck
REM Run from repo root:
REM   scripts\v12_formal_hotday_smoke_healthcheck.bat

set REPO=%CD%
set OUT=outputs\v12_solweig_typology_pilot\formal_hotday_smoke_summary
set LOG=%OUT%\v12_formal_hotday_smoke_healthcheck.txt

if not exist "%OUT%" mkdir "%OUT%"

echo ================================================== > "%LOG%"
echo OpenHeat v12 formal-hotday smoke healthcheck       >> "%LOG%"
echo repo=%REPO%                                       >> "%LOG%"
echo generated_at=%DATE% %TIME%                         >> "%LOG%"
echo ================================================== >> "%LOG%"
echo. >> "%LOG%"

echo [1/8] Git head/status
echo [1/8] Git head/status >> "%LOG%"
git log --oneline --decorate -3 >> "%LOG%" 2>&1
git status -sb >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo [2/8] Forcing files
echo [2/8] Forcing files >> "%LOG%"
dir data\solweig\v12_formal_hotday_forcing >> "%LOG%" 2>&1
powershell -NoProfile -Command "$files=@('data\solweig\v12_formal_hotday_forcing\v12_formal_hotday_S128_h13.txt','data\solweig\v12_formal_hotday_forcing\v12_formal_hotday_S128_h15.txt'); foreach($p in $files){ if(Test-Path $p){ $l=Get-Content $p; Write-Output ('FORCING ' + $p + ' lines=' + $l.Count + ' duplicate_rows=' + ($l[1] -eq $l[2])); Write-Output ('HEADER ' + $l[0]) } else { Write-Output ('MISSING ' + $p) } }" >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo [3/8] Manifest row counts
echo [3/8] Manifest row counts >> "%LOG%"
powershell -NoProfile -Command "$a=(Import-Csv configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv).Count; $b=(Import-Csv configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv).Count; Write-Output ('solweig_manifest_rows=' + $a); Write-Output ('preprocess_manifest_rows=' + $b)" >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo [4/8] Formal-hotday aggregation report key lines
echo [4/8] Formal-hotday aggregation report key lines >> "%LOG%"
findstr /I "Rows Raster Focus qa_status" "%OUT%\v12_solweig_typology_aggregation_report.md" >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo [5/8] Formal-hotday summary table
echo [5/8] Formal-hotday summary table >> "%LOG%"
python -c "import pandas as pd; p=r'%OUT%\tmrt_cell_summary_long.csv'; d=pd.read_csv(p); preferred=['cell_id','hour_sgt','scenario_id','tmrt_mean_c','tmrt_p90_c','tmrt_max_c','delta_tmrt_p90_c','m_rad_pct','qa_status']; cols=[c for c in preferred if c in d.columns]; missing=[c for c in preferred if c not in d.columns]; print('available_columns=' + ','.join(d.columns)); print('missing_preferred_columns=' + (','.join(missing) if missing else 'none')); print(('[WARN] missing preferred columns: ' + ','.join(missing)) if missing else '[PASS] all preferred columns present'); print(d[cols].round(3).to_string(index=False) if cols else '[WARN] no preferred columns available')" >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo [6/8] Base-vs-overhead delta by cell/hour
echo [6/8] Base-vs-overhead delta by cell/hour >> "%LOG%"
python -c "import pandas as pd; p=r'%OUT%\tmrt_cell_summary_long.csv'; outp=r'%OUT%\base_vs_overhead_delta_by_cell_hour.csv'; d=pd.read_csv(p); wide=d.pivot_table(index=['cell_id','hour_sgt'], columns='scenario_id', values=['tmrt_mean_c','tmrt_p90_c','tmrt_max_c'], aggfunc='first'); rows=[]; idx=wide.index; cols=wide.columns; import math; [rows.append({'cell_id':i[0],'hour_sgt':i[1],'delta_mean_overhead_minus_base':wide.loc[i,('tmrt_mean_c','overhead_as_canopy')]-wide.loc[i,('tmrt_mean_c','base')],'delta_p90_overhead_minus_base':wide.loc[i,('tmrt_p90_c','overhead_as_canopy')]-wide.loc[i,('tmrt_p90_c','base')],'delta_max_overhead_minus_base':wide.loc[i,('tmrt_max_c','overhead_as_canopy')]-wide.loc[i,('tmrt_max_c','base')]}) for i in idx]; out=pd.DataFrame(rows); out.to_csv(outp,index=False); print(out.round(3).to_string(index=False)); print('delta_table_generated=' + outp + ' rows=' + str(len(out)))" >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo [7/8] Formal-vs-epsilon comparison
echo [7/8] Formal-vs-epsilon comparison >> "%LOG%"
type "%OUT%\formal_vs_epsilon_comparison.md" >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo [8/8] Staged file safety scan
echo [8/8] Staged file safety scan >> "%LOG%"
git diff --cached --name-only >> "%LOG%" 2>&1
git diff --cached --name-only | findstr /I "\.tif \.tiff data\\solweig data\\rasters Tmrt_average svfs.zip wall_height wall_aspect hourly_grid_heatstress_forecast" >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo [SUMMARY] PASS/WARN checks
echo [SUMMARY] PASS/WARN checks >> "%LOG%"
powershell -NoProfile -Command "$warn=0; function Check($name,$ok,$detail){ if($ok){ Write-Output ('PASS ' + $name + ' - ' + $detail) } else { $script:warn=1; Write-Output ('WARN ' + $name + ' - ' + $detail) } }; $forcing=@('data\solweig\v12_formal_hotday_forcing\v12_formal_hotday_S128_h13.txt','data\solweig\v12_formal_hotday_forcing\v12_formal_hotday_S128_h15.txt'); $forcingOk=$true; foreach($p in $forcing){ if(Test-Path $p){ $l=Get-Content $p; if($l.Count -lt 3 -or $l[1] -ne $l[2]){ $forcingOk=$false } } else { $forcingOk=$false } }; Check 'forcing files exist and duplicate rows true' $forcingOk ('files=' + $forcing.Count); $solweig=0; if(Test-Path 'configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv'){ $solweig=(Import-Csv 'configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv').Count }; Check 'solweig manifest rows == 20' ($solweig -eq 20) ('rows=' + $solweig); $pre=0; if(Test-Path 'configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv'){ $pre=(Import-Csv 'configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv').Count }; Check 'preprocess manifest rows == 10' ($pre -eq 10) ('rows=' + $pre); $agg=0; if(Test-Path '%OUT%\tmrt_cell_summary_long.csv'){ $agg=(Import-Csv '%OUT%\tmrt_cell_summary_long.csv').Count }; Check 'aggregation rows == 20' ($agg -eq 20) ('rows=' + $agg); $report=''; if(Test-Path '%OUT%\v12_solweig_typology_aggregation_report.md'){ $report=Get-Content '%OUT%\v12_solweig_typology_aggregation_report.md' -Raw }; $linesOk=($report -match 'Raster' -and $report -match 'Focus'); Check 'raster/focus completeness lines present' $linesOk ('report=%OUT%\v12_solweig_typology_aggregation_report.md'); $deltaPath='%OUT%\base_vs_overhead_delta_by_cell_hour.csv'; $deltaOk=(Test-Path $deltaPath); Check 'base-vs-overhead delta table generated' $deltaOk ('table=' + $deltaPath); if($warn){ Write-Output 'SUMMARY_STATUS=WARN' } else { Write-Output 'SUMMARY_STATUS=PASS' }" >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo ================================================== >> "%LOG%"
echo HEALTHCHECK COMPLETE                              >> "%LOG%"
echo Paste this file to ChatGPT if review is needed:    >> "%LOG%"
echo %LOG%                                             >> "%LOG%"
echo ================================================== >> "%LOG%"

echo.
echo Healthcheck written to:
echo %LOG%
echo.
type "%LOG%"
