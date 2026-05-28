# B8.7b.3p Status

Status: `B87B3P_PASS_WITH_NONFINAL_SMOKE_DIFFERENCES`

## Key results

- Batches discovered: `9`
- Final ML label source batch: `b85_f5_n150_multiforcing`
- N150 protocol id: `F5_N150_QA_DSM_V08_CDSM_PER_TILE_SCENARIO_SVF_FLATDEM_NOLC_FD01_FD02_H10_12_13_15_16`
- Planned N300 protocol id: `B87C_PLANNED_QA_DSM_V08_CDSM_V07_GRID_SCENARIO_SVF_FLATDEM_NOLC_FD01_FD02_H10_12_13_15_16`
- DSM: DSM PASS: final F5 and planned B87C use reviewed_heightqa / qa_corrected_final lineage.
- CDSM: CDSM PASS: final F5 and planned B87C use v08 dsm_vegetation_2m_toapayoh lineage.
- SVF/base-overhead: SVF PASS_WITH_ASSERTION: final F5 uses separate base/overhead per-tile SVF; planned B87C must materialize scenario-specific overhead SVF and not reuse base SVF.
- DEM/landcover: DEM/landcover PASS: flat DEM convention and INPUT_LC=None / USE_LC_BUILD=false are consistent.
- Forcing/tile/SOLWEIG: Forcing/tile/SOLWEIG PASS: FD01+FD02, hours 10/12/13/15/16, base+overhead_as_canopy, 100m+100m buffer at 2m, and SOLWEIG core parameters are compatible.
- Nonfinal smoke differences: 5 nonfinal smoke/deprecated caveat rows; treated as WARN_NONFINAL_PROTOCOL_DIFFERENCE, not final ML mixing.
- Blockers: `none`
- Recommended next lane: B8.7b.4 materialization package may proceed with protocol_id and parity assertions.

## Files created / modified

- `configs/v12/systemb_b87b3p_solweig_protocol_parity.yaml`
- `scripts/v12_b87b3p_input_inventory.py`
- `scripts/v12_b87b3p_batch_discovery.py`
- `scripts/v12_b87b3p_protocol_extractor.py`
- `scripts/v12_b87b3p_source_lineage_audit.py`
- `scripts/v12_b87b3p_svf_overhead_parity.py`
- `scripts/v12_b87b3p_ml_label_trace.py`
- `scripts/v12_b87b3p_parity_decision.py`
- `scripts/v12_b87b3p_run_protocol_parity.py`
- `docs/v12/OpenHeat_SystemB_B8_7b3p_SOLWEIG_protocol_parity_CN.md`
- `outputs/v12_surrogate/b8_7b3p_solweig_protocol_parity/*`

## Claim boundaries

PASS: no QGIS/SOLWEIG; no raster copy/write/move; no raster pixel read; no svfs.zip open; no run-ready manifest/runner; no AOI/B9/WBGT/risk/coupling.
