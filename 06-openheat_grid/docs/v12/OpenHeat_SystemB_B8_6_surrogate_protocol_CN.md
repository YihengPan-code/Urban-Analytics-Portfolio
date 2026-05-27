# OpenHeat System B B8.6 surrogate protocol / baseline gate 中文说明

生成时间：2026-05-27 16:44:12

## 结论

- B8.6 状态：`B86_WEAK_BASELINE_NEEDS_N150_MULTIFORCING`
- 数据集规模：750 行 x 42 列
- 主目标：`delta_tmrt_p90_c = overhead_as_canopy - base`
- 最佳基线摘要：random_forest_regressor on delta_tmrt_p90_c: mean main-holdout MAE=0.1616, R2=-0.145, Spearman=0.611, MAE improvement vs dummy=50.9%
- B9 状态：`BLOCKED`

## 1. 为什么 B8.6 接在 F4 后面

F4 已确认 N24 核心小时稳定性，并把 `delta_tmrt_p90_c` 作为目标卡变量。B8.6 只消费既有紧凑 N150 标签和紧凑特征表，用来建立 surrogate 协议、验证划分和基线门槛；N24/F4 只作为 stress-validation 解释上下文。

## 2. 数据集和目标定义

- 行粒度：cell × hour × `overhead_as_canopy_minus_base`。
- `cell_id` 是分组标识，不作为数值预测特征。
- `hour_sgt` 被允许进入 hour-aware 基线模型，但同时必须评估 hour holdout。
- scenario 不作为主目标预测特征，因为主目标已经是 overhead 与 base 的差值。

## 3. 验证协议

- 主证据：cell_group_holdout、spatial_holdout、typology_holdout、hour_holdout。
- random_split 仅为诊断，不作为主证据。
- forcing-day holdout 当前不可用，因为既有 N150 标签是 single-forcing；后续需要 N150 multi-forcing。

## 4. 基线模型结果

| split_family       | model                            |       MAE |     RMSE |         R2 |   Spearman_observed_vs_predicted |   MAE_improvement_fraction_over_dummy |
|:-------------------|:---------------------------------|----------:|---------:|-----------:|---------------------------------:|--------------------------------------:|
| cell_group_holdout | random_forest_regressor          | 0.178765  | 0.473795 |  0.171605  |                         0.573895 |                              0.456296 |
| cell_group_holdout | hist_gradient_boosting_regressor | 0.178811  | 0.433332 |  0.309498  |                         0.489383 |                              0.443765 |
| cell_group_holdout | elasticnet                       | 0.235825  | 0.478777 |  0.279607  |                         0.37211  |                              0.258306 |
| cell_group_holdout | ridge                            | 0.237189  | 0.479534 |  0.276628  |                         0.366933 |                              0.254245 |
| cell_group_holdout | linear_regression                | 0.237885  | 0.479866 |  0.275466  |                         0.364905 |                              0.252347 |
| cell_group_holdout | dummy_mean                       | 0.318491  | 0.604045 | -0.143881  |                       nan        |                              0        |
| hour_holdout       | random_forest_regressor          | 0.0761076 | 0.355155 |  0.69415   |                         0.824823 |                              0.764282 |
| hour_holdout       | hist_gradient_boosting_regressor | 0.095959  | 0.371539 |  0.65379   |                         0.748523 |                              0.70266  |
| hour_holdout       | elasticnet                       | 0.219268  | 0.473806 |  0.429109  |                         0.440997 |                              0.310077 |
| hour_holdout       | ridge                            | 0.219993  | 0.473987 |  0.428461  |                         0.439946 |                              0.307725 |
| hour_holdout       | linear_regression                | 0.220243  | 0.474148 |  0.427757  |                         0.439218 |                              0.306871 |
| hour_holdout       | dummy_mean                       | 0.316509  | 0.616699 | -0.0149418 |                       nan        |                              0        |
| spatial_holdout    | random_forest_regressor          | 0.202413  | 0.533209 |  0.0634701 |                         0.551462 |                              0.377576 |
| spatial_holdout    | hist_gradient_boosting_regressor | 0.218173  | 0.513208 |  0.100619  |                         0.493322 |                              0.321284 |
| spatial_holdout    | elasticnet                       | 0.250293  | 0.507792 |  0.224007  |                         0.370109 |                              0.221367 |
| spatial_holdout    | ridge                            | 0.251482  | 0.508666 |  0.219798  |                         0.366411 |                              0.217451 |
| spatial_holdout    | linear_regression                | 0.25286   | 0.509846 |  0.214871  |                         0.364519 |                              0.212964 |
| spatial_holdout    | dummy_mean                       | 0.320148  | 0.604412 | -0.0584638 |                       nan        |                              0        |
| typology_holdout   | hist_gradient_boosting_regressor | 0.180207  | 0.314543 | -0.167012  |                         0.384745 |                              0.485712 |
| typology_holdout   | random_forest_regressor          | 0.189299  | 0.361876 | -1.50948   |                         0.49493  |                              0.437699 |
| typology_holdout   | ridge                            | 0.236176  | 0.35424  | -0.374989  |                         0.241986 |                              0.289893 |
| typology_holdout   | elasticnet                       | 0.236242  | 0.354105 | -0.364943  |                         0.241111 |                              0.290532 |
| typology_holdout   | linear_regression                | 0.240856  | 0.358888 | -0.415863  |                         0.233727 |                              0.274549 |
| typology_holdout   | dummy_mean                       | 0.311346  | 0.424353 | -1.28891   |                       nan        |                              0        |

## 5. 目标敏感性

| target            | available   | best_model                       |   mean_main_MAE |   mean_main_spearman | b86_target_card_verdict                     |
|:------------------|:------------|:---------------------------------|----------------:|---------------------:|:--------------------------------------------|
| delta_tmrt_p90_c  | True        | random_forest_regressor          |        0.161646 |             0.611277 | PRIMARY_REMAINS_B8_6_TARGET_CARD            |
| tmrt_p90_c        | True        | random_forest_regressor          |        2.64406  |             0.900496 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| delta_tmrt_mean_c | True        | random_forest_regressor          |        0.2595   |             0.866057 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| delta_tmrt_p95_c  | True        | random_forest_regressor          |        0.125057 |             0.501852 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| m_rad_pct01       | True        | hist_gradient_boosting_regressor |        0.150172 |             0.690169 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |

## 6. N24 stress-validation bridge

- bridge 行数：21。
- robust priority anchors、neutral-boundary cells 和 unstable-review cells 只用于解释压力测试，不进入训练。
- h10 仍保留 caveat，不能作为 priority anchor 证据。

## 7. Surrogate 角色决定

| gate                         | status                                    | next_action                                                                                |
|:-----------------------------|:------------------------------------------|:-------------------------------------------------------------------------------------------|
| label_input                  | PASS                                      | Use compact N150 pairwise labels only; do not rerun SOLWEIG.                               |
| feature_input                | PASS                                      | Keep features compact and non-raster; do not derive new raster features in this lane.      |
| validation_protocol          | PASS                                      | Treat random_split as diagnostic only; keep grouped/holdout evidence primary.              |
| baseline_gate                | BASELINE_PROMISING                        | Review grouped/typology/hour holdout metrics before any promotion.                         |
| forcing_day_holdout          | FUTURE_REQUIRED                           | Run a future controlled N150 multi-forcing precheck/execution lane before B9 or promotion. |
| n24_stress_validation_bridge | PASS                                      | Use N24 anchors/neutral/unstable cells for interpretation checks, not training.            |
| b9_status                    | BLOCKED                                   | Keep B9 blocked until separately scoped after N150 multi-forcing and promotion review.     |
| final_status                 | B86_WEAK_BASELINE_NEEDS_N150_MULTIFORCING | N150 multi-forcing remains the next hardening recommendation unless blockers are found.    |

## 8. Claim boundaries

- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 observed truth。
- 这不是 causal feature importance。
- 没有提交 raster。
- 没有 Tmrt-to-WBGT conversion。
