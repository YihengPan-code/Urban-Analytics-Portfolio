# OpenHeat System B B8.7a N300 设计 QA 降负与补丁说明

## 结论

- B8.7a 状态：`B87A_PATCHED_DESIGN_READY_FOR_REVIEW`
- 是否发现人工 QA 输入：`yes`
- 水体 / 纯河道快速复核队列：`8` 行
- 自动替换候选池：`681` 行
- v3 设计表行数：`150` 行

## 为什么 B8.7a 接在 B8.7 后面

B8.7 已经生成 150 个 N300 候选单元，并确认与当前 N150 标签没有重叠，角色配额也保持严格平衡。但它仍然存在 west_south 支持不足、住宅 / 交通类型集中、TP_0037 与 TP_0433 锚点复核、中性边界多样性、稀疏特征空间以及 connected shade corridor 来源缺口等人工 QA 问题。因此 B8.7a 只做 QA 降负、人工模板、自动复核标记、候选替换池和 v3 设计草案。

## 人工 QA 工作流

优先检查水体、河道或纯表面候选；其次检查 west_south；然后检查 TP_0037 / TP_0433 锚点类候选；再检查中性多样性；最后检查 park_open_space / commercial 覆盖不足以及 residential / transport 集中。只检查明显应排除的单元也可以；不确定的行会保留为 REVIEW，而不是自动排除。

## 当前状态解释

如果人工 QA 输入缺失，v3 表是 `DRAFT_AUTO_ONLY`，候选集合与 B8.7 保持一致，只增加补丁状态和 QA 标记。人工输入提供后，脚本会按 `exclude` / `replace` / `source_review` 等决策应用补丁，并尽量保持 150 行、无 N150 重叠、无重复、角色配额不变。

## 来源复核

manual_source_review_blockers=3; known_connected_shade_corridor_gap=carried_to_B86G3。connected shade corridor 仍需未来 B8.6g3 获取或核查行人遮阴网络、covered walkway 或等价矢量来源；本轮不会从质心距离推断连通性。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 hazard score 或 risk score。
- 不是 exposure / vulnerability score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有创建 N300 execution manifest。
- 没有 Tmrt-to-WBGT 转换。
- 没有 System A/B coupling。
