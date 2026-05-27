# OpenHeat System A A-L1H.6 前瞻评估框架

生成日期：2026-05-27
决策状态：`A_L1H6_WAITING_FOR_FORMAL_SNAPSHOT`

## 1. 为什么 A-L1H.6 接在 A-L1H.5 之后

A-L1H.5 已冻结 System A Level 1 的模型卡与小时输出契约。本通道不重新训练模型，也不改变契约决策；它只准备未来正式冻结快照的前瞻评估框架。

## 2. 冻结契约依赖

本框架依赖 A-L1H.5 的状态文件、小时输出契约、输出模式表、阈值策略登记表和站点注意事项登记表。`wbgt_a_c` 仍是主输出；`p_ge31_optional` 仍是可选诊断伴随列；`p_ge33_optional` 仍是探索性列。

## 3. 快照检测结果

检测结果：`WAITING_FOR_FORMAL_SNAPSHOT`。

候选快照：`无`。

如果没有有效正式前瞻快照，本框架输出 `WAITING_FOR_FORMAL_SNAPSHOT`，并且不生成伪造指标。

## 4. 未来输入模式

未来正式快照必须包含：`timestamp_sgt`、`timestamp_utc`、`station_id`、`official_wbgt_c`、`wbgt_a_c`、`wbgt_a_model_id`、`wbgt_a_version`、`is_retrospective_or_prospective` 和 `quality_flag`。

可选列包括：`p_ge31_optional`、`p_ge31_model_id_optional`、`p_ge31_threshold_policy_optional`、`p_ge33_optional`、`expected_exceedance_ge31_optional`、区间上下界和 `lead_time_hours_optional`。

## 5. 评估指标

有正式前瞻行时，框架会报告 `n_rows`、`n_stations`、`n_ge31`、`n_ge33`、ge31 的召回率、精确率、漏报率、误报比例、CSI、`p_ge31_optional` 的 Brier 和 ECE、高尾 MAE、固定 31 C 基线、可选 P_ge31 策略、期望超阈误差、区间覆盖率以及站点注意事项刷新。

## 6. 提升门槛逻辑

`p_ge31_optional` 当前门槛状态：`P_GE31_REMAINS_OPTIONAL_WAITING`。只有在正式前瞻快照中相对 `wbgt_a_c` fixed_31 保持实质性召回/漏报改善、精确率与误报表现可接受、Brier/ECE 稳定且站点注意事项未失败时，才可进入更强的内部伴随列讨论。

`p_ge33_optional` 当前状态：`P_GE33_REMAINS_EXPLORATORY`。除非至少有 30 个 ge33 事件并有明确校准证据，否则仍保持探索性。

## 7. 站点注意事项刷新

站点注意事项刷新正在等待正式快照。

这些站点结果只是监测和解释注意事项，不是站点修正模型。

## 8. 声明边界

- 不训练新模型。
- 不创建站点修正 WBGT。
- 不创建本地 100 m WBGT。
- 不创建官方预警概率。
- 不创建 risk_score 或 hazard_score。
- 不创建 System A/B 耦合输出。
- 不使用 System B、SOLWEIG 或 Tmrt 特征。

## 9. 下一步建议

在未来正式快照冻结后，把紧凑 CSV/CSV.GZ/Parquet 快照放入配置中的候选目录，并重新运行：

`python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml`
