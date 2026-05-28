# B8.7b.4 + B87C Materialization Execution Package Report

Status: `B87B4_DIAGNOSTIC_ONLY`

## 1. Why this follows B8.7b.3

B8.7b.3 locked the full-AOI raster/vector sources and concluded that B87C was blocked until local per-cell assets and an execution package existed. This lane converts that source lock into a local-only asset plan, manifest, QGIS materialization runner, SOLWEIG runner, resume logic, and postrun QA packet.

## 2. Source lock summary

dsm=LOCKED; cdsm_base_vegetation=LOCKED; grid_geometry=LOCKED; svf_base_full=LOCKED_FULL_AOI_SOURCE_ONLY; svf_overhead=REQUIRES_SCENARIO_SPECIFIC_MATERIALIZATION

## 3. Materialized local asset readiness

- Candidate cells: `150`
- Local asset root: `C:/OpenHeat-local/solweig/b87c_n300/assets`
- Base ready cells: `0`
- Overhead ready cells: `0`
- Current non-ready assets are documented in `b87b4_materialization_blocker_register.csv`.

## 4. SVF materialization status

SVF/svfs.zip ready cell-scenarios: `0/300`. Base and overhead SVF are scenario-specific. The overhead scenario must not reuse base SVF.

## 5. Manifest status

`b87c_manifest.csv` rows: `3000`. Rows remain `not_ready` until required local rasters, wall rasters, and scenario-specific `svfs.zip` exist.

## 6. Runner/localizer status

Local runner inventory rows: `5`. Repo runners default to `RUN_ENABLED=False` and `DRY_RUN=True`; local copies are created under `C:/OpenHeat-local/solweig/b87c_n300/runners`.

## 7. QGIS full-stage execution

Run QGIS materialization first, then rebuild the manifest and localize the refreshed manifest copy. After manifest audit shows no `not_ready` rows, run SOLWEIG stages in order: `smoke`, `pilot_5`, `pilot_20`, `full_150`.

## 8. Resume/failure plan

Use `resume_key` and `expected_tmrt_path`. The runner skips existing readable Tmrt outputs and writes compact logs under `C:/OpenHeat-local/solweig/b87c_n300/run_logs`.

## 9. Postrun QA

Run `scripts/v12_b87c_postrun_qa.py --config configs/v12/systemb_b87b4_b87c_materialization_package.yaml` after QGIS execution, then refresh the compact review packet with `b87c_postrun_packet_script.ps1`.

## 10. Git hygiene

No raster, `svfs.zip`, data/solweig, data/rasters, data/archive, or hourly forecast CSV outputs should be staged from the repo. Heavy execution assets stay under `C:/OpenHeat-local`.

## 11. Claim boundaries

Local-only raster writes are allowed under `C:/OpenHeat-local` only. This lane creates no repo raster writes, no AOI/B9, no WBGT/risk/hazard/exposure/vulnerability output, no observed truth claim, and no causal feature-importance claim.
