# OpenHeat System B N150 SOLWEIG manifest 计划（B6）

## 运行矩阵含义

完整 N150 期望矩阵包含 150 个格网、2 个情景和 5 个小时，因此为 1500 行。由于 N24 已经完成，B7 未来只需要执行 126 个新增格网、2 个情景和 5 个小时，即 1260 行。

## 已创建的 manifest

- `configs/v12/v12_solweig_n150_full_run_matrix.csv`：完整 N150 期望标签矩阵，包含 N24 复用行和新增待执行行。
- `configs/v12/v12_solweig_n150_new_run_matrix.csv`：B7 应执行的新运行矩阵，排除已完成 N24 和 B2.2 replaced-out cells。
- `configs/v12/v12_solweig_n150_new_base_manifest.csv`：新增 base 情景 630 行。
- `configs/v12/v12_solweig_n150_new_overhead_manifest.csv`：新增 overhead_as_canopy 情景 630 行。

## B7 执行边界

manifest 只描述未来 SOLWEIG 运行计划；B6 本身不运行 QGIS、不运行 SOLWEIG、不读取 raster。所有预期 raw output 路径均标记 `do_not_commit_raw_output=true`，raw 栅格输出仍应保持未提交。

## 与 B5 目标族的关系

每一行 manifest 都携带 `tmrt_p90_c`、`delta_tmrt_p90_c`、`m_rad_pct01` 的 B5 目标族标识，并把未来 reference domain 标记为 `n150_training_future`。这只是未来标签聚合与归一化的契约，不是最终地图、风险分数或 WBGT 产品。
