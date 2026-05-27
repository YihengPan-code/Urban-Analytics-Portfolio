# OpenHeat System B B8.5-F3b 单网格完整切片执行包中文说明

生成时间：2026-05-27 03:54:04

## 结论

- 决策状态：`READY_FOR_HUMAN_ONECELL_SLICE`
- cell_id：`TP_0037`
- manifest run count：`20`
- 预执行 ready 数量：`20/20`
- postrun 状态：`NOT_RUN_YET`
- raster QA 状态：`NOT_RUN_YET`
- 预期本地 run log：`C:/OpenHeat-local/solweig/b85_f3b_onecell/run_logs/b85_f3b_onecell_qgis_run_log.csv`

## 本轮授权范围

本轮只准备 TP_0037 的 one-cell full slice，组合为 2 个 forcing days、5 个 SGT 小时、2 个 scenarios，共 20 次人工控制的 QGIS/SOLWEIG 运行。

- forcing days：`FD01_high_shortwave_hot_20260507` 与 `FD02_humid_hot_cloudy_or_diffuse_20260508`
- hours_sgt：`10, 12, 13, 15, 16`
- scenarios：`base` 与 `overhead_as_canopy`
- 输出 group 前缀：`b85_f3b_onecell`

## 边界声明

- Codex/Python 没有运行 QGIS/SOLWEIG。
- preparation lane 没有创建、复制、移动或打开任何 raster。
- preparation lane 没有复制或打开 `svfs.zip`。
- Raster QA 只会在人工执行完成且 postrun validation 通过后读取本地 `Tmrt_average.tif` 内容。
- 不会写出或提交任何 raster、image、GeoTIFF、PNG 或大型数组。
- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 full 480。
- 没有进行 Tmrt-to-WBGT conversion。
- 没有创建 AOI-wide prediction、hazard_score、risk_score 或 System A/B coupling 输出。
- 本说明只授权 20-run one-cell human-controlled slice。
- Full 480 在 one-cell full slice 通过前仍然 blocked。

## 人工执行方式

仓库中的 QGIS runner 必须保持 `DRY_RUN=True`。如果人工审查后要真正执行，必须把 runner 复制到 `C:/OpenHeat-local/solweig/b85_f3b_onecell` 下的本地非 Git 路径，并且只在本地副本中手动改为 `DRY_RUN=False`。真实 SOLWEIG 输出只能写入 `C:/OpenHeat-local/solweig/b85_f1_tiles/...`，run log 只能写入 `C:/OpenHeat-local/solweig/b85_f3b_onecell/run_logs/b85_f3b_onecell_qgis_run_log.csv`。

## 验证方式

pre-execution asset check 使用 F2d/F0 readiness 元数据生成，不打开 raster 内容。postrun validator 不读取 raster 内容；它只检查本地 run log 是否存在、20 个 run 是否为 success、预期 `Tmrt_average.tif` 是否存在且文件大小大于 0。若人工尚未执行，validator 和 raster QA 会输出 `NOT_RUN_YET`，不会把“未执行”误报为失败。
