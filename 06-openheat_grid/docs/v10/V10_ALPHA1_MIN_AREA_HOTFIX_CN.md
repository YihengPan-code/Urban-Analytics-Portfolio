# OpenHeat v1.0-alpha.1 min_area hotfix

## Problem

Running:

```bat
scripts\v10_run_alpha1_hotfix_pipeline.bat
```

failed at the deduplication step:

```text
TypeError: '<' not supported between instances of 'float' and 'dict'
```

The failing line was:

```python
if geom.area < min_area:
```

`min_area` is a dictionary in the current config, likely source-specific, such as:

```json
"min_area_m2": {
  "default": 10,
  "osm": 10,
  "microsoft": 20,
  "google": 20
}
```

The script assumed it was a single numeric value.

## Fix

Run:

```bat
python scripts\patch_v10_alpha1_min_area.py
```

Then re-run:

```bat
scripts\v10_run_alpha1_hotfix_pipeline.bat
```

The patch makes `v10_deduplicate_building_footprints.py` accept both:

```json
"min_area_m2": 10
```

and:

```json
"min_area_m2": {
  "default": 10,
  "osm": 10,
  "microsoft": 20,
  "google": 20
}
```

## Scope

This only fixes the deduplication min-area threshold parsing. It does not change the core deduplication logic, height assignment, rasterization, or completeness audit.

After re-running the pipeline, check:

```bat
python -c "import rasterio; p='data/rasters/v10/dsm_buildings_2m_augmented.tif'; src=rasterio.open(p); print('nodata:', src.nodata); print('shape:', src.shape); src.close()"
```

Expected:

```text
nodata: None
```
