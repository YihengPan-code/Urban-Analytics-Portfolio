# OpenHeat v1.0-alpha.1 Hotfix 包

解压到 `06-openheat_grid/` 根目录后运行：

```bat
scripts\v10_run_alpha1_hotfix_pipeline.bat
```

这个 hotfix 会覆盖以下脚本：

```text
scripts/v10_deduplicate_building_footprints.py
scripts/v10_assign_building_heights.py
scripts/v10_rasterize_augmented_dsm.py
scripts/v10_building_completeness_audit.py
```

并新增：

```text
scripts/v10_run_alpha1_hotfix_pipeline.bat
docs/v10/V10_ALPHA1_HOTFIX_GUIDE_CN.md
```

核心修复：

- augmented DSM 不再设置 `nodata=0.0`；`0.0` 是合法 ground/no-building height。
- rasterize 死代码删除，显式 `MergeAlg.replace`，高建筑覆盖低建筑。
- dedup duplicate merge 时提升 OSM height/levels/type 信息。
- completeness report 增加 ratio > 1.0 解释、critical v0.9 tile recovery、negative-gain cell 输出。

跑完后请检查：

```bat
python -c "import rasterio; src=rasterio.open('data/rasters/v10/dsm_buildings_2m_augmented.tif'); print(src.nodata); src.close()"
```

期望输出：

```text
None
```
