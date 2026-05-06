# OpenHeat-ToaPayoh v0.6：Live API 与 WBGT 校准指南

## 1. v0.6 的定位

v0.6 是从“sample forecast engine”走向“真实预测系统”的第一步。它完成的是：

```text
真实天气预报接入 → 街区网格热压力预测 → 官方观测接入 → 校准准备
```

它还不是最终模型。正式的 operational warning 至少还需要：

- 多日 / 多热事件 official WBGT observation；
- forecast vs observation hindcast 验证；
- Toa Payoh 真实 grid features；
- Tmrt/SVF/shade 的更物理化估计；
- 不确定性面板。

## 2. 先跑离线模式

```bash
python scripts/run_live_forecast_v06.py --mode sample
python scripts/run_nea_api_schema_check.py --mode fixture
pytest -q
```

这一步证明你的 Python 环境、热指标计算、hotspot ranking、NEA response parser、calibration skeleton 都能跑通。

## 3. 再跑 live forecast

```bash
python scripts/run_live_forecast_v06.py --mode live
```

成功后看：

```text
outputs/v06_live_hotspot_ranking.csv
outputs/v06_live_event_windows.csv
```

`v06_live_hotspot_ranking.csv` 是 v0.6 最重要的输出。它回答：

> 未来 4 天内，Toa Payoh 哪些 grid cell 的 heat-stress priority 最高？

## 4. 再检查 NEA/data.gov.sg 观测

```bash
python scripts/run_nea_api_schema_check.py --mode live
```

成功后看：

```text
outputs/v06_live_station_observations.csv
outputs/v06_live_grid_nearest_stations.csv
```

这一步不是为了预测，而是为了检查：

- API 是否能访问；
- station schema 有没有变化；
- wind speed unit 是否需要 knots → m/s；
- Toa Payoh grid 最近对应哪些 official stations；
- official WBGT 是否能被抓取。

## 5. WBGT 校准应该怎么做

不要用一天三个 fixture 点就宣称“校准完成”。真正校准需要这样做：

### Step A：每天定时抓 official WBGT

建议每 15–30 分钟抓一次：

```bash
python scripts/run_nea_api_schema_check.py --mode live
```

长期建议写 cron job：

```bash
*/15 * * * * cd /path/to/openheat && python scripts/archive_nea_observations.py
```

v0.6 还没有 archive 脚本，你可以先手动跑。

### Step B：同时保存 forecast issue time

每次跑 Open-Meteo forecast 时，需要保存：

```text
forecast_issue_time
valid_time
forecast lead time
predicted wbgt_proxy_c
```

这样以后才能算：

```text
lead_time_1h skill
lead_time_6h skill
lead_time_24h skill
lead_time_48h skill
```

### Step C：做 paired table

目标表长这样：

```text
station_id
valid_time
lead_time_h
wbgt_proxy_c
official_wbgt_c
air_temperature_c
relative_humidity_percent
wind_speed_ms
```

然后使用：

```python
from openheat_forecast.calibration import fit_linear_calibration, apply_linear_calibration
model = fit_linear_calibration(paired_df, proxy_col='wbgt_proxy_c', obs_col='official_wbgt_c')
```

### Step D：报告校准质量

最少报告：

```text
MAE
RMSE
Bias
Correlation
N observations
N stations
N heat-stress days
moderate/high WBGT coverage
```

如果没有 moderate/high WBGT 样本，不能说模型能用于热浪预警。

## 6. v0.6 适合怎么写进 portfolio

可以写：

> v0.6 operationalised the data-ingestion and calibration layer by connecting forecast meteorology with official Singapore WBGT and station observations. The system can now generate 4-day hotspot rankings and is ready for multi-day hindcast calibration.

不要写：

> v0.6 已经是官方级 heat-stress warning system。

