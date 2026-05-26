# Sprint B3 QGIS / UMEP Environment Detection

Status: **BLOCKED_FOR_DIRECT_QGIS_PROCESS**

Direct QGIS Processing invocation from the Codex PowerShell context is blocked and should not be retried in this sprint.

- QGIS Desktop candidate found: `C:\Program Files\QGIS 3.44.3\bin\qgis-bin.exe`
- `qgis_process-qgis.bat --version`: confirmed QGIS `3.44.3-Solothurn`
- `python-qgis.bat --version`: confirmed Python `3.12.11`
- `qgis_process.exe`: crashed with Windows access-violation style exit code during probing
- `qgis_process list` / provider discovery: unstable from this Codex PowerShell context
- UMEP Processing provider visibility: **not confirmed from Codex**
- SOLWEIG algorithm id visibility: **not confirmed from Codex**

## Interpretation

This is an environment invocation issue, not a System B target/sample issue.

Do not retry direct `qgis_process` execution from Codex PowerShell. Do not run QGIS from the conda `openheat` Python. Actual SOLWEIG execution must be run manually inside QGIS Desktop Python Console, where QGIS Processing and the UMEP plugin are loaded by QGIS itself.

## Manual QGIS Python Console Instructions

Open QGIS Desktop 3.44.3, confirm the UMEP plugin and Processing provider are visible, then run:

```python
from pathlib import Path
script = Path(r'C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid/scripts/qgis/v12_b3_n24_run_solweig_from_manifest.py')
exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'))
```

The script is a QGIS Python Console script. It is not a `qgis_process` script and must not be run from conda Python.
