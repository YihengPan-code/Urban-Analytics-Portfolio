# OpenHeat v1.0-alpha: OSM-first Augmented Building DSM Guide

## 1. 版本目标

v1.0-alpha 的目标不是继续调热风险模型，而是先修复 v0.9 audit 暴露的上游 morphology 数据问题：HDB3D + URA building DSM 在 selected SOLWEIG tiles 中相对 OSM-mapped building area 只有很低 completeness，导致旧 hazard ranking 可能把 DSM 数据空洞误判为真实开阔高热区域。

v1.0-alpha 先做一个 **OSM-first augmented DSM pilot**：

```text
HDB3D + URA + OSM building polygons
→ source standardisation
→ conservative deduplication
→ height assignment with provenance
→ 2m augmented building DSM
→ old vs new completeness audit
```

暂时不加入 Microsoft / Google / OneMap，避免第一版过度复杂。等 OSM-first 流程跑通，再扩展到多源 ML-derived footprints。

---

## 2. 新增文件

```text
configs/v10/v10_alpha_augmented_dsm_config.example.json
scripts/v10_extract_osm_buildings.py
scripts/v10_standardize_building_sources.py
scripts/v10_deduplicate_building_footprints.py
scripts/v10_assign_building_heights.py
scripts/v10_rasterize_augmented_dsm.py
scripts/v10_building_completeness_audit.py
scripts/v10_run_alpha_osm_augmented_dsm_pipeline.bat
requirements_v10_alpha.txt
```

---

## 3. 运行前检查

确保这些文件已经存在：

```text
data/grid/toa_payoh_grid_v07_features.geojson
data/features_3d/aoi_buffered_200m.geojson
data/features_3d/hdb3d_buildings_toapayoh.geojson
data/features_3d/ura_buildings_toapayoh.geojson
data/raw/ura_masterplan2019_land_use.geojson
data/rasters/v08/dsm_buildings_2m_toapayoh.tif
```

如果 `data/features_3d/aoi_buffered_200m.geojson` 不存在，脚本会用 grid union + 200m buffer 生成 AOI 逻辑。

---

## 4. 安装依赖

```bat
pip install -r requirements_v10_alpha.txt
```

如果你使用 conda-forge，建议：

```bat
conda install -c conda-forge geopandas shapely pandas numpy requests rasterio pyproj
```

---

## 5. 一键运行

在项目根目录运行：

```bat
scripts\v10_run_alpha_osm_augmented_dsm_pipeline.bat
```

它会依次执行：

```text
1. OSM buildings extraction
2. Source standardisation
3. Footprint deduplication
4. Height assignment
5. Augmented DSM rasterization
6. Completeness audit
```

---

## 6. 分步运行

### Step 1: 下载 OSM buildings

```bat
python scripts\v10_extract_osm_buildings.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
```

输出：

```text
data/raw/buildings_v10/osm_buildings_toapayoh.geojson
```

如果 Overpass API 报错，稍后重试或换 endpoint。脚本已有多个 endpoint fallback。

---

### Step 2: 标准化 HDB3D / URA / OSM

```bat
python scripts\v10_standardize_building_sources.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
```

输出：

```text
data/features_3d/v10/source_standardized/hdb3d_standardized.geojson
data/features_3d/v10/source_standardized/ura_standardized.geojson
data/features_3d/v10/source_standardized/osm_standardized.geojson
data/features_3d/v10/canonical_candidates/all_building_candidates_v10.geojson
outputs/v10_dsm_audit/v10_source_standardization_QA.md
```

---

### Step 3: Deduplicate footprints

```bat
python scripts\v10_deduplicate_building_footprints.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
```

输出：

```text
data/features_3d/v10/canonical/canonical_buildings_v10.geojson
data/features_3d/v10/canonical/canonical_buildings_v10_conflicts.geojson
outputs/v10_dsm_audit/v10_dedup_QA_report.md
```

注意：v1.0-alpha 的 dedup 是保守策略。模糊重叠的 footprints 会进入 `conflict_review`，不会自动进入 canonical layer，避免重复烧录建筑。

---

### Step 4: Height imputation

```bat
python scripts\v10_assign_building_heights.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
```

输出：

```text
data/features_3d/v10/height_imputed/canonical_buildings_v10_height.geojson
data/features_3d/v10/height_imputed/height_imputation_QA.csv
outputs/v10_dsm_audit/v10_height_imputation_QA.md
```

高度层级：

```text
1. HDB3D / source explicit height
2. OSM height tag
3. OSM building:levels × 3m
4. land-use / area default
```

每栋建筑都会保留：

```text
height_m
height_source
height_confidence
height_warning
```

---

### Step 5: Rasterize augmented DSM

```bat
python scripts\v10_rasterize_augmented_dsm.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
```

输出：

```text
data/rasters/v10/dsm_buildings_2m_augmented.tif
outputs/v10_dsm_audit/v10_rasterize_augmented_dsm_QA.md
```

注意：这个 DSM 只包含 ground-up buildings。高架桥、covered walkways、viaducts 不应混入 building DSM，它们未来应该进入 overhead / transport DSM。

---

### Step 6: Completeness audit

```bat
python scripts\v10_building_completeness_audit.py --config configs\v10\v10_alpha_augmented_dsm_config.example.json
```

输出：

```text
outputs/v10_dsm_audit/v10_building_completeness_per_cell.csv
outputs/v10_dsm_audit/v10_building_completeness_per_tile.csv
outputs/v10_dsm_audit/v10_building_completeness_map.geojson
outputs/v10_dsm_audit/v10_completeness_gain_report.md
```

重点看：

```text
old_vs_osm_completeness
new_vs_osm_completeness
coverage_gain_vs_osm
new_minus_old_dsm_area_m2
```

---

## 7. 成功标准

v1.0-alpha 跑通后，应看到：

```text
1. OSM buildings 成功下载并转为 EPSG:3414。
2. canonical buildings 数量高于原 HDB3D+URA 有效建筑数。
3. augmented DSM building area 明显高于旧 DSM。
4. T01/T02/T05/T06 等 v09 problematic tiles 的 completeness 明显改善。
5. 没有大面积 null height。
6. large low-confidence buildings 数量可控，并可人工 QA。
```

---

## 8. 跑完后发给 AI 检查的文件

```text
outputs/v10_dsm_audit/v10_source_standardization_QA.md
outputs/v10_dsm_audit/v10_dedup_QA_report.md
outputs/v10_dsm_audit/v10_height_imputation_QA.md
outputs/v10_dsm_audit/v10_rasterize_augmented_dsm_QA.md
outputs/v10_dsm_audit/v10_completeness_gain_report.md
outputs/v10_dsm_audit/v10_building_completeness_per_tile.csv
```

如果只想先快速判断，优先发：

```text
outputs/v10_dsm_audit/v10_completeness_gain_report.md
outputs/v10_dsm_audit/v10_building_completeness_per_tile.csv
```

---

## 9. 重要解释边界

- OSM 不是 ground truth；completeness 是 relative to OSM-mapped building area。
- OSM 可能包含 roof/shelter/linkway-like structures，后续需要区分 building DSM 和 overhead DSM。
- v1.0-alpha 只是 OSM-first augmented DSM pilot，不是最终 v1.0 full multi-source DSM。
- Microsoft / Google / OneMap 暂时未接入；等 OSM-first 流程稳定后再加。
- 如果 canonical dedup 保守策略导致 conflict_review 太多，可以在 v1.0-beta 调整规则。
