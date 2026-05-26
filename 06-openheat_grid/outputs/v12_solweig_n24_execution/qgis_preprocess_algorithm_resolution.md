# QGIS Preprocess Algorithm Resolution

Status: **PASS**

- wall_algorithm_id: `umep:Urban Geometry: Wall Height and Aspect`
- wall_found: `True`
- svf_algorithm_id: `umep:Urban Geometry: Sky View Factor`
- svf_found: `True`

## Verified Parameter Mapping

Wall Height and Aspect:

```text
INPUT -> building DSM tile
INPUT_LIMIT -> 3.0 m
OUTPUT_HEIGHT -> wall_height.tif
OUTPUT_ASPECT -> wall_aspect.tif
```

Sky View Factor:

```text
INPUT_DSM -> building DSM tile
INPUT_CDSM -> scenario vegetation DSM
TRANS_VEG -> 3
INPUT_TDSM -> None
INPUT_THEIGHT -> 25.0
ANISO -> True
WALL_SCHEME -> False
KMEANS -> True
CLUSTERS -> 5
INPUT_DEM -> None
INPUT_SVFHEIGHT -> 1.0
OUTPUT_DIR -> svf_<scenario>/
OUTPUT_FILE -> svf_<scenario>/svf.tif
expected zip -> svf_<scenario>/svfs.zip
```

## Registry Parameters Seen

- wall_parameters: `INPUT, INPUT_LIMIT, OUTPUT_HEIGHT, OUTPUT_ASPECT`
- svf_parameters: `INPUT_DSM, INPUT_CDSM, TRANS_VEG, INPUT_TDSM, INPUT_THEIGHT, ANISO, WALL_SCHEME, KMEANS, CLUSTERS, INPUT_DEM, INPUT_SVFHEIGHT, OUTPUT_DIR, OUTPUT_FILE`
