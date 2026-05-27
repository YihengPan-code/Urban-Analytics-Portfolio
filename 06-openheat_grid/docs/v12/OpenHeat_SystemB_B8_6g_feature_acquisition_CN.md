# OpenHeat System B B8.6g 矢量/紧凑特征获取说明

## 结论

- B8.6g 状态：`B86G_FEATURE_ACQUISITION_PASS`
- 复测准备：`PARTIAL_RETEST_ONLY`
- 推荐下一步：B8.6g2 partial feature-upgraded retest plus B8.7-N300-PRE design freeze
- AOI / B9：继续阻断

## 为什么接在 B8.6f 后面

B8.6f 的结论是：AOI preflight 仍然阻断，B9 仍然阻断，主要原因不是再跑一个更复杂模型，而是局地遮阴、架空结构、热口袋、边界环境、树木与建筑相互作用、峡谷高度粗糙度等特征表达不足。B8.6g 因此只做矢量/紧凑来源发现、特征表生成、覆盖率和复测准备判断。

## 已计算的特征族

pedestrian-accessible shaded fraction, overhead geometry shape descriptors, sunlit-hot-pocket area fraction, local boundary / edge context, neighbourhood-scale context, tree/building shadow interaction, canyon orientation / height roughness, typology-specific geometry

## 仍然阻断或缺源的特征族

connected shade corridor / shade continuity

## 重要解释

本轮生成的 pedestrian shade、sunlit hot pocket、tree/building interaction、canyon roughness 等多项字段是紧凑代理或矢量派生紧凑特征。它们可以进入未来 B8.6g2/B8.6f2 的诊断复测，但不能直接升级为生产级空间闭合证据。connected shade corridor 需要真正的行人遮阴网络或连通性来源，本轮不从质心距离臆造。

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
