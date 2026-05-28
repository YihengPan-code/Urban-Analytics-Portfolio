# B8.7b.1 Manual Local Root Instructions

Mode: `MANUAL_INPUT_FOUND`

Fill a manual local-root CSV only if automatic metadata discovery cannot resolve the local asset roots.

Expected input path:

`outputs/v12_surrogate/b8_7b1_local_asset_remap/manual_inputs/b87b1_manual_local_roots.csv`

Required columns:

- `root_key`
- `local_root_path`
- `required`
- `description`
- `user_status`
- `notes`

Valid `user_status` values:

- `use`
- `missing`
- `unknown`
- `not_applicable`

Rules:

- Use `use` only for roots you verified locally by path existence/listing.
- Do not copy local assets into Git.
- Do not open `.tif`, `.tiff`, `.vrt`, `.asc`, `.img`, `.nc`, `.grib`, raw SOLWEIG rasters, or `svfs.zip`.
- Do not run QGIS or SOLWEIG in this lane.
- Do not create a run-ready manifest, QGIS runner, local runner, or local execution package.

Claim boundary:

B8.7b.1 local asset readiness only; not B9, not AOI-wide prediction, not local WBGT, not hazard_score or risk_score, not exposure/vulnerability score, not observed truth, not causal feature importance, no raster read/write/copy/open, no QGIS/SOLWEIG execution, no run-ready N300 manifest, no QGIS runner, no local runner, no Tmrt-to-WBGT conversion, and no System A/B coupling.
