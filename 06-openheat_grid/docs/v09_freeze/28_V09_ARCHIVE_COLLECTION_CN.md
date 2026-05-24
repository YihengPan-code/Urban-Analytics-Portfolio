# OpenHeat v0.9 archive 持续采集脚本

## 脚本

```text
scripts/run_v09_archive_loop.bat
```

## 功能

- 每 15 分钟采集一次 NEA realtime archive。
- 维持 long-format archive，若检测到旧 wide-format 自动停止。
- 可选每 1 小时保存一次 Open-Meteo forecast snapshot。

## 运行前检查

确认路径：

```bat
notepad scripts\run_v09_archive_loop.bat
```

检查：

```text
PROJECT_DIR
CONDA_ENV
ARCHIVE_FILE
GRID_FILE
```

## 运行

```bat
scripts\run_v09_archive_loop.bat
```

或后台最小化：

```bat
start /min scripts\run_v09_archive_loop.bat
```

## 格式要求

archive 必须有：

```text
api_name
variable
value
timestamp
station_id
station_name
station_lat
station_lon
```

如果脚本发现没有 `variable` 或 `value` 列，会停止，避免把旧 wide archive 继续混进去。
