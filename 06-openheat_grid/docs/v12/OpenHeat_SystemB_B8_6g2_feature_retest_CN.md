# OpenHeat System B B8.6g2 特征升级代理模型复测说明

生成时间：2026-05-27 23:03:52

## 结论

- B8.6g2 状态：`B86G2_DIAGNOSTIC_IMPROVEMENT_ONLY`
- 选定工作流：`b86g_proxy_features_only` + `logistic_regression` / `ridge`
- 主目标：`delta_tmrt_p90_c`
- 中性阈值：0.05 C
- AOI / B9：继续阻断；本轮不生成 AOI-wide prediction，也不进入 B9。

## 为什么接在 B8.6g 后面

B8.6g 只完成了紧凑/矢量派生特征获取，没有训练最终代理模型，也没有生成 AOI 范围预测。B8.6g2 的作用是在 N150 紧凑数据上复测这些新特征是否改善 spatial、typology、cell-group、forcing-day 和 hour 留出验证。

## 输入规模

- 建模行数：1500
- 唯一 cell 数：150
- 特征表通过 `cell_id` 与 F5 标签连接；`cell_id` 只用于元数据和分组，不作为数值预测特征。

## 泄漏审计和特征集

目标派生列、状态/方法/来源列、路径列、raster/QGIS/SOLWEIG/WBGT/risk/hazard/observed 相关列均被排除。`hour_sgt` 可作为预测特征，但 hour holdout 必须保留为泛化检验。

| feature_set                      |   feature_count |   proxy_feature_count |   vector_or_vector_compact_feature_count | status    |
|:---------------------------------|----------------:|----------------------:|-----------------------------------------:|:----------|
| b86d_baseline_without_b86g       |              11 |                     0 |                                        0 | AVAILABLE |
| b86g_proxy_features_only         |              17 |                    16 |                                        2 | AVAILABLE |
| b86g_vector_derived_compact_only |               4 |                     0 |                                        3 | AVAILABLE |
| b86g_proxy_plus_vector_compact   |              20 |                    16 |                                        5 | AVAILABLE |
| b86g_no_status_columns           |              21 |                    17 |                                        5 | AVAILABLE |
| b86g_high_priority_only          |              12 |                     8 |                                        5 | AVAILABLE |
| b86g_all_safe_numeric            |              20 |                    16 |                                        5 | AVAILABLE |

## 主要验证结果

| split_family        |    MAE |   Spearman |   top10pct_overlap |   neutral_accuracy |   false_promotion_rate |
|:--------------------|-------:|-----------:|-------------------:|-------------------:|-----------------------:|
| cell_group_holdout  | 0.1659 |     0.5266 |             0.5333 |             0.8589 |                 0.1411 |
| forcing_day_holdout | 0.1352 |     0.676  |             0.6    |             0.8913 |                 0.1087 |
| hour_holdout        | 0.1397 |     0.6651 |             0.6    |             0.8856 |                 0.1144 |
| spatial_holdout     | 0.168  |     0.5174 |             0.5    |             0.8372 |                 0.1628 |
| typology_holdout    | 0.199  |     0.4104 |             0.5619 |             0.7907 |                 0.2093 |

## 与 B8.6d / B8.6f 的比较

| split_family        |   Spearman_delta_vs_b86d |   top10_delta_vs_b86d |   false_promotion_delta_vs_b86d |   anchor_MAE_delta_vs_b86d | b86f_context_status   |
|:--------------------|-------------------------:|----------------------:|--------------------------------:|---------------------------:|:----------------------|
| cell_group_holdout  |                   0.0643 |               -0.0667 |                         -0.0761 |                    -0.0271 | BLOCKED               |
| forcing_day_holdout |                  -0.0331 |               -0.2    |                          0.0031 |                     0.3156 | not_mapped            |
| hour_holdout        |                  -0.0474 |               -0.2267 |                          0.0059 |                     0.2112 | not_mapped            |
| spatial_holdout     |                   0.3453 |                0.1875 |                         -0.075  |                    -0.2182 | BLOCKED               |
| typology_holdout    |                   0.0493 |               -0.1524 |                         -0.046  |                     0.1436 | DIAGNOSTIC_ONLY       |

## 特征消融

spatial_help=neighbourhood_context; neutral_false_promotion_help=canyon_roughness, edge_context, neighbourhood_context, overhead_geometry, pedestrian_shade, tree_building_interaction, typology_geometry; anchor_help=canyon_roughness, edge_context, neighbourhood_context, overhead_geometry, tree_building_interaction, typology_geometry

## 锚点、中性边界和不稳定单元

- 锚点诊断行数：21
- 中性/近零诊断行数：68
- 不稳定单元诊断行数：33

## AOI 预检和下一路线

AOI preflight 仍为阻断状态；即使出现诊断改善，也只能建议未来单独评审的 dry-run preflight，不能在本轮执行。推荐下一路线：`B8.7-N300-PRE plus B8.6g3 true vector source acquisition`。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk score 或 hazard score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有 Tmrt-to-WBGT 转换。
- 没有 System A/B coupling。
