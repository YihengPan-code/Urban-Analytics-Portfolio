# B8.7a N300 Design QA Patch Report

Status: `B87A_PATCHED_DESIGN_READY_FOR_REVIEW`

## 1. Why B8.7a follows B8.7

B8.7 ended as `B87_N300_DESIGN_NEEDS_QA`: the N300 design had 150 candidate
rows, zero overlap with current N150 labels, exact role quotas, and several
manual-review warnings. B8.7a reduces manual QA burden and prepares a patched
candidate-design table without creating execution artifacts.

## 2. B8.7 Warning Summary

- Spatial: west_south was below the B8.7a target minimum.
- Typology: residential/transport concentration remains a review item, and
  park_open_space remains sparse.
- Anchor replication: TP_0037 and TP_0433 remain review contexts unless patched.
- Neutral replication: diversity across preferred neutral groups remains a
  review context.
- Sparse/OOD: high nearest-N150 distance candidates remain review items.
- Connected shade corridor source remains unavailable for this lane.

## 3. Manual QA Workflow

Manual input found: `yes`. The template and
instructions support quick review of obvious exclusions, especially pure
river/water-only cells and pedestrian-relevance mismatches.

## 4. Auto QA Scoring

The auto scoring flags water/pure-river risk, outside-pedestrian relevance,
west_south, residential/transport concentration, park/commercial context,
anchor/neutral contexts, sparse/OOD risk, connected-shade source absence, and
feature coverage gaps.

## 5. Water / Pure River Review Queue

Queue count: `8`.

## 6. Candidate Replacements

Auto replacement candidates ranked: `681`. Replacements are
candidate-design rows only and are not run-ready.

## 7. v3 Design Status

v3 design row count: `150`.

## 8. After-Patch Audit

Role balance: PASS=6 WARN=0 FAIL=0

Spatial balance: PASS=4 WARN=0 FAIL=0

Typology balance: PASS=4 WARN=4 FAIL=0

Anchor replication: PASS=3 WARN=2 FAIL=0

Neutral replication: PASS=9 WARN=1 FAIL=0

Source-review blockers: manual_source_review_blockers=3; known_connected_shade_corridor_gap=carried_to_B86G3

## 9. Freeze Readiness

| decision_item | status | evidence |
| --- | --- | --- |
| manual_input | PASS | manual input found |
| candidate_count | PASS | rows=150 expected=150 |
| n150_overlap | PASS | overlap_count=0 |
| duplicate_cell_id | PASS | duplicate_count=0 |
| role_quota | PASS | PASS=6 WARN=0 FAIL=0 |
| manual_patch_blockers | PASS | blocked_replacements=0 |
| spatial_balance | PASS | PASS=4 WARN=0 FAIL=0 |
| typology_balance | WARN | PASS=4 WARN=4 FAIL=0 |
| anchor_replication | WARN | PASS=3 WARN=2 FAIL=0 |
| neutral_replication | WARN | PASS=9 WARN=1 FAIL=0 |
| feature_source_gap | WARN | connected shade corridor source remains future B86G3 item |
| final_freeze_readiness | B87A_PATCHED_DESIGN_READY_FOR_REVIEW | B8.7a remains design QA only; even freeze-ready does not allow SOLWEIG execution |

## 10. Next Lane Recommendation

If manual QA is absent, finish manual QA first. After manual QA and review
acceptance, the next lane can be B8.7b execution precheck only. B8.6g3
true-vector feature acquisition remains recommended for connected shade
corridor and pedestrian/covered-walkway source gaps.

## 11. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not risk / hazard score.
- Not exposure/vulnerability scoring.
- Not observed truth.
- Not causal feature importance.
- No raster.
- No QGIS / SOLWEIG.
- No N300 execution manifest.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
