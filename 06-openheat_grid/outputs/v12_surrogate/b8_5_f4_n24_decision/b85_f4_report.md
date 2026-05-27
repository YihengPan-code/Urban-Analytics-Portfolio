# B8.5-F4 N24 Stability Decision Matrix Report

Generated: 2026-05-27 16:12:41

## 1. Why F4 follows F3c

F3c produced the controlled N24 / 480-run compact evidence package. F4 is the review gate that decides what that evidence supports before any N150 or B9 movement.

## 2. What F3c proved

- 24 cells x 2 forcing days x 5 hours x 2 scenarios = 480 controlled runs.
- Postrun validation is 480/480 PASS.
- F3c raster QA and alignment QA compact evidence are PASS.
- Core-hour delta_tmrt_p90_c rank stability is strong enough for target-card evidence.

## 3. What F3c did not prove

- It did not prove local WBGT prediction.
- It did not prove risk.
- It did not prove observed truth or causal effects of installed overhead infrastructure.
- It did not authorize B9, AOI-wide prediction, or System A/B coupling.

## 4. Hour-level stability interpretation

| hour_sgt | spearman_fd01_fd02 | sign_stability_fraction | top5_overlap | top10pct_overlap | top20pct_overlap | warn_count | high_severity_count | decision | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 0.657072 | 0.875000 | 0.400000 | 0.333333 | 0.400000 | 8 | 3 | STABLE_WITH_CAVEAT | h10 is usable only as caveated evidence: lower rank agreement, weaker top-k overlap, and low-sun-angle sensitivity. |
| 12 | 0.920276 | 1.000000 | 0.800000 | 1.000000 | 0.800000 | 4 | 0 | CORE_STABLE | Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap. |
| 13 | 0.967903 | 1.000000 | 0.800000 | 1.000000 | 0.800000 | 2 | 0 | CORE_STABLE | Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap. |
| 15 | 0.946160 | 1.000000 | 0.800000 | 1.000000 | 0.800000 | 3 | 0 | CORE_STABLE | Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap. |
| 16 | 0.992752 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | CORE_STABLE | Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap. |

## 5. h10 caveat

h10 is weaker and remains caveated; it is not anchor evidence.

## 6. Robust priority cells

| cell_id | evidence_hours | fd01_rank_summary | fd02_rank_summary | median_delta_core_fd01 | median_delta_core_fd02 | stability_notes | recommended_role | robust_priority_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0141 | h12:FD01+FD02; h13:FD01+FD02; h15:FD01+FD02; h16:FD01+FD02 | h12=2; h13=2; h15=3; h16=3 | h12=3; h13=2; h15=3; h16=3 | -0.909126 | -0.932670 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | surrogate_priority_anchor | 80 |
| TP_0857 | h12:FD01+FD02; h13:FD01+FD02; h15:FD01+FD02; h16:FD01+FD02 | h12=1; h13=1; h15=1; h16=1 | h12=1; h13=1; h15=1; h16=1 | -2.963661 | -2.838631 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | surrogate_priority_anchor | 80 |
| TP_0433 | h12:FD01+FD02; h13:FD01+FD02; h15:FD01+FD02; h16:FD01+FD02 | h12=3; h13=3; h15=2; h16=2 | h12=2; h13=3; h15=2; h16=2 | -0.899854 | -0.969952 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | surrogate_priority_anchor | 77 |
| TP_0542 | h12:FD01+FD02; h13:FD01+FD02; h15:FD01+FD02; h16:FD01+FD02 | h12=5; h13=4; h15=5; h16=4 | h12=4; h13=4; h15=4; h16=4 | -0.499394 | -0.561513 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | surrogate_priority_anchor | 50 |
| TP_0037 | h12:FD02; h13:FD02; h15:FD02; h16:FD01+FD02 | h12=10; h13=7; h15=6; h16=5 | h12=5; h13=5; h15=5; h16=5 | -0.411931 | -0.488179 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | visualization_anchor | 28 |

## 7. Neutral-boundary cells

Near-zero deltas and near-zero sign flips are treated as neutral-boundary behavior, not warming evidence.

| cell_id | neutral_boundary_count | neutral_core_count | sign_flip_count | sign_flip_near_zero_count | median_delta_core_fd01 | median_delta_core_fd02 | caveats |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0115 | 10 | 8 | 0 | 0 | 0.000000 | 0.000000 | Many near-zero deltas; classify as stable neutral comparator. |
| TP_0301 | 10 | 8 | 0 | 0 | 0.000000 | 0.000000 | Many near-zero deltas; classify as stable neutral comparator. |
| TP_0326 | 10 | 8 | 1 | 1 | 0.000000 | 0.000000 | Near-zero sign flip; classify as neutral-boundary rather than warming. |
| TP_0366 | 10 | 8 | 0 | 0 | -0.019471 | -0.024104 | Many near-zero deltas; classify as stable neutral comparator. |
| TP_0492 | 10 | 8 | 0 | 0 | 0.000000 | 0.000000 | Many near-zero deltas; classify as stable neutral comparator. |
| TP_0565 | 10 | 8 | 0 | 0 | -0.014348 | -0.017702 | Many near-zero deltas; classify as stable neutral comparator. |
| TP_0676 | 10 | 8 | 0 | 0 | -0.021103 | -0.015850 | Many near-zero deltas; classify as stable neutral comparator. |
| TP_0960 | 10 | 8 | 0 | 0 | -0.004490 | -0.009220 | Many near-zero deltas; classify as stable neutral comparator. |
| TP_0986 | 10 | 8 | 0 | 0 | 0.000000 | 0.000000 | Many near-zero deltas; classify as stable neutral comparator. |

## 8. Unstable cells

| cell_id | instability_type | stability_class | max_abs_rank_drift_core_hours | h10_rank_drift | sign_flip_count | sign_flip_near_zero_count | sign_flip_non_neutral_count | top_k_presence_count | median_delta_core_fd01 | median_delta_core_fd02 | review_notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0059 | h10-only instability | unstable_review | 2 | 6 | 0 | 0 | 0 | 0 | -0.208569 | -0.246855 | Instability is present; distinguish h10-only caveat from core-hour disagreement before use. |
| TP_0098 | h10-only instability | unstable_review | 3 | 14 | 1 | 0 | 1 | 0 | -0.281234 | -0.322368 | Instability is present; distinguish h10-only caveat from core-hour disagreement before use. |
| TP_0773 | h10-only instability | unstable_review | 2 | 4 | 0 | 0 | 0 | 0 | -0.345855 | -0.438980 | Instability is present; distinguish h10-only caveat from core-hour disagreement before use. |
| TP_0326 | neutral-boundary sign flip | neutral_boundary | 0 | 2 | 1 | 1 | 0 | 0 | 0.000000 | 0.000000 | Sign flip is inside the neutral delta band and should not be interpreted as warming evidence. |
| TP_0154 | true instability candidate | high_priority_unstable | 7 | 2 | 0 | 0 | 0 | 0 | -0.352878 | -0.275128 | Meaningful cooling evidence coexists with core-hour rank instability; review before anchoring. |
| TP_0409 | true instability candidate | high_priority_unstable | 8 | 16 | 1 | 0 | 1 | 3 | -0.432002 | -0.238160 | Meaningful cooling evidence coexists with core-hour rank instability; review before anchoring. |
| TP_0575 | true instability candidate | high_priority_unstable | 6 | 3 | 0 | 0 | 0 | 0 | -0.327592 | -0.465652 | Meaningful cooling evidence coexists with core-hour rank instability; review before anchoring. |

## 9. Target-card decision

`delta_tmrt_p90_c` is ready as the primary target-card variable for SOLWEIG-derived radiative modifier / cooling sensitivity evidence.

## 10. N150 recommendation

`ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK`. B9 remains blocked.

## 11. Surrogate role decision

`SURROGATE_PROTOCOL_READY_N24_STRESS_VALIDATION_NO_TRAINING_IN_F4`. No surrogate is trained in F4.

## 12. Claim boundaries

- Not B9.
- Not local WBGT.
- Not risk.
- Not N150 execution.
- No raster committed.
- No Tmrt-to-WBGT conversion.

## Evidence validation notes

- F3c status is N24_STABILITY_REVIEW_READY.
- Postrun validation is 480/480 PASS.
- Cell-hour and pairwise compact summaries have the expected N24/F3c shape.
- F3c raster/alignment QA compact evidence is PASS; F4 did not open rasters.

## Blockers

- none

## Decision status

`F4_N24_DECISION_PASS`
