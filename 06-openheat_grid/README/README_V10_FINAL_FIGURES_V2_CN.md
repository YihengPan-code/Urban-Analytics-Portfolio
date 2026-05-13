# OpenHeat v10 final figures/maps package v2

这是针对第一版最终制图输出的重写版本。目标是：

- 色系统一：navy / slate / muted blue / muted purple / muted warm accent；
- 去掉“彩虹式”配色和过度鲜艳的分类色；
- 地图布局更稳，不再让标题、图例、地图互相重叠；
- 不依赖在线底图，保证可复现；
- 解释图改成 highlight map，而不是把全 AOI 涂成五颜六色。

## 新增文件

```text
configs/v10/v10_final_figures_config.v2.json
scripts/figures_v2/v10_figures_style_v2.py
scripts/figures_v2/v10_build_final_interpretation_layer_v2.py
scripts/figures_v2/v10_make_final_maps_v2.py
scripts/figures_v2/v10_make_final_charts_v2.py
scripts/figures_v2/v10_make_workflow_schematic_v2.py
scripts/v10_run_final_figures_pipeline_v2.bat
docs/v10/V10_FINAL_FIGURE_MAP_GUIDE_V2_CN.md
```

## 一键运行

在项目根目录运行：

```bat
scripts\v10_run_final_figures_pipeline_v2.bat
```

输出：

```text
outputs/v10_final_figures_v2/maps/
outputs/v10_final_figures_v2/charts/
outputs/v10_final_figures_v2/v10_final_hotspot_interpretation_table.csv
outputs/v10_final_figures_v2/v10_final_hotspot_interpretation_map.geojson
outputs/v10_final_figures_v2/v10_final_hotspot_interpretation_counts.csv
```

## 需要的输入

默认使用你已经生成的 v10 文件：

```text
data/grid/toa_payoh_grid_v07_features.geojson
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.csv
outputs/v10_gamma_comparison/v10_vs_v08_rank_comparison.csv
outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_rank_comparison.csv
outputs/v10_ranking_audit/v10_old_false_positive_candidates.csv
data/grid/v10/toa_payoh_grid_v10_basic_morphology.csv
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv
data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv
outputs/v10_epsilon_solweig/v10_epsilon_focus_tmrt_summary.csv
outputs/v10_epsilon_solweig/v10_epsilon_base_vs_overhead_tmrt_comparison.csv
```

如果路径不同，修改：

```text
configs/v10/v10_final_figures_config.v2.json
```

## 推荐报告图组

建议最终报告使用：

```text
chart_00_v10_workflow_schematic
map_05_building_density_gain
map_01_v10_gamma_base_hazard
map_03_overhead_fraction
map_04_overhead_sensitivity_rank_shift
map_06_final_hotspot_interpretation
chart_01_epsilon_tmrt_timeseries
chart_02_epsilon_tmrt_delta_bars
chart_03_04_top20_and_morphology_summary
```

## 重要改动

第一版 final hotspot interpretation map 太像全域 categorical land-use map，颜色太多且视觉噪声大。v2 采用 highlight-map 逻辑：

```text
other cells = very light gray
confident / overhead-confounded / DSM-gap corrected / reference = muted highlight colors
```

也就是说，这张图表达的是“解释类别与证据等级”，不是另一个连续 hazard score。
