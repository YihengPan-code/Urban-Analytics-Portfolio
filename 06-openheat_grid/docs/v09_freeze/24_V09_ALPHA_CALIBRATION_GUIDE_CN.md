# OpenHeat v0.9-alpha：NEA WBGT archive QA + historical forecast pairing 指南

## 目标

v0.9-alpha 的目标不是训练正式 ML，而是建立 calibration data foundation：

```text
NEA official WBGT archive
+ Open-Meteo historical forecast/weather forcing
+ station metadata
+ optional nearest v0.8 grid morphology
→ v09_wbgt_station_pairs.csv
```

这个 paired table 是后续 v0.9-beta baseline calibration、v0.9-ML residual learning、uncertainty quantification 的基础。

## 新增文件

```text
configs/v09_alpha_config.example.json
scripts/v09_common.py
scripts/v09_archive_qa.py
scripts/v09_fetch_historical_forecast_for_archive.py
scripts/v09_build_wbgt_station_pairs.py
scripts/v09_evaluate_wbgt_pairs_baseline.py
scripts/v09_run_alpha_pipeline.bat
```

## 你需要先准备什么

### 1. NEA long-format archive

把你采集的 24h archive 放在：

```text
data/archive/nea_realtime_observations.csv
```

它必须是 v0.6.4+ 的 long format，包含：

```text
api_name
variable
value
timestamp
station_id
station_name
station_lat
station_lon
heat_stress_category
```

### 2. v0.8 grid morphology 文件

建议有：

```text
data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv
```

如果没有，v0.9-alpha 仍然能生成 station-weather pairs，但 nearest-grid morphology 会被标记为 missing。注意：Toa Payoh grid morphology 只对 S128 / S145 / S127 等附近站点有解释意义，全岛远处站点会被标记为 regional proxy。

### 3. 网络连接

`v09_fetch_historical_forecast_for_archive.py` 会访问 Open-Meteo：

```text
https://historical-forecast-api.open-meteo.com/v1/forecast
```

如果 historical forecast API 失败，会 fallback 到：

```text
https://archive-api.open-meteo.com/v1/archive
```

## 运行顺序

### Step 1: Archive QA

```bat
python scripts\v09_archive_qa.py --config configs\v09_alpha_config.example.json
```

输出：

```text
outputs/v09_alpha_calibration/v09_archive_QA_report.md
outputs/v09_alpha_calibration/v09_archive_variable_summary.csv
outputs/v09_alpha_calibration/v09_wbgt_station_summary.csv
outputs/v09_alpha_calibration/v09_wbgt_category_counts.csv
```

先打开 QA report，确认：

```text
- official_wbgt_c 存在
- station 数量合理
- WBGT 有 Low / Moderate / High
- S128 Bishan station 出现且距离 Toa Payoh 较近
```

### Step 2: 回填 Open-Meteo historical forecast/weather forcing

```bat
python scripts\v09_fetch_historical_forecast_for_archive.py --config configs\v09_alpha_config.example.json --api auto
```

输出：

```text
data/calibration/v09_historical_forecast_by_station_hourly.csv
outputs/v09_alpha_calibration/v09_historical_forecast_fetch_report.md
```

默认 `--api auto` 会先尝试 Historical Forecast API。如果失败，再尝试 Historical Weather API。Historical Forecast API 更适合 forecast calibration；Historical Weather API 是 reanalysis/hindcast fallback。

### Step 3: 生成 paired calibration table

```bat
python scripts\v09_build_wbgt_station_pairs.py --config configs\v09_alpha_config.example.json
```

输出：

```text
data/calibration/v09_wbgt_station_pairs.csv
outputs/v09_alpha_calibration/v09_wbgt_pairing_QA_report.md
outputs/v09_alpha_calibration/v09_raw_proxy_baseline_metrics.csv
outputs/v09_alpha_calibration/v09_raw_proxy_metrics_by_station.csv
```

`v09_wbgt_station_pairs.csv` 是 v0.9-alpha 最重要的输出。

### Step 4: baseline diagnostic

```bat
python scripts\v09_evaluate_wbgt_pairs_baseline.py --config configs\v09_alpha_config.example.json
```

输出：

```text
outputs/v09_alpha_calibration/v09_baseline_calibration_diagnostics.md
outputs/v09_alpha_calibration/v09_baseline_overall_metrics.csv
outputs/v09_alpha_calibration/v09_baseline_metrics_by_station.csv
outputs/v09_alpha_calibration/v09_baseline_event_detection_metrics.csv
outputs/v09_alpha_calibration/v09_residual_by_hour.csv
```

## 一键运行

如果上面文件都准备好了，可以运行：

```bat
scripts\v09_run_alpha_pipeline.bat
```

## 输出如何解释

### `v09_wbgt_station_pairs.csv`

每行是：

```text
one official WBGT observation × matched Open-Meteo historical forcing
```

核心字段：

```text
timestamp_sgt
station_id
official_wbgt_c
heat_stress_category
temperature_2m
relative_humidity_2m
wind_speed_10m
shortwave_radiation
direct_radiation
diffuse_radiation
cloud_cover
wbgt_proxy_weather_only_c
wbgt_residual_weather_only_c
nearest_grid_cell
nearest_grid_distance_m
morphology_representativeness
```

### 注意：proxy 不是 official WBGT

`wbgt_proxy_weather_only_c` 是 screening-level physics proxy。它用于 residual calibration，不应被称为 official WBGT。

### 注意：morphology 不是全岛有效

Toa Payoh grid morphology 对附近站点有意义，例如 Bishan / MacRitchie / Kallang；对于全岛远处站点，只能作为 regional placeholder，不应解释其 local morphology residual。

## v0.9-alpha 的边界

可以说：

```text
v0.9-alpha establishes the archive QA and paired calibration dataset needed for official-WBGT residual analysis.
```

不要说：

```text
v0.9-alpha trains a validated ML model.
```

24h archive 只能用于 calibration smoke test。正式 ML residual learning 至少需要 14–30 天，更理想是 30–60 天，并使用 leave-one-station-out / leave-one-day-out CV。

## 下一步

v0.9-beta：

```text
raw physics proxy
→ global bias correction
→ linear calibration
→ station residual diagnostics
```

v0.9-ML：

```text
physics proxy residual learning
+ quantile/conformal uncertainty
```

这符合 ML 文件里的建议：ML 应用于 residual learning 和 uncertainty，不应用来替代 Open-Meteo、thermal index formulas 或 deterministic GIS features。
