# OpenHeat System B 产品分类边界

本文档定义 OpenHeat v12 / System B 在 Sprint B1 中使用的产品分类。当前工作只做已有 SOLWEIG/Tmrt 摘要的目标稳健性审计，不做 System A/B 耦合，也不生成规划风险产品。

## 当前定位

System B 当前只表示 SOLWEIG 派生的辐射暴露差异。它回答的是：在相同外部气象强迫下，哪些局地空间结构更可能呈现较高辐射热危害潜势。

System B 指标不是观测真值，不是公共预警，也不包含暴露或脆弱性。

## Product A：System A WBGT 热应激状态

来源：System A。

回答问题：什么时候热。

当前状态：本 sprint 不实现、不重跑、不输出 System A 结果。Product A 可作为未来耦合时的时间门控来源，但本 sprint 只在架构边界上引用其角色。

允许表述：

- System A WBGT heat-stress state
- calibrated hourly WBGT temporal baseline
- AOI temporal severity candidate

## Product B：System B 辐射热危害潜势

来源：SOLWEIG/Tmrt 摘要表。

回答问题：在同一外部强迫下，哪里因空间结构呈现更高的辐射热危害潜势。

候选字段：

- `tmrt_p90_c`
- `delta_tmrt_p90_c`
- `m_rad_pct`
- companion metrics such as `tmrt_mean_c`, `tmrt_p75_c`, `tmrt_p95_c`, `tmrt_max_c`, and threshold-area metrics when available

当前状态：Sprint B1 只审计 Product B 目标族的可用性、排序稳健性、情景敏感性、小时稳定性和解释性。

允许表述：

- SOLWEIG-derived radiant exposure indicator
- radiative heat-hazard potential
- simulation-informed local radiative modifier
- first-order local heat hazard prioritisation

## Product B2：可选 UTCI/PET 敏感性层

来源：未来可能的 UTCI/PET 后处理或敏感性实验。

回答问题：在 Tmrt 之外，热舒适指数对候选空间排序是否给出相近或相反的信号。

当前状态：未来工作。本 sprint 不实现、不计算、不导出 B2 产品。

## Product C：WBGT 条件化辐射优先级

来源：未来 Product A 与 Product B 的明确耦合合同。

回答问题：当 System A 表示时段达到热应激条件时，哪些局地空间应优先关注其辐射热危害潜势。

当前状态：未来工作。本 sprint 不实现 System A/B 耦合，不输出 Product C。

## Product D：规划热风险优先级

来源：未来 hazard、exposure、vulnerability 的显式组合。

回答问题：在规划或治理语境中，哪些地点因热危害、暴露和脆弱性共同作用而需要优先干预。

当前状态：未来工作。本 sprint 不接入人口、活动、敏感人群、设施暴露或脆弱性数据，不输出 Product D。

## 禁止用语

以下表述只能作为“禁止用语”列出，不得作为 OpenHeat System B 的能力声明：

- local WBGT
- observed heat truth
- risk map
- official warning
- System B predicts WBGT
- Tmrt equals WBGT

## Sprint B1 边界

Sprint B1 只读取既有摘要产物，审计 `tmrt_p90_c`、`delta_tmrt_p90_c`、`m_rad_pct` 及其伴随指标是否适合作为 System B 目标族。它不运行 SOLWEIG，不运行 QGIS，不读取 raster，不训练 surrogate，不生成 risk_score，不生成 local_wbgt_c，也不执行 System A/B 耦合。
