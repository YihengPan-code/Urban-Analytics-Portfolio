# OpenHeat System A L1 高尾残差分解协议

## 目的

本协议对应 Lane A-L1H.0，只分析既有 System A OOF 预测 / model score：

`residual_c = official_wbgt_c - model_score`

正残差表示模型相对官方 WBGT 目标低估。本轮只判断 ge31 高尾问题更接近全局 Level 1 分数压缩、站点残差偏差、天气情景交互，还是混合结构。

## 输入优先级

首选已跟踪的 hourly_max OOF：

`outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv`

备选仅用于可兼容比较：

- `outputs/v11_beta_calibration/hourly_mean/v11_beta_oof_predictions.csv`
- `outputs/v11_beta_calibration/all_stations/v11_beta_oof_predictions.csv`
- `outputs/v11_beta_calibration/no_S142/v11_beta_oof_predictions.csv`

本 lane 不要求 `outputs/v11_beta_formal/` 存在；若 hourly_max OOF 可用，不因 formal OOF 缺失而 BLOCKED。

## 模型与阈值

主模型为 `M4_inertia_ridge`，若同一 OOF 中存在，则同时输出 `M7_compact_weather_ridge` 作为 comparator。所有输入均来自既有 OOF score，不训练新模型。

固定阈值：

- ge31: `official_wbgt_c >= 31` 与 `model_score >= 31`
- ge33: `official_wbgt_c >= 33` 与 `model_score >= 33`，仅探索性

事件类别：

- hit: observed ge31 且 predicted ge31
- miss: observed ge31 且未 predicted ge31
- false_alarm: 未 observed ge31 且 predicted ge31
- true_negative: 其余

## 输出

所有 lane 输出写入：

`outputs/v11_systema_l1_high_tail/`

核心输出包括输入 inventory、标准化分析输入、按 observed bin / predicted bin / station / hour / regime 的残差汇总、ge31 miss / false alarm / hit inventory、ge33 exploratory inventory，以及 `high_tail_bias_report.md`。

## Claim 边界

本协议只产生 retrospective OOF diagnostic。不得据此声称：

- 已验证 local 100m WBGT prediction
- `P_ge31` 是 official warning probability
- 已建立 operational prospective forecast skill
- ge33 已成为稳定建模结论

后续行动必须经过报告复核后再进入 A-L1H.1 / A-L1H.2 / A-L1H.3 或 A-L2。
