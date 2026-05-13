# OpenHeat v1.1 long-term archive collector

这是为 OpenHeat v1.1 calibration / ML 准备的长期 archive 采集包。

## 快速开始

```bat
pip install pandas numpy requests tabulate
scripts\v11_archive_preflight.bat
scripts\v11_archive_collect_once.bat
```

## 长期运行

临时循环：

```bat
scripts\v11_archive_loop_15min.bat
```

更推荐 Windows Task Scheduler：

```bat
scripts\v11_archive_make_task_scheduler_commands.bat
```

复制打印出来的 `schtasks` 命令，用管理员 CMD 执行。

## 核心输出

```text
data/archive/v11_longterm/normalized/nea_wbgt_v11_longterm_normalized.csv
data/archive/v11_longterm/normalized/nea_station_weather_v11_longterm_wide.csv
data/archive/v11_longterm/normalized/openmeteo_forecast_snapshots_v11_longterm.csv
data/archive/v11_longterm/paired/v11_operational_station_weather_pairs.csv
data/calibration/v11/v11_station_weather_pairs_from_archive.csv
outputs/v11_archive_longterm/v11_archive_latest_QA_report.md
```

这些文件是 v1.1-alpha / beta / gamma 的地基。

## Git 注意

不要把 `data/archive/` 提交到 Git。它会越来越大。
