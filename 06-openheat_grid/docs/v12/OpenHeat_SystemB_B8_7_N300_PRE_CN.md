# OpenHeat System B B8.7 N300-PRE 设计冻结与真矢量来源审查说明

## 结论

- B8.7 状态：`B87_N300_DESIGN_NEEDS_QA`
- N300 候选行数：150
- 与当前 N150 标签重叠：0
- connected shade corridor 来源状态：`NOT_AVAILABLE_REQUIRES_MANUAL_DATA`
- AOI / B9：继续阻断

## 为什么 B8.7 接在 B8.6g2 后面

B8.6g2 显示紧凑代理特征对诊断排序有改善，但仍然不是 AOI-wide prediction，也不是 B9。空间留出、类型留出、锚点低估和中性单元误提升仍需要更多样本支持和真矢量来源审查。因此本轮只做 N300 设计冻结预检和 B8.6g3 来源审查，不创建执行包。

## B8.6g2 证据摘要

空间留出 Spearman 约 0.517，top10pct 约 0.500，false promotion 约 0.163；cell-group 留出 Spearman 约 0.527；typology 留出仍然混合，Spearman 约 0.410，false promotion 约 0.209。结论仍是 `B86G2_DIAGNOSTIC_IMPROVEMENT_ONLY`。

## N300 设计审查

候选设计保持 150 行，并且没有与当前 N150 标签重叠。角色配额保持固定，但空间、类型、锚点、中性边界和稀疏特征空间仍需要人工 QA，尤其是 west_south、TP_0037、TP_0433、park_open_space / commercial 覆盖和 residential / transport 集中度。

## 特征覆盖审查

vector_derived=1 proxy_only=7 not_available=1 review=connected shade corridor / shade continuity

## 真矢量来源审查

本轮只审查紧凑/矢量/矢量派生来源。overhead geometry 和 building/canyon 类来源较可用；tree/building interaction 仍有代理或不完整来源限制；connected shade corridor 不能从质心距离推断，必须等待行人遮阴网络、covered walkway 或等价连通性表。

## 人工 QA 包

- QA checklist：`outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_checklist.csv`
- QA guide：`outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_guide.md`

## 冻结决策

当前决策为 `B87_N300_DESIGN_NEEDS_QA`。若人工 QA 接受候选设计，可进入未来 B8.7b execution precheck；若 connected shade corridor / pedestrian network 来源不足，应先进入 B8.6g3 true-vector feature acquisition。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk score 或 hazard score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有创建 N300 execution manifest。
- 没有 Tmrt-to-WBGT 转换。
- 没有 System A/B coupling。
