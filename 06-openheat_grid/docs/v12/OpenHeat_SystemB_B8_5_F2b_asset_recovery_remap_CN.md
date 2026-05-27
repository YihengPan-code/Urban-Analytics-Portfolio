# OpenHeat System B B8.5-F2b 本地资产恢复与路径重映射说明

修复日期：2026-05-27

## 结论

本次 B8.5-F2b 文档修复仅处理中文编码，不改变任何 readiness CSV 指标、运行矩阵或资产判定。

当前状态为 `PARTIAL_REMAP_AVAILABLE`。

- F2a ready runs：`0/480`
- F2b strict ready runs：`0/480`
- 若本地输出根目录已创建且 QGIS 手工检查通过，F2b ready runs：`240/480`
- 已恢复资产：`cell_geometry=24; raster_tile=145; svf_zip=48`
- 仍缺失或需人工确认：`local_output_root=1; met_forcing_file=5; qgis_algorithm_manual_check=1`
- 已选择根别名：`original_project`
- 本地输出根目录动作：`human_create_parent_and_directory`
- QGIS/SOLWEIG executed：`no`

## 范围边界

本次工作只是 B8.5-F2b 本地 SOLWEIG 资产发现、根别名重映射与就绪模拟门禁的中文说明修复。

QGIS 没有运行，SOLWEIG 没有运行。没有创建、复制、打开分析或暂存任何 raster。`svfs.zip` 没有被复制或打开。没有创建 AOI-wide prediction，没有创建 local WBGT，没有创建 `hazard_score`、`risk_score` 或 System A/B coupling 输出。

这不是 B9，不是本地 WBGT 预测，不是风险图，也不是风险评分。它只说明人工执行前所需的本地资产是否可通过根别名找到和引用。实际人工 QGIS 执行仍需要人工确认。

## 路径与提交安全

报告应优先使用根别名与相对路径，不应把本地用户目录当作可移植约定。

`C:/OpenHeat-local/...` 只作为 Git 工作树外的本地执行约定。大体量 raster 与 `svfs.zip` 不应复制进本工作树，也不应提交。

## 下一步

先按 `b85_f2b_manual_remap_checklist.md` 完成人工检查。若状态不是 `READY_AFTER_REMAP`，应先解决仍缺失的文件资产，或由人工创建本地输出根目录，然后重新运行相应门禁。只有人工确认 QGIS/UMEP SOLWEIG 算法可用后，才可进入后续手动执行。
