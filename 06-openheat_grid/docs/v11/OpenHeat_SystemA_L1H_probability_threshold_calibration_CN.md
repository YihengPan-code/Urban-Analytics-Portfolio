# OpenHeat System A L1H 概率 / 阈值校准说明

## 对应任务

本文档对应 `A-L1H.2 — probability / threshold calibration`。

本任务回答一个限定问题：

> 在不重训 M4/M7 基础 WBGT 模型、不实现 formula-v2、不实现 high-tail regression 的前提下，现有 M4/M7 OOF 分数能否被校准为有用的 `P(WBGT >= 31)` 诊断伴随量和阈值操作点？

## Claim Boundary

本任务只做 retrospective OOF score-to-event calibration。

允许表述：

- `P_ge31` 是现有 System A 分数的诊断伴随概率；
- 阈值操作点是站点留一 OOF 诊断结果；
- deterministic WBGT_A score 与 `P_ge31` 分开报告。

禁止表述：

- official warning probability；
- prospective forecast skill；
- validated local WBGT prediction；
- risk map / hazard map 已完成；
- radiation-hot regime 是因果机制证明。

## 为什么接在 A-L1H.1 后面

A-L1H.0 发现 high-tail compression 和 station bias。

A-L1H.0c 发现 full-period radiation-hot regime 中集中出现许多 observed ge31 events 和 misses，但这只是回顾性诊断，不是因果证明。

A-L1H.1 发现简单 formula/proxy 路线 `WEAK_OR_NEGATIVE`：

- raw formula/proxy candidates 没有 fixed_31 crossings；
- best raw formula max prediction 仍低于 31 C；
- M4/M7 OOF scores 比 raw formulas 更有用，但 nominal score >=31 与 event detection 不完全对齐。

所以 A-L1H.2 直接测试分数到事件概率和阈值的校准，而不是改写公式或重训回归模型。

## 输入

配置文件：

- `configs/v11/systema_l1h_probability_threshold_calibration.yaml`

主要输入：

- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv`
- `outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_threshold_metrics_31_33.csv`

主分析使用 `residual_weather_merge_full_period.csv` 中的 M4/M7 `loso` 行，因为这些行包含 `fold == station_id`，可用于 station-grouped held-out calibration。

## 校准器

对 `M4_inertia_ridge` 和 `M7_compact_weather_ridge` 分别运行：

- `fixed_score_31` baseline；
- raw score threshold scan: `best_F1`, `recall_90`, `precision_70`, `max_Youden`；
- score-bin empirical event rate；
- logistic score-only calibration；
- isotonic score-only calibration；
- optional diagnostic logistic score + `hour_sgt`；
- optional diagnostic logistic score + `radiation_hot_flag`。

可推广的候选优先从非 diagnostic calibrators 中选择；score+hour 和 score+radiation-hot 只作为诊断对照。

## 验证方法

若 LOSO fold 可用：

1. 每次留出一个 station/fold；
2. calibrator 只在其他 stations 的 OOF rows 上拟合；
3. 对 held-out station rows 预测概率；
4. 阈值操作点在 training stations 中选择，再应用到 held-out station。

如果 fold 结构不可用，结果必须降级为 apparent-only 或 BLOCKED，不能 promoted。

## 输出

输出目录：

- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/`

核心输出：

- `calibration_input_inventory.csv`
- `calibration_analysis_input.csv`
- `probability_predictions_oof.csv.gz`
- `score_bin_event_rates.csv`
- `reliability_bins_fixed.csv`
- `reliability_bins_quantile.csv`
- `probability_calibration_metrics.csv`
- `threshold_operating_points.csv`
- `threshold_by_station.csv`
- `threshold_by_regime.csv`
- `probability_threshold_calibration_report.md`
- `A_L1H_2_STATUS.md`

## 判读状态

`PASS_CANDIDATE_PROBABILITY_COMPANION`：

station-grouped validation 可用，`P_ge31` 改善 fixed score threshold 的解释，并且 reliability / threshold diagnostics 足够支持作为诊断伴随量。

`PARTIAL_DIAGNOSTIC`：

概率校准看起来有用，但 reliability、threshold improvement 或验证强度不足以 promoted。

`WEAK_OR_NEGATIVE`：

概率校准没有改善 reliability 或阈值诊断。

`BLOCKED`：

输入、fold、station metadata 或必要列缺失。

## 下一步边界

A-L1H.2 不执行：

- A-L1H.3 high-tail regression；
- A-L2 station-context preflight；
- formula-v2；
- System B / SOLWEIG 修改；
- archive collector 修改。

报告可以建议下一步，但任何下一步都必须作为独立 lane / issue 启动。
