# OpenHeat System B B8.5-F5 N150 multi-forcing 执行包中文说明

生成时间：2026-05-27 17:45:04

## 1. 为什么 F5 跟在 B8.6 后面

B8.5-F4 已通过 N24 decision matrix，并允许在 precheck 后进行 N150 controlled execution。B8.6 找到一个 weak but real 的 N150 single-forcing surrogate baseline，但也明确指出：现有 N150 label 只有 single-forcing，不能支持 promotion 或 B9。因此 F5 的任务是准备 N150 multi-forcing 的 human-execution package，而不是训练 surrogate、不是生成 B9，也不是做 risk。

## 2. Manifest 定义与数量

- cells：150
- forcing days：2
- hours SGT：5（10、12、13、15、16）
- scenarios：2（base、overhead_as_canopy）
- expected run count：3000
- manifest 状态：`N150_MULTIFORCING_STABILITY_REVIEW_READY`
- pre-execution ready count：`3000/3000`
- local run log：`C:/OpenHeat-local/solweig/b85_f5_n150/run_logs/b85_f5_n150_qgis_run_log.csv`

输出 group 只能使用：

`b85_f5_n150/<forcing_day_id>/<cell_id>/<scenario>/h<hour>`

预期 `Tmrt_average.tif` 只能位于：

`C:/OpenHeat-local/solweig/b85_f1_tiles/<expected_output_group>/Tmrt_average.tif`

## 3. Pre-execution readiness

pre-execution asset check 对每个 run 记录 `cell_geometry_ready`、`raster_tiles_ready`、`svf_ready`、`met_forcing_ready`、`output_root_ready`、`qgis_manual_check_status`、`expected_output_path_outside_git`、`run_ready` 和 `blockers`。本检查只做路径存在性检查，不打开 raster 内容，也不打开 `svfs.zip`。

## 4. Runner safety / resume / fail-safe

仓库中的 runner 必须保持 `DRY_RUN=True`。真实执行只能发生在 `C:/OpenHeat-local/solweig/b85_f5_n150` 下的 local-only copy 中，并且只允许人工在本地副本中把 `DRY_RUN=False`。Runner 会拒绝非 3000-row manifest、非 150-cell manifest、forcing day/hour/scenario 不匹配、从 Git worktree 真实执行、或输出路径不在 `C:/OpenHeat-local/solweig/b85_f1_tiles` 下。Resume 会跳过已有 success run log 且 expected output 存在的 rows，并且 fail-safe 会按配置停止。

## 5. Manual QGIS execution

QGIS Console wrapper 必须读取本地 runner，使用 `encoding="utf-8-sig"`，显式注入 `__file__`，设置 `sys.argv=[runner]`，并把 `cwd` 切换到 `runner.parent`。本地 runner 应写成 UTF-8 without BOM。安全门不能删除。

## 6. Postrun / raster / label / stability scripts

- postrun 状态：`3000/3000_EXECUTED_OUTPUTS_VALID`
- raster QA 状态：`PASS`
- label merge 状态：`PASS`
- stability 状态：`PASS`

人工尚未执行时，这些脚本应输出 `NOT_RUN_YET` 或 `PREPARED`，不能把“尚未执行”误报为失败。postrun validator 不读取 raster 内容；raster QA 只在 postrun 通过后读取 3000 个 local `Tmrt_average.tif`，并且只写 compact CSV。

## 7. F5 可以解锁什么

如果 3000/3000 execution、raster QA、label merge 和 stability summary 都通过，F5 可以为后续 surrogate promotion review 提供 N150 forcing-day stability evidence。它只能支持后续审查，不自动授权 B9。

## 8. F5 不证明什么

- 不证明 local WBGT。
- 不证明 risk。
- 不证明 observed truth。
- 不证明 causal feature importance。
- 不证明 AOI-wide prediction。
- 不证明 B9 readiness。
- 不把 Tmrt 转成 WBGT。

## 9. Claim boundaries

- not B9
- not local WBGT
- not risk
- not observed truth
- not causal feature importance
- no raster committed
- no Tmrt-to-WBGT conversion
- no hazard_score / risk_score / System A-B coupling
