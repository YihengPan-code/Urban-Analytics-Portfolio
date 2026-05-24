# v1.2 SOLWEIG Wave 0 run guide

## 0. Purpose

Wave 0 verifies that QGIS + UMEP + SOLWEIG can still run with the recovered v10-epsilon source-of-truth setup.

Wave 0 uses:

```text
cell = TP_0986
tile = data/solweig/v10_epsilon_tiles/E02_confident_hot_anchor_2_TP_0986
hour = 13 SGT
scenario = base
forcing = data/solweig/v09_met_forcing_2026_05_07_S128_h13.txt
```

It reuses v10 tile inputs but writes a new v12 output:

```text
outputs/v12_solweig_typology_pilot/wave0_reuse_v10_TP0986_h13_base/Tmrt_average.tif
```

This is a technical smoke test, not the Core-8 pilot.

## 1. Files added

```text
configs/v12/v12_solweig_typology_config.example.json
configs/v12/v12_solweig_wave0_reuse_v10_manifest.csv
configs/v12/v12_solweig_core8_run_matrix_planned.csv

scripts/v12_solweig_provenance_check.py
scripts/v12_solweig_wave0_reuse_v10_qgis.py
scripts/v12_solweig_select_cells.py
scripts/v12_solweig_prepare_rasters.py
scripts/v12_solweig_qgis_loop.py
scripts/v12_solweig_aggregate_tmrt.py
```

## 2. First local checks

Run in normal terminal:

```bat
python scripts\v12_solweig_provenance_check.py ^
  --config configs\v12\v12_solweig_typology_config.example.json
```

Expected:

```text
n_missing = 0
```

If anything is missing, do not run QGIS.

## 3. Run Wave 0 in QGIS

Open QGIS.

Then:

```text
Plugins > Python Console > Show Editor
```

Open or paste:

```text
scripts/v12_solweig_wave0_reuse_v10_qgis.py
```

Run the script.

Expected output:

```text
outputs/v12_solweig_typology_pilot/wave0_reuse_v10_TP0986_h13_base/Tmrt_average.tif
outputs/v12_solweig_typology_pilot/wave0_reuse_v10_TP0986_h13_base_log.txt
```

## 4. Aggregate Wave 0

After QGIS run, return to terminal:

```bat
python scripts\v12_solweig_aggregate_tmrt.py ^
  --manifest configs\v12\v12_solweig_wave0_reuse_v10_manifest.csv ^
  --out-dir outputs\v12_solweig_typology_pilot\wave0_summary
```

Inspect:

```bat
type outputs\v12_solweig_typology_pilot\wave0_summary\v12_solweig_typology_aggregation_report.md
```

## 5. Pass criteria

Wave 0 passes if:

```text
Tmrt_average.tif exists
aggregation script reads it
n_valid_pixels > 0
tmrt_mean_c / tmrt_p90_c / tmrt_max_c are finite
raster aligns with TP_0986 focus cell
```

## 6. After Wave 0 passes

Do not immediately run 80 runs.

Next steps:

```text
1. Prepare v12 Core-8 tile folders:
   python scripts\v12_solweig_select_cells.py --config configs\v12\v12_solweig_typology_config.example.json

2. Prepare v12 tile rasters:
   python scripts\v12_solweig_prepare_rasters.py --config configs\v12\v12_solweig_typology_config.example.json

3. Generate Wall Height / Aspect and SVF in QGIS for v12 tiles.

4. Create QGIS manifest for Wave 1.

5. Run Wave 1:
   TP_0986, TP_0542, TP_0059 × hours 10/13/16 × base
```

## 7. Do-not-commit list

Do not commit:

```text
*.tif
*.tiff
data/solweig/v12_typology_tiles/*/dsm_*.tif
data/solweig/v12_typology_tiles/*/wall_*.tif
data/solweig/v12_typology_tiles/*/svf_*/
data/solweig/v12_typology_tiles/*/solweig_*/
outputs/v12_solweig_typology_pilot/**/Tmrt_average.tif
```

Small CSV/MD summaries can be committed later after review.
