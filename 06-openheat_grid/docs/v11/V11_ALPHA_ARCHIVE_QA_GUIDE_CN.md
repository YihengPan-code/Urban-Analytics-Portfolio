# OpenHeat v1.1-alpha Archive QA 指南

## 目标

v1.1-alpha 的目标不是训练 ML，而是把后台持续积累的 archive 变成一个可检查、可复现、可训练的 paired dataset：

```text
station × timestamp × official_WBGT × weather_forcing × raw_proxy × v10_features
```

这一步回答：

```text
archive 到底有多少天？
每个 station 有多少样本？
WBGT≥31 / ≥33 event 够不够？
weather forcing 是否能和 official WBGT 对齐？
后续能不能做 calibration / ML？
```

## 运行前你需要准备什么

### 1. NEA / official WBGT archive

默认脚本会搜索：

```text
data/archive/**/*wbgt*.csv
outputs/archive/**/*wbgt*.csv
```

至少需要包含：

```text
timestamp
station_id
official_wbgt_c / wbgt_c / WBGT
```

如果列名不同，编辑：

```text
configs/v11/v11_alpha_archive_config.example.json
```

在 `column_overrides.nea` 中写入真实列名。

### 2. Weather / Open-Meteo archive

默认搜索：

```text
data/archive/**/*openmeteo*.csv
data/archive/**/*weather*.csv
```

建议包含：

```text
timestamp
air_temperature_c
relative_humidity_pct
wind_speed_m_s
shortwave_w_m2
cloud_cover_pct
precipitation_mm
```

如果是全 AOI 一套 weather forcing，不需要 `station_id`；脚本会按 timestamp merge 到每个 station。

### 3. station-to-cell mapping

请编辑：

```text
configs/v11/station_to_cell.example.csv
```

把每个 NEA station 映射到一个代表性的 v10 grid cell：

```text
station_id,station_name,cell_id,station_lat,station_lon,notes
S128,NEA station S128,TP_0565,,,
```

这一步对 v1.1-beta 的 morphology / overhead-aware calibration 很重要。没有它，alpha 仍能跑，但 v10 spatial features 可能无法合并。

## 一键运行

```bat
scripts\v11_run_alpha_archive_pipeline.bat
```

## 输出

```text
outputs/v11_alpha_archive/v11_archive_inventory_report.md
outputs/v11_alpha_archive/v11_paired_dataset_report.md
outputs/v11_alpha_archive/v11_archive_QA_report.md
outputs/v11_alpha_archive/v11_cv_split_plan.md

data/calibration/v11/v11_station_weather_pairs.csv
data/calibration/v11/v11_cv_splits.csv
```

## 跑完后重点检查

打开：

```text
outputs/v11_alpha_archive/v11_archive_QA_report.md
```

重点看：

```text
Rows
Stations
Days
WBGT≥31 count
WBGT≥33 count
missingness
highest-WBGT days
```

## 判断标准

```text
< 7 days        只适合 smoke test
7–14 days       可以做 baseline replay
30+ days        可以做 residual ML pilot
60+ days        可以做较可信的 LOSO + blocked-time CV
跨季节           才能谈 operational robustness
```
