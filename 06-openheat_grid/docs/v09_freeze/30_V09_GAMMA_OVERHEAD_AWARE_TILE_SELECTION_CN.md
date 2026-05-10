# OpenHeat v0.9-gamma: overhead-aware SOLWEIG tile reselection

## 为什么要做这个 hotfix

初始 v0.9-gamma tile QA 发现：

- T01 hazard tile 的高架桥位于 tile center 且范围较大；
- T03 social-risk tile 与 T04 candidate-policy tile 约 50% 重合；
- 所有初始 tiles 均与 overhead structures 相交。

这意味着初始 tile set 不适合作为“干净”的 building+canopy radiant-exposure SOLWEIG 实验样区。这个 patch 把 tile selection 从 rank-only 改成 rank + overhead + spatial-separation constraints。

## 新的 tile 设计

默认选择：

1. `clean_hazard_top`: 高 heat hazard，但低 overhead confounding。
2. `conservative_risk_top`: 主风险优先级 tile，尽量控制 focus-cell overhead。
3. `social_risk_top`: 社会敏感优先级 tile，避免与其他 tiles 高重合。
4. `open_paved_hotspot`: 高道路比例、低绿量、低遮阴、较高 hazard 的开放硬化热点。
5. `clean_shaded_reference`: 低 hazard、高 shade、高绿色信号、低 overhead 的 reference。
6. 可选 `overhead_confounded_hazard_case`: 高 hazard + 高 overhead 的诊断 tile，不作为 clean tile。

## 运行顺序

### 0. 确认输入

需要已有：

```text
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_rankings.geojson
outputs/v09_gamma_qa/v09_overhead_structures.geojson
data/grid/toa_payoh_grid_v07_features.geojson
data/rasters/v08/dsm_buildings_2m_toapayoh.tif
data/rasters/v08/dsm_vegetation_2m_toapayoh.tif
```

其中 `v09_overhead_structures.geojson` 来自你已有的 Overpass overhead 检测脚本。

### 1. 一键 pre-UMEP

```bat
scripts\v09_gamma_overhead_aware_pre_umep_pipeline.bat
```

这会依次运行：

```text
v09_gamma_build_overhead_cell_qa.py
v09_gamma_select_tiles_overhead_aware.py
v09_gamma_clip_tiles_overhead_aware.py
```

### 2. 检查 tile selection QA

```bat
type data\solweig\v09_tiles_overhead_aware\v09_solweig_tile_selection_overhead_aware_QA_report.md
```

重点看：

- `selection_status` 是否大多为 `strict`；
- clean reference 是否没有 warning；
- `overhead_fraction_cell` 和 `tile_overhead_fraction` 是否可接受；
- tile 间 `max_iou_with_previous` 是否低于 0.20；
- `overhead_confounded_hazard_case` 如果存在，只作为诊断。

### 3. QGIS 人工 QA

打开：

```text
data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware.geojson
data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware_buffered.geojson
outputs/v09_gamma_qa/v09_overhead_structures_footprints.geojson
```

确认：

- clean hazard tile 不在高架桥中心；
- T03/T04 不再高度重叠；
- reference tile 是树冠/公园/低 hazard reference，而不是高架/轨道遮阴 reference。

### 4. 对每个 tile 跑 QGIS/UMEP SOLWEIG

每个 tile 文件夹在：

```text
data/solweig/v09_tiles_overhead_aware/Txx_*/
```

UMEP 使用：

```text
dsm_buildings_tile.tif
dsm_vegetation_tile.tif
```

不要用 `*_masked.tif` 给 UMEP；它们是 Python QA / aggregation 用，nodata = -9999。

建议输出 Tmrt 文件名保留 HHMM：

```text
Tmrt_2026_5_7_1000D.tif
Tmrt_2026_5_7_1200D.tif
Tmrt_2026_5_7_1300D.tif
Tmrt_2026_5_7_1500D.tif
Tmrt_2026_5_7_1600D.tif
```

### 5. post-UMEP 聚合

```bat
scripts\v09_gamma_overhead_aware_post_umep_pipeline.bat
```

输出：

```text
outputs/v09_solweig/v09_solweig_tmrt_grid_summary_overhead_aware.csv
outputs/v09_solweig/v09_solweig_tmrt_grid_summary_overhead_aware_report.md
```

检查时间解析：

```bat
python -c "import pandas as pd; df=pd.read_csv('outputs/v09_solweig/v09_solweig_tmrt_grid_summary_overhead_aware.csv'); print(sorted(df['tmrt_time_label'].dropna().astype(str).unique()))"
```

应该看到：

```text
1000, 1200, 1300, 1500, 1600
```

不应该看到：

```text
2026
```

## 解释边界

- 这个 patch 不把高架桥直接烧进 DSM，因为高架结构是 overhead canopy，而不是从地面长出的实心建筑。
- 高架/天桥/covered walkway 在当前版本中作为 confounding QA 和 sensitivity issue 标记。
- `overhead_confounded_hazard_case` 可以作为 v0.9-gamma 的特殊诊断案例，但不应作为 clean hazard tile。
- 如果 SOLWEIG tile 仍有 high overhead fraction，需要在 report 中说明 Tmrt 可能被高估。
