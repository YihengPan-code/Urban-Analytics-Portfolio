# OpenHeat v1.1 / v11 archive collector hotfix guide

这份 hotfix 针对 v11 long-term archive collector 的 4 个关键问题：

1. 旧 v0.9 / v10 archive 不会自动进入 v11 archive。
2. `past_days=1` 的 Open-Meteo hindcast 被 operational-only filter 丢掉。
3. raw JSON 长期保留但没有清理逻辑。
4. collector 自己生成 paired dataset，而 v11-alpha 也会生成另一份，容易让下游拿错。

## Hotfix 后的默认策略

- 旧 archive 通过 `v11_archive_migrate_legacy.py` 一次性迁移到 v11 archive root。
- pairing 同时保留：
  - `operational_match`
  - `posthoc_weather_match`
  - `pair_used_for_calibration`
  - `weather_match_mode`
- v11 collector 的权威 paired dataset 输出为：

```text
data/calibration/v11/v11_station_weather_pairs.csv
```

- v11-alpha 应跳过 legacy `v11_alpha_build_pairs.py`，使用：

```bat
scripts\v11_run_alpha_archive_from_collector_pipeline.bat
```

- raw JSON 默认保留 14 天，collector 每次运行末尾会自动清理旧日期目录。

## 推荐运行顺序

### 1. 安装 / 覆盖 hotfix 文件

将 hotfix 包解压到项目根目录，允许覆盖同名文件。

### 2. 迁移旧 archive

```bat
scripts\v11_archive_migrate_legacy.bat
```

检查：

```text
outputs/v11_archive_longterm/v11_archive_legacy_migration_report.md
```

确认旧 v09/v10 WBGT rows 和 event counts 已进入 v11 long archive。

### 3. 跑一次 collector

```bat
scripts\v11_archive_collect_once.bat
```

检查：

```text
outputs/v11_archive_longterm/v11_archive_latest_QA_report.md
```

重点看：

```text
pair_used_for_calibration
operational_match
posthoc_weather_match
weather_match_mode
pair_location_source
```

### 4. 跑 v11-alpha collector-based QA

确保 v11-alpha/beta 包已安装，然后运行：

```bat
scripts\v11_run_alpha_archive_from_collector_pipeline.bat
```

这一步会跳过 legacy pairing，只使用 collector 生成的：

```text
data/calibration/v11/v11_station_weather_pairs.csv
```

### 5. 挂长期任务

确认上述流程正常后，再用 Task Scheduler 或 loop bat 长期运行 collector。

## 不要做什么

不要同时让 collector 和 `v11_alpha_build_pairs.py` 各自生成 paired dataset 后混用。v11 collector 的 station-local Open-Meteo pairing 是权威版本，alpha/beta 应使用它。

不要把 `data/archive/` 提交进 Git。长期 archive 会增长，应该保留本地或外部备份。
