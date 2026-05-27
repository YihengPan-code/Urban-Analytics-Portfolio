# OpenHeat System B B8.5-F2c FD02 met forcing 说明

生成时间：2026-05-27 02:08:09

## 结论

本轮状态为 `GENERATED_LOCAL_ONLY`。目标是为 `FD02_humid_hot_cloudy_or_diffuse_20260508` 生成或恢复 S128 在 2026-05-08 的 10、12、13、15、16 点 SOLWEIG met forcing 文本文件。

- 已通过本地文本校验的 met forcing 文件：`5/5`。
- 模板来源：`b8_worktree_project`，使用 FD01 的 v09 单小时 met forcing 文件推断列顺序、表头和格式。
- 天气来源：`v09_historical_forecast_by_station_hourly`，按 `station_id=S128` 和 SGT 日期/小时匹配。
- FD02 生成后的 projected ready runs：`480/480`。
- 剩余 blocker：`local_output_root_needs_create; qgis_algorithm_manual_check`。

## 安全边界

- 本轮没有运行 QGIS。
- 本轮没有运行 SOLWEIG。
- 本轮没有创建、复制或打开 raster。
- 本轮没有复制或打开 `svfs.zip`。
- 生成的 met forcing 文件只在 `C:/OpenHeat-local/solweig/met_forcing/b85_f2c`，属于 local-only 文件，不能提交到 Git。
- 本轮不是 B9，不生成 AOI-wide prediction。
- 本轮不生成 local WBGT、`hazard_score`、`risk_score`，也不生成 System A/B coupling 输出。

## 文件命名修正

上游记录里可能出现 `v09_met_foring_2026_05_08_S128_h16.txt` 的拼写错误。本轮统一规范为 `v09_met_forcing_2026_05_08_S128_h16.txt`，并在 manifest notes 中记录该修正。

## 方法说明

脚本先从既有 FD01 v09 met forcing 文件读取 UMEP 表头、列顺序、数据行数量和格式。只有模板 schema 可用、且 FD02/S128/目标小时天气行完整时，才写出本地 met forcing 文件。每个单小时文件保留 FD01 模板的两行相同数据行约定，用于避免旧版 SOLWEIG 对单行 metdata 的维度问题。

天气变量来自站点小时天气源，不使用 official WBGT target 来生成 forcing 字段；当前模板也不包含 WBGT 输入列。因此这里不能被解释为局地 WBGT 校准，也不能被解释为风险模型。

## 下一步

下一步是用本轮 `b85_f2c_next_remap_roots.yaml` 中的 local met root 重新跑 F2b/F2a readiness，同时准备本地 SOLWEIG output root，并在人工环境中做 QGIS/UMEP algorithm manual check。只有这些检查通过后，才进入后续人工 QGIS/SOLWEIG 执行。
