# OpenHeat v11 archive collector hotfix

这是 v11 long-term archive collector 的最终 hotfix 包。

## 修复内容

1. 新增旧 archive 迁移脚本：
   - `scripts/v11_archive_migrate_legacy.py`
   - `scripts/v11_archive_migrate_legacy.bat`

2. 修复 Open-Meteo `past_days=1` hindcast 被过滤的问题：
   - 默认 `allow_posthoc_weather_if_no_operational_match = true`
   - paired table 新增：
     - `operational_match`
     - `posthoc_weather_match`
     - `pair_used_for_calibration`
     - `weather_match_mode`

3. 修复 raw JSON retention 未实现的问题：
   - collector 每次运行末尾自动清理旧 raw JSON 日期目录
   - 新增手动清理脚本：
     - `scripts/v11_archive_cleanup_raw_json.py`
     - `scripts/v11_archive_cleanup_raw_json.bat`

4. 修复 paired dataset 双入口问题：
   - collector 默认直接写：
     - `data/calibration/v11/v11_station_weather_pairs.csv`
   - 新增 alpha QA pipeline：
     - `scripts/v11_run_alpha_archive_from_collector_pipeline.bat`
   - 该 pipeline 跳过 `v11_alpha_build_pairs.py`

## 推荐顺序

```bat
scripts\v11_archive_migrate_legacy.bat
scripts\v11_archive_collect_once.bat
scripts\v11_run_alpha_archive_from_collector_pipeline.bat
```

然后检查：

```text
outputs/v11_archive_longterm/v11_archive_legacy_migration_report.md
outputs/v11_archive_longterm/v11_archive_latest_QA_report.md
outputs/v11_alpha_archive/v11_archive_QA_report.md
```

## 注意

此包不包含 archive 数据本身。`data/archive/` 不应该进入 Git。
