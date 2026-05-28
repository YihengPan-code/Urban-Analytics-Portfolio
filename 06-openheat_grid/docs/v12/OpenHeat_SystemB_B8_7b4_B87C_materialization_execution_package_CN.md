# OpenHeat System B B8.7b.4 + B87C 本地物化与执行包说明

## 结论

本 lane 接在 B8.7b.3 之后。B8.7b.3 已经锁定全幅 DSM、基础植被 CDSM、网格、基础全幅 SVF 来源和 v10 overhead 矢量来源，但没有逐单元 SOLWEIG 执行资产。因此 B8.7b.4/B87C 的任务是把这些锁定来源转成 **本地专用** 的逐单元资产计划、真实 3000 行 manifest、QGIS 物化 runner、SOLWEIG runner、续跑策略和 postrun QA 包。

## 本 lane 做什么

- 在 `C:/OpenHeat-local/solweig/b87c_n300` 下建立本地执行根目录。
- 为 150 个新 N300 单元建立本地资产目录。
- 从锁定网格写出本地 `focus_cell.geojson`。
- 从 compact weather CSV 生成本地单小时 UMEP forcing 文本。
- 生成 `b87c_manifest.csv`，共 150 × 2 天 × 5 小时 × 2 场景 = 3000 行。
- 生成 QGIS 专用的 SVF/资产物化 runner 和 SOLWEIG runner。
- 生成 smoke、pilot_5、pilot_20、full_150 批次策略。
- 生成 postrun QA 计划和 compact review packet 脚本。

## 本 lane 不做什么

- 不在 Git worktree 内写入 `.tif`、`.tiff`、`.vrt`、`.asc`、`.img`、`.nc`、`.grib` 或 `svfs.zip`。
- 不把 `data/solweig`、`data/rasters`、`data/archive` 作为本 lane 输出。
- 不在普通 Codex Python 中运行 QGIS、UMEP 或 SOLWEIG。
- 不生成 AOI-wide prediction，不启动 B9。
- 不生成 WBGT、risk、hazard、exposure 或 vulnerability 输出。
- 不把 SOLWEIG Tmrt 转成 WBGT。
- 不声称观测真值，也不声称特征重要性具有因果解释。

## 关键科学边界

base 场景使用建筑 DSM 与现有植被 DSM。`overhead_as_canopy` 场景使用建筑 DSM 与 `max(现有植被 DSM, overhead canopy)`。二者必须分别生成 SOLWEIG 兼容的 SVF 资产；`overhead_as_canopy` 不能复用 base SVF。

B8.7b.3 锁定的全幅 `SkyViewFactor.tif` 只是 base 场景来源，不等于逐 tile 的 `svfs.zip`。如果 UMEP 需要 `svfs.zip`，必须由 QGIS/UMEP runner 在本地目录中生成。

## Tile 约定

本包沿用 v12 N24/N150 SOLWEIG 执行配置中的约定：

- focus cell: 100 m；
- buffer: 100 m；
- 目标 raster resolution: 2 m；
- 预期 tile 宽度: 300 m；
- flat DEM: 本地生成 0 值 tile；
- wall height/aspect: 由 UMEP Wall Height and Aspect 算法生成；
- SVF: 由 UMEP Sky View Factor 算法按场景生成。

## 推荐执行顺序

1. 运行 repo 侧包生成脚本，刷新 manifest、说明和本地 runner 副本。
2. 在 QGIS Desktop Python Console 中运行本地 `v12_b87b4_qgis_svf_materialization_runner_LOCAL.py`。
3. 先保持 `DRY_RUN=True` 检查，再在本地副本中设置 `RUN_ENABLED=True` 和 `DRY_RUN=False`。
4. 物化完成后先运行 `scripts/v12_b87c_manifest_builder.py`，再运行 `scripts/v12_b87c_runner_localizer.py`，刷新 `READY/not_ready` 状态和本地 manifest 副本。
5. 运行 `scripts/v12_b87c_manifest_audit.py`，确认没有 `not_ready` 行。
6. 运行本地 `v12_b87c_qgis_solweig_n300_runner_LOCAL.py`，顺序为 `smoke`、`pilot_5`、`pilot_20`、`full_150`。
7. B87C 完成后运行 `scripts/v12_b87c_postrun_qa.py`，只提交 compact QA 表和说明，不提交 heavy outputs。

## 状态解释

- `B87B4_MATERIALIZATION_COMPLETE_READY_FOR_B87C_RUN`：所有本地资产和 manifest/runner 已就绪。
- `B87B4_PENDING_QGIS_SVF_GENERATION`：非 SVF 资产已就绪，但 `svfs.zip` 仍需 QGIS/UMEP 生成。
- `B87C_PACKAGE_READY_NOT_RUN`：manifest 与 runner 已生成，但尚未执行 SOLWEIG。
- `B87B4_BLOCKED_TILE_SPEC`：tile extent、buffer 或物化约定无法恢复。
- `B87B4_BLOCKED_ASSET_CREATION`：本地资产创建失败。
- `B87B4_DIAGNOSTIC_ONLY`：当前环境只完成了 compact package 和可安全生成的本地轻量资产；后续需要 QGIS runner。

## Git 卫生

本 lane 允许 repo 中出现 compact CSV、Markdown、YAML 和 Python 脚本。所有 heavy raster/vector execution assets 必须留在 `C:/OpenHeat-local/solweig/b87c_n300`。不要 stage 或 commit 本地执行输出、raster、`svfs.zip` 或任何 raw API dump。
