# OpenHeat v0.8-beta: UMEP building + canopy morphology merge and forecast guide

本 patch 用于将 `toa_payoh_grid_v08_umep_morphology_with_veg.csv` 合并进既有 v0.7/v0.7.1 grid，并用 UMEP building+canopy 输出替换：

- `svf` ← `svf_umep_mean_open_with_veg`
- `shade_fraction` ← `shade_fraction_umep_10_16_open_with_veg`

旧 proxy 会保留为：

- `svf_proxy_v07`
- `shade_fraction_proxy_v07`

## 推荐运行顺序

```bat
python scripts\v08_apply_umep_morphology_with_veg.py --base-grid data\grid\toa_payoh_grid_v07_features_beta_final_v071_risk.csv --umep data\grid\toa_payoh_grid_v08_umep_morphology_with_veg.csv --out-grid data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv
```

```bat
python scripts\run_live_forecast_v06.py --mode live --grid data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv --out-dir outputs\v08_umep_with_veg_forecast_live
```

```bat
python scripts\v08_finalize_umep_with_veg_forecast_outputs.py --forecast-dir outputs\v08_umep_with_veg_forecast_live --grid-csv data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv --grid-geojson data\grid\toa_payoh_grid_v07_features.geojson
```

```bat
python scripts\v08_compare_proxy_vs_umep_with_veg_forecast.py --old-ranking outputs\v07_beta_final_forecast_live\v06_live_hotspot_ranking.csv --new-ranking outputs\v08_umep_with_veg_forecast_live\v06_live_hotspot_ranking.csv --metric hazard_score
```

或者直接运行：

```bat
scripts\v08_run_umep_with_veg_forecast_workflow.bat
```

## 输出文件

```text
data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv
outputs/v08_umep_with_veg_morphology_merge_QA.md
outputs/v08_umep_with_veg_forecast_live/v08_umep_with_veg_hotspot_ranking_with_grid_features.csv
outputs/v08_umep_with_veg_forecast_live/v08_umep_with_veg_hotspot_ranking_with_grid_features.geojson
outputs/v08_umep_with_veg_forecast_live/v08_umep_with_veg_hotspot_QA_report.md
outputs/v08_umep_with_veg_comparison/v08_proxy_vs_umep_with_veg_forecast_comparison.md
```

## 解释边界

这一步是 **3D morphology upgrade**，不是完整 SOLWEIG/Tmrt 模拟。UMEP 输出已经包含 building + canopy 的几何遮蔽与阴影，但 forecast engine 仍使用现有 UTCI/WBGT proxy 框架。`svf` 和 `shade_fraction` 与 v0.7 proxy 相比物理可信度更高，但本阶段仍未显式模拟材料反照率、墙面温度、完整辐射通量、CFD 风场或真实行人活动。

## 推荐主版本

v0.8-beta 主版本建议使用：

```text
svf = svf_umep_mean_open_with_veg
shade_fraction = shade_fraction_umep_10_16_open_with_veg
```

这比 building-only UMEP 更适合新加坡赤道城市，因为建筑阴影在正午很短，而树冠遮阴对行人热暴露贡献更大。
