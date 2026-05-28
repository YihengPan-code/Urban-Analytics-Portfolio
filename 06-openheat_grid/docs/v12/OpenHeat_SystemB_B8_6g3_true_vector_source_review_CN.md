# OpenHeat System B B8.6g3 真矢量来源审查与来源复核收口说明

## 结论

- B8.6g3 状态：`B86G3_SOURCE_REVIEW_PASS`
- B8.7b execution precheck：`B86G3_READY_FOR_B87B_PRECHECK`
- 外部 / 真矢量来源：`B86G3_NEEDS_EXTERNAL_VECTOR_SOURCE`
- N300 v4 行数：`150`
- N150 重叠：`0`
- duplicate cell_id：`0`
- AOI / B9：继续阻断

## 为什么 B8.6g3 接在 B8.7a 后面

B8.7a 已经把 N300 v3 候选设计修补为 150 行，且无 N150 重叠、无重复，并替换了 TP_0830、TP_0858、TP_0943 三个基本水面单元。但 TP_0103、TP_0104、TP_0464 仍是 source_review，connected shade corridor 也仍然缺少真矢量连通性来源。因此 B8.6g3 只做来源审查、来源复核收口、设计闸门判断和未来提示词，不创建任何执行包。

## B8.7a patched design 摘要

本轮从 B8.7a v3 patched design 出发。B8.6g3 v4 仍保持 150 行、0 个 N150 重叠、0 个 duplicate cell_id。如果没有必须替换的 source_review 单元，v4 与 B8.7a 的差异只是来源复核元数据。

## 人工来源复核事实

- TP_0103：混合河道与两岸，河面约四分之一，不是纯水面；保留，但记录 river-edge caveat。
- TP_0104：同 TP_0103；保留，但记录 river-edge caveat。
- TP_0464：约 37% waterworks、63% woodland，不是纯水面；保留，但记录 utility-site / pedestrian-relevance caveat。
- TP_0159：2022 年为施工场地，但 2026 年为 Toa Payoh Sport Hall；保留，并记录时间性土地利用错配。
- TP_0519：woodland；保留为 vegetation/canopy/green-control candidate。
- TP_0830、TP_0858、TP_0943：基本水面，已在 B8.7a 排除并替换。

## TP_0103 / TP_0104 / TP_0464 收口

三个 source_review 单元均收口为 keep-with-caveat，不再阻断 B8.7b execution precheck。它们的 caveat 是文档和后续 QA 约束，不是 AOI/B9 特征闭合证据。

## 真矢量来源审查

- connected shade corridor：`MISSING_EXPLICIT_SHADE_CONNECTIVITY_SOURCE`。缺少显式行人遮阴网络或连通性表，不能从质心距离、普通 shade fraction 或紧凑单元比例推断。
- pedestrian network：`NO_FULL_FOOTPATH_NETWORK_SOURCE`。covered walkway / pedestrian bridge 来源有帮助，但还不是完整 footpath / walkway 网络。
- building / canyon：`BUILDING_FOOTPRINT_HEIGHT_SOURCE_AVAILABLE`。建筑 footprint / height 来源可用于未来 canyon derivation，但不能升级为 observed local WBGT 证据。
- tree / building interaction：`BUILDING_GEOMETRY_PRESENT_TREE_CANOPY_VECTOR_MISSING`。建筑来源存在，但仍需要 tree-canopy vector 或可信的 vector-derived interaction table。

## 三类 blocker 的区分

1. execution-precheck blocker：候选数量、N150 重叠、duplicate、source_review 单元未收口等会阻断 B8.7b precheck。B8.6g3 当前未发现这些阻断。
2. surrogate / AOI / B9 feature blocker：connected shade corridor、tree/building interaction 和完整 pedestrian network 等真矢量缺口仍阻断 AOI/B9。
3. documentation caveat only：TP_0103、TP_0104、TP_0464 的混合水边 / utility woodland caveat 属于文档 caveat，不自动阻断 B8.7b precheck。

## N300 v4 设计状态

v4 是 source-reviewed design，不是 run-ready manifest。它没有创建 SOLWEIG manifest、QGIS runner、本地执行说明、raster、AOI-wide prediction、B9、local WBGT、hazard_score、risk_score 或 System A/B coupling。

## B8.7b readiness

B8.7b N300 execution precheck may proceed as a precheck-only lane; B8.6g3 creates no execution artifact.

## B8.6g4 建议

建议后续开启 B8.6g4 external/vector acquisition，专门获取或整合 connected shade corridor、pedestrian footpath / walkway、covered walkway、tree canopy、building/canyon 和 water/park/road edge 的真矢量来源。AOI/B9 在这些缺口关闭前继续阻断。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk / hazard score。
- 不是 exposure / vulnerability score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有创建 N300 execution manifest。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
