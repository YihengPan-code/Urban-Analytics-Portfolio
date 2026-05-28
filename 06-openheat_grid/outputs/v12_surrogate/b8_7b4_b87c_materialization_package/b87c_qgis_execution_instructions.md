# B87C QGIS execution instructions

Status: package created, SOLWEIG not run by Codex.

1. Run `scripts/v12_b87c_runner_localizer.py --config configs/v12/systemb_b87b4_b87c_materialization_package.yaml` if the local runner copies need refreshing.
2. Open QGIS Desktop with UMEP installed.
3. In the QGIS Python Console, paste the snippet from `b87c_qgis_console_execution_snippet.py`.
4. First run the local materialization runner:
   `C:\OpenHeat-local\solweig\b87c_n300\runners\v12_b87b4_qgis_svf_materialization_runner_LOCAL.py`
5. Keep `DRY_RUN=True` for the first pass. Then set `RUN_ENABLED=True` and `DRY_RUN=False` inside the local copy.
6. After materialization, re-run `scripts/v12_b87c_manifest_builder.py` and then `scripts/v12_b87c_runner_localizer.py` so ready/not_ready statuses and the local manifest copy refresh.
7. Run `scripts/v12_b87c_manifest_audit.py` and confirm there are no `not_ready` rows.
8. Run the local SOLWEIG runner:
   `C:\OpenHeat-local\solweig\b87c_n300\runners\v12_b87c_qgis_solweig_n300_runner_LOCAL.py`
9. Use stages in order: `smoke`, `pilot_5`, `pilot_20`, then `full_150`.

Safety boundaries:

- Local-only raster/SVF writes under `C:/OpenHeat-local/solweig/b87c_n300` only.
- No repo raster writes.
- No AOI/B9/WBGT/risk/hazard/exposure/vulnerability outputs.
- `overhead_as_canopy` must use its own `svfs.zip`; do not reuse base SVF.
