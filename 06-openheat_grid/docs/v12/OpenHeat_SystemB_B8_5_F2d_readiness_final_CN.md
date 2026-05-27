# OpenHeat System B B8.5-F2d final readiness 中文说明

生成时间：2026-05-27 02:40:59

## 结论

- 决策状态：`READY_FOR_MANUAL_QGIS`
- 文件资产 ready：`480/480`
- ready_for_manual_qgis：`480/480`
- local output root 状态：`PASS`
- QGIS manual check 状态：`PASS`
- 剩余阻塞项：`none`

## Manifest 检查

- 行数：`480`
- cell 数：`24`
- forcing day 数：`2`
- hour 数：`5`
- scenario 数：`2`

## 边界声明

- 本轮没有运行 QGIS/SOLWEIG。
- 本轮没有创建、复制或打开任何 raster。
- 本轮没有复制或打开 `svfs.zip`。
- 本轮只是 readiness rerun，不是 B9。
- 本轮不是 local WBGT。
- 本轮不是 risk。
- 本轮没有创建 AOI-wide prediction、local WBGT、hazard_score、risk_score 或 System A/B coupling 输出。
- 只有当状态为 `READY_FOR_MANUAL_QGIS` 时，本说明才授权下一步人工 QGIS review。
- 即使是 `READY_FOR_MANUAL_QGIS`，也不是执行；它只是允许进入由人工控制的执行 lane。

## 解释

本轮把 F2b 找回的 tile/SVF/cell geometry 资产通过 `original_project` root alias 重新纳入检查，并把 F2c 生成的 FD02 local met forcing 文件纳入检查。FD02 met forcing 如有 sha256 记录，本轮会对文本文件计算 sha256 并比对；raster 和 `svfs.zip` 只做存在性元数据检查，不读取内容。
