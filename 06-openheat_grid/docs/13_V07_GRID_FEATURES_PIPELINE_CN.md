# OpenHeat-ToaPayoh v0.7-alpha Grid Features Pipeline

## 目标

v0.7-alpha 的目标不是一次性做完 17 个最高精度 feature，而是把 v0.6 的 `data/sample/toa_payoh_grid_sample.csv` 替换成一个真实 Toa Payoh 100 m grid feature table。

输出文件：

```text
data/grid/toa_payoh_grid_v07.geojson
data/grid/toa_payoh_grid_v07.csv
data/grid/toa_payoh_grid_v07_features.csv
data/grid/toa_payoh_grid_v07_features.geojson
data/features/*.csv
data/features/provenance/*.yaml
outputs/v07_grid_features_QA_report.md
outputs/v07_grid_feature_preview.png
```

`toa_payoh_grid_v07_features.csv` 可以直接作为 forecast engine 的 grid 输入：

```bat
python scripts\run_live_forecast_v06.py --mode live --grid data\grid\toa_payoh_grid_v07_features.csv
```

## 当前 pipeline 能自动提取的 feature

只要原始数据放进 `data/raw/`，脚本可以自动生成：

```text
cell_id
lat
lon
centroid_x_svy21
centroid_y_svy21
building_density
road_fraction
land_use_hint
land_use_raw
land_use_fraction
gpr_area_weighted
park_distance_m
large_park_distance_m
water_distance_m
mean_building_height_m
max_building_height_m
svf
shade_fraction
gvi_percent
tree_canopy_fraction
impervious_fraction
elderly_proxy
outdoor_exposure_proxy
forecast_spatial_note
```

其中 `svf`、`shade_fraction`、`gvi_percent` 在 v0.7-alpha 里是 screening-level proxies，不是 UMEP/SOLWEIG 或街景分割的真实输出。

## 安装额外依赖

如果你已经装好了 v0.6 的依赖，还需要补装 geospatial 包：

```bat
pip install -r requirements_v07_geospatial.txt
```

如果 Windows 上 `geopandas` 安装失败，建议用 conda：

```bat
conda install -c conda-forge geopandas pyogrio rasterio shapely pyproj matplotlib
```

## 第一步：用 sample fixture 测试 pipeline

先不要下载大数据，先确认脚本能跑：

```bat
python scripts\v07_build_grid_features.py --config configs\v07_grid_features_config.sample_fixture.json
```

成功后检查：

```bat
python -c "import pandas as pd; df=pd.read_csv('data/grid/toa_payoh_grid_v07_features.csv'); print(df.head().to_string()); print(df.columns.tolist())"
```

再用 v0.6 forecast engine 测试：

```bat
python scripts\run_live_forecast_v06.py --mode sample --grid data\grid\toa_payoh_grid_v07_features.csv --out-dir outputs\v07_sample_forecast_test
```

## 第二步：下载官方开放数据

推荐用脚本下载三个官方数据集：

```bat
python scripts\v07_download_official_geodata.py --datasets ura_buildings ura_land_use nparks_parks
```

它会保存到：

```text
data/raw/ura_masterplan2019_buildings.geojson
data/raw/ura_masterplan2019_land_use.geojson
data/raw/nparks_parks_nature_reserves.geojson
```

这些数据较大：building layer 约 50 MB，land-use layer 约 166 MB，parks layer 约 2–3 MB。

## 第三步：准备 roads / water

当前脚本可以读取 `roads` 和 `water` vector 文件，但不会自动从 OSM 抽取。你有两个选项：

### 快速做法：QGIS 手动导出

1. 下载 Geofabrik Singapore OSM PBF。
2. 在 QGIS 打开 OSM/PBF 或转换后的 GeoPackage。
3. 选择 Toa Payoh AOI 周围 roads lines，导出为：

```text
data/raw/osm_roads_toa_payoh.geojson
```

4. 选择 water polygons，导出为：

```text
data/raw/osm_water_toa_payoh.geojson
```

### 暂时跳过

如果没有 roads / water 文件，可以在 config 中把路径设为空字符串。脚本会把 `road_fraction` 填 0，`water_distance_m` 填 9999。v0.7-alpha 可以先这样跑，但 ranking 的 road heat / water cooling 解释会弱一些。

## 第四步：跑真实 Toa Payoh grid features

编辑：

```text
configs/v07_grid_features_config.example.json
```

确认 raw paths 指向你的真实数据，然后运行：

```bat
python scripts\v07_build_grid_features.py --config configs\v07_grid_features_config.example.json
```

检查 QA：

```text
outputs/v07_grid_features_QA_report.md
outputs/v07_grid_feature_preview.png
```

## 第五步：接入 forecast engine

用真实 grid 跑 sample forecast：

```bat
python scripts\run_live_forecast_v06.py --mode sample --grid data\grid\toa_payoh_grid_v07_features.csv --out-dir outputs\v07_forecast_sample
```

用真实 grid 跑 live forecast：

```bat
python scripts\run_live_forecast_v06.py --mode live --grid data\grid\toa_payoh_grid_v07_features.csv --out-dir outputs\v07_forecast_live
```

核心输出：

```text
outputs/v07_forecast_live/v06_live_hotspot_ranking.csv
outputs/v07_forecast_live/v06_live_event_windows.csv
outputs/v07_forecast_live/v06_live_hourly_grid_heatstress_forecast.csv
```

## v0.7-alpha 的边界

v0.7-alpha 可以支持“真实 spatial downscaling grid”，但不能声称是街道级物理模拟。特别注意：

- `svf` 是 morphology proxy，不是真实 SVF。
- `shade_fraction` 是 screening proxy，不是 UMEP shadow output。
- `gvi_percent` 默认从 tree canopy proxy 转换，不是真实 street-view GVI。
- `elderly_proxy` 和 `outdoor_exposure_proxy` 是 placeholder，需要 v0.7.1 重新定义。
- GHSL height 如使用，是 100 m average building height，不适合直接做 building-level shadow。

## 后续手动/外部步骤

你自己需要做或准备：

1. 确定研究范围。建议先用 1–2 km² Toa Payoh Central / Town Park / Bishan edge，不要全 Toa Payoh。
2. 下载官方 building / land-use / parks 数据，或运行下载脚本。
3. 准备 OSM roads/water，或暂时跳过。
4. 如要 NDVI/Dynamic World/GHSL：注册 Google Earth Engine，导出 `cell_id, tree_canopy_fraction, ndvi_mean, mean_building_height_m` CSV 后放进 config 的 `optional_feature_csv`。
5. 如要真实 SVF/shade：安装 QGIS + UMEP，准备 DSM 后导出 grid-level CSV，在 v0.8/v0.9 替换 proxy。

