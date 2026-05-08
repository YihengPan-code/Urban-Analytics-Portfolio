# OpenHeat-ToaPayoh v0.6.4 Hotfix 完成报告

## 完成内容

v0.6.4 修复了 v0.6.3 中两个影响后续 calibration 和解释性的核心问题：

1. `archive_nea_observations.py` 改为 long-format archive，避免 WBGT metadata 在宽表 merge 中丢失。
2. `hotspot_engine.py` 新增 UTCI/WBGT 分离 alert 和 continuous hazard scoring，避免非 WBGT-advisory 天气下 hotspot hazard score 饱和。

## 核心代码改动

### `src/openheat_forecast/live_pipeline.py`

新增：

- `_standard_archive_columns()`
- `station_observations_to_long()`
- `fetch_latest_nea_observation_long_bundle()`

### `scripts/archive_nea_observations.py`

现在默认输出 long format：

```text
one station × one variable × one timestamp
```

同时新增 legacy wide archive 检测：如果发现旧版宽表 archive，会自动备份并开始新的 long-format archive，避免旧脏数据混入 calibration dataset。

### `src/openheat_forecast/hotspot_engine.py`

新增输出列：

```text
hazard_utci_intensity_score
hazard_utci_duration_score
hazard_utci_relative_score
hazard_wbgt_intensity_score
hazard_wbgt_duration_score
wbgt_alert
utci_alert
combined_alert
```

## 测试结果

```text
14 passed, 1 warning
```

warning 来自 pandas 对 `'H'` frequency alias 的未来弃用提醒，不影响运行。

## 已生成检查输出

```text
outputs/v06_offline_hotspot_ranking.csv
outputs/v06_offline_event_windows.csv
outputs/v06_4_fixture_archive_long.csv
outputs/v06_4_hotspot_preview.png
```

## 用户下一步运行命令

```bat
python scripts\run_live_forecast_v06.py --mode live
python scripts\run_nea_api_schema_check.py --mode live --api-version v2
python scripts\archive_nea_observations.py --mode live --api-version v2
python scripts\plot_v06_hotspots.py
```

## 解释边界

v0.6.4 仍然不是 operational public-health warning system。它是一个 forecast-to-hotspot workflow prototype：

```text
Open-Meteo background weather
→ sample / future real grid features
→ screening UTCI/WBGT proxy
→ hotspot/event ranking
→ NEA official WBGT archive for future calibration
```

真实科学升级需要 v0.7 的 Toa Payoh spatial features 和 v0.8 的 WBGT calibration。
