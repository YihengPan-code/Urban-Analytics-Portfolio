# OpenHeat System B B87E N300 代理模型基准说明

生成时间：2026-05-28 13:19:37

状态：`B87E_SURROGATE_BENCHMARK_PASS_NO_PROMOTION`

本阶段评估的是 SOLWEIG 派生 `delta_tmrt_p90_c` 的代理模型/仿真器，不是观测 WBGT 校准，也不是全域 AOI/B9 推理。

## 验证

主证据包含按 `cell_id` 分组的 GroupKFold、old-to-new 泛化、空间/类型/角色 holdout（如可用）和 context holdout。随机切分只作为诊断，不作为 headline 证据。

## 模型

headline 模型注册表沿用 N150 兼容顺序：featureless mean、context mean、ridge、elasticnet、random forest、extra trees、hist gradient boosting。`extra_trees` 作为既有 N150 候选基线单独报告。

## 决策

推广决策：`B87E_EXTRA_TREES_REMAINS_CANDIDATE`。推荐下一阶段：`B87F_surrogate_patch_stronger_features_before_any_AOI_preflight`。

## 边界

不生成 AOI/B9 输出，不做 WBGT 转换，不生成 hazard/risk/exposure/vulnerability 图层，不声称观测真值，不把特征重要性解释为因果证据。
