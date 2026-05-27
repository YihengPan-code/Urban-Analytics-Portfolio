# OpenHeat System A 冻结交接说明

生成日期：2026-05-27
决策状态：`A_L1H8_DOSSIER_PASS`
分支：`codex/systema-development-dossier`

## 冻结状态

System A 已冻结并等待正式快照。`wbgt_a_c` 是唯一主输出；`p_ge31_optional`、期望超阈值和区间只能作为可选诊断伴随列；`p_ge33_optional` 保持探索性。

## 交接重点

- A-L1H.5 契约不得在本交接中修改。
- A-L1H.6 和 A-L1H.7 的门槛不得在本交接中修改。
- Level 2 仅为解释性侧车，不产生站点修正或本地网格 WBGT。
- 当前等待真实正式快照；不能使用实时增长归档作为正式通过证据。
- 不创建官方预警概率、System A/B 耦合输出、risk_score 或 hazard_score。

## 未来第一步

当真实正式快照存在时，先复查 A-L1H.7 写入流程，再运行：

```bash
python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml
```

## 重入资料

- 主报告：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_report.md`
- 等待登记：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_formal_snapshot_waiting_register.csv`
- 重入提示：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_codex_reentry_prompt.md`
- 架构图：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_systema_architecture_diagram.md`

## 缺失的可选既有证据

无
