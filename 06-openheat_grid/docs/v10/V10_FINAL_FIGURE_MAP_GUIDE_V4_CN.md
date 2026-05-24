# V10 final figure / map guide v4

## v4 修改目的

- 修复 workflow schematic 的文字与编号 badge 重叠。
- 修复 contextily basemap 的 `zoom=None` bug。
- 保留 chart_01 的上一版单图折线布局。
- 保持地图：卫星底图 + 半透明 thematic layer + 右上指北针 + 右下比例尺。

## 推荐检查顺序

1. `charts/chart_00_v10_workflow_schematic.png`
2. `maps/map_01_v10_gamma_base_hazard.png`
3. `maps/map_03_overhead_fraction.png`
4. `maps/map_04_overhead_sensitivity_rank_shift.png`
5. `maps/map_06_final_hotspot_interpretation.png`
6. `charts/chart_01_epsilon_tmrt_timeseries.png`

## libpng iCCP warning

这类 warning 多来自在线卫星瓦片的色彩 profile，不影响地图结果。若底图能正常显示，可忽略。
