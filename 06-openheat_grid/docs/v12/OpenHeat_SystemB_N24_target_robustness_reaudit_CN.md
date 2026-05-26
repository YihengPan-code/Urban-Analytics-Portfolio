# OpenHeat System B N24 目标稳健性复审说明

## 为什么需要 B4
B4 的目的，是在 B3 已经完成并校验通过的 N24 SOLWEIG 汇总结果之上，重新审计 System B 的辐射暴露目标族是否稳健。它只读取既有 CSV/Markdown 汇总，不重跑 SOLWEIG，不运行 QGIS，不读取原始栅格。

## N24 相比 Core 8 增加了什么
Core 8 只能说明早期目标选择是否有初步一致性；N24 增加了更多诊断角色、替换单元和连续性锚点，使 p90、p95、max、均值以及阈值面积指标可以在更宽的样本内比较。B4 仍然是样本内证据，不是全 AOI 最终结论。

## p90 做得好的地方
`tmrt_p90_c` 的 B4 建议状态为 `n24_supported_primary_candidate`。关键证据包括：跨小时平均 Spearman `0.993`，p90 与 p75 平均 Spearman `0.931`，p90 与 pct_ge_50 平均 Spearman `0.896`。
这说明 p90 在 N24 内可以作为混合单元上尾辐射暴露的主要候选指标：它比均值更能看到局部热斑，又不像 max 那样完全依赖单个极端像元。

## 为什么还需要 p95、max 和阈值面积伴随指标
p95 用来检查 p90 以上的更高尾部是否改变解释；max 用作极端像元敏感性和 QA 检查，不适合作为主目标；阈值面积指标说明有多少比例像元超过 40/45/50/55 C 的 Tmrt 门槛。
B4 的尾部分类计数为 `{'threshold_area_hot': 20, 'uniform_hot': 12, 'mixed_cell_upper_tail': 6, 'max_only_extreme': 6, 'mostly_shaded_low_tail': 4}`。阈值面积的 N24 汇总建议为 `{'pct_pixels_tmrt_ge_40': 'optional_companion', 'pct_pixels_tmrt_ge_45': 'optional_companion', 'pct_pixels_tmrt_ge_50': 'optional_companion', 'pct_pixels_tmrt_ge_55': 'optional_companion'}`。

## overhead_as_canopy 敏感性意味着什么
`overhead_as_canopy` 只是结构敏感性场景，用来观察架空/遮蔽结构假设改变时，均值、p90、p95、max 和阈值面积是否同步变化。它不是绝对真实世界，也不是观测验证。

## 为什么这仍然不是 local WBGT / risk
SOLWEIG/Tmrt 输出是模拟得到的辐射暴露目标，不是 WBGT，不是风险，不是官方预警，也不是地面观测真值。B4 不计算 local WBGT、hazard_score、risk_score，不训练代理模型，也不做 System A/B 耦合。

## 下一步可以做什么
建议进入 B5：N24 target freeze / modifier reference definition update。只有在目标族被接受之后，才应准备后续 surrogate protocol 或 System A/B coupling contract。
