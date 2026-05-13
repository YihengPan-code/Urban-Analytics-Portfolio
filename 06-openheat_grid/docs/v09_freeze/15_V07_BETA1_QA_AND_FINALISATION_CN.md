# OpenHeat-ToaPayoh v0.7-beta.1：Forecast 输出整理与 QA 指南

## 目的

v0.7-beta.1 不改变热压力模型公式，不重新调整 UTCI/WBGT proxy 权重。它只做三件事：

1. 将 v0.7-beta grid feature 中的解释性列安全 merge 回 hotspot ranking，避免 pandas `_x/_y` 列名冲突。
2. 自动生成 hotspot QA 报告，包括 top20 vs all cells、SVF 饱和、shade floor、tree canopy zero、impervious 修复摘要、hazard vs risk 分离。
3. 生成可直接在 QGIS 打开的 hotspot ranking GeoJSON。

## 推荐输入

正式 beta grid 建议使用：

```text
data/grid/toa_payoh_grid_v07_features_beta_final.csv
```

如果你刚做完 impervious 修复，先执行：

```bat
copy data\grid\toa_payoh_grid_v07_features_beta_gee_impervfix.csv data\grid\toa_payoh_grid_v07_features_beta_final.csv
```

然后跑 forecast：

```bat
python scripts\run_live_forecast_v06.py --mode live --grid data\grid\toa_payoh_grid_v07_features_beta_final.csv --out-dir outputs\v07_beta_final_forecast_live
```

## 生成 v0.7-beta.1 QA 输出

```bat
python scripts\v07_beta1_finalize_forecast_outputs.py --forecast-dir outputs\v07_beta_final_forecast_live --grid-csv data\grid\toa_payoh_grid_v07_features_beta_final.csv --grid-geojson data\grid\toa_payoh_grid_v07_features.geojson
```

输出文件：

```text
outputs/v07_beta_final_forecast_live/v07_beta1_hotspot_ranking_with_grid_features.csv
outputs/v07_beta_final_forecast_live/v07_beta1_hotspot_ranking_with_grid_features.geojson
outputs/v07_beta_final_forecast_live/v07_beta1_top_vs_all_summary.csv
outputs/v07_beta_final_forecast_live/v07_beta1_hazard_vs_risk_comparison.csv
outputs/v07_beta_final_forecast_live/v07_beta1_feature_diagnostics.json
outputs/v07_beta_final_forecast_live/v07_beta1_hotspot_QA_report.md
```

## 如何解读 top20 vs all

理想情况下，top20 hotspot 应该相对于所有 grid 呈现：

- 更高 `max_utci_c` / `max_wbgt_proxy_c`；
- 更高 `hazard_score`；
- 更高 `svf`；
- 更低 `shade_fraction`；
- 更低 `gvi_percent` / `tree_canopy_fraction` / `ndvi_mean`；
- 更高 `road_fraction` 或 `impervious_fraction`。

如果 top20 hotspot 反而出现在高树冠、高 NDVI、高 shade 的区域，需要回看地图和 cooling proxy 权重。

## hazard rank vs risk rank

- `hazard_score`：更接近“物理热压力最高的地方”。
- `risk_priority_score`：综合了 hazard + vulnerability + exposure。

在 v0.7-beta 阶段，`elderly_proxy` 与 `outdoor_exposure_proxy` 仍然较弱，所以正式叙述中应优先使用 **hazard hotspot**，而不是过度解释 risk priority。

## SVF 饱和检查

QA 报告会自动记录：

```text
svf>=0.98 share
svf>=0.95 share
```

如果 `svf>=0.98` 超过 40%，说明 SVF proxy 过度饱和；如果低于 20%，暂时可以接受。v0.8/v0.9 应用 UMEP-derived SVF 替代 proxy。

## 地图 QA

打开：

```text
outputs/v07_beta_final_forecast_live/v07_beta1_hotspot_ranking_with_grid_features.geojson
```

在 QGIS 中按 `rank`、`risk_priority_score` 或 `hazard_score` 渲染。检查 top hotspot 是否落在：

- 开阔道路/铺装面；
- 低树冠、低 NDVI cell；
- 遮阴不足的 HDB 空地或交通节点；
- 商业/交通/户外节点附近。

如果 hotspot 大量落在水体、公园密林或明显阴凉区域，需要回看 `water_fraction`、`gvi_percent`、`shade_fraction` 和 `park_distance_m`。
