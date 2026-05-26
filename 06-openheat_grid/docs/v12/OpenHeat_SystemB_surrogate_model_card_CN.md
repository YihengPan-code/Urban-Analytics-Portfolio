# OpenHeat System B Surrogate Model Card (B8.3)

生成时间: 2026-05-26 22:02:12

## 1. 模型用途

本模型卡记录 B8.2 基线结果进入 B8.3 审阅时的候选 surrogate/emulator。候选模型为 `extra_trees`，用途是近似 SOLWEIG 派生的局地辐射修饰标签，主目标为 `delta_tmrt_p90_c`。

边界：这不是观测 WBGT 校准，不是 100 m 局地 WBGT 预测，不是风险图，也不是最终 AOI 全域推理产品。树模型的表现只能作为预测诊断，不能解释为真实世界因果机制。

## 2. 输入与数据范围

- 标签集：B7/B8 N150 SOLWEIG 派生标签。
- 行数：150 cells x 2 scenarios x 5 hours = 1500 rows。
- 场景：base, overhead_as_canopy。
- 小时：10, 12, 13, 15, 16 SGT。
- 强迫条件：当前单一 forcing setup；尚未做多 forcing 稳定性检验。
- 输入特征：B8.1.1 `feature_schema.csv` 中 `role == feature` 且 `predictor_tier == physical_core` 的 115 个特征。

## 3. 目标

- 主目标：`delta_tmrt_p90_c`。
- 次目标：`tmrt_p90_c`。
- 保留标签：`m_rad_pct01`，仅用于预测后的排序/修饰标签解释，不作为主回归目标。

## 4. Feature Contract

- physical_core 特征数：115。
- exposure / vulnerability / risk / social / source / note / version / name 等禁用 token 命中数：0。
- 目标泄漏 token 命中数：0。
- 坐标是否进入 headline 特征：否。
- spatial diagnostic 坐标列数量：4，本轮 headline 模型未使用。

| item                    |   count | status   |
|:------------------------|--------:|:---------|
| SVF                     |      14 | PASS     |
| shade                   |      39 | PASS     |
| building_density_height |      23 | PASS     |
| vegetation              |       9 | PASS     |
| water                   |       3 | PASS     |
| road_hardscape          |      11 | PASS     |
| overhead                |      22 | PASS     |

## 5. 验证证据

B8.2 已覆盖 `cell_grouped_holdout`、`spatial_holdout`、`feature_bin_holdout`、`hour_holdout`、`scenario_holdout`。主目标 `delta_tmrt_p90_c` 的模型选择以 cell-grouped 与 spatial holdout 为核心，feature-bin、hour、scenario 作为诊断证据。

| split_family         | best_model_by_mae   | candidate_model   |   candidate_mae |   candidate_spearman |   candidate_improvement_over_featureless_mae |   candidate_cell_top10_overlap | evidence_status   |
|:---------------------|:--------------------|:------------------|----------------:|---------------------:|---------------------------------------------:|-------------------------------:|:------------------|
| cell_grouped_holdout | extra_trees         | extra_trees       |        0.940126 |             0.723394 |                                      1.90761 |                       0.4      | PASS              |
| spatial_holdout      | extra_trees         | extra_trees       |        0.989158 |             0.72795  |                                      1.85767 |                       0.5      | PASS              |
| feature_bin_holdout  | extra_trees         | extra_trees       |        2.22978  |             0.66344  |                                      1.86196 |                       0.458333 | PARTIAL           |
| hour_holdout         | random_forest       | extra_trees       |        0.759383 |             0.963438 |                                      2.0668  |                       0.826667 | PARTIAL           |
| scenario_holdout     | random_forest       | extra_trees       |        0.735921 |             0.89452  |                                      2.08862 |                       0.833333 | PARTIAL           |

主目标 ranking 诊断：`extra_trees` 在 cell/spatial holdout 的平均 Spearman 为 0.726，cell-level top-10% overlap 平均为 0.444。这支持内部优先级排序审阅，但不是风险预测证据。

次目标 `tmrt_p90_c` 的表现较弱，维持为 secondary diagnostic，不作为本轮主要产品：

| split_family         | model            |     MAE |    RMSE |         R2 |   spearman |   improvement_over_featureless_MAE |
|:---------------------|:-----------------|--------:|--------:|-----------:|-----------:|-----------------------------------:|
| cell_grouped_holdout | extra_trees      | 5.99429 | 6.53337 |  0.333176  |   0.374984 |                            1.30711 |
| cell_grouped_holdout | featureless_mean | 7.3014  | 8.19719 | -0.0154014 | nan        |                            0       |
| feature_bin_holdout  | extra_trees      | 6.77924 | 7.57968 |  0.174207  |   0.37425  |                            1.29048 |
| feature_bin_holdout  | featureless_mean | 8.06972 | 9.27812 | -0.164008  | nan        |                            0       |
| spatial_holdout      | extra_trees      | 6.01863 | 6.54289 |  0.338465  |   0.373191 |                            1.28268 |
| spatial_holdout      | featureless_mean | 7.3013  | 8.19595 | -0.0146491 | nan        |                            0       |

## 6. 适用范围

- `delta_tmrt_p90_c` 在 N150 内部 cell-grouped 与 spatial holdout 上有支持性证据。
- 如果只用于内部候选排序，Spearman 与 top-k 指标提供了诊断信号。
- hour/scenario transfer 只能作为诊断，因为这些切分允许同一 cell 在训练和测试中跨小时或跨场景出现。

## 7. 失败点与风险

- feature-bin / typology 外推证据较弱，且 water bin 存在 blocked/degenerate 情况。
- 当前只有 N150 样本与单一 forcing setup。
- 尚无多 forcing 稳定性证据。
- 尚无外部局地实测验证。
- 尚未进行 AOI 全域推理，也没有最终地图。
- 树模型或特征重要性不能当作因果解释。

## 8. Promotion Gate

| gate_id                            | status     | blocker_for_b9   |
|:-----------------------------------|:-----------|:-----------------|
| no_target_leakage                  | PASS       | no               |
| physical_core_feature_contract     | PASS       | no               |
| cell_grouped_performance           | PASS       | no               |
| spatial_holdout_performance        | PASS       | no               |
| feature_bin_typology_extrapolation | PARTIAL    | yes              |
| topk_prioritisation_signal         | PARTIAL    | yes              |
| secondary_tmrt_target              | PARTIAL    | no               |
| no_random_split_headline           | PASS       | no               |
| no_local_wbgt_claim                | PASS       | no               |
| no_risk_claim                      | PASS       | no               |
| multi_forcing_stability            | NOT_TESTED | yes              |
| full_aoi_inference_readiness       | FAIL       | yes              |

## 9. 决策

- candidate_for_internal_model_card_review: yes
- approved_for_final_AOI_inference: no
- recommended_next_gate: B8.5-F0 N24 x 2-3 forcing days

不得表述为 AOI 地图已获最终批准；B9 全域推理必须等待多 forcing / model-card gate 接受后再启动。

## 10. 下一步

- B8.5-F0: N24 x 2-3 forcing days，用于稳定性检验。
- B8.3b: 如评审要求，可做可选 model-card hardening。
- B9: 只有在多 forcing 与 model-card gate 接受后，才考虑 full AOI inference。
