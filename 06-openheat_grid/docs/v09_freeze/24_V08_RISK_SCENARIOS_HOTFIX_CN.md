# OpenHeat v0.8 risk-scenarios finalisation hotfix

## 修复的问题

如果 `scripts/v08_generate_risk_scenarios.py` 已经成功写出：

```text
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_rankings.csv
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_topn_overlap.csv
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_topn_summary.csv
```

但在 `pd.concat(top_tables, ...)` 阶段报：

```text
pandas.errors.InvalidIndexError: Reindexing only valid with uniquely valued Index objects
```

通常是因为某个中间 top table 出现重复列名或非唯一列索引。

这个 hotfix 不重算风险情景分数，而是读取已生成的 `v08_risk_scenario_rankings.csv`，重新生成缺失的 top cells、GeoJSON、QA report 和 metadata。

## 使用方法

在项目根目录运行：

```bat
python scripts\v08_finalize_risk_scenarios_hotfix.py
```

如果路径不同，可以手动指定：

```bat
python scripts\v08_finalize_risk_scenarios_hotfix.py ^
  --scenario-csv outputs\v08_umep_with_veg_forecast_live\risk_scenarios\v08_risk_scenario_rankings.csv ^
  --out-dir outputs\v08_umep_with_veg_forecast_live\risk_scenarios ^
  --geometry outputs\v08_umep_with_veg_forecast_live\v08_umep_with_veg_hotspot_ranking_with_grid_features.geojson
```

## 输出

```text
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_top_cells.csv
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_topn_overlap.csv
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_topn_summary.csv
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_rankings.geojson
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_QA_report.md
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_metadata.json
```

## 说明

- 这个脚本会自动检查并处理重复列名。
- GeoJSON 使用 inner merge，并过滤空 geometry，避免 QGIS 读取 null geometry feature。
- 如果某个 scenario rank 列不存在，会跳过并给出 warning。
