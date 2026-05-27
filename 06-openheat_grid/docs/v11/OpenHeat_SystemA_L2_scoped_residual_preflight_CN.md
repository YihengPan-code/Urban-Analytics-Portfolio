# OpenHeat System A L2 站点残差范围化预检说明

生成日期：2026-05-27
决策状态：`A_L2_SCOPED_SIGNAL_PROMISING`

## 定位

本文件对应 A-L2.1c。它只检验 27 个站点层面的站点周边特征，是否能在留一站验证下解释 Level 1 之后仍存在的站点残差排序或幅度。它不是 Level 2 修正模型，不生成站点修正 WBGT，也不生成 100 m 本地 WBGT。

## 数据单位

输入表是一站一行，共 27 行。`station_id` 只作为标识符，不作为预测变量。主要目标为：

- `mean_context_adjusted_score_residual_c`
- `mean_context_adjusted_high_tail_residual_c`

概率误差、漏报率和误报比例只作为诊断列，不作为主要建模目标。

## 验证方式

所有模型使用留一站验证。Ridge 和 ElasticNet 在每个外层训练折内再做内层留一站选择超参数。空模型为训练站点均值。没有使用小时行作为独立样本，也没有随机拆分。

## 结果摘要

| target_label | n_stations | null_mae | best_model_family | best_feature_set_id | best_mae | mae_improvement_fraction | best_spearman | target_decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high-tail residual | 26.000000 | 0.431620 | elasticnet | compact_water_road | 0.403497 | 0.065158 | 0.357265 | A_L2_SCOPED_SIGNAL_PROMISING |
| score residual | 27.000000 | 0.287287 | one_feature_ridge | one_feature:landuse_entropy_250m | 0.282430 | 0.016907 | -0.137363 | A_L2_NOT_IDENTIFIABLE |

## 置换与稳定性

置换检验只针对每个主要目标的最佳合格非空模型，使用全数据留一站选出的固定超参数，作为预检级别的随机结构对照。

| target_label | model_family | feature_set_id | iterations | permutation_p_value_mae_directional | permutation_p_value_spearman_directional |
| --- | --- | --- | --- | --- | --- |
| high-tail residual | elasticnet | compact_water_road | 1000.000000 | 0.052947 | 0.024975 |
| score residual | one_feature_ridge | one_feature:landuse_entropy_250m | 1000.000000 | 0.141858 | 0.308691 |

## S142 / S139 限制

S142：n_ge31=15，score residual=0.7726，high-tail residual=2.2396。

S139：n_ge31=1，score residual=-0.3106，high-tail residual=0.1109。

S142 仍是高尾低估的主要警示站点。S139 的事件支持很低，不能用于推广站点级可靠性结论。

## 是否进入 A-L2.2

Proceed to A-L2.2 only as a protocol review for station-level residual explanation; do not promote to station correction, station-adjusted WBGT, or local 100 m WBGT.

## 边界声明

- 不创建站点修正 WBGT。
- 不声称站点环境是因果修正项。
- 不创建本地 100 m WBGT。
- 不提出业务化或实时预报声明。
- 站点周边特征只用于站点层面的残差解释预检。
