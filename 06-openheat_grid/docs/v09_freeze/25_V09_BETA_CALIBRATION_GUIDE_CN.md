# OpenHeat v0.9-beta：WBGT proxy 校准指南

## 目标

v0.9-beta 的目标不是复杂 ML，而是建立一套严肃的 **physics WBGT proxy calibration baseline**：

1. 评估 raw physics proxy；
2. 测试 global bias correction；
3. 测试 period-specific bias correction；
4. 测试 linear proxy calibration，并诊断 slope 是否危险；
5. 测试 current-weather regime calibration；
6. 测试 lagged/cumulative shortwave 的 thermal-inertia calibration；
7. 用 Leave-One-Station-Out CV 作为主验证，不使用 random split 作为主证据。

## 为什么加入 thermal inertia features？

v0.9-alpha 显示 raw proxy 完全漏报 `WBGT >= 31°C` 和 `WBGT >= 33°C`。一部分原因可能是下午官方 WBGT 的偏差滞后于瞬时短波辐射：建筑、地面、黑球温度和局地热储存会让 15:00–16:00 的 residual 继续升高，即使短波辐射已经下降。因此 v0.9-beta 加入：

- `shortwave_3h_mean`
- `shortwave_lag_1h`
- `shortwave_lag_2h`
- `cumulative_day_shortwave_whm2`
- `dTair_dt_1h`

## 模型列表

- `M0_raw_proxy`: 原始 physics WBGT proxy。
- `M1_global_bias`: 全局平均残差校正。
- `M1b_period_bias`: day/night/shoulder 分时段 bias 校正。
- `M2_linear_proxy`: `official ~ proxy` 线性校准；主要用于诊断 slope。
- `M3_regime_current_ridge`: 当前天气状态 Ridge 校准。
- `M4_inertia_ridge`: 加入 lagged/cumulative shortwave 的热惯性 Ridge 校准。
- `M5_inertia_morphology_ridge`: M4 + station-nearest morphology。注意：Toa Payoh morphology 对远处 station 代表性弱，因此它主要是诊断模型。

## 运行方式

```bat
python scripts\v09_beta_fit_calibration_models.py --config configs\v09_beta_config.example.json
```

或者一键运行：

```bat
scripts\v09_beta_run_pipeline.bat
```

## 输出

```text
outputs/v09_beta_calibration/
├── v09_beta_engineered_pairs.csv
├── v09_beta_predictions_long.csv
├── v09_beta_model_metadata.csv
├── v09_beta_model_metrics.csv
├── v09_beta_event_detection_metrics.csv
├── v09_beta_metrics_by_station.csv
├── v09_beta_residual_by_hour.csv
├── v09_beta_linear_slope_diagnostics.csv
├── v09_beta_focus_station_timeline.csv
└── v09_beta_calibration_report.md
```

## 重点怎么看

打开：

```bat
type outputs\v09_beta_calibration\v09_beta_calibration_report.md
```

优先看：

1. LOSO-CV overall MAE 是否优于 raw proxy；
2. daytime / peak MAE 是否改善；
3. nighttime MAE 是否被 global bias correction 恶化；
4. `WBGT>=31` recall 是否从 raw proxy 的 0 提高；
5. `M2_linear_proxy` slope 是否过大；
6. `M4_inertia_ridge` 是否优于 `M3_regime_current_ridge`。

## 成功标准（pilot）

当前 24h archive 只适合 pilot，不适合最终 ML。v0.9-beta 的理想结果：

- LOSO-CV `WBGT>=31` recall > 0，并明显高于 raw proxy；
- daytime / peak-window MAE 低于 raw proxy；
- nighttime MAE 不应显著恶化；
- `WBGT>=33` event 数量太少，只报告不设硬阈值；
- 如果 M4/M5 明显优于 M3，说明 thermal inertia features 有价值。

## 解释边界

- 不要用 random split 声称泛化能力；
- M2 大 slope 只说明 raw proxy 动态范围压缩，不一定适合作为 operational model；
- M5 morphology features 对远处 station 代表性弱，因此不要把它解释为全岛形态校准；
- v0.9-beta 仍是 non-ML calibration baseline，后续 ML 应学习 residual，而不是替代 physics proxy。
