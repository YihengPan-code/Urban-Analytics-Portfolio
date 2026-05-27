# OpenHeat System B B8.5-F4 N24 稳定性决策矩阵中文说明

生成时间：2026-05-27 16:12:41

## 结论

- F4 决策状态：`F4_N24_DECISION_PASS`
- 核心小时结论：h12/h13/h15/h16 are core-stable across FD01/FD02 for delta_tmrt_p90_c ranking.
- h10 结论：h10 is weaker and remains caveated; it is not anchor evidence.
- N150 建议：`ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK`
- B9 状态：`BLOCKED_F4_IS_NOT_B9`

## 为什么 F4 接在 F3c 之后

F3c 已完成 N24 / 480-run 的受控执行证据包。F4 不再运行 QGIS/SOLWEIG，也不读取任何 raster；它只消费 F3c 的紧凑 CSV/Markdown 证据，用来判断 `delta_tmrt_p90_c` 是否可作为目标卡和后续 surrogate 协议的依据。

## F3c 已证明的内容

- 24 个 cells、2 个 forcing days、5 个 SGT hours、2 个 scenarios，共 480 个运行结果通过 postrun validation。
- F3c 的 raster QA、alignment QA 和 stability summary 为 PASS。
- h12/h13/h15/h16 的核心小时排序稳定性支持 N24 层面的目标卡判断。

## F3c 没有证明的内容

- 没有证明 local WBGT。
- 没有证明 risk。
- 没有证明 `Tmrt` 等于 WBGT。
- 没有证明实际安装 overhead infrastructure 的因果效应。
- 没有授权 B9、AOI-wide prediction、hazard_score、risk_score 或 System A/B coupling。

## 小时层级稳定性解释

| hour_sgt | spearman_fd01_fd02 | sign_stability_fraction | top5_overlap | top10pct_overlap | top20pct_overlap | warn_count | high_severity_count | decision | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 0.657072 | 0.875000 | 0.400000 | 0.333333 | 0.400000 | 8 | 3 | STABLE_WITH_CAVEAT | h10 is usable only as caveated evidence: lower rank agreement, weaker top-k overlap, and low-sun-angle sensitivity. |
| 12 | 0.920276 | 1.000000 | 0.800000 | 1.000000 | 0.800000 | 4 | 0 | CORE_STABLE | Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap. |
| 13 | 0.967903 | 1.000000 | 0.800000 | 1.000000 | 0.800000 | 2 | 0 | CORE_STABLE | Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap. |
| 15 | 0.946160 | 1.000000 | 0.800000 | 1.000000 | 0.800000 | 3 | 0 | CORE_STABLE | Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap. |
| 16 | 0.992752 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | CORE_STABLE | Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap. |

## h10 caveat

h10 的 Spearman、top-k overlap 和 sign stability 弱于核心小时。F4 将 h10 作为低太阳高度角 caveat，不把 h10 用作 priority anchor。

## Robust priority cells

| cell_id | evidence_hours | fd01_rank_summary | fd02_rank_summary | median_delta_core_fd01 | median_delta_core_fd02 | stability_notes | recommended_role | robust_priority_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0141 | h12:FD01+FD02; h13:FD01+FD02; h15:FD01+FD02; h16:FD01+FD02 | h12=2; h13=2; h15=3; h16=3 | h12=3; h13=2; h15=3; h16=3 | -0.909126 | -0.932670 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | surrogate_priority_anchor | 80 |
| TP_0857 | h12:FD01+FD02; h13:FD01+FD02; h15:FD01+FD02; h16:FD01+FD02 | h12=1; h13=1; h15=1; h16=1 | h12=1; h13=1; h15=1; h16=1 | -2.963661 | -2.838631 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | surrogate_priority_anchor | 80 |
| TP_0433 | h12:FD01+FD02; h13:FD01+FD02; h15:FD01+FD02; h16:FD01+FD02 | h12=3; h13=3; h15=2; h16=2 | h12=2; h13=3; h15=2; h16=2 | -0.899854 | -0.969952 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | surrogate_priority_anchor | 77 |
| TP_0542 | h12:FD01+FD02; h13:FD01+FD02; h15:FD01+FD02; h16:FD01+FD02 | h12=5; h13=4; h15=5; h16=4 | h12=4; h13=4; h15=4; h16=4 | -0.499394 | -0.561513 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | surrogate_priority_anchor | 50 |
| TP_0037 | h12:FD02; h13:FD02; h15:FD02; h16:FD01+FD02 | h12=10; h13=7; h15=6; h16=5 | h12=5; h13=5; h15=5; h16=5 | -0.411931 | -0.488179 | Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence. | visualization_anchor | 28 |

## Neutral-boundary cells

接近 0 的 delta 和接近 0 的 sign flip 被解释为 neutral-boundary，不解释为真实 warming。

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

## Unstable cells

| cell_id | instability_type | stability_class | max_abs_rank_drift_core_hours | h10_rank_drift | sign_flip_count | sign_flip_near_zero_count | sign_flip_non_neutral_count | top_k_presence_count | median_delta_core_fd01 | median_delta_core_fd02 | review_notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0059 | h10-only instability | unstable_review | 2 | 6 | 0 | 0 | 0 | 0 | -0.208569 | -0.246855 | Instability is present; distinguish h10-only caveat from core-hour disagreement before use. |
| TP_0098 | h10-only instability | unstable_review | 3 | 14 | 1 | 0 | 1 | 0 | -0.281234 | -0.322368 | Instability is present; distinguish h10-only caveat from core-hour disagreement before use. |
| TP_0773 | h10-only instability | unstable_review | 2 | 4 | 0 | 0 | 0 | 0 | -0.345855 | -0.438980 | Instability is present; distinguish h10-only caveat from core-hour disagreement before use. |
| TP_0326 | neutral-boundary sign flip | neutral_boundary | 0 | 2 | 1 | 1 | 0 | 0 | 0.000000 | 0.000000 | Sign flip is inside the neutral delta band and should not be interpreted as warming evidence. |
| TP_0154 | true instability candidate | high_priority_unstable | 7 | 2 | 0 | 0 | 0 | 0 | -0.352878 | -0.275128 | Meaningful cooling evidence coexists with core-hour rank instability; review before anchoring. |
| TP_0409 | true instability candidate | high_priority_unstable | 8 | 16 | 1 | 0 | 1 | 3 | -0.432002 | -0.238160 | Meaningful cooling evidence coexists with core-hour rank instability; review before anchoring. |
| TP_0575 | true instability candidate | high_priority_unstable | 6 | 3 | 0 | 0 | 0 | 0 | -0.327592 | -0.465652 | Meaningful cooling evidence coexists with core-hour rank instability; review before anchoring. |

## Target-card decision

`delta_tmrt_p90_c = overhead_as_canopy - base` 可作为 SOLWEIG-derived radiative modifier / cooling sensitivity evidence 的 primary target。它不是 WBGT，不是 risk，不是 observed truth，也不是实际安装设施的因果效应。

## N150 recommendation

`ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK`。这只表示后续 readiness / controlled execution gate 的建议；F4 没有创建 N150 manifest 或 runner，也没有执行 N150。

## Surrogate role decision

`SURROGATE_PROTOCOL_READY_N24_STRESS_VALIDATION_NO_TRAINING_IN_F4`。System B 可以把 N24 用作 multi-forcing stress-validation set，并推进 target-card / protocol suite；F4 不训练 surrogate。

## Claim boundaries

- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 N150 execution。
- 没有提交 raster。
- 没有 Tmrt-to-WBGT conversion。
