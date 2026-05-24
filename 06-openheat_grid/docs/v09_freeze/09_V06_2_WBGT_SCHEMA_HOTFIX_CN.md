# v0.6.2 WBGT schema hotfix

本 hotfix 处理两个问题：

1. `v1/environment/wbgt` 可能返回 403，因此 live WBGT 建议使用 `--api-version v2`。
2. `v2` WBGT payload 在某些时刻/接口形态下可能不含 `station_lat/station_lon`，旧版脚本会在 nearest-station 步骤崩溃。现在脚本会保留 official WBGT observations，并写出一个 diagnostic nearest-station table，而不是中断。

推荐命令：

```bat
python scripts\run_nea_api_schema_check.py --mode live --api-version v2
python scripts\archive_nea_observations.py --mode live --api-version v2
python scripts\debug_fetch_wbgt_raw.py --api-version v2
```

如果 `outputs/debug_wbgt_raw.json` 里能看到站点坐标但 parser 未识别，可根据实际 schema 继续增强 `live_api.py`。
