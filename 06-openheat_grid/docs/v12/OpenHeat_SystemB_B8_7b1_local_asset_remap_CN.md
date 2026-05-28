# OpenHeat System B B8.7b.1 本地资产重映射就绪性说明

## 结论

- 状态：`B87B1_WAITING_LOCAL_ROOTS`
- 手动本地根目录输入：`yes`
- 已解析根目录数量：`12`
- 新候选单元数量：`150`
- cell tile folder 解析数量：`0`
- SVF/DSM/CDSM/DEM/landcover 就绪数量：`0/0/0/0/0`
- met forcing 就绪：`150/150`
- output root 就绪：`150/150`
- AOI / B9：`AOI_PREFLIGHT_BLOCKED / B9_BLOCKED`

## 1. 为什么 B8.7b.1 接在 B8.7b 后面

B8.7b 已经确认 N300 v4 设计、300 个唯一单元索引和 3000 行预览计划成立，但 150 个新候选单元没有本地 cell asset 映射。因此 B8.7b.1 只处理本地根目录和资产路径重映射就绪性，不创建真正执行包。

## 2. B8.7b 已经通过的内容

B8.7b 已通过：150 个新候选、150 个既有 N150 标签单元、300 个唯一 cell、3000 个预览运行、forcing 设计来自 B8.5-F5。`b87b_run_plan_preview.csv` 仍然是 preview，不是 execution manifest。

## 3. 本地根目录发现

手动本地根目录输入为 `yes`；元数据可解析根目录数量为 `12`；必需根目录缺口为 `0`。所有检查只使用 `Path.exists`、`Path.is_dir`、`Path.is_file`、文件大小和文件名 glob 元数据。

## 4. 手动本地根目录模板状态

已写出 `b87b1_manual_local_root_template.csv` 和 `b87b1_manual_local_root_instructions.md`。如果当前 Codex 环境无法看到本地根目录，请在 `outputs/v12_surrogate/b8_7b1_local_asset_remap/manual_inputs/b87b1_manual_local_roots.csv` 填写手动 CSV 后重新运行。

## 5. 资产路径模式登记

`b87b1_asset_pattern_registry.csv` 只登记候选模式：cell tile folder、SVF、DSM、CDSM、DEM、landcover、met forcing、QGIS manual check 和 output root。它不创建文件、不创建目录、不复制资产。

## 6. Cell 资产元数据审计

已对 `150` 个新候选单元做元数据审计。cell tile folder 解析数量为 `0`。

## 7. 150 个新候选的解析就绪性

ready cells 为 `0/150`。SVF/DSM/CDSM/DEM/landcover 就绪数量为 `0/0/0/0/0`。

## 8. 缺失 / 歧义资产登记

waiting=900; missing=0; ambiguous=0

## 9. B8.7c 前置清单

`b87b1_b87c_prerequisite_checklist.csv` 明确保留 B8.7c manifest / runner gate。只有本地资产映射解决，并且用户明确授权未来 B8.7c lane 后，才可以创建真正 manifest 或 runner。

## 10. 就绪性决策

最终决策为 `B87B1_WAITING_LOCAL_ROOTS`。建议下一 lane：`B8.7b.2_local_asset_fix`。

## 11. 如果状态是 WAITING_LOCAL_ROOTS，用户需要做什么

请只填写手动本地根目录 CSV，使用 `use`、`missing`、`unknown` 或 `not_applicable` 标记。不要把 raster、`svfs.zip`、本地 run log 或 SOLWEIG 输出复制进 Git。填写后重新运行 B8.7b.1。

## 12. 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk / hazard score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有 raster read/write/copy/open。
- 没有 QGIS / SOLWEIG execution。
- 没有 run-ready N300 manifest。
- 没有 QGIS runner。
- 没有 local runner。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
