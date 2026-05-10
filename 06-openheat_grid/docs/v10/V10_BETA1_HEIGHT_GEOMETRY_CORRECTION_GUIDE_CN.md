# OpenHeat v10-beta.1 高度 / 几何修正指南

## 目标

v10-beta 已经证明旧 hazard ranking 存在 building DSM coverage-gap false positives。进入 v10-gamma UMEP/SVF/shadow 前，需要先处理少数高度明显异常的大 footprint：

- `v10_bldg_000001`：原高度约 85.3 m，但 Google Street View / QGIS 目测显示明显低于旁边 71 m 高楼的一半，因此手动修正为 30 m。
- `v10_bldg_000002`：block complex，包含两栋高塔和低/中层底座。原始 polygon 把 93.7 m 统一应用到整个 complex，需用手动 split polygons 替代。

## 输入

```text
configs/v10/v10_beta1_height_geometry_config.example.json

data/features_3d/v10/height_imputed/canonical_buildings_v10_height_reviewed.geojson

data/features_3d/v10/manual_qa/manual_split_buildings_v10.geojson
```

`manual_split_buildings_v10.geojson` 应包含 `v10_bldg_000002` 的分割 polygon。建议字段：

```text
manual_id
parent_building_id
part_type
manual_height_m
height_confidence
manual_notes
```

如果没有这些字段，脚本会尽量使用默认：tower=93.7m，podium=15m，unknown=30m。

## 可选 corrections CSV

如不存在，脚本会自动写出默认：

```text
data/features_3d/v10/manual_qa/v10_beta1_height_geometry_corrections.csv
```

默认内容：

```csv
target_type,target_id,manual_decision,manual_height_m,manual_notes
building,v10_bldg_000001,height_adjust,30,...
building,v10_bldg_000002,split_complex,,...
```

## 运行

```bat
scripts\v10_run_beta1_height_geometry_pipeline.bat
```

或分步：

```bat
python scripts\v10_beta1_apply_height_geometry_corrections.py --config configs\v10\v10_beta1_height_geometry_config.example.json
python scripts\v10_beta1_rasterize_heightqa_dsm.py --config configs\v10\v10_beta1_height_geometry_config.example.json
```

## 输出

```text
data/features_3d/v10/height_imputed/canonical_buildings_v10_height_reviewed_heightqa.geojson

data/features_3d/v10/manual_qa/split_replaced_originals_v10.geojson

outputs/v10_dsm_audit/v10_beta1_applied_height_geometry_corrections.csv
outputs/v10_dsm_audit/v10_beta1_height_geometry_QA_report.md

data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif
outputs/v10_dsm_audit/v10_beta1_heightqa_rasterize_QA_report.md
```

## 关键检查

```bat
python -c "import rasterio; p='data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif'; src=rasterio.open(p); print('nodata:', src.nodata); print('shape:', src.shape); src.close()"
```

应为：

```text
nodata: None
```

## 后续

v10-gamma UMEP/SVF/shadow 应使用：

```text
data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif
```

不要再使用 alpha.3 的：

```text
data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif
```
