# OpenHeat v1.0-alpha Patch

This patch adds an OSM-first augmented building DSM pipeline for OpenHeat-ToaPayoh.

## Files

- configs/v10/v10_alpha_augmented_dsm_config.example.json
- scripts/v10_extract_osm_buildings.py
- scripts/v10_standardize_building_sources.py
- scripts/v10_deduplicate_building_footprints.py
- scripts/v10_assign_building_heights.py
- scripts/v10_rasterize_augmented_dsm.py
- scripts/v10_building_completeness_audit.py
- scripts/v10_run_alpha_osm_augmented_dsm_pipeline.bat
- docs/v10/V10_ALPHA_AUGMENTED_DSM_GUIDE_CN.md
- requirements_v10_alpha.txt

## Quick run

```bat
pip install -r requirements_v10_alpha.txt
scripts10_run_alpha_osm_augmented_dsm_pipeline.bat
```

## Main output

- data/rasters/v10/dsm_buildings_2m_augmented.tif
- outputs/v10_dsm_audit/v10_completeness_gain_report.md
- outputs/v10_dsm_audit/v10_building_completeness_per_tile.csv

