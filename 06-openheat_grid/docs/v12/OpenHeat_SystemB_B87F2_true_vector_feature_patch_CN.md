# OpenHeat System B B87F2 真矢量特征补丁说明

生成时间：2026-05-28 15:06:41

状态：`B87F2_FEATURE_PATCH_PARTIAL_NO_AOI`

## 运行原因

B87F 表明，仅靠模型调参不足以让 N300 代理模型进入 AOI 预检。B87F2 因此只检查一个问题：在不运行 QGIS、SOLWEIG、不读取或写入栅格、不生成 AOI/B9/WBGT/风险结果的前提下，现有本地真矢量和紧凑代理特征是否能改善迁移和排序表现。

## 来源结论

已找到来源：`building_canyon, compact_grid_feature, overhead_geometry, pedestrian_network, tree_building_interaction, water_park_road_edge`。仍缺失或未关闭的来源：`connected_shade_corridor, tree_building_interaction`。连接遮荫廊道、完整步行网络、树冠与建筑真矢量交互若仍未关闭，则 AOI 预检继续受阻。

## 特征补丁

本轮构建了覆盖步道/上盖、OSM 本地步行网络代理、建筑矢量形态、水体边缘代理，以及树木-建筑、上盖-步行、上盖-植被、水体-空间背景等紧凑交互项。缺少真矢量来源的部分被明确标记为代理，不作为因果解释。

## 模型结果

补丁矩阵规模：`3000 x 468`。最佳 GroupKFold：`b87f2_pruned_best_effort / extra_trees MAE=0.137744`。最佳 old-to-new：`b87f2_pruned_best_effort / extra_trees MAE=0.201257`。最佳排序 Spearman：`0.800468`。

## 决策

AOI 闸门：`BLOCKED_SOURCE_GAPS_REMAIN`。停止/继续建议：`CONTINUE_FEATURE_ACQUISITION`。推荐下一车道：`STOP_MODEL_TUNING_OR_EXTERNAL_TRUE_VECTOR_ACQUISITION`。

## 声明边界

本轮结果只是 SOLWEIG 模拟 Tmrt 差值的代理模型诊断；不是观测真值，不是 WBGT 校准，不是 AOI/B9 推理，不是热危害或风险图，也不是暴露、脆弱性或因果特征重要性结论。
