# v0.6 观测归档：为真正 WBGT 校准做准备

v0.6 已经包含一个最小归档脚本：

```bash
python scripts/archive_nea_observations.py --mode live
```

输出：

```text
data/archive/nea_realtime_observations.csv
```

建议在热季连续运行至少 2–4 周。最简单的 cron：

```bash
*/15 * * * * cd /path/to/openheat_toapayoh_v0_6_live_calibration && /path/to/python scripts/archive_nea_observations.py --mode live
```

为什么要归档？因为校准不是拿“当前时刻一行数据”就能做。你需要多时段、多天气状态、最好包含 moderate/high WBGT 的观测样本。最低可用标准：

```text
≥ 30 paired observations
≥ 2 days
至少包含 WBGT ≥ 31°C 的时段
最好包含 WBGT ≥ 33°C 的时段
```

下一步你还需要同时归档 forecast issue：

```text
forecast_issue_time
valid_time
station_id / grid_id
wbgt_proxy_c
lead_time_h
```

有了 observation archive + forecast archive，才可以建立真正的 hindcast calibration table。
