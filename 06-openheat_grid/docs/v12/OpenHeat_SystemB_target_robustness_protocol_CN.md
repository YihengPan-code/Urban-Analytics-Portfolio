# OpenHeat System B 目标稳健性审计协议

本文档定义 Sprint B1 对 System B / SOLWEIG 派生目标族的审计协议。审计对象是既有摘要表中的辐射暴露指标，不是外部标准验证，也不是对观测热应激的校准。

## 为什么需要审计 p90

`tmrt_p90_c` 是 OpenHeat 当前 operational target，而不是国际统一标准。选择 p90 的直觉是避免单个极端像元控制排序，同时保留高暴露尾部信息；但这种选择需要在现有样本中接受稳健性检查。

审计应比较 p90 与以下伴随目标之间的关系：

- mean
- p75
- p95
- max
- area-above-threshold metrics, if available
- `delta_tmrt_p90_c`
- `m_rad_pct`

如果 p90 相对这些伴随目标排序不稳定，后续不能把 p90 单独作为 System B 的强结论基础。

## 协议维度

### 1. Target availability

检查每个 scenario / hour 是否存在候选目标字段，记录缺失字段、非空样本数、cell 数、以及 valid-pixel 统计。

### 2. Ranking correlation

在同一 scenario / hour 内，对所有可用目标两两计算 Spearman 排名相关。Core 8 场景中若 `n_cells < 8`，结果只作为小样本诊断；即使 `n_cells = 8`，也不应过度解释。

### 3. Top-k overlap

在同一 scenario / hour 内比较目标两两 top-k 集合：

- Core 8 使用 `top_k = min(3, n_cells)`
- 更大样本使用 `top_k = ceil(0.25 * n_cells)`

输出 overlap count 与 Jaccard overlap。Core 8 的 top-k 统计只用于诊断，不用于正式验证。

### 4. Scenario sensitivity

若 base 与 overhead scenario 可按 `cell_id` / `hour` 配对，则计算 overhead minus base 的 p90、modifier 与可用伴随指标差值。重点检查 overhead 处理是否在预期方向上降低或改变辐射目标，以及哪些 cell 变化最大。

### 5. Hour stability

在同一 scenario 和同一目标指标内，比较不同小时之间的 cell 排名。输出小时对之间的 Spearman 排名相关与 top-k overlap，并识别持续高排名或持续低排名 cell。

### 6. Typology interpretability

若存在 typology label 或 pilot cell label，检查持续高/低排名 cell 是否与 hardscape、shade、wooded、road-edge、water-adjacent 等标签方向相符。若标签不可用，只输出 cell 级目标排名并标记解释性缺口。

### 7. Pedestrian relevance flags

若摘要或配置中存在 pedestrian-accessible、walkway、bus-stop、school-gate 等标记，应在解释性审计中保留。若没有显式 pedestrian-accessible mask，则必须把它列为后续 Product B 使用的限制。

### 8. Decision rule

基于上述证据作出以下之一的建议：

1. keep p90 primary：若 `tmrt_p90_c` 可用、与相邻分位数/mean 排序一致、top-k 稳定，保留为 primary。
2. use p90 + companion target：若 p90 基本稳健但存在尾部或阈值敏感性，要求配套 p95、area-above-threshold、`delta_tmrt_p90_c` 或 `m_rad_pct`。
3. downgrade p90 if unstable：若 p90 排名相对 mean/p75/p95/top-k 明显不稳定，降级为 sensitivity target。
4. require future pedestrian-accessible mask：若高排名由不可通行或非行人暴露区域驱动，要求未来加入 pedestrian-accessible mask 后再作下游使用。

## Sprint B1 输出边界

本协议只支持 System B target robustness audit。它不运行 SOLWEIG，不运行 QGIS，不读取 raster，不训练 ML，不创建 surrogate，不输出 risk_score，不输出 local_wbgt_c，不执行 System A/B coupling。
