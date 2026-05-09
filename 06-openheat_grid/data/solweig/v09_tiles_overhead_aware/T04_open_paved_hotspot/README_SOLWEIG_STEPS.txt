# SOLWEIG steps for T04_open_paved_hotspot

Use these UMEP-ready rasters in QGIS/UMEP:

- `dsm_buildings_tile.tif`
- `dsm_vegetation_tile.tif` if present

The `*_masked.tif` files use nodata=-9999 and are intended for Python QA / aggregation, not for UMEP GUI.

Recommended SOLWEIG times for v0.9-gamma:
- 2026-05-07 10:00
- 2026-05-07 12:00
- 2026-05-07 13:00
- 2026-05-07 15:00
- 2026-05-07 16:00

Put Tmrt outputs in this folder or a subfolder named `solweig_outputs/`.
Please keep HHMM in filenames, e.g.:
- `Tmrt_2026_5_7_1000D.tif`
- `Tmrt_2026_5_7_1300D.tif`

Tile notes:
- tile_type: open_paved_hotspot
- focus_cell_id: TP_0120
- overhead_fraction_cell: 0.0
- tile_overhead_fraction: 0.049936412207636546
- selection_status: strict
