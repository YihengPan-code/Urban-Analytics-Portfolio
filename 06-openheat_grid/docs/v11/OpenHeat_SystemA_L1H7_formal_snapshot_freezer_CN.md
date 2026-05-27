# OpenHeat System A A-L1H.7 正式快照冻结器与模式桥

生成日期：2026-05-27
决策状态：`A_L1H7_WAITING_FOR_FORMAL_INPUT`

## 1. 为什么 A-L1H.7 接在 A-L1H.6 之后

A-L1H.5 已经冻结 System A Level 1 的小时输出契约。A-L1H.6 已经建立前瞻评估框架，但当前状态仍在等待正式冻结快照。A-L1H.7 的作用是把未来快照创建过程做成可复查的冻结器与模式桥：只检查紧凑候选表，只在语义安全时桥接列名，并输出 READY、WAITING 或 BLOCKED 证据包。

## 2. 候选表搜索结果

本轮只搜索配置中的正式/前瞻紧凑根目录，允许 `.csv`、`.csv.gz` 和 `.parquet`。候选表数量：`6`。最佳候选：`无`。

## 3. 列映射结果

目标列来自 A-L1H.6 必需输入模式。精确列名直接通过；安全别名只有在时区语义或契约来源清楚时才会使用。`timestamp` 这类列如果不能确认 SGT 语义，会记录为 `AMBIGUOUS_MAPPING`，不会静默改名。

## 4. 模式与禁用列检查

必需列包括 `timestamp_sgt`、`timestamp_utc`、`station_id`、`official_wbgt_c`、`wbgt_a_c`、`wbgt_a_model_id`、`wbgt_a_version`、`is_retrospective_or_prospective` 和 `quality_flag`。禁用列包括 `cell_id`、`local_wbgt_c`、`delta_wbgt_cell`、`station_adjusted_wbgt_c`、`risk_score` 和 `hazard_score`。一旦候选正式快照含有禁用列，该候选会被拒绝。

## 5. 冻结就绪决策

冻结模式：`dry_run`。

最佳候选支持度：`n_rows=NA`，`n_prospective_rows=NA`，`n_ge31=NA`，`n_ge33=NA`。

只有在必需列齐全或安全映射、禁用列缺失、前瞻行数与 ge31 事件达到配置阈值、`official_wbgt_c` 与 `wbgt_a_c` 为数值、模型和版本元数据存在、`quality_flag` 存在、且回顾/前瞻标签存在时，才会输出 `A_L1H7_READY_TO_FREEZE`。

## 6. dry_run 与 write_snapshot 行为

默认 `dry_run` 不写正式快照数据表，只写清单、检查表、清单模式、验证表、命令模板、报告和状态文件。只有当配置显式设置 `freeze_mode: write_snapshot` 且真实候选表通过检查时，才会在 `outputs/v11_systema_l1_high_tail/formal_snapshot/` 写出紧凑 CSV.GZ 快照。

## 7. 下游 A-L1H.6 重跑说明

A-L1H.7 不会自动运行 A-L1H.6。正式快照写出并复查后，再运行：

`python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml`

## 8. 声明边界

- 不训练新模型。
- 不修改 archive collector。
- 不创建 station-adjusted WBGT。
- 不创建本地 100 m WBGT。
- 不创建官方预警概率。
- 不创建 risk_score 或 hazard_score。
- 不创建 System A/B 耦合输出。
- 不使用 System B、SOLWEIG 或 Tmrt 特征。
- 不创建伪指标或伪快照行。
