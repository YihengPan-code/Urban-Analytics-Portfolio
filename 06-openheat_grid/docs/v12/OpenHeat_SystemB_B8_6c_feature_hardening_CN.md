# OpenHeat System B B8.6c 特征加固与失败审计说明

生成时间：2026-05-27 19:28:28

## 结论

- B8.6c 状态：`B86C_TWO_STAGE_PROMISING`
- 扫描特征候选：289
- 安全特征：158
- 排除 / 元数据 / 泄漏风险 / 未来风险叠加特征：131
- 最佳特征集改进摘要：minimal_physics_interpretable/random_forest_regressor vs baseline random_forest_regressor: supporting Spearman 0.441 (+0.001), top10pct 0.245 (-0.024), MAE gain -1.4%.
- 空间与类型失败摘要：spatial flagged 2/4 bins; typology flagged 2/5 bins.
- 锚点 / 中性边界 / 不稳定单元摘要：anchor underprediction rows 17; neutral confusion rows 29; unstable flagged rows 68.
- 两阶段预检摘要：full_safe_compact, threshold=0.05, random_forest_classifier+random_forest_regressor: neutral_accuracy=0.770, supporting Spearman=0.489, top10pct=0.361, anchor_MAE=0.673.
- B8.6d 建议：Recommend B8.6d to formalize the two-stage neutral-boundary workflow before any AOI-wide preflight; B9 remains blocked.
- AOI-wide / B9 状态：`BLOCKED`

## 为什么 B8.6c 接在 B8.6b 后面

B8.6b 已经证明 F5 紧凑标签在强迫日留出和小时留出上表现较强，但 cell-group、空间和 typology 留出仍然偏弱。因此 B8.6c 不追逐更复杂模型，而是审计特征表达缺口、失败模式和后续工作流。

## 边界

- 这不是 B9。
- 这不是 AOI-wide prediction。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 observed truth。
- 这不是 causal feature importance。
- 没有读取或生成 raster。
- 没有运行 SOLWEIG 或 QGIS。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
