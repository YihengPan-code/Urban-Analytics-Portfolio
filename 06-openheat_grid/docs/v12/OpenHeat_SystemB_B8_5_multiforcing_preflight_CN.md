# OpenHeat System B B8.5-F0 多强迫预检说明

生成时间：2026-05-26

## 结论

- 状态：`PASS`
- N24 cell 数量：`24`
- N24 来源：`original_retained_n24_cells`
- 计划 SOLWEIG run matrix 行数：`480`
- QGIS / SOLWEIG 是否执行：`no`

## 边界

本文件只用于 B8.5-F0 预检、协议和 manifest 说明。此阶段没有运行 QGIS，没有运行 SOLWEIG，没有创建 raster，没有创建 AOI 全域推理，没有创建局地 WBGT，没有创建 `hazard_score` 或 `risk_score`，也没有创建 System A/B coupling 输出。

System B 当前仍是 SOLWEIG 派生局地辐射修饰标签的候选 surrogate/emulator 工作流。`delta_tmrt_p90_c` 不是 delta WBGT，`m_rad_pct01` 不是风险，B8.5-F0 不批准 B9 AOI-wide inference。

## 科学目的

B8.2/B8.3 显示 `extra_trees` 可作为 N150 单一 forcing setup 下的内部候选模型，但多 forcing 稳定性尚未测试。B8.5-F0 的目标是在 B9 全域推理前，设计一个小规模敏感性运行协议：

- N24 cells
- 2 个 forcing days
- 5 个小时：10、12、13、15、16 SGT
- 2 个场景：`base`、`overhead_as_canopy`
- 共 `24 x 2 x 5 x 2 = 480` 个计划 run

## 已选 forcing days

| forcing_day_id | date | regime_label | n_station_hours | n_ge31_obs | 选择依据 |
| --- | --- | --- | ---: | --- | --- |
| `FD01_high_shortwave_hot_20260507` | 2026-05-07 | `high_shortwave_hot` | 135 | 198 | GE31-rich high-shortwave / hot forcing day；可用 v09 paired station 文件中有 official WBGT GE31 观测支持。 |
| `FD02_humid_hot_cloudy_or_diffuse_20260508` | 2026-05-08 | `humid_hot_cloudy_or_diffuse` | 135 | not_available | 对照日，用于 humidity / cloud / diffuse / radiation diversity；本地 paired station 文件没有可用 GE31 观测，因此不视为 GE31-rich。 |

FD01 是 GE31-rich 的高短波、高热 forcing day。FD02 的作用不是提供第二个 GE31-rich 事件，而是作为湿度、云量、散射辐射和短波辐射结构不同的对照日。

## 后续评估协议

后续若执行 QGIS / SOLWEIG，应按 `b85_f0_solweig_run_matrix.csv` 逐行执行，并在执行后比较不同 forcing day 下的：

- `delta_tmrt_p90_c` 排序相关性
- 按 hour / scenario 分组的 Spearman
- top-k overlap
- `delta_tmrt_p90_c` 符号稳定性
- `m_rad_pct01` 排名稳定性
- cell class 稳定性
- unstable-cell inventory
- forcing-day interaction notes

若这些稳定性证据不足，B9 AOI-wide inference 应继续阻塞。
