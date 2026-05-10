# V10 final figure / map guide v3（中文）

## 本次修订目标

根据用户反馈，v3 主要解决以下问题：

1. 地图图面语言统一：比例尺固定右下，指北针固定右上。
2. 在底层加入 Toa Payoh 卫星底图，提升空间直觉。
3. 主题图层做轻度透明化，避免完全遮蔽地表纹理。
4. `chart_01_epsilon_tmrt_timeseries` 重构为 small-multiples，以避免图例、标题和曲线相互遮挡。

## 地图设计逻辑

- basemap: `Esri.WorldImagery`
- overlay alpha: `0.68`
- AOI outline: 深海军蓝
- numeric maps: muted single-hue / diverging palette
- interpretation map: category highlight over imagery

## 如果卫星底图没有显示

请检查：

1. Python 环境是否安装：
   - `contextily`
   - `xyzservices`
2. 是否有网络连接
3. 防火墙是否阻止瓦片请求

脚本已经做了 fallback：如果底图加载失败，会保留无底图制图能力。

## chart_01 的新结构

- 每个 focus cell 一行
- 同一行内比较 `base` 与 `overhead`
- 每行右上角显示 mean ΔTmrt
- 共享 y 范围，便于横向比较

## 推荐最终图组

建议最终报告优先使用：

1. `map_01_v10_gamma_base_hazard`
2. `map_03_overhead_fraction`
3. `map_04_overhead_sensitivity_rank_shift`
4. `map_06_final_hotspot_interpretation`
5. `chart_01_epsilon_tmrt_timeseries`
6. `chart_02_epsilon_tmrt_delta_bars`
7. `chart_03_04_top20_and_morphology_summary`
