# CODEX TASK - v12 pre-scale closeout + formal-hot-day SOLWEIG QA tooling

Repository root:

```text
C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid
```

Environment:

```bat
conda activate openheat
```

## Current project state

Treat the repo as already past the v1.2-beta Core-8 checkpoint:

```text
Wave 0 PASS
Wave 1 base PASS
Core 8 base PASS, 40/40 rasters and 40/40 focus cells
Core 8 overhead_as_canopy PASS, 40/40 rasters and 40/40 focus cells
TP0542 h15 distribution diagnostic PASS / interpretable
```

Current result boundary:

```text
SOLWEIG-derived 100m mixed-cell Tmrt modifier evidence only.
Not local WBGT.
Not observed truth.
Not hazard map.
Not risk map.
No surrogate / ML yet.
```

Current forcing limitation:

```text
Core-8 pilot used v10-epsilon forcing, not formal-hot-day forcing.
```

## Goal

Implement the pre-scale development layer:

```text
1. pilot closeout docs;
2. formal-hot-day QA plan and runbook;
3. formal-hot-day smoke plan CSVs;
4. manifest-builder script;
5. post-run comparison diagnostic script.
```

Do not run QGIS or SOLWEIG. Do not generate rasters.

## Files

Required files:

```text
docs/v12/OpenHeat_v12_pre_scale_development_plan_CN.md
docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_closeout_CN.md
docs/v12/OpenHeat_v12_formal_hotday_SOLWEIG_QA_plan_CN.md
docs/v12/OpenHeat_v12_formal_hotday_SOLWEIG_QA_runbook_CN.md
configs/v12/v12_solweig_formal_hotday_smoke_plan.csv
configs/v12/v12_solweig_formal_hotday_core8_plan_optional.csv
configs/v12/v12_formal_hotday_forcing_config.example.json
scripts/v12_solweig_formal_hotday_manifest_builder.py
scripts/v12_solweig_compare_formal_hotday_vs_epsilon.py
```

Optional because `docs/codex/` is tracked:

```text
docs/codex/CODEX_TASK_v12_pre_scale_closeout_formal_hotday_QA.md
```

## Smoke QA matrix

Use this 20-run smoke design:

```text
cells: TP_0986, TP_0565, TP_0542, TP_0059, TP_0835
hours: h13, h15
scenarios: base, overhead_as_canopy
runs: 5 x 2 x 2 = 20
```

Forcing file paths in the plan CSV:

```text
data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h13.txt
data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h15.txt
```

Do not create these forcing files in this task.

## Self-check commands

```bat
python -m py_compile scripts\v12_solweig_formal_hotday_manifest_builder.py
python -m py_compile scripts\v12_solweig_compare_formal_hotday_vs_epsilon.py

python scripts\v12_solweig_formal_hotday_manifest_builder.py ^
  --plan configs\v12\v12_solweig_formal_hotday_smoke_plan.csv ^
  --base-manifest configs\v12\v12_solweig_core8_base_manifest.csv ^
  --overhead-manifest configs\v12\v12_solweig_core8_overhead_manifest.csv ^
  --out-solweig-manifest configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv ^
  --out-preprocess-manifest configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv ^
  --allow-missing-forcing

python scripts\v12_solweig_compare_formal_hotday_vs_epsilon.py --help
```

Then inspect:

```bat
powershell -Command "(Import-Csv configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv).Count"
powershell -Command "(Import-Csv configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv).Count"
```

Expected:

```text
20
10
```

## Git safety guard

Before staging:

```bat
git status --short
git diff --name-only
```

After staging:

```bat
git diff --cached --name-only | findstr /I "\.tif \.tiff data\\solweig data\\rasters Tmrt_average svfs.zip wall_height wall_aspect raw archive hourly_grid_heatstress_forecast"
```

Expected output: empty.
