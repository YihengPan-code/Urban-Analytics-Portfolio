# OpenHeat System A A-L1H.3 高尾挑战者基准说明

本文档说明 A-L1H.3 的用途、输入、验证方式与结论边界。A-L1H.3 是一个受限的高尾挑战者基准，不替代当前 Level 1 输出合同。

## 目的

A-L1H.2b 已接受 `M4_inertia_ridge + isotonic_score_only` 作为回顾性 `P_ge31` 诊断伴随量。它改善了 `official_wbgt_c >= 31` 的捕获，但高尾压缩、站点差异、辐射高温时段和低支持度分箱仍是 caveat。

A-L1H.3 只回答一个问题：在站点留一验证下，小型受限挑战者是否能比当前 M4+isotonic 伴随量减少 ge31 漏报，同时不造成不可接受的误报或站点/天气分型过拟合。

## 使用边界

- `P_ge31` 仍是回顾性诊断伴随量。
- 本基准不声明官方预警概率。
- 本基准不声明前瞻 forecast skill。
- 本基准不声明本地 100m WBGT。
- `ge33` 仅作为探索性诊断，不用于提升候选模型。
- A-L2 不在本 lane 中启动；如需站点上下文残差工作，应另开 A-L2.0 preflight。

## 输入

主要输入为：

- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/probability_predictions_oof.csv.gz`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/threshold_operating_points.csv`
- `outputs/v11_systema_l1_high_tail/level1_integration/systema_l1h_output_contract.csv`

## 验证设计

主验证为 `station_grouped_loso`。每个外层 fold 持出一个站点，挑战者只在其他站点上训练，并预测持出站点。

挑战者的超参数使用训练站点内部的 station-grouped CV 选择。外层持出站点不参与超参数选择或阈值选择。

## 特征合同

允许特征限于当前 M4 分数、小时循环项、天气变量和辐射/短波分型标记。禁止使用：

- `station_id` 作为特征；
- fold；
- `official_wbgt_c` 作为预测特征；
- `obs_ge31`、`obs_ge33` 或事件标签；
- `residual_c` 或目标派生列；
- System B、SOLWEIG、Tmrt；
- 本地 100m cell morphology。

`high_tail_residual_correction` 可在训练站点内把 `official_wbgt_c - model_score` 作为监督目标来拟合残差校正，但该残差不作为预测特征，也不在持出站点中使用标签信息。

## 输出

输出写入：

`outputs/v11_systema_l1_high_tail/high_tail_challenger/`

关键文件包括：

- `challenger_input_inventory.csv`
- `challenger_feature_schema.csv`
- `challenger_oof_predictions.csv.gz`
- `challenger_overall_metrics.csv`
- `challenger_threshold_metrics.csv`
- `challenger_reliability_metrics.csv`
- `challenger_by_station.csv`
- `challenger_by_regime.csv`
- `challenger_pairwise_vs_current_companion.csv`
- `high_tail_challenger_report.md`
- `A_L1H_3_STATUS.md`

## 运行命令

```powershell
python scripts/v11_l1h3_run_high_tail_challenger.py --config configs/v11/systema_l1h3_high_tail_challenger.yaml
```

在 Codex bundled runtime 中，如果系统 `python` 不在 PATH，可使用 bundled `python.exe` 执行同一脚本。

## 结论解释

挑战者只有在以下条件同时满足时才可标记为 `PROMISING_CHALLENGER`：

- 相比当前 M4+isotonic best-F1 伴随量，recall 提高或 miss_rate 降低；
- precision 不低于 0.60，除非明确标记为 recall-first 诊断；
- CSI 提高或持平；
- Brier 和 reliability 不劣化到不可接受；
- 通过 station-grouped LOSO；
- 不依赖 station_id 或泄漏特征。

否则结论应为 `RECALL_FIRST_DIAGNOSTIC`、`WEAK_OR_NEGATIVE` 或 `BLOCKED`。
