# OpenHeat-ToaPayoh v0.6.4.1 — source-review patched forecast + NEA/WBGT calibration prototype

这是 v0.6.4 的二次 source-review hotfix。它保留 v0.6.4 的两项核心修复：

1. NEA observation archive 改成 long format；
2. UTCI/WBGT alert 分离，并修复 hotspot hazard score 饱和问题。

v0.6.4.1 进一步修复 `src可能的问题.pdf` 指出的几个问题：WBGT v1 endpoint 风险、WBGT-only station matching、wind cap、GVI cap、park-cooling decay、Tmrt low-SVF wall longwave 项，以及 calibration pairing 对 long archive 的适配。

## 系统逻辑

```text
Open-Meteo background forecast
    ↓
Toa Payoh sample grid-feature downscaling / local modification
    ↓
screening-level UTCI / WBGT proxy hotspot ranking
    ↓
NEA official WBGT station observations
    ↓
future: multi-day bias correction / hindcast calibration
```

重要定位：Open-Meteo 在 Toa Payoh 尺度提供的是背景气象，不是街区内 50–100 m 的空间差异。v0.7 的 building density、SVF、GVI、shade、road fraction 等真实 grid features 才是 intra-neighbourhood spatial downscaling 的核心。

## 快速运行：离线测试

```bat
cd /d "你的项目路径\openheat_toapayoh_v0_6_4_1_review_patch"
pip install -r requirements.txt
python scripts\run_live_forecast_v06.py --mode sample
python scripts\archive_nea_observations.py --mode fixture --archive outputs\v06_4_1_fixture_archive_long.csv
pytest -q
```

预期：

```text
18 passed, 1 warning
```

## 运行 live forecast

```bat
python scripts\run_live_forecast_v06.py --mode live
```

输出：

```text
outputs\v06_live_openmeteo_forecast_raw.csv
outputs\v06_live_hourly_grid_heatstress_forecast.csv
outputs\v06_live_hotspot_ranking.csv
outputs\v06_live_event_windows.csv
```

## 检查 NEA / data.gov.sg WBGT schema

v0.6.4.1 默认使用 v2。WBGT 会强制走 v2 weather endpoint，即使你在 legacy 测试里传了 `--api-version v1`。

```bat
python scripts\run_nea_api_schema_check.py --mode live
```

输出：

```text
outputs\v06_1_nea_station_observations_schema_check.csv
outputs\v06_1_grid_nearest_wbgt_station.csv
```

## 归档 NEA observations

```bat
python scripts\archive_nea_observations.py --mode live
```

归档到：

```text
data\archive\nea_realtime_observations.csv
```

v0.6.4+ archive 是 long format，每行是：

```text
one station × one variable × one timestamp
```

关键字段：

```text
archive_run_utc
api_name
variable
value
unit
timestamp
station_id
station_name
station_lat
station_lon
heat_stress_category
api_version
endpoint_url
fetch_timestamp_utc
value_missing
```

## 查看结果

Hotspot ranking：

```bat
python -c "import pandas as pd; df=pd.read_csv('outputs/v06_live_hotspot_ranking.csv'); print(df[['rank','cell_id','max_utci_c','max_wbgt_proxy_c','hazard_score','risk_priority_score']].head(15).to_string())"
```

Event windows：

```bat
python -c "import pandas as pd; df=pd.read_csv('outputs/v06_live_event_windows.csv'); print(df[['time','max_wbgt_proxy_c','max_utci_c','wbgt_alert','utci_alert','combined_alert']].head(20).to_string())"
```

Archive：

```bat
python -c "import pandas as pd; df=pd.read_csv('data/archive/nea_realtime_observations.csv'); print(df[['api_name','variable','timestamp','station_id','station_name','station_lat','station_lon','value','heat_stress_category']].tail(30).to_string())"
```

## 当前边界

v0.6.4.1 仍然是 workflow/calibration-ready prototype，不是正式街道级公共健康预警系统：

1. Toa Payoh grid 仍是 sample/synthetic features；
2. `tmrt_proxy_c` 是 screening proxy，不是 SOLWEIG/UMEP；
3. `wbgt_proxy_c` 是 screening proxy，不是 official WBGT；
4. calibration 需要多日 NEA WBGT archive；
5. nearest official WBGT station 只能作为 nearby calibration proxy。

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

详见：

```text
docs/12_V06_4_1_SRC_REVIEW_PATCH_CN.md
outputs/V06_4_1_COMPLETION_REPORT_CN.md
```
