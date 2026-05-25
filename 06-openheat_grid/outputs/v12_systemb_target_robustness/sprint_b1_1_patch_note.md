# Sprint B1.1 Patch Note

## Files patched
- `outputs/v12_systemb_target_robustness/systemb_target_robustness_report.md`
- `outputs/v12_systemb_target_robustness/systemb_target_decision_matrix.csv`

## Original issue
The Sprint B1 report conclusion said "Downgrade p90 pending more samples," which was too strong for the evidence. Core 8 does not reject p90; it supports p90 as a provisional upper-tail System B target while leaving canonical target selection for a larger validation sample.

## Updated decision wording
`tmrt_p90_c` is retained as a provisional primary System B target candidate, not promoted to canonical target. It should proceed with required companion metrics and N=24 validation. `delta_tmrt_p90_c` and `m_rad_pct` remain companions derived from p90, and threshold-area metrics should be added in the next aggregation pass.

## Boundary confirmation
- no new computation
- no rasters touched
- no .tif touched
- no SOLWEIG rerun
- no QGIS
- no model training
- no risk map
- no local WBGT
- no System A/B coupling
- no commit/stage performed
