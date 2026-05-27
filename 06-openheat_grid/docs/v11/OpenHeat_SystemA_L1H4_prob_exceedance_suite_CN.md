# OpenHeat System A A-L1H.4 概率 / 超阈值伴随套件说明

生成日期：2026-05-27
决策状态：`A_L1H4_COMPANION_PROMISING`

## 1. 为什么接在 A-L2.1c 之后

A-L2.1c 显示，站点环境特征对高尾残差只有弱解释力，对分数残差暂不可识别。因此本轮不建立站点修正 WBGT，也不生成本地 100 m WBGT，而是回到 Level 1 的阈值行为、概率伴随、超阈值期望和区间不确定性。

## 2. 为什么 Level 1 仍是主改进路径

当前证据更支持在确定性 WBGT_A 之外增加伴随诊断列，而不是替换 WBGT_A。概率和区间只用于内部回顾性评估，不能表述为官方预警概率或实时健康风险。

## 3. 输入清单与目标定义

主验证表包含 1674 行、27 个站点、ge31 事件 204 个、ge33 事件 15 个。目标包括 `official_wbgt_c`、`ge31`、`ge33`、`exceedance_ge31_c` 和 `exceedance_ge33_c`。

## 4. 验证切分设计

主验证采用留一站点（LOSO）。若源数据存在 time_block 折，则作为次级阻塞时间验证。不使用随机切分作为主要证据。标准化 logistic 回归使用固定并公开的超参数（C=1.0、无 class weighting），并采用仓库内稳定求解器，因为本运行环境中的 sklearn estimator fit 会硬退出。

## 5. 确定性基线

确定性基线仍为 M4_inertia_ridge 的 WBGT_A 分数，并与 M7_compact_weather_ridge 和 v09 代理分数比较。固定 31 °C 阈值只作为基线，不被替换为本轮输出。

## 6. 阈值策略

阈值策略包括 fixed_31、best_F1、recall90 和 precision70。训练折只用于选择阈值， held-out 折用于评估。

## 7. P_ge31 / P_ge33 模型

isotonic_m4_score_ge31 Brier=0.052, ECE_fixed=0.018, PR-AUC=0.610, best_F1 threshold=0.446.

P_ge33 因事件支持不足时只保留探索性标记，不提升为正式伴随列。

## 8. 期望超阈值

deterministic_score_gap_m4_ge31 MAE=0.100 C, positive-event MAE=0.779 C; delta MAE vs deterministic score gap=0.000 C.

## 9. 分位数 / 区间伴随

conformal_m4_residual nominal 90% coverage=0.898, mean width=2.869 C.

## 10. 站点诊断与 S142 限制

S142: n_ge31=15, recall=0.533, miss_rate=0.467, false_alarm_ratio=0.000; S139: n_ge31=1, recall=1.000, miss_rate=0.000, false_alarm_ratio=0.889. Station diagnostics remain caveats, not station corrections.

## 11. 决策矩阵

| criterion                     | status      | detail                                                                                                                                               |
| ----------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| primary_threshold_recall_miss | PASS        | isotonic_m4_score_ge31 best_F1 vs WBGT_A fixed_31: recall 0.588->0.765 (delta 0.176), precision 0.682->0.678 (delta -0.004), miss_rate 0.412->0.235. |
| false_alarm_precision_control | PASS        | precision=0.678; false_alarm_ratio=0.322.                                                                                                            |
| probability_calibration       | PASS        | isotonic_m4_score_ge31 Brier=0.052, ECE_fixed=0.018, PR-AUC=0.610, best_F1 threshold=0.446.                                                          |
| no_s142_sensitivity           | PASS        | no-S142 recall delta vs fixed_31=0.180.                                                                                                              |
| blocked_time_secondary        | PASS        | blocked-time recall delta vs fixed_31=0.358.                                                                                                         |
| ge33_support                  | LOW_SUPPORT | P_ge33 remains exploratory and is not promoted.                                                                                                      |
| expected_exceedance_available | PASS        | Expected exceedance metrics are available for score-gap/direct/two-part companions.                                                                  |
| interval_available            | PASS        | Interval metrics are available for conformal and quantile companions where runtime support exists.                                                   |
| claim_boundary                | PASS        | Companion only; no station-adjusted WBGT, no local 100m WBGT, no System B coupling output, no risk/hazard score.                                     |

## 12. 输出契约草案

建议未来 System A 小时输出保留 `wbgt_a_c`，并仅可选增加 `p_ge31_optional`、`p_ge33_optional`、`expected_exceedance_ge31_optional`、`prediction_interval_low_optional` 和 `prediction_interval_high_optional`。

## 13. 声明边界

- 不创建站点修正 WBGT。
- 不创建本地 100 m WBGT。
- 不输出 System B 耦合结果。
- 不创建 risk_score 或 hazard_score。
- 本套件只是伴随诊断，除非后续模型卡明确提升，否则不是 canonical 替代。
