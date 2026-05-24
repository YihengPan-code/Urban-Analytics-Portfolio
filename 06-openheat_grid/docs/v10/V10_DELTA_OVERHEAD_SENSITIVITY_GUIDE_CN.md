# OpenHeat v10-delta Overhead Infrastructure Sensitivity Guide

> 目标：在 v10-gamma reviewed-DSM heat-hazard ranking 之后，单独量化高架道路、轨道高架、天桥、covered walkway、station canopy 等 overhead infrastructure 对 pedestrian heat-risk 解释的影响。

---

## 1. 为什么需要 v10-delta

v10-gamma 已经完成 reviewed building DSM + vegetation DSM 的 UMEP SVF/shadow 重跑，并生成了 data-integrity-corrected hazard ranking。v10-gamma 的结果显示：v08/v10 hazard ranking 全局 Spearman 仍高，但 top20 只重合 10/20；旧 v08 top20 中 12 个 DSM-gap false-positive candidates 有 9 个离开 v10 top20。

但是 v10-gamma 仍然不显式模拟：

- elevated road / expressway / flyover;
- elevated rail / MRT / viaduct;
- pedestrian bridges;
- covered walkways;
- station canopy / transport shelter.

这些不能放进 ordinary building DSM，因为它们往往是上方有遮挡、下方仍可通行的 two-layer infrastructure。

---

## 2. v10-delta 的核心原则

### 不把高架桥直接当建筑

building DSM 表示 ground-up solid building。高架桥和 covered structures 是 overhead canopy / transport deck，不应该直接烧进 building DSM。

### 区分桥面与桥下

- 桥面：可能很热，但通常不是 pedestrian exposure surface；
- 桥下：可能有遮阴，可能降低 Tmrt；
- covered walkway / station canopy：通常是 pedestrian shelter adaptation。

因此 v10-delta 不是直接改主 hazard map，而是做 sensitivity + flag。

---

## 3. 这个 patch 做什么

它分两段：

### A. Overhead QA + sensitivity grid

```bat
scripts\v10_delta_run_overhead_qa_pipeline.bat
```

生成：

```text
data/features_3d/v10/overhead/overhead_structures_v10.geojson
outputs/v10_overhead_qa/v10_overhead_per_cell.csv
outputs/v10_overhead_qa/v10_overhead_per_cell.geojson
data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv
outputs/v10_overhead_sensitivity/v10_delta_grid_overhead_merge_QA_report.md
```

### B. Forecast sensitivity + comparison

```bat
scripts\v10_delta_run_overhead_forecast_and_compare.bat
```

生成：

```text
outputs/v10_delta_overhead_sensitivity_forecast_live/
outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_comparison.md
outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_rank_comparison.csv
```

---

## 4. 输入文件

默认使用：

```text
outputs/v09_gamma_qa/v09_overhead_structures_footprints.geojson
outputs/v09_gamma_qa/v09_overhead_structures.geojson
data/features_3d/v10/manual_qa/overhead_candidates_v10.geojson
data/features_3d/v10/manual_qa/manual_overhead_candidates_v10.geojson  # optional
```

如果 `manual_overhead_candidates_v10.geojson` 不存在没有关系。

v10-gamma grid 输入：

```text
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv
```

v10-gamma base ranking 输入：

```text
outputs/v10_gamma_forecast_live/v06_live_hotspot_ranking.csv
```

---

## 5. 你自己需要做什么

### Step 1: 在 QGIS 中快速检查 overhead layer

运行第一段 pipeline 后，打开：

```text
data/features_3d/v10/overhead/overhead_structures_v10.geojson
outputs/v10_overhead_qa/v10_overhead_per_cell.geojson
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.geojson
```

看：

- v10 top hazards 是否被高架交汇处覆盖；
- high-overhead cells 是 elevated road/rail，还是 covered walkway；
- 是否有明显缺失的 high-overhead polygon。

如果你发现一个大型高架交汇处没有被识别，可以手动补到：

```text
data/features_3d/v10/manual_qa/manual_overhead_candidates_v10.geojson
```

字段建议：

```text
overhead_id
overhead_type
height_m
opacity
pedestrian_access
ground_underpass_access
source_note
manual_notes
```

然后重跑：

```bat
scripts\v10_delta_run_overhead_qa_pipeline.bat
```

---

## 6. 运行步骤

### Step 1：Overhead QA

```bat
scripts\v10_delta_run_overhead_qa_pipeline.bat
```

查看：

```bat
type outputs\v10_overhead_qa\v10_delta_overhead_layer_QA_report.md
type outputs\v10_overhead_qa\v10_overhead_cell_QA_report.md
type outputs\v10_overhead_sensitivity\v10_delta_grid_overhead_merge_QA_report.md
```

### Step 2：Overhead forecast sensitivity

```bat
scripts\v10_delta_run_overhead_forecast_and_compare.bat
```

查看：

```bat
type outputs\v10_delta_overhead_comparison\v10_base_vs_overhead_sensitivity_comparison.md
```

---

## 7. 如何解释结果

### overhead_confounding_flag

```text
clean_or_minor        overhead_fraction < 0.02
moderate_confounding  0.02–0.10
major_confounding     > 0.10
```

### overhead_shade_proxy

这是一个简化 sensitivity proxy，不是严格 UMEP shadow：

```text
covered walkway      high shade weight
station canopy       high shade weight
pedestrian bridge    medium-high shade weight
elevated rail        medium shade weight
elevated road        medium-low shade weight
```

### shade_fraction_overhead_sens

用公式：

```text
1 - (1 - shade_fraction_v10_base) × (1 - overhead_shade_proxy)
```

这个是 ground-level pedestrian shade sensitivity，不等于桥面热环境。

---

## 8. 重要 limitation

- v10-delta 不替代 v10-gamma base ranking；
- overhead-shade sensitivity 是 proxy，不是 full SOLWEIG physical rerun；
- elevated road / rail 是 two-layer infrastructure：桥面热和桥下遮阴不能混成一个解释；
- 如果 high-overhead cells 对 top ranking 影响很大，下一步应该做 selected-tile overhead DSM / SOLWEIG sensitivity。

---

## 9. 跑完后发给我

```text
outputs/v10_overhead_qa/v10_delta_overhead_layer_QA_report.md
outputs/v10_overhead_qa/v10_overhead_cell_QA_report.md
outputs/v10_overhead_sensitivity/v10_delta_grid_overhead_merge_QA_report.md
outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_comparison.md
```

如果方便，也发：

```text
outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_rank_comparison.csv
outputs/v10_delta_overhead_sensitivity_forecast_live/v10_delta_overhead_hotspot_ranking_with_features.csv
```

---

## 10. v10-delta 通过标准

- overhead layer 成功构建；
- 每个 cell 有 overhead_fraction / overhead_shade_proxy / confounding flag；
- v10-gamma top hazards 的 overhead exposure 被量化；
- overhead-shade sensitivity ranking 成功与 base ranking 比较；
- 报告明确区分 pedestrian under-bridge shade 和 transport-deck surface heat。
