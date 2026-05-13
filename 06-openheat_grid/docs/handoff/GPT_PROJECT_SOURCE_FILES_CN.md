# GPT 项目源文件夹建议清单

> 目的：如果要把 OpenHeat 项目迁移到新的 GPT Project / 新对话，让 AI 快速理解上下文，同时避免上传巨大 raster、SOLWEIG tif、raw archive 大文件。

---

## 最小必需文件

建议至少放这些：

```text
OPENHEAT_HANDOFF_CN.md
NEW_CHAT_PROMPT_CN.md
docs/v09_freeze/V09_FREEZE_NOTE_CN.md
docs/v09_freeze/V09_REVISED_FINDINGS_CN.md
docs/v09_freeze/33_V09_BUILDING_DSM_GAP_AUDIT_CN.md
docs/v09_freeze/32_V09_COMPLETE_WORK_RECORD_CN.md
docs/v10/V10_PROJECT_STRUCTURE_CN.md
directory_structure.md
```

---

## 如果要让 AI 帮你写 v10 代码

再加：

```text
scripts/v09_gamma_check_building_completeness.py
scripts/v09_gamma_check_overhead_structures.py
scripts/v08_hdb3d_to_geojson.py
scripts/v08_clip_buildings_to_aoi.py
scripts/v08_merge_buildings_with_height.py
scripts/v08_rasterize_building_dsm.py
scripts/v07_build_grid_features.py
src/openheat_grid/features.py
src/openheat_grid/geospatial.py
src/openheat_grid/grid.py
src/openheat_forecast/hotspot_engine.py
```

---

## 如果要让 AI 理解 calibration / ML 部分

再加：

```text
scripts/v09_archive_qa.py
scripts/v09_build_wbgt_station_pairs.py
scripts/v09_beta_fit_calibration_models.py
scripts/v09_beta_threshold_scan.py
outputs/v09_alpha_calibration/v09_archive_QA_report.md
outputs/v09_alpha_calibration/v09_wbgt_pairing_QA_report.md
outputs/v09_beta_calibration/v09_beta_calibration_report.md
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_report.md
```

---

## 不建议放入 GPT Project source 的文件

这些太大或不必要：

```text
*.tif
*.aux.xml
data/rasters/
data/solweig/*/solweig_outputs*/
data/archive/nea_realtime_observations.csv
large raw GeoJSON if > 50MB
.git/
.pytest_cache/
__pycache__/
*.zip
*.lnk
```

如果需要讨论 raster/SOLWEIG 结果，只上传 summary CSV / report markdown，不上传 tif。

---

## 推荐打包方式

运行：

```bat
python scripts\create_openheat_handoff_package.py --root . --mode gpt_sources
```

会生成适合上传给 GPT Project 的小包。

如果要完整保留所有 docs/scripts/configs：

```bat
python scripts\create_openheat_handoff_package.py --root . --mode docs_scripts
```
