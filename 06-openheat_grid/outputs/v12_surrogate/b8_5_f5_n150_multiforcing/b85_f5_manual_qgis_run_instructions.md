# B8.5-F5 Manual QGIS N150 / 3000-Run Instructions

Generated: 2026-05-27 17:21:16

## Decision

`READY_FOR_HUMAN_N150_MULTIFORCING`

## Authorized Runset

- Cells: `150`
- Forcing days: `FD01_high_shortwave_hot_20260507, FD02_humid_hot_cloudy_or_diffuse_20260508`
- Hours SGT: `10, 12, 13, 15, 16`
- Scenarios: `base, overhead_as_canopy`
- Expected run count: `3000`
- Pre-execution ready count: `3000/3000`

## Human Gate

Codex/Python did not run QGIS or SOLWEIG. This package authorizes only the N150 / 3000 human-controlled runset. It is not B9, not local WBGT, not risk, not observed truth, not causal feature importance, and not Tmrt-to-WBGT conversion.

## Required Manual Steps

1. Review the manifest: `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_n150_manifest.csv`.
2. Review the repo-tracked runner without changing it: `scripts/qgis/v12_b85_f5_n150_qgis_runner.py`.
3. Copy the runner to a local-only path under `C:/OpenHeat-local/solweig/b85_f5_n150`.
4. Keep the repo-tracked runner as `DRY_RUN = True`.
5. In the local-only copy only, manually change `DRY_RUN = False`.
6. Preserve the safety gate; do not remove the Git-worktree refusal checks.
7. Run exactly 3000 manifest rows. DO NOT RUN FULL AOI. N150 / 3000 ONLY.
8. Keep the run log at `C:/OpenHeat-local/solweig/b85_f5_n150/run_logs/b85_f5_n150_qgis_run_log.csv`.
9. Keep SOLWEIG outputs under `C:/OpenHeat-local/solweig/b85_f1_tiles` only.
10. Do not commit rasters, `.tif`, `.tiff`, `svfs.zip`, local met forcing files, or local-only outputs.

## QGIS Console Robust Wrapper

Use this wrapper in the QGIS Python Console after copying the runner locally and editing only the local copy. It reads the local runner with `encoding="utf-8-sig"`, injects `__file__`, sets `sys.argv = [runner]`, and changes `cwd` to `runner.parent`.

```python
from pathlib import Path
import os
import sys

runner = Path(r"C:/OpenHeat-local/solweig/b85_f5_n150/v12_b85_f5_n150_qgis_runner.py")
code = runner.read_text(encoding="utf-8-sig")
globals_dict = {
    "__name__": "__console__",
    "__file__": str(runner),
}
sys.argv = [str(runner)]
os.chdir(runner.parent)
exec(compile(code, str(runner), "exec"), globals_dict)
```

## PowerShell Copy Encoding Note

If copying through PowerShell and editing the local runner, write the local copy as UTF-8 without BOM. Do not copy or open `svfs.zip`.

```powershell
$src = "C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/scripts/qgis/v12_b85_f5_n150_qgis_runner.py"
$dst = "C:/OpenHeat-local/solweig/b85_f5_n150/v12_b85_f5_n150_qgis_runner.py"
New-Item -ItemType Directory -Force -Path (Split-Path $dst)
$text = Get-Content -Raw -Encoding UTF8 $src
[System.IO.File]::WriteAllText($dst, $text, [System.Text.UTF8Encoding]::new($false))
```

## After Manual Execution

Run, from the repo subdirectory:

```powershell
python scripts/v12_b85_f5_validate_n150_multiforcing.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml
python scripts/v12_b85_f5_raster_qa.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml
python scripts/v12_b85_f5_label_merge.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml
python scripts/v12_b85_f5_stability_summary.py --config configs/v12/systemb_b85_f5_n150_multiforcing.yaml
```

B9 remains blocked after F5 until a separate promotion review explicitly authorizes it.
