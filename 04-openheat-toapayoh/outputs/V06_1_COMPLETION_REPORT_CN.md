# OpenHeat-ToaPayoh v0.6.1 完成报告

## 版本定位

v0.6.1 是对 v0.6 live calibration skeleton 的修订版，重点吸收 `V0.6优化意见.pdf` 中关于 API、时区、NEA/WBGT calibration、长期归档和科学定位的建议。

本版本的目标：

```text
把 v0.6 从“能接 live API 的原型”推进到
“可长期归档、可校准、科学表述更稳健的 heat-stress forecast prototype”。
```

## 已完成优化

### 1. API key 逻辑修正

- Open-Meteo 不再暗示需要 key；
- data.gov.sg / NEA 读接口默认不需要 key；
- `DATA_GOV_SG_API_KEY` 只作为 optional future-proof header。

### 2. NEA endpoint 策略修正

默认改用 legacy v1 endpoints：

```text
https://api.data.gov.sg/v1/environment/wbgt
https://api.data.gov.sg/v1/environment/air-temperature
https://api.data.gov.sg/v1/environment/relative-humidity
https://api.data.gov.sg/v1/environment/wind-speed
```

同时保留 v2 支持：

```bash
python scripts/run_nea_api_schema_check.py --mode live --api-version v2
```

### 3. 时区修正

新增：

```text
src/openheat_forecast/time_utils.py
```

所有 forecast/observation timestamp 统一转换到 timezone-aware `Asia/Singapore`。

### 4. Parser 稳健性增强

`normalise_realtime_station_readings()` 现在支持：

- v1 schema；
- v2 schema；
- null value；
- station list 变化；
- endpoint URL 和 fetch timestamp 归档。

### 5. Calibration 定位修正

v0.6.1 明确：

```text
WBGT_proxy -> official NEA WBGT
```

官方 WBGT 是校准目标，不是输入变量。

### 6. Nearest station representativeness

nearest-station table 新增：

```text
nearest_station_distance_m
station_representativeness
```

用于提醒：Toa Payoh 的 calibration 多半是 nearby/regional station proxy，不是每个街区 cell 的直接验证。

### 7. 长期归档

新增：

```text
.github/workflows/archive_nea_observations.yml
```

可每 15 分钟运行：

```bash
python scripts/archive_nea_observations.py --mode live --api-version v1
```

### 8. 新增测试

当前测试：

```text
9 passed
```

覆盖：

- old v1 NEA fixture；
- v2 fixture backward compatibility；
- null value handling；
- timezone pairing；
- nearest station representativeness；
- calibration readiness。

## 运行记录

已成功运行：

```bash
python scripts/run_live_forecast_v06.py --mode sample
python scripts/run_nea_api_schema_check.py --mode fixture
python scripts/archive_nea_observations.py --mode fixture --archive outputs/v06_1_fixture_archive_test.csv
pytest -q
```

生成关键输出：

```text
outputs/v06_offline_hourly_grid_heatstress_forecast.csv
outputs/v06_offline_hotspot_ranking.csv
outputs/v06_offline_event_windows.csv
outputs/v06_1_nea_station_observations_schema_check.csv
outputs/v06_1_grid_nearest_wbgt_station.csv
outputs/v06_1_fixture_archive_test.csv
outputs/v06_1_offline_hotspot_preview.png
```

## 仍需你本地完成的部分

### 1. 本地联网 live run

```bash
python scripts/run_live_forecast_v06.py --mode live
python scripts/run_nea_api_schema_check.py --mode live --api-version v1
```

### 2. 长期归档

```bash
python scripts/archive_nea_observations.py --mode live --api-version v1
```

或者启用 GitHub Actions。

### 3. 正式 calibration

最低要求：

```text
≥ 30 paired observations
≥ 2 days
至少包含 WBGT ≥ 31°C
```

更理想：

```text
包含 sunny / overcast / pre-thundershower regimes
包含 WBGT ≥ 33°C high period
```

### 4. v0.7 真实 grid features

v0.6.1 仍然使用 sample grid。v0.7 应优先制作真实 Toa Payoh grid features，而不是继续堆 API。

## 推荐项目表述

> OpenHeat-ToaPayoh v0.6.1 operationalises a live forecast and calibration-ready layer for neighbourhood heat-stress hotspot prioritisation. It uses Open-Meteo as background meteorology, official NEA WBGT observations as calibration targets, and local grid features as the basis for statistical downscaling of intra-neighbourhood heat-stress differences.

不要写：

> It accurately predicts official WBGT at every Toa Payoh street cell.
