# OpenHeat System B B8.7b.3 全幅来源锁定与物化预案

## 结论

状态：`B87B3_SOURCE_LOCK_READY_FOR_MATERIALIZATION`。

B8.7b.3 接在 B8.7b.2 之后，因为 B8.7b.2 没有找到 150 个新 N300 单元的逐单元 `TP_xxxx` 资产文件夹。新的人工线索表明，真实来源是全幅 DSM、植被 DSM、SVF 和网格/架空结构矢量，而不是已经切好的逐单元文件夹。

## 来源锁定

- DSM：`LOCKED (qa_corrected_final)`。锁定为人工 QA 与高度/几何 QA 后的最终 DSM，不使用旧版或中间版 DSM。
- CDSM：`LOCKED (likely_final_base_vegetation_dsm)`。作为现状植被 DSM。
- 网格：`LOCKED (likely_final_geometry_source)`。用于 Toa Payoh 100 m 单元几何与 N300 覆盖检查。
- DEM/landcover：`DEM=NOT_APPLICABLE_GENERATE_FLAT_TILE (flat_dem_convention); landcover=NOT_APPLICABLE_NOT_USED (not_used_by_solweig_source_of_truth)`。DEM 以后按平坦瓦片约定生成；landcover 不作为 SOLWEIG 来源要求。

## SVF 场景模型

base 场景使用建筑 DSM + 现状植被 DSM。overhead_as_canopy 场景使用建筑 DSM + max(现状植被 DSM, 架空结构 canopy)。base 的 `SkyViewFactor.tif` 是全幅来源，不是逐 tile 的 `svfs.zip`。overhead_as_canopy 必须在后续 lane 中生成场景专属 SVF，不能复用 base SVF。

## 架空结构来源

架空结构状态：`LOCKED_CANONICAL_V10_OVERHEAD_LAYER`。当前锁定来自 v12 配置和来源说明中一致指向的 v10 overhead 结构图层。

## 元数据与可行性

栅格头信息：`HEADER_OK=3/3`。提取/物化可行性：`base=FEASIBLE_FOR_B87B4_PREMATERIALIZATION; overhead=FEASIBLE_FOR_B87B4_PREMATERIALIZATION`。本 lane 只做元数据和预案，不裁剪、不复制、不移动、不写入任何栅格，也不创建逐单元资产。

## 下一步

建议下一 lane：`B8.7b.4 local-only materialization/pre-extraction package`。B8.7c 只能在本地逐单元资产物化完成、并且用户明确授权执行包之后再考虑。

## 边界

PASS: no raster pixel read; no raster write/copy/move/symlink; no svfs.zip open; no QGIS/SOLWEIG; no manifest/runner; no AOI/B9/WBGT/risk/coupling。
