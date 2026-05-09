# SOLWEIG steps for T02_conservative_risk_top

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
- tile_type: conservative_risk_top
- focus_cell_id: TP_0378
- overhead_fraction_cell: 0.0376454202107611
- tile_overhead_fraction: 0.01957086764423476
- selection_status: strict
