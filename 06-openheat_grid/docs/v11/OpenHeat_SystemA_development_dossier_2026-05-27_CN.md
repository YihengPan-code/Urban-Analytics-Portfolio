# OpenHeat System A 开发档案与冻结交接

生成日期：2026-05-27
决策状态：`A_L1H8_DOSSIER_PASS`

## 1. 当前 System A 状态

System A 当前处于冻结/等待状态。A-L1H.5 已冻结 Level 1 小时输出契约，`wbgt_a_c` 是确定性的主输出。A-L1H.6 已建立前瞻评估框架，但等待真实的正式快照。A-L1H.7 已建立正式快照冻结器，但当前等待真实正式输入。A-L2.1c 只保留为解释性侧车。

## 2. 证据链

证据链从高尾残差诊断、公式/代理审计、概率阈值校准、高尾基准、Level 2 可识别性与站点特征 QA，推进到 A-L1H.4 伴随概率套件、A-L1H.5 输出契约、A-L1H.6 前瞻框架和 A-L1H.7 快照冻结器。本轮只做归档、综合和交接，不训练新模型。

## 3. 输出契约

A-L1H.5 的冻结契约要求：`timestamp_sgt`、`timestamp_utc`、`wbgt_a_c`、`wbgt_a_model_id`、`wbgt_a_version`、`s_wbgt_ge31`、`s_wbgt_band_31_33`、`source_forcing`、`is_retrospective_or_prospective` 和 `quality_flag`。

可选诊断列包括：`p_ge31_optional`、`p_ge33_optional`、`expected_exceedance_ge31_optional`、`prediction_interval_low_optional` 和 `prediction_interval_high_optional`。

禁止列包括：`station_adjusted_wbgt_c`、`local_wbgt_c`、`delta_wbgt_cell`、`risk_score` 和 `hazard_score`。

## 4. Level 2 边界

Level 2 只是解释性侧车。它不产生站点修正 WBGT，不产生本地 100 m WBGT，不产生 System B 修饰量，也不产生 System A/B 耦合输出。更长归档、更好的站点元数据、SVF、LCZ 和站点布设数据只能作为未来解释性选项。

## 5. 正式快照说明

正式快照是未来前瞻评估和任何更强伴随列讨论的前置条件。快照必须包含冻结契约所需字段，必须区分回顾行和前瞻行，并且需要足够行数和事件支持。不能把持续增长的实时归档当作正式通过证据，也不能创建伪造快照行。

## 6. 未来重启路径

未来重启时，先检查分支和工作区状态，读取本档案和 A-L1H.5 契约。如果真实正式快照已经存在，先运行 A-L1H.7 写入冻结快照；确认 manifest 和 validation 后，再运行 A-L1H.6 前瞻评估。只有正式评估支持时，才讨论 `p_ge31_optional` 的更强内部伴随状态。除非门槛失败且用户明确开启新通道，否则不训练新模型。

## 7. 允许与禁止表述

| claim                                         | decision              | allowed_wording                                                       | forbidden_upgrade                           |
| --------------------------------------------- | --------------------- | --------------------------------------------------------------------- | ------------------------------------------- |
| WBGT_A deterministic temporal baseline        | ALLOWED               | WBGT_A deterministic temporal baseline.                               | Validated local WBGT prediction.            |
| P_ge31 optional diagnostic companion          | ALLOWED_WITH_BOUNDARY | P_ge31 optional diagnostic companion.                                 | Official warning probability.               |
| retrospective LOSO evidence                   | ALLOWED               | Retrospective station-held-out LOSO evidence.                         | Final prospective pass.                     |
| prospective harness ready                     | ALLOWED               | Prospective evaluation harness ready and waiting for formal snapshot. | Prospective evaluation complete.            |
| Level 2 explanatory weak signal               | ALLOWED_WITH_BOUNDARY | Level 2 shows weak high-tail explanatory signal.                      | Station correction or causal driver proof.  |
| official warning probability                  | FORBIDDEN             | None.                                                                 | Official warning probability.               |
| station-adjusted WBGT                         | FORBIDDEN             | None.                                                                 | station_adjusted_wbgt_c.                    |
| local 100m WBGT                               | FORBIDDEN             | None.                                                                 | local_wbgt_c or validated 100 m local WBGT. |
| risk/hazard score                             | FORBIDDEN             | None.                                                                 | risk_score or hazard_score.                 |
| System A/B coupling claim                     | FORBIDDEN             | None.                                                                 | System A/B coupling output.                 |
| final prospective pass before formal snapshot | FORBIDDEN             | Waiting for formal snapshot.                                          | Final prospective pass.                     |

## 8. Codex 重入提示

未来提示已写入：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_codex_reentry_prompt.md`。

## 9. 架构图

架构图已写入：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_systema_architecture_diagram.md`。

## 10. 车道状态矩阵

| lane_item                      | current_decision              | blocker                                                                                     | allowed_next_action                                                                         | forbidden_action                                             |
| ------------------------------ | ----------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Level 1 deterministic baseline | PRIMARY_FROZEN                | None for current frozen contract; prospective validation still pending for stronger claims. | Evaluate wbgt_a_c on a future formal snapshot.                                              | Replace primary output without a new explicit lane.          |
| P_ge31 companion               | OPTIONAL_DIAGNOSTIC_COMPANION | No formal prospective snapshot yet.                                                         | Evaluate promotion gates in A-L1H.6 after snapshot.                                         | Call it official warning probability.                        |
| expected exceedance            | OPTIONAL_DIAGNOSTIC           | Prospective evaluation absent.                                                              | Report as internal diagnostic if populated by contract.                                     | Treat as corrected WBGT forecast.                            |
| conformal interval             | OPTIONAL_DIAGNOSTIC           | Near-ge33 support weak; prospective validation absent.                                      | Retain interval diagnostics in formal evaluation.                                           | Claim guaranteed operational interval.                       |
| P_ge33                         | EXPLORATORY_LOW_SUPPORT       | Insufficient ge33 event support.                                                            | Report support count; revisit only with at least 30 real events and calibration evidence.   | Promote severe warning probability.                          |
| Level 2 residual explanation   | EXPLANATORY_ONLY              | n=27 station constraints, S142/S139 caveats, limited station metadata.                      | Future explanatory protocol with longer archive and better station metadata/SVF/LCZ/siting. | Create station correction or System B modifier.              |
| station-adjusted WBGT          | FORBIDDEN                     | No identifiable score residual correction and no validated station correction model.        | None in current lane.                                                                       | Output station_adjusted_wbgt_c.                              |
| local 100m WBGT                | FORBIDDEN                     | System A does not convert SOLWEIG/Tmrt or station context into local WBGT.                  | None in current lane.                                                                       | Output local_wbgt_c or delta_wbgt_cell.                      |
| formal snapshot                | WAITING_FOR_REAL_INPUT        | No real compact candidate with required schema and support.                                 | Run A-L1H.7 write_snapshot after reviewed input exists.                                     | Use live-growing archive as formal pass or create fake rows. |
| prospective evaluation         | HARNESS_READY_WAITING         | Formal snapshot missing.                                                                    | Run A-L1H.6 after formal snapshot freeze.                                                   | Claim final prospective pass before snapshot.                |
| System B coupling              | OUT_OF_SCOPE_FORBIDDEN        | No scoped coupling lane and no validated coupling contract.                                 | Open a separate future lane only if explicitly requested.                                   | Create System A/B coupling output in this lane.              |
| risk/hazard                    | FORBIDDEN                     | Exposure and vulnerability are not explicit and no risk model is complete.                  | Discuss future risk overlay only after separate explicit scope.                             | Output risk_score or hazard_score.                           |
