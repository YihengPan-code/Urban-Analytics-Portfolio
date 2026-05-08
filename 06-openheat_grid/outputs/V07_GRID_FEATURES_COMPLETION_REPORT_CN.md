# OpenHeat-ToaPayoh v0.7-alpha Grid Features Pipeline 完成报告

本版本在 v0.6.4.1 forecast/calibration prototype 基础上新增了真实空间降尺度 grid feature pipeline。

## 新增内容

```text
src/openheat_grid/
  geospatial.py
  grid.py
  features.py
  provenance.py

scripts/
  v07_build_grid_features.py
  v07_download_official_geodata.py
  v07_extract_osm_roads_water.py

configs/
  v07_grid_features_config.example.json
  v07_grid_features_config.sample_fixture.json

earth_engine/
  v07_export_height_vegetation_to_grid.js

docs/
  13_V07_GRID_FEATURES_PIPELINE_CN.md

requirements_v07_geospatial.txt
```

## 核心输出

```text
data/grid/toa_payoh_grid_v07.geojson
data/grid/toa_payoh_grid_v07_features.csv
data/grid/toa_payoh_grid_v07_features.geojson
data/features/*.csv
data/features/provenance/*.yaml
outputs/v07_grid_features_QA_report.md
outputs/v07_grid_feature_preview.png
```

## 已测试

离线 sample fixture pipeline 可以运行；生成的 `toa_payoh_grid_v07_features.csv` 已经能被 v0.6 forecast engine 作为 grid 输入读取。

```bat
python scripts\v07_build_grid_features.py --config configs\v07_grid_features_config.sample_fixture.json
python scripts\run_live_forecast_v06.py --mode sample --grid data\grid\toa_payoh_grid_v07_features.csv --out-dir outputs\v07_sample_forecast_test
```

测试：

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_v07_grid_features.py -q
1 passed
```

## 重要边界

- v0.7-alpha 的 `svf`、`shade_fraction`、`gvi_percent` 是 screening-level proxies。
- 真实 SVF / shade 需要 QGIS + UMEP + DSM。
- NDVI / Dynamic World / GHSL 可以通过 Earth Engine 模板导出 CSV 后接入。
- `elderly_proxy` 和 `outdoor_exposure_proxy` 现在是 placeholder，建议 v0.7.1 单独定义。
