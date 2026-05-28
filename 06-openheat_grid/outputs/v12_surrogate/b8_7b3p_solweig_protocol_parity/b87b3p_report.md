# B8.7b.3p SOLWEIG Protocol Parity Audit

Status: `B87B3P_PASS_WITH_NONFINAL_SMOKE_DIFFERENCES`

## 1. Why parity is required before N300 execution

N300 would extend the System B label family. It must not mix early smoke, N24, N150, and planned N300 outputs from incompatible DSM/CDSM/SVF/DEM/landcover/forcing/SOLWEIG protocols.

## 2. Batch lineage summary

Discovered batches: `9`. Early v10/Core8/F3a/F3b evidence is nonfinal or deprecated. F3c/F4 are formal N24 validation evidence. F5 N150 is the current final ML label source. B87C is planned only.

## 3. Final ML label source trace

Final source batch: `b85_f5_n150_multiforcing`. N150 protocol id: `F5_N150_QA_DSM_V08_CDSM_PER_TILE_SCENARIO_SVF_FLATDEM_NOLC_FD01_FD02_H10_12_13_15_16`. The label file has one F5 label source and legacy single-forcing evidence is metadata-only, not merged.

## 4. B87C planned protocol summary

Planned N300 protocol id: `B87C_PLANNED_QA_DSM_V08_CDSM_V07_GRID_SCENARIO_SVF_FLATDEM_NOLC_FD01_FD02_H10_12_13_15_16`. It uses the B8.7b.3 source lock: reviewed-height QA DSM, v08 vegetation CDSM, v07 grid geometry lock, base full-AOI SVF source for base materialization, scenario-specific overhead SVF, v10 overhead layer, flat DEM, no landcover.

## 5. Source/path parity matrix

DSM PASS: final F5 and planned B87C use reviewed_heightqa / qa_corrected_final lineage.

CDSM PASS: final F5 and planned B87C use v08 dsm_vegetation_2m_toapayoh lineage.

Grid path has a derived-feature caveat: final F5 evidence references v10 feature/sample artifacts while B87C locks v07 geometry. B8.7b.4 must assert geometry lineage before materialization.

## 6. SVF overhead parity

SVF PASS_WITH_ASSERTION: final F5 uses separate base/overhead per-tile SVF; planned B87C must materialize scenario-specific overhead SVF and not reuse base SVF.

## 7. DEM/landcover parity

DEM/landcover PASS: flat DEM convention and INPUT_LC=None / USE_LC_BUILD=false are consistent.

## 8. Tile/SOLWEIG parameter parity

Forcing/tile/SOLWEIG PASS: FD01+FD02, hours 10/12/13/15/16, base+overhead_as_canopy, 100m+100m buffer at 2m, and SOLWEIG core parameters are compatible.

## 9. Nonfinal smoke differences

5 nonfinal smoke/deprecated caveat rows; treated as WARN_NONFINAL_PROTOCOL_DIFFERENCE, not final ML mixing.

## 10. Blockers / decision

Blockers: `none`.

Decision: `B87B3P_PASS_WITH_NONFINAL_SMOKE_DIFFERENCES`.

## 11. Required B8.7b.4 parity assertions

Set protocol_id, assert locked DSM/CDSM/grid lineage, assert flat DEM/no landcover, assert scenario-specific SVF separation, assert overhead CDSM max rule, assert forcing/hour/scenario sets, and assert pairwise delta direction.

## 12. Claim boundaries

No QGIS/SOLWEIG was run. No raster was copied, moved, written, or read for pixels. No svfs.zip was opened. No run-ready manifest or runner was created. No AOI, B9, WBGT, risk, hazard, exposure, vulnerability, or System A/B coupling output was created.

## Files

See `b87b3p_*` CSV/Markdown artifacts under `outputs/v12_surrogate/b8_7b3p_solweig_protocol_parity/`.
