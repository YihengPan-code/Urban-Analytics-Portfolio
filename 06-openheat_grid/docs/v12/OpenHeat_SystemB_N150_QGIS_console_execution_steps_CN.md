# OpenHeat System B N150 QGIS Console Execution Steps

## Scope

This guide is for Sprint B7 only: N150 new-run-only SOLWEIG execution. It reuses the completed N24 summaries and does not rerun N24 cells.

It does not compute local WBGT, hazard_score, risk_score, surrogate models, final maps, or System A/B coupling.

## QGIS Desktop run

1. Open QGIS Desktop.
2. Confirm the UMEP plugin is installed and enabled.
3. Confirm the UMEP Processing provider is visible in the Processing toolbox.
4. Open the Python Console.
5. Run:

```python
from pathlib import Path
script = Path(r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid/scripts/qgis/v12_b7_n150_run_solweig_new_from_manifest.py")
exec(compile(script.read_text(encoding="utf-8"), str(script), "exec"))
```

Expected B7 new runs: `1260`.

Existing N24 cells are not rerun. The runner uses the B7 new-run-only matrix and supports `skip_completed` / resume by checking existing `Tmrt_average.tif` outputs.

Monitor:

- progress lines like `[001/1260]`
- repeated preprocessing or SOLWEIG failures
- final `SUMMARY expected=1260 attempted=<n> success=<n> skipped_completed=<n> failed_preprocess=<n> failed_solweig=<n> blocked=<n>`

Raw QGIS/SOLWEIG outputs are local-only under:

```text
data/solweig/v12_n150_tiles/
```

## Repo-side post-run commands

After the QGIS Console run finishes, aggregate the N126 new outputs:

```powershell
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v12_b7_n150_aggregate_new_tmrt.py
```

Then merge with completed N24 summaries:

```powershell
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v12_b7_n150_merge_with_n24.py
```

Then refresh the B7 report:

```powershell
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v12_b7_n150_refresh_execution_report.py
```

## Git safety

Do not commit raw outputs.

Never stage or commit:

```text
.tif
.tiff
svfs.zip
data/solweig/
data/rasters/
```
