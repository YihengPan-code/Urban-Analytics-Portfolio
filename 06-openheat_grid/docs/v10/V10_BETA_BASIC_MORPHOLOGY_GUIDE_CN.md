# OpenHeat v10-beta：Basic Morphology Recompute + Old/New Shift Audit 指南

> 目标：在 v10-alpha.3 reviewed building DSM 通过后，先重算基础建筑形态指标，并审计旧 v08/v09 hazard ranking 是否受到 building DSM gap 影响。
>
> 重要边界：v10-beta **不是最终 hazard ranking**。最终热危险排序需要在后续 v10-gamma 中用 reviewed DSM 重新跑 UMEP SVF / shadow。

---

## 1. 版本定位

v10-beta 的核心问题是：

> 旧 v08/v09 top hazard cells 是否因为旧 DSM building completeness 低而被错误推高？

因此 v10-beta 会比较：

```text
old v08/current DSM
vs
v10 reviewed augmented DSM
```

每个 100m grid cell 的：

```text
building_area_m2
building_density
open_pixel_fraction
building_height_mean / max / p50 / p90
```

并把这些变化与旧 hazard ranking、v10 completeness gain 结合起来，输出 DSM-gap false-positive candidates。

---

## 2. 输入文件

请先确认存在：

```text
data/grid/toa_payoh_grid_v07_features.geojson

data/rasters/v08/dsm_buildings_2m_toapayoh.tif

data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif

data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv

outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_rankings.csv

outputs/v10_dsm_audit/v10_alpha3_building_completeness_per_cell.csv
```

如果最后一个 alpha3 per-cell completeness 文件名不同，脚本会自动在 `outputs/v10_dsm_audit/` 里搜索 `*alpha3*per_cell*.csv` / `*completeness*per_cell*.csv`。

---

## 3. 运行方法

### 一键运行

```bat
scripts\v10_run_beta_basic_morphology_pipeline.bat
```

它会执行：

```text
0. input check
1. compute basic morphology
2. build morphology shift audit
```

### 分步运行

```bat
python scripts\v10_beta_check_inputs.py --config configs\v10\v10_beta_morphology_config.example.json
```

```bat
python scripts\v10_beta_compute_basic_morphology.py --config configs\v10\v10_beta_morphology_config.example.json
```

```bat
python scripts\v10_beta_build_morphology_shift_audit.py --config configs\v10\v10_beta_morphology_config.example.json
```

---

## 4. 输出文件

```text
data/grid/v10/toa_payoh_grid_v10_basic_morphology.csv
data/grid/v10/toa_payoh_grid_v10_basic_morphology.geojson

outputs/v10_morphology/v10_beta_input_check_report.md
outputs/v10_morphology/v10_basic_morphology_QA_report.md
outputs/v10_morphology/v10_old_vs_new_building_morphology_shift.csv

outputs/v10_ranking_audit/v10_beta_morphology_shift_audit_report.md
outputs/v10_ranking_audit/v10_old_false_positive_candidates.csv
outputs/v10_ranking_audit/v10_old_top50_morphology_shift.csv
```

---

## 5. 重点解释字段

### Morphology fields

```text
old_building_density
v10_building_density
delta_building_density

old_building_area_m2
v10_building_area_m2
delta_building_area_m2

old_open_pixel_fraction
v10_open_pixel_fraction
delta_open_pixel_fraction

old_building_height_mean_m
v10_building_height_mean_m
delta_building_height_mean_m
```

### Audit flags

```text
old_top20_hazard
old_top50_hazard
low_old_completeness
zero_old_completeness
high_coverage_gain
large_building_density_gain
possible_old_dsm_gap_false_positive
```

`possible_old_dsm_gap_false_positive` 的意思是：

```text
旧 hazard rank 很高
且旧 building completeness 很低
且 v10 coverage gain 很高
且 v10 building density 已经变得非零/明显
```

这不是最终定论，但它是旧 ranking 被 DSM gap 污染的强候选证据。

---

## 6. 如何判断结果是否合理

### 预期应该看到

```text
old top hazard cells 的 v10_building_density 明显高于 old_building_density
old top hazard cells 中许多 zero_old_completeness 被修复
v10_old_false_positive_candidates.csv 不为空
T01/T06/TP_0116/TP_0575 等 critical cells 的 delta_building_area_m2 明显为正
```

### 如果看到异常

#### v10_building_density 全部接近 old
说明 reviewed DSM 没有被正确读取，检查路径：

```text
data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif
```

#### `nodata: 0.0`
说明 reviewed DSM 不适合继续使用。应回到 alpha.3 rasterize 修复。

#### false-positive candidates 为 0
不一定错误，但需要检查是否正确 merge 了 old hazard rank 和 completeness per-cell CSV。

---

## 7. v10-beta 之后做什么

如果 v10-beta 确认 old top hazard cells 大量变成 non-zero building density，则进入：

```text
v10-gamma: UMEP SVF / shadow recomputation with reviewed DSM
```

如果 v10-beta 发现某些 false-positive candidates 仍然很复杂，则先做：

```text
v10-beta.1: manual QA / rank-shift review
```

---

## 8. 写作建议

可以这样写：

> v10-beta recomputed basic building morphology using the reviewed augmented DSM. This stage does not yet constitute final heat-hazard reranking, because SVF and shadow have not been recomputed. Instead, it audits whether old high-hazard cells were associated with building DSM coverage gaps. Cells flagged as possible old DSM-gap false positives will be inspected before v10 UMEP reruns.

中文：

> v10-beta 使用 reviewed augmented DSM 重算基础建筑形态。该阶段不是最终热危险重排，因为 SVF 和 shade 仍未重算；其目标是审计旧 top hazard cells 是否与旧 DSM 覆盖缺口有关。被标记为 possible old DSM-gap false positive 的 cell 将作为后续 UMEP 重跑和人工检查的重点。
