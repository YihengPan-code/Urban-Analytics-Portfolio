# OpenHeat System B B87D N300 标签整合说明

生成时间：2026-05-28 13:19:23

状态：`B87D_N300_LABEL_INTEGRATION_PASS`

本阶段只把已经完成的 B87C 本地 SOLWEIG `Tmrt_average.tif` 输出读取为紧凑统计表，并与既有 F5 N150 标签整合为 N300 标签表。

## 提取约定

采用最终 F5 约定：`F5_FULL_150X150_VALID_NON_NODATA_TMRT_AVERAGE_TIF_V1`。统计对象是完整 150x150 的 2m tile，像元筛选为有限值且非 nodata；不裁剪 100m focus mask，不写入任何 raster。

## 标签方向

`delta_tmrt_* = overhead_as_canopy - base`。负值通常表示 overhead-as-canopy 情景下模拟 Tmrt 较低，但这不是 WBGT 降温、不是观测真值、不是风险或危害地图。

## 输出

- `b87d_b87c_tmrt_stats_by_run.csv`：逐运行 Tmrt 统计。
- `b87d_b87c_pairwise_delta_by_cell_hour.csv`：B87C new150 配对标签。
- `b87d_n300_pairwise_delta_by_cell_hour.csv`：F5 N150 + B87C new150 整合标签。

## 边界

本阶段不运行 QGIS/SOLWEIG，不复制/移动/写入 raster，不生成 AOI/B9 推理，不做 WBGT 转换，不生成 hazard/risk/exposure/vulnerability 输出，也不提出因果特征重要性结论。
