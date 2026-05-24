# 从 v0.6 到 v0.7：你真正需要做的事

v0.6 已经把 forecast + official observation 接口打通。v0.7 的核心不是继续加模型，而是把 **sample grid** 换成 **真实 Toa Payoh spatial features**。

## 任务 1：制作真实 Toa Payoh 研究边界

建议范围：

```text
Toa Payoh Central + HDB blocks + MRT/bus interchange + neighbourhood parks
约 1.5–2.5 km²
```

输出：

```text
data/processed/toa_payoh_boundary.geojson
```

## 任务 2：制作 50 m 或 100 m grid

字段至少包括：

```text
cell_id
lat
lon
geometry
```

输出：

```text
data/processed/toa_payoh_grid_100m.geojson
```

## 任务 3：building features

需要：

```text
building_density
mean_building_height
max_building_height
svf_proxy
```

可先用：

```text
URA building footprint
HDB max floor level proxy
Google Open Buildings 2.5D height
```

没有高度时，先用 HDB floor × 3 m 做 proxy。

## 任务 4：shade / radiation proxy

v0.7 可先做简化：

```text
shade_fraction_0900
shade_fraction_1200
shade_fraction_1500
shade_fraction_daily_mean
```

v0.8 再升级为 SOLWEIG/UMEP。

## 任务 5：greenery / surface features

字段：

```text
gvi_percent
ndvi_mean
park_distance_m
water_distance_m
road_fraction
impervious_fraction
```

你的 GVI Calculator 可以用来补 POI-level / street-level GVI。v0.7 grid 版可以先用 NDVI/tree canopy proxy。

## 任务 6：exposure and vulnerability proxy

字段：

```text
elderly_proxy
outdoor_exposure_proxy
bus_stop_distance_m
school_distance_m
hawker_centre_distance_m
eldercare_distance_m
```

v0.7 先做 proxy，不需要声称是真实人口风险。

## 任务 7：替换 v0.6 sample grid

将最终 CSV 写成：

```text
data/processed/toa_payoh_grid_features_v07.csv
```

必须包含 v0.6 engine 需要的字段：

```text
cell_id,lat,lon,building_density,road_fraction,gvi_percent,svf,shade_fraction,park_distance_m,elderly_proxy,outdoor_exposure_proxy,land_use_hint
```

然后运行：

```bash
python scripts/run_live_forecast_v06.py --mode live --grid data/processed/toa_payoh_grid_features_v07.csv
```

## 任务 8：不要做太大

v0.7 的目标不是全新加坡，而是：

```text
一个真实 neighbourhood grid + 一个可信 hotspot ranking + 一个校准计划
```

这个比“全城 10 m UTCI”更容易被导师/招生官相信。
