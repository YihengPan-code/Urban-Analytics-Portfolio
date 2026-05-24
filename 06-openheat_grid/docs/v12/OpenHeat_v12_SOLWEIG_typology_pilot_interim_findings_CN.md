# OpenHeat v1.2-beta SOLWEIG typology pilot interim findings

**Document date:** 2026-05-24  
**Project:** OpenHeat-ToaPayoh  
**Stage:** v1.2-beta SOLWEIG typology pilot interim review  
**Status:** interim findings note for review  

本文只整理既有 v1.2-beta typology pilot 输出，没有重新运行 SOLWEIG，没有创建 raster，没有训练 surrogate / ML，没有生成 hazard map 或 risk map，也没有修改任何 v1.1 输出。

Forcing scope note: 本 pilot 使用 v10-epsilon forcing：

```text
data/solweig/v09_met_forcing_2026_05_07_S128_h{10,12,13,15,16}.txt
```

这还不是 formal-hot-day forcing；因此当前结果只适合解释为 v10-epsilon forcing 条件下的 typology sanity / modifier evidence。

## 0. 结论摘要

Wave 0、Wave 1、Core 8 base、Core 8 `overhead_as_canopy` 均已通过技术检查。Core 8 base 给出了稳定且物理上可解释的 typology ranking；Core 8 overhead sensitivity 进一步支持 `tmrt_p90_c` 作为 100m mixed-cell 上尾辐射 modifier target。

这些结果应被解释为：

```text
SOLWEIG-derived Tmrt modifier evidence
100m mixed-cell upper-tail radiative modifier evidence
```

不得解释为：

```text
local WBGT
observed truth
validated local WBGT prediction
risk
risk map
real-time public health warning
```

## 1. 使用的既有输出

主要依据：

```text
outputs/v12_solweig_typology_pilot/wave0_summary/v12_solweig_typology_aggregation_report.md
outputs/v12_solweig_typology_pilot/wave1_base_summary/v12_solweig_typology_aggregation_report.md
outputs/v12_solweig_typology_pilot/core8_base_summary/v12_solweig_typology_aggregation_report.md
outputs/v12_solweig_typology_pilot/core8_overhead_summary/v12_solweig_typology_aggregation_report.md
outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta_report.md
outputs/v12_solweig_typology_pilot/core8_overhead_summary/tp0542_h15_distribution/tp0542_h15_distribution_diagnostic.md
data/grid/v12/solweig_typology_pilot_cells_revised_v2.csv
docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_runbook_CN.md
docs/v12/SOLWEIG_typology_pilot_runbook_CN_updated.md
```

## 2. Run Matrix 技术通过摘要

| stage | cells / hours / scenario | rows | raster exists | focus cell exists | qa_status | technical pass |
|---|---:|---:|---:|---:|---|---|
| Wave 0 | TP0986 h13 base smoke | 1 | 1 / 1 | 1 / 1 | ok | PASS |
| Wave 1 base | TP0986 / TP0542 / TP0059, h10 / h13 / h16 | 9 | 9 / 9 | 9 / 9 | all ok | PASS |
| Core 8 base | 8 cells x 5 hours x base | 40 | 40 / 40 | 40 / 40 | all ok | PASS |
| Core 8 overhead_as_canopy | 8 cells x 5 hours x overhead_as_canopy | 40 | 40 / 40 | 40 / 40 | all ok | PASS |

补充说明：中间的 h13 overhead smoke 也已通过，3 / 3 outputs、3 / 3 focus cells、qa_status 全部为 `ok`。后续解释以完整 Core 8 overhead matrix 为准。

## 3. Core 8 Base：稳定且物理可解释

Core 8 base 的平均 `tmrt_p90_c` ranking 如下。该排序在 5 个小时上整体稳定，符合 pilot 目标：高暴露低层住宅、school-gate / asphalt road-edge、硬质铺装、街谷 / 墙边、mixed high-rise estate、shaded walkway、wooded green-space diagnostic 分层清晰。

这里的 `m_rad_pct` 是 Core 8 / v10-epsilon forcing / 当前 scenario 内的 batch-relative ranking，不是 full-domain modifier，也不能直接外推为全域辐射修正因子。

| cell_id | current interpretation | mean tmrt_p90_c | p90 range | mean m_rad_pct | qa_status |
|---|---|---:|---:|---:|---|
| TP_0986 | high-exposure low-rise residential null-control | 56.666 | 46.359 - 62.464 | 1.000 | ok |
| TP_0565 | school-gate / asphalt road-edge hot anchor | 56.562 | 46.272 - 62.353 | 0.875 | ok |
| TP_0059 | parking-lot hardscape diagnostic | 56.246 | 45.901 - 62.027 | 0.750 | ok |
| TP_0627 | street-canyon / wall-adjacent low-SVF corridor | 56.023 | 45.631 - 61.868 | 0.625 | ok |
| TP_0366 | school-gate / bus-stop mixed waiting node | 55.777 | 45.438 - 61.700 | 0.500 | ok |
| TP_0326 | stable high-rise residential estate | 54.511 | 43.964 - 61.313 | 0.375 | ok |
| TP_0542 | river-edge shaded pedestrian walkway | 48.228 | 35.836 - 57.675 | 0.250 | ok |
| TP_0835 | wooded green-space low-radiative diagnostic | 34.737 | 32.775 - 35.600 | 0.125 | ok |

Representative h13 base metrics:

| cell_id | tmrt_mean_c | tmrt_p90_c | tmrt_max_c | delta_tmrt_p90_c | m_rad_pct |
|---|---:|---:|---:|---:|---:|
| TP_0986 | 60.673 | 62.464 | 62.528 | 0.739 | 1.000 |
| TP_0565 | 60.055 | 62.353 | 62.466 | 0.628 | 0.875 |
| TP_0059 | 61.813 | 62.027 | 62.190 | 0.301 | 0.750 |
| TP_0627 | 59.235 | 61.818 | 62.208 | 0.092 | 0.625 |
| TP_0366 | 60.561 | 61.633 | 62.005 | -0.092 | 0.500 |
| TP_0326 | 49.468 | 60.513 | 62.624 | -1.212 | 0.375 |
| TP_0542 | 39.116 | 55.485 | 62.578 | -6.240 | 0.250 |
| TP_0835 | 35.594 | 35.600 | 35.635 | -26.126 | 0.125 |

Interpretation:

- `TP_0986` 和 `TP_0565` 稳定处于上端，符合 high-exposure residential null-control 与 asphalt road-edge hot anchor 的角色。
- `TP_0059` 是 hardscape / parking-lot 诊断样本，base p90 高但不需要强行解释为 pedestrian hotspot。
- `TP_0542` mean 低但 p90 在部分小时仍捕捉 exposed pocket，说明 mixed-cell 内部存在低辐射背景与高辐射局部暴露并存。
- `TP_0835` mean、p90、max 几乎重合且整体极低，应解释为 wooded green-space / low-radiative diagnostic，而不是 open grass。

## 4. Core 8 Overhead Sensitivity

Base vs `overhead_as_canopy` 的 by-cell delta summary：

| cell_id | mean delta mean | mean delta p90 | min delta p90 | max delta p90 | max abs delta p90 | interpretation |
|---|---:|---:|---:|---:|---:|---|
| TP_0542 | -0.320 | -2.417 | -11.581 | 0.244 | 11.581 | mapped pedestrian-overhead / shaded river-walkway sensitivity |
| TP_0059 | -2.460 | -0.183 | -0.218 | -0.122 | 0.218 | mean strongly lowered, upper tail largely retained |
| TP_0366 | -0.324 | -0.054 | -0.076 | -0.037 | 0.076 | small, explainable sensitivity |
| TP_0627 | -0.000 | -0.000 | -0.002 | 0.000 | 0.002 | near-null |
| TP_0326 | -0.216 | 0.000 | 0.000 | 0.000 | 0.000 | p90 null despite small mean change |
| TP_0565 | -0.010 | 0.000 | 0.000 | 0.000 | 0.000 | p90 null hot anchor |
| TP_0835 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | wooded low-radiative null |
| TP_0986 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | high-exposure residential null-control |

Key cell interpretations:

- `TP_0986` 是 high-exposure low-rise residential null-control。Full Core 8 overhead 中 p90 delta 为 0 across hours，符合 no mapped overhead should produce near-null sensitivity 的预期。
- `TP_0565` 是 school-gate / asphalt road-edge hot anchor。Overhead p90 delta 为 0 across hours，说明其上尾暴露主要不是由 mapped overhead sensitivity 控制；这个结果支持把它保留为 hot-anchor reference，而不是 overhead response case。
- `TP_0059` 是 parking-lot hardscape diagnostic。Overhead 使 mean 大幅下降，mean delta 约 -1.357 至 -3.220 C；但 p90 只轻微下降，p90 delta 约 -0.122 至 -0.218 C。这正是 `tmrt_p90_c` 作为 upper-tail target 的价值：mean 可以被大量较冷像元拉动，但 p90 仍保留 cell 内高暴露上尾。
- `TP_0542` 是 mapped pedestrian-overhead / shaded river-walkway case。h15 p90 明显下降，是本轮最重要的 mixed-cell upper-tail 证据。

## 5. TP0542 h15 Distribution Diagnostic

TP0542 h15 的 quantile diagnostic 显示，overhead scenario 对 p90 的影响很强，但对 p95 / p99 / max 几乎不改变：

| quantile | base_tmrt_c | overhead_tmrt_c | overhead - base |
|---:|---:|---:|---:|
| 75 | 36.381 | 35.974 | -0.407 |
| 80 | 37.020 | 36.359 | -0.661 |
| 85 | 37.859 | 37.070 | -0.789 |
| 90 | 50.729 | 39.148 | -11.581 |
| 95 | 56.381 | 56.228 | -0.152 |
| 99 | 60.755 | 60.755 | -0.000 |
| 100 | 60.761 | 60.761 | 0.000 |

Area-above-threshold diagnostic:

| threshold_c | base pct >= threshold | overhead pct >= threshold | delta percentage point |
|---:|---:|---:|---:|
| 40 | 11.40 | 9.08 | -2.32 |
| 45 | 10.12 | 7.84 | -2.28 |
| 50 | 10.12 | 7.84 | -2.28 |
| 55 | 6.76 | 6.48 | -0.28 |
| 60 | 4.24 | 4.24 | 0.00 |

Interpretation:

TP0542 h15 不是简单的 "max 变冷" 案例。它更像是 mapped overhead / shade geometry 把一部分 top-decile pixels 从高 Tmrt band 推入 lower / intermediate Tmrt band；但少量最热像元仍然存在，所以 p95、p99、max 基本不变。

Percentile discontinuity 很清楚：base p85 仍约 37 C，但 base p90 跳到 50.7 C；overhead 把 p90 拉回 39.1 C，而 p95 / p99 / max 几乎不变。

这正好说明：

```text
tmrt_mean_c 可能过度受低辐射背景像元影响
tmrt_max_c 可能过度受少量极端像元影响
tmrt_p90_c 能更稳定地代表 100m mixed-cell 的上尾辐射暴露
```

因此，本轮结果支持把 `tmrt_p90_c` 作为 100m mixed-cell upper-tail radiative modifier target，并继续使用 `delta_tmrt_p90_c` / `m_rad_pct` 作为相对 radiative modifier 表达。

## 6. Typology Label Updates / Caveats

`TP_0835` 必须解释为 wooded green-space / low-radiative diagnostic，而不是 open grass。手工 QA 表明该 cell 已从 open field / grass 语义转为植被覆盖树林；SOLWEIG 输出的极低且近乎均质的 Tmrt 分布也支持这一解释。

`TP_0986` 是 high-exposure low-rise residential null-control，不是人群暴露或风险节点。它的价值是几何稳定、低植被、高暴露、无 mapped overhead；overhead p90 delta 为 0，符合 null-control 角色。

`TP_0565` 是 school-gate / asphalt road-edge hot anchor。它有行人相关性，但仍是 100m mixed cell，不能当作单一门口点位或 observed pedestrian truth。Overhead p90 delta near zero，说明它不是 mapped-overhead response case。

`TP_0059` 是 parking-lot hardscape diagnostic。它支持 hardscape physics sanity check，但行人相关性弱于 school-gate / waiting-node cells，不应被称为 risk hotspot。它的 mean-vs-p90 overhead response 支持使用 p90 而不是 mean 作为上尾 target。

`TP_0542` 是 mapped pedestrian-overhead / shaded river-walkway case。h15 distribution diagnostic 支持 p90 的 mixed-cell upper-tail 解释，但不应被外推为全部 shaded walkway 都具有同样响应。

## 7. Interpretation Caveats

所有结果都是 100m mixed-cell summaries，不是 point-level pedestrian Tmrt。

SOLWEIG 输出是 modeled Tmrt field，不是观测真值；当前阶段没有把 Tmrt 转换为 local WBGT，也没有校准 observed local WBGT。

`m_rad_pct` 是当前 manifest batch 内的相对 ranking，不能跨不同 forcing、scenario、domain 直接比较，除非 reference domain 和 normalization 明确一致。

`overhead_as_canopy` 是 mapped geometry sensitivity，不包含 unmapped micro-shelter。街景可见但 DSM / overhead layer 未表达的小遮阴结构只能作为 uncertainty 或单独 manual sensitivity，不能混入 canonical overhead scenario。

`tmrt_max_c` 只适合作 diagnostic evidence。若 max 与 p90 / p95 不一致，应优先解释 distribution，而不是用 max 支撑主要结论。

当前结果支持 "SOLWEIG-derived local radiative modifier evidence"，不支持 "hazard map equals risk map"，也不支持 "validated local WBGT prediction"。

## 8. Interim Recommendation

建议在本 interim findings note 完成 review / checkpoint 前，暂缓 until review/checkpoint optional diagnostics 和 formal-hot-day forcing。Review 后的下一步选项应限于 pilot closeout / checkpoint，或 formal-hot-day forcing QA。当前已有证据足够支持下一步讨论：

```text
1. 是否接受 Core 8 base ranking 作为 v1.2-beta pilot 的 typology sanity check。
2. 是否接受 TP0835 relabel 为 wooded green-space / low-radiative diagnostic。
3. 是否接受 TP0542 h15 distribution 作为 p90 upper-tail target 的关键证据。
4. 是否接受 TP0059 mean-vs-p90 response 作为 p90 target 的补充证据。
5. 是否继续保持所有结果在 SOLWEIG-derived Tmrt modifier evidence 的 claim boundary 内。
```

Review 完成后，再决定是否需要追加 optional diagnostics 或正式热日 forcing；在 review 前不建议继续扩大运行规模。

## 9. Next Decision Gate

下一决策门应只处理三件事：

```text
1. accept Core 8 typology sanity pass；
2. decide checkpoint / optional diagnostics / formal-hot-day forcing QA；
3. do not start surrogate / ML / hazard map yet。
```

在该 gate 前，继续保持当前 claim boundary：no local WBGT, no observed truth, no risk map, no hazard map。
