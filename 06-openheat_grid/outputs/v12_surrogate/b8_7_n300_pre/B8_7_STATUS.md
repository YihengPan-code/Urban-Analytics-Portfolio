# B8.7 Status

Status: B87_N300_DESIGN_NEEDS_QA
Branch: codex/b87-n300-pre-source-review
Scope: B8.7-N300-PRE design freeze/source review only; no execution artifacts.

## Commands Run By Suite

- `python scripts/v12_b87_run_n300_pre.py --config configs/v12/systemb_b87_n300_pre.yaml`

## Key Results

- N300 candidate count: 150
- Overlap with current N150 labels: 0
- Role balance: PASS=6 WARN=0 FAIL=0
- Spatial balance: PASS=3 WARN=1 FAIL=0
- Typology balance: PASS=4 WARN=4 FAIL=0
- Anchor replication: PASS=3 WARN=2 FAIL=0
- Neutral replication: PASS=9 WARN=1 FAIL=0
- Feature coverage: vector_derived=1 proxy_only=7 not_available=1 review=connected shade corridor / shade continuity
- Connected shade corridor source status: NOT_AVAILABLE_REQUIRES_MANUAL_DATA
- AOI/B9 status: AOI_PREFLIGHT_BLOCKED / B9_BLOCKED
- Recommended next lane: manual N300 QA, then B8.6g3 true-vector feature acquisition, then B8.7b precheck

## Files Created / Modified

- `configs/v12/systemb_b87_n300_pre.yaml`
- `scripts/v12_b87_input_inventory.py`
- `scripts/v12_b87_n300_design_audit.py`
- `scripts/v12_b87_feature_schema_audit.py`
- `scripts/v12_b87_source_availability_review.py`
- `scripts/v12_b87_candidate_qa_package.py`
- `scripts/v12_b87_precheck_decision.py`
- `scripts/v12_b87_run_n300_pre.py`
- `docs/v12/OpenHeat_SystemB_B8_7_N300_PRE_CN.md`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_input_inventory.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_v2_input_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_design_freeze_candidates.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_exclusion_register.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_role_balance_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_spatial_balance_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_typology_balance_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_anchor_replication_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_neutral_replication_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_sparse_feature_space_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_control_cell_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_feature_coverage_audit.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_true_vector_source_inventory.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_true_vector_source_gap_register.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_connected_shade_corridor_source_review.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_pedestrian_network_source_review.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_overhead_geometry_source_review.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_building_canyon_source_review.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_tree_building_interaction_source_review.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_checklist.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_guide.md`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_freeze_decision_matrix.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_aoi_b9_boundary_matrix.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_next_lane_decision_matrix.csv`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_codex_prompt_B87B_N300_execution_precheck.md`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_codex_prompt_B86G3_true_vector_feature_acquisition.md`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_codex_prompt_B86H_scope_limited_dry_run.md`
- `outputs/v12_surrogate/b8_7_n300_pre/b87_report.md`
- `outputs/v12_surrogate/b8_7_n300_pre/B8_7_STATUS.md`

## Caveats

This lane is design/source review only. It does not create a SOLWEIG manifest,
QGIS runner, raster, AOI-wide prediction, B9 output, local WBGT, hazard_score,
risk_score, exposure/vulnerability score, observed-truth claim, causal
feature-importance claim, Tmrt-to-WBGT conversion, or System A/B coupling.

## Safe To Commit After Review

Controlled B8.7 config, scripts, docs, compact CSV, and Markdown outputs.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip
packages, AOI-wide prediction outputs, B9 outputs, WBGT, hazard_score,
risk_score, exposure/vulnerability score, and System A/B coupling outputs.
