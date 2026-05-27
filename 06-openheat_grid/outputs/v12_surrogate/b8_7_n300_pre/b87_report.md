# B8.7-N300-PRE Design Freeze And B8.6g3 Source Review

Status: `B87_N300_DESIGN_NEEDS_QA`

## 1. Why B8.7 follows B8.6g2

B8.6g2 improved compact diagnostic ranking but kept AOI preflight and B9
blocked. B8.7 therefore reviews the N300 v2 design and true-vector source
availability without creating execution artifacts.

## 2. B8.6g2 Evidence Summary

| split_family | b86g2_Spearman | b86g2_top10pct_overlap | b86g2_false_promotion_rate | b86f_context_status |
| --- | --- | --- | --- | --- |
| cell_group_holdout | 0.5266004415931803 | 0.5333333333333333 | 0.1410964559887191 | BLOCKED |
| forcing_day_holdout | 0.676002624163536 | 0.6 | 0.1087036968508307 | not_mapped |
| hour_holdout | 0.6650945697437939 | 0.6 | 0.114392256290521 | not_mapped |
| spatial_holdout | 0.5173736115998343 | 0.5 | 0.1627677928837865 | BLOCKED |
| typology_holdout | 0.4103509239448553 | 0.5619047619047619 | 0.2093342469913667 | DIAGNOSTIC_ONLY |

## 3. N300 Design Audit

- Candidate count: 150
- Overlap with current N150 labels: 0
- Input audit: PASS=4 WARN=0 FAIL=0

## 4. Balance Audits

- Role balance: PASS=6 WARN=0 FAIL=0
- Spatial balance: PASS=3 WARN=1 FAIL=0
- Typology balance: PASS=4 WARN=4 FAIL=0
- Anchor replication: PASS=3 WARN=2 FAIL=0
- Neutral replication: PASS=9 WARN=1 FAIL=0
- Sparse feature-space: PASS=1 WARN=2 FAIL=0
- Control cells: PASS=3 WARN=0 FAIL=0

## 5. Feature Coverage Audit

vector_derived=1 proxy_only=7 not_available=1 review=connected shade corridor / shade continuity

## 6. True-Vector Source Review

| source_category | source_status | source_candidate_count | can_support_B86G3_count | recommended_action |
| --- | --- | --- | --- | --- |
| connected_shade_corridor | NOT_AVAILABLE_REQUIRES_MANUAL_DATA | 40 | 0 | do not infer corridor continuity; acquire/QA pedestrian covered-walkway or shade-network source |
| pedestrian_network | PARTIAL_SOURCE_REQUIRES_QA | 36 | 3 | review geometry completeness and derive only source-backed compact features |
| overhead_geometry | AVAILABLE_FOR_B86G3_REVIEW | 57 | 53 | use in B8.6g3 source acquisition after schema/coverage QA |
| building_canyon | AVAILABLE_FOR_B86G3_REVIEW | 102 | 95 | use in B8.6g3 source acquisition after schema/coverage QA |
| tree_building_interaction | PARTIAL_SOURCE_REQUIRES_QA | 102 | 67 | review geometry completeness and derive only source-backed compact features |
| water_park_road_hardscape_edge | PARTIAL_SOURCE_REQUIRES_QA | 64 | 59 | review geometry completeness and derive only source-backed compact features |

## 7. Connected Shade Corridor Status

Connected shade corridor source status: `NOT_AVAILABLE_REQUIRES_MANUAL_DATA`. Do not infer corridor
continuity from centroid distance; future work needs pedestrian/covered-walkway
or shade-network geometry or equivalent vector-derived compact connectivity.

## 8. Manual QA Package

- Checklist: `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_checklist.csv`
- QA guide: `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_guide.md`
- High-priority QA rows: 114

## 9. Freeze Decision

| decision_item | status | evidence | recommended_action |
| --- | --- | --- | --- |
| n300_candidate_input | PASS | candidate_count=150 | none |
| n150_overlap | PASS | overlap_with_n150_count=0 | none |
| role_balance | PASS | PASS=6 WARN=0 FAIL=0 | review role deviations if any |
| spatial_balance | WARN | PASS=3 WARN=1 FAIL=0 | inspect weak-bin distribution, especially west_south |
| typology_balance | WARN | PASS=4 WARN=4 FAIL=0 | inspect residential/transport concentration and park/commercial coverage |
| anchor_replication | WARN | PASS=3 WARN=2 FAIL=0 | inspect TP_0037/TP_0433 preferred-minimum shortfalls if present |
| neutral_replication | WARN | PASS=9 WARN=1 FAIL=0 | inspect neutral-boundary diversity before execution precheck |
| sparse_feature_space | WARN | PASS=1 WARN=2 FAIL=0 | mark p90/p95 cases as execution-risk for manual QA |
| control_cell_coverage | PASS | PASS=3 WARN=0 FAIL=0 | confirm controls remain baseline-like |
| feature_coverage | PASS | vector_derived=1 proxy_only=7 not_available=1 review=connected shade corridor / shade continuity | carry source gaps into B8.6g3; do not promote proxy features |
| connected_shade_corridor_source | WARN | source_status=NOT_AVAILABLE_REQUIRES_MANUAL_DATA | do not infer continuity; require pedestrian/shade-network source QA |
| no_execution_artifacts_created | PASS | B8.7 package contains compact CSV/Markdown/docs/scripts only. | keep no SOLWEIG manifest, no QGIS runner, no AOI/B9 outputs |
| final_freeze_decision | B87_N300_DESIGN_NEEDS_QA | decision combines input, balance, feature, source, and no-execution checks | manual N300 QA, then B8.6g3 true-vector feature acquisition, then B8.7b precheck |

## 10. Future Lane Recommendation

Recommended next lane: manual N300 QA, then B8.6g3 true-vector feature acquisition, then B8.7b precheck.

## 11. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not risk / hazard score.
- Not observed truth.
- Not causal feature importance.
- No raster.
- No QGIS / SOLWEIG.
- No N300 execution manifest.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
