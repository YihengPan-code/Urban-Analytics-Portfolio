# System A Level 1 输出契约

本契约只覆盖 System A Level 1 的临时、回顾性输出。它定义的是站点网络背景热应激分数和 ge31 诊断概率，不定义 100m 网格本地 WBGT、风险分数、SOLWEIG/Tmrt 输出或公共预警。

## 字段解释

| 字段 | 含义 | 允许解释 | 禁止解释 |
|---|---|---|---|
| timestamp_sgt | 新加坡时间戳 | Level 1 时间严重度对齐键 | 实时预警发布时间 |
| timestamp_utc | UTC 时间戳 | 跨系统/日志对齐键 | 本地微气候空间键 |
| station_id | 站点编号 | 站点网络诊断单元 | 100m cell_id |
| dataset_label | hourly_max / hourly_mean 等诊断标签 | 表明目标聚合语境 | 模型族或风险等级 |
| wbgt_a_score_c | WBGT_A 回归分数 | 背景 WBGT-like 热应激强度 | validated local WBGT 或官方 WBGT |
| wbgt_a_score_model_id | 回归分数模型 ID | 当前默认 M4_like_inertia_ridge | 模型性能证明 |
| wbgt_a_score_version | 输出版本 | 追踪 Sprint 4A 契约版本 | 训练版本或部署版本 |
| p_ge31_diagnostic | ge31 诊断概率 | 回顾性官方 WBGT >=31 的诊断概率 | 官方预警概率或前瞻 forecast 概率 |
| p_ge31_calibrator_id | 概率校准器 | logistic_score_calibration | 新模型训练声明 |
| p_ge31_validation_context | 概率验证语境 | blocked_date_calibration | 线上前瞻验证 |
| ge31_screening_flag_best_f1_optional | 可选 best-F1 筛查标记 | 研究报告中的诊断筛查 | 官方 advisory |
| ge31_screening_flag_high_recall_optional | 可选高召回筛查标记 | 研究报告中偏保守筛查 | 精准警报 |
| p_ge33_exploratory_optional | ge33 探索占位 | 仅探索性分析 | 运营输出 |
| is_retrospective | 是否回顾性 | 必须为 true | 可被理解为 live forecast |
| source_prediction_context | 来源语境 | OOF / blocked-date 诊断来源说明 | 线上生产环境 |
| quality_flag | 质量标记 | 标记样本、缺失、schema-only 等 | 风险等级 |
| notes | 备注 | 解释行级 caveat | 额外输出禁止字段 |

## 两种输出模式：station_diagnostic 与 aoi_temporal

`station_diagnostic` 是站点行级的回顾性诊断输出，适合模型诊断、station bias analysis 和回顾性报告。它保留 `station_id`，但不能被 System B 当作 cell-level severity、cell modifier 或 local WBGT 使用。

`aoi_temporal` 是面向下游 System B temporal gating 的合适模式。该模式应使用 AOI-level 时间严重度行，并显式提供 `aoi_id`、`spatial_scope` 和 `aggregation_method`。任何 AOI 聚合方法都必须在输出契约或伴随报告中说明，不能隐含地把 station row 直接升级为 AOI 或 cell 结果。

System B 不得直接消费 station-level diagnostic rows 作为 cell-level severity。System B 只能消费 AOI-level temporal severity，或消费已明确记录聚合方法的 temporal aggregation 输出。

## 允许解释

System A Level 1 当前可以被解释为：一个站点网络背景热应激评分层。`wbgt_a_score_c` 是 WBGT-like 回归分数，`p_ge31_diagnostic` 是基于该分数的 ge31 回顾性诊断概率。它们适合用于研究报告、回顾性分析、方法比较和 System B 的时间严重度输入。

## 禁止解释

不得把任何 Level 1 字段解释为 100m cell 本地 WBGT、健康风险、公共预警、实时 forecast skill、SOLWEIG/Tmrt 结果、暴露或脆弱性结果。也不得把站点残差转写成 cell modifier。

## System B 示例用法

允许：System B 读取 `timestamp_sgt`、`wbgt_a_score_c`、`p_ge31_diagnostic`，把它们作为同一时间片下的背景热严重度门控信号，再与独立定义的辐射/形态 hazard modifier 组合。组合后的量仍应叫 hazard score 或 prioritisation score，而不是 local WBGT。

## 误用示例

禁止：把 `wbgt_a_score_c + station_residual + cell_modifier` 输出为 `local_wbgt_c`。这会把站点网络诊断分数静默升级成未验证的 100m 本地 WBGT。

## 质量标记

- `ok_retrospective_sample`: 来自既有诊断预测的小样本行。
- `sample_only_retrospective`: Sprint 4A 样本导出，不是完整运营导出。
- `schema_only_no_source_predictions`: 源预测缺失时，仅写出表头。
- `missing_probability`: 该行概率伴随输出不可用。
- `source_gap`: 上游证据文件缺失。

## 回顾性与前瞻性 caveat

本契约默认 `is_retrospective=true`。当前证据来自 LOSO、formal-hourly OOF-derived、blocked-date 和 historical future-block 诊断。它们支持回顾性诊断和报告，不支持“已经证明实时 forecast skill”。
