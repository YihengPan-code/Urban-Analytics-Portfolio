# OpenHeat 新聊天重入上下文（2026-05-28）

项目身份：A WBGT-gated, SOLWEIG-informed, surrogate-assisted local heat hazard ranking prototype for Toa Payoh, Singapore.

主 worktree：`C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid`  
可读 sibling：`C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid`；`C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_al1h/06-openheat_grid`

## 当前最佳状态

- System A：冻结等待。`wbgt_a_c` 是唯一主输出；P_ge31/expected exceedance/interval 是可选诊断；P_ge33 探索性；A-L1H.6/7 等真实 formal snapshot。
- System B：B87C raw SOLWEIG full_150 完成，B87D N300 label pass，B87E/F no promotion，B87F2 是最佳本地源 checkpoint，B87G0 结论是 external-source-required。
- 当前 stop/go：停止模型调参；只允许 external true-vector source acquisition 或关闭 System B surrogate phase。AOI/B9/WBGT/risk 全部 blocked。

## 先读文件

- `docs/handoff/OpenHeat_SystemA_SystemB_FULL_DEVLOG_2026-05-28_CN.md`
- `docs/handoff/OpenHeat_NEW_CHAT_REENTRY_CONTEXT_2026-05-28_CN.md`
- `outputs/devlog_2026_05_28/OPENHEAT_DEVLOG_STATUS.md`
- `outputs/v12_surrogate/b87g0_source_breakthrough_attempt/B87G0_STATUS.md`
- `outputs/v12_surrogate/b87g0_source_breakthrough_attempt/b87g0_report.md`
- `outputs/v12_surrogate/b87f2_true_vector_feature_patch/B87F2_STATUS.md`
- `outputs/v12_surrogate/b87d_n300_label_integration/B87D_STATUS.md`
- `docs/handoff/OpenHeat_SystemA_FROZEN_HANDOFF_2026-05-27_CN.md`
- `outputs/v11_systema_l1_high_tail/systema_development_dossier/A_L1H8_STATUS.md`

## 推荐下一 lane

1. System A：只有真实 formal snapshot 已存在时，先运行 A-L1H.7 freeze，再运行 A-L1H.6 prospective eval。
2. System B：只有外部 connected shade corridor / true tree-building source 可用时，开 external true-vector acquisition；否则写 closure note。
3. Product C/Risk：必须等 System A formal snapshot pass + System B AOI preflight source gates clear；risk 还需 exposure/vulnerability。

## 禁止表述

- 不说 local 100m WBGT。
- 不说 official warning probability。
- 不说 observed truth。
- 不说 AOI/B9 inference 已完成。
- 不说 hazard/risk/exposure/vulnerability output。
- 不说 SOLWEIG Tmrt 等于 WBGT。

## 重入命令

当前 PowerShell 中 bare `python` 不在 PATH；本轮验证使用 `C:/Users/CloudStar/anaconda3/envs/openheat/python.exe`。

### B8 / devlog / System B worktree

```powershell
cd C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid
git status -sb -uno
git status --short -- .
C:/Users/CloudStar/anaconda3/envs/openheat/python.exe scripts/v12_devlog_run.py --config configs/v12/openheat_devlog_2026_05_28.yaml
```

### AL1H / System A reactivation worktree

```powershell
cd C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_al1h/06-openheat_grid
git status -sb -uno
git status --short -- .
C:/Users/CloudStar/anaconda3/envs/openheat/python.exe scripts/v11_l1h7_run_formal_snapshot_freezer.py --config configs/v11/systema_l1h7_formal_snapshot_freezer.yaml
C:/Users/CloudStar/anaconda3/envs/openheat/python.exe scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml
```
