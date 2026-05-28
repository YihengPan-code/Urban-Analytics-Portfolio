# OpenHeat System B B8.7b.4 + B87C Materialization Package

## Decision

B87C materialization is a local-only, missing-only, per-cell cached preparation
step for the B87C SOLWEIG execution package. It does not run SOLWEIG and does
not create WBGT, risk, AOI, B9, or observed-truth outputs.

## Current Materialization Rule

- Existing partial assets under `C:/OpenHeat-local/solweig/b87c_n300` must be
  preserved.
- Shared per-cell assets are generated once per cell, not once per scenario:
  `focus_cell.geojson`, building DSM, flat DEM, base CDSM, overhead canopy CDSM,
  and the overhead canopy raster/tile.
- Wall height/aspect are shared per cell and are generated once per cell.
- SVF remains scenario-specific:
  `svf_base/svfs.zip` and `svf_overhead_as_canopy/svfs.zip` are separate assets.
- `overhead_as_canopy` must not reuse base SVF.

## Safe Defaults

Repo-side package and runner defaults are safe:

- `run_enabled`: `false`
- `dry_run`: `true`
- `materialization_mode`: `missing_only`
- `overwrite_existing_assets`: `false`
- `STAGE`: `remaining` for the materialization runner

An existing non-empty asset is skipped. Empty, non-file, or otherwise ambiguous
targets are marked `needs_review` and are not overwritten unless overwrite is
explicitly enabled.

## Recommended Order

1. Run materialization first for remaining or missing assets in QGIS.
2. Rebuild the manifest with `scripts/v12_b87c_manifest_builder.py`.
3. Audit the manifest with `scripts/v12_b87c_manifest_audit.py`.
4. Only after all manifest rows are ready, run SOLWEIG smoke, pilot, then full
   stages.

## Git Hygiene

Do not commit rasters, `svfs.zip`, raw API dumps, or local execution outputs.
Heavy assets stay under `C:/OpenHeat-local`; repo outputs are limited to compact
CSV, Markdown, YAML, and Python artifacts.
