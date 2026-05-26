# OpenHeat System B B8.5-F2a 本地资产就绪性说明

生成时间：2026-05-26 23:52:20

## 结论

本次门禁状态为 `PARTIAL_ASSETS_MISSING`。就绪运行数为 `0/480`。

缺失或需要人工确认的资产类别如下：

- `cell_geometry=24`
- `local_output_root=1`
- `met_forcing_file=5`
- `qgis_algorithm_manual_check=1`
- `raster_tile=145`
- `svf_zip=48`

本地原始输出根目录检查状态为 `NEEDS_CREATE`。QGIS/SOLWEIG executed = `no`。

## 范围边界

本次工作只是 B8.5-F2a 本地资产就绪性与 dry-run 规划门禁。QGIS 没有运行，SOLWEIG 没有运行，没有创建或复制任何 raster，没有创建或复制 `svfs.zip`，没有创建 AOI-wide prediction，没有创建 local WBGT，没有创建 `hazard_score` 或 `risk_score`，也没有创建 System A/B coupling 输出。

这不是 B9。它不是本地 WBGT 预测，也不是风险图或风险评分。SOLWEIG 相关路径只用于检查人工执行前的本地资产是否足够，不代表 Tmrt 等于 WBGT，也不代表风险已经建模完成。

## 判读规则

只有当状态为 `READY_FOR_MANUAL_QGIS` 时，下一步才可以进入人工复核后的 QGIS 执行。若状态为 `PARTIAL_ASSETS_MISSING`，必须先补齐或人工确认缺失资产，再重新运行本门禁。若状态为 `BLOCKED`，必须先修复 manifest、skeleton 或本地输出根目录安全问题。

## 当前缺口与人工检查

缺失或需要人工确认的资产类别摘要：`cell_geometry=24; local_output_root=1; met_forcing_file=5; qgis_algorithm_manual_check=1; raster_tile=145; svf_zip=48`。

具体缺失路径和人工检查动作见：

- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_missing_assets.csv`
- `outputs/v12_surrogate/b8_5_f2_asset_readiness/b85_f2_manual_execution_checklist.md`

本地输出根目录只允许作为 Git 工作树外的人工 QGIS 输出位置。若检查结果为 `NEEDS_CREATE`，应由人工在本地创建；本次文档修复不会创建该目录，也不会写入 SOLWEIG raster 输出。

## 下一步建议

在人工 QGIS 执行前，先解决本地缺失资产：`cell_geometry=24; local_output_root=1; met_forcing_file=5; qgis_algorithm_manual_check=1; raster_tile=145; svf_zip=48`。本地输出根目录状态仍为 `NEEDS_CREATE`。

Manual QGIS execution can proceed only after readiness is `READY_FOR_MANUAL_QGIS`。
