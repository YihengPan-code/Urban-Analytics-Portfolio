# V10 final figure/map guide v2

## 设计原则

1. **统一色系**：全部图使用 navy、slate、muted blue、muted purple、warm accent。避免彩虹图。
2. **不依赖底图**：地图不拉在线 tile，保证论文和归档可复现。
3. **地图留白充足**：标题、图例、比例尺、北箭头不与地图重叠。
4. **解释图是 highlight map**：不是每个 cell 都强调，而是突出最终证据类别。
5. **PNG + SVG 双输出**：PNG 直接放报告；SVG 可用于后续 Illustrator / PowerPoint 精修。

## 运行

```bat
scripts\v10_run_final_figures_pipeline_v2.bat
```

## 输出文件说明

### Maps

- `map_01_v10_gamma_base_hazard`: reviewed DSM + UMEP morphology 的 base hazard。
- `map_02_v08_to_v10_rank_shift`: v08 到 v10-gamma 的 rank shift。
- `map_03_overhead_fraction`: overhead infrastructure fraction。
- `map_04_overhead_sensitivity_rank_shift`: v10 base 到 overhead sensitivity 的 rank shift。
- `map_05_building_density_gain`: reviewed DSM 后 building density gain。
- `map_06_final_hotspot_interpretation`: confident / caveated hotspot interpretation。

### Charts

- `chart_00_v10_workflow_schematic`: v10 audit → correct → validate workflow。
- `chart_01_epsilon_tmrt_timeseries`: v10-epsilon SOLWEIG Tmrt time series。
- `chart_02_epsilon_tmrt_delta_bars`: overhead scenario Tmrt delta。
- `chart_03_04_top20_and_morphology_summary`: top20 overlap + morphology summary。

## 需要人工检查

跑完后请检查：

```text
TP_0565 / TP_0986 是否被标为 confident_hotspot
TP_0088 / TP_0916 是否被标为 overhead_confounded
TP_0433 是否被标为 shaded_reference
TP_0945 是否被标为 dense_built_edge_case
```

如果分类需要微调，改：

```text
configs/v10/v10_final_figures_config.v2.json
```
