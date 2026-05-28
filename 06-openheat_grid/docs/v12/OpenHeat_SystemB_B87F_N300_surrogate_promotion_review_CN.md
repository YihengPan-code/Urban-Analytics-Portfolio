# OpenHeat System B B87F N300 代理模型晋级复核说明

生成时间：2026-05-28 14:11:59

状态：`B87F_EXTRA_TREES_REMAINS_CANDIDATE_NO_PROMOTION`

## 范围

本轮只复核 N300 SOLWEIG 模拟 Tmrt 差值标签上的代理模型。它不是观测真值，不是 WBGT 转换，不是 AOI/B9 推理，也不是风险、危害、暴露或脆弱性输出。

## 主要结论

- B87E 先前状态：`B87E_SURROGATE_BENCHMARK_PASS_NO_PROMOTION`。
- B87F 最优 GroupKFold：`b87e_original_main / extra_trees MAE=0.150376`。
- 最优 old-to-new：`no_coordinates_no_design_flags / random_forest MAE=0.213904`。
- 特征集赢家：`b87e_original_main`。
- 晋级决定：`NO_AOI_PREFLIGHT`。
- AOI 预检门：`BLOCKED_NO_AOI_PREFLIGHT`。

## 诊断

B87E 没有晋级的核心原因是：没有模型在分组交叉验证、old-to-new 泛化、分层稳定性和源数据门槛上同时明确超过既有 `extra_trees` 候选。B87F 的补丁复核继续把 `extra_trees` 作为 N150/B87E 候选基线，并对低缺失、低相关、物理核心、上下文残差和稳健 old-to-new 特征集进行了受控比较。

## 下一步

推荐下一轮：`B87F2_feature_patch_and_B86g4_true_vector_source_acquisition`。在连接遮荫廊道、完整步行网络、树冠与建筑真矢量交互等 B8.6g3 缺口没有关闭前，不应生成 AOI/B9 输出。

## 边界

本轮没有运行 QGIS 或 SOLWEIG，没有读取、写入、复制或移动栅格，没有生成 AOI、B9、WBGT、风险、危害、暴露或脆弱性结果，也不把特征重要性解释为因果证据。
