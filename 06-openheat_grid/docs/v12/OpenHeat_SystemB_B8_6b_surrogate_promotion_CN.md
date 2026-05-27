# OpenHeat System B B8.6b 代理模型晋级评审说明

生成时间：2026-05-27 18:11:49

## 结论

- B8.6b 状态：`B86B_WEAK_NEEDS_FEATURE_UPGRADE`
- F5 标签行数：1500
- 唯一 cell 数：150
- 最佳主目标模型：`hist_gradient_boosting_regressor`
- 强迫日留出结果：Forcing-day holdout MAE=0.0666, R2=0.850, Spearman=0.864, top10pct=1.000, improvement=70.0%.
- AOI-wide preflight 建议：AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation.
- B9 状态：`BLOCKED`

## 为什么 B8.6b 接在 F5 后面

B8.6 只验证了单一强迫日的 N150 代理基线，并把强迫日泛化列为后续必需条件。B8.5-F5 已完成 N150 多强迫日紧凑标签，因此 B8.6b 使用 F5 标签重新评审代理模型是否可以进入未来的 AOI-wide preflight 设计评审。

## 数据和泄漏边界

- 训练目标只来自 F5 `b85_f5_pairwise_delta_by_cell_hour.csv`。
- 旧的单强迫 N150 标签只作为历史元数据，不混入训练目标。
- `cell_id` 只是分组标识，不作为数值预测变量。
- `forcing_day_id` 只用于留出验证和诊断，不进入主证据模型。
- Tmrt 目标列、delta 列、rank 列、WBGT、hazard、risk、暴露和脆弱性列均不作为预测变量。

## 目标敏感性

| target | forcing_day_MAE | forcing_day_R2 | forcing_day_spearman | forcing_day_top10pct_overlap | target_card_verdict |
| --- | --- | --- | --- | --- | --- |
| delta_tmrt_p90_c | 0.0666 | 0.8496 | 0.8641 | 1.0000 | PRIMARY_REMAINS_TARGET_CARD_VARIABLE |
| delta_tmrt_mean_c | 0.2605 | 0.6907 | 0.8640 | 0.9000 | COMPANION_TARGET_RECOMMENDED_FOR_MEAN_MEDIAN_SENSITIVITY |
| delta_tmrt_p50_c | 0.7776 | 0.4976 | 0.7822 | 0.9000 | COMPANION_TARGET_RECOMMENDED_FOR_MEAN_MEDIAN_SENSITIVITY |
| delta_tmrt_p95_c | 0.0353 | 0.9030 | 0.7757 | 0.8667 | SECONDARY_SENSITIVITY_NOT_PRIMARY_REPLACEMENT |
| base_tmrt_p90_c | 10.1135 | -1.1715 | 0.8669 | 0.8000 | SECONDARY_SENSITIVITY_NOT_PRIMARY_REPLACEMENT |
| overhead_tmrt_p90_c | 10.1093 | -1.1571 | 0.8605 | 0.7667 | SECONDARY_SENSITIVITY_NOT_PRIMARY_REPLACEMENT |

结论：`delta_tmrt_p90_c` 仍是主目标卡变量。若 mean 或 p50 更容易预测或幅度更大，它们应作为伴随目标报告，而不是自动替换 p90。

## 验证设计

- 主证据：强迫日留出。
- 支撑证据：cell 分组留出、小时留出、空间分箱留出、typology 留出。
- random split 仅为诊断，不作为晋级主证据。

## 晋级门槛

| gate | status | next_action |
| --- | --- | --- |
| label_input | PASS | Keep old single-forcing labels as metadata only. |
| feature_input | PASS | Upgrade compact features only if generalisation remains weak. |
| forcing_day_holdout | PASS | Use this as primary promotion evidence; random split remains diagnostic only. |
| cell_spatial_typology_hour_holdouts | WARN | Treat any collapsing split as a feature/target hardening signal. |
| target_sensitivity | PASS | Keep p90 primary by role; report mean/p50 as companion targets when they are more predictable or larger in magnitude. |
| anchor_neutral_unstable_audit | WARN | Keep h10 caveat separated and do not promote neutral-boundary cells from model artefacts. |
| h10_caveat | PASS | Do not use h10 alone as anchor evidence. |
| aoi_preflight | B86B_WEAK_NEEDS_FEATURE_UPGRADE | AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation. |
| b9_status | BLOCKED | B9 remains separately scoped and blocked. |
| final_status | B86B_WEAK_NEEDS_FEATURE_UPGRADE | AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation. |

## 明确不声明

- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 observed truth。
- 这不是 causal feature importance。
- 没有提交 raster。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
