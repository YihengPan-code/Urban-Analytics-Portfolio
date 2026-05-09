# OpenHeat v0.9-beta threshold scan extension 与结论报告

## 目的

v0.9-beta 已经证明 M3/M4 ridge calibration 显著改善平均误差，但如果直接用 `prediction >= 31°C` 判断 official `WBGT >= 31°C`，仍会漏报不少事件。threshold scan 的目的不是修改官方阈值，而是寻找当前模型输出尺度上的 **decision threshold**。

例如：

```text
official event = official_WBGT >= 31°C
model event    = M4_pred >= 29.3°C
```

这里的 29.3°C 是模型判别阈值，不是官方 WBGT 阈值。

## 运行

```bat
python scripts\v09_beta_threshold_scan.py --config configs\v09_beta_threshold_config.example.json
python scripts\v09_beta_make_conclusion_report.py
```

## 输出

```text
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_metrics.csv
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_summary.csv
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_report.md
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_focus_station_timeline.csv
outputs/v09_beta_calibration/v09_beta_conclusion_report.md
```

## 报告时要写清楚

- decision threshold 是 post-hoc model-score threshold，不替代官方 WBGT threshold。
- WBGT>=33 事件太少，结果只作为诊断。
- threshold scan 只能基于当前 24h pilot archive，不应声称泛化。
