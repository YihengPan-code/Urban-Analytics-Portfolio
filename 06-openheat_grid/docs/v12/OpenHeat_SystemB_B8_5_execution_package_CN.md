# OpenHeat System B B8.5-F1 执行包说明

生成时间：2026-05-26 23:29:34

## 结论

B8.5-F1 只准备后续 QGIS/SOLWEIG 执行所需的配置、清单、参数契约和日志/聚合契约。当前状态为 `PASS`，但资产就绪状态保持为 `PARTIAL`。本阶段没有运行 QGIS，没有运行 SOLWEIG，没有创建或复制 raster，没有创建本地 WBGT，没有创建 risk map、hazard_score、risk_score，也没有创建 AOI-wide prediction 或 System A/B coupling 输出。本包不代表 B9 AOI-wide inference 获批。

## 范围

- 控制清单：`outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_solweig_run_matrix.csv`
- 计划行数：`480`
- 单元格数量：`24`
- forcing days：`2`
- 小时：`10,12,13,15,16` SGT
- 场景：`base` 和 `overhead_as_canopy`
- 资产就绪状态：`PARTIAL`
- 源 manifest 要求：`solweig_execute_now=no`
- QGIS/SOLWEIG executed：`no`

## 产物

- manifest validation：`outputs/v12_surrogate/b8_5_execution_package/b85_f1_manifest_validation.csv`
- required asset inventory：`outputs/v12_surrogate/b8_5_execution_package/b85_f1_required_asset_inventory.csv`
- QGIS parameter contract：`outputs/v12_surrogate/b8_5_execution_package/b85_f1_qgis_parameter_contract.csv`
- expected run log schema：`outputs/v12_surrogate/b8_5_execution_package/b85_f1_expected_run_log_schema.csv`
- expected aggregation contract：`outputs/v12_surrogate/b8_5_execution_package/b85_f1_expected_aggregation_contract.csv`
- QGIS skeleton：`scripts/qgis/v12_b85_qgis_solweig_execution_SKELETON.py`
- status：`outputs/v12_surrogate/b8_5_execution_package/B8_5_F1_STATUS.md`

## 路径说明

报告和 CSV 中的仓库资产应使用 repo-relative path。原始 SOLWEIG 输出根目录使用本地占位路径 `C:/OpenHeat-local/solweig/b85_f1_tiles`；该路径只表示人工 QGIS 执行时的本地输出位置，不能作为盲目执行命令，也不能把 raster 或 `svfs.zip` 提交到仓库。

## 后续步骤

下一步只能是人工复核后的 QGIS 执行。执行者应使用本包中的 skeleton 和契约，确认 QGIS/UMEP 算法、met forcing 文件、focus-cell mask、raster/SVF 路径和本地输出目录。SOLWEIG 输出仍然只是 Tmrt 派生的局地辐射修饰标签，不能被解释为 WBGT，也不能升级为风险图或本地 WBGT 图。
