# OpenHeat System A A-L1H.5 模型卡与小时输出契约

生成日期：2026-05-27
决策状态：`A_L1H5_CONTRACT_PASS`

## 1. 为什么 A-L1H.5 接在 A-L1H.4 和 A-L2.1c 之后

A-L1H.4 的结论是 `A_L1H4_COMPANION_PROMISING`：确定性的 `wbgt_a_c` 仍是 System A Level 1 主输出，`p_ge31_optional` 只能作为可选诊断伴随列，`p_ge33_optional` 因事件支持不足仍为探索性。A-L2.1c 显示站点环境对高尾残差只有弱解释信号，分数残差不可识别，因此本契约不建立站点修正层。

## 2. System A 主输出

System A Level 1 的主输出是 `wbgt_a_c`，含义是校准后的小时级 WBGT_A 时间基线。`s_wbgt_ge31` 和 `s_wbgt_band_31_33` 只由 `wbgt_a_c` 派生，用于确定性阈值语境，不是风险分数，也不是公共预警等级。

## 3. 可选伴随列

| item                                      | decision           | allowed_column_name                                                         | caveat                                                                          |
| ----------------------------------------- | ------------------ | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| wbgt_a_c deterministic baseline           | PRIMARY            | wbgt_a_c                                                                    | Calibrated hourly WBGT_A temporal baseline, not local 100 m WBGT.               |
| s_wbgt_ge31 deterministic severity / band | PRIMARY            | s_wbgt_ge31; s_wbgt_band_31_33                                              | Severity band is deterministic WBGT_A context, not a probability or risk score. |
| p_ge31_optional                           | OPTIONAL_COMPANION | p_ge31_optional; p_ge31_model_id_optional; p_ge31_threshold_policy_optional | Station-held-out retrospective diagnostic only.                                 |
| p_ge33_optional                           | EXPLORATORY_ONLY   | p_ge33_optional                                                             | ge33 event support is below promotion threshold.                                |
| expected_exceedance_ge31_optional         | OPTIONAL_COMPANION | expected_exceedance_ge31_optional                                           | Magnitude diagnostic above 31 C; not a corrected WBGT forecast.                 |
| prediction_interval_low/high_optional     | OPTIONAL_COMPANION | prediction_interval_low_optional; prediction_interval_high_optional         | Retrospective conformal interval diagnostic; near-ge33 coverage remains weak.   |

## 4. 阈值策略登记

| policy_id   | policy_role                      | threshold | recall | precision | miss_rate | caveats                                                                                                      |
| ----------- | -------------------------------- | --------- | ------ | --------- | --------- | ------------------------------------------------------------------------------------------------------------ |
| fixed_31    | baseline_reference               | 31.000    | 0.588  | 0.682     | 0.412     | Baseline only; A-L1H.4 showed lower recall and higher miss rate than optional P_ge31 best_F1.                |
| best_F1     | retrospective_operating_point    | 0.446     | 0.765  | 0.678     | 0.235     | Selected on training folds and evaluated held-out; requires prospective validation.                          |
| recall90    | screening_high_tail_sensitive    | 0.212     | 0.946  | 0.545     | 0.054     | Improves recall but raises false alarms; use only as diagnostic screen.                                      |
| precision70 | precision_sensitive_if_supported | 0.654     | 0.363  | 0.673     | 0.637     | A-L1H.4 isotonic row is evaluated but does not strictly reach 0.70 precision; retain as recorded diagnostic. |

以上策略都不是官方公共预警阈值。

## 5. 站点注意事项

S142 仍是高尾漏报注意站点：S142: n_ge31=15.000; recall=0.533; miss_rate=0.467; false_alarm_ratio=0.000。

S139 事件支持很低且误报敏感：S139: n_ge31=1.000; recall=1.000; miss_rate=0.000; false_alarm_ratio=0.889。

这些内容是监测与解释注意事项，不是站点修正模型。

## 6. Level 2 边界

| boundary_item             | decision                               | forbidden_use                                          |
| ------------------------- | -------------------------------------- | ------------------------------------------------------ |
| level2_role               | EXPLANATORY_ONLY                       | Hourly correction layer or operational forecast model. |
| high_tail_residual_signal | WEAK_EXPLANATORY_SIGNAL_NOT_CORRECTION | Correct wbgt_a_c or create station-adjusted WBGT.      |
| score_residual            | NOT_IDENTIFIABLE                       | Claim station context fixes Level 1 score residual.    |
| station_adjusted_wbgt     | FORBIDDEN                              | station_adjusted_wbgt_c output.                        |
| local_cell_level_modifier | FORBIDDEN                              | local 100 m WBGT or System A/B coupling output.        |

Level 2 当前只能作为弱解释层，不能输出 `station_adjusted_wbgt_c`，也不能生成本地网格 WBGT。

## 7. System B 与耦合边界

本契约不使用 System B、SOLWEIG、Tmrt、形态学、cell_id 或局地辐射修饰特征，也不创建 System A/B 耦合输出。

## 8. 前瞻评估计划

未来需要冻结模型卡、输出契约和阈值策略，然后在新的正式归档快照上区分回顾行与前瞻行。LOSO 仍是回顾证据；前瞻时间验证必须报告 recall_ge31、precision_ge31、miss_rate_ge31、Brier、ECE、高尾 MAE 和站点注意事项。

## 9. 最终允许与禁止表述

允许表述：校准后的小时 WBGT_A 时间基线；可选的回顾性 `P_ge31` 诊断伴随列；可选的 31 C 超阈期望值与区间诊断；站点注意事项监测。

禁止表述：已验证的本地 100 m WBGT 预测；官方预警概率；站点修正 WBGT；System A/B 耦合输出；risk_score；hazard_score；已提升的 ge33 概率。

## 10. 下一建议通道

建议冻结并审阅 A-L1H.5 契约包。下一步应是基于冻结快照的前瞻评估协议，而不是站点修正层、局地 WBGT 或 System A/B 耦合。
