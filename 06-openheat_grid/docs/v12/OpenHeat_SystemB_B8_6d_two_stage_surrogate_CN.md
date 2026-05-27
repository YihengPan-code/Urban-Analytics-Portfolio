# OpenHeat System B B8.6d 两阶段代理工作流说明

生成时间：2026-05-27 20:29:14

## 结论

- B8.6d 状态：`B86D_TWO_STAGE_DIAGNOSTIC_ONLY`
- 主目标：`delta_tmrt_p90_c = overhead_as_canopy - base`
- 最佳阈值：0.05 C
- Stage 1 分类器：`logistic_regression`
- Stage 2 回归器：`ridge`
- B9 状态：`B9_BLOCKED`

## 为什么接在 B8.6c 后面

B8.6c 显示，简单增加安全特征并没有明显修复 cell-group、空间和 typology 留出的弱项；但两阶段预检对中性边界和支持性排序有改善信号。因此 B8.6d 只在紧凑 N150 数据上正式评审两阶段工作流，不生成 AOI-wide 预测。

## 中性边界定义

`neutral = abs(delta_tmrt_p90_c) <= threshold`。`delta_tmrt_p90_c < -threshold` 被视为 meaningful cooling；正值或弱正值只跟踪，不作为晋级冷却候选。

## 综合结果

| split_family        |    MAE |   Spearman |   top10pct_overlap |   neutral_accuracy |   false_promotion_rate |
|:--------------------|-------:|-----------:|-------------------:|-------------------:|-----------------------:|
| cell_group_holdout  | 0.1741 |     0.4623 |             0.6    |             0.7387 |                 0.2172 |
| forcing_day_holdout | 0.0864 |     0.7091 |             0.8    |             0.8607 |                 0.1056 |
| hour_holdout        | 0.088  |     0.7125 |             0.8267 |             0.8667 |                 0.1085 |
| spatial_holdout     | 0.2243 |     0.172  |             0.3125 |             0.667  |                 0.2378 |
| typology_holdout    | 0.2937 |     0.3611 |             0.7143 |             0.7143 |                 0.2553 |

## 目标角色

`delta_tmrt_p90_c` 仍作为热口袋 / 上尾部主目标。`delta_tmrt_mean_c`、`delta_tmrt_p50_c`、`delta_tmrt_p95_c` 作为伴随敏感性输出，不自动替换 p90。

## 边界

- 这不是 B9。
- 这不是 AOI-wide prediction。
- 这不是 local WBGT。
- 这不是 hazard_score 或 risk_score。
- 这不是 observed truth。
- 这不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 SOLWEIG 或 QGIS。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
