# OpenHeat v1.0-alpha.3 Manual QA Application Guide

## 目标

v10-alpha.3 用于把人工 QA 结果应用到 v10-alpha.1 的 canonical building layer：

1. 将 `v10_bldg_000690` 从 ground-up building DSM 移到 overhead candidates；
2. 合并已人工确认的 Top conflict targets；
3. 追加手动 digitised 的 missing buildings；
4. 输出 reviewed canonical layer；
5. 生成 reviewed augmented building DSM；
6. 重新做 completeness audit。

## 输入

默认读取：

```text
data/features_3d/v10/height_imputed/canonical_buildings_v10_height.geojson
data/features_3d/v10/canonical/canonical_buildings_v10_conflicts.geojson
data/features_3d/v10/manual_qa/manual_missing_buildings_v10.geojson
outputs/v10_dsm_audit/alpha2_qa_targets/v10_alpha2_conflict_QA_targets.csv
```

如果你已经填写了人工 review 表，则放在：

```text
data/features_3d/v10/manual_qa/v10_alpha2_manual_review_filled.csv
```

没有该 CSV 时，脚本会根据配置默认：

- 把 `v10_bldg_000690` 移到 overhead candidates；
- 自动合并 Top 20 conflict targets（前提是你已经人工确认它们是真实建筑）；
- 追加 `manual_missing_buildings_v10.geojson`。

## 运行

```bat
scripts\v10_run_alpha3_manual_qa_pipeline.bat
```

或者分步：

```bat
python scripts\v10_alpha3_apply_manual_qa_decisions.py --config configs\v10\v10_alpha3_manual_qa_config.example.json
python scripts\v10_rasterize_reviewed_dsm.py --config configs\v10\v10_alpha3_manual_qa_config.example.json
python scripts\v10_alpha3_reviewed_completeness_audit.py --config configs\v10\v10_alpha3_manual_qa_config.example.json
```

## 输出

```text
data/features_3d/v10/height_imputed/canonical_buildings_v10_height_reviewed.geojson
data/features_3d/v10/manual_qa/overhead_candidates_v10.geojson
data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif
outputs/v10_dsm_audit/v10_alpha3_manual_decisions_report.md
outputs/v10_dsm_audit/v10_alpha3_rasterize_reviewed_dsm_QA.md
outputs/v10_dsm_audit/v10_alpha3_completeness_gain_report.md
```

## 判断标准

通过条件：

- reviewed DSM 的 `nodata` 仍为 None；
- `v10_bldg_000690` 不再进入 reviewed building DSM，而进入 overhead candidates；
- Top conflict targets 被合并进 reviewed canonical；
- manual missing buildings 被追加；
- T01/T02/T05/T06 不应回到旧 DSM gap 状态；
- reviewed completeness 可以略低于 alpha.1，因为 station canopy / shelter 不再作为 ground-up building 计入，这是合理的。

## 进入 v10-beta 前

请检查：

```text
outputs/v10_dsm_audit/v10_alpha3_manual_decisions_report.md
outputs/v10_dsm_audit/v10_alpha3_rasterize_reviewed_dsm_QA.md
outputs/v10_dsm_audit/v10_alpha3_completeness_gain_report.md
```

如果这些通过，就可以进入 v10-beta basic morphology recomputation。
