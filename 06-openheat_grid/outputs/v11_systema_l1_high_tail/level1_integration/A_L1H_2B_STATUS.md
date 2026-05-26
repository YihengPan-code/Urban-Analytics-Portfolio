# A-L1H.2b Status

Status: PASS
Decision: ACCEPT_DIAGNOSTIC_COMPANION_HOLD_OPERATIONAL_CLAIMS
Generated: 2026-05-26
Branch: codex/systema-l1h2b-level1-integration

## Scope

System A Level 1 high-tail integration, model-card note, evidence ledger, and output contract. No model training, no recalibration, no formula-v2, no high-tail regression, no A-L2, no System B or SOLWEIG changes, and no archive collector changes.

## Command

- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts/v11_l1h_run_level1_integration_report.py --config configs/v11/systema_l1h_level1_integration.yaml`

## Files Created / Modified

- `outputs/v11_systema_l1_high_tail/level1_integration/systema_l1h_evidence_ledger.csv`
- `outputs/v11_systema_l1_high_tail/level1_integration/systema_l1h_output_contract.csv`
- `outputs/v11_systema_l1_high_tail/level1_integration/systema_l1h_claim_boundary_matrix.csv`
- `outputs/v11_systema_l1_high_tail/level1_integration/systema_l1h_decision_matrix.csv`
- `outputs/v11_systema_l1_high_tail/level1_integration/systema_l1h_station_regime_caveats.csv`
- `outputs/v11_systema_l1_high_tail/level1_integration/systema_l1h_next_gate_recommendations.csv`
- `outputs/v11_systema_l1_high_tail/level1_integration/systema_l1h_integration_report.md`
- `outputs/v11_systema_l1_high_tail/level1_integration/A_L1H_2B_STATUS.md`
- `docs/v11/OpenHeat_SystemA_Level1_high_tail_integration_CN.md`

## Key Results

- Current companion definition: P_ge31 = M4_inertia_ridge model_score calibrated with isotonic_score_only under station_grouped_loso; selected diagnostic threshold about 0.309.
- Reliability assessment: Reliable enough for internal retrospective diagnostic use as a companion to WBGT_A; not reliable enough for official warning probability or prospective forecast claims.
- High-tail assessment: ge31 capture is materially improved versus the fixed score 31 threshold, but high-tail compression and station/regime caveats remain; ge31 is not fully solved and ge33 remains exploratory.
- A-L2 decision: HOLD A-L2 until Level 1 high-tail evidence is closed and station-context residual work is explicitly opened.
- A-L1H.3 decision: OPTIONAL separate A-L1H.3 review gate only if further high-tail improvement is requested; not implemented in A-L1H.2b.

## Caveats

- P_ge31 is retrospective and diagnostic only.
- P_ge31 is not official warning probability and not prospective forecast skill.
- WBGT_A score remains primary but is not local 100m WBGT.
- ge33 remains exploratory.

## Source Report Check

- none

## Safe To Commit

- Config, scripts, docs, and compact level1_integration CSV/Markdown outputs after review.

## Not Safe To Commit

- Raw archives, rasters, SOLWEIG outputs, tif/tiff files, svfs.zip, patch zip packages, or large hourly forecast CSVs.
