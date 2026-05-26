# OpenHeat System B N24 QGIS Console Execution Steps

This is the manual QGIS Desktop execution guide for Sprint B3/B3.1/B3.2. Codex must not run `qgis_process`, must not run QGIS from conda Python, and must not run full SOLWEIG from PowerShell.

## 1. Start QGIS Desktop

1. Open QGIS Desktop 3.44.3.
2. Confirm the UMEP plugin is installed and enabled.
3. Open Processing Toolbox.
4. Confirm these UMEP algorithms are visible:
   - `umep:Urban Geometry: Wall Height and Aspect`
   - `umep:Urban Geometry: Sky View Factor`
   - `umep:Outdoor Thermal Comfort: SOLWEIG`

Direct `qgis_process` invocation from the Codex PowerShell context was unstable and is blocked for this sprint.

## 2. Run the B3.1 Console Script

In QGIS Desktop:

1. Open Plugins > Python Console.
2. Open the console editor.
3. Run:

```python
from pathlib import Path
script = Path(r'C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid/scripts/qgis/v12_b3_n24_run_solweig_from_manifest.py')
exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'))
```

The script is a QGIS Python Console script. It does not require conda Python and does not require `qgis_process`.

## 3. What the Script Does

Expected main runs: `240`.

For each frozen B2.2 N24 cell, the script prepares or reuses:

- tile building DSM
- flat DEM
- base vegetation DSM
- overhead_as_canopy vegetation DSM
- wall_height and wall_aspect via UMEP Wall Height and Aspect
- `svfs.zip` for `base` and `overhead_as_canopy` via UMEP Sky View Factor

Then it runs the frozen B2.2 run matrix:

- cells: `24`
- scenarios: `base`, `overhead_as_canopy`
- hours SGT: `10`, `12`, `13`, `15`, `16`
- expected main SOLWEIG runs: `240`

The script supports `skip_completed=true`. Existing readable `Tmrt_average.tif` outputs are logged as `skipped_completed`.

B3.2 note: the script now continues after successful runs. If the first run already produced `Tmrt_average.tif`, a rerun should log `[001/240] ... skipped_completed` and continue to `[002/240]`.

## 4. Log Handling

The script does not append silently to an old all-blocked log.

At the start of each manual run:

- if `outputs/v12_solweig_n24_execution/n24_solweig_run_log.csv` exists, it is moved to `outputs/v12_solweig_n24_execution/archived_run_logs/`
- a new log is started with `attempt_id` and `run_started_at`

Run log path:

```text
outputs/v12_solweig_n24_execution/n24_solweig_run_log.csv
```

Allowed status values:

```text
success
skipped_completed
failed_preprocess
failed_solweig
blocked_environment
blocked_algorithm_missing
```

At the end, the console prints a summary line:

```text
SUMMARY expected=240 attempted=<n> success=<n> skipped_completed=<n> failed_preprocess=<n> failed_solweig=<n> blocked=<n>
```

`attempted` excludes `skipped_completed` rows and includes rows that failed during preprocessing or SOLWEIG.

## 5. Outputs

Raw local SOLWEIG outputs:

```text
data/solweig/v12_n24_tiles/
```

Summary/log outputs:

```text
outputs/v12_solweig_n24_execution/n24_solweig_run_log.csv
outputs/v12_solweig_n24_execution/qgis_algorithm_resolution.md
outputs/v12_solweig_n24_execution/qgis_preprocess_algorithm_resolution.md
outputs/v12_solweig_n24_execution/n24_effective_solweig_parameters.json
outputs/v12_solweig_n24_execution/n24_effective_solweig_parameters.md
```

After manual QGIS execution completes, aggregate from conda `openheat`:

```powershell
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v12_b3_n24_aggregate_tmrt.py
```

## 6. Safety Rules

- Raw rasters and SOLWEIG outputs under `data/solweig/v12_n24_tiles/` are local-only.
- Do not commit `data/solweig/` raw outputs.
- Do not commit `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG folders, or large raw raster artifacts.
- Do not stage or commit from QGIS.
- The QGIS script does not call `git add`, `git commit`, or `qgis_process`.

## 7. Scientific Boundary

This sprint is System B SOLWEIG-derived Tmrt execution only.

It does not produce local WBGT, hazard_score, risk_score, System A/B coupling, surrogate models, final maps, or observed validation truth.
