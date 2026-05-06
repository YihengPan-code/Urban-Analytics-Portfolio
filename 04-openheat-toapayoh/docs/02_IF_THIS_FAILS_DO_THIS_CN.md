# 如果 v0.6.1 跑不起来：逐项排查指南

## 1. `ModuleNotFoundError: openheat_forecast`

你可能没有在项目根目录运行。

正确：

```bash
cd openheat_toapayoh_v0_6_1_feedback_optimised
python scripts/run_live_forecast_v06.py --mode sample
```

或者手动设置：

```bash
export PYTHONPATH=$PWD/src
```

## 2. `requests.exceptions.ConnectionError` 或 timeout

说明当前环境不能访问外网。先跑离线模式：

```bash
python scripts/run_live_forecast_v06.py --mode sample
python scripts/run_nea_api_schema_check.py --mode fixture
```

在你自己的电脑或学校网络上再跑：

```bash
python scripts/run_live_forecast_v06.py --mode live
```

## 3. data.gov.sg 返回 403 / rate limit

v0.6.1 默认不需要 API key。先确认你使用的是默认 v1 endpoint：

```bash
python scripts/run_nea_api_schema_check.py --mode live --api-version v1
```

如果仍然 403/429，说明当前网络或平台策略限制了访问。此时可以尝试注册 higher-rate-limit key，并作为 optional header 使用：

```bash
export DATA_GOV_SG_API_KEY="你的_optional_key"
python scripts/run_nea_api_schema_check.py --mode live --api-version v1
```

Windows PowerShell：

```powershell
$env:DATA_GOV_SG_API_KEY="你的_optional_key"
python scripts/run_nea_api_schema_check.py --mode live --api-version v1
```

## 4. API schema 变了

先打印原始 JSON：

```python
from openheat_forecast.live_api import fetch_datagov_realtime_api
import json
payload = fetch_datagov_realtime_api('wbgt', api_version='v1')
print(json.dumps(payload, indent=2)[:5000])
```

检查这些字段是否还存在：

```text
metadata.stations
items[].timestamp
items[].readings[].station_id
items[].readings[].value
metadata.reading_unit

如果你使用 `api_version="v2"`，再检查：

data.stations
data.readings
data.readings[].timestamp
data.readings[].data[].stationId
data.readings[].data[].value
data.readingUnit
```

如果字段名改变，改：

```text
src/openheat_forecast/live_api.py
normalise_realtime_station_readings()
```

## 5. `pythermalcomfort` 报错

v0.6.1 有 fallback UTCI proxy，所以一般不会崩。但如果你想正式算 UTCI，请确保安装：

```bash
pip install -U pythermalcomfort
```

如果 pythermalcomfort 的 API 版本变化，检查：

```python
from pythermalcomfort.models import utci
```

v0.6.1 当前调用位于：

```text
src/openheat_forecast/thermal_indices.py
calculate_utci_or_proxy()
```

## 6. 输出值看起来过高或过低

先检查：

```text
wind_speed_10m_ms 是否真的是 m/s
relative_humidity_2m 是否是 %
shortwave_radiation 是否是 W/m²
grid features 是否在 0–1 合理范围
```

最常见错误是：风速单位混淆。Open-Meteo 在 v0.6.1 live fetcher 中已使用 `wind_speed_unit=ms`，NEA wind speed 如果 readingUnit 是 knots，会自动乘以 0.514444。

## 7. 校准结果很奇怪

不要急着调模型，先看 paired data：

```python
paired_df[['station_id','time','wbgt_proxy_c','official_wbgt_c']].head(20)
```

确认：

- 时间是否同一时区；
- forecast valid_time 是否和 official observation timestamp 对齐；
- 是否只拿到了一个站；
- 是否只有低 WBGT 日；
- 是否把 station-level observation 错配到 grid-level prediction。

## 8. 最小可交付版本

即使 live API 暂时跑不起来，你仍然可以提交：

```text
sample forecast engine
API parser fixture tests
calibration skeleton
clear limitation and next-step plan
```

这已经比纯概念图强很多，因为它展示了系统架构、数据契约、校准思路和可复现代码。
