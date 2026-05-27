# OpenHeat System B B8.6f 代理模型闭合综合审查说明

## 结论

- B8.6f 状态：`B86F_SURROGATE_CLOSURE_PASS`
- AOI preflight 状态：`AOI_PREFLIGHT_BLOCKED`
- B9 状态：`BLOCKED`
- N300 v2 候选设计行数：150
- N300 v2 角色配比：typology_gap_fill=50；spatial_gap_fill=30；anchor_like_replication=25；neutral_boundary_replication=25；sparse_feature_space=10；control_cell=10

## 为什么 B8.6f 接在 B8.6e 后面

B8.6e 已经定位了空间留出失败、锚点低估和中性单元误提升问题，但安全工程特征探针没有闭合 spatial_holdout。B8.6f 因此只做证据综合、候选设计复核、特征获取路线图和弃权门诊断，不做 AOI-wide 预测，也不进入 B9。

## B8.6e 证明了什么，没有证明什么

B8.6e 证明当前紧凑特征存在空间和类型覆盖缺口；没有证明安全工程特征已经可以作为生产级空间闭合证据。类型留出中的 Spearman 改善只能作为诊断线索，因为 top-k 支持变差。坐标和距离特征只能用于诊断空间外推风险，不能作为生产预测特征。

## 空间失败综合

west_north、west_south、east_south、east_north 仍然是需要审查的空间分箱。主要失败模式包括 spatial-bin-out-of-domain、anchor-underprediction、neutral-false-promotion、feature-distribution-shift、target-role-mismatch 和 sample-support-low。

## 锚点和中性失败综合

TP_0857、TP_0542、TP_0433、TP_0037、TP_0141 仍然需要作为锚点门控单元。已知中性单元和近零单元仍可能被模型误提升为有意义冷却，因此中性边界必须保留为弃权或复核条件。

## 安全特征探针裁决

B8.6e 的安全物理工程特征没有改善 spatial_holdout，也没有改善 cell_group。typology 的 Spearman 改善是诊断性的，同时 top-k 变差，不能视为生产级闭合。

## N300 v1 审计与 N300 v2 设计

N300 v1 是候选设计，不是运行清单，并且过度偏向 typology_gap_fill。B8.6f 生成了角色配额平衡的 N300 v2：typology_gap_fill=50；spatial_gap_fill=30；anchor_like_replication=25；neutral_boundary_replication=25；sparse_feature_space=10；control_cell=10。该文件仍然只是 candidate design，不是 SOLWEIG manifest，不是 QGIS runner，也不是 N300 执行包。

## 特征获取路线图

高优先级特征族包括：pedestrian-accessible shaded fraction、connected shade corridor / shade continuity、overhead geometry shape descriptors、sunlit-hot-pocket area fraction、tree/building shadow interaction、canyon orientation / height roughness。下一步应优先做 B8.6g vector/compact feature acquisition，并保持无 raster、无 QGIS、无 SOLWEIG。

## 弃权门诊断

B8.6f 只在已有 B8.6d/B8.6e 紧凑预测和失败诊断上模拟 moderate / strict gate。该诊断不会生成 AOI-wide 预测。只有在未来保留覆盖率和空间指标同时显著改善时，才可考虑单独的 scope-limited dry-run preflight。

## 推荐下一路线

优先推荐 B8.6g vector/compact feature acquisition；如果评审接受 N300 v2 角色平衡设计，则推进 B8.7-N300-PRE targeted sample design freeze。B8.6h scope-limited dry-run preflight 仅作为低优先级、条件性未来路线。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 hazard_score 或 risk_score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
