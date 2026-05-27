# B8.6f Status

Status: B86F_SURROGATE_CLOSURE_PASS
Branch: codex/b86f-surrogate-closure-megasuite
Scope: System B surrogate closure mega-suite using compact diagnostic/design inputs only.

## Key Results

- Inputs: see `b86f_input_inventory.csv`.
- B8.6e caveat headline: safe physical engineered features did not close spatial_holdout.
- Spatial failure headline: spatial_holdout remains blocking; west_north/west_south/east_south/east_north all require review.
- Anchor/neutral headline: anchor underprediction and neutral false-promotion remain explicit gates.
- N300 v2 role mix: typology_gap_fill=50, spatial_gap_fill=30, anchor_like_replication=25, neutral_boundary_replication=25, sparse_feature_space=10, control_cell=10
- Feature acquisition headline: vector/compact feature acquisition is recommended.
- AOI preflight status: AOI_PREFLIGHT_BLOCKED.
- B9 status: BLOCKED.
- Recommended next lane: B8.6g vector/compact feature acquisition; B8.7-N300-PRE targeted sample design freeze.

## Commands Run By Suite

- `python scripts/v12_b86f_run_surrogate_closure.py --config configs/v12/systemb_b86f_surrogate_closure.yaml`

## Files Created / Modified

- `configs/v12/systemb_b86f_surrogate_closure.yaml`
- `scripts/v12_b86f_input_inventory.py`
- `scripts/v12_b86f_failure_synthesis.py`
- `scripts/v12_b86f_n300_design_review.py`
- `scripts/v12_b86f_feature_acquisition_plan.py`
- `scripts/v12_b86f_abstention_gate.py`
- `scripts/v12_b86f_scope_limited_probe.py`
- `scripts/v12_b86f_workflow_decision.py`
- `scripts/v12_b86f_run_surrogate_closure.py`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_input_inventory.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_b86e_caveat_register.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_failure_synthesis.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_spatial_failure_decision_table.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_anchor_neutral_failure_matrix.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_safe_feature_probe_verdict.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_n300_design_v1_audit.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_n300_role_quota_plan.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_targeted_n300_design_v2.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_targeted_n300_design_review.md`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_feature_acquisition_register.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_feature_acquisition_spec.md`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_abstention_rule_catalog.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_abstention_gate_metrics.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_scope_limited_surrogate_metrics.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_aoi_preflight_readiness_matrix.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_next_lane_decision_matrix.csv`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_codex_prompt_B86G_feature_acquisition.md`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_codex_prompt_B87_N300_PRE.md`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_report.md`
- `outputs/v12_surrogate/b8_6f_surrogate_closure/B8_6F_STATUS.md`
- `docs/v12/OpenHeat_SystemB_B8_6f_surrogate_closure_CN.md`

## Caveats

- Labels are SOLWEIG-derived compact Tmrt deltas, not observed truth.
- Feature interpretation is diagnostic, not causal.
- Coordinate and distance context remains diagnostic-only.
- No AOI-wide prediction, B9 output, local WBGT, hazard_score, risk_score, raster, QGIS/SOLWEIG, Tmrt-to-WBGT conversion, or System A/B coupling output was created.

## Safe To Commit After Review

Compact B8.6f config, scripts, docs, CSV, and Markdown outputs.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide prediction outputs, B9 outputs, WBGT, hazard_score, risk_score, and System A/B coupling outputs.
