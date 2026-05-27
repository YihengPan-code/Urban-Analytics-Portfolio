# OpenHeat System B B8.5-F3a 微批次执行包中文说明

生成时间：2026-05-27 03:04:59

## 结论

- 决策状态：`READY_FOR_HUMAN_MICROBATCH`
- 选择 cell_id：`TP_0037`
- 微批次数量：`4`
- 预执行 ready 数量：`4/4`
- postrun 状态：`NOT_RUN_YET`
- 预期本地 run log：`C:/OpenHeat-local/solweig/b85_f3a_microbatch/run_logs/b85_f3a_microbatch_qgis_run_log.csv`

## 微批次设计

本轮只准备 4 个由人工控制的 QGIS/SOLWEIG smoke test：

- forcing day：`FD01_high_shortwave_hot_20260507` 与 `FD02_humid_hot_cloudy_or_diffuse_20260508`
- hour_sgt：`13`
- scenario：`base` 与 `overhead_as_canopy`
- 输出根目录只能是：`C:/OpenHeat-local/solweig/b85_f1_tiles`

## 边界声明

- Codex/Python 没有运行 QGIS/SOLWEIG。
- 本 lane 没有创建、复制或打开任何 raster。
- 本 lane 没有复制或打开 `svfs.zip`。
- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 本 lane 没有创建 AOI-wide prediction、local WBGT、hazard_score、risk_score 或 System A/B coupling 输出。
- 本说明只授权 4-run human-controlled micro-batch。
- Full 480 execution 在 micro-batch validation 通过前仍然 blocked。

## 执行方式

仓库中的 QGIS runner 默认 `DRY_RUN=True`。如果人工审查后要真正执行，必须把 runner 复制到本地非 Git 路径，并且只在本地副本中手动改为 `DRY_RUN=False`。真实 SOLWEIG 输出只能写入 `C:/OpenHeat-local/solweig/b85_f1_tiles/...`，run log 只能写入 `C:/OpenHeat-local/solweig/b85_f3a_microbatch/run_logs/...`。

## 验证方式

准备阶段只检查 F2d readiness 元数据并写出 manifest、pre-execution asset check、run-log schema 和人工执行说明。postrun validator 不读取 raster 内容；它只检查本地 run log 状态、预期输出路径是否存在、以及文件大小是否大于 0。若人工尚未执行，validator 会输出 `NOT_RUN_YET`，不会把“未执行”误报为失败。
