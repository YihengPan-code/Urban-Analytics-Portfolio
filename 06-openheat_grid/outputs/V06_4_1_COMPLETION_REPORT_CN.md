# OpenHeat-ToaPayoh v0.6.4.1 完成报告

## 完成内容

v0.6.4.1 是基于 source-code review 的二次 hotfix。它在 v0.6.4 已有的 archive long format 和 UTCI/WBGT alert scoring 基础上，进一步修复了：

- WBGT v1 endpoint 误用风险；
- hazard_score 在 sub-WBGT-31 regime 的区分度问题；
- calibration nearest-station matching 应只使用 WBGT station network；
- screening-level microclimate proxy 中的 GVI cap、park cooling decay、wind cap、Tmrt low-SVF longwave 项；
- `make_paired_wbgt_table()` 对 v0.6.4 long archive 的适配。

## 测试结果

```text
18 passed, 1 warning
```

## 已生成的示例输出

- `outputs/v06_offline_hotspot_ranking.csv`
- `outputs/v06_offline_event_windows.csv`
- `outputs/v06_4_1_fixture_archive_long.csv`
- `outputs/v06_4_hotspot_preview.png`

## 运行建议

先跑离线：

```bat
python scripts\run_live_forecast_v06.py --mode sample
python scripts\archive_nea_observations.py --mode fixture --archive outputs\v06_4_1_fixture_archive_long.csv
pytest -q
```

再跑 live：

```bat
python scripts\run_live_forecast_v06.py --mode live
python scripts\run_nea_api_schema_check.py --mode live
python scripts\archive_nea_observations.py --mode live
python scripts\plot_v06_hotspots.py
```

## 判断

v0.6.4.1 可以作为 v0.7 之前的稳定版本。下一步不建议继续大修 API 层，而应进入真实 Toa Payoh grid feature engineering。
