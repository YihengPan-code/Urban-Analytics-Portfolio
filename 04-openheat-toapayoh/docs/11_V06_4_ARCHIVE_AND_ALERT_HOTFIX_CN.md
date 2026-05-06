# OpenHeat-ToaPayoh v0.6.4 Hotfix：Archive long format + UTCI/WBGT alert scoring

## 这版修复的两个核心问题

### 1. NEA archive 改为 long format

v0.6.3 的 `archive_nea_observations.py` 会把 air temperature、relative humidity、wind speed 和 WBGT 强行合并成一张宽表。由于不同 API 的 station coverage、timestamp、metadata 不完全一致，宽表 merge 可能导致 WBGT 行丢失：

- `timestamp`
- `station_name`
- `station_lat`
- `station_lon`
- `heat_stress_category`

v0.6.4 改为 long format：

```text
archive_run_utc
archive_source
archive_status
api_name
variable
value
unit
timestamp
record_updated_timestamp
station_id
device_id
station_name
station_town_center
station_lat
station_lon
heat_stress_category
reading_type
reading_unit
api_version
endpoint_url
fetch_timestamp_utc
value_missing
```

每一行现在代表：

> one station × one variable × one timestamp

这会让后续 calibration 更清楚：只需要筛选 `variable == official_wbgt_c`，再与模型的 `wbgt_proxy_c` 按 station/time 配对。

### 2. 分离 WBGT alert 和 UTCI alert

v0.6.3 的 `neighbourhood_alert` 主要按 WBGT proxy 判断。如果 WBGT proxy 低于 31°C，系统会显示 low；但同一时段 UTCI 可能已经达到 strong heat stress。这会造成解释混乱。

v0.6.4 新增：

```text
wbgt_alert
utci_alert
combined_alert
neighbourhood_alert
```

其中：

- `wbgt_alert` 对齐新加坡 WBGT low / moderate / high 语境；
- `utci_alert` 对齐 UTCI thermal comfort / heat stress 语境；
- `combined_alert` 是原型系统的综合提醒，不是官方公共健康预警；
- `neighbourhood_alert` 暂时保留为 backward-compatible alias，现在等于 `combined_alert`。

### 3. Hotspot hazard score 改为连续评分

v0.6.3 中，如果没有任何 cell 达到 WBGT ≥31°C，且所有 cell 都有较多 strong UTCI hours，`hazard_score` 可能变成常数，导致 hotspot ranking 主要由 vulnerability/exposure 拉开。

v0.6.4 的 hazard score 加入连续强度和相对排名：

```text
hazard_utci_intensity_score
hazard_utci_duration_score
hazard_utci_relative_score
hazard_wbgt_intensity_score
hazard_wbgt_duration_score
hazard_score
```

新的 `hazard_score` 同时考虑：

- peak UTCI absolute intensity；
- UTCI duration；
- relative UTCI ranking across cells；
- peak WBGT proxy intensity；
- WBGT threshold exceedance duration。

这样即使没有达到 WBGT moderate threshold，也能区分“相对更热”的 grid cell。

## 推荐运行命令

先跑离线测试：

```bat
python scripts\run_live_forecast_v06.py --mode sample
python scripts\archive_nea_observations.py --mode fixture --archive outputs\v06_4_fixture_archive_long.csv
pytest -q
```

再跑 live：

```bat
python scripts\run_live_forecast_v06.py --mode live
python scripts\run_nea_api_schema_check.py --mode live --api-version v2
python scripts\archive_nea_observations.py --mode live --api-version v2
```

v0.6.4 已把 `--api-version` 默认值改为 `v2`，所以也可以简写为：

```bat
python scripts\run_nea_api_schema_check.py --mode live
python scripts\archive_nea_observations.py --mode live
```

## 如何检查结果

### Archive 是否修好

```bat
python -c "import pandas as pd; df=pd.read_csv('data/archive/nea_realtime_observations.csv'); print(df[['api_name','variable','timestamp','station_id','station_name','station_lat','station_lon','value']].tail(20).to_string())"
```

你应该能看到 `official_wbgt_c` 行保留 station metadata。

### Alert 是否修好

```bat
python -c "import pandas as pd; df=pd.read_csv('outputs/v06_live_event_windows.csv'); print(df[['time','max_wbgt_proxy_c','max_utci_c','wbgt_alert','utci_alert','combined_alert']].head(20).to_string())"
```

### Hotspot scoring 是否修好

```bat
python -c "import pandas as pd; df=pd.read_csv('outputs/v06_live_hotspot_ranking.csv'); print(df[['rank','cell_id','max_utci_c','max_wbgt_proxy_c','hazard_score','risk_priority_score']].head(15).to_string())"
```

`hazard_score` 不应该再全部相同。

## 仍然没有解决的问题

v0.6.4 仍然是 workflow prototype。它还没有解决：

1. sample grid 不是 Toa Payoh 真实空间特征；
2. Tmrt 仍是 proxy，不是 SOLWEIG/UMEP 输出；
3. WBGT 仍是 screening proxy，不是官方 WBGT；
4. calibration 还需要连续归档多日 NEA WBGT；
5. nearest official WBGT station 只能作为 nearby proxy，不能代表 Toa Payoh 每个 street-level cell。

## 下一步 v0.7

v0.7 的重点不是继续修 API，而是构建真实 Toa Payoh grid features：

```text
building_density
mean/max_building_height
road_fraction
impervious_fraction
park_distance_m
water_distance_m
GVI / NDVI / tree canopy proxy
SVF proxy
shade_fraction
elderly_proxy
outdoor_exposure_proxy
```

这一步完成后，OpenHeat 才会从 synthetic workflow 变成真实 neighbourhood-scale spatial downscaling prototype。
