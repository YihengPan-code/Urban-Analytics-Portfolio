# v12 QGIS preprocessing automation — final runner guide

## 0. Scope

This guide automates the two QGIS/UMEP preprocessing steps needed before SOLWEIG:

```text
Wall Height and Aspect
Sky View Factor
```

It does not run SOLWEIG itself.

## 1. Confirmed local UMEP algorithms

Confirmed from local QGIS discovery and Processing History:

```text
Wall:
  algorithm = umep:Urban Geometry: Wall Height and Aspect
  params = INPUT, INPUT_LIMIT, OUTPUT_HEIGHT, OUTPUT_ASPECT

SVF:
  algorithm = umep:Urban Geometry: Sky View Factor
  params = INPUT_DSM, INPUT_CDSM, TRANS_VEG, INPUT_TDSM, INPUT_THEIGHT,
           ANISO, WALL_SCHEME, KMEANS, CLUSTERS, INPUT_DEM,
           INPUT_SVFHEIGHT, OUTPUT_DIR, OUTPUT_FILE
```

The runner writes:

```text
wall_height.tif
wall_aspect.tif
svf_base/svfs.zip
```

for each manifest row.

## 2. Create Wave 1 preprocessing manifest

Run in normal terminal:

```bat
python scripts\v12_solweig_make_preprocess_manifest.py ^
  --tile-metadata data\solweig\v12_typology_tiles\v12_typology_tile_metadata.csv ^
  --out configs\v12\v12_solweig_preprocess_wave1_base_manifest.csv ^
  --cells TP_0986,TP_0542,TP_0059 ^
  --scenarios base
```

Check:

```bat
type configs\v12\v12_solweig_preprocess_wave1_base_manifest.csv
```

Expected rows:

```text
TP_0986 base
TP_0542 base
TP_0059 base
```

## 3. Run preprocessing in QGIS

Open QGIS:

```text
Plugins → Python Console → Show Editor
```

Run:

```python
from pathlib import Path
exec(compile(Path('C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid/scripts/qgis/v12_qgis_preprocess_from_manifest.py').read_text(), 'v12_qgis_preprocess_from_manifest.py', 'exec'))
```

Outputs:

```text
outputs/v12_solweig_typology_pilot/qgis_preprocess/v12_qgis_preprocess_log.txt
outputs/v12_solweig_typology_pilot/qgis_preprocess/v12_qgis_preprocess_log.csv
```

## 4. Check outputs in normal terminal

```bat
python scripts\v12_solweig_check_preprocess_outputs.py ^
  --manifest configs\v12\v12_solweig_preprocess_wave1_base_manifest.csv
```

Expected:

```text
n_ready = 3
n_not_ready = 0
```

## 5. Then run Wave 1 SOLWEIG

Only after preprocessing passes, create / run Wave 1 SOLWEIG manifest:

```text
TP_0986 / TP_0542 / TP_0059
× h10 / h13 / h16
× base
```

Use:

```text
scripts/v12_solweig_qgis_loop.py
```

## 6. Do not commit

Do not commit:

```text
wall_height.tif
wall_aspect.tif
svf_base/
svfs.zip
svf.tif
*.tif
```

Only commit small scripts, config, docs, and small summary CSV/MD after review.
