# Codex prompt: B8.7b.4 materialization with protocol parity

Lane status from B8.7b.3p: `B87B3P_PASS_WITH_NONFINAL_SMOKE_DIFFERENCES`.

Proceed only if the user explicitly authorizes B8.7b.4. Implement protocol parity assertions before any run-ready B87C manifest or runner:

- `protocol_id` must equal `B87C_PLANNED_QA_DSM_V08_CDSM_V07_GRID_SCENARIO_SVF_FLATDEM_NOLC_FD01_FD02_H10_12_13_15_16` or an explicitly versioned successor.
- Assert building DSM = `dsm_buildings_2m_augmented_reviewed_heightqa.tif`, status `qa_corrected_final`.
- Assert base vegetation CDSM = `dsm_vegetation_2m_toapayoh.tif`.
- Assert overhead CDSM is `max(existing vegetation DSM, overhead canopy)`.
- Assert base and `overhead_as_canopy` SVF artifacts are separate; overhead must not reuse base SVF.
- Assert flat DEM convention and landcover disabled (`INPUT_LC=None`, `USE_LC_BUILD=false`).
- Assert forcing days FD01/FD02, hours 10/12/13/15/16, scenarios base and overhead_as_canopy.
- Assert label convention remains SOLWEIG Tmrt only and pairwise delta is `overhead_as_canopy - base`.
- State early v10/Core8/F3a/F3b smoke batches are nonfinal and are not mixed into current ML labels.

Do not create AOI/B9/WBGT/risk outputs. Do not stage or commit rasters, `svfs.zip`, raw SOLWEIG outputs, or local run logs.
