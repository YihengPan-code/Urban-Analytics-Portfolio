# OpenHeat v0.8-beta review hotfix

本补丁针对 v0.8 UMEP+vegetation 合并与对比脚本的三个工程稳健性问题：

1. `EXPLANATORY_COLS` 原本硬编码且缺列时静默跳过。现在脚本会打印 ranking/grid 实际列名，并在 QA report 中记录缺失的 expected columns 与 fallback risk columns。
2. GeoJSON 原本使用 `how="right"`，当 ranking 里存在 geometry 表没有的 `cell_id` 时会写出 null geometry。现在改为 geometry-safe inner merge，并输出 missing geometry cell_id 清单。
3. Comparison 脚本原本没有显式报告 NaN。现在会统计 old/new metric 与 rank 的 NaN 数量，并只用 non-NaN clean subset 计算 Spearman 和 Top-N overlap。

## 使用

覆盖到项目根目录后正常运行：

```bat
python scripts\v08_finalize_umep_with_veg_forecast_outputs.py --forecast-dir outputs\v08_umep_with_veg_forecast_live --grid-csv data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv --grid-geojson data\grid\toa_payoh_grid_v07_features.geojson
```

```bat
python scripts\v08_compare_proxy_vs_umep_with_veg_forecast.py --old-ranking outputs\v07_beta_final_forecast_live\v06_live_hotspot_ranking.csv --new-ranking outputs\v08_umep_with_veg_forecast_live\v06_live_hotspot_ranking.csv --metric hazard_score
```

## 新增诊断输出

- `*_hotspot_QA_report.md` 会包含 missing explanatory columns 与 GeoJSON geometry diagnostics。
- 如果有 ranking cell 缺 geometry，会输出 `*_missing_geometry_cell_ids.csv`。
- comparison 会额外输出 `v08_proxy_vs_umep_with_veg_rank_comparison_clean.csv`，即参与 Spearman / Top-N overlap 的 clean subset。
