# OpenHeat System B B8.7b N300 执行预检说明

## 结论

- B8.7b 状态：`B87B_PRECHECK_NEEDS_LOCAL_ASSET_REMAP`
- N300 v4 新候选数：`150`
- 既有 N150 标签数：`150`
- N300 唯一单元总数：`300`
- 预计新增运行数：`3000`
- AOI / B9：`AOI_PREFLIGHT_BLOCKED / B9_BLOCKED`

## 1. 为什么 B8.7b 接在 B8.6g3 后面

B8.6g3 已经把 N300 v4 的来源复核 caveat 收口，并确认 150 个新候选与既有 N150 标签集没有重叠、没有重复。connected shade corridor、完整 pedestrian network 和 tree/building interaction 的真矢量缺口仍然阻断 AOI / B9。因此 B8.7b 只做未来执行包预检，不创建真实执行包。

## 2. N300 v4 设计验证

本轮验证确认 v4 仍为 150 行，新候选没有重复 cell_id，也没有与既有 N150 标签单元重叠。TP_0103、TP_0104、TP_0464、TP_0159、TP_0519 的 caveat 已随设计携带；TP_0830、TP_0858、TP_0943 仍不在 v4 设计中。

## 3. N150 + 新候选 = N300 样本索引

`b87b_n300_total_sample_index.csv` 合并既有 labelled N150 与 B8.6g3 新候选，得到 `300` 个唯一 cell。该表是样本索引，不是 SOLWEIG manifest。

## 4. 预计运行数

2 forcing days x 5 hours x 2 scenarios = 3000 additional preview runs。因此未来新增 150 个候选若按 F5 设计执行，预计为 `3000` 个 SOLWEIG 运行。

## 5. forcing 设计

forcing 设计来自 B8.5-F5：两个 forcing day、五个 SGT 小时、两个情景（base 与 overhead_as_canopy）。B8.7b 只审计该设计，不强行改写。

## 6. 资产 readiness

150 new candidate cells audited; 150 have no prior local cell-asset mapping and require future local asset remap; no raster contents opened.

## 7. path remap

10 path/remap rows; 4 unresolved or placeholder-only local-audit rows.

## 8. pre-manifest schema preview

`b87b_pre_manifest_schema_preview.csv` 只是 schema preview。`b87b_run_plan_preview.csv` 的每一行都标记为 `precheck_only_not_execution_manifest=true`、`not_run_ready=true`、`no_qgis_solweig_execution=true`，不是可执行 manifest。

## 9. batch / resume / failure 策略

预览建议 future lane 使用 smoke、pilot、production chunk 和 full_new_n150 分组；resume 需要同时检查 run log 与预期输出 metadata；失败应按 cell / forcing day / hour / scenario 隔离。B8.7b 不创建 runner。

## 10. runtime / storage 估计

Runtime remains unknown because prior local logs are not reliable enough。Tmrt-only storage estimate 259.37 MB。若本地日志呈现亚秒级或缓存式耗时，则不能当作真实物理运行耗时。

## 11. Git hygiene

本轮创建了 no-raster-commit guard，检查 `.tif/.tiff/.vrt/.asc/.img/.nc/.grib`、`svfs.zip`、`data/solweig`、`data/rasters`、`data/archive`、hourly forecast CSV、AOI/B9/WBGT/risk/hazard 输出、execution manifest、QGIS runner 和 local runner。没有 stage，没有 commit。

## 12. readiness decision

最终 decision 为 `B87B_PRECHECK_NEEDS_LOCAL_ASSET_REMAP`。当前主要限制是新 150 个候选的本地 cell asset / path remap 仍需未来 B8.7c 明确授权后处理。

## 13. B8.7c 下一步

B8.7c N300 execution package only after explicit authorization, starting with local asset remap; B8.6g4 external-vector acquisition remains required before AOI/B9。B8.7c 只有在用户明确授权后，才可以创建真实 manifest 或 local-only QGIS runner，并且必须保留 no-raster-commit 与 local-only 边界。

## 14. 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk / hazard score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有 raster read/write/copy。
- 没有 QGIS / SOLWEIG execution。
- 没有 run-ready N300 manifest。
- 没有 QGIS runner。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
