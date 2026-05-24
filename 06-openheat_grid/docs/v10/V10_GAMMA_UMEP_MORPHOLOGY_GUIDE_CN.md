# OpenHeat v10-gamma：reviewed DSM UMEP morphology + v10 hazard rerun 指南

> 目标：使用 v10 reviewed augmented building DSM 复刻 v08 的 UMEP SVF / shadow morphology 流程，生成 v10 `svf` / `shade_fraction` / building morphology grid，随后重跑 forecast / hazard ranking，并和 v08 current-DSM ranking 对比。

---

## 1. 阶段定位

v10-beta 已经证明旧 v08/v09 top hazard cells 中存在大量 DSM-gap false-positive candidates。v10-gamma 的任务不是再做 basic morphology，而是：

```text
reviewed building DSM + vegetation DSM
→ UMEP SVF / shadow
→ 100m grid zonal statistics
→ v10 forecast grid
→ run forecast/hazard engine
→ v08 vs v10 ranking comparison
```

这一步完成后，才可以开始讨论新的 reviewed-DSM heat-hazard ranking。

---

## 2. 运行前必须确认

需要这些文件：

```text
data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif
data/rasters/v08/dsm_vegetation_2m_toapayoh.tif
data/grid/toa_payoh_grid_v07_features.geojson
data/grid/v10/toa_payoh_grid_v10_basic_morphology.csv
data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv
outputs/v08_umep_with_veg_forecast_live/v06_live_hotspot_ranking.csv
```

最重要的是 reviewed DSM 必须：

```text
nodata = None
0.0 = valid ground / no-building height
```

检查命令：

```bat
python -c "import rasterio; p='data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif'; src=rasterio.open(p); print('nodata:', src.nodata); print('shape:', src.shape); src.close()"
```

---

## 3. Step A：pre-UMEP 检查和文件夹准备

```bat
scripts\v10_gamma_pre_umep_pipeline.bat
```

它会生成：

```text
outputs/v10_umep_morphology/v10_gamma_prepare_umep_inputs_report.md
data/rasters/v10/V10_GAMMA_UMEP_MANUAL_STEPS.txt
```

并创建：

```text
data/rasters/v10/umep_svf_with_veg/
data/rasters/v10/umep_shadow_with_veg/
outputs/v10_umep_morphology/
outputs/v10_gamma_forecast_live/
outputs/v10_gamma_comparison/
```

---

## 4. Step B：QGIS / UMEP 手工运行

在 QGIS / UMEP 中使用：

```text
Reviewed building DSM:
  data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif

Vegetation DSM:
  data/rasters/v08/dsm_vegetation_2m_toapayoh.tif
```

推荐复刻 v08 参数：

```text
vegetation transmissivity = 3%
trunk zone = 25%
shadow date = 2026-03-20 或与 v08 baseline 一致
shadow hours = 08:00–19:00，至少需要 10:00–16:00
```

SVF 输出放：

```text
data/rasters/v10/umep_svf_with_veg/
```

必须至少有：

```text
SkyViewFactor.tif
svfs.zip
```

Shadow 输出放：

```text
data/rasters/v10/umep_shadow_with_veg/
```

文件名建议类似：

```text
Shadow_20260320_1000_LST.tif
Shadow_20260320_1100_LST.tif
...
Shadow_20260320_1600_LST.tif
```

---

## 5. Step C：post-UMEP morphology 聚合

UMEP 输出完成后运行：

```bat
scripts\v10_gamma_post_umep_morphology_pipeline.bat
```

输出：

```text
data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv
data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.geojson
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.geojson
outputs/v10_umep_morphology/v10_gamma_zonal_umep_morphology_QA_report.md
outputs/v10_umep_morphology/v10_gamma_grid_merge_QA_report.md
```

检查时间标签和摘要：

```bat
python -c "import pandas as pd; df=pd.read_csv('data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv'); print([c for c in df.columns if 'shade_fraction_umep_' in c][:20]); print(df[['cell_id','svf_umep_mean_open_v10','shade_fraction_umep_10_16_open_v10','building_pixel_fraction_v10']].head().to_string(index=False))"
```

---

## 6. Step D：重跑 forecast / hazard ranking 并比较 v08-v10

```bat
scripts\v10_gamma_run_forecast_and_compare.bat
```

输出：

```text
outputs/v10_gamma_forecast_live/v06_live_hotspot_ranking.csv
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.csv
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.geojson
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_QA_report.md

outputs/v10_gamma_comparison/v10_vs_v08_forecast_ranking_comparison.md
outputs/v10_gamma_comparison/v10_vs_v08_rank_comparison.csv
outputs/v10_gamma_comparison/v10_vs_v08_topset_details.csv
```

---

## 7. 跑完后重点看什么

1. `v10_gamma_zonal_umep_morphology_QA_report.md`：SVF / shade 是否合理。
2. `v10_gamma_grid_merge_QA_report.md`：v10 是否成功替换 `svf` / `shade_fraction` / `building_density`。
3. `v10_vs_v08_forecast_ranking_comparison.md`：old top hazards 是否离开 v10 top set。
4. `v10_old_false_positive_candidates.csv` 里的 cells 是否大量从 top ranking 掉出。

如果旧 false-positive candidates 大量离开 top20/top50，这就证明：旧 v08/v09 ranking 确实被 building DSM coverage gap 污染。

---

## 8. 重要边界

- v10-gamma 仍然不包含 overhead / transport DSM。
- 高架桥、covered walkway、station canopy 应继续作为 overhead layer / limitation。
- v10-gamma 是 reviewed building DSM + vegetation DSM 的 corrected morphology ranking。
- 真正完整的 pedestrian shade simulation 仍需要未来 `dsm_overhead_2m.tif` sensitivity。
