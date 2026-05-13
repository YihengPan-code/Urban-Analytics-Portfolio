# OpenHeat v1.1 long-term archive collector guide

## 1. 这个脚本解决什么问题

`v11_archive_collect_once.py` 是为 v1.1 / v11 calibration 和 ML 准备的长期数据采集器。它不再保存巨大的全 grid hourly forecast 文件，而是保存能直接用于 calibration / residual learning / threshold scan 的轻量数据：

```text
NEA official WBGT + NEA station weather
Open-Meteo hourly forcing snapshots
station × timestamp operational pairing table
v10 morphology / overhead feature joins
fallback proxy features for smoke tests
run-level QA report
```

它的核心输出可以直接给：

```text
v1.1-alpha archive QA
v1.1-beta calibration baselines
v1.1-gamma ML residual learning
v1.1-delta uncertainty / threshold scans
```

## 2. 为什么不保存巨大的 hourly grid forecast CSV

之前 `v06_live_hourly_grid_heatstress_forecast.csv` 一类文件可达数百 MB，不适合长期 archive，也不适合 Git。长期 ML 校准真正需要的是：

```text
official WBGT observation
valid-time weather forcing
station/grid morphology context
model proxy / residual
```

而不是每次都保存全 AOI × 全 hour × 全 variable 的巨大展开表。

## 3. 运行前准备

把本包解压到项目根目录：

```text
06-openheat_grid/
├─ configs/v11/v11_longterm_archive_config.example.json
├─ scripts/v11_archive_collect_once.py
├─ scripts/v11_archive_collect_once.bat
├─ scripts/v11_archive_loop_15min.bat
├─ scripts/v11_archive_preflight.py
└─ docs/v11/V11_LONGTERM_ARCHIVE_GUIDE_CN.md
```

安装依赖：

```bash
pip install pandas numpy requests tabulate
```

`tabulate` 不是必需，但可以让 report markdown table 更好看。

## 4. API key

Data.gov.sg API 在测试时可以无 key 访问，但生产 workflow 官方建议申请 API key 以获得更高 rate limits 和维护通知。设置方式：

```bat
setx DATA_GOV_SG_API_KEY "你的key"
```

重新打开 CMD 后生效。没有 key 时脚本仍会尝试请求。

## 5. 先跑 preflight

```bat
scripts\v11_archive_preflight.bat
```

检查：

```text
NEA endpoints 是否启用
v10 feature files 是否存在
station_to_cell.csv 是否需要编辑
Open-Meteo location 设置
```

## 6. 收集一次 snapshot

```bat
scripts\v11_archive_collect_once.bat
```

输出：

```text
data/archive/v11_longterm/long/nea_realtime_observations_v11_longterm.csv
data/archive/v11_longterm/normalized/nea_wbgt_v11_longterm_normalized.csv
data/archive/v11_longterm/normalized/nea_station_weather_v11_longterm_wide.csv
data/archive/v11_longterm/normalized/openmeteo_forecast_snapshots_v11_longterm.csv
data/archive/v11_longterm/paired/v11_operational_station_weather_pairs.csv
data/calibration/v11/v11_station_weather_pairs_from_archive.csv
outputs/v11_archive_longterm/v11_archive_latest_QA_report.md
```

## 7. 手动 15 分钟循环

适合临时 overnight 运行：

```bat
scripts\v11_archive_loop_15min.bat
```

停止方法：Ctrl+C。

## 8. Windows Task Scheduler

更稳的长期方式是任务计划程序。先运行：

```bat
scripts\v11_archive_make_task_scheduler_commands.bat
```

它会打印类似：

```bat
schtasks /Create /TN "OpenHeat_v11_archive_15min" /SC MINUTE /MO 15 /TR "cmd /c cd /d <PROJECT_DIR> && <BAT_PATH>" /F
```

用管理员 CMD 执行打印出来的命令即可。

## 9. 输出解释

### 9.1 NEA long table

```text
data/archive/v11_longterm/long/nea_realtime_observations_v11_longterm.csv
```

长表格式，每行一个 station-variable-reading：

```text
timestamp
station_id
variable
value
station_lat/lon
heat_stress_category
archive_run_utc
endpoint_url
```

### 9.2 WBGT normalized table

```text
data/archive/v11_longterm/normalized/nea_wbgt_v11_longterm_normalized.csv
```

适合 v11 alpha QA：

```text
timestamp_sgt
station_id
official_wbgt_c
heat_stress_category
station_lat/lon
```

### 9.3 Open-Meteo snapshots

```text
data/archive/v11_longterm/normalized/openmeteo_forecast_snapshots_v11_longterm.csv
```

核心字段：

```text
forecast_issue_time_utc
valid_time_sgt
location_id
station_id if station-specific
temperature_2m
relative_humidity_2m
shortwave_radiation
direct_radiation
diffuse_radiation
cloud_cover
wind_speed_10m
wind_direction_10m
precipitation
```

默认每小时抓一次 Open-Meteo，避免 15 分钟循环中重复拉太多 forecast snapshots。

### 9.4 Operational station-weather pairs

```text
data/archive/v11_longterm/paired/v11_operational_station_weather_pairs.csv
```

这是后续 v1.1 beta/gamma 最关键的表。它把 official WBGT 和对应 valid-time Open-Meteo forecast 合在一起，并尽量保证：

```text
forecast_issue_time <= observation_time
```

也就是说，它更接近 operational forecast calibration，而不是事后拿未来数据配对。

### 9.5 Fallback proxy columns

如果 weather columns 可用，脚本会生成：

```text
wetbulb_stull_c
raw_proxy_wbgt_fallback_c
raw_proxy_wbgt_radiative_fallback_c
```

这些只是 smoke-test proxy，不是最终 OpenHeat WBGT production model。正式 v1.1 beta 最好接入你项目已有的 production proxy。

## 10. station_to_cell mapping

文件：

```text
configs/v11/station_to_cell.example.csv
```

如果要测试 v10 morphology / overhead features 对 official WBGT residual 是否有帮助，需要把 station 映射到 representative grid cell：

```csv
station_id,station_name,cell_id,station_lat,station_lon,notes
S128,NEA station S128,TP_0565,,,example
```

如果站点不在 Toa Payoh AOI，`cell_id` 可以留空。这种站仍可用于 weather-only calibration，但 morphology/overhead features 不会 join。

## 11. 什么时候可以开始 ML

建议：

```text
7 days: smoke test
14 days: baseline replay
30 days: residual learning pilot
60+ days: 更可信 LOSO + blocked-time CV
跨季节: operational robustness
```

不要因为行数多就直接上 ML。15-min records 强自相关，真正有效样本远小于 row count。

## 12. 不要提交到 Git 的文件

加入 `.gitignore`：

```gitignore
data/archive/
outputs/v11_archive_longterm/
*.tif
*.zip
outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv
```

长期 archive 留在本地或外部存储，不进 Git。

## 13. 常见问题

### Q: Open-Meteo 没有每 15 分钟数据怎么办？

Open-Meteo hourly forcing 会按 observation timestamp floor 到 hour 做配对。官方 WBGT 仍保留 15-min resolution。

### Q: 为什么 Open-Meteo 只每小时抓？

因为 forecast hourly valid-time 不需要每 15 分钟重复抓。脚本仍每 15 分钟抓 NEA，Open-Meteo 默认每 60 分钟抓一次。

### Q: WBGT endpoint 是什么？

配置默认使用：

```text
https://api-open.data.gov.sg/v2/real-time/api/weather?api=wbgt
```

这是你当前 archive 中已验证过的 endpoint。

### Q: 如果 Data.gov.sg schema 改了怎么办？

脚本会保存 raw JSON 到：

```text
data/archive/v11_longterm/raw_json/
```

可以用它 debug parser。
