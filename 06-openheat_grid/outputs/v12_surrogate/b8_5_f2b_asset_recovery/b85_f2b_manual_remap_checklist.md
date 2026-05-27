# B8.5-F2b Manual Remap Checklist

Generated: 2026-05-27 01:42:50

## Decision

`PARTIAL_REMAP_AVAILABLE`

## Safe execution boundary

- QGIS/SOLWEIG executed: `no`
- No rasters were created, copied, opened for analysis, or staged.
- `svfs.zip` was not copied or opened.
- This is not B9, not local WBGT, not hazard_score, not risk, and not System A/B coupling.
- This only determines whether local assets can be found/remapped for later manual execution.

## Human checks before manual QGIS

- Confirm QGIS/UMEP SOLWEIG algorithm availability manually.
- Confirm the selected root aliases are available on the execution machine: `original_project`.
- Local output root action: `human_create_parent_and_directory`.
- Do not copy raster tiles or `svfs.zip` into Git.
- Keep manual SOLWEIG outputs under the local-only root convention.

## Recovered assets by type

`cell_geometry=24; raster_tile=145; svf_zip=48`

## Still missing assets by type

`local_output_root=1; met_forcing_file=5; qgis_algorithm_manual_check=1`
