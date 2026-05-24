# OpenHeat v10 final figures / maps package v3

这版是针对你本轮反馈做的 **v3 修订包**，重点修三件事：

1. **地图要素位置统一**
   - 比例尺：右下角
   - 指北针：右上角

2. **地图加入卫星底图**
   - 使用 `contextily` + `Esri.WorldImagery`
   - 主题图层采用轻微透明处理，保留卫星空间语境
   - 如果本机无网络或未安装 `contextily`，脚本会自动退回无底图版本，不会直接报废

3. **chart_01 重新排版**
   - 不再把 5 个 cell 的 base / overhead 全堆在一张拥挤折线图里
   - 改成 **5 行 small multiples**
   - 每行一个 focus cell，右上角单独标注 mean ΔTmrt
   - 显著减少遮挡、压缩、变形、图例冲突

---

## 新增/主要文件

- `configs/v10/v10_final_figures_config.v3.json`
- `scripts/figures_v3/v10_figures_style_v3.py`
- `scripts/figures_v3/v10_make_final_maps_v3.py`
- `scripts/figures_v3/v10_make_final_charts_v3.py`
- `scripts/figures_v3/v10_make_workflow_schematic_v3.py`
- `scripts/figures_v3/v10_build_final_interpretation_layer_v3.py`
- `scripts/v10_run_final_figures_pipeline_v3.bat`

---

## 运行前建议

如果你想启用卫星底图，建议先安装：

```bash
pip install contextily xyzservices
```

如果不装，也可以跑，只是输出为无底图版本。

---

## 运行方式

在项目根目录执行：

```bat
scripts\v10_run_final_figures_pipeline_v3.bat
```

输出目录：

```text
outputs/v10_final_figures_v3/
```

---

## 你这轮重点检查哪些图

请优先检查：

- `maps/map_01_v10_gamma_base_hazard.png`
- `maps/map_03_overhead_fraction.png`
- `maps/map_04_overhead_sensitivity_rank_shift.png`
- `maps/map_06_final_hotspot_interpretation.png`
- `charts/chart_01_epsilon_tmrt_timeseries.png`

尤其确认：

- 比例尺是否位于右下角
- 指北针是否位于右上角
- 卫星底图是否成功加载
- 主题层透明度是否合适
- chart_01 是否已经消除遮挡与压缩问题
