# OpenHeat v1.0-alpha.1 Hotfix Guide

这个 hotfix 修复 v1.0-alpha OSM-first augmented DSM 中发现的几个工程问题：

1. `dsm_buildings_2m_augmented.tif` 不应设置 `nodata=0.0`。在 flat-terrain DSM 里，`0.0` 是合法地面 / 无建筑高度，不是缺失值。
2. `v10_rasterize_augmented_dsm.py` 中重复 rasterize 的死代码被移除，并显式使用 `MergeAlg.replace`，按高度升序烧录，让高建筑覆盖低建筑。
3. dedup 阶段现在会在 duplicate merge 时把 OSM 的 `height` / `building:levels` / building type 信息提升到 canonical record，避免高度标签只进入 provenance 却在 height assignment 阶段丢失。
4. completeness report 增加 ratio > 1.0 说明、critical v0.9 tile recovery 表，以及 negative-gain cell CSV。

---

## 使用方法

解压到项目根目录：

```text
C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid
```

然后运行：

```bat
scripts\v10_run_alpha1_hotfix_pipeline.bat
```

或分步运行：

```bat
python scripts\v10_deduplicate_building_footprints.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
python scripts\v10_assign_building_heights.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
python scripts\v10_rasterize_augmented_dsm.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
python scripts\v10_building_completeness_audit.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
```

---

## 跑完后检查

### 1. DSM nodata 必须是 None

```bat
python -c "import rasterio; p='data/rasters/v10/dsm_buildings_2m_augmented.tif'; src=rasterio.open(p); print('nodata:', src.nodata); print('shape:', src.shape); src.close()"
```

期望：

```text
nodata: None
```

如果仍然是 `0.0`，不要拿这个 DSM 跑 UMEP/SOLWEIG。

### 2. 查看 raster QA

```bat
type outputs\v10_dsm_audit\v10_rasterize_augmented_dsm_QA.md
```

重点看：

```text
Raster nodata metadata: None
0.0 is valid ground / no-building height
```

### 3. 查看 height source 是否改善

```bat
type outputs\v10_dsm_audit\v10_height_imputation_QA.md
```

如果 OSM height/levels promotion 生效，`osm_levels_x_3m` / `osm_height_tag` 数量可能比 v10-alpha 略有提升，`lu_default` 可能略降。

### 4. 查看 completeness report

```bat
type outputs\v10_dsm_audit\v10_completeness_gain_report.md
```

重点看：

```text
Critical v0.9 tile recovery
Negative-gain cell QA
ratio >1.0 explanation
```

---

## 需要重新跑哪些阶段？

这个 hotfix 不需要重新下载 OSM，也不需要重新 standardize sources。

建议重跑：

```text
Dedup → Height assignment → Rasterize DSM → Completeness audit
```

不需要重跑：

```text
v10_extract_osm_buildings.py
v10_standardize_building_sources.py
```

除非你怀疑 OSM 范围本身有问题。

---

## 这次 hotfix 后的解释

v10-alpha 的核心 conclusion 大概率不变：OSM-first augmentation 大幅修复 HDB3D+URA building DSM coverage gap。

但在使用 augmented DSM 进入 UMEP / SVF / shadow / SOLWEIG 前，必须使用 v10-alpha.1 的 no-nodata DSM。

```text
completeness proof: v10-alpha already useful
UMEP-ready DSM: use v10-alpha.1 hotfix output
```
