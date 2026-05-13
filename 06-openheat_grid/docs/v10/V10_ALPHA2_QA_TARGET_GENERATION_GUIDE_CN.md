# OpenHeat v1.0-alpha.2 QA Target Generation Guide

## 1. 目的

v1.0-alpha.1 已经成功生成 OSM-first augmented building DSM，并且修复了 `nodata=0.0` 和 OSM height/levels promotion 问题。下一步不是马上重跑 UMEP/SOLWEIG，而是先抽出最值得人工检查的对象。

v1.0-alpha.2 的目标是生成一个 QGIS-ready manual QA target set，用来检查：

1. 大型低置信度建筑；
2. 可能是 transport / shelter / overhead 的大结构；
3. dedup conflict-review 候选；
4. old-vs-new DSM 面积负增长 cell；
5. old high-hazard 且旧 DSM completeness 很低 / coverage gain 很高的 cell；
6. 与 v0.9 critical SOLWEIG tiles 相交的可疑建筑。

---

## 2. 新增文件

```text
configs/v10/v10_alpha2_qa_config.example.json

scripts/v10_alpha2_generate_qa_targets.py
scripts/v10_run_alpha2_qa_targets.bat

docs/v10/V10_ALPHA2_QA_TARGET_GENERATION_GUIDE_CN.md
```

---

## 3. 运行前需要确认

需要已经存在 v1.0-alpha.1 输出：

```text
data/features_3d/v10/height_imputed/canonical_buildings_v10_height.geojson
data/features_3d/v10/canonical/canonical_buildings_v10_conflicts.geojson
outputs/v10_dsm_audit/v10_building_completeness_per_cell.csv
outputs/v10_dsm_audit/v10_negative_gain_cells.csv
```

还建议存在：

```text
data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware_buffered.geojson
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_rankings.geojson
```

如果这些 optional 文件不存在，脚本会 warning，但仍会生成 building/conflict QA targets。

---

## 4. 运行方法

在项目根目录运行：

```bat
scripts\v10_run_alpha2_qa_targets.bat
```

或者：

```bat
python scripts\v10_alpha2_generate_qa_targets.py --config configs\v10\v10_alpha2_qa_config.example.json
```

---

## 5. 输出文件

默认输出到：

```text
outputs/v10_dsm_audit/alpha2_qa_targets/
```

包含：

```text
v10_alpha2_building_QA_targets.csv
v10_alpha2_building_QA_targets.geojson

v10_alpha2_conflict_QA_targets.csv
v10_alpha2_conflict_QA_targets.geojson

v10_alpha2_cell_QA_targets.csv
v10_alpha2_cell_QA_targets.geojson

v10_alpha2_manual_review_template.csv
v10_alpha2_QA_report.md
```

---

## 6. QGIS 检查方法

在 QGIS 中打开：

```text
outputs/v10_dsm_audit/alpha2_qa_targets/v10_alpha2_building_QA_targets.geojson
outputs/v10_dsm_audit/alpha2_qa_targets/v10_alpha2_conflict_QA_targets.geojson
outputs/v10_dsm_audit/alpha2_qa_targets/v10_alpha2_cell_QA_targets.geojson
data/rasters/v10/dsm_buildings_2m_augmented.tif
```

建议按这些字段上色：

```text
qa_category
qa_priority_score
height_confidence
height_warning
v09_tile_types
```

重点检查：

1. `large_low_confidence_building`
2. `transport_shelter_overhead_candidate`
3. `very_large_default_height_building`
4. `critical_tile_building_review`
5. `conflict_review_large_candidate`
6. `negative_gain_cell`
7. `old_top_hazard_cell;low_old_completeness;high_coverage_gain`

---

## 7. 人工决策建议

在 `v10_alpha2_manual_review_template.csv` 中填写：

```text
review_status
manual_decision
manual_height_m
manual_notes
```

建议 `manual_decision` 使用：

```text
keep_building_dsm
move_to_overhead_dsm
height_adjust
remove
merge_conflict
no_action
```

含义：

- `keep_building_dsm`：真实 ground-up building，保留在 building DSM；
- `move_to_overhead_dsm`：高架、天桥、covered walkway、shelter、roof-like canopy，未来进入 overhead DSM；
- `height_adjust`：保留 footprint，但修改高度；
- `remove`：false positive 或不应作为建筑；
- `merge_conflict`：dedup 冲突候选应合并进 canonical；
- `no_action`：检查后无需修改。

---

## 8. 下一步

完成 manual review 后，可以进入：

```text
v1.0-alpha.3: apply manual QA decisions
```

即根据 CSV 里的人工决策修改 canonical building layer：

1. remove / move overhead candidates；
2. update height_m；
3. merge selected conflict candidates；
4. rebuild augmented DSM；
5. rerun completeness audit。

然后才能进入：

```text
v1.0-beta: basic morphology recomputation + rank-shift audit
```
