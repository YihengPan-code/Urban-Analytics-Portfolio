# OpenHeat System A L2 站点缓冲区特征 QA

生成日期：2026-05-27
决策状态：`PASS_FEATURE_QA_READY_FOR_SCOPED_MODEL`
配置：`configs/v11/systema_l2_station_feature_qa.yaml`

## 1. 为什么 A-L2.1b 接在 A-L2.1a-S1 之后

A-L2.0 已经发现 Level 1 控制之后仍存在站点层面的残差结构；A-L2.1a-S1 则为 27 个站点构建了建筑、绿地、土地利用、道路和水体的 OSM 缓冲区特征。A-L2.1b 的职责是做 QA、共线性检查和残差关联筛查，判断这些站点静态特征是否足以支持未来 A-L2.1c 的小范围站点层面预检模型。

本车道不训练残差模型。

## 2. 特征来源概览

| feature_group | feature_count | all_27_feature_count | allowed_feature_count | source_names |
| --- | --- | --- | --- | --- |
| buildings | 8 | 8 | 8 | osm_station_context_buildings |
| green | 8 | 8 | 8 | osm_station_context_green |
| landuse | 8 | 4 | 4 | osm_station_context_landuse |
| roads | 16 | 16 | 16 | osm_station_context_roads |
| water | 8 | 8 | 8 | osm_station_context_water |

本次只使用 A-L2.1a-S1 已写出的紧凑 CSV 表，不复制原始 OSM、data.gov.sg、OneMap、栅格、SOLWEIG、System B 或归档数据。

## 3. 分布与缺失情况

| feature_column | feature_group | buffer_m | feature_type | n_non_null | missing_fraction | zero_fraction | near_constant_flag | outlier_stations_robust_z |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| landuse_entropy_50m | landuse | 50 | numeric | 24 | 0.111111 | 0.500000 | no | S128:2.120(z=5.47);S125:1.835(z=4.64);S150:1.522(z=3.73);S141:1.502(z=3.68) |
| landuse_majority_50m | landuse | 50 | categorical | 24 | 0.111111 |  | no |  |
| landuse_entropy_100m | landuse | 100 | numeric | 26 | 0.037037 | 0.269231 | no |  |
| landuse_majority_100m | landuse | 100 | categorical | 26 | 0.037037 |  | no |  |
| building_count_100m | buildings | 100 | numeric | 27 | 0.000000 | 0.037037 | no | S140:64.000(z=20.23);S187:27.000(z=7.76);S135:18.000(z=4.72) |
| building_count_250m | buildings | 250 | numeric | 27 | 0.000000 | 0.000000 | no | S144:319.000(z=12.14);S140:315.000(z=11.97);S187:173.000(z=5.99) |
| building_count_500m | buildings | 500 | numeric | 27 | 0.000000 | 0.000000 | no | S144:996.000(z=8.71);S140:589.000(z=4.67);S187:517.000(z=3.96) |
| building_count_50m | buildings | 50 | numeric | 27 | 0.000000 | 0.296296 | no | S140:20.000(z=12.82);S187:8.000(z=4.72) |
| building_footprint_fraction_100m | buildings | 100 | numeric | 27 | 0.000000 | 0.074074 | no |  |
| building_footprint_fraction_250m | buildings | 250 | numeric | 27 | 0.000000 | 0.000000 | no |  |
| building_footprint_fraction_500m | buildings | 500 | numeric | 27 | 0.000000 | 0.000000 | no |  |
| building_footprint_fraction_50m | buildings | 50 | numeric | 27 | 0.000000 | 0.333333 | no | S187:0.300(z=7.31);S140:0.198(z=4.60);S151:0.170(z=3.86);S141:0.165(z=3.71) |
| distance_to_major_road_m_100m | roads | 100 | numeric | 27 | 0.000000 | 0.000000 | no | S151:2273.982(z=48.83);S187:1400.517(z=29.50);S142:456.259(z=8.60);S124:388.030(z=7.09);S135:249.300(z=4.02) |
| distance_to_major_road_m_250m | roads | 250 | numeric | 27 | 0.000000 | 0.000000 | no | S151:2273.982(z=48.83);S187:1400.517(z=29.50);S142:456.259(z=8.60);S124:388.030(z=7.09);S135:249.300(z=4.02) |
| distance_to_major_road_m_500m | roads | 500 | numeric | 27 | 0.000000 | 0.000000 | no | S151:2273.982(z=48.83);S187:1400.517(z=29.50);S142:456.259(z=8.60);S124:388.030(z=7.09);S135:249.300(z=4.02) |
| distance_to_major_road_m_50m | roads | 50 | numeric | 27 | 0.000000 | 0.000000 | no | S151:2273.982(z=48.83);S187:1400.517(z=29.50);S142:456.259(z=8.60);S124:388.030(z=7.09);S135:249.300(z=4.02) |

_Showing 16 of 48 rows._

50/100 m 的土地利用 majority/entropy 字段覆盖不完整，因此不进入 primary candidate set。常量或近常量特征也不进入小型主候选集。

## 4. 共线性簇

| collinearity_cluster | cluster_size | representative_feature | max_abs_spearman_in_cluster | cluster_members |
| --- | --- | --- | --- | --- |
| C002 | 2 | green_space_fraction_250m | 0.831602 | green_space_fraction_250m;green_space_fraction_500m |
| C004 | 4 | distance_to_water_m_250m | 1.000000 | distance_to_water_m_100m;distance_to_water_m_250m;distance_to_water_m_500m;distance_to_water_m_50m |
| C005 | 2 | road_density_m_per_ha_250m | 1.000000 | road_density_m_per_ha_250m;road_length_m_250m |
| C007 | 4 | landuse_entropy_250m | 0.853526 | landuse_entropy_100m;landuse_entropy_250m;landuse_entropy_500m;landuse_entropy_50m |
| C008 | 6 | distance_to_park_or_green_m_250m | 1.000000 | distance_to_park_or_green_m_100m;distance_to_park_or_green_m_250m;distance_to_park_or_green_m_500m;distance_to_park_or_green_m_50m;green_space_fraction_100m;green_space_fraction_50m |
| C011 | 2 | road_density_m_per_ha_500m | 1.000000 | road_density_m_per_ha_500m;road_length_m_500m |
| C013 | 6 | distance_to_major_road_m_250m | 1.000000 | distance_to_major_road_m_100m;distance_to_major_road_m_250m;distance_to_major_road_m_500m;distance_to_major_road_m_50m;major_road_length_m_100m;major_road_length_m_50m |
| C014 | 2 | building_count_250m | 0.843898 | building_count_250m;building_count_500m |
| C015 | 2 | building_count_100m | 0.825894 | building_count_100m;building_footprint_fraction_100m |
| C016 | 4 | road_density_m_per_ha_100m | 1.000000 | road_density_m_per_ha_100m;road_density_m_per_ha_50m;road_length_m_100m;road_length_m_50m |
| C018 | 2 | building_count_50m | 0.896853 | building_count_50m;building_footprint_fraction_50m |

abs(Spearman) >= 0.80 记为高共线性，abs(Spearman) >= 0.90 记为近重复。代表特征只是后续筛选建议，不是因果解释。

## 5. 缓冲区尺度冗余

| feature_group | base_feature | feature_a | feature_b | abs_spearman_r | redundancy_status | recommended_feature |
| --- | --- | --- | --- | --- | --- | --- |
| green | distance_to_park_or_green_m | distance_to_park_or_green_m_50m | distance_to_park_or_green_m_100m | 1.000000 | near_duplicate | distance_to_park_or_green_m_250m |
| green | distance_to_park_or_green_m | distance_to_park_or_green_m_50m | distance_to_park_or_green_m_250m | 1.000000 | near_duplicate | distance_to_park_or_green_m_250m |
| green | distance_to_park_or_green_m | distance_to_park_or_green_m_50m | distance_to_park_or_green_m_500m | 1.000000 | near_duplicate | distance_to_park_or_green_m_250m |
| green | distance_to_park_or_green_m | distance_to_park_or_green_m_100m | distance_to_park_or_green_m_250m | 1.000000 | near_duplicate | distance_to_park_or_green_m_250m |
| green | distance_to_park_or_green_m | distance_to_park_or_green_m_100m | distance_to_park_or_green_m_500m | 1.000000 | near_duplicate | distance_to_park_or_green_m_250m |
| green | distance_to_park_or_green_m | distance_to_park_or_green_m_250m | distance_to_park_or_green_m_500m | 1.000000 | near_duplicate | distance_to_park_or_green_m_250m |
| roads | distance_to_major_road_m | distance_to_major_road_m_50m | distance_to_major_road_m_100m | 1.000000 | near_duplicate | distance_to_major_road_m_250m |
| roads | distance_to_major_road_m | distance_to_major_road_m_50m | distance_to_major_road_m_250m | 1.000000 | near_duplicate | distance_to_major_road_m_250m |
| roads | distance_to_major_road_m | distance_to_major_road_m_50m | distance_to_major_road_m_500m | 1.000000 | near_duplicate | distance_to_major_road_m_250m |
| roads | distance_to_major_road_m | distance_to_major_road_m_100m | distance_to_major_road_m_250m | 1.000000 | near_duplicate | distance_to_major_road_m_250m |
| roads | distance_to_major_road_m | distance_to_major_road_m_100m | distance_to_major_road_m_500m | 1.000000 | near_duplicate | distance_to_major_road_m_250m |
| roads | distance_to_major_road_m | distance_to_major_road_m_250m | distance_to_major_road_m_500m | 1.000000 | near_duplicate | distance_to_major_road_m_250m |
| water | distance_to_water_m | distance_to_water_m_50m | distance_to_water_m_100m | 1.000000 | near_duplicate | distance_to_water_m_250m |
| water | distance_to_water_m | distance_to_water_m_50m | distance_to_water_m_250m | 1.000000 | near_duplicate | distance_to_water_m_250m |
| water | distance_to_water_m | distance_to_water_m_50m | distance_to_water_m_500m | 1.000000 | near_duplicate | distance_to_water_m_250m |
| water | distance_to_water_m | distance_to_water_m_100m | distance_to_water_m_250m | 1.000000 | near_duplicate | distance_to_water_m_250m |

_Showing 16 of 26 rows._

同一基础特征在 50/100/250/500 m 之间高度相关时，优先选择可解释且覆盖稳定的尺度；不会自动选择最大或最小缓冲区。

## 6. 残差关联筛查

| feature_column | target_label | spearman_r | n_pairwise | p_value_status | bootstrap_ci_low | bootstrap_ci_high | screen_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| water_fraction_100m | high-tail residual | 0.509460 | 26 | available | 0.269932 | 0.721828 | descriptive_candidate |
| distance_to_water_m_100m | high-tail residual | -0.471453 | 26 | available | -0.807481 | -0.069321 | descriptive_candidate |
| distance_to_water_m_250m | high-tail residual | -0.471453 | 26 | available | -0.806041 | -0.047533 | descriptive_candidate |
| distance_to_water_m_500m | high-tail residual | -0.471453 | 26 | available | -0.814566 | -0.071664 | descriptive_candidate |
| distance_to_water_m_50m | high-tail residual | -0.471453 | 26 | available | -0.784511 | -0.043034 | descriptive_candidate |
| road_density_m_per_ha_500m | high-tail residual | -0.469402 | 26 | available | -0.730430 | -0.101045 | descriptive_candidate |
| road_length_m_500m | high-tail residual | -0.469402 | 26 | available | -0.724212 | -0.114672 | descriptive_candidate |
| water_fraction_250m | high-tail residual | 0.440067 | 26 | available | 0.088751 | 0.710586 | descriptive_candidate |
| building_footprint_fraction_50m | score residual | -0.421715 | 27 | available | -0.691852 | -0.008773 | descriptive_candidate |
| road_density_m_per_ha_50m | score residual | -0.415751 | 27 | available | -0.706119 | -0.027630 | descriptive_candidate |
| road_length_m_50m | score residual | -0.415751 | 27 | available | -0.710686 | -0.019464 | descriptive_candidate |
| building_count_50m | score residual | -0.410353 | 27 | available | -0.668159 | -0.048648 | descriptive_candidate |
| building_count_100m | score residual | -0.398352 | 27 | available | -0.692457 | -0.030318 | descriptive_candidate |
| road_density_m_per_ha_100m | score residual | -0.375458 | 27 | available | -0.669637 | -0.010377 | descriptive_candidate |
| road_length_m_100m | score residual | -0.375458 | 27 | available | -0.692765 | -0.019848 | descriptive_candidate |
| major_road_length_m_100m | high-tail residual | -0.372508 | 26 | available | -0.673388 | 0.029810 | descriptive_candidate |

_Showing 16 of 88 rows._

这些结果只是站点层面的描述性 Spearman 筛查。概率误差结果只作为次要信息写入 CSV，因为 A-L2.0 显示该信号较弱。

## 7. S142 / S139 / S137 / S128 站点背景复核

| station_id | n_ge31 | score_residual | high_tail_residual | context_highlights |
| --- | --- | --- | --- | --- |
| S142 | 15 | 0.772569 | 2.239617 | building_footprint_fraction_100m=0.000000(below_station_iqr);building_footprint_fraction_250m=0.057495(below_station_iqr);distance_to_water_m_100m=30.393194(below_station_iqr);distance_to_water_m_250m=30.393194(below_station_iqr);distance_to_water_m_500m=30.393194(below_station_iqr) |
| S139 | 1 | -0.310600 | 0.110892 | building_footprint_fraction_250m=0.046559(below_station_iqr);distance_to_park_or_green_m_100m=311.182019(above_station_iqr);distance_to_park_or_green_m_250m=311.182019(above_station_iqr);distance_to_park_or_green_m_500m=311.182019(above_station_iqr);distance_to_park_or_green_m_50m=311.182019(above_station_iqr) |
| S137 | 13 | 0.774637 | 1.347448 | building_footprint_fraction_100m=0.019293(below_station_iqr);building_footprint_fraction_250m=0.063395(below_station_iqr);building_footprint_fraction_500m=0.024623(below_station_iqr);distance_to_park_or_green_m_100m=264.238004(above_station_iqr);distance_to_park_or_green_m_250m=264.238004(above_station_iqr) |
| S128 | 11 | 0.121816 | 1.158280 | building_footprint_fraction_250m=0.259109(above_station_iqr);distance_to_water_m_100m=30.010074(below_station_iqr);distance_to_water_m_250m=30.010074(below_station_iqr);distance_to_water_m_500m=30.010074(below_station_iqr);distance_to_water_m_50m=30.010074(below_station_iqr) |

S142 仍是 A-L2.0 中主要的高尾低估复核对象。S139 的事件支持很低，不应据此推广站点特异性概率结论。站点背景差异只能作为复核线索，不能解释为因果修正。

## 8. 建议的 A-L2.1c 候选特征集

| candidate_feature | feature_group | buffer_m | reason_selected | collinearity_cluster | allowed_for_scoped_model | recommended_role |
| --- | --- | --- | --- | --- | --- | --- |
| building_footprint_fraction_250m | buildings | 250 | configured small-set preference;full all-27 coverage;interpretable station-context feature;high-tail residual r=-0.210940 | C001 | yes | primary_candidate |
| distance_to_park_or_green_m_250m | green | 250 | configured small-set preference;full all-27 coverage;interpretable station-context feature;score residual r=0.193583 | C008 | yes | primary_candidate |
| green_space_fraction_250m | green | 250 | configured small-set preference;full all-27 coverage;interpretable station-context feature;score residual r=-0.251685 | C002 | yes | primary_candidate |
| landuse_entropy_250m | landuse | 250 | configured small-set preference;full all-27 coverage;interpretable station-context feature;score residual r=0.200977 | C007 | yes | primary_candidate |
| major_road_length_m_250m | roads | 250 | configured small-set preference;full all-27 coverage;interpretable station-context feature;high-tail residual r=-0.252823 | C006 | yes | primary_candidate |
| road_density_m_per_ha_250m | roads | 250 | configured small-set preference;full all-27 coverage;interpretable station-context feature;high-tail residual r=-0.303932 | C005 | yes | primary_candidate |
| distance_to_water_m_250m | water | 250 | configured small-set preference;full all-27 coverage;interpretable station-context feature;high-tail residual r=-0.471453 | C004 | yes | primary_candidate |
| water_fraction_250m | water | 250 | configured small-set preference;full all-27 coverage;interpretable station-context feature;high-tail residual r=0.440067 | C003 | yes | primary_candidate |

主候选集刻意保持小规模，不包含 `station_id`、官方 WBGT、残差目标、事件标签、System B 或 SOLWEIG 特征。其他完整覆盖的数值特征只作为 secondary sensitivity 或因近重复而排除。

## 9. A-L2.1c 是否可以继续

A-L2.1c may proceed only as a station-level n=27 scoped preflight model using the small primary set and sensitivity checks; no station-adjusted WBGT or causal correction.

如果未来开启 A-L2.1c，建模单位必须是站点层面 n=27，不能把站点静态特征当成小时级独立样本。

## 10. 声明边界

- 未训练模型。
- 不声称站点背景因果修正。
- 未创建站点调整后的 WBGT。
- 未创建本地 100 m WBGT。
- 未触碰 System B 或 SOLWEIG 输出。
