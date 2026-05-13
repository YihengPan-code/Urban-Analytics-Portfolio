# v1.0-alpha.1 min_area / indentation fix v2

修复 `v10_deduplicate_building_footprints.py` 中由于上一版 min_area patch 导致的 `IndentationError`。

## 使用

在项目根目录运行：

```bat
python scripts\patch_v10_alpha1_min_area_v2.py
```

然后重新运行：

```bat
scripts\v10_run_alpha1_hotfix_pipeline.bat
```

## 修复内容

- 新增 `resolve_min_area(dedup, row)`，同时支持数字型和 dict 型 `min_area_m2` 配置；
- 修复 malformed indentation block；
- 保留原脚本备份为 `.bak_min_area_v2_YYYYMMDD_HHMMSS`。
