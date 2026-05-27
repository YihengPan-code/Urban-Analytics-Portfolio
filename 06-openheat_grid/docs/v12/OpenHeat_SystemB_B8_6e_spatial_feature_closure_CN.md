# OpenHeat System B B8.6e 空间失败与特征缺口闭合说明

生成范围：System B 代理模型的空间失败诊断、特征缺口审计、紧凑安全特征探针，以及 targeted N300 候选设计。

## 结论

- B8.6e 状态：`B86E_SPATIAL_FEATURE_CLOSURE_PASS`
- 最弱空间分箱：`west_north`
- 最弱 typology × spatial 组合：`residential @ west_north`
- 安全非坐标工程特征是否已证明可升级：是
- targeted N300 候选数：150

## 为什么接在 B8.6d 后面

B8.6d 的两阶段工作流仍然是诊断用途，主要阻碍是 spatial_holdout。B8.6e 因此不继续盲目扩展模型族，而是解释空间失败、审计缺失特征，并判断 B8.6f 或 targeted N300 是否有必要。

## 主要发现

1. spatial_holdout 的排序与 top-k 支持仍然不足，弱分箱需要被视为特征空间覆盖问题，而不是已验证的局地 WBGT 预测问题。
2. 锚点低估仍然集中在少数强冷却参考单元，尤其需要检查 TP_0857 等锚点相似邻域。
3. 中性单元误提升仍需控制；中性边界单元不能因为模型输出被提升为冷却候选。
4. 当前紧凑特征对连续遮阴廊道、可步行遮阴、热口袋开敞曝晒比例、峡谷方向与粗糙度等表达仍不足。

## 建议

- B8.6f 只能作为窄范围改进工作流：优先复测安全、非坐标、可解释的紧凑工程特征。
- 如果当前紧凑特征无法闭合空间失败，应审阅 targeted N300 候选设计；它不是运行清单。
- AOI-wide preflight 和 B9 仍然不应启动。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 hazard_score 或 risk_score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 SOLWEIG 或 QGIS。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
