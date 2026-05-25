# OpenHeat v1.2-beta formal-hot-day SOLWEIG QA runbook

**Document date:** 2026-05-25
**Use case:** local Windows / Anaconda Prompt + QGIS Python Console execution

## 0. Preconditions

```bat
cd C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid
conda activate openheat
git status --short
```

Expected before starting:

```text
No unintended staged files.
No .tif/.tiff/data/solweig/data/rasters staged.
Formal-hot-day forcing files exist locally.
```

## 1. Add plan files and helper scripts

The development package adds:

```text
docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_closeout_CN.md
docs/v12/OpenHeat_v12_pre_scale_development_plan_CN.md
docs/v12/OpenHeat_v12_formal_hotday_SOLWEIG_QA_plan_CN.md
docs/v12/OpenHeat_v12_formal_hotday_SOLWEIG_QA_runbook_CN.md
configs/v12/v12_solweig_formal_hotday_smoke_plan.csv
configs/v12/v12_solweig_formal_hotday_core8_plan_optional.csv
configs/v12/v12_formal_hotday_forcing_config.example.json
scripts/v12_solweig_formal_hotday_manifest_builder.py
scripts/v12_solweig_compare_formal_hotday_vs_epsilon.py
```

## 2. Build manifests

```bat
python scripts\v12_solweig_formal_hotday_manifest_builder.py ^
  --plan configs\v12\v12_solweig_formal_hotday_smoke_plan.csv ^
  --base-manifest configs\v12\v12_solweig_core8_base_manifest.csv ^
  --overhead-manifest configs\v12\v12_solweig_core8_overhead_manifest.csv ^
  --out-solweig-manifest configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv ^
  --out-preprocess-manifest configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv
```

If forcing files are not generated yet and you only want to test manifest generation:

```bat
python scripts\v12_solweig_formal_hotday_manifest_builder.py ^
  --plan configs\v12\v12_solweig_formal_hotday_smoke_plan.csv ^
  --base-manifest configs\v12\v12_solweig_core8_base_manifest.csv ^
  --overhead-manifest configs\v12\v12_solweig_core8_overhead_manifest.csv ^
  --out-solweig-manifest configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv ^
  --out-preprocess-manifest configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv ^
  --allow-missing-forcing
```

Expected:

```text
SOLWEIG manifest rows: 20
Preprocess manifest rows: 10
```

## 3. Run QGIS preprocessing

Open QGIS, then Python Console. Execute the repo script with the formal smoke preprocess manifest.

Expected script:

```text
scripts/qgis/v12_qgis_preprocess_from_manifest.py
```

Manifest:

```text
configs/v12/v12_solweig_preprocess_formal_hotday_smoke_manifest.csv
```

After QGIS preprocessing, verify:

```bat
python scripts\v12_solweig_check_preprocess_outputs.py ^
  --manifest configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv
```

## 4. Run SOLWEIG in QGIS Python Console

Use existing path-safe QGIS loop:

```text
scripts/v12_solweig_qgis_loop.py
```

Run manifest:

```text
configs/v12/v12_solweig_formal_hotday_smoke_manifest.csv
```

Important:

```text
Use INPUTMET, not INPUT_MET.
Use QGIS Python Console, not plain Python, for UMEP processing.run.
```

## 5. Aggregate formal-hot-day smoke results

Use the existing aggregator, pointing to the formal-hot-day smoke manifest and output summary directory.

Suggested output:

```text
outputs/v12_solweig_typology_pilot/formal_hotday_smoke_summary/
```

If aggregator CLI differs in your local repo, check:

```bat
python scripts\v12_solweig_aggregate_tmrt.py --help
```

Then run the equivalent of:

```bat
python scripts\v12_solweig_aggregate_tmrt.py ^
  --manifest configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv ^
  --output-dir outputs\v12_solweig_typology_pilot\formal_hotday_smoke_summary
```

## 6. Compare against v10-epsilon-forcing Core-8 pilot

```bat
python scripts\v12_solweig_compare_formal_hotday_vs_epsilon.py ^
  --epsilon-base outputs\v12_solweig_typology_pilot\core8_base_summary\tmrt_cell_summary_long.csv ^
  --epsilon-overhead outputs\v12_solweig_typology_pilot\core8_overhead_summary\tmrt_cell_summary_long.csv ^
  --formal-summary outputs\v12_solweig_typology_pilot\formal_hotday_smoke_summary\tmrt_cell_summary_long.csv ^
  --out-csv outputs\v12_solweig_typology_pilot\formal_hotday_smoke_summary\formal_vs_epsilon_comparison.csv ^
  --out-md outputs\v12_solweig_typology_pilot\formal_hotday_smoke_summary\formal_vs_epsilon_comparison.md
```

## 7. Commit guard

Before commit:

```bat
git status --short
git diff --cached --name-only
```

Hard guard:

```bat
git diff --cached --name-only | findstr /I "\.tif \.tiff data\\solweig data\\rasters Tmrt_average svfs.zip wall_height wall_aspect raw archive hourly_grid_heatstress_forecast"
```

Expected: no output.

Stage only docs/config/scripts/small summaries:

```bat
git add docs\v12\OpenHeat_v12_SOLWEIG_typology_pilot_closeout_CN.md
git add docs\v12\OpenHeat_v12_pre_scale_development_plan_CN.md
git add docs\v12\OpenHeat_v12_formal_hotday_SOLWEIG_QA_plan_CN.md
git add docs\v12\OpenHeat_v12_formal_hotday_SOLWEIG_QA_runbook_CN.md
git add configs\v12\v12_formal_hotday_forcing_config.example.json
git add configs\v12\v12_solweig_formal_hotday_smoke_plan.csv
git add configs\v12\v12_solweig_formal_hotday_core8_plan_optional.csv
git add configs\v12\v12_solweig_formal_hotday_smoke_manifest.csv
git add configs\v12\v12_solweig_preprocess_formal_hotday_smoke_manifest.csv
git add scripts\v12_solweig_formal_hotday_manifest_builder.py
git add scripts\v12_solweig_compare_formal_hotday_vs_epsilon.py
```

Suggested commit after static implementation, before local SOLWEIG outputs:

```bat
git commit -m "chore(v12): add formal-hot-day SOLWEIG QA planning tools"
```

Suggested commit after smoke result summaries only:

```bat
git add outputs\v12_solweig_typology_pilot\formal_hotday_smoke_summary\*.md
git add outputs\v12_solweig_typology_pilot\formal_hotday_smoke_summary\*.csv
git commit -m "docs(v12): add formal-hot-day SOLWEIG smoke QA summary"
```
