# OpenHeat System B B8.5-F3a 栅格内容 QA 中文说明

生成时间：2026-05-27 03:37:00

## 结论

- 决策状态：`MICRO_BATCH_RASTER_QA_PASS`
- 成功打开栅格：`4/4`
- 对齐状态：`PASS`
- 每次运行 p90 范围：`57.57-61.60 C`
- base-vs-overhead_as_canopy delta 摘要：FD01 mean -0.663888 C (overhead_neutral); FD02 mean -0.598506 C (overhead_neutral)
- FD02-vs-FD01 对比摘要：base mean -2.762285 C, p90 -0.404498 C (plausible_forcing_difference); overhead_as_canopy mean -2.696902 C, p90 -0.382623 C (plausible_forcing_difference)
- 下一步建议：`F3b one-cell full slice`

## 1. 为什么这是 F3a POST 之后的步骤

F3a POST 已经确认 4/4 run log success，并确认 4/4 预期 `Tmrt_average.tif` 文件存在；但上一阶段没有打开 raster 内容。本 QA lane 只补上四个本地栅格的紧凑内容检查。

## 2. 读取了什么，没有写什么

本脚本只读取 manifest 中声明的四个本地 `Tmrt_average.tif`。它没有运行 QGIS/SOLWEIG，没有复制或打开 `svfs.zip`，没有创建、复制、移动任何 raster，也没有写 GeoTIFF、PNG、裁剪栅格或大型数组输出。

## 3. Raster inventory 摘要

| run_id | forcing_day_id | scenario | exists | file_size_bytes | crs | width | height | opened_for_qa |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13 | FD01_high_shortwave_hot_20260507 | base | yes | 90658 | EPSG:3414 | 150 | 150 | yes |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13 | FD01_high_shortwave_hot_20260507 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150 | 150 | yes |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13 | FD02_humid_hot_cloudy_or_diffuse_20260508 | base | yes | 90658 | EPSG:3414 | 150 | 150 | yes |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13 | FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150 | 150 | yes |

## 4. 每次运行 Tmrt 统计

| run_id | scenario | valid_pixel_count | nodata_fraction | mean_c | p50_c | p90_c | p95_c | max_c | sanity_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13 | base | 22500 | 0.000000 | 50.766133 | 57.573914 | 61.598778 | 62.174397 | 62.579208 | PASS |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13 | overhead_as_canopy | 22500 | 0.000000 | 50.102245 | 57.132648 | 61.245582 | 61.816008 | 62.564804 | PASS |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13 | base | 22500 | 0.000000 | 48.003849 | 53.093161 | 58.075171 | 58.936028 | 59.546646 | PASS |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13 | overhead_as_canopy | 22500 | 0.000000 | 47.405343 | 52.669868 | 57.567973 | 58.391335 | 59.527508 | PASS |

## 5. Base-vs-overhead_as_canopy delta

这里的 delta 定义为 `overhead_as_canopy - base`。它只是 overhead-as-canopy sensitivity，不代表精确的真实高架/连廊物理效应。

| forcing_day_id | mean_delta_c | p50_delta_c | p90_delta_c | p95_delta_c | min_delta_c | max_delta_c | delta_direction_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FD01_high_shortwave_hot_20260507 | -0.663888 | 0.000000 | 0.000000 | 0.000000 | -26.959572 | 0.057655 | overhead_neutral |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | -0.598506 | 0.000000 | 0.000000 | 0.000000 | -24.135750 | 0.013489 | overhead_neutral |

## 6. FD01-vs-FD02 forcing-day 对比

| scenario | contrast_direction | mean_difference_c | p90_difference_c | valid_overlap_pixels | qualitative_status |
| --- | --- | --- | --- | --- | --- |
| base | FD02_minus_FD01 | -2.762285 | -0.404498 | 22500 | plausible_forcing_difference |
| overhead_as_canopy | FD02_minus_FD01 | -2.696902 | -0.382623 | 22500 | plausible_forcing_difference |

## 7. 对齐、nodata 与 sanity

| check_name | status | value | details |
| --- | --- | --- | --- |
| all_4_rasters_have_same_shape | PASS | 150x150 | Shape comparison uses height x width. |
| all_4_rasters_have_same_crs | PASS | EPSG:3414 | CRS must match before pixelwise deltas. |
| all_4_rasters_have_same_transform | PASS | (29300.0, 2.0, 0.0, 34500.0, 0.0, -2.0) | Transform must match before pixelwise deltas. |
| all_4_rasters_have_same_nodata_dtype | PASS | -9999.0/float32 | Nodata and dtype should be consistent across the micro-batch. |
| expected_pixel_count_consistency | PASS | 22500 | Pixel count should be identical for the four local rasters. |
| output_path_outside_git_worktree | PASS | C:/OpenHeat-local/solweig/b85_f1_tiles | Local SOLWEIG raster paths should remain outside the Git worktree and under local_output_root. |
| no_raster_output_written | PASS | False | QA writes only CSV/Markdown control artifacts. |

## 8. Micro-batch content QA 是否通过

当前判定为 `MICRO_BATCH_RASTER_QA_PASS`。若为 PASS，则四个栅格均可打开、统计值在合理范围内、栅格对齐通过，且 base-vs-overhead_as_canopy delta 未显示 warming/suspicious 信号。

## 9. 下一步建议

建议下一步：`F3b one-cell full slice`。

## 10. Claim boundaries

- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 full multi-forcing stability。
- 没有进行 Tmrt-to-WBGT conversion。
- 没有提交或写出任何 raster。
- 本结果只服务于 4-run micro-batch 内容 QA。
