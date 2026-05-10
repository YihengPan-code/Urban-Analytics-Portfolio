# OpenHeat v10-beta.1 height / geometry correction patch

解压到项目根目录后运行：

```bat
scripts\v10_run_beta1_height_geometry_pipeline.bat
```

前提：你已经在 QGIS 中创建：

```text
data/features_3d/v10/manual_qa/manual_split_buildings_v10.geojson
```

这个 patch 会：

1. 将 `v10_bldg_000001` 高度修正为 30m；
2. 删除 `v10_bldg_000002` 原始 block-complex polygon；
3. 添加 `manual_split_buildings_v10.geojson` 中的 tower/podium split polygons；
4. 输出 `canonical_buildings_v10_height_reviewed_heightqa.geojson`；
5. 栅格化为 `dsm_buildings_2m_augmented_reviewed_heightqa.tif`；
6. 保持 `nodata=None`，确保 0.0 是合法地面。
