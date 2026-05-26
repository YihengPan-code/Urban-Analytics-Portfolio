# OpenHeat System A Level 1 高尾部整合说明

## 任务与状态

本文档对应 `A-L1H.2b - System A Level 1 high-tail integration / output contract`。

- Status: `PASS`
- Decision: `ACCEPT_DIAGNOSTIC_COMPANION_HOLD_OPERATIONAL_CLAIMS`
- 范围：只记录 System A Level 1 当前高尾部整合结论、输出契约和声明边界。
- 本次修订仅修复中文文档编码与表述；不训练模型，不重新运行概率校准，不修改 CSV 证据表，不启动 A-L2 或 A-L1H.3。

## 1. 从 A-L1H.0 到 A-L1H.2 的变化

A-L1H.0 发现，System A 的确定性 WBGT_A 分数仍可作为回顾性时间严重度诊断，但在 ge31 附近存在高尾部压缩：固定 31 分数阈值会漏掉一部分观测 WBGT 大于等于 31 C 的事件，并且 S142 等站点存在偏差。

A-L1H.0b 做了部分天气情景合并，保留率为 2700/6696，即 40.3%。该结果只能作为部分时期诊断证据。A-L1H.0c 随后恢复了全时期天气情景覆盖，6696/6696 行全部匹配，并显示 radiation-hot 情景包含了大多数 ge31 事件和漏报，但这仍然只是回顾性情景诊断，不是因果证明。

A-L1H.1 审计了 formula/proxy 路线，结论为 `WEAK_OR_NEGATIVE`。原始公式或物理代理候选没有产生 fixed_31 crossing，因此不能替代当前 WBGT_A 分数，也不能作为 formula-v2 已完成的证据。

A-L1H.2 接受了一个概率伴随诊断量：`M4_inertia_ridge + isotonic_score_only`，验证方式为 `station_grouped_loso`。该伴随量改善了 ge31 的回顾性识别，但不改变主分数，也不构成运行性预报能力。

## 2. 当前伴随量

当前伴随量定义如下：

`P_ge31 = M4_inertia_ridge model_score calibrated with isotonic_score_only under station_grouped_loso; selected diagnostic threshold about 0.309.`

核心指标来自 A-L1H.2 的站点留一回顾性诊断：

- Brier 约 `0.052`
- PR-AUC 约 `0.610`
- 选定诊断阈值约 `0.309`
- precision 约 `0.678`
- recall 约 `0.765`
- F1 约 `0.719`
- CSI 约 `0.561`

`P_ge31` 的角色是回顾性诊断伴随量，用来辅助解释现有 M4 分数对 ge31 事件的识别。它不是官方预警概率，不是政策阈值，也不是前瞻性预报技能证明。

## 3. 当前可靠内容

当前可靠结论仅限于内部回顾性诊断：

- `WBGT_A_score` 或 `model_score` 仍然是 System A Level 1 的主要时间严重度诊断分数。
- `P_ge31` 可以作为 ge31 的回顾性诊断伴随量。
- A-L1H.2 显示，相比固定分数阈值 31，`P_ge31` 的诊断阈值约 0.309 能更好地平衡 ge31 的 precision、recall、F1 和 CSI。

安全表述应保持为：System A Level 1 提供回顾性 WBGT_A 时间严重度诊断；`P_ge31` 是站点留一验证下的内部回顾性 ge31 伴随诊断量。

## 4. 仍未解决内容

ge31 捕捉已经有实质改善，但还没有完全解决。高尾部压缩仍然存在，站点和情景 caveat 仍需保留：

- S142 仍是高尾部漏报和低估相关的重点诊断站点。
- S139 的 ge31 支持较低，站点级结论不稳定。
- radiation-hot 情景、very-high shortwave 和 shortwave_3h 情景是重要的回顾性诊断背景，但不能解释为已证明的因果机制。
- ge33 事件支持不足，仍然只属于探索性诊断。

因此，不能声称 ge31 已完全解决，不能声称 ge33 概率已经可靠，也不能把情景变量解释为真实世界热风险因子的因果证明。

## 5. A-L2 决策

A-L2 当前应保持 `HOLD`。

原因是：A-L1H.2b 是 Level 1 输出契约整合任务，不做站点上下文残差建模。S142、S139 等站点 caveat 说明后续可能需要站点上下文审查，但这必须作为单独的 A-L2 任务和评审关口启动，不能从本文档修订中直接开始。

## 6. A-L1H.3 决策

A-L1H.3 只作为可选的独立 review gate。

如果用户希望继续提高高尾部识别能力，可以单独打开 A-L1H.3 high-tail regression 审查任务。但本次 A-L1H.2b 不实现 high-tail regression，不比较新模型，也不重新训练基础 WBGT 模型。

## 7. 输出契约

当前 System A Level 1 输出契约如下：

1. `WBGT_A_score` 或 `model_score`
   - 角色：主要的回顾性时间严重度诊断分数。
   - 可用作：内部背景严重度诊断。
   - 不可用作：local 100m WBGT、官方预警、公众告警、前瞻性预报技能证明。

2. `P_ge31`
   - 角色：回顾性 ge31 诊断伴随量。
   - 来源：现有 `M4_inertia_ridge` 分数经过 `isotonic_score_only` 校准，验证方式为 `station_grouped_loso`。
   - 可用作：内部回顾性 ge31 高尾部复核。
   - 不可用作：官方预警概率、政策概率、公众告警概率、前瞻性预报能力证明。

3. 可选阈值操作点
   - 当前诊断阈值约为 `0.309`。
   - 可用作：内部回顾性诊断标记。
   - 不可用作：最终政策阈值、运行性预警触发器、公众告警阈值。

## 8. 声明边界

允许的表述：

- calibrated hourly WBGT_A temporal severity diagnostic
- retrospective diagnostic companion for observed WBGT >= 31 C
- internal retrospective ge31 high-tail review
- ge33 remains exploratory
- A-L2 remains held
- A-L1H.3 remains optional and separate

禁止的表述：

- validated local 100m WBGT prediction
- official warning probability
- prospective forecast skill
- real-time heat risk forecast
- public-facing alert
- System A/B coupled risk is complete
- hazard map equals risk map
- radiation-hot regime proves causal heat-risk mechanism

## 9. 推荐下一关口

- 接受 A-L1H.2 的 `P_ge31` 作为诊断伴随量。
- 暂缓 A-L2。
- 仅在用户要求进一步改善高尾部时，单独开启 A-L1H.3 review gate。
- 任何运行性、对外预警或前瞻性技能声明之前，都必须先做 prospective metadata / lead-time evaluation。
- 使用 A-L1H.2b integration report 作为当前 System A Level 1 输出契约。
