# OpenHeat v1.1-beta Calibration Baseline 指南

## 目标

v1.1-beta 不是直接上复杂 ML，而是重建并升级 v0.9 的 calibration baseline。核心问题：

```text
raw physics proxy 是否有系统性偏差？
global bias correction 是否已经足够？
weather-regime / thermal inertia 是否改善？
v10 corrected morphology 是否有 residual value？
overhead features 是否有 residual value？
```

## 模型序列

```text
M0_raw_proxy
    原始 proxy，不训练，是必须 beat 的 baseline。

M1_global_bias
    raw_proxy + train residual mean。

M2_linear_proxy
    official_WBGT ~ raw_proxy。

M3_weather_ridge
    raw_proxy + temp/rh/wind/shortwave/cloud/hour。

M4_inertia_ridge
    M3 + lag/rolling shortwave/temp features。

M5_v10_morphology_ridge
    M4 + v10 reviewed morphology features。

M6_v10_overhead_ridge
    M5 + v10-delta overhead features。
```

## 运行前要求

先完成 v1.1-alpha：

```bat
scripts\v11_run_alpha_archive_pipeline.bat
```

确保存在：

```text
data/calibration/v11/v11_station_weather_pairs.csv
data/calibration/v11/v11_cv_splits.csv
```

## 一键运行

```bat
scripts\v11_run_beta_calibration_pipeline.bat
```

## 输出

```text
outputs/v11_beta_calibration/v11_beta_oof_predictions.csv
outputs/v11_beta_calibration/v11_beta_calibration_metrics.csv
outputs/v11_beta_calibration/v11_beta_model_feature_sets.csv
outputs/v11_beta_calibration/v11_beta_calibration_baseline_report.md
outputs/v11_beta_calibration/v11_beta_threshold_scan_all.csv
outputs/v11_beta_calibration/v11_beta_threshold_scan_best_f1.csv
outputs/v11_beta_calibration/v11_beta_threshold_scan_recall_priority.csv
outputs/v11_beta_calibration/v11_beta_threshold_scan_report.md
```

## 如何解读

### 1. 先看 MAE / RMSE / bias

打开：

```text
outputs/v11_beta_calibration/v11_beta_calibration_baseline_report.md
```

理想模式：

```text
M0 raw proxy 有明显 bias
M1/M2 修正大部分 global bias
M3/M4 改善 weather-regime / afternoon residual
M5/M6 如果改善，说明 v10 morphology/overhead 对 station residual 有价值
```

如果 M5/M6 没提升，也不是失败。它可能说明 official station WBGT 不足以验证 100m morphology，或 station environment 不代表所有 cell。

### 2. 再看 threshold scan

打开：

```text
outputs/v11_beta_calibration/v11_beta_threshold_scan_report.md
```

重点看：

```text
WBGT≥31 best-F1 threshold
WBGT≥31 recall-priority threshold
WBGT≥33 event count 是否足够
```

WBGT≥33 如果 event 很少，只能 exploratory，不能写成 production threshold。

## 严禁 random split

脚本默认只用：

```text
LOSO: leave-one-station-out
blocked-time CV
```

不要 random split。15-min/hourly weather archive 强自相关，random split 会严重泄漏同一天/同站日变化。
