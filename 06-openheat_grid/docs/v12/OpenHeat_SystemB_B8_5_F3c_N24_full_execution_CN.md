# OpenHeat System B B8.5-F3c N24 完整执行包中文说明

生成时间：2026-05-27 05:08:25

## 结论

- 决策状态：`N24_STABILITY_REVIEW_READY`
- manifest run count：`480`
- unique cell count：`24`
- 预执行 ready 数量：`480/480`
- postrun 状态：`480/480_EXECUTED_OUTPUTS_VALID`
- raster QA 状态：`PASS`
- stability summary 状态：`PASS`
- 预期本地 run log：`C:/OpenHeat-local/solweig/b85_f3c_n24/run_logs/b85_f3c_n24_qgis_run_log.csv`

## 本轮授权范围

本轮只准备 B8.5-F3c 的 N24 human-controlled runset：24 个 cells、2 个 forcing days、5 个 SGT hours、2 个 scenarios，共 480 次人工控制的 QGIS/SOLWEIG 运行。输出 group 只能使用：

`b85_f3c_n24/<forcing_day_id>/<cell_id>/<scenario>/h<hour>`

预期 `Tmrt_average.tif` 只能位于：

`C:/OpenHeat-local/solweig/b85_f1_tiles/<expected_output_group>/Tmrt_average.tif`

## 边界声明

- Codex/Python 没有运行 QGIS/SOLWEIG。
- preparation lane 没有创建、复制、移动或打开任何 raster。
- preparation lane 没有复制或打开 `svfs.zip`。
- Raster QA 只会在人工执行完成且 postrun validation 通过后读取本地 `Tmrt_average.tif` 内容。
- 不会写出或提交任何 raster、image、GeoTIFF、PNG 或大型数组。
- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 N150。
- 这不是 full AOI。
- 没有进行 Tmrt-to-WBGT conversion。
- 没有创建 AOI-wide prediction、hazard_score、risk_score 或 System A/B coupling 输出。
- 本说明只授权 480-run N24 human-controlled runset。
- N150 / B9 在 N24 execution 和 stability review 通过前仍然 blocked。

## 人工执行方式

仓库中的 QGIS runner 必须保持 `DRY_RUN=True`。如果人工审查后要真正执行，必须把 runner 复制到 `C:/OpenHeat-local/solweig/b85_f3c_n24` 下的本地非 Git 路径，并且只在本地副本中手动改为 `DRY_RUN=False`。真实 SOLWEIG 输出只能写入 `C:/OpenHeat-local/solweig/b85_f1_tiles/...`，run log 只能写入 `C:/OpenHeat-local/solweig/b85_f3c_n24/run_logs/b85_f3c_n24_qgis_run_log.csv`。

QGIS Console wrapper 必须读取本地 runner，使用 `encoding="utf-8-sig"`，显式注入 `__file__ = local runner path`，设置 `sys.argv = [runner]`，并把 `cwd` 切换为 `runner.parent`。安全门必须保留，不能删除。

## 验证方式

pre-execution asset check 使用 F2d/F0 readiness 元数据生成，不打开 raster 内容。postrun validator 不读取 raster 内容；它只检查本地 run log 是否存在、480 个 expected run status 是否为 `success` 或 `skipped_success_existing_output`、预期 `Tmrt_average.tif` 是否存在且文件大小大于 0。若人工尚未执行，validator、raster QA 和 stability summary 会输出 `NOT_RUN_YET`，不会把“未执行”误报为失败。
